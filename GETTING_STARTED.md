# Getting Started with RAG Engine

Complete step-by-step guide to get your RAG engine up and running in minutes.

## 📋 Prerequisites Checklist

Before you begin, ensure you have:

- [ ] **Python 3.10 or higher** installed
  ```bash
  python3 --version  # Should show 3.10+
  ```

- [ ] **Git** installed (for cloning repository)
  ```bash
  git --version
  ```

- [ ] **8GB+ RAM** available (16GB recommended)

- [ ] **50GB+ disk space** for models and data

- [ ] **Internet connection** for downloading models

---

## 🚀 Quick Start (5 Minutes)

### Option 1: Automated Setup (Recommended)

```bash
# 1. Navigate to backend directory
cd backend

# 2. Run automated setup script
./setup.sh

# 3. Start the server
python main.py

# 4. Open browser to API docs
# Visit: http://localhost:8000/docs
```

That's it! The script handles everything:
- ✅ Checks Python version
- ✅ Installs Ollama
- ✅ Pulls required models
- ✅ Creates virtual environment
- ✅ Installs dependencies
- ✅ Runs tests

### Option 2: Manual Setup (10 Minutes)

#### Step 1: Install Ollama

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**macOS:**
```bash
brew install ollama
```

**Windows:**
Download from https://ollama.com/download

#### Step 2: Start Ollama

```bash
# Start Ollama service
ollama serve

# In another terminal, verify it's running
ollama list
```

#### Step 3: Pull Required Models

```bash
# Pull LLM model (this may take a few minutes)
ollama pull llama3.2:3b

# Pull embedding model
ollama pull nomic-embed-text
```

#### Step 4: Setup Python Environment

```bash
# Navigate to backend
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

#### Step 5: Test Installation

```bash
# Run installation test
python test_installation.py

# Should see all checks passing ✓
```

#### Step 6: Start Server

```bash
# Start FastAPI server
python main.py

# Server will start at http://localhost:8000
```

---

## ✅ Verification Steps

### 1. Check API is Running

```bash
# Test health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status": "ok"}
```

### 2. Check Available Models

```bash
curl http://localhost:8000/api/rag/models

# Should list available LLM and embedding models
```

### 3. Test Document Ingestion

```bash
curl -X POST "http://localhost:8000/api/rag/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "content": "Python is a high-level programming language known for its simplicity and readability.",
        "metadata": {"source": "test.txt"}
      }
    ],
    "collection_name": "test"
  }'

# Expected: {"status": "success", "documents_ingested": 1, ...}
```

### 4. Test Query

```bash
curl -X POST "http://localhost:8000/api/rag/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is Python?",
    "collection_name": "test"
  }'

# Expected: {"answer": "Python is a high-level...", ...}
```

---

## 🎯 Your First RAG Application

### Example 1: Basic Q&A

Create a file `test_basic.py`:

```python
import requests

BASE_URL = "http://localhost:8000/api/rag"

# 1. Ingest some documents
documents = [
    {
        "content": "FastAPI is a modern, fast web framework for building APIs with Python 3.7+.",
        "metadata": {"source": "fastapi_intro.txt"}
    },
    {
        "content": "FastAPI provides automatic API documentation and data validation using Pydantic.",
        "metadata": {"source": "fastapi_features.txt"}
    }
]

response = requests.post(f"{BASE_URL}/ingest", json={
    "documents": documents,
    "collection_name": "fastapi_docs"
})
print("Ingestion:", response.json())

# 2. Ask questions
questions = [
    "What is FastAPI?",
    "What features does FastAPI provide?",
    "Is FastAPI fast?"
]

for question in questions:
    response = requests.post(f"{BASE_URL}/query", json={
        "question": question,
        "collection_name": "fastapi_docs"
    })
    result = response.json()
    print(f"\nQ: {question}")
    print(f"A: {result['answer']}")
```

Run it:
```bash
python test_basic.py
```

### Example 2: Using RAG-Fusion

```python
import requests

BASE_URL = "http://localhost:8000/api/rag"

# Ingest documents about machine learning
documents = [
    {"content": "Machine learning is a subset of AI that enables systems to learn from data.", "metadata": {}},
    {"content": "Deep learning uses neural networks with multiple layers.", "metadata": {}},
    {"content": "Supervised learning trains models on labeled data.", "metadata": {}},
]

requests.post(f"{BASE_URL}/ingest", json={
    "documents": documents,
    "collection_name": "ml_docs"
})

# Query with RAG-Fusion for better results
response = requests.post(f"{BASE_URL}/query", json={
    "question": "How does machine learning work?",
    "collection_name": "ml_docs",
    "config": {
        "rag_technique": "rag_fusion",
        "top_k": 3
    }
})

result = response.json()
print("Answer:", result['answer'])
print("\nGenerated queries:", result['metadata'].get('queries_generated', []))
```

### Example 3: Custom Prompt Template

```python
import requests

BASE_URL = "http://localhost:8000/api/rag"

# Custom prompt for code-focused responses
custom_prompt = """You are a coding assistant. Provide code examples when relevant.

Context: {context}

Question: {question}

Answer with code examples:"""

response = requests.post(f"{BASE_URL}/query", json={
    "question": "How do I create a list in Python?",
    "collection_name": "python_docs",
    "config": {
        "prompt_template": custom_prompt
    }
})

print(response.json()['answer'])
```

---

## 🎨 Explore the API

### Interactive API Documentation

Visit http://localhost:8000/docs to explore:
- All available endpoints
- Request/response schemas
- Try out API calls directly in browser
- See example requests and responses

### Alternative Documentation

Visit http://localhost:8000/redoc for:
- Clean, readable API documentation
- Detailed schema information
- Organized by tags

---

## 📚 Next Steps

### 1. Run Example Scripts

```bash
# Direct engine usage examples
python examples/rag_example.py

# API client examples
python examples/api_client_example.py
```

### 2. Try Different Models

```bash
# Pull a larger model for better quality
ollama pull llama3.1:8b

# Use it in your queries
curl -X POST "http://localhost:8000/api/rag/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Your question",
    "collection_name": "docs",
    "config": {
      "llm_model": "llama3.1:8b"
    }
  }'
```

### 3. Experiment with RAG Techniques

Try each technique to see which works best:

```python
techniques = ["standard", "rag_fusion", "hyde", "multi_query"]

for technique in techniques:
    response = requests.post(f"{BASE_URL}/query", json={
        "question": "Your complex question here",
        "collection_name": "docs",
        "config": {"rag_technique": technique}
    })
    print(f"\n{technique}: {response.json()['answer'][:100]}...")
```

### 4. Integrate with Your Application

See [`INTEGRATION_GUIDE.md`](INTEGRATION_GUIDE.md) for:
- Frontend integration (React/TypeScript)
- Backend integration patterns
- Production deployment
- Monitoring and scaling

---

## 🔧 Configuration Tips

### For Better Quality

```python
config = {
    "llm_model": "llama3.1:8b",  # Larger model
    "rag_technique": "rag_fusion",  # Better retrieval
    "top_k": 5,  # More context
    "temperature": 0.3  # More creative
}
```

### For Faster Responses

```python
config = {
    "llm_model": "llama3.2:1b",  # Smaller model
    "rag_technique": "standard",  # Simpler technique
    "top_k": 2,  # Less context
    "temperature": 0.0  # Deterministic
}
```

### For Vague Questions

```python
config = {
    "rag_technique": "hyde",  # Hypothetical document embeddings
    "llm_model": "llama3.1:8b"
}
```

---

## 🐛 Troubleshooting

### Issue: "Connection refused"

**Solution:**
```bash
# Make sure Ollama is running
ollama serve

# Check if it's accessible
curl http://localhost:11434/api/tags
```

### Issue: "Model not found"

**Solution:**
```bash
# List available models
ollama list

# Pull the model you need
ollama pull llama3.2:3b
```

### Issue: "Out of memory"

**Solution:**
```python
# Use a smaller model
config = {
    "llm_model": "llama3.2:1b",
    "chunk_size": 500,
    "top_k": 2
}
```

### Issue: "Slow responses"

**Solutions:**
1. Use smaller models (1B-3B)
2. Reduce top_k (2-3)
3. Use standard RAG instead of fusion
4. Enable GPU if available

### Issue: "Installation test fails"

**Solution:**
```bash
# Check each component individually
python3 --version  # Should be 3.10+
ollama list  # Should show models
pip list | grep langchain  # Should show langchain packages

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

---

## 📖 Documentation Reference

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [`QUICKSTART.md`](backend/QUICKSTART.md) | Quick reference | First time setup |
| [`RAG_ENGINE_README.md`](backend/RAG_ENGINE_README.md) | Complete docs | Deep dive |
| [`INTEGRATION_GUIDE.md`](INTEGRATION_GUIDE.md) | Integration | Building apps |
| [`DEPLOYMENT.md`](backend/DEPLOYMENT.md) | Production | Deploying |
| [`IMPLEMENTATION_SUMMARY.md`](IMPLEMENTATION_SUMMARY.md) | Overview | Understanding |

---

## 💡 Pro Tips

1. **Start Simple**: Begin with standard RAG, then experiment with advanced techniques

2. **Monitor Performance**: Check response times and adjust configuration accordingly

3. **Use Collections**: Organize documents by topic or workspace

4. **Persist Vector Stores**: Set `persist_directory` to avoid re-indexing

5. **Experiment with Prompts**: Custom prompts can significantly improve results

6. **Batch Ingestion**: Ingest multiple documents at once for efficiency

7. **Cache Embeddings**: Reuse embeddings when possible

8. **Monitor Resources**: Keep an eye on memory and CPU usage

---

## 🎓 Learning Path

### Week 1: Basics
- [ ] Complete setup
- [ ] Run example scripts
- [ ] Try basic queries
- [ ] Understand standard RAG

### Week 2: Advanced
- [ ] Experiment with RAG-Fusion
- [ ] Try HyDE technique
- [ ] Create custom prompts
- [ ] Test different models

### Week 3: Integration
- [ ] Integrate with your app
- [ ] Build a simple UI
- [ ] Add authentication
- [ ] Deploy to staging

### Week 4: Production
- [ ] Performance tuning
- [ ] Set up monitoring
- [ ] Deploy to production
- [ ] Document your setup

---

## 🆘 Getting Help

1. **Check Documentation**: Most answers are in the docs
2. **Run Examples**: See working code in `examples/`
3. **Check Logs**: Look at server logs for errors
4. **Test Endpoints**: Use `/docs` to test API calls
5. **Health Check**: Use `/health` to verify status

---

## ✨ You're Ready!

You now have:
- ✅ A running RAG engine
- ✅ Multiple LLM models available
- ✅ Advanced RAG techniques at your disposal
- ✅ Comprehensive documentation
- ✅ Working examples

**Start building amazing RAG applications!** 🚀

---

**Quick Commands Reference:**

```bash
# Start server
python main.py

# Run examples
python examples/api_client_example.py

# Test installation
python test_installation.py

# View API docs
open http://localhost:8000/docs

# Check health
curl http://localhost:8000/health
```

Happy building! 🎉
