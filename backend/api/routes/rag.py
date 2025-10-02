"""
RAG API routes for the advanced RAG engine.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import structlog
import json
from pathlib import Path

from api.schemas.rag_schemas import (
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    UpdateConfigRequest,
    ConfigResponse,
    HealthCheckResponse,
    ListModelsResponse,
    ListPromptTemplatesResponse,
    ListTechniquesResponse,
    PromptTemplateSchema,
    RAGTechniqueInfo,
    SourceDocument
)
from services.rag_engine import RAGEngine, RAGConfig
from langchain_core.documents import Document

logger = structlog.get_logger()

router = APIRouter()

# Global RAG engine instance (in production, use dependency injection or session management)
_rag_engine: Dict[str, RAGEngine] = {}


def get_rag_engine(collection_name: str = "default") -> RAGEngine:
    """Get or create RAG engine instance for a collection."""
    if collection_name not in _rag_engine:
        _rag_engine[collection_name] = RAGEngine(RAGConfig())
    return _rag_engine[collection_name]


@router.post("/ingest", response_model=IngestResponse)
async def ingest_documents(request: IngestRequest):
    """
    Ingest documents into the RAG system.
    
    - **documents**: List of documents with content and metadata
    - **collection_name**: Optional collection name for organization
    - **config**: Optional RAG configuration
    """
    try:
        collection_name = request.collection_name or "default"
        
        # Create or get RAG engine
        if request.config:
            config = RAGConfig(**request.config.model_dump())
            engine = RAGEngine(config)
            _rag_engine[collection_name] = engine
        else:
            engine = get_rag_engine(collection_name)
        
        # Convert to LangChain documents
        documents = [
            Document(
                page_content=doc.content,
                metadata=doc.metadata
            )
            for doc in request.documents
        ]
        
        # Ingest documents
        result = await engine.ingest_documents(documents, collection_name)
        
        logger.info(
            "Documents ingested",
            collection=collection_name,
            count=result["documents_ingested"]
        )
        
        return IngestResponse(**result)
        
    except Exception as e:
        logger.error("Document ingestion failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """
    Query the RAG system.
    
    - **question**: User question
    - **collection_name**: Optional collection name to query
    - **config**: Optional RAG configuration for this query
    """
    try:
        collection_name = request.collection_name or "default"
        
        # Get or update RAG engine
        engine = get_rag_engine(collection_name)
        
        # Update config if provided
        if request.config:
            engine.update_config(**request.config.model_dump(exclude_none=True))
        
        # Query
        result = await engine.query(request.question)
        
        logger.info(
            "Query processed",
            collection=collection_name,
            technique=result["technique"],
            question_length=len(request.question)
        )
        
        # Convert to response schema
        return QueryResponse(
            answer=result["answer"],
            source_documents=[
                SourceDocument(**doc) for doc in result["source_documents"]
            ],
            technique=result["technique"],
            metadata={
                k: v for k, v in result.items()
                if k not in ["answer", "source_documents", "technique"]
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Query failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.put("/config", response_model=ConfigResponse)
async def update_config(request: UpdateConfigRequest, collection_name: str = "default"):
    """
    Update RAG engine configuration.
    
    - **config**: New RAG configuration
    - **collection_name**: Collection to update
    """
    try:
        engine = get_rag_engine(collection_name)
        engine.update_config(**request.config.model_dump(exclude_none=True))
        
        logger.info("Configuration updated", collection=collection_name)
        
        return ConfigResponse(
            status="success",
            message="Configuration updated successfully",
            config=request.config
        )
        
    except Exception as e:
        logger.error("Config update failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Config update failed: {str(e)}")


@router.get("/config", response_model=ConfigResponse)
async def get_config(collection_name: str = "default"):
    """
    Get current RAG engine configuration.
    
    - **collection_name**: Collection to get config from
    """
    try:
        engine = get_rag_engine(collection_name)
        
        from api.schemas.rag_schemas import RAGConfigSchema
        config_dict = {
            "llm_model": engine.config.llm_model,
            "llm_temperature": engine.config.llm_temperature,
            "llm_base_url": engine.config.llm_base_url,
            "embedding_model": engine.config.embedding_model,
            "embedding_strategy": engine.config.embedding_strategy.value,
            "embedding_base_url": engine.config.embedding_base_url,
            "chunk_size": engine.config.chunk_size,
            "chunk_overlap": engine.config.chunk_overlap,
            "retrieval_strategy": engine.config.retrieval_strategy.value,
            "top_k": engine.config.top_k,
            "score_threshold": engine.config.score_threshold,
            "rag_technique": engine.config.rag_technique.value,
            "prompt_template": engine.config.prompt_template,
            "vector_store_type": engine.config.vector_store_type,
            "persist_directory": engine.config.persist_directory,
        }
        
        return ConfigResponse(
            status="success",
            message="Configuration retrieved successfully",
            config=RAGConfigSchema(**config_dict)
        )
        
    except Exception as e:
        logger.error("Config retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Config retrieval failed: {str(e)}")


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(collection_name: str = "default"):
    """
    Check health of RAG engine.
    
    - **collection_name**: Collection to check
    """
    try:
        engine = get_rag_engine(collection_name)
        
        return HealthCheckResponse(
            status="healthy",
            llm_available=engine.llm is not None,
            embedding_available=engine.embeddings is not None,
            vector_store_initialized=engine.vectorstore is not None
        )
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthCheckResponse(
            status="unhealthy",
            llm_available=False,
            embedding_available=False,
            vector_store_initialized=False
        )


@router.get("/models", response_model=ListModelsResponse)
async def list_models():
    """
    List available LLM and embedding models.
    """
    return ListModelsResponse(
        llm_models=[
            "llama3.2:3b",
            "llama3.2:1b",
            "llama3.1:8b",
            "llama3.1:70b",
            "mistral:7b",
            "mixtral:8x7b",
            "phi3:mini",
            "gemma2:9b",
            "qwen2.5:7b",
            "deepseek-r1:7b",
            "gpt-oss:120b-cloud"
        ],
        embedding_models=[
            "nomic-embed-text",
            "mxbai-embed-large",
            "all-minilm",
            "text-embedding-ada-002",  # OpenAI
            "text-embedding-3-small",  # OpenAI
            "text-embedding-3-large",  # OpenAI
            "all-MiniLM-L6-v2",  # Sentence Transformers
            "all-mpnet-base-v2",  # Sentence Transformers
        ]
    )


@router.get("/prompt-templates", response_model=ListPromptTemplatesResponse)
async def list_prompt_templates():
    """
    List available prompt templates from config files.
    """
    try:
        # Get the path to the templates config file
        config_path = Path(__file__).parent.parent.parent / "config" / "templates" / "default.json"
        
        if not config_path.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Template configuration file not found at {config_path}"
            )
        
        # Load templates from JSON file
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        # Convert to PromptTemplateSchema objects
        templates = [
            PromptTemplateSchema(**template_data)
            for template_data in config_data.get("templates", [])
        ]
        
        logger.info("Prompt templates loaded", count=len(templates), source=str(config_path))
        
        return ListPromptTemplatesResponse(templates=templates)
        
    except json.JSONDecodeError as e:
        logger.error("Failed to parse template config", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Invalid JSON in template configuration: {str(e)}"
        )
    except Exception as e:
        logger.error("Failed to load prompt templates", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load templates: {str(e)}"
        )


@router.get("/techniques", response_model=ListTechniquesResponse)
async def list_techniques():
    """
    List available RAG techniques with descriptions.
    """
    techniques = [
        RAGTechniqueInfo(
            name="standard",
            description="Standard RAG: Direct retrieval and generation",
            use_case="General purpose Q&A with straightforward queries"
        ),
        RAGTechniqueInfo(
            name="rag_fusion",
            description="RAG-Fusion: Generates multiple query variations and fuses results",
            use_case="Complex queries that benefit from multiple perspectives"
        ),
        RAGTechniqueInfo(
            name="hyde",
            description="HyDE: Generates hypothetical document first, then retrieves",
            use_case="When query is vague or requires domain knowledge expansion"
        ),
        RAGTechniqueInfo(
            name="multi_query",
            description="Multi-Query: Generates multiple perspectives for better retrieval",
            use_case="Overcoming limitations of distance-based similarity search"
        ),
        RAGTechniqueInfo(
            name="contextual_compression",
            description="Contextual Compression: Compresses retrieved context for relevance",
            use_case="When dealing with large documents or reducing noise"
        )
    ]
    
    return ListTechniquesResponse(techniques=techniques)


@router.delete("/collection/{collection_name}")
async def delete_collection(collection_name: str):
    """
    Delete a collection and its RAG engine instance.
    
    - **collection_name**: Collection to delete
    """
    try:
        if collection_name in _rag_engine:
            del _rag_engine[collection_name]
            logger.info("Collection deleted", collection=collection_name)
            return {"status": "success", "message": f"Collection '{collection_name}' deleted"}
        else:
            raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Collection deletion failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")


@router.get("/collections")
async def list_collections():
    """
    List all active collections.
    """
    return {
        "collections": list(_rag_engine.keys()),
        "count": len(_rag_engine)
    }
