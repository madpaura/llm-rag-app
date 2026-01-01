"""
In-memory caching service for performance optimization.
Provides LRU cache for embeddings, query results, and frequently accessed data.
"""
import asyncio
import time
from typing import Any, Dict, Optional, Callable, TypeVar, Generic
from functools import wraps
from collections import OrderedDict
import hashlib
import json
import structlog
from dataclasses import dataclass, field
from threading import Lock

logger = structlog.get_logger()

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with TTL support."""
    value: T
    created_at: float
    ttl: Optional[float] = None
    hits: int = 0
    
    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl


class LRUCache(Generic[T]):
    """
    Thread-safe LRU cache with TTL support.
    Optimized for multi-user scenarios.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: Optional[float] = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = Lock()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}
    
    def _make_key(self, key: Any) -> str:
        """Create a hashable key from any input."""
        if isinstance(key, str):
            return key
        try:
            key_str = json.dumps(key, sort_keys=True, default=str)
            return hashlib.md5(key_str.encode()).hexdigest()
        except (TypeError, ValueError):
            return str(hash(str(key)))
    
    def get(self, key: Any) -> Optional[T]:
        """Get value from cache."""
        cache_key = self._make_key(key)
        
        with self._lock:
            if cache_key not in self._cache:
                self._stats["misses"] += 1
                return None
            
            entry = self._cache[cache_key]
            
            if entry.is_expired():
                del self._cache[cache_key]
                self._stats["misses"] += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(cache_key)
            entry.hits += 1
            self._stats["hits"] += 1
            
            return entry.value
    
    def set(self, key: Any, value: T, ttl: Optional[float] = None) -> None:
        """Set value in cache."""
        cache_key = self._make_key(key)
        
        with self._lock:
            # Remove if exists
            if cache_key in self._cache:
                del self._cache[cache_key]
            
            # Evict oldest if at capacity
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
                self._stats["evictions"] += 1
            
            self._cache[cache_key] = CacheEntry(
                value=value,
                created_at=time.time(),
                ttl=ttl if ttl is not None else self.default_ttl
            )
    
    def delete(self, key: Any) -> bool:
        """Delete value from cache."""
        cache_key = self._make_key(key)
        
        with self._lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """Remove expired entries. Returns count of removed entries."""
        removed = 0
        with self._lock:
            expired_keys = [
                k for k, v in self._cache.items() if v.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]
                removed += 1
        return removed
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / total if total > 0 else 0
            return {
                **self._stats,
                "size": len(self._cache),
                "max_size": self.max_size,
                "hit_rate": round(hit_rate, 4)
            }


class EmbeddingCache:
    """
    Specialized cache for embeddings.
    Caches both text embeddings and query embeddings.
    """
    
    def __init__(self, max_size: int = 5000, ttl: float = 7200):
        self._cache = LRUCache[list](max_size=max_size, default_ttl=ttl)
        self.logger = structlog.get_logger()
    
    def get_embedding(self, text: str) -> Optional[list]:
        """Get cached embedding for text."""
        return self._cache.get(text)
    
    def set_embedding(self, text: str, embedding: list) -> None:
        """Cache embedding for text."""
        self._cache.set(text, embedding)
    
    def get_batch_embeddings(self, texts: list) -> tuple[list, list, list]:
        """
        Get cached embeddings for batch of texts.
        Returns: (cached_embeddings, cached_indices, uncached_texts)
        """
        cached = []
        cached_indices = []
        uncached = []
        
        for i, text in enumerate(texts):
            embedding = self._cache.get(text)
            if embedding is not None:
                cached.append(embedding)
                cached_indices.append(i)
            else:
                uncached.append((i, text))
        
        return cached, cached_indices, uncached
    
    def set_batch_embeddings(self, texts: list, embeddings: list) -> None:
        """Cache batch of embeddings."""
        for text, embedding in zip(texts, embeddings):
            self._cache.set(text, embedding)
    
    @property
    def stats(self) -> Dict[str, Any]:
        return self._cache.stats


class QueryResultCache:
    """
    Cache for RAG query results.
    Caches search results and generated answers.
    """
    
    def __init__(self, max_size: int = 500, ttl: float = 1800):
        self._search_cache = LRUCache[list](max_size=max_size, default_ttl=ttl)
        self._answer_cache = LRUCache[dict](max_size=max_size // 2, default_ttl=ttl)
    
    def _make_search_key(self, query: str, workspace_id: int, k: int) -> str:
        """Create cache key for search query."""
        return f"search:{workspace_id}:{k}:{hashlib.md5(query.encode()).hexdigest()}"
    
    def _make_answer_key(self, query: str, workspace_id: int, technique: str) -> str:
        """Create cache key for answer."""
        return f"answer:{workspace_id}:{technique}:{hashlib.md5(query.encode()).hexdigest()}"
    
    def get_search_results(self, query: str, workspace_id: int, k: int) -> Optional[list]:
        """Get cached search results."""
        key = self._make_search_key(query, workspace_id, k)
        return self._search_cache.get(key)
    
    def set_search_results(self, query: str, workspace_id: int, k: int, results: list) -> None:
        """Cache search results."""
        key = self._make_search_key(query, workspace_id, k)
        self._search_cache.set(key, results)
    
    def get_answer(self, query: str, workspace_id: int, technique: str) -> Optional[dict]:
        """Get cached answer."""
        key = self._make_answer_key(query, workspace_id, technique)
        return self._answer_cache.get(key)
    
    def set_answer(self, query: str, workspace_id: int, technique: str, answer: dict) -> None:
        """Cache answer."""
        key = self._make_answer_key(query, workspace_id, technique)
        self._answer_cache.set(key, answer)
    
    def invalidate_workspace(self, workspace_id: int) -> None:
        """Invalidate all cache entries for a workspace."""
        # Note: This is a simple implementation. For production,
        # consider using a more efficient invalidation strategy.
        self._search_cache.clear()
        self._answer_cache.clear()
    
    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "search_cache": self._search_cache.stats,
            "answer_cache": self._answer_cache.stats
        }


# Global cache instances (singletons)
_embedding_cache: Optional[EmbeddingCache] = None
_query_cache: Optional[QueryResultCache] = None
_general_cache: Optional[LRUCache] = None


def get_embedding_cache() -> EmbeddingCache:
    """Get or create embedding cache singleton."""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache()
    return _embedding_cache


def get_query_cache() -> QueryResultCache:
    """Get or create query result cache singleton."""
    global _query_cache
    if _query_cache is None:
        _query_cache = QueryResultCache()
    return _query_cache


def get_general_cache() -> LRUCache:
    """Get or create general purpose cache singleton."""
    global _general_cache
    if _general_cache is None:
        _general_cache = LRUCache(max_size=2000)
    return _general_cache


def cached(cache_name: str = "general", ttl: Optional[float] = None):
    """
    Decorator for caching function results.
    
    Usage:
        @cached("embeddings", ttl=3600)
        async def get_embedding(text: str) -> list:
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache = get_general_cache()
            key = f"{func.__name__}:{args}:{kwargs}"
            
            result = cache.get(key)
            if result is not None:
                return result
            
            result = await func(*args, **kwargs)
            cache.set(key, result, ttl=ttl)
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache = get_general_cache()
            key = f"{func.__name__}:{args}:{kwargs}"
            
            result = cache.get(key)
            if result is not None:
                return result
            
            result = func(*args, **kwargs)
            cache.set(key, result, ttl=ttl)
            return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


async def cleanup_caches():
    """Cleanup expired entries from all caches."""
    removed = 0
    
    if _embedding_cache:
        removed += _embedding_cache._cache.cleanup_expired()
    
    if _query_cache:
        removed += _query_cache._search_cache.cleanup_expired()
        removed += _query_cache._answer_cache.cleanup_expired()
    
    if _general_cache:
        removed += _general_cache.cleanup_expired()
    
    if removed > 0:
        logger.info(f"Cache cleanup: removed {removed} expired entries")
    
    return removed


def get_all_cache_stats() -> Dict[str, Any]:
    """Get statistics from all caches."""
    return {
        "embedding_cache": _embedding_cache.stats if _embedding_cache else None,
        "query_cache": _query_cache.stats if _query_cache else None,
        "general_cache": _general_cache.stats if _general_cache else None
    }
