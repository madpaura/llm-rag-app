"""
Workspace management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import structlog

from core.database import get_db, Workspace, WorkspaceMember, User, DataSource, Document, DocumentChunk, ChatSession, ChatMessage
from api.routes.auth import get_current_user

logger = structlog.get_logger()
router = APIRouter()

class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = None

class WorkspaceResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_active: bool
    created_at: str
    member_count: int
    role: str

class WorkspaceMemberResponse(BaseModel):
    id: int
    user_id: int
    username: str
    email: str
    role: str
    joined_at: str

@router.get("/", response_model=List[WorkspaceResponse])
async def get_user_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get workspaces for current user. Admins see all workspaces, regular users see only their own."""
    user_id = current_user.id
    
    if current_user.is_admin:
        # Admin users can see all workspaces
        workspaces = db.query(Workspace).filter(Workspace.is_active == True).all()
    else:
        # Regular users only see workspaces they are members of
        workspaces = db.query(Workspace)\
            .join(WorkspaceMember)\
            .filter(WorkspaceMember.user_id == user_id)\
            .filter(Workspace.is_active == True)\
            .all()
    
    result = []
    for workspace in workspaces:
        member = db.query(WorkspaceMember)\
            .filter(WorkspaceMember.workspace_id == workspace.id)\
            .filter(WorkspaceMember.user_id == user_id)\
            .first()
        
        member_count = db.query(WorkspaceMember)\
            .filter(WorkspaceMember.workspace_id == workspace.id)\
            .count()
        
        # For admin viewing other's workspaces, show as "admin" role
        role = member.role if member else ("admin" if current_user.is_admin else "viewer")
        
        result.append(WorkspaceResponse(
            id=workspace.id,
            name=workspace.name,
            description=workspace.description,
            is_active=workspace.is_active,
            created_at=workspace.created_at.isoformat(),
            member_count=member_count,
            role=role
        ))
    
    return result

@router.post("/", response_model=WorkspaceResponse)
async def create_workspace(
    workspace_data: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new workspace."""
    user_id = current_user.id
    
    # Check if workspace name already exists
    existing = db.query(Workspace).filter(Workspace.name == workspace_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace name already exists"
        )
    
    # Create workspace
    workspace = Workspace(
        name=workspace_data.name,
        description=workspace_data.description,
        created_by=user_id
    )
    db.add(workspace)
    db.flush()
    
    # Add creator as admin member
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user_id,
        role="admin"
    )
    db.add(member)
    db.commit()
    
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        description=workspace.description,
        is_active=workspace.is_active,
        created_at=workspace.created_at.isoformat(),
        member_count=1,
        role="admin"
    )

def check_workspace_access(workspace_id: int, user: User, db: Session) -> Workspace:
    """Check if user has access to workspace. Returns workspace if access granted."""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Admins have access to all workspaces
    if user.is_admin:
        return workspace
    
    # Check if user is a member of this workspace
    member = db.query(WorkspaceMember)\
        .filter(WorkspaceMember.workspace_id == workspace_id)\
        .filter(WorkspaceMember.user_id == user.id)\
        .first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this workspace"
        )
    
    return workspace


@router.get("/{workspace_id}")
async def get_workspace(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get workspace details."""
    workspace = check_workspace_access(workspace_id, current_user, db)
    
    return {
        "id": workspace.id,
        "name": workspace.name,
        "description": workspace.description,
        "is_active": workspace.is_active,
        "created_at": workspace.created_at.isoformat()
    }

@router.get("/{workspace_id}/members", response_model=List[WorkspaceMemberResponse])
async def get_workspace_members(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get workspace members."""
    check_workspace_access(workspace_id, current_user, db)
    
    members = db.query(WorkspaceMember, User)\
        .join(User)\
        .filter(WorkspaceMember.workspace_id == workspace_id)\
        .all()
    
    result = []
    for member, user in members:
        result.append(WorkspaceMemberResponse(
            id=member.id,
            user_id=user.id,
            username=user.username,
            email=user.email,
            role=member.role,
            joined_at=member.joined_at.isoformat()
        ))
    
    return result


@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a workspace and all associated data.
    This includes: data sources, documents, document chunks, chat sessions, chat messages, and members.
    """
    user_id = current_user.id
    
    # Check if workspace exists
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # System admins can delete any workspace
    if current_user.is_admin:
        pass  # Allow deletion
    else:
        # Check if user is admin of the workspace
        member = db.query(WorkspaceMember)\
            .filter(WorkspaceMember.workspace_id == workspace_id)\
            .filter(WorkspaceMember.user_id == user_id)\
            .first()
        
        if not member or member.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only workspace admins can delete workspaces"
            )
    
    try:
        # Delete chat messages for all sessions in this workspace
        chat_sessions = db.query(ChatSession).filter(ChatSession.workspace_id == workspace_id).all()
        for session in chat_sessions:
            db.query(ChatMessage).filter(ChatMessage.session_id == session.id).delete()
        
        # Delete chat sessions
        db.query(ChatSession).filter(ChatSession.workspace_id == workspace_id).delete()
        
        # Delete document chunks and documents for all data sources
        data_sources = db.query(DataSource).filter(DataSource.workspace_id == workspace_id).all()
        for ds in data_sources:
            documents = db.query(Document).filter(Document.data_source_id == ds.id).all()
            for doc in documents:
                db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
            db.query(Document).filter(Document.data_source_id == ds.id).delete()
        
        # Delete data sources
        db.query(DataSource).filter(DataSource.workspace_id == workspace_id).delete()
        
        # Delete workspace members
        db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace_id).delete()
        
        # Delete workspace
        db.delete(workspace)
        db.commit()
        
        logger.info(f"Workspace {workspace_id} and all associated data deleted")
        
        return {
            "success": True,
            "message": f"Workspace '{workspace.name}' and all associated data deleted successfully"
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete workspace: {str(e)}"
        )
