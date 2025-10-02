"""
Example script demonstrating RAG engine usage.
"""
import asyncio
from services.rag_engine import RAGEngine, RAGConfig, RAGTechnique, EmbeddingStrategy, RetrievalStrategy
from langchain_core.documents import Document


async def example_standard_rag():
    """Example: Standard RAG."""
    print("\n=== Standard RAG Example ===\n")
    
    # Create RAG engine with default config
    config = RAGConfig(
        llm_model="llama3.2:3b",
        embedding_model="nomic-embed-text",
        chunk_size=1000,
        chunk_overlap=200,
        rag_technique=RAGTechnique.STANDARD
    )
    
    engine = RAGEngine(config)
    
    # Sample documents about AI agents
    documents = [
        Document(
            page_content="""
            Task Decomposition is the process of breaking a complex task into smaller, 
            manageable sub-steps or subgoals. It can be prompted directly to a language 
            model (e.g., "Steps for XYZ"), guided by task-specific instructions, or 
            assisted by human input. Techniques like Chain-of-Thought and Tree-of-Thought 
            use this decomposition to improve reasoning and interpretability.
            """,
            metadata={"source": "ai_agents_doc", "section": "planning"}
        ),
        Document(
            page_content="""
            Chain of Thought (CoT) has become a standard prompting technique for enhancing 
            model performance on complex tasks. The model is instructed to "think step by step" 
            to utilize more test-time computation to decompose hard tasks into smaller and 
            simpler steps.
            """,
            metadata={"source": "ai_agents_doc", "section": "techniques"}
        ),
        Document(
            page_content="""
            Tree of Thoughts extends CoT by exploring multiple reasoning possibilities at 
            each step. It first decomposes the problem into multiple thought steps and 
            generates multiple thoughts per step, creating a tree structure.
            """,
            metadata={"source": "ai_agents_doc", "section": "advanced_techniques"}
        )
    ]
    
    # Ingest documents
    print("Ingesting documents...")
    result = await engine.ingest_documents(documents, collection_name="ai_agents")
    print(f"✓ Ingested {result['documents_ingested']} documents, created {result['chunks_created']} chunks")
    
    # Query
    print("\nQuerying: 'What is Task Decomposition?'")
    response = await engine.query("What is Task Decomposition?")
    
    print(f"\nAnswer:\n{response['answer']}")
    print(f"\nTechnique: {response['technique']}")
    print(f"\nSource Documents: {len(response['source_documents'])}")


async def example_rag_fusion():
    """Example: RAG-Fusion technique."""
    print("\n=== RAG-Fusion Example ===\n")
    
    config = RAGConfig(
        llm_model="llama3.2:3b",
        rag_technique=RAGTechnique.RAG_FUSION,
        top_k=3
    )
    
    engine = RAGEngine(config)
    
    documents = [
        Document(
            page_content="Python is a high-level programming language known for its simplicity and readability.",
            metadata={"source": "python_intro"}
        ),
        Document(
            page_content="Python supports multiple programming paradigms including procedural, object-oriented, and functional programming.",
            metadata={"source": "python_features"}
        ),
        Document(
            page_content="Python has a large standard library and extensive ecosystem of third-party packages.",
            metadata={"source": "python_ecosystem"}
        ),
        Document(
            page_content="Python is widely used in web development, data science, machine learning, and automation.",
            metadata={"source": "python_applications"}
        )
    ]
    
    print("Ingesting documents...")
    await engine.ingest_documents(documents, collection_name="python_docs")
    
    print("\nQuerying with RAG-Fusion: 'What makes Python popular?'")
    response = await engine.query("What makes Python popular?")
    
    print(f"\nAnswer:\n{response['answer']}")
    print(f"\nGenerated Queries:")
    for i, query in enumerate(response.get('metadata', {}).get('queries_generated', []), 1):
        print(f"  {i}. {query}")


async def example_hyde():
    """Example: HyDE technique."""
    print("\n=== HyDE (Hypothetical Document Embeddings) Example ===\n")
    
    config = RAGConfig(
        llm_model="llama3.2:3b",
        rag_technique=RAGTechnique.HYDE,
        top_k=4
    )
    
    engine = RAGEngine(config)
    
    documents = [
        Document(
            page_content="Machine learning is a subset of AI that enables systems to learn from data without explicit programming.",
            metadata={"source": "ml_basics"}
        ),
        Document(
            page_content="Deep learning uses neural networks with multiple layers to learn hierarchical representations of data.",
            metadata={"source": "deep_learning"}
        ),
        Document(
            page_content="Supervised learning trains models on labeled data to make predictions on new, unseen data.",
            metadata={"source": "supervised_learning"}
        ),
        Document(
            page_content="Reinforcement learning involves agents learning to make decisions by interacting with an environment.",
            metadata={"source": "reinforcement_learning"}
        )
    ]
    
    print("Ingesting documents...")
    await engine.ingest_documents(documents, collection_name="ml_docs")
    
    print("\nQuerying with HyDE: 'How do machines learn?'")
    response = await engine.query("How do machines learn?")
    
    print(f"\nAnswer:\n{response['answer']}")
    print(f"\nHypothetical Document (first 200 chars):")
    print(f"{response.get('metadata', {}).get('hypothetical_document', '')[:200]}...")


async def example_custom_prompt():
    """Example: Custom prompt template."""
    print("\n=== Custom Prompt Template Example ===\n")
    
    custom_prompt = """You are a helpful coding assistant. Based on the documentation below, provide a clear and practical answer with code examples if relevant.

Documentation: {context}

Question: {question}

Answer with code examples:"""
    
    config = RAGConfig(
        llm_model="llama3.2:3b",
        prompt_template=custom_prompt,
        chunk_size=500
    )
    
    engine = RAGEngine(config)
    
    documents = [
        Document(
            page_content="To create a list in Python, use square brackets: my_list = [1, 2, 3]. Lists are mutable and can contain mixed types.",
            metadata={"source": "python_lists"}
        ),
        Document(
            page_content="List comprehensions provide a concise way to create lists: squares = [x**2 for x in range(10)]",
            metadata={"source": "python_comprehensions"}
        )
    ]
    
    print("Ingesting documents...")
    await engine.ingest_documents(documents, collection_name="code_docs")
    
    print("\nQuerying with custom prompt: 'How do I create a list in Python?'")
    response = await engine.query("How do I create a list in Python?")
    
    print(f"\nAnswer:\n{response['answer']}")


async def example_different_embeddings():
    """Example: Different embedding strategies."""
    print("\n=== Different Embedding Strategies Example ===\n")
    
    # Ollama embeddings
    config_ollama = RAGConfig(
        embedding_strategy=EmbeddingStrategy.OLLAMA,
        embedding_model="nomic-embed-text"
    )
    
    print("Using Ollama embeddings (nomic-embed-text)")
    engine = RAGEngine(config_ollama)
    
    documents = [
        Document(
            page_content="FastAPI is a modern, fast web framework for building APIs with Python.",
            metadata={"source": "fastapi_intro"}
        )
    ]
    
    await engine.ingest_documents(documents, collection_name="fastapi_docs")
    response = await engine.query("What is FastAPI?")
    print(f"Answer: {response['answer'][:100]}...")


async def example_retrieval_strategies():
    """Example: Different retrieval strategies."""
    print("\n=== Retrieval Strategies Example ===\n")
    
    documents = [
        Document(page_content=f"Document {i} about various topics in AI and machine learning.", metadata={"id": i})
        for i in range(10)
    ]
    
    # Similarity search
    print("1. Similarity Search")
    config = RAGConfig(retrieval_strategy=RetrievalStrategy.SIMILARITY, top_k=3)
    engine = RAGEngine(config)
    await engine.ingest_documents(documents, collection_name="test_docs")
    
    # MMR (Maximum Marginal Relevance)
    print("2. MMR (Maximum Marginal Relevance) - reduces redundancy")
    config.retrieval_strategy = RetrievalStrategy.MMR
    engine.update_config(retrieval_strategy=RetrievalStrategy.MMR)


async def main():
    """Run all examples."""
    print("=" * 70)
    print("RAG Engine Examples")
    print("=" * 70)
    
    try:
        await example_standard_rag()
        await asyncio.sleep(1)
        
        await example_rag_fusion()
        await asyncio.sleep(1)
        
        await example_hyde()
        await asyncio.sleep(1)
        
        await example_custom_prompt()
        await asyncio.sleep(1)
        
        await example_different_embeddings()
        await asyncio.sleep(1)
        
        await example_retrieval_strategies()
        
        print("\n" + "=" * 70)
        print("All examples completed successfully!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
