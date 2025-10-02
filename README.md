# Organization-Wide RAG Application

A production-ready Retrieval-Augmented Generation (RAG) application with advanced features including RAG-Fusion, HyDE, and multi-model support. Built with FastAPI, LangChain, and Ollama for flexible, high-performance document Q&A.

## 🚀 Quick Start

```bash
# Automated setup
cd backend
./setup.sh

# Start server
python main.py

# Visit API docs
open http://localhost:8000/docs
```

## Architecture Overview

### Advanced RAG Engine (NEW ✨)
- **Multiple LLM Support**: Ollama (Llama, Mistral, Phi, Gemma, etc.)
- **Flexible Embeddings**: Ollama, OpenAI, Sentence Transformers
- **Advanced Techniques**: RAG-Fusion, HyDE, Multi-Query, Contextual Compression
- **Configurable Retrieval**: Similarity, MMR, score threshold
- **Custom Prompts**: 5 built-in templates + custom support
- **Vector Stores**: Chroma, FAISS with persistence

### Backend Services
- **RAG Engine API**: Advanced RAG with technique selection (`/api/rag/*`)
- **Ingestion Service**: Git repos, Confluence, document processing
- **Vector Service**: Embeddings and vector database operations
- **Query Service**: Traditional RAG pipeline
- **Workspace Service**: Multi-tenant workspace management
- **Auth Service**: JWT-based authentication

### Frontend
- **React + TypeScript** application with modern UI
- **Tailwind CSS** for styling
- **Real-time Chat** interface
- **RAG Configuration** panel

### Databases
- **PostgreSQL**: Metadata, workspaces, users, audit logs
- **Vector Database**: Chroma, FAISS, Pinecone, or Weaviate

## Key Features

### 🎯 Advanced RAG Capabilities
- **RAG-Fusion**: Multi-query generation for complex questions
- **HyDE**: Hypothetical document embeddings for vague queries
- **Multi-Query**: Multiple perspective retrieval
- **Custom Prompts**: Domain-specific prompt templates
- **Dynamic Configuration**: Runtime model and parameter switching

### 📚 Data Ingestion
- Git repository cloning and parsing
- Confluence wiki integration
- PDF and Word document processing
- Configurable chunking (size, overlap)
- Multiple embedding strategies

### 💬 Query Interface
- Natural language chat interface
- Context-aware responses with citations
- Persistent chat history per workspace
- Follow-up question support
- Source document tracking

### 🏢 Workspace Management
- Project-isolated collections
- Role-based access control
- Data privacy and security
- Per-workspace configuration

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, LangChain, Ollama
- **Frontend**: React 18, TypeScript, Tailwind CSS
- **Databases**: PostgreSQL, Chroma/FAISS
- **LLM**: Ollama (Llama, Mistral, etc.) or OpenAI
- **Embeddings**: Ollama, OpenAI, Sentence Transformers
- **Deployment**: Docker, Docker Compose
- **Monitoring**: Structlog, Prometheus

## Available Models

### LLM Models (Ollama)
- llama3.2:3b, llama3.2:1b
- llama3.1:8b, llama3.1:70b
- mistral:7b, mixtral:8x7b
- phi3:mini, gemma2:9b
- qwen2.5:7b, deepseek-r1:7b

### Embedding Models
- nomic-embed-text (Ollama)
- mxbai-embed-large (Ollama)
- text-embedding-3-small (OpenAI)
- all-mpnet-base-v2 (Sentence Transformers)

## Project Structure

```
llm-rag-app/
├── backend/
│   ├── services/
│   │   └── rag_engine.py          # Advanced RAG engine
│   ├── api/
│   │   ├── routes/rag.py          # RAG API endpoints
│   │   └── schemas/rag_schemas.py # API schemas
│   ├── examples/
│   │   ├── rag_example.py         # Usage examples
│   │   └── api_client_example.py  # API client
│   ├── main.py                    # FastAPI app
│   ├── setup.sh                   # Automated setup
│   ├── RAG_ENGINE_README.md       # Full documentation
│   ├── QUICKSTART.md              # Quick start guide
│   └── requirements.txt           # Dependencies
├── frontend/                      # React application
├── INTEGRATION_GUIDE.md           # Integration guide
└── README.md                      # This file
```

## Getting Started

### Option 1: Automated Setup (Recommended)

```bash
cd backend
./setup.sh
```

### Option 2: Manual Setup

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull models
ollama pull llama3.2:3b
ollama pull nomic-embed-text

# 3. Install Python dependencies
cd backend
pip install -r requirements.txt

# 4. Start server
python main.py
```

### Quick Test

```bash
# Test with example script
python examples/api_client_example.py

# Or use curl
curl -X POST "http://localhost:8000/api/rag/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is Python?",
    "collection_name": "test"
  }'
```

## Documentation

- **📖 Full Documentation**: [`backend/RAG_ENGINE_README.md`](backend/RAG_ENGINE_README.md)
- **⚡ Quick Start**: [`backend/QUICKSTART.md`](backend/QUICKSTART.md)
- **🔧 Integration Guide**: [`INTEGRATION_GUIDE.md`](INTEGRATION_GUIDE.md)
- **📊 Project Summary**: [`backend/RAG_ENGINE_SUMMARY.md`](backend/RAG_ENGINE_SUMMARY.md)
- **📝 Project Context**: [`claude.md`](claude.md)
- **🌐 API Docs**: http://localhost:8000/docs (when running)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/rag/ingest` | POST | Ingest documents |
| `/api/rag/query` | POST | Query with RAG |
| `/api/rag/config` | GET/PUT | Manage configuration |
| `/api/rag/models` | GET | List available models |
| `/api/rag/techniques` | GET | List RAG techniques |
| `/api/rag/prompt-templates` | GET | List prompt templates |
| `/api/rag/collections` | GET | List collections |
| `/api/rag/health` | GET | Health check |

## Usage Examples

### Basic Query

```python
import requests

# Ingest documents
requests.post("http://localhost:8000/api/rag/ingest", json={
    "documents": [{"content": "Python is a programming language.", "metadata": {}}],
    "collection_name": "docs"
})

# Query
response = requests.post("http://localhost:8000/api/rag/query", json={
    "question": "What is Python?",
    "collection_name": "docs"
})

print(response.json()["answer"])
```

### Advanced: RAG-Fusion

```python
response = requests.post("http://localhost:8000/api/rag/query", json={
    "question": "Complex multi-faceted question?",
    "collection_name": "docs",
    "config": {
        "rag_technique": "rag_fusion",
        "llm_model": "llama3.1:8b",
        "top_k": 5
    }
})
```

## Development Status

### ✅ Phase 1: MVP (Completed)
- Basic RAG pipeline
- Authentication system
- Multi-workspace support
- Document ingestion
- Web interface

### ✅ Phase 2: Advanced RAG Engine (Completed)
- Multiple LLM support (Ollama)
- Advanced RAG techniques (Fusion, HyDE, Multi-Query)
- Configurable embeddings
- Custom prompt templates
- Dynamic configuration
- Comprehensive API

### 🚀 Phase 3: Frontend Integration (Next)
- RAG configuration UI
- Model selection interface
- Technique comparison
- Analytics dashboard

## Contributing

Contributions are welcome! Please see individual service directories for development setup.

## License

MIT License
