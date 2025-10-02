"""
Quick installation test script for RAG engine.
Run this to verify your setup is working correctly.
"""
import sys
import subprocess


def check_python_version():
    """Check Python version."""
    print("Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro} (requires 3.10+)")
        return False


def check_ollama():
    """Check if Ollama is installed and running."""
    print("\nChecking Ollama...")
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("✓ Ollama is installed and running")
            return True
        else:
            print("✗ Ollama is installed but not responding")
            return False
    except FileNotFoundError:
        print("✗ Ollama not found. Install from https://ollama.com")
        return False
    except subprocess.TimeoutExpired:
        print("✗ Ollama timeout. Try running 'ollama serve'")
        return False
    except Exception as e:
        print(f"✗ Error checking Ollama: {e}")
        return False


def check_ollama_models():
    """Check if required models are available."""
    print("\nChecking Ollama models...")
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        output = result.stdout.lower()
        
        # Check for LLM model
        llm_models = ["llama3.2", "llama3.1", "mistral", "phi3", "gemma"]
        has_llm = any(model in output for model in llm_models)
        
        if has_llm:
            print("✓ LLM model found")
        else:
            print("✗ No LLM model found. Run: ollama pull llama3.2:3b")
        
        # Check for embedding model
        has_embedding = "nomic-embed-text" in output or "mxbai-embed" in output
        
        if has_embedding:
            print("✓ Embedding model found")
        else:
            print("✗ No embedding model found. Run: ollama pull nomic-embed-text")
        
        return has_llm and has_embedding
        
    except Exception as e:
        print(f"✗ Error checking models: {e}")
        return False


def check_dependencies():
    """Check if required Python packages are installed."""
    print("\nChecking Python dependencies...")
    
    required_packages = [
        "fastapi",
        "langchain",
        "langchain_ollama",
        "chromadb",
        "structlog"
    ]
    
    missing = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package}")
            missing.append(package)
    
    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    return True


def test_rag_engine():
    """Test RAG engine initialization."""
    print("\nTesting RAG engine initialization...")
    
    try:
        from services.rag_engine import RAGEngine, RAGConfig
        
        config = RAGConfig(
            llm_model="llama3.2:3b",
            embedding_model="nomic-embed-text"
        )
        
        engine = RAGEngine(config)
        
        if engine.llm and engine.embeddings:
            print("✓ RAG engine initialized successfully")
            return True
        else:
            print("✗ RAG engine initialization incomplete")
            return False
            
    except Exception as e:
        print(f"✗ RAG engine initialization failed: {e}")
        return False


def test_api_import():
    """Test API routes import."""
    print("\nTesting API imports...")
    
    try:
        from api.routes import rag
        from api.schemas import rag_schemas
        
        print("✓ API routes and schemas imported successfully")
        return True
        
    except Exception as e:
        print(f"✗ API import failed: {e}")
        return False


def main():
    """Run all checks."""
    print("=" * 70)
    print("RAG Engine Installation Test")
    print("=" * 70)
    
    results = []
    
    # Run checks
    results.append(("Python Version", check_python_version()))
    results.append(("Ollama Installation", check_ollama()))
    results.append(("Ollama Models", check_ollama_models()))
    results.append(("Python Dependencies", check_dependencies()))
    results.append(("RAG Engine", test_rag_engine()))
    results.append(("API Imports", test_api_import()))
    
    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 All checks passed! Your installation is ready.")
        print("\nNext steps:")
        print("1. Start the server: python main.py")
        print("2. Visit: http://localhost:8000/docs")
        print("3. Try examples: python examples/api_client_example.py")
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("\nQuick fixes:")
        print("- Install Ollama: curl -fsSL https://ollama.com/install.sh | sh")
        print("- Pull models: ollama pull llama3.2:3b && ollama pull nomic-embed-text")
        print("- Install deps: pip install -r requirements.txt")
    
    print("=" * 70)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
