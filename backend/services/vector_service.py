"""
Vector database service for embeddings and similarity search.
"""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import faiss
import pickle
import os
import asyncio
import structlog
from abc import ABC, abstractmethod

from core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

class VectorStore(ABC):
    """Abstract base class for vector stores."""
    
    @abstractmethod
    async def add_vectors(self, vectors: List[np.ndarray], metadata: List[Dict[str, Any]], ids: List[str]) -> bool:
        """Add vectors to the store."""
        pass
    
    @abstractmethod
    async def search(self, query_vector: np.ndarray, k: int = 5) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search for similar vectors."""
        pass
    
    @abstractmethod
    async def delete_vectors(self, ids: List[str]) -> bool:
        """Delete vectors by IDs."""
        pass

class FAISSVectorStore(VectorStore):
    """FAISS-based vector store implementation."""
    
    def __init__(self, index_path: str, dimension: int = 384):
        self.index_path = index_path
        self.dimension = dimension
        self.index = None
        self.metadata = {}
        self.id_to_index = {}
        self.index_to_id = {}
        self._load_index()
    
    def _load_index(self):
        """Load existing index or create new one."""
        try:
            if os.path.exists(f"{self.index_path}.index"):
                self.index = faiss.read_index(f"{self.index_path}.index")
                with open(f"{self.index_path}.metadata", 'rb') as f:
                    data = pickle.load(f)
                    self.metadata = data.get('metadata', {})
                    self.id_to_index = data.get('id_to_index', {})
                    self.index_to_id = data.get('index_to_id', {})
                
                # Check if dimension matches, recreate if not
                if self.index.d != self.dimension:
                    logger.warning(f"FAISS index dimension mismatch: index has {self.index.d}, expected {self.dimension}. Recreating index.")
                    self.index = faiss.IndexFlatIP(self.dimension)
                    self.metadata = {}
                    self.id_to_index = {}
                    self.index_to_id = {}
                    logger.info(f"Created new FAISS index with dimension {self.dimension}")
                else:
                    logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors (dim={self.index.d})")
            else:
                self.index = faiss.IndexFlatIP(self.dimension)
                logger.info(f"Created new FAISS index with dimension {self.dimension}")
        except Exception as e:
            logger.error(f"Error loading FAISS index: {e}")
            self.index = faiss.IndexFlatIP(self.dimension)
    
    def _save_index(self):
        """Save index and metadata to disk."""
        try:
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
            faiss.write_index(self.index, f"{self.index_path}.index")
            with open(f"{self.index_path}.metadata", 'wb') as f:
                pickle.dump({
                    'metadata': self.metadata,
                    'id_to_index': self.id_to_index,
                    'index_to_id': self.index_to_id
                }, f)
            logger.debug("Saved FAISS index")
        except Exception as e:
            logger.error(f"Error saving FAISS index: {e}")
    
    async def add_vectors(self, vectors: List[np.ndarray], metadata: List[Dict[str, Any]], ids: List[str]) -> bool:
        """Add vectors to FAISS index."""
        try:
            if len(vectors) != len(metadata) or len(vectors) != len(ids):
                raise ValueError("Vectors, metadata, and IDs must have same length")
            
            if len(vectors) == 0:
                logger.warning("No vectors to add")
                return True
            
            # Check vector dimension matches index
            vector_dim = vectors[0].shape[0]
            if vector_dim != self.dimension:
                logger.error(f"Vector dimension mismatch: vectors have dim {vector_dim}, index expects {self.dimension}")
                # Recreate index with correct dimension
                self.dimension = vector_dim
                self.index = faiss.IndexFlatIP(self.dimension)
                self.metadata = {}
                self.id_to_index = {}
                self.index_to_id = {}
                logger.info(f"Recreated FAISS index with dimension {self.dimension}")
            
            # Normalize vectors for cosine similarity
            vectors_array = np.array(vectors).astype('float32')
            faiss.normalize_L2(vectors_array)
            
            # Add to index
            start_idx = self.index.ntotal
            self.index.add(vectors_array)
            
            # Update mappings
            for i, vector_id in enumerate(ids):
                idx = start_idx + i
                self.id_to_index[vector_id] = idx
                self.index_to_id[idx] = vector_id
                self.metadata[vector_id] = metadata[i]
            
            self._save_index()
            logger.info(f"Added {len(vectors)} vectors to FAISS index")
            return True
            
        except Exception as e:
            logger.error(f"Error adding vectors to FAISS: {e}")
            return False
    
    async def search(self, query_vector: np.ndarray, k: int = 5) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search for similar vectors in FAISS index."""
        try:
            if self.index.ntotal == 0:
                return []
            
            # Normalize query vector
            query_vector = query_vector.reshape(1, -1).astype('float32')
            faiss.normalize_L2(query_vector)
            
            # Search
            scores, indices = self.index.search(query_vector, min(k, self.index.ntotal))
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx != -1 and idx in self.index_to_id:
                    vector_id = self.index_to_id[idx]
                    metadata = self.metadata.get(vector_id, {})
                    results.append((vector_id, float(score), metadata))
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching FAISS index: {e}")
            return []
    
    async def delete_vectors(self, ids: List[str]) -> bool:
        """Delete vectors by IDs (FAISS doesn't support deletion, so we mark as deleted)."""
        try:
            for vector_id in ids:
                if vector_id in self.metadata:
                    self.metadata[vector_id]['deleted'] = True
            
            self._save_index()
            logger.info(f"Marked {len(ids)} vectors as deleted")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting vectors: {e}")
            return False

class EmbeddingService:
    """
    Service for generating embeddings.
    Supports multiple providers: ollama, openai, sentence_transformers
    """
    
    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or settings.EMBEDDING_PROVIDER
        self.model = None
        self.ollama_embeddings = None
        self._dimension = 384  # Default dimension
        self._load_model()
    
    def _load_model(self):
        """Load the embedding model based on provider."""
        try:
            if self.provider == "ollama":
                from langchain_ollama import OllamaEmbeddings
                self.ollama_embeddings = OllamaEmbeddings(
                    model=settings.OLLAMA_EMBEDDING_MODEL,
                    base_url=settings.OLLAMA_BASE_URL
                )
                # Ollama nomic-embed-text produces 768-dim embeddings
                self._dimension = 768
                logger.info(f"Loaded Ollama embedding model: {settings.OLLAMA_EMBEDDING_MODEL}")
                
            elif self.provider == "openai":
                from langchain_openai import OpenAIEmbeddings
                self.ollama_embeddings = OpenAIEmbeddings()
                self._dimension = 1536  # OpenAI ada-002 dimension
                logger.info("Loaded OpenAI embedding model")
                
            elif self.provider == "sentence_transformers":
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
                self._dimension = self.model.get_sentence_embedding_dimension()
                logger.info(f"Loaded SentenceTransformer model: {settings.EMBEDDING_MODEL}")
                
            else:
                raise ValueError(f"Unsupported embedding provider: {self.provider}")
                
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            raise
    
    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        return self._dimension
    
    async def encode(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for texts."""
        try:
            if self.provider in ["ollama", "openai"]:
                # Use LangChain embeddings
                embeddings = await asyncio.to_thread(
                    self.ollama_embeddings.embed_documents, texts
                )
                return [np.array(emb, dtype=np.float32) for emb in embeddings]
            else:
                # Use SentenceTransformer
                embeddings = self.model.encode(texts, convert_to_numpy=True)
                return [emb.astype(np.float32) for emb in embeddings]
                
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return []
    
    async def encode_single(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        try:
            if self.provider in ["ollama", "openai"]:
                embedding = await asyncio.to_thread(
                    self.ollama_embeddings.embed_query, text
                )
                return np.array(embedding, dtype=np.float32)
            else:
                embedding = self.model.encode([text], convert_to_numpy=True)
                return embedding[0].astype(np.float32)
                
        except Exception as e:
            logger.error(f"Error generating single embedding: {e}")
            return np.array([])

class VectorService:
    """Main vector service combining embedding and storage."""
    
    def __init__(self, embedding_provider: Optional[str] = None):
        self.embedding_service = EmbeddingService(provider=embedding_provider)
        self.vector_store = self._create_vector_store()
    
    def _create_vector_store(self) -> VectorStore:
        """Create vector store based on configuration."""
        if settings.VECTOR_DB_TYPE == "faiss":
            return FAISSVectorStore(
                settings.FAISS_INDEX_PATH,
                dimension=self.embedding_service.dimension
            )
        else:
            raise ValueError(f"Unsupported vector DB type: {settings.VECTOR_DB_TYPE}")
    
    async def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """Add documents to vector store."""
        try:
            texts = [doc['content'] for doc in documents]
            embeddings = await self.embedding_service.encode(texts)
            
            if not embeddings:
                return False
            
            ids = [doc['id'] for doc in documents]
            # Include content in metadata so it can be retrieved during search
            metadata = [doc.copy() for doc in documents]
            
            return await self.vector_store.add_vectors(embeddings, metadata, ids)
            
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {e}")
            return False
    
    async def search_documents(self, query: str, k: int = 5, workspace_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search for relevant documents."""
        try:
            query_embedding = await self.embedding_service.encode_single(query)
            if query_embedding.size == 0:
                return []
            
            results = await self.vector_store.search(query_embedding, k)
            
            # Filter by workspace if specified
            filtered_results = []
            for vector_id, score, metadata in results:
                if metadata.get('deleted'):
                    continue
                
                if workspace_id is None or metadata.get('workspace_id') == workspace_id:
                    filtered_results.append({
                        'id': vector_id,
                        'score': score,
                        'content': metadata.get('content', ''),
                        'title': metadata.get('title', ''),
                        'source': metadata.get('source', ''),
                        'metadata': metadata
                    })
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
    
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """Delete documents from vector store."""
        return await self.vector_store.delete_vectors(document_ids)
