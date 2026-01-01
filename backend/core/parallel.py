"""
Parallel processing utilities for improved ingestion performance.
Provides async task management and batch processing.
"""
import asyncio
from typing import List, TypeVar, Callable, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass
import structlog
import time

from .config import get_settings

logger = structlog.get_logger()
settings = get_settings()

T = TypeVar('T')
R = TypeVar('R')


@dataclass
class BatchResult:
    """Result of a batch operation."""
    successful: List[Any]
    failed: List[Tuple[Any, Exception]]
    total_time: float
    items_per_second: float


class ParallelProcessor:
    """
    Utility for parallel processing of tasks.
    Supports both async and thread-based parallelism.
    """
    
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or settings.MAX_PARALLEL_EMBEDDINGS
        self._thread_pool = ThreadPoolExecutor(max_workers=self.max_workers)
        self.logger = structlog.get_logger()
    
    async def map_async(
        self,
        func: Callable[[T], R],
        items: List[T],
        batch_size: int = None,
        progress_callback: Callable[[int, int], None] = None
    ) -> List[R]:
        """
        Apply async function to items in parallel batches.
        
        Args:
            func: Async function to apply
            items: List of items to process
            batch_size: Items per batch (default: max_workers)
            progress_callback: Optional callback(completed, total)
            
        Returns:
            List of results in same order as items
        """
        if not items:
            return []
        
        batch_size = batch_size or self.max_workers
        results = [None] * len(items)
        completed = 0
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_indices = list(range(i, min(i + batch_size, len(items))))
            
            # Process batch concurrently
            tasks = [func(item) for item in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Store results
            for idx, result in zip(batch_indices, batch_results):
                if isinstance(result, Exception):
                    self.logger.warning(f"Task {idx} failed: {result}")
                    results[idx] = None
                else:
                    results[idx] = result
            
            completed += len(batch)
            if progress_callback:
                progress_callback(completed, len(items))
        
        return results
    
    async def map_threaded(
        self,
        func: Callable[[T], R],
        items: List[T],
        batch_size: int = None
    ) -> List[R]:
        """
        Apply CPU-bound function to items using thread pool.
        
        Args:
            func: Sync function to apply
            items: List of items to process
            batch_size: Items per batch
            
        Returns:
            List of results
        """
        if not items:
            return []
        
        loop = asyncio.get_event_loop()
        
        async def run_in_thread(item):
            return await loop.run_in_executor(self._thread_pool, func, item)
        
        return await self.map_async(run_in_thread, items, batch_size)
    
    async def process_batches(
        self,
        items: List[T],
        batch_processor: Callable[[List[T]], List[R]],
        batch_size: int = None,
        progress_callback: Callable[[int, int, str], None] = None
    ) -> BatchResult:
        """
        Process items in batches with a batch processor function.
        
        Args:
            items: Items to process
            batch_processor: Async function that processes a batch
            batch_size: Size of each batch
            progress_callback: Optional callback(completed, total, message)
            
        Returns:
            BatchResult with successful and failed items
        """
        if not items:
            return BatchResult([], [], 0.0, 0.0)
        
        batch_size = batch_size or settings.INGESTION_BATCH_SIZE
        successful = []
        failed = []
        start_time = time.time()
        
        total_batches = (len(items) + batch_size - 1) // batch_size
        
        for batch_idx, i in enumerate(range(0, len(items), batch_size)):
            batch = items[i:i + batch_size]
            batch_num = batch_idx + 1
            
            if progress_callback:
                progress_callback(
                    i, len(items), 
                    f"Processing batch {batch_num}/{total_batches}"
                )
            
            try:
                if asyncio.iscoroutinefunction(batch_processor):
                    results = await batch_processor(batch)
                else:
                    results = await asyncio.to_thread(batch_processor, batch)
                successful.extend(results)
            except Exception as e:
                self.logger.error(f"Batch {batch_num} failed: {e}")
                for item in batch:
                    failed.append((item, e))
        
        total_time = time.time() - start_time
        items_per_second = len(items) / total_time if total_time > 0 else 0
        
        return BatchResult(
            successful=successful,
            failed=failed,
            total_time=total_time,
            items_per_second=items_per_second
        )
    
    def shutdown(self):
        """Shutdown the thread pool."""
        self._thread_pool.shutdown(wait=True)


class AsyncSemaphore:
    """
    Rate-limited semaphore for controlling concurrent operations.
    Useful for API rate limiting.
    """
    
    def __init__(self, max_concurrent: int, rate_limit: float = None):
        """
        Args:
            max_concurrent: Maximum concurrent operations
            rate_limit: Minimum seconds between operations (optional)
        """
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._rate_limit = rate_limit
        self._last_acquire = 0.0
    
    async def acquire(self):
        """Acquire the semaphore with optional rate limiting."""
        await self._semaphore.acquire()
        
        if self._rate_limit:
            now = time.time()
            elapsed = now - self._last_acquire
            if elapsed < self._rate_limit:
                await asyncio.sleep(self._rate_limit - elapsed)
            self._last_acquire = time.time()
    
    def release(self):
        """Release the semaphore."""
        self._semaphore.release()
    
    async def __aenter__(self):
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.release()


async def parallel_embed(
    texts: List[str],
    embedding_func: Callable[[List[str]], List[Any]],
    batch_size: int = None,
    max_concurrent: int = None
) -> List[Any]:
    """
    Generate embeddings in parallel batches.
    
    Args:
        texts: Texts to embed
        embedding_func: Async function to generate embeddings
        batch_size: Texts per batch
        max_concurrent: Maximum concurrent batches
        
    Returns:
        List of embeddings
    """
    batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE
    max_concurrent = max_concurrent or settings.MAX_PARALLEL_EMBEDDINGS
    
    semaphore = AsyncSemaphore(max_concurrent)
    results = [None] * len(texts)
    
    async def process_batch(start_idx: int, batch: List[str]):
        async with semaphore:
            embeddings = await embedding_func(batch)
            for i, emb in enumerate(embeddings):
                results[start_idx + i] = emb
    
    tasks = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        tasks.append(process_batch(i, batch))
    
    await asyncio.gather(*tasks)
    return results


# Global processor instance
_processor: Optional[ParallelProcessor] = None


def get_parallel_processor() -> ParallelProcessor:
    """Get or create the global parallel processor."""
    global _processor
    if _processor is None:
        _processor = ParallelProcessor()
    return _processor
