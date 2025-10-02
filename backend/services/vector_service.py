"""
Vector database service for embeddings and similarity search.
"""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import pickle
import os
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
                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")
            else:
                self.index = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine similarity
                logger.info("Created new FAISS index")
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
    """Service for generating embeddings."""
    
    def __init__(self):
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the embedding model."""
        try:
            self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
            logger.info(f"Loaded embedding model: {settings.EMBEDDING_MODEL}")
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            raise
    
    async def encode(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for texts."""
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return [emb for emb in embeddings]
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return []
    
    async def encode_single(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        try:
            embedding = self.model.encode([text], convert_to_numpy=True)
            return embedding[0]
        except Exception as e:
            logger.error(f"Error generating single embedding: {e}")
            return np.array([])

class VectorService:
    """Main vector service combining embedding and storage."""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = self._create_vector_store()
    
    def _create_vector_store(self) -> VectorStore:
        """Create vector store based on configuration."""
        if settings.VECTOR_DB_TYPE == "faiss":
            return FAISSVectorStore(settings.FAISS_INDEX_PATH)
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
            metadata = [{k: v for k, v in doc.items() if k != 'content'} for doc in documents]
            
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
