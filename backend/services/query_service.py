"""
RAG query service with LLM integration.
"""
from typing import List, Dict, Any, Optional
import openai
import structlog
from datetime import datetime

from core.config import get_settings
from services.vector_service import VectorService

logger = structlog.get_logger()
settings = get_settings()

class LLMService:
    """Service for LLM interactions."""
    
    def __init__(self):
        if settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY
        else:
            logger.warning("OpenAI API key not configured")
    
    async def generate_response(self, prompt: str, context: str = "", 
                              max_tokens: int = None) -> Dict[str, Any]:
        """Generate response using LLM."""
        try:
            max_tokens = max_tokens or settings.LLM_MAX_TOKENS
            
            messages = [
                {
                    "role": "system",
                    "content": """You are a helpful AI assistant that answers questions based on the provided context. 
                    Always cite your sources when possible and be clear about what information comes from the context vs your general knowledge.
                    If the context doesn't contain enough information to answer the question, say so clearly."""
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
            
            response = await openai.ChatCompletion.acreate(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=max_tokens
            )
            
            return {
                "success": True,
                "content": response.choices[0].message.content,
                "usage": response.usage._asdict() if response.usage else {},
                "model": settings.LLM_MODEL
            }
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": "I apologize, but I'm unable to generate a response at this time."
            }

class RAGQueryService:
    """Main RAG query service combining retrieval and generation."""
    
    def __init__(self):
        self.vector_service = VectorService()
        self.llm_service = LLMService()
    
    async def query(self, question: str, workspace_id: int, 
                   k: int = 5, include_sources: bool = True) -> Dict[str, Any]:
        """Process a RAG query."""
        try:
            logger.info(f"Processing RAG query for workspace {workspace_id}")
            
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
                    "sources": [],
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
            
            # Prepare sources for citation
            sources = []
            if include_sources:
                sources = self._prepare_sources(retrieved_docs)
            
            return {
                "success": True,
                "answer": llm_response["content"],
                "sources": sources,
                "context_used": True,
                "retrieved_docs_count": len(retrieved_docs),
                "usage": llm_response.get("usage", {}),
                "model": llm_response.get("model", "")
            }
            
        except Exception as e:
            logger.error(f"Error processing RAG query: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _prepare_context(self, retrieved_docs: List[Dict[str, Any]], 
                        max_context_length: int = 4000) -> str:
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
        """Prepare source citations from retrieved documents."""
        sources = []
        
        for i, doc in enumerate(retrieved_docs):
            source = {
                "id": i + 1,
                "title": doc.get('title', 'Unknown'),
                "source": doc.get('source', ''),
                "score": round(doc.get('score', 0.0), 3),
                "content_preview": doc.get('content', '')[:200] + "..." if len(doc.get('content', '')) > 200 else doc.get('content', '')
            }
            
            # Add metadata if available
            metadata = doc.get('metadata', {})
            if 'repo_url' in metadata:
                source['repo_url'] = metadata['repo_url']
            if 'page_url' in metadata:
                source['page_url'] = metadata['page_url']
            if 'file_path' in metadata:
                source['file_path'] = metadata['file_path']
            
            sources.append(source)
        
        return sources

class ChatService:
    """Service for managing chat sessions and history."""
    
    def __init__(self):
        self.rag_service = RAGQueryService()
    
    async def process_chat_message(self, message: str, session_id: int, 
                                  workspace_id: int, user_id: int) -> Dict[str, Any]:
        """Process a chat message with context awareness."""
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
                metadata={"timestamp": datetime.utcnow().isoformat()}
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
            
            # Process RAG query
            rag_result = await self.rag_service.query(
                question=enhanced_query,
                workspace_id=workspace_id
            )
            
            if not rag_result["success"]:
                return rag_result
            
            # Store assistant response
            assistant_message = ChatMessage(
                session_id=session_id,
                role="assistant",
                content=rag_result["answer"],
                metadata={
                    "sources": rag_result.get("sources", []),
                    "retrieved_docs_count": rag_result.get("retrieved_docs_count", 0),
                    "usage": rag_result.get("usage", {}),
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
                "context_used": rag_result.get("context_used", False)
            }
            
        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            return {"success": False, "error": str(e)}
    
    def _enhance_query_with_context(self, current_message: str, 
                                   recent_messages: List) -> str:
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
                    "metadata": msg.metadata or {},
                    "created_at": msg.created_at.isoformat()
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return []
