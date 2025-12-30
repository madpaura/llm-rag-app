"""
Query and chat endpoints for RAG functionality.
"""
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import structlog
import json

from core.database import get_db, ChatSession, Workspace
from services.query_service import RAGQueryService, ChatService

logger = structlog.get_logger()
router = APIRouter()
security = HTTPBearer()

class QueryRequest(BaseModel):
    question: str
    workspace_id: int
    k: Optional[int] = 5
    rag_technique: Optional[str] = None  # standard, rag_fusion, hyde, multi_query

class QueryResponse(BaseModel):
    success: bool
    answer: str
    sources: List[Dict[str, Any]]
    context_used: bool
    retrieved_docs_count: int
    technique: Optional[str] = None

class ChatMessageRequest(BaseModel):
    message: str
    session_id: int
    rag_technique: Optional[str] = None  # standard, rag_fusion, hyde, multi_query

class ChatSessionCreate(BaseModel):
    workspace_id: int
    title: Optional[str] = None

@router.post("/search", response_model=QueryResponse)
async def search_knowledge_base(
    request: QueryRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Search the knowledge base with a question."""
    try:
        # TODO: Verify user access to workspace
        workspace = db.query(Workspace).filter(Workspace.id == request.workspace_id).first()
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        # Process RAG query
        rag_service = RAGQueryService()
        result = await rag_service.query(
            question=request.question,
            workspace_id=request.workspace_id,
            k=request.k,
            rag_technique=request.rag_technique
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Query processing failed")
            )
        
        return QueryResponse(
            success=True,
            answer=result["answer"],
            sources=result.get("sources", []),
            context_used=result.get("context_used", False),
            retrieved_docs_count=result.get("retrieved_docs_count", 0),
            technique=result.get("technique", "standard")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing search query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/chat/sessions")
async def create_chat_session(
    request: ChatSessionCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Create a new chat session."""
    try:
        # TODO: Get user from token
        user_id = 1  # Mock user ID
        
        # Verify workspace exists and user has access
        workspace = db.query(Workspace).filter(Workspace.id == request.workspace_id).first()
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        # Create chat session
        session = ChatSession(
            workspace_id=request.workspace_id,
            user_id=user_id,
            title=request.title or f"Chat Session - {workspace.name}"
        )
        db.add(session)
        db.commit()
        
        return {
            "id": session.id,
            "workspace_id": session.workspace_id,
            "title": session.title,
            "created_at": session.created_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating chat session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/chat/sessions/{workspace_id}")
async def get_chat_sessions(
    workspace_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get chat sessions for a workspace."""
    try:
        # TODO: Get user from token and verify access
        user_id = 1  # Mock user ID
        
        sessions = db.query(ChatSession)\
            .filter(ChatSession.workspace_id == workspace_id)\
            .filter(ChatSession.user_id == user_id)\
            .order_by(ChatSession.updated_at.desc())\
            .all()
        
        result = []
        for session in sessions:
            result.append({
                "id": session.id,
                "workspace_id": session.workspace_id,
                "title": session.title,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat() if session.updated_at else session.created_at.isoformat()
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting chat sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/chat/message")
async def send_chat_message(
    request: ChatMessageRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Send a message in a chat session."""
    try:
        # TODO: Get user from token
        user_id = 1  # Mock user ID
        
        # Get chat session and verify access
        session = db.query(ChatSession).filter(ChatSession.id == request.session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to chat session"
            )
        
        # Process chat message
        chat_service = ChatService()
        result = await chat_service.process_chat_message(
            message=request.message,
            session_id=request.session_id,
            workspace_id=session.workspace_id,
            user_id=user_id,
            rag_technique=request.rag_technique
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to process message")
            )
        
        return {
            "success": True,
            "message_id": result["message_id"],
            "answer": result["answer"],
            "sources": result.get("sources", []),
            "context_used": result.get("context_used", False),
            "technique": result.get("technique", "standard")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/chat/history/{session_id}")
async def get_chat_history(
    session_id: int,
    limit: Optional[int] = 50,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get chat history for a session."""
    try:
        # TODO: Get user from token and verify access
        user_id = 1  # Mock user ID
        
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to chat session"
            )
        
        # Get chat history
        chat_service = ChatService()
        history = await chat_service.get_chat_history(session_id, limit)
        
        return {
            "session_id": session_id,
            "messages": history
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# WebSocket endpoint for real-time chat
@router.websocket("/chat/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: int):
    """WebSocket endpoint for real-time chat."""
    await websocket.accept()
    
    try:
        # TODO: Authenticate WebSocket connection
        
        chat_service = ChatService()
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Process message
            result = await chat_service.process_chat_message(
                message=message_data["message"],
                session_id=session_id,
                workspace_id=message_data["workspace_id"],
                user_id=1,  # TODO: Get from auth
                rag_technique=message_data.get("rag_technique")
            )
            
            # Send response back to client
            await websocket.send_text(json.dumps({
                "type": "response",
                "success": result["success"],
                "answer": result.get("answer", ""),
                "sources": result.get("sources", []),
                "technique": result.get("technique", "standard"),
                "error": result.get("error")
            }))
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "error": str(e)
        }))
