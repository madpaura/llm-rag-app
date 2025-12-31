"""
Main FastAPI application entry point for the RAG system.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import structlog
from contextlib import asynccontextmanager

from api.routes import auth, workspaces, ingestion, query, health, rag
from core.config import get_settings
from core.database import init_db
from core.logging import setup_logging

# Setup structured logging
setup_logging()
logger = structlog.get_logger()

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting RAG application...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    logger.info("Shutting down RAG application...")

# Create FastAPI app
app = FastAPI(
    title="Organization RAG API",
    description="""
## RAG-powered Knowledge Base API

This API provides Retrieval-Augmented Generation capabilities for developer onboarding and knowledge management.

### Features
- **Document Ingestion**: Upload documents, connect Git repos, or Confluence spaces
- **RAG Queries**: Ask questions and get AI-powered answers with citations
- **Multiple RAG Techniques**: Standard, RAG-Fusion, HyDE, Multi-Query
- **Workspace Management**: Organize knowledge bases by team or project
- **Chat Sessions**: Maintain conversation history with context

### Authentication
All endpoints (except health checks) require Bearer token authentication.
    """,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(workspaces.router, prefix="/api/workspaces", tags=["workspaces"])
app.include_router(ingestion.router, prefix="/api/ingestion", tags=["ingestion"])
app.include_router(query.router, prefix="/api/query", tags=["query"])
app.include_router(rag.router, prefix="/api/rag", tags=["rag-engine"])

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Organization RAG API",
        "version": "1.0.0",
        "status": "running"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
