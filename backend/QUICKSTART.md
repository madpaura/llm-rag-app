# RAG Engine Quick Start Guide

Get started with the advanced RAG engine in 5 minutes.

## Prerequisites

1. **Python 3.10+** installed
2. **Ollama** installed and running
3. Required models pulled

## Installation

### 1. Install Ollama

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama

# Windows
# Download from https://ollama.com/download
```

### 2. Pull Required Models

```bash
# LLM model
ollama pull llama3.2:3b

# Embedding model
ollama pull nomic-embed-text
```

### 3. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

## Start the Server

```bash
# Make sure Ollama is running
ollama serve

# In another terminal, start the FastAPI server
cd backend
python main.py
```

The API will be available at `http://localhost:8000`

## Quick Test

### Option 1: Using cURL

```bash
# Ingest documents
curl -X POST "http://localhost:8000/api/rag/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "content": "Python is a high-level programming language.",
        "metadata": {"source": "intro.txt"}
      }
    ],
    "collection_name": "test"
  }'

# Query
curl -X POST "http://localhost:8000/api/rag/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is Python?",
    "collection_name": "test"
  }'
```

### Option 2: Using Python Client

```python
# Save as test_rag.py
import requests

# Ingest
response = requests.post("http://localhost:8000/api/rag/ingest", json={
    "documents": [
        {
            "content": "Python is a high-level programming language.",
            "metadata": {"source": "intro.txt"}
        }
    ],
    "collection_name": "test"
})
print("Ingest:", response.json())

# Query
response = requests.post("http://localhost:8000/api/rag/query", json={
    "question": "What is Python?",
    "collection_name": "test"
})
print("Answer:", response.json()["answer"])
```

Run it:
```bash
python test_rag.py
```

### Option 3: Using Example Scripts

```bash
# Run comprehensive examples
cd backend
python examples/api_client_example.py
```

## API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

## Common Use Cases

### 1. Standard RAG

```python
import requests

# Ingest
requests.post("http://localhost:8000/api/rag/ingest", json={
    "documents": [{"content": "Your content", "metadata": {}}],
    "collection_name": "my_docs"
})

# Query
response = requests.post("http://localhost:8000/api/rag/query", json={
    "question": "Your question?",
    "collection_name": "my_docs"
})
print(response.json()["answer"])
```

### 2. RAG-Fusion (Better for Complex Queries)

```python
response = requests.post("http://localhost:8000/api/rag/query", json={
    "question": "Complex question requiring multiple perspectives?",
    "collection_name": "my_docs",
    "config": {
        "rag_technique": "rag_fusion",
        "top_k": 5
    }
})
```

### 3. HyDE (Better for Vague Queries)

```python
response = requests.post("http://localhost:8000/api/rag/query", json={
    "question": "Vague or broad question?",
    "collection_name": "my_docs",
    "config": {
        "rag_technique": "hyde"
    }
})
```

### 4. Custom Prompt Template

```python
custom_prompt = """Answer the question based on context.

Context: {context}
Question: {question}
Answer:"""

response = requests.post("http://localhost:8000/api/rag/query", json={
    "question": "Your question?",
    "collection_name": "my_docs",
    "config": {
        "prompt_template": custom_prompt
    }
})
```

### 5. Different Models

```python
# Use a larger model for better quality
response = requests.post("http://localhost:8000/api/rag/query", json={
    "question": "Your question?",
    "collection_name": "my_docs",
    "config": {
        "llm_model": "llama3.1:8b",  # Larger model
        "temperature": 0.3
    }
})
```

## Configuration Options

### Essential Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `llm_model` | "llama3.2:3b" | LLM model name |
| `embedding_model` | "nomic-embed-text" | Embedding model |
| `rag_technique` | "standard" | RAG technique |
| `top_k` | 4 | Number of documents to retrieve |
| `chunk_size` | 1000 | Text chunk size |
| `temperature` | 0.0 | LLM temperature |

### RAG Techniques

- **standard**: Fast, straightforward
- **rag_fusion**: Best for complex queries
- **hyde**: Best for vague queries
- **multi_query**: Overcomes similarity search limitations

## Troubleshooting

### Issue: "Connection refused"

**Solution**: Make sure Ollama is running
```bash
ollama serve
```

### Issue: "Model not found"

**Solution**: Pull the model
```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

### Issue: "Out of memory"

**Solution**: Use a smaller model
```python
config = {
    "llm_model": "llama3.2:1b",  # Smaller model
    "chunk_size": 500,
    "top_k": 2
}
```

### Issue: "Slow responses"

**Solution**: 
1. Use smaller models
2. Reduce top_k
3. Use standard RAG instead of fusion/hyde
4. Enable GPU acceleration in Ollama

## Next Steps

1. **Read the full documentation**: `backend/RAG_ENGINE_README.md`
2. **Explore examples**: `backend/examples/`
3. **Try different techniques**: Experiment with RAG-Fusion, HyDE
4. **Customize prompts**: Create domain-specific prompts
5. **Scale up**: Use larger models for production

## Available Models

### Small Models (Fast, Lower Quality)
- llama3.2:1b
- llama3.2:3b
- phi3:mini

### Medium Models (Balanced)
- llama3.1:8b
- mistral:7b
- gemma2:9b

### Large Models (Best Quality, Slower)
- llama3.1:70b
- mixtral:8x7b
- gpt-oss:120b-cloud

## API Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/rag/ingest` | POST | Ingest documents |
| `/api/rag/query` | POST | Query RAG system |
| `/api/rag/config` | GET/PUT | Manage configuration |
| `/api/rag/models` | GET | List available models |
| `/api/rag/techniques` | GET | List RAG techniques |
| `/api/rag/collections` | GET | List collections |
| `/api/rag/health` | GET | Health check |

## Support

- **API Docs**: http://localhost:8000/docs
- **Full README**: `backend/RAG_ENGINE_README.md`
- **Examples**: `backend/examples/`

Happy RAG building! 🚀
