"""
Workspace management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import structlog

from core.database import get_db, Workspace, WorkspaceMember, User

logger = structlog.get_logger()
router = APIRouter()
security = HTTPBearer()

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
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get workspaces for current user."""
    # TODO: Get user from token
    user_id = 1  # Mock user ID
    
    # Query workspaces where user is a member
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
        
        result.append(WorkspaceResponse(
            id=workspace.id,
            name=workspace.name,
            description=workspace.description,
            is_active=workspace.is_active,
            created_at=workspace.created_at.isoformat(),
            member_count=member_count,
            role=member.role if member else "viewer"
        ))
    
    return result

@router.post("/", response_model=WorkspaceResponse)
async def create_workspace(
    workspace_data: WorkspaceCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Create a new workspace."""
    # TODO: Get user from token
    user_id = 1  # Mock user ID
    
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

@router.get("/{workspace_id}")
async def get_workspace(
    workspace_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get workspace details."""
    # TODO: Check user access to workspace
    
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
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
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get workspace members."""
    # TODO: Check user access to workspace
    
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
