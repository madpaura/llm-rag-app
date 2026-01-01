# RAG Application Architecture

A comprehensive Retrieval-Augmented Generation (RAG) system for developer onboarding and organizational knowledge management.

## Table of Contents

- [Goals](#goals)
- [System Overview](#system-overview)
- [Architecture Diagram](#architecture-diagram)
- [Component Details](#component-details)
- [Data Flow](#data-flow)
- [Technology Stack](#technology-stack)

---

## Goals

### Primary Objectives

1. **Developer Onboarding Acceleration**
   - Reduce time for new developers to become productive
   - Provide instant access to organizational knowledge
   - Enable natural language queries over codebases and documentation

2. **Knowledge Centralization**
   - Aggregate documentation from multiple sources (Git, Confluence, files)
   - Maintain up-to-date knowledge base with automatic syncing
   - Preserve context and relationships between documents

3. **Intelligent Code Understanding**
   - AST-based code parsing for semantic understanding
   - Automatic code summarization using LLMs
   - Call graph analysis for dependency tracking

4. **Flexible RAG Techniques**
   - Support multiple retrieval strategies for different use cases
   - Configurable chunking and embedding strategies
   - Workspace isolation for multi-tenant deployments

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐     │
│   │   React Web UI   │    │   REST API       │    │   CLI Tools      │     │
│   │   (Port 3000)    │    │   Clients        │    │                  │     │
│   └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘     │
│            │                       │                       │                │
└────────────┼───────────────────────┼───────────────────────┼────────────────┘
             │                       │                       │
             └───────────────────────┼───────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────────┐
│                           NGINX REVERSE PROXY                                │
│                              (Port 80/8080)                                  │
├────────────────────────────────────┼────────────────────────────────────────┤
│   /rag/ui  → Frontend              │                                        │
│   /rag/api → Backend API           │                                        │
│   /rag/api/docs → Swagger UI       │                                        │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────────┐
│                           APPLICATION LAYER                                  │
│                         FastAPI Backend (Port 8000)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│   │    Auth     │  │  Workspace  │  │  Ingestion  │  │    Query    │       │
│   │   Service   │  │   Service   │  │   Service   │  │   Service   │       │
│   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │
│                                                                              │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│   │    Code     │  │   Vector    │  │    LLM      │  │     RAG     │       │
│   │   Parser    │  │   Service   │  │   Service   │  │   Engine    │       │
│   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
             │                       │                       │
             ▼                       ▼                       ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│      SQLite         │  │    FAISS Vector     │  │      Ollama         │
│     Database        │  │       Store         │  │    LLM Server       │
│                     │  │                     │  │                     │
│  - Users            │  │  - Document         │  │  - Embeddings       │
│  - Workspaces       │  │    Embeddings       │  │    (nomic-embed)    │
│  - Documents        │  │  - Code Unit        │  │  - Generation       │
│  - Code Units       │  │    Embeddings       │  │    (llama/mistral)  │
│  - Chat Sessions    │  │  - Metadata Index   │  │                     │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

---

## Architecture Diagram

### High-Level Request Flow

```
┌──────────┐     ┌─────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  User    │────▶│  Nginx  │────▶│  FastAPI │────▶│  Service │────▶│  Storage │
│  Request │     │  Proxy  │     │  Router  │     │  Layer   │     │  Layer   │
└──────────┘     └─────────┘     └──────────┘     └──────────┘     └──────────┘
                                                        │
                                                        ▼
                                                 ┌──────────┐
                                                 │  Ollama  │
                                                 │   LLM    │
                                                 └──────────┘
```

### Ingestion Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INGESTION PIPELINE                                 │
└─────────────────────────────────────────────────────────────────────────────┘

     ┌─────────┐      ┌─────────┐      ┌─────────┐
     │   Git   │      │  Files  │      │Confluence│
     │  Repos  │      │ Upload  │      │   Wiki   │
     └────┬────┘      └────┬────┘      └────┬────┘
          │                │                │
          └────────────────┼────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │    Source Detection    │
              │  (Language/File Type)  │
              └───────────┬────────────┘
                          │
            ┌─────────────┴─────────────┐
            │                           │
            ▼                           ▼
   ┌─────────────────┐        ┌─────────────────┐
   │  Code Pipeline  │        │  Doc Pipeline   │
   │  (C/C++, etc.)  │        │  (MD, PDF, etc.)│
   └────────┬────────┘        └────────┬────────┘
            │                          │
            ▼                          ▼
   ┌─────────────────┐        ┌─────────────────┐
   │   Tree-sitter   │        │    Text        │
   │   AST Parsing   │        │   Extraction   │
   └────────┬────────┘        └────────┬────────┘
            │                          │
            ▼                          ▼
   ┌─────────────────┐        ┌─────────────────┐
   │  Extract Units  │        │    Chunking    │
   │  (Func/Class)   │        │  (1000 chars)  │
   └────────┬────────┘        └────────┬────────┘
            │                          │
            ▼                          │
   ┌─────────────────┐                 │
   │  LLM Summary    │                 │
   │   Generation    │                 │
   └────────┬────────┘                 │
            │                          │
            └──────────┬───────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │    Embedding    │
              │   Generation    │
              │ (nomic-embed)   │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  Vector Store   │
              │    (FAISS)      │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │   Database      │
              │   (SQLite)      │
              └─────────────────┘
```

### Query Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             QUERY PIPELINE                                   │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │   User Query    │
                    │  "How do I..."  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  RAG Technique  │
                    │   Selection     │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│    Standard     │ │   RAG-Fusion    │ │      HyDE       │
│      RAG        │ │                 │ │                 │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         │          ┌────────┴────────┐          │
         │          │  Multi-Query    │          │
         │          │  Generation     │          │
         │          └────────┬────────┘          │
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    Embedding    │
                    │   (Query/Doc)   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Vector Search  │
                    │    (FAISS)      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    Reranking    │
                    │  (Optional RRF) │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Context Assembly│
                    │  + Prompt Build │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  LLM Generation │
                    │    (Ollama)     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    Response     │
                    │  + Citations    │
                    └─────────────────┘
```

---

## Component Details

### 1. Authentication Service

- JWT-based token authentication
- User registration and login
- Token refresh mechanism
- Role-based access control (admin, member)

### 2. Workspace Service

- Multi-tenant workspace isolation
- Workspace membership management
- Per-workspace vector stores
- Access control enforcement

### 3. Ingestion Service

Handles multiple data sources:

| Source Type | Description | Supported Formats |
|-------------|-------------|-------------------|
| **Git** | Clone and parse repositories | All supported file types |
| **Files** | Direct file upload | PDF, MD, TXT, DOCX, Code files |
| **Confluence** | Wiki page import | HTML → Markdown conversion |
| **Code Directory** | Local code ingestion | C, C++, Python, JS, etc. |

### 4. Code Parser Service

- **Tree-sitter** based AST parsing
- Extracts: Functions, Classes, Structs, Methods
- Builds call graphs for dependency analysis
- Generates hierarchical summaries (function → class → file)

### 5. Vector Service

- **FAISS** for efficient similarity search
- Workspace-isolated collections
- Metadata filtering support
- Configurable retrieval strategies (similarity, MMR)

### 6. LLM Service (Ollama)

- Local LLM inference
- Embedding generation (nomic-embed-text)
- Text generation (configurable model)
- Streaming response support

### 7. RAG Engine

Implements multiple retrieval techniques:

| Technique | Description | Best For |
|-----------|-------------|----------|
| **Standard** | Direct query → retrieve → generate | Simple, direct questions |
| **RAG-Fusion** | Multi-query with RRF reranking | Complex queries |
| **HyDE** | Hypothetical document generation | Conceptual questions |
| **Multi-Query** | Query decomposition | Multi-part questions |

---

## Data Flow

### Document Ingestion Flow

```
1. User uploads document / provides Git URL
2. System detects file type and language
3. For code files:
   a. Parse with tree-sitter
   b. Extract code units (functions, classes)
   c. Generate LLM summaries for each unit
   d. Build call graph
4. For documents:
   a. Extract text content
   b. Split into chunks (1000 chars, 200 overlap)
5. Generate embeddings for all chunks
6. Store in FAISS vector index
7. Save metadata to SQLite database
```

### Query Processing Flow

```
1. User submits question
2. Select RAG technique based on query type
3. Process query through selected technique:
   - Standard: Direct embedding
   - RAG-Fusion: Generate query variations
   - HyDE: Generate hypothetical answer
   - Multi-Query: Decompose into sub-questions
4. Search vector store for relevant chunks
5. Apply reranking if needed (RRF for fusion)
6. Assemble context from top-k results
7. Build prompt with context + question
8. Generate response with LLM
9. Return answer with source citations
```

---

## Technology Stack

### Backend
- **FastAPI** - Async Python web framework
- **SQLAlchemy** - ORM for database operations
- **Pydantic** - Data validation
- **structlog** - Structured logging

### Frontend
- **React** - UI framework
- **TypeScript** - Type-safe JavaScript
- **TailwindCSS** - Styling
- **Axios** - HTTP client

### AI/ML
- **Ollama** - Local LLM inference
- **FAISS** - Vector similarity search
- **Tree-sitter** - Code parsing
- **LangChain** - LLM orchestration

### Infrastructure
- **Nginx** - Reverse proxy
- **SQLite** - Metadata database
- **Docker** (optional) - Containerization

---

## Directory Structure

```
llm-rag-app/
├── backend/
│   ├── api/
│   │   ├── routes/          # API endpoints
│   │   └── schemas/         # Pydantic models
│   ├── core/
│   │   ├── config.py        # Configuration
│   │   ├── database.py      # DB models
│   │   └── logging.py       # Logging setup
│   ├── services/
│   │   ├── code_parser_service.py
│   │   ├── code_ingestion_service.py
│   │   ├── vector_service.py
│   │   ├── ollama_service.py
│   │   └── rag_engine.py
│   └── main.py              # FastAPI app
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── contexts/        # React contexts
│   │   ├── hooks/           # Custom hooks
│   │   └── services/        # API client
│   └── public/
├── nginx/
│   ├── rag-app.conf         # Nginx config
│   ├── rag-locations.conf   # Location blocks
│   └── setup-nginx.sh       # Setup script
├── rag/
│   └── PRD.md               # Product requirements
└── docs/                    # Documentation
```

---

## Security Considerations

1. **Authentication**: JWT tokens with expiration
2. **Authorization**: Workspace-level access control
3. **Input Validation**: Pydantic schema validation
4. **CORS**: Configurable allowed origins
5. **Rate Limiting**: Recommended for production
6. **Secrets**: Environment variables for sensitive config

---

## Scalability Notes

- **Horizontal Scaling**: Stateless API design allows multiple instances
- **Vector Store**: FAISS can be replaced with distributed solutions (Milvus, Pinecone)
- **Database**: SQLite can be migrated to PostgreSQL for production
- **LLM**: Ollama can be replaced with cloud providers (OpenAI, Anthropic)

---

## Next Steps

See [FEATURES.md](./FEATURES.md) for detailed feature documentation and [USAGE_GUIDE.md](./USAGE_GUIDE.md) for integration and user guides.
