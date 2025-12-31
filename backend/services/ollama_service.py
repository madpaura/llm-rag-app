"""
Unified Ollama service for LLM and embeddings management.
"""
import httpx
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import structlog

from langchain_ollama import OllamaLLM, OllamaEmbeddings
from core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class OllamaModel:
    """Ollama model information."""
    name: str
    size: int
    modified_at: str
    digest: str


class OllamaService:
    """
    Unified service for Ollama LLM and embeddings.
    Provides health checks, model management, and instance creation.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        llm_model: Optional[str] = None,
        embedding_model: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.llm_model = llm_model or settings.OLLAMA_LLM_MODEL
        self.embedding_model = embedding_model or settings.OLLAMA_EMBEDDING_MODEL
        self.timeout = timeout or settings.OLLAMA_TIMEOUT
        
        self._llm: Optional[OllamaLLM] = None
        self._embeddings: Optional[OllamaEmbeddings] = None
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check if Ollama service is available and responsive.
        
        Returns:
            Dictionary with health status and available models
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    
                    return {
                        "status": "healthy",
                        "available": True,
                        "base_url": self.base_url,
                        "models": models,
                        "llm_model_available": self.llm_model in models,
                        "embedding_model_available": self.embedding_model in models
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "available": False,
                        "error": f"HTTP {response.status_code}"
                    }
                    
        except httpx.ConnectError:
            return {
                "status": "unavailable",
                "available": False,
                "error": f"Cannot connect to Ollama at {self.base_url}"
            }
        except Exception as e:
            logger.error("Ollama health check failed", error=str(e))
            return {
                "status": "error",
                "available": False,
                "error": str(e)
            }
    
    async def list_models(self) -> List[OllamaModel]:
        """
        List all available Ollama models.
        
        Returns:
            List of OllamaModel objects
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                
                if response.status_code == 200:
                    data = response.json()
                    return [
                        OllamaModel(
                            name=m.get("name", ""),
                            size=m.get("size", 0),
                            modified_at=m.get("modified_at", ""),
                            digest=m.get("digest", "")
                        )
                        for m in data.get("models", [])
                    ]
                return []
                
        except Exception as e:
            logger.error("Failed to list Ollama models", error=str(e))
            return []
    
    async def pull_model(self, model_name: str) -> bool:
        """
        Pull a model from Ollama registry.
        
        Args:
            model_name: Name of the model to pull
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=600.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/pull",
                    json={"name": model_name},
                    timeout=600.0
                )
                return response.status_code == 200
                
        except Exception as e:
            logger.error("Failed to pull Ollama model", model=model_name, error=str(e))
            return False
    
    def get_llm(
        self,
        model: Optional[str] = None,
        temperature: float = 0.0,
        **kwargs
    ) -> OllamaLLM:
        """
        Get or create an Ollama LLM instance.
        
        Args:
            model: Model name (defaults to configured model)
            temperature: Temperature for generation
            **kwargs: Additional arguments for OllamaLLM
            
        Returns:
            OllamaLLM instance
        """
        model = model or self.llm_model
        
        return OllamaLLM(
            model=model,
            base_url=self.base_url,
            temperature=temperature,
            **kwargs
        )
    
    def get_embeddings(
        self,
        model: Optional[str] = None,
        **kwargs
    ) -> OllamaEmbeddings:
        """
        Get or create an Ollama embeddings instance.
        
        Args:
            model: Embedding model name (defaults to configured model)
            **kwargs: Additional arguments for OllamaEmbeddings
            
        Returns:
            OllamaEmbeddings instance
        """
        model = model or self.embedding_model
        
        return OllamaEmbeddings(
            model=model,
            base_url=self.base_url,
            **kwargs
        )
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate text using Ollama.
        
        Args:
            prompt: Input prompt
            model: Model to use
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Dictionary with response and metadata
        """
        try:
            llm = self.get_llm(model=model, temperature=temperature)
            
            response = await asyncio.to_thread(llm.invoke, prompt)
            
            return {
                "success": True,
                "content": response,
                "model": model or self.llm_model
            }
            
        except Exception as e:
            logger.error("Ollama generation failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "content": ""
            }
    
    async def embed_texts(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate embeddings for texts.
        
        Args:
            texts: List of texts to embed
            model: Embedding model to use
            
        Returns:
            Dictionary with embeddings and metadata
        """
        try:
            embeddings = self.get_embeddings(model=model)
            
            vectors = await asyncio.to_thread(embeddings.embed_documents, texts)
            
            return {
                "success": True,
                "embeddings": vectors,
                "model": model or self.embedding_model,
                "count": len(vectors)
            }
            
        except Exception as e:
            logger.error("Ollama embedding failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "embeddings": []
            }
    
    async def embed_query(
        self,
        text: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate embedding for a single query text.
        
        Args:
            text: Text to embed
            model: Embedding model to use
            
        Returns:
            Dictionary with embedding and metadata
        """
        try:
            embeddings = self.get_embeddings(model=model)
            
            vector = await asyncio.to_thread(embeddings.embed_query, text)
            
            return {
                "success": True,
                "embedding": vector,
                "model": model or self.embedding_model
            }
            
        except Exception as e:
            logger.error("Ollama query embedding failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "embedding": []
            }


# Singleton instance
_ollama_service: Optional[OllamaService] = None


def get_ollama_service() -> OllamaService:
    """Get or create the singleton Ollama service instance."""
    global _ollama_service
    if _ollama_service is None:
        _ollama_service = OllamaService()
    return _ollama_service
