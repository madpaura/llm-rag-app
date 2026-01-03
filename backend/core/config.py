"""
Application configuration management.
"""
from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator
import os

class Settings(BaseSettings):
    """Application settings."""
    
    # App Configuration
    APP_NAME: str = "Organization RAG API"
    DEBUG: bool = True
    VERSION: str = "1.0.0"
    
    # Database - PostgreSQL recommended for production (better concurrency)
    # SQLite: sqlite:///./data/rag.db
    # PostgreSQL: postgresql://user:password@localhost:5432/rag_db
    DATABASE_URL: str = "postgresql://rag_user:rag_password@localhost:5432/rag_db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 1800  # Recycle connections after 30 minutes
    
    # Vector Database
    VECTOR_DB_TYPE: str = "faiss"  # faiss, pinecone, weaviate
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: Optional[str] = None
    WEAVIATE_URL: Optional[str] = None
    # FAISS indexes are now workspace-isolated: ./data/workspaces/{workspace_id}/faiss_index
    FAISS_BASE_PATH: str = "./data/workspaces"
    
    # LLM Configuration
    LLM_PROVIDER: str = "ollama"  # ollama, openai
    OPENAI_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-3.5-turbo"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 1000
    
    # Ollama Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_LLM_MODEL: str = "gpt-oss:20b-cloud"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    OLLAMA_TIMEOUT: int = 120
    
    # Groq Configuration
    GROQ_API_KEY: Optional[str] = None
    GROQ_URL: str = "https://api.groq.com/openai/v1"
    
    # Embedding Configuration
    EMBEDDING_PROVIDER: str = "ollama"  # ollama, openai, sentence_transformers
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    # RAG Configuration
    DEFAULT_RAG_TECHNIQUE: str = "standard"  # standard, rag_fusion, hyde, multi_query
    DEFAULT_RETRIEVAL_STRATEGY: str = "similarity"  # similarity, mmr, similarity_score_threshold
    DEFAULT_TOP_K: int = 4
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080", "http://localhost", "http://127.0.0.1"]
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1", "*"]
    
    # File Storage - Now workspace-isolated
    # Uploads: ./data/workspaces/{workspace_id}/uploads
    # Git repos: ./data/workspaces/{workspace_id}/git_repos
    DATA_BASE_DIR: str = "./data/workspaces"
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    # Git Integration
    GIT_TIMEOUT: int = 300  # 5 minutes
    
    # Confluence Integration
    CONFLUENCE_BASE_URL: Optional[str] = None
    CONFLUENCE_USERNAME: Optional[str] = None
    CONFLUENCE_API_TOKEN: Optional[str] = None
    
    # Monitoring
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    
    # Performance
    MAX_CONCURRENT_INGESTIONS: int = 5
    QUERY_TIMEOUT: int = 30
    
    # Caching
    EMBEDDING_CACHE_SIZE: int = 5000
    EMBEDDING_CACHE_TTL: int = 7200  # 2 hours
    QUERY_CACHE_SIZE: int = 500
    QUERY_CACHE_TTL: int = 1800  # 30 minutes
    
    # Batch Processing
    EMBEDDING_BATCH_SIZE: int = 32
    INGESTION_BATCH_SIZE: int = 50
    MAX_PARALLEL_EMBEDDINGS: int = 4
    
    # Backup
    BACKUP_DIR: str = "./data/backups"
    BACKUP_RETENTION_COUNT: int = 5
    AUTO_BACKUP_ENABLED: bool = False
    
    # Default Admin User (from .env)
    ADMIN_USERNAME: str = "admin"
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "admin123"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("ALLOWED_HOSTS", pre=True)
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
