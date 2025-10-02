"""
Advanced RAG Engine with configurable LLM, embeddings, and retrieval strategies.
Supports RAG-Fusion, HyDE, and other advanced techniques.
"""
from typing import List, Dict, Any, Optional, Literal
from enum import Enum
import asyncio
from dataclasses import dataclass

from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain_community.vectorstores import Chroma, FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document
import structlog

logger = structlog.get_logger()


class EmbeddingStrategy(str, Enum):
    """Supported embedding strategies."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    SENTENCE_TRANSFORMERS = "sentence_transformers"


class RetrievalStrategy(str, Enum):
    """Supported retrieval strategies."""
    SIMILARITY = "similarity"
    MMR = "mmr"  # Maximum Marginal Relevance
    SIMILARITY_SCORE_THRESHOLD = "similarity_score_threshold"


class RAGTechnique(str, Enum):
    """Advanced RAG techniques."""
    STANDARD = "standard"
    RAG_FUSION = "rag_fusion"
    HYDE = "hyde"  # Hypothetical Document Embeddings
    MULTI_QUERY = "multi_query"
    CONTEXTUAL_COMPRESSION = "contextual_compression"


@dataclass
class RAGConfig:
    """Configuration for RAG engine."""
    # LLM Configuration
    llm_model: str = "llama3.2:3b"
    llm_temperature: float = 0.0
    llm_base_url: Optional[str] = None
    
    # Embedding Configuration
    embedding_model: str = "nomic-embed-text"
    embedding_strategy: EmbeddingStrategy = EmbeddingStrategy.OLLAMA
    embedding_base_url: Optional[str] = None
    
    # Chunking Configuration
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    # Retrieval Configuration
    retrieval_strategy: RetrievalStrategy = RetrievalStrategy.SIMILARITY
    top_k: int = 4
    score_threshold: Optional[float] = None
    
    # RAG Technique
    rag_technique: RAGTechnique = RAGTechnique.STANDARD
    
    # Prompt Template
    prompt_template: Optional[str] = None
    
    # Vector Store Configuration
    vector_store_type: Literal["chroma", "faiss"] = "chroma"
    persist_directory: Optional[str] = None


class RAGEngine:
    """
    Advanced RAG Engine with support for multiple LLMs, embeddings, and techniques.
    """
    
    def __init__(self, config: RAGConfig):
        """Initialize RAG engine with configuration."""
        self.config = config
        self.llm = None
        self.embeddings = None
        self.vectorstore = None
        self.retriever = None
        self.text_splitter = None
        
        self._initialize_components()
        
    def _initialize_components(self):
        """Initialize LLM, embeddings, and other components."""
        # Initialize LLM
        self.llm = self._create_llm()
        
        # Initialize embeddings
        self.embeddings = self._create_embeddings()
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap
        )
        
        logger.info(
            "RAG engine initialized",
            llm_model=self.config.llm_model,
            embedding_model=self.config.embedding_model,
            technique=self.config.rag_technique.value
        )
    
    def _create_llm(self):
        """Create LLM instance based on configuration."""
        llm_kwargs = {
            "model": self.config.llm_model,
            "temperature": self.config.llm_temperature,
        }
        
        if self.config.llm_base_url:
            llm_kwargs["base_url"] = self.config.llm_base_url
            
        return OllamaLLM(**llm_kwargs)
    
    def _create_embeddings(self):
        """Create embeddings instance based on configuration."""
        if self.config.embedding_strategy == EmbeddingStrategy.OLLAMA:
            emb_kwargs = {"model": self.config.embedding_model}
            if self.config.embedding_base_url:
                emb_kwargs["base_url"] = self.config.embedding_base_url
            return OllamaEmbeddings(**emb_kwargs)
        
        elif self.config.embedding_strategy == EmbeddingStrategy.OPENAI:
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(model=self.config.embedding_model)
        
        elif self.config.embedding_strategy == EmbeddingStrategy.SENTENCE_TRANSFORMERS:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            return HuggingFaceEmbeddings(model_name=self.config.embedding_model)
        
        else:
            raise ValueError(f"Unsupported embedding strategy: {self.config.embedding_strategy}")
    
    def _get_default_prompt_template(self) -> str:
        """Get default RAG prompt template."""
        return """You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer concise.

Question: {question}

Context: {context}

Answer:"""
    
    def _create_prompt(self) -> ChatPromptTemplate:
        """Create prompt template."""
        template = self.config.prompt_template or self._get_default_prompt_template()
        return ChatPromptTemplate.from_template(template)
    
    async def ingest_documents(
        self,
        documents: List[Document],
        collection_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingest documents into vector store.
        
        Args:
            documents: List of documents to ingest
            collection_name: Optional collection name for organization
            
        Returns:
            Dictionary with ingestion statistics
        """
        try:
            # Split documents
            splits = self.text_splitter.split_documents(documents)
            
            logger.info(
                "Documents split",
                original_count=len(documents),
                split_count=len(splits)
            )
            
            # Create vector store
            if self.config.vector_store_type == "chroma":
                self.vectorstore = Chroma.from_documents(
                    documents=splits,
                    embedding=self.embeddings,
                    collection_name=collection_name or "default",
                    persist_directory=self.config.persist_directory
                )
            elif self.config.vector_store_type == "faiss":
                self.vectorstore = FAISS.from_documents(
                    documents=splits,
                    embedding=self.embeddings
                )
                if self.config.persist_directory:
                    self.vectorstore.save_local(self.config.persist_directory)
            
            # Create retriever
            self._create_retriever()
            
            return {
                "status": "success",
                "documents_ingested": len(documents),
                "chunks_created": len(splits),
                "collection_name": collection_name or "default"
            }
            
        except Exception as e:
            logger.error("Document ingestion failed", error=str(e))
            raise
    
    def _create_retriever(self):
        """Create retriever based on configuration."""
        if not self.vectorstore:
            raise ValueError("Vector store not initialized. Ingest documents first.")
        
        search_kwargs = {"k": self.config.top_k}
        
        if self.config.retrieval_strategy == RetrievalStrategy.SIMILARITY:
            self.retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs=search_kwargs
            )
        elif self.config.retrieval_strategy == RetrievalStrategy.MMR:
            self.retriever = self.vectorstore.as_retriever(
                search_type="mmr",
                search_kwargs=search_kwargs
            )
        elif self.config.retrieval_strategy == RetrievalStrategy.SIMILARITY_SCORE_THRESHOLD:
            if self.config.score_threshold:
                search_kwargs["score_threshold"] = self.config.score_threshold
            self.retriever = self.vectorstore.as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs=search_kwargs
            )
    
    async def query(self, question: str) -> Dict[str, Any]:
        """
        Query the RAG system.
        
        Args:
            question: User question
            
        Returns:
            Dictionary with answer and metadata
        """
        if not self.retriever:
            raise ValueError("Retriever not initialized. Ingest documents first.")
        
        try:
            # Select RAG technique
            if self.config.rag_technique == RAGTechnique.STANDARD:
                result = await self._standard_rag(question)
            elif self.config.rag_technique == RAGTechnique.RAG_FUSION:
                result = await self._rag_fusion(question)
            elif self.config.rag_technique == RAGTechnique.HYDE:
                result = await self._hyde_rag(question)
            elif self.config.rag_technique == RAGTechnique.MULTI_QUERY:
                result = await self._multi_query_rag(question)
            else:
                result = await self._standard_rag(question)
            
            return result
            
        except Exception as e:
            logger.error("Query failed", error=str(e), question=question)
            raise
    
    async def _standard_rag(self, question: str) -> Dict[str, Any]:
        """Standard RAG implementation."""
        # Retrieve documents
        docs = await asyncio.to_thread(self.retriever.invoke, question)
        
        # Format context
        context = self._format_docs(docs)
        
        # Create chain
        prompt = self._create_prompt()
        chain = prompt | self.llm | StrOutputParser()
        
        # Generate answer
        answer = await asyncio.to_thread(
            chain.invoke,
            {"context": context, "question": question}
        )
        
        return {
            "answer": answer,
            "source_documents": [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata
                }
                for doc in docs
            ],
            "technique": "standard"
        }
    
    async def _rag_fusion(self, question: str) -> Dict[str, Any]:
        """
        RAG-Fusion: Generate multiple queries and fuse results.
        Improves retrieval by generating diverse query perspectives.
        """
        # Generate multiple query variations
        query_generation_prompt = PromptTemplate(
            input_variables=["question"],
            template="""You are a helpful assistant that generates multiple search queries based on a single input query.
Generate 3 different versions of the given question to retrieve relevant documents from a vector database.
Provide these alternative questions separated by newlines.

Original question: {question}

Alternative questions:"""
        )
        
        query_chain = query_generation_prompt | self.llm | StrOutputParser()
        generated_queries = await asyncio.to_thread(query_chain.invoke, {"question": question})
        
        # Parse generated queries
        queries = [question] + [q.strip() for q in generated_queries.split("\n") if q.strip()]
        
        logger.info("RAG-Fusion queries generated", count=len(queries))
        
        # Retrieve documents for each query
        all_docs = []
        for query in queries[:4]:  # Limit to 4 queries
            docs = await asyncio.to_thread(self.retriever.invoke, query)
            all_docs.extend(docs)
        
        # Remove duplicates and rank
        unique_docs = self._deduplicate_documents(all_docs)
        top_docs = unique_docs[:self.config.top_k]
        
        # Format context and generate answer
        context = self._format_docs(top_docs)
        prompt = self._create_prompt()
        chain = prompt | self.llm | StrOutputParser()
        
        answer = await asyncio.to_thread(
            chain.invoke,
            {"context": context, "question": question}
        )
        
        return {
            "answer": answer,
            "source_documents": [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata
                }
                for doc in top_docs
            ],
            "technique": "rag_fusion",
            "queries_generated": queries
        }
    
    async def _hyde_rag(self, question: str) -> Dict[str, Any]:
        """
        HyDE (Hypothetical Document Embeddings): Generate hypothetical answer first,
        then use it to retrieve relevant documents.
        """
        # Generate hypothetical document
        hyde_prompt = PromptTemplate(
            input_variables=["question"],
            template="""Please write a passage to answer the question. The passage should be detailed and informative.

Question: {question}

Passage:"""
        )
        
        hyde_chain = hyde_prompt | self.llm | StrOutputParser()
        hypothetical_doc = await asyncio.to_thread(hyde_chain.invoke, {"question": question})
        
        logger.info("HyDE hypothetical document generated", length=len(hypothetical_doc))
        
        # Use hypothetical document to retrieve
        docs = await asyncio.to_thread(self.retriever.invoke, hypothetical_doc)
        
        # Format context and generate final answer
        context = self._format_docs(docs)
        prompt = self._create_prompt()
        chain = prompt | self.llm | StrOutputParser()
        
        answer = await asyncio.to_thread(
            chain.invoke,
            {"context": context, "question": question}
        )
        
        return {
            "answer": answer,
            "source_documents": [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata
                }
                for doc in docs
            ],
            "technique": "hyde",
            "hypothetical_document": hypothetical_doc
        }
    
    async def _multi_query_rag(self, question: str) -> Dict[str, Any]:
        """
        Multi-Query RAG: Generate multiple perspectives and retrieve for each.
        Similar to RAG-Fusion but with different query generation strategy.
        """
        # Generate multiple perspectives
        multi_query_prompt = PromptTemplate(
            input_variables=["question"],
            template="""You are an AI language model assistant. Your task is to generate 3 different versions of the given user question to retrieve relevant documents from a vector database. By generating multiple perspectives on the user question, your goal is to help the user overcome some of the limitations of distance-based similarity search.

Provide these alternative questions separated by newlines.

Original question: {question}

Alternative questions:"""
        )
        
        query_chain = multi_query_prompt | self.llm | StrOutputParser()
        generated_queries = await asyncio.to_thread(query_chain.invoke, {"question": question})
        
        queries = [question] + [q.strip() for q in generated_queries.split("\n") if q.strip()]
        
        # Retrieve and combine
        all_docs = []
        for query in queries[:4]:
            docs = await asyncio.to_thread(self.retriever.invoke, query)
            all_docs.extend(docs)
        
        unique_docs = self._deduplicate_documents(all_docs)
        top_docs = unique_docs[:self.config.top_k]
        
        # Generate answer
        context = self._format_docs(top_docs)
        prompt = self._create_prompt()
        chain = prompt | self.llm | StrOutputParser()
        
        answer = await asyncio.to_thread(
            chain.invoke,
            {"context": context, "question": question}
        )
        
        return {
            "answer": answer,
            "source_documents": [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata
                }
                for doc in top_docs
            ],
            "technique": "multi_query",
            "queries_used": queries
        }
    
    def _format_docs(self, docs: List[Document]) -> str:
        """Format documents for context."""
        return "\n\n".join(doc.page_content for doc in docs)
    
    def _deduplicate_documents(self, docs: List[Document]) -> List[Document]:
        """Remove duplicate documents based on content."""
        seen = set()
        unique_docs = []
        
        for doc in docs:
            content_hash = hash(doc.page_content)
            if content_hash not in seen:
                seen.add(content_hash)
                unique_docs.append(doc)
        
        return unique_docs
    
    def update_config(self, **kwargs):
        """Update configuration dynamically."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # Reinitialize components if needed
        if any(k in kwargs for k in ['llm_model', 'llm_temperature', 'llm_base_url']):
            self.llm = self._create_llm()
        
        if any(k in kwargs for k in ['embedding_model', 'embedding_strategy', 'embedding_base_url']):
            self.embeddings = self._create_embeddings()
        
        if any(k in kwargs for k in ['chunk_size', 'chunk_overlap']):
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap
            )
        
        if any(k in kwargs for k in ['retrieval_strategy', 'top_k', 'score_threshold']):
            if self.vectorstore:
                self._create_retriever()
        
        logger.info("RAG engine configuration updated", updated_fields=list(kwargs.keys()))
