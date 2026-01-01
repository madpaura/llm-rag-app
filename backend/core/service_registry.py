"""
Service registry for lazy loading and singleton management.
Improves startup time and memory usage for multi-user scenarios.
"""
import asyncio
from typing import Optional, Dict, Any, TypeVar, Generic, Callable
from functools import wraps
import structlog
from threading import Lock
import time

logger = structlog.get_logger()

T = TypeVar('T')


class LazyService(Generic[T]):
    """
    Lazy-loading wrapper for services.
    Service is only initialized when first accessed.
    """
    
    def __init__(self, factory: Callable[[], T], name: str = "service"):
        self._factory = factory
        self._instance: Optional[T] = None
        self._lock = Lock()
        self._name = name
        self._init_time: Optional[float] = None
    
    @property
    def instance(self) -> T:
        """Get or create the service instance."""
        if self._instance is None:
            with self._lock:
                if self._instance is None:
                    start = time.time()
                    logger.info(f"Initializing {self._name}...")
                    self._instance = self._factory()
                    self._init_time = time.time() - start
                    logger.info(f"{self._name} initialized in {self._init_time:.2f}s")
        return self._instance
    
    @property
    def is_initialized(self) -> bool:
        """Check if service has been initialized."""
        return self._instance is not None
    
    def reset(self) -> None:
        """Reset the service instance."""
        with self._lock:
            self._instance = None
            self._init_time = None


class ServiceRegistry:
    """
    Central registry for all application services.
    Provides lazy loading, singleton management, and health checks.
    """
    
    _instance: Optional['ServiceRegistry'] = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._services: Dict[str, LazyService] = {}
        self._startup_time: Optional[float] = None
        self._initialized = True
        self.logger = structlog.get_logger()
    
    def register(self, name: str, factory: Callable, lazy: bool = True) -> None:
        """
        Register a service with the registry.
        
        Args:
            name: Service name
            factory: Factory function to create the service
            lazy: If True, service is created on first access
        """
        if lazy:
            self._services[name] = LazyService(factory, name)
        else:
            # Initialize immediately
            self._services[name] = LazyService(factory, name)
            _ = self._services[name].instance
    
    def get(self, name: str) -> Any:
        """Get a service by name."""
        if name not in self._services:
            raise KeyError(f"Service '{name}' not registered")
        return self._services[name].instance
    
    def get_if_initialized(self, name: str) -> Optional[Any]:
        """Get a service only if it's already initialized."""
        if name not in self._services:
            return None
        service = self._services[name]
        return service._instance if service.is_initialized else None
    
    def is_initialized(self, name: str) -> bool:
        """Check if a service is initialized."""
        if name not in self._services:
            return False
        return self._services[name].is_initialized
    
    def reset(self, name: str) -> None:
        """Reset a specific service."""
        if name in self._services:
            self._services[name].reset()
    
    def reset_all(self) -> None:
        """Reset all services."""
        for service in self._services.values():
            service.reset()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about registered services."""
        stats = {
            "total_services": len(self._services),
            "initialized_services": sum(
                1 for s in self._services.values() if s.is_initialized
            ),
            "services": {}
        }
        
        for name, service in self._services.items():
            stats["services"][name] = {
                "initialized": service.is_initialized,
                "init_time": service._init_time
            }
        
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all initialized services."""
        results = {"healthy": True, "services": {}}
        
        for name, service in self._services.items():
            if not service.is_initialized:
                results["services"][name] = {"status": "not_initialized"}
                continue
            
            try:
                instance = service._instance
                if hasattr(instance, 'health_check'):
                    if asyncio.iscoroutinefunction(instance.health_check):
                        check = await instance.health_check()
                    else:
                        check = instance.health_check()
                    results["services"][name] = check
                else:
                    results["services"][name] = {"status": "ok"}
            except Exception as e:
                results["services"][name] = {"status": "error", "error": str(e)}
                results["healthy"] = False
        
        return results


# Global registry instance
_registry: Optional[ServiceRegistry] = None


def get_registry() -> ServiceRegistry:
    """Get the global service registry."""
    global _registry
    if _registry is None:
        _registry = ServiceRegistry()
    return _registry


def register_service(name: str, lazy: bool = True):
    """
    Decorator to register a service factory.
    
    Usage:
        @register_service("vector_service")
        def create_vector_service():
            return VectorService()
    """
    def decorator(factory: Callable):
        get_registry().register(name, factory, lazy=lazy)
        return factory
    return decorator


def get_service(name: str) -> Any:
    """Get a service from the global registry."""
    return get_registry().get(name)


# Pre-register core services
def _register_core_services():
    """Register core application services."""
    registry = get_registry()
    
    # Vector service (lazy - expensive to initialize)
    def create_vector_service():
        from services.vector_service import VectorService
        return VectorService()
    registry.register("vector_service", create_vector_service, lazy=True)
    
    # Ollama service (lazy - requires network)
    def create_ollama_service():
        from services.ollama_service import OllamaService
        return OllamaService()
    registry.register("ollama_service", create_ollama_service, lazy=True)
    
    # Embedding service (lazy - depends on ollama)
    def create_embedding_service():
        from services.vector_service import EmbeddingService
        return EmbeddingService()
    registry.register("embedding_service", create_embedding_service, lazy=True)
    
    # Ingestion orchestrator (lazy)
    def create_ingestion_orchestrator():
        from services.ingestion_service import IngestionOrchestrator
        return IngestionOrchestrator()
    registry.register("ingestion_orchestrator", create_ingestion_orchestrator, lazy=True)
    
    # Query service (lazy)
    def create_query_service():
        from services.query_service import QueryService
        return QueryService()
    registry.register("query_service", create_query_service, lazy=True)
    
    logger.info(f"Registered {len(registry._services)} core services")


# Initialize on import
_register_core_services()
