"""
Pydantic schemas for RAG API endpoints.
"""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class RAGConfigSchema(BaseModel):
    """Schema for RAG engine configuration."""
    # LLM Configuration
    llm_model: str = Field(default="llama3.2:3b", description="LLM model name")
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0, description="LLM temperature")
    llm_base_url: Optional[str] = Field(default=None, description="Custom LLM base URL")
    
    # Embedding Configuration
    embedding_model: str = Field(default="nomic-embed-text", description="Embedding model name")
    embedding_strategy: Literal["ollama", "openai", "sentence_transformers"] = Field(
        default="ollama",
        description="Embedding strategy"
    )
    embedding_base_url: Optional[str] = Field(default=None, description="Custom embedding base URL")
    
    # Chunking Configuration
    chunk_size: int = Field(default=1000, ge=100, le=10000, description="Chunk size for text splitting")
    chunk_overlap: int = Field(default=200, ge=0, le=1000, description="Overlap between chunks")
    
    # Retrieval Configuration
    retrieval_strategy: Literal["similarity", "mmr", "similarity_score_threshold"] = Field(
        default="similarity",
        description="Retrieval strategy"
    )
    top_k: int = Field(default=4, ge=1, le=20, description="Number of documents to retrieve")
    score_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score threshold"
    )
    
    # RAG Technique
    rag_technique: Literal["standard", "rag_fusion", "hyde", "multi_query", "contextual_compression"] = Field(
        default="standard",
        description="RAG technique to use"
    )
    
    # Prompt Template
    prompt_template: Optional[str] = Field(
        default=None,
        description="Custom prompt template with {context} and {question} placeholders"
    )
    
    # Vector Store Configuration
    vector_store_type: Literal["chroma", "faiss"] = Field(
        default="chroma",
        description="Vector store type"
    )
    persist_directory: Optional[str] = Field(
        default=None,
        description="Directory to persist vector store"
    )


class DocumentSchema(BaseModel):
    """Schema for a document."""
    content: str = Field(..., description="Document content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")


class IngestRequest(BaseModel):
    """Request schema for document ingestion."""
    documents: List[DocumentSchema] = Field(..., description="List of documents to ingest")
    collection_name: Optional[str] = Field(default=None, description="Collection name")
    config: Optional[RAGConfigSchema] = Field(default=None, description="Optional RAG configuration")


class IngestResponse(BaseModel):
    """Response schema for document ingestion."""
    status: str
    documents_ingested: int
    chunks_created: int
    collection_name: str
    message: str = "Documents ingested successfully"


class QueryRequest(BaseModel):
    """Request schema for RAG query."""
    question: str = Field(..., description="User question", min_length=1)
    config: Optional[RAGConfigSchema] = Field(default=None, description="Optional RAG configuration")
    collection_name: Optional[str] = Field(default=None, description="Collection name to query")


class SourceDocument(BaseModel):
    """Schema for source document in response."""
    content: str
    metadata: Dict[str, Any]


class QueryResponse(BaseModel):
    """Response schema for RAG query."""
    answer: str
    source_documents: List[SourceDocument]
    technique: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UpdateConfigRequest(BaseModel):
    """Request schema for updating RAG configuration."""
    config: RAGConfigSchema


class ConfigResponse(BaseModel):
    """Response schema for configuration operations."""
    status: str
    message: str
    config: RAGConfigSchema


class HealthCheckResponse(BaseModel):
    """Response schema for health check."""
    status: str
    llm_available: bool
    embedding_available: bool
    vector_store_initialized: bool


class ListModelsResponse(BaseModel):
    """Response schema for listing available models."""
    llm_models: List[str]
    embedding_models: List[str]


class PromptTemplateSchema(BaseModel):
    """Schema for prompt template."""
    name: str
    template: str
    description: Optional[str] = None
    variables: List[str] = Field(default_factory=lambda: ["context", "question"])


class ListPromptTemplatesResponse(BaseModel):
    """Response schema for listing prompt templates."""
    templates: List[PromptTemplateSchema]


class RAGTechniqueInfo(BaseModel):
    """Information about a RAG technique."""
    name: str
    description: str
    use_case: str


class ListTechniquesResponse(BaseModel):
    """Response schema for listing RAG techniques."""
    techniques: List[RAGTechniqueInfo]
