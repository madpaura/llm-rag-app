# Advanced RAG Engine API

A comprehensive Retrieval-Augmented Generation (RAG) backend API with support for multiple LLM models, embedding strategies, and advanced RAG techniques.

## Features

### 🚀 Core Capabilities

- **Multiple LLM Support**: Ollama models (Llama, Mistral, Phi, Gemma, etc.)
- **Flexible Embeddings**: Ollama, OpenAI, and Sentence Transformers
- **Advanced RAG Techniques**:
  - Standard RAG
  - RAG-Fusion (multi-query generation and fusion)
  - HyDE (Hypothetical Document Embeddings)
  - Multi-Query RAG
  - Contextual Compression
- **Configurable Retrieval**: Similarity, MMR, score threshold
- **Custom Prompt Templates**: Define your own prompts
- **Multiple Vector Stores**: Chroma, FAISS
- **Collection Management**: Organize documents by collections

## API Endpoints

### Document Ingestion

**POST** `/api/rag/ingest`

Ingest documents into the RAG system.

```json
{
  "documents": [
    {
      "content": "Your document content here",
      "metadata": {
        "source": "example.pdf",
        "page": 1
      }
    }
  ],
  "collection_name": "my_collection",
  "config": {
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "embedding_model": "nomic-embed-text"
  }
}
```

### Query RAG System

**POST** `/api/rag/query`

Query the RAG system with a question.

```json
{
  "question": "What is task decomposition?",
  "collection_name": "my_collection",
  "config": {
    "llm_model": "llama3.2:3b",
    "rag_technique": "rag_fusion",
    "top_k": 4,
    "temperature": 0.0
  }
}
```

Response:
```json
{
  "answer": "Task decomposition is...",
  "source_documents": [
    {
      "content": "Document content...",
      "metadata": {"source": "example.pdf"}
    }
  ],
  "technique": "rag_fusion",
  "metadata": {
    "queries_generated": ["query1", "query2", "query3"]
  }
}
```

### Configuration Management

**GET** `/api/rag/config?collection_name=my_collection`

Get current configuration.

**PUT** `/api/rag/config?collection_name=my_collection`

Update configuration.

```json
{
  "config": {
    "llm_model": "llama3.1:8b",
    "temperature": 0.7,
    "rag_technique": "hyde",
    "top_k": 5
  }
}
```

### List Available Resources

**GET** `/api/rag/models`

List available LLM and embedding models.

**GET** `/api/rag/prompt-templates`

List available prompt templates.

**GET** `/api/rag/techniques`

List available RAG techniques with descriptions.

### Collection Management

**GET** `/api/rag/collections`

List all active collections.

**DELETE** `/api/rag/collection/{collection_name}`

Delete a collection.

### Health Check

**GET** `/api/rag/health?collection_name=my_collection`

Check RAG engine health status.

## Configuration Options

### LLM Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `llm_model` | string | "llama3.2:3b" | LLM model name |
| `llm_temperature` | float | 0.0 | Temperature (0.0-2.0) |
| `llm_base_url` | string | null | Custom Ollama base URL |

### Embedding Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `embedding_model` | string | "nomic-embed-text" | Embedding model name |
| `embedding_strategy` | enum | "ollama" | ollama, openai, sentence_transformers |
| `embedding_base_url` | string | null | Custom embedding base URL |

### Chunking Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `chunk_size` | int | 1000 | Chunk size (100-10000) |
| `chunk_overlap` | int | 200 | Overlap between chunks (0-1000) |

### Retrieval Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `retrieval_strategy` | enum | "similarity" | similarity, mmr, similarity_score_threshold |
| `top_k` | int | 4 | Number of documents to retrieve (1-20) |
| `score_threshold` | float | null | Minimum similarity score (0.0-1.0) |

### RAG Technique

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `rag_technique` | enum | "standard" | standard, rag_fusion, hyde, multi_query, contextual_compression |

### Prompt Template

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt_template` | string | null | Custom prompt with {context} and {question} placeholders |

### Vector Store

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `vector_store_type` | enum | "chroma" | chroma, faiss |
| `persist_directory` | string | null | Directory to persist vector store |

## RAG Techniques Explained

### Standard RAG
Direct retrieval and generation. Best for straightforward queries.

```json
{
  "rag_technique": "standard"
}
```

### RAG-Fusion
Generates multiple query variations and fuses results. Best for complex queries that benefit from multiple perspectives.

```json
{
  "rag_technique": "rag_fusion"
}
```

### HyDE (Hypothetical Document Embeddings)
Generates a hypothetical answer first, then uses it to retrieve relevant documents. Best when queries are vague or require domain knowledge expansion.

```json
{
  "rag_technique": "hyde"
}
```

### Multi-Query RAG
Generates multiple perspectives for better retrieval. Helps overcome limitations of distance-based similarity search.

```json
{
  "rag_technique": "multi_query"
}
```

## Available Models

### LLM Models (Ollama)
- llama3.2:3b, llama3.2:1b
- llama3.1:8b, llama3.1:70b
- mistral:7b, mixtral:8x7b
- phi3:mini
- gemma2:9b
- qwen2.5:7b
- deepseek-r1:7b
- gpt-oss:120b-cloud

### Embedding Models
**Ollama:**
- nomic-embed-text
- mxbai-embed-large
- all-minilm

**OpenAI:**
- text-embedding-ada-002
- text-embedding-3-small
- text-embedding-3-large

**Sentence Transformers:**
- all-MiniLM-L6-v2
- all-mpnet-base-v2

## Prompt Templates

### Default
Concise Q&A template (3 sentences max).

### Detailed
Comprehensive answers with examples.

### Technical
Technical documentation with code examples.

### Conversational
Natural, friendly conversation style.

### Step-by-Step
Tutorial-style explanations.

## Usage Examples

### Example 1: Basic RAG Query

```python
import requests

# Ingest documents
response = requests.post("http://localhost:8000/api/rag/ingest", json={
    "documents": [
        {
            "content": "LangChain is a framework for developing applications powered by language models.",
            "metadata": {"source": "docs"}
        }
    ],
    "collection_name": "langchain_docs"
})

# Query
response = requests.post("http://localhost:8000/api/rag/query", json={
    "question": "What is LangChain?",
    "collection_name": "langchain_docs"
})

print(response.json()["answer"])
```

### Example 2: RAG-Fusion with Custom Config

```python
response = requests.post("http://localhost:8000/api/rag/query", json={
    "question": "How does task decomposition work in AI agents?",
    "collection_name": "ai_docs",
    "config": {
        "llm_model": "llama3.1:8b",
        "rag_technique": "rag_fusion",
        "top_k": 5,
        "temperature": 0.2,
        "retrieval_strategy": "mmr"
    }
})

result = response.json()
print(f"Answer: {result['answer']}")
print(f"Queries used: {result['metadata']['queries_generated']}")
```

### Example 3: HyDE with Custom Prompt

```python
custom_prompt = """You are a technical expert. Use the context to provide a detailed technical answer.

Context: {context}

Question: {question}

Technical Answer:"""

response = requests.post("http://localhost:8000/api/rag/query", json={
    "question": "Explain the architecture of transformers",
    "collection_name": "ml_papers",
    "config": {
        "rag_technique": "hyde",
        "prompt_template": custom_prompt,
        "llm_model": "mixtral:8x7b"
    }
})
```

### Example 4: Using Different Embeddings

```python
# OpenAI embeddings
response = requests.post("http://localhost:8000/api/rag/ingest", json={
    "documents": [...],
    "collection_name": "openai_collection",
    "config": {
        "embedding_strategy": "openai",
        "embedding_model": "text-embedding-3-small"
    }
})

# Sentence Transformers
response = requests.post("http://localhost:8000/api/rag/ingest", json={
    "documents": [...],
    "collection_name": "st_collection",
    "config": {
        "embedding_strategy": "sentence_transformers",
        "embedding_model": "all-mpnet-base-v2"
    }
})
```

## Installation

1. Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

2. Install Ollama (if not already installed):
```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama
```

3. Pull required models:
```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

4. Start the server:
```bash
python main.py
```

The API will be available at `http://localhost:8000`.

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         FastAPI App                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      RAG API Routes                          │
│  /ingest, /query, /config, /models, /techniques             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       RAG Engine                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │     LLM      │  │  Embeddings  │  │ Text Splitter│      │
│  │   (Ollama)   │  │   (Ollama)   │  │  (LangChain) │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Vector Store │  │  Retriever   │  │RAG Techniques│      │
│  │(Chroma/FAISS)│  │  (Similarity)│  │(Fusion/HyDE) │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Best Practices

1. **Choose the right technique**:
   - Standard: Simple, fast queries
   - RAG-Fusion: Complex queries needing multiple perspectives
   - HyDE: Vague queries or domain expansion
   - Multi-Query: Overcoming similarity search limitations

2. **Optimize chunk size**:
   - Smaller chunks (500-1000): Better precision
   - Larger chunks (1500-2000): Better context

3. **Adjust top_k**:
   - Lower (2-4): More focused answers
   - Higher (5-10): More comprehensive context

4. **Use appropriate models**:
   - Small models (3B): Fast, lower quality
   - Medium models (7-8B): Balanced
   - Large models (70B+): Best quality, slower

5. **Persist vector stores**:
   - Set `persist_directory` to save and reload collections

## Troubleshooting

### Ollama Connection Issues
```bash
# Check if Ollama is running
ollama list

# Start Ollama service
ollama serve
```

### Model Not Found
```bash
# Pull the model
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

### Memory Issues
- Use smaller models (3B instead of 70B)
- Reduce chunk_size and top_k
- Use FAISS instead of Chroma for large datasets

## Performance Tips

1. **Batch ingestion**: Ingest multiple documents at once
2. **Reuse collections**: Don't recreate vector stores unnecessarily
3. **Persist vector stores**: Save to disk for faster startup
4. **Use appropriate hardware**: GPU for large models, CPU for small models
5. **Cache embeddings**: Reuse embeddings when possible

## License

MIT License
