# RAG Engine Integration Guide

Complete guide for integrating the advanced RAG engine into your application.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Backend Setup](#backend-setup)
3. [API Integration](#api-integration)
4. [Frontend Integration](#frontend-integration)
5. [Advanced Usage](#advanced-usage)
6. [Production Deployment](#production-deployment)

---

## Quick Start

### Automated Setup

```bash
cd backend
./setup.sh
```

This script will:
- Check Python version
- Install Ollama (if needed)
- Pull required models
- Create virtual environment
- Install dependencies
- Run installation tests

### Manual Setup

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull models
ollama pull llama3.2:3b
ollama pull nomic-embed-text

# 3. Install Python dependencies
cd backend
pip install -r requirements.txt

# 4. Test installation
python test_installation.py

# 5. Start server
python main.py
```

---

## Backend Setup

### Directory Structure

```
backend/
├── services/
│   ├── rag_engine.py          # Core RAG engine
│   ├── query_service.py       # Existing query service
│   └── vector_service.py      # Existing vector service
├── api/
│   ├── routes/
│   │   ├── rag.py            # New RAG endpoints
│   │   ├── query.py          # Existing query endpoints
│   │   └── ...
│   └── schemas/
│       └── rag_schemas.py    # RAG API schemas
├── examples/
│   ├── rag_example.py        # Direct usage examples
│   └── api_client_example.py # API client examples
├── main.py                   # FastAPI app
└── requirements.txt          # Updated dependencies
```

### Configuration

Create `.env` file:

```bash
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434

# Vector Store
VECTOR_STORE_PERSIST_DIR=./data/vector_stores

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Starting the Server

```bash
# Development
python main.py

# Production with Uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## API Integration

### Base URL

```
http://localhost:8000/api/rag
```

### Authentication

If your app uses JWT authentication, include the token:

```python
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}
```

### Core Endpoints

#### 1. Ingest Documents

```python
import requests

response = requests.post(
    "http://localhost:8000/api/rag/ingest",
    json={
        "documents": [
            {
                "content": "Document content here",
                "metadata": {
                    "source": "file.pdf",
                    "page": 1,
                    "workspace_id": "workspace_123"
                }
            }
        ],
        "collection_name": "workspace_123",
        "config": {
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "embedding_model": "nomic-embed-text"
        }
    }
)

result = response.json()
print(f"Ingested {result['documents_ingested']} documents")
```

#### 2. Query Documents

```python
response = requests.post(
    "http://localhost:8000/api/rag/query",
    json={
        "question": "What is the main topic?",
        "collection_name": "workspace_123",
        "config": {
            "llm_model": "llama3.2:3b",
            "rag_technique": "standard",
            "top_k": 4,
            "temperature": 0.0
        }
    }
)

result = response.json()
print(f"Answer: {result['answer']}")
print(f"Sources: {len(result['source_documents'])}")
```

#### 3. Get Available Models

```python
response = requests.get("http://localhost:8000/api/rag/models")
models = response.json()

print("LLM Models:", models['llm_models'])
print("Embedding Models:", models['embedding_models'])
```

#### 4. List RAG Techniques

```python
response = requests.get("http://localhost:8000/api/rag/techniques")
techniques = response.json()

for tech in techniques['techniques']:
    print(f"{tech['name']}: {tech['description']}")
```

### Python Client Class

```python
class RAGClient:
    def __init__(self, base_url="http://localhost:8000", token=None):
        self.base_url = base_url
        self.headers = {"Content-Type": "application/json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
    
    def ingest(self, documents, collection_name, config=None):
        response = requests.post(
            f"{self.base_url}/api/rag/ingest",
            json={
                "documents": documents,
                "collection_name": collection_name,
                "config": config
            },
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def query(self, question, collection_name, config=None):
        response = requests.post(
            f"{self.base_url}/api/rag/query",
            json={
                "question": question,
                "collection_name": collection_name,
                "config": config
            },
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

# Usage
client = RAGClient(token="your_jwt_token")
result = client.query("What is Python?", "my_docs")
```

---

## Frontend Integration

### React/TypeScript Integration

#### 1. Create RAG Service

```typescript
// src/services/ragService.ts

import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/rag';

export interface Document {
  content: string;
  metadata: Record<string, any>;
}

export interface RAGConfig {
  llm_model?: string;
  embedding_model?: string;
  rag_technique?: 'standard' | 'rag_fusion' | 'hyde' | 'multi_query';
  top_k?: number;
  temperature?: number;
  chunk_size?: number;
  chunk_overlap?: number;
  prompt_template?: string;
}

export interface QueryResponse {
  answer: string;
  source_documents: Array<{
    content: string;
    metadata: Record<string, any>;
  }>;
  technique: string;
  metadata: Record<string, any>;
}

class RAGService {
  private getHeaders() {
    const token = localStorage.getItem('token');
    return {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    };
  }

  async ingestDocuments(
    documents: Document[],
    collectionName: string,
    config?: RAGConfig
  ) {
    const response = await axios.post(
      `${API_BASE_URL}/ingest`,
      {
        documents,
        collection_name: collectionName,
        config,
      },
      { headers: this.getHeaders() }
    );
    return response.data;
  }

  async query(
    question: string,
    collectionName: string,
    config?: RAGConfig
  ): Promise<QueryResponse> {
    const response = await axios.post(
      `${API_BASE_URL}/query`,
      {
        question,
        collection_name: collectionName,
        config,
      },
      { headers: this.getHeaders() }
    );
    return response.data;
  }

  async getModels() {
    const response = await axios.get(`${API_BASE_URL}/models`, {
      headers: this.getHeaders(),
    });
    return response.data;
  }

  async getTechniques() {
    const response = await axios.get(`${API_BASE_URL}/techniques`, {
      headers: this.getHeaders(),
    });
    return response.data;
  }

  async getConfig(collectionName: string) {
    const response = await axios.get(`${API_BASE_URL}/config`, {
      params: { collection_name: collectionName },
      headers: this.getHeaders(),
    });
    return response.data;
  }

  async updateConfig(collectionName: string, config: RAGConfig) {
    const response = await axios.put(
      `${API_BASE_URL}/config`,
      { config },
      {
        params: { collection_name: collectionName },
        headers: this.getHeaders(),
      }
    );
    return response.data;
  }
}

export const ragService = new RAGService();
```

#### 2. Create RAG Configuration Component

```typescript
// src/components/RAGConfig.tsx

import React, { useState, useEffect } from 'react';
import { ragService, RAGConfig } from '../services/ragService';

interface RAGConfigProps {
  collectionName: string;
  onConfigChange?: (config: RAGConfig) => void;
}

export function RAGConfigPanel({ collectionName, onConfigChange }: RAGConfigProps) {
  const [config, setConfig] = useState<RAGConfig>({
    llm_model: 'llama3.2:3b',
    rag_technique: 'standard',
    top_k: 4,
    temperature: 0.0,
  });
  
  const [models, setModels] = useState<any>(null);
  const [techniques, setTechniques] = useState<any[]>([]);

  useEffect(() => {
    loadModelsAndTechniques();
  }, []);

  async function loadModelsAndTechniques() {
    const [modelsData, techniquesData] = await Promise.all([
      ragService.getModels(),
      ragService.getTechniques(),
    ]);
    setModels(modelsData);
    setTechniques(techniquesData.techniques);
  }

  function handleConfigChange(updates: Partial<RAGConfig>) {
    const newConfig = { ...config, ...updates };
    setConfig(newConfig);
    onConfigChange?.(newConfig);
  }

  return (
    <div className="rag-config-panel">
      <h3>RAG Configuration</h3>
      
      {/* LLM Model Selection */}
      <div className="form-group">
        <label>LLM Model</label>
        <select
          value={config.llm_model}
          onChange={(e) => handleConfigChange({ llm_model: e.target.value })}
        >
          {models?.llm_models.map((model: string) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
        </select>
      </div>

      {/* RAG Technique Selection */}
      <div className="form-group">
        <label>RAG Technique</label>
        <select
          value={config.rag_technique}
          onChange={(e) => handleConfigChange({ rag_technique: e.target.value as any })}
        >
          {techniques.map((tech) => (
            <option key={tech.name} value={tech.name}>
              {tech.name} - {tech.description}
            </option>
          ))}
        </select>
      </div>

      {/* Top K */}
      <div className="form-group">
        <label>Top K Documents: {config.top_k}</label>
        <input
          type="range"
          min="1"
          max="10"
          value={config.top_k}
          onChange={(e) => handleConfigChange({ top_k: parseInt(e.target.value) })}
        />
      </div>

      {/* Temperature */}
      <div className="form-group">
        <label>Temperature: {config.temperature}</label>
        <input
          type="range"
          min="0"
          max="1"
          step="0.1"
          value={config.temperature}
          onChange={(e) => handleConfigChange({ temperature: parseFloat(e.target.value) })}
        />
      </div>
    </div>
  );
}
```

#### 3. Enhanced Chat Component

```typescript
// src/components/EnhancedChat.tsx

import React, { useState } from 'react';
import { ragService, RAGConfig } from '../services/ragService';

export function EnhancedChat({ workspaceId }: { workspaceId: string }) {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [config, setConfig] = useState<RAGConfig>({
    rag_technique: 'standard',
    top_k: 4,
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    try {
      const result = await ragService.query(question, workspaceId, config);
      setAnswer(result.answer);
      setSources(result.source_documents);
    } catch (error) {
      console.error('Query failed:', error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="enhanced-chat">
      <RAGConfigPanel
        collectionName={workspaceId}
        onConfigChange={setConfig}
      />
      
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question..."
          disabled={loading}
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Thinking...' : 'Ask'}
        </button>
      </form>

      {answer && (
        <div className="answer">
          <h4>Answer:</h4>
          <p>{answer}</p>
          
          <h4>Sources ({sources.length}):</h4>
          {sources.map((source, idx) => (
            <div key={idx} className="source">
              <p>{source.content.substring(0, 200)}...</p>
              <small>{JSON.stringify(source.metadata)}</small>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

---

## Advanced Usage

### Custom Prompt Templates

```python
# Backend: Define custom prompt
custom_prompt = """You are a helpful coding assistant.

Context: {context}

Question: {question}

Provide a detailed answer with code examples:"""

# API call with custom prompt
response = requests.post("/api/rag/query", json={
    "question": "How do I use async/await in Python?",
    "collection_name": "python_docs",
    "config": {
        "prompt_template": custom_prompt,
        "llm_model": "llama3.1:8b"
    }
})
```

### RAG-Fusion for Complex Queries

```python
# Use RAG-Fusion for multi-faceted questions
response = requests.post("/api/rag/query", json={
    "question": "What are the pros and cons of microservices architecture?",
    "collection_name": "architecture_docs",
    "config": {
        "rag_technique": "rag_fusion",
        "top_k": 6,
        "temperature": 0.3
    }
})

# Access generated queries
queries = response.json()['metadata']['queries_generated']
print("Generated queries:", queries)
```

### HyDE for Vague Questions

```python
# Use HyDE when the question is broad or vague
response = requests.post("/api/rag/query", json={
    "question": "Tell me about machine learning",
    "collection_name": "ml_docs",
    "config": {
        "rag_technique": "hyde",
        "llm_model": "mixtral:8x7b"
    }
})

# See the hypothetical document
hypo_doc = response.json()['metadata']['hypothetical_document']
print("Hypothetical doc:", hypo_doc[:200])
```

---

## Production Deployment

### Docker Setup

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose ports
EXPOSE 8000 11434

# Start script
COPY start.sh .
RUN chmod +x start.sh

CMD ["./start.sh"]
```

```bash
# start.sh
#!/bin/bash
ollama serve &
sleep 5
ollama pull llama3.2:3b
ollama pull nomic-embed-text
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  rag-backend:
    build: ./backend
    ports:
      - "8000:8000"
      - "11434:11434"
    volumes:
      - ./data:/app/data
    environment:
      - OLLAMA_BASE_URL=http://localhost:11434
      - VECTOR_STORE_PERSIST_DIR=/app/data/vector_stores
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:8000
    depends_on:
      - rag-backend
```

### Environment Variables

```bash
# Production .env
OLLAMA_BASE_URL=http://ollama-service:11434
VECTOR_STORE_PERSIST_DIR=/data/vector_stores
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
ALLOWED_ORIGINS=https://your-domain.com
LOG_LEVEL=info
```

### Performance Tuning

```python
# Use connection pooling
import httpx

client = httpx.AsyncClient(
    limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
)

# Batch processing
async def process_batch(questions, collection_name):
    tasks = [
        ragService.query(q, collection_name)
        for q in questions
    ]
    return await asyncio.gather(*tasks)
```

---

## Monitoring & Logging

### Add Logging

```python
import structlog

logger = structlog.get_logger()

# In your code
logger.info(
    "query_processed",
    collection=collection_name,
    technique=config.rag_technique,
    duration_ms=duration
)
```

### Metrics

```python
from prometheus_client import Counter, Histogram

query_counter = Counter('rag_queries_total', 'Total RAG queries')
query_duration = Histogram('rag_query_duration_seconds', 'Query duration')

@query_duration.time()
async def query_with_metrics(question, collection_name):
    query_counter.inc()
    return await rag_engine.query(question)
```

---

## Testing

### Unit Tests

```python
# tests/test_rag_engine.py
import pytest
from services.rag_engine import RAGEngine, RAGConfig

@pytest.mark.asyncio
async def test_standard_rag():
    config = RAGConfig(llm_model="llama3.2:3b")
    engine = RAGEngine(config)
    
    documents = [Document(page_content="Test content")]
    await engine.ingest_documents(documents)
    
    result = await engine.query("What is this about?")
    assert result['answer']
    assert result['technique'] == 'standard'
```

### Integration Tests

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_ingest_and_query():
    # Ingest
    response = client.post("/api/rag/ingest", json={
        "documents": [{"content": "Test", "metadata": {}}],
        "collection_name": "test"
    })
    assert response.status_code == 200
    
    # Query
    response = client.post("/api/rag/query", json={
        "question": "Test question?",
        "collection_name": "test"
    })
    assert response.status_code == 200
    assert "answer" in response.json()
```

---

## Summary

You now have a complete RAG engine with:

✅ Multiple LLM and embedding model support  
✅ Advanced RAG techniques (Fusion, HyDE, Multi-Query)  
✅ Configurable retrieval strategies  
✅ Custom prompt templates  
✅ REST API with comprehensive endpoints  
✅ Frontend integration examples  
✅ Production deployment guides  
✅ Monitoring and testing setup  

**Next Steps:**
1. Run `./setup.sh` to get started
2. Test with `python examples/api_client_example.py`
3. Integrate into your frontend
4. Deploy to production

For more details, see:
- `backend/RAG_ENGINE_README.md` - Full documentation
- `backend/QUICKSTART.md` - Quick start guide
- `backend/examples/` - Code examples
