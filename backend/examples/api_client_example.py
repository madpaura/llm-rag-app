"""
Example API client for testing the RAG engine endpoints.
"""
import requests
import json
from typing import Dict, Any, List


class RAGClient:
    """Client for interacting with RAG API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api/rag"
    
    def ingest_documents(
        self,
        documents: List[Dict[str, Any]],
        collection_name: str = "default",
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Ingest documents into RAG system."""
        payload = {
            "documents": documents,
            "collection_name": collection_name
        }
        if config:
            payload["config"] = config
        
        response = requests.post(f"{self.api_url}/ingest", json=payload)
        response.raise_for_status()
        return response.json()
    
    def query(
        self,
        question: str,
        collection_name: str = "default",
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Query the RAG system."""
        payload = {
            "question": question,
            "collection_name": collection_name
        }
        if config:
            payload["config"] = config
        
        response = requests.post(f"{self.api_url}/query", json=payload)
        response.raise_for_status()
        return response.json()
    
    def get_config(self, collection_name: str = "default") -> Dict[str, Any]:
        """Get current configuration."""
        response = requests.get(
            f"{self.api_url}/config",
            params={"collection_name": collection_name}
        )
        response.raise_for_status()
        return response.json()
    
    def update_config(
        self,
        config: Dict[str, Any],
        collection_name: str = "default"
    ) -> Dict[str, Any]:
        """Update configuration."""
        response = requests.put(
            f"{self.api_url}/config",
            params={"collection_name": collection_name},
            json={"config": config}
        )
        response.raise_for_status()
        return response.json()
    
    def list_models(self) -> Dict[str, List[str]]:
        """List available models."""
        response = requests.get(f"{self.api_url}/models")
        response.raise_for_status()
        return response.json()
    
    def list_prompt_templates(self) -> Dict[str, Any]:
        """List available prompt templates."""
        response = requests.get(f"{self.api_url}/prompt-templates")
        response.raise_for_status()
        return response.json()
    
    def list_techniques(self) -> Dict[str, Any]:
        """List available RAG techniques."""
        response = requests.get(f"{self.api_url}/techniques")
        response.raise_for_status()
        return response.json()
    
    def list_collections(self) -> Dict[str, Any]:
        """List all collections."""
        response = requests.get(f"{self.api_url}/collections")
        response.raise_for_status()
        return response.json()
    
    def delete_collection(self, collection_name: str) -> Dict[str, Any]:
        """Delete a collection."""
        response = requests.delete(f"{self.api_url}/collection/{collection_name}")
        response.raise_for_status()
        return response.json()
    
    def health_check(self, collection_name: str = "default") -> Dict[str, Any]:
        """Check health of RAG engine."""
        response = requests.get(
            f"{self.api_url}/health",
            params={"collection_name": collection_name}
        )
        response.raise_for_status()
        return response.json()


def example_basic_workflow():
    """Example: Basic RAG workflow."""
    print("\n=== Basic RAG Workflow ===\n")
    
    client = RAGClient()
    
    # 1. Ingest documents
    print("1. Ingesting documents...")
    documents = [
        {
            "content": "Python is a high-level programming language known for its simplicity.",
            "metadata": {"source": "python_intro.txt"}
        },
        {
            "content": "Python supports object-oriented, functional, and procedural programming.",
            "metadata": {"source": "python_features.txt"}
        }
    ]
    
    result = client.ingest_documents(
        documents=documents,
        collection_name="python_docs"
    )
    print(f"✓ Ingested {result['documents_ingested']} documents")
    
    # 2. Query
    print("\n2. Querying...")
    response = client.query(
        question="What is Python?",
        collection_name="python_docs"
    )
    print(f"Answer: {response['answer']}")
    print(f"Technique: {response['technique']}")
    print(f"Sources: {len(response['source_documents'])}")


def example_rag_fusion():
    """Example: RAG-Fusion technique."""
    print("\n=== RAG-Fusion Example ===\n")
    
    client = RAGClient()
    
    # Ingest with custom config
    documents = [
        {
            "content": "Machine learning enables computers to learn from data without explicit programming.",
            "metadata": {"source": "ml_intro"}
        },
        {
            "content": "Deep learning uses neural networks with multiple layers for complex pattern recognition.",
            "metadata": {"source": "deep_learning"}
        },
        {
            "content": "Supervised learning trains models on labeled data to make predictions.",
            "metadata": {"source": "supervised"}
        }
    ]
    
    config = {
        "chunk_size": 500,
        "chunk_overlap": 100,
        "rag_technique": "rag_fusion",
        "top_k": 3
    }
    
    print("Ingesting with RAG-Fusion config...")
    client.ingest_documents(
        documents=documents,
        collection_name="ml_docs",
        config=config
    )
    
    print("\nQuerying with RAG-Fusion...")
    response = client.query(
        question="How do machines learn?",
        collection_name="ml_docs"
    )
    
    print(f"Answer: {response['answer']}")
    
    if 'queries_generated' in response.get('metadata', {}):
        print("\nGenerated Queries:")
        for i, q in enumerate(response['metadata']['queries_generated'], 1):
            print(f"  {i}. {q}")


def example_hyde():
    """Example: HyDE technique."""
    print("\n=== HyDE Example ===\n")
    
    client = RAGClient()
    
    documents = [
        {
            "content": "FastAPI is a modern web framework for building APIs with Python 3.7+.",
            "metadata": {"source": "fastapi"}
        },
        {
            "content": "FastAPI provides automatic API documentation and data validation.",
            "metadata": {"source": "fastapi_features"}
        }
    ]
    
    client.ingest_documents(documents, "fastapi_docs")
    
    print("Querying with HyDE...")
    response = client.query(
        question="What are the benefits of FastAPI?",
        collection_name="fastapi_docs",
        config={"rag_technique": "hyde"}
    )
    
    print(f"Answer: {response['answer']}")
    
    if 'hypothetical_document' in response.get('metadata', {}):
        print(f"\nHypothetical doc (first 150 chars):")
        print(response['metadata']['hypothetical_document'][:150] + "...")


def example_custom_prompt():
    """Example: Custom prompt template."""
    print("\n=== Custom Prompt Template Example ===\n")
    
    client = RAGClient()
    
    # List available templates
    print("Available prompt templates:")
    templates = client.list_prompt_templates()
    for template in templates['templates']:
        print(f"  - {template['name']}: {template['description']}")
    
    # Use technical template
    custom_prompt = """You are a technical expert. Use the context to provide a detailed technical answer.

Context: {context}

Question: {question}

Technical Answer:"""
    
    documents = [
        {
            "content": "REST APIs use HTTP methods like GET, POST, PUT, DELETE for CRUD operations.",
            "metadata": {"source": "rest_api"}
        }
    ]
    
    client.ingest_documents(documents, "api_docs")
    
    print("\nQuerying with custom prompt...")
    response = client.query(
        question="Explain REST API methods",
        collection_name="api_docs",
        config={"prompt_template": custom_prompt}
    )
    
    print(f"Answer: {response['answer']}")


def example_model_selection():
    """Example: Different model selection."""
    print("\n=== Model Selection Example ===\n")
    
    client = RAGClient()
    
    # List available models
    print("Available models:")
    models = client.list_models()
    print(f"LLM models: {', '.join(models['llm_models'][:5])}...")
    print(f"Embedding models: {', '.join(models['embedding_models'][:5])}...")
    
    # Use different models
    documents = [
        {
            "content": "Docker containers provide isolated environments for applications.",
            "metadata": {"source": "docker"}
        }
    ]
    
    config = {
        "llm_model": "llama3.2:3b",
        "embedding_model": "nomic-embed-text",
        "temperature": 0.3
    }
    
    print(f"\nUsing LLM: {config['llm_model']}")
    print(f"Using Embeddings: {config['embedding_model']}")
    
    client.ingest_documents(documents, "docker_docs", config)
    response = client.query("What is Docker?", "docker_docs")
    print(f"Answer: {response['answer'][:100]}...")


def example_config_management():
    """Example: Configuration management."""
    print("\n=== Configuration Management Example ===\n")
    
    client = RAGClient()
    
    # Create collection
    documents = [{"content": "Test document", "metadata": {}}]
    client.ingest_documents(documents, "test_collection")
    
    # Get current config
    print("Current configuration:")
    config = client.get_config("test_collection")
    print(json.dumps(config['config'], indent=2))
    
    # Update config
    print("\nUpdating configuration...")
    new_config = {
        "llm_temperature": 0.7,
        "top_k": 5,
        "rag_technique": "multi_query"
    }
    
    result = client.update_config(new_config, "test_collection")
    print(f"✓ {result['message']}")
    
    # Verify update
    updated_config = client.get_config("test_collection")
    print(f"New temperature: {updated_config['config']['llm_temperature']}")
    print(f"New top_k: {updated_config['config']['top_k']}")


def example_collection_management():
    """Example: Collection management."""
    print("\n=== Collection Management Example ===\n")
    
    client = RAGClient()
    
    # Create multiple collections
    print("Creating collections...")
    for name in ["collection_a", "collection_b", "collection_c"]:
        client.ingest_documents(
            [{"content": f"Document in {name}", "metadata": {}}],
            name
        )
        print(f"✓ Created {name}")
    
    # List collections
    print("\nActive collections:")
    collections = client.list_collections()
    for col in collections['collections']:
        print(f"  - {col}")
    print(f"Total: {collections['count']}")
    
    # Delete a collection
    print("\nDeleting collection_b...")
    result = client.delete_collection("collection_b")
    print(f"✓ {result['message']}")
    
    # List again
    collections = client.list_collections()
    print(f"Remaining collections: {collections['count']}")


def example_health_check():
    """Example: Health check."""
    print("\n=== Health Check Example ===\n")
    
    client = RAGClient()
    
    # Check health
    health = client.health_check()
    print(f"Status: {health['status']}")
    print(f"LLM Available: {health['llm_available']}")
    print(f"Embeddings Available: {health['embedding_available']}")
    print(f"Vector Store Initialized: {health['vector_store_initialized']}")


def example_techniques_info():
    """Example: List RAG techniques."""
    print("\n=== RAG Techniques Information ===\n")
    
    client = RAGClient()
    
    techniques = client.list_techniques()
    
    for tech in techniques['techniques']:
        print(f"\n{tech['name'].upper()}")
        print(f"  Description: {tech['description']}")
        print(f"  Use Case: {tech['use_case']}")


def main():
    """Run all examples."""
    print("=" * 70)
    print("RAG API Client Examples")
    print("=" * 70)
    
    try:
        example_basic_workflow()
        
        example_rag_fusion()
        
        example_hyde()
        
        example_custom_prompt()
        
        example_model_selection()
        
        example_config_management()
        
        example_collection_management()
        
        example_health_check()
        
        example_techniques_info()
        
        print("\n" + "=" * 70)
        print("All examples completed successfully!")
        print("=" * 70)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API server.")
        print("Make sure the server is running at http://localhost:8000")
        print("Run: python main.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
