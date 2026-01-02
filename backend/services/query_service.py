"""
RAG query service with LLM integration.
Supports Ollama and OpenAI providers with configurable RAG techniques.

Note: This service uses VectorService for workspace-filtered retrieval.
For direct RAG engine access without workspace filtering, use rag_engine.py.
"""
from typing import List, Dict, Any, Optional
import asyncio
import structlog
from datetime import datetime

from core.config import get_settings
from services.vector_service import VectorService
from services.ollama_service import get_ollama_service

logger = structlog.get_logger()
settings = get_settings()


class LLMService:
    """
    Service for LLM interactions.
    Supports Ollama and OpenAI providers.
    """
    
    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or settings.LLM_PROVIDER
        self._ollama_service = None
        self._openai_client = None
        self._initialize()
    
    def _initialize(self):
        """Initialize the LLM provider."""
        if self.provider == "ollama":
            self._ollama_service = get_ollama_service()
            logger.info(f"LLM Service initialized with Ollama: {settings.OLLAMA_LLM_MODEL}")
        elif self.provider == "openai":
            import openai
            if settings.OPENAI_API_KEY:
                openai.api_key = settings.OPENAI_API_KEY
                self._openai_client = openai
                logger.info("LLM Service initialized with OpenAI")
            else:
                logger.warning("OpenAI API key not configured")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    async def generate_response(
        self, 
        prompt: str, 
        context: str = "", 
        max_tokens: int = None,
        temperature: float = None
    ) -> Dict[str, Any]:
        """Generate response using configured LLM."""
        try:
            max_tokens = max_tokens or settings.LLM_MAX_TOKENS
            temperature = temperature if temperature is not None else settings.LLM_TEMPERATURE
            
            if self.provider == "ollama":
                return await self._generate_ollama(prompt, context, temperature)
            else:
                return await self._generate_openai(prompt, context, max_tokens, temperature)
                
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": "I apologize, but I'm unable to generate a response at this time."
            }
    
    async def _generate_ollama(
        self, 
        prompt: str, 
        context: str, 
        temperature: float
    ) -> Dict[str, Any]:
        """Generate response using Ollama."""
        system_prompt = """You are a helpful AI assistant that answers questions based on the provided context. 
Always cite your sources when possible and be clear about what information comes from the context vs your general knowledge.
If the context doesn't contain enough information to answer the question, say so clearly.

IMPORTANT: When formatting your response:
- Use proper markdown formatting with line breaks
- For tables, put each row on a separate line:
  | Header1 | Header2 |
  |---------|---------|
  | Cell1   | Cell2   |
- Use bullet points for lists
- Use **bold** for emphasis"""
        
        if context:
            full_prompt = f"{system_prompt}\n\nContext:\n{context}\n\nQuestion: {prompt}\n\nAnswer:"
        else:
            full_prompt = f"{system_prompt}\n\nQuestion: {prompt}\n\nAnswer:"
        
        llm = self._ollama_service.get_llm(temperature=temperature)
        response = await asyncio.to_thread(llm.invoke, full_prompt)
        
        return {
            "success": True,
            "content": response,
            "model": settings.OLLAMA_LLM_MODEL,
            "provider": "ollama"
        }
    
    async def _generate_openai(
        self, 
        prompt: str, 
        context: str, 
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Generate response using OpenAI."""
        messages = [
            {
                "role": "system",
                "content": """You are a helpful AI assistant that answers questions based on the provided context. 
Always cite your sources when possible and be clear about what information comes from the context vs your general knowledge.
If the context doesn't contain enough information to answer the question, say so clearly.

IMPORTANT: When formatting your response:
- Use proper markdown formatting with line breaks
- For tables, put each row on a separate line:
  | Header1 | Header2 |
  |---------|---------|
  | Cell1   | Cell2   |
- Use bullet points for lists
- Use **bold** for emphasis"""
            }
        ]
        
        if context:
            messages.append({
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {prompt}"
            })
        else:
            messages.append({
                "role": "user",
                "content": prompt
            })
        
        response = await self._openai_client.ChatCompletion.acreate(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return {
            "success": True,
            "content": response.choices[0].message.content,
            "usage": response.usage._asdict() if response.usage else {},
            "model": settings.LLM_MODEL,
            "provider": "openai"
        }


class RAGQueryService:
    """
    Main RAG query service combining retrieval and generation.
    Supports multiple RAG techniques: standard, rag_fusion, hyde, multi_query.
    """
    
    def __init__(self):
        self.vector_service = VectorService()
        self.llm_service = LLMService()
        self._ollama_service = get_ollama_service() if settings.LLM_PROVIDER == "ollama" else None
    
    async def query(
        self, 
        question: str, 
        workspace_id: int, 
        k: int = 5, 
        include_sources: bool = True,
        rag_technique: str = None
    ) -> Dict[str, Any]:
        """
        Process a RAG query with configurable technique.
        
        Args:
            question: User question
            workspace_id: Workspace to search in
            k: Number of documents to retrieve
            include_sources: Whether to include source citations
            rag_technique: RAG technique to use (standard, rag_fusion, hyde, multi_query)
        """
        try:
            technique = rag_technique or settings.DEFAULT_RAG_TECHNIQUE
            logger.info(f"Processing RAG query for workspace {workspace_id} using technique: {technique}")
            
            # Select RAG technique
            if technique == "standard":
                result = await self._standard_rag(question, workspace_id, k)
            elif technique == "rag_fusion":
                result = await self._rag_fusion(question, workspace_id, k)
            elif technique == "hyde":
                result = await self._hyde_rag(question, workspace_id, k)
            elif technique == "multi_query":
                result = await self._multi_query_rag(question, workspace_id, k)
            else:
                result = await self._standard_rag(question, workspace_id, k)
            
            if not result["success"]:
                return result
            
            # Prepare sources for citation
            sources = []
            if include_sources and result.get("retrieved_docs"):
                sources = self._prepare_sources(result["retrieved_docs"])
            
            return {
                "success": True,
                "answer": result["answer"],
                "sources": sources,
                "context_used": result.get("context_used", True),
                "retrieved_docs_count": len(result.get("retrieved_docs", [])),
                "technique": technique,
                "model": result.get("model", "")
            }
            
        except Exception as e:
            logger.error(f"Error processing RAG query: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _standard_rag(
        self, 
        question: str, 
        workspace_id: int, 
        k: int
    ) -> Dict[str, Any]:
        """Standard RAG: retrieve then generate."""
        # Retrieve relevant documents
        retrieved_docs = await self.vector_service.search_documents(
            query=question,
            k=k,
            workspace_id=workspace_id
        )
        
        if not retrieved_docs:
            return {
                "success": True,
                "answer": "I couldn't find any relevant information in the knowledge base to answer your question.",
                "retrieved_docs": [],
                "context_used": False
            }
        
        # Prepare context from retrieved documents
        context = self._prepare_context(retrieved_docs)
        
        # Generate response using LLM
        llm_response = await self.llm_service.generate_response(
            prompt=question,
            context=context
        )
        
        if not llm_response["success"]:
            return {
                "success": False,
                "error": llm_response.get("error", "Failed to generate response")
            }
        
        return {
            "success": True,
            "answer": llm_response["content"],
            "retrieved_docs": retrieved_docs,
            "context_used": True,
            "model": llm_response.get("model", "")
        }
    
    async def _rag_fusion(
        self, 
        question: str, 
        workspace_id: int, 
        k: int
    ) -> Dict[str, Any]:
        """
        RAG-Fusion: Generate multiple query variations and fuse results.
        Improves retrieval by generating diverse query perspectives.
        """
        # Generate multiple query variations
        query_prompt = f"""Generate 3 different versions of the following question to retrieve relevant documents.
Provide these alternative questions separated by newlines.

Original question: {question}

Alternative questions:"""
        
        llm_response = await self.llm_service.generate_response(prompt=query_prompt, context="")
        
        if not llm_response["success"]:
            # Fallback to standard RAG
            return await self._standard_rag(question, workspace_id, k)
        
        # Parse generated queries
        queries = [question] + [q.strip() for q in llm_response["content"].split("\n") if q.strip()]
        queries = queries[:4]  # Limit to 4 queries
        
        logger.info(f"RAG-Fusion generated {len(queries)} queries")
        
        # Retrieve documents for each query
        all_docs = []
        seen_ids = set()
        
        for query in queries:
            docs = await self.vector_service.search_documents(
                query=query,
                k=k,
                workspace_id=workspace_id
            )
            for doc in docs:
                doc_id = doc.get('id')
                if doc_id and doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    all_docs.append(doc)
        
        if not all_docs:
            return {
                "success": True,
                "answer": "I couldn't find any relevant information in the knowledge base to answer your question.",
                "retrieved_docs": [],
                "context_used": False
            }
        
        # Sort by score and take top k
        all_docs.sort(key=lambda x: x.get('score', 0), reverse=True)
        top_docs = all_docs[:k]
        
        # Generate answer
        context = self._prepare_context(top_docs)
        answer_response = await self.llm_service.generate_response(
            prompt=question,
            context=context
        )
        
        if not answer_response["success"]:
            return {
                "success": False,
                "error": answer_response.get("error", "Failed to generate response")
            }
        
        return {
            "success": True,
            "answer": answer_response["content"],
            "retrieved_docs": top_docs,
            "context_used": True,
            "model": answer_response.get("model", ""),
            "queries_used": queries
        }
    
    async def _hyde_rag(
        self, 
        question: str, 
        workspace_id: int, 
        k: int
    ) -> Dict[str, Any]:
        """
        HyDE (Hypothetical Document Embeddings): Generate hypothetical answer first,
        then use it to retrieve relevant documents.
        """
        # Generate hypothetical document
        hyde_prompt = f"""Please write a detailed passage to answer the following question. 
The passage should be informative and contain relevant information.

Question: {question}

Passage:"""
        
        llm_response = await self.llm_service.generate_response(prompt=hyde_prompt, context="")
        
        if not llm_response["success"]:
            # Fallback to standard RAG
            return await self._standard_rag(question, workspace_id, k)
        
        hypothetical_doc = llm_response["content"]
        logger.info(f"HyDE generated hypothetical document: {len(hypothetical_doc)} chars")
        
        # Use hypothetical document to retrieve
        retrieved_docs = await self.vector_service.search_documents(
            query=hypothetical_doc,
            k=k,
            workspace_id=workspace_id
        )
        
        if not retrieved_docs:
            return {
                "success": True,
                "answer": "I couldn't find any relevant information in the knowledge base to answer your question.",
                "retrieved_docs": [],
                "context_used": False
            }
        
        # Generate final answer using retrieved context
        context = self._prepare_context(retrieved_docs)
        answer_response = await self.llm_service.generate_response(
            prompt=question,
            context=context
        )
        
        if not answer_response["success"]:
            return {
                "success": False,
                "error": answer_response.get("error", "Failed to generate response")
            }
        
        return {
            "success": True,
            "answer": answer_response["content"],
            "retrieved_docs": retrieved_docs,
            "context_used": True,
            "model": answer_response.get("model", ""),
            "hypothetical_document": hypothetical_doc
        }
    
    async def _multi_query_rag(
        self, 
        question: str, 
        workspace_id: int, 
        k: int
    ) -> Dict[str, Any]:
        """
        Multi-Query RAG: Generate multiple perspectives and retrieve for each.
        Similar to RAG-Fusion but with different query generation strategy.
        """
        # Generate multiple perspectives
        multi_query_prompt = f"""You are an AI assistant. Generate 3 different versions of the given question 
to retrieve relevant documents from a knowledge base. By generating multiple perspectives, 
help overcome limitations of distance-based similarity search.

Provide these alternative questions separated by newlines.

Original question: {question}

Alternative questions:"""
        
        llm_response = await self.llm_service.generate_response(prompt=multi_query_prompt, context="")
        
        if not llm_response["success"]:
            return await self._standard_rag(question, workspace_id, k)
        
        queries = [question] + [q.strip() for q in llm_response["content"].split("\n") if q.strip()]
        queries = queries[:4]
        
        # Retrieve and combine
        all_docs = []
        seen_ids = set()
        
        for query in queries:
            docs = await self.vector_service.search_documents(
                query=query,
                k=k,
                workspace_id=workspace_id
            )
            for doc in docs:
                doc_id = doc.get('id')
                if doc_id and doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    all_docs.append(doc)
        
        if not all_docs:
            return {
                "success": True,
                "answer": "I couldn't find any relevant information in the knowledge base to answer your question.",
                "retrieved_docs": [],
                "context_used": False
            }
        
        # Sort and take top k
        all_docs.sort(key=lambda x: x.get('score', 0), reverse=True)
        top_docs = all_docs[:k]
        
        # Generate answer
        context = self._prepare_context(top_docs)
        answer_response = await self.llm_service.generate_response(
            prompt=question,
            context=context
        )
        
        if not answer_response["success"]:
            return {
                "success": False,
                "error": answer_response.get("error", "Failed to generate response")
            }
        
        return {
            "success": True,
            "answer": answer_response["content"],
            "retrieved_docs": top_docs,
            "context_used": True,
            "model": answer_response.get("model", ""),
            "queries_used": queries
        }
    
    def _prepare_context(
        self, 
        retrieved_docs: List[Dict[str, Any]], 
        max_context_length: int = 4000
    ) -> str:
        """Prepare context string from retrieved documents."""
        context_parts = []
        current_length = 0
        
        for i, doc in enumerate(retrieved_docs):
            doc_context = f"Source {i+1} - {doc.get('title', 'Unknown')}:\n{doc.get('content', '')}\n"
            
            if current_length + len(doc_context) > max_context_length:
                break
            
            context_parts.append(doc_context)
            current_length += len(doc_context)
        
        return "\n---\n".join(context_parts)
    
    def _prepare_sources(self, retrieved_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare source citations from retrieved documents with navigation info."""
        sources = []
        
        for i, doc in enumerate(retrieved_docs):
            metadata = doc.get('metadata', {})
            
            source = {
                "id": i + 1,
                "title": doc.get('title', 'Unknown'),
                "source": doc.get('source', ''),
                "score": round(doc.get('score', 0.0), 3),
                "content_preview": doc.get('content', '')[:200] + "..." if len(doc.get('content', '')) > 200 else doc.get('content', ''),
                # Citation navigation fields
                "document_id": doc.get('document_id') or metadata.get('document_id'),
                "chunk_id": doc.get('chunk_id') or metadata.get('chunk_id'),
                "start_line": doc.get('start_line') or metadata.get('start_line'),
                "end_line": doc.get('end_line') or metadata.get('end_line'),
                "page_number": metadata.get('page_number'),
                "file_path": doc.get('source') or metadata.get('file_path', '')
            }
            
            # Add additional metadata if available
            if 'repo_url' in metadata:
                source['repo_url'] = metadata['repo_url']
            if 'page_url' in metadata:
                source['page_url'] = metadata['page_url']
            
            # JIRA metadata
            if metadata.get('issue_key') or metadata.get('project_key'):
                source['issue_key'] = metadata.get('issue_key')
                source['issue_type'] = metadata.get('issue_type')
                source['issue_status'] = metadata.get('status')
                source['issue_url'] = metadata.get('issue_url')
                source['project_key'] = metadata.get('project_key')
            
            # Confluence metadata
            if metadata.get('space_key') or metadata.get('page_id'):
                source['space_key'] = metadata.get('space_key')
                source['page_id'] = metadata.get('page_id')
                source['confluence_url'] = metadata.get('page_url')
            
            sources.append(source)
        
        return sources


class ChatService:
    """Service for managing chat sessions and history."""
    
    def __init__(self):
        self.rag_service = RAGQueryService()
    
    async def process_chat_message(
        self, 
        message: str, 
        session_id: int, 
        workspace_id: int, 
        user_id: int,
        rag_technique: str = None
    ) -> Dict[str, Any]:
        """Process a chat message with context awareness and configurable RAG technique."""
        try:
            from core.database import get_db, ChatSession, ChatMessage
            
            db = next(get_db())
            
            # Get chat session
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if not session:
                return {"success": False, "error": "Chat session not found"}
            
            # Store user message
            user_message = ChatMessage(
                session_id=session_id,
                role="user",
                content=message,
                message_metadata={"timestamp": datetime.utcnow().isoformat()}
            )
            db.add(user_message)
            db.flush()
            
            # Get recent chat history for context
            recent_messages = db.query(ChatMessage)\
                .filter(ChatMessage.session_id == session_id)\
                .order_by(ChatMessage.created_at.desc())\
                .limit(10)\
                .all()
            
            # Prepare enhanced query with chat context
            enhanced_query = self._enhance_query_with_context(message, recent_messages)
            
            # Process RAG query with technique
            rag_result = await self.rag_service.query(
                question=enhanced_query,
                workspace_id=workspace_id,
                rag_technique=rag_technique
            )
            
            if not rag_result["success"]:
                return rag_result
            
            # Store assistant response
            assistant_message = ChatMessage(
                session_id=session_id,
                role="assistant",
                content=rag_result["answer"],
                message_metadata={
                    "sources": rag_result.get("sources", []),
                    "retrieved_docs_count": rag_result.get("retrieved_docs_count", 0),
                    "technique": rag_result.get("technique", "standard"),
                    "model": rag_result.get("model", ""),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            db.add(assistant_message)
            db.commit()
            
            return {
                "success": True,
                "message_id": assistant_message.id,
                "answer": rag_result["answer"],
                "sources": rag_result.get("sources", []),
                "context_used": rag_result.get("context_used", False),
                "technique": rag_result.get("technique", "standard")
            }
            
        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            return {"success": False, "error": str(e)}
    
    def _enhance_query_with_context(
        self, 
        current_message: str, 
        recent_messages: List
    ) -> str:
        """Enhance current query with recent chat context."""
        if not recent_messages or len(recent_messages) <= 1:
            return current_message
        
        # Get last few exchanges (excluding current message)
        context_messages = []
        for msg in reversed(recent_messages[1:6]):  # Last 5 messages before current
            if msg.role in ["user", "assistant"]:
                context_messages.append(f"{msg.role}: {msg.content}")
        
        if context_messages:
            context_str = "\n".join(context_messages)
            enhanced_query = f"Previous conversation context:\n{context_str}\n\nCurrent question: {current_message}"
            return enhanced_query
        
        return current_message
    
    async def get_chat_history(self, session_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat history for a session."""
        try:
            from core.database import get_db, ChatMessage
            
            db = next(get_db())
            
            messages = db.query(ChatMessage)\
                .filter(ChatMessage.session_id == session_id)\
                .order_by(ChatMessage.created_at.asc())\
                .limit(limit)\
                .all()
            
            history = []
            for msg in messages:
                history.append({
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "metadata": msg.message_metadata or {},
                    "created_at": msg.created_at.isoformat()
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return []
