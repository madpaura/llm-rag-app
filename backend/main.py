"""
Main FastAPI application entry point for the RAG system.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import HTMLResponse
import structlog
from contextlib import asynccontextmanager

from api.routes import auth, workspaces, ingestion, query, health, rag, admin, embeddings
from core.config import get_settings
from core.database import init_db, check_db_connectivity, ensure_admin_user
from core.logging import setup_logging
from core.cache import cleanup_caches

# Setup structured logging
setup_logging()
logger = structlog.get_logger()

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with optimized startup."""
    import time
    start_time = time.time()
    
    logger.info("Starting RAG application...")
    
    # Step 1: Check database connectivity
    logger.info("Checking database connectivity...")
    db_status = check_db_connectivity()
    if not db_status["connected"]:
        logger.error(f"Database connection failed: {db_status['error']}")
        logger.error("Please check your DATABASE_URL in .env file")
        # Continue anyway - tables creation might fix it
    else:
        logger.info("Database connection successful")
    
    # Step 2: Initialize database tables
    await init_db()
    logger.info("Database tables initialized")
    
    # Step 3: Ensure admin user exists
    admin_result = ensure_admin_user()
    if admin_result.get("created"):
        logger.info(f"Created default admin user: {admin_result['username']}")
    elif admin_result.get("error"):
        logger.warning(f"Could not ensure admin user: {admin_result['error']}")
    else:
        logger.info(f"Admin user exists: {admin_result.get('username', 'unknown')}")
    
    # Note: Heavy services (vector store, embeddings) are lazy-loaded
    # They will be initialized on first use, not at startup
    
    startup_time = time.time() - start_time
    logger.info(f"Application started in {startup_time:.2f}s (services lazy-loaded)")
    
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down RAG application...")
    await cleanup_caches()
    logger.info("Caches cleaned up")

# API root path configuration (for nginx proxy)
# When behind nginx at /rag/api, the root_path tells Swagger UI the correct base URL
import os
ROOT_PATH = os.environ.get("ROOT_PATH", "/rag/api")

# Create FastAPI app
app = FastAPI(
    title="Organization RAG API",
    description="""
# RAG-powered Knowledge Base API

A comprehensive Retrieval-Augmented Generation (RAG) system for developer onboarding and organizational knowledge management.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
│                    http://localhost/rag/ui                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Nginx Reverse Proxy                        │
│                 /rag/ui → Frontend, /rag/api → Backend          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (This API)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │   Auth   │  │Workspace │  │Ingestion │  │   RAG Query      │ │
│  │  Service │  │ Service  │  │ Service  │  │   Service        │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            ▼                   ▼                   ▼
    ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
    │   SQLite     │   │    FAISS     │   │   Ollama     │
    │   Database   │   │ Vector Store │   │  LLM/Embed   │
    └──────────────┘   └──────────────┘   └──────────────┘
```

---

## 🚀 Quick Start Workflow

### Step 1: Authentication
```bash
# Register a new user
POST /api/auth/register
{
  "email": "user@example.com",
  "username": "developer",
  "password": "securepassword"
}

# Login to get access token
POST /api/auth/login
{
  "email": "user@example.com",
  "password": "securepassword"
}
# Response: { "access_token": "eyJ...", "token_type": "bearer" }
```

### Step 2: Create a Workspace
```bash
# Create workspace for your project/team
POST /api/workspaces/
Authorization: Bearer <token>
{
  "name": "my-project",
  "description": "Documentation for my project"
}
# Response: { "id": 1, "name": "my-project", ... }
```

### Step 3: Ingest Documents
```bash
# Option A: Ingest from Git repository
POST /api/ingestion/git
Authorization: Bearer <token>
{
  "workspace_id": 1,
  "name": "project-docs",
  "repo_url": "https://github.com/org/repo.git",
  "branch": "main"
}

# Option B: Upload files directly
POST /api/ingestion/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data
# Files: document.pdf, readme.md, etc.
```

### Step 4: Query Your Knowledge Base
```bash
# Ask questions about your documents
POST /api/query/chat/message
Authorization: Bearer <token>
{
  "workspace_id": 1,
  "session_id": 1,
  "message": "How do I set up the development environment?",
  "rag_technique": "standard"
}
```

---

## 📚 RAG Techniques Explained

### 1. **Standard RAG** (`standard`)
The classic retrieve-then-generate approach.

```
Query → Embed → Vector Search → Top-K Documents → LLM → Answer
```

**Best for**: Simple, direct questions with clear answers in the documents.

### 2. **RAG-Fusion** (`rag_fusion`)
Generates multiple query variations and combines results using Reciprocal Rank Fusion.

```
Query → Generate 3-5 Query Variations → 
  ├── Variation 1 → Vector Search → Results 1
  ├── Variation 2 → Vector Search → Results 2
  └── Variation 3 → Vector Search → Results 3
      ↓
  Reciprocal Rank Fusion (RRF) → Merged Results → LLM → Answer
```

**Best for**: Complex queries that might be phrased differently in the source documents.

### 3. **HyDE (Hypothetical Document Embeddings)** (`hyde`)
Generates a hypothetical answer first, then searches for similar real documents.

```
Query → LLM generates hypothetical answer → 
  Embed hypothetical answer → Vector Search → 
  Real documents similar to hypothesis → LLM → Final Answer
```

**Best for**: Questions where the answer style is predictable but exact wording varies.

### 4. **Multi-Query** (`multi_query`)
Breaks complex questions into sub-questions, retrieves for each, then synthesizes.

```
Complex Query → LLM decomposes into sub-questions →
  ├── Sub-Q1 → Retrieve → Context 1
  ├── Sub-Q2 → Retrieve → Context 2
  └── Sub-Q3 → Retrieve → Context 3
      ↓
  Combined Context → LLM → Comprehensive Answer
```

**Best for**: Multi-part questions requiring information from different document sections.

---

## 🔄 Embedding & Indexing Process

### Document Processing Pipeline

```
Source (Git/Files/Confluence)
        │
        ▼
┌───────────────────┐
│  1. EXTRACTION    │  Parse files: .py, .md, .txt, .pdf, etc.
│     & PARSING     │  Extract text content and metadata
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  2. CHUNKING      │  Split into chunks (default: 1000 chars)
│                   │  Overlap: 200 chars for context continuity
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  3. EMBEDDING     │  Convert chunks to vectors using:
│                   │  - Ollama: nomic-embed-text (768 dim)
│                   │  - OpenAI: text-embedding-ada-002
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  4. INDEXING      │  Store in FAISS vector database
│                   │  Enables fast similarity search
└───────────────────┘
```

### Supported File Types
- **Code**: `.py`, `.js`, `.ts`, `.java`, `.go`, `.rs`, `.cpp`, `.c`, `.h`
- **Documentation**: `.md`, `.rst`, `.txt`, `.pdf`, `.docx`
- **Config**: `.yaml`, `.yml`, `.json`, `.toml`

---

## 🔐 Authentication

All API endpoints (except `/health/`) require Bearer token authentication:

```
Authorization: Bearer <your_access_token>
```

Tokens expire after 30 minutes by default. Use the `/api/auth/me` endpoint to verify your token.

---

## 📖 API Sections

- **Authentication**: User registration, login, and token management
- **Workspaces**: Create and manage knowledge base workspaces
- **Ingestion**: Import documents from Git, files, or Confluence
- **Query**: Chat with your knowledge base using RAG
- **RAG Engine**: Direct access to RAG pipeline components
- **Health**: Service health checks

---

## 🛠️ Configuration

Key environment variables:
- `OLLAMA_BASE_URL`: Ollama server URL (default: http://localhost:11434)
- `OLLAMA_LLM_MODEL`: LLM model for generation (default: gpt-oss:20b-cloud)
- `OLLAMA_EMBEDDING_MODEL`: Embedding model (default: nomic-embed-text)
- `CHUNK_SIZE`: Document chunk size (default: 1000)
- `CHUNK_OVERLAP`: Chunk overlap (default: 200)

    """,
    version="1.0.0",
    root_path=ROOT_PATH,
    docs_url=None,  # Disable default docs, we'll add custom styled ones
    redoc_url=None,
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Custom Swagger UI with professional styling
SWAGGER_UI_CSS = """
    body { background: #fafafa; }
    .swagger-ui .topbar { display: none; }
    .swagger-ui .info { margin: 30px 0; }
    .swagger-ui .info .title { color: #2c3e50; font-size: 2.5em; }
    .swagger-ui .info .description { font-size: 14px; line-height: 1.6; }
    .swagger-ui .info .description h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
    .swagger-ui .info .description h2 { color: #34495e; margin-top: 25px; }
    .swagger-ui .info .description h3 { color: #7f8c8d; }
    .swagger-ui .info .description pre { background: #2d3748; color: #e2e8f0; border-radius: 4px; padding: 2px; }
    .swagger-ui .info .description code { background: #edf2f7; color: #61cf68; padding: 2px 6px; border-radius: 4px; }
    .swagger-ui .opblock-tag { color: #2c3e50; font-size: 1.2em; border-bottom: 1px solid #ecf0f1; }
    .swagger-ui .opblock.opblock-get { background: rgba(97, 175, 254, 0.1); border-color: #61affe; }
    .swagger-ui .opblock.opblock-post { background: rgba(73, 204, 144, 0.1); border-color: #49cc90; }
    .swagger-ui .opblock.opblock-put { background: rgba(252, 161, 48, 0.1); border-color: #fca130; }
    .swagger-ui .opblock.opblock-delete { background: rgba(249, 62, 62, 0.1); border-color: #f93e3e; }
    .swagger-ui .btn.execute { background: #3498db; border-color: #3498db; }
    .swagger-ui .btn.execute:hover { background: #2980b9; }
    .swagger-ui section.models { border: 1px solid #ecf0f1; border-radius: 8px; }
    .swagger-ui section.models h4 { color: #2c3e50; }
"""

@app.get("/api/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{app.title} - API Documentation</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
        <style>{SWAGGER_UI_CSS}</style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
        <script>
            window.onload = function() {{
                SwaggerUIBundle({{
                    url: "{ROOT_PATH}/api/openapi.json",
                    dom_id: '#swagger-ui',
                    presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
                    layout: "BaseLayout",
                    docExpansion: "none",
                    filter: true,
                    tryItOutEnabled: true,
                    syntaxHighlight: {{ theme: "agate" }}
                }});
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# Custom ReDoc with better styling  
@app.get("/api/redoc", include_in_schema=False)
async def custom_redoc_html():
    return get_redoc_html(
        openapi_url=f"{ROOT_PATH}/api/openapi.json",
        title=f"{app.title} - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@latest/bundles/redoc.standalone.js",
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
app.include_router(embeddings.router, prefix="/api/embeddings", tags=["embeddings"])
app.include_router(query.router, prefix="/api/query", tags=["query"])
app.include_router(rag.router, prefix="/api/rag", tags=["rag-engine"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

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
