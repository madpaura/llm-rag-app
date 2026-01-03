"""
Admin API routes for backup, cache management, user management, and system monitoring.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import structlog

from core.backup import get_backup_service, scheduled_backup
from core.cache import get_all_cache_stats, cleanup_caches, get_embedding_cache, get_query_cache
from core.service_registry import get_registry
from api.routes.auth import get_current_user, require_admin
from core.database import User, Workspace, WorkspaceMember, get_db

logger = structlog.get_logger()
router = APIRouter()


# ============== User Management Schemas ==============

class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None
    is_admin: bool = False
    permissions: Optional[Dict[str, bool]] = None


class UpdateUserRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    permissions: Optional[Dict[str, bool]] = None


class UserListResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_admin: bool
    permissions: Optional[Dict[str, Any]]
    workspace_count: int
    created_at: Optional[str]


# ============== User Management Endpoints ==============

@router.get("/users", response_model=List[UserListResponse])
async def list_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all users with their workspace counts."""
    users = db.query(User).all()
    
    result = []
    for user in users:
        workspace_count = db.query(WorkspaceMember).filter(
            WorkspaceMember.user_id == user.id
        ).count()
        
        result.append(UserListResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            permissions=user.permissions or {},
            workspace_count=workspace_count,
            created_at=user.created_at.isoformat() if user.created_at else None
        ))
    
    return result


@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get detailed user information including workspaces."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's workspaces
    memberships = db.query(WorkspaceMember).filter(
        WorkspaceMember.user_id == user_id
    ).all()
    
    workspaces = []
    for membership in memberships:
        workspace = db.query(Workspace).filter(
            Workspace.id == membership.workspace_id
        ).first()
        if workspace:
            workspaces.append({
                "id": workspace.id,
                "name": workspace.name,
                "description": workspace.description,
                "role": membership.role,
                "joined_at": membership.joined_at.isoformat() if membership.joined_at else None
            })
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "permissions": user.permissions or {},
        "workspaces": workspaces,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None
    }


@router.post("/users")
async def create_user(
    request: CreateUserRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new user."""
    # Check if username or email already exists
    existing = db.query(User).filter(
        (User.username == request.username) | (User.email == request.email)
    ).first()
    
    if existing:
        if existing.username == request.username:
            raise HTTPException(status_code=400, detail="Username already exists")
        raise HTTPException(status_code=400, detail="Email already exists")
    
    # Default permissions for new users
    default_permissions = {
        "can_view_embeddings": False,
        "can_manage_workspaces": True,
        "can_manage_users": False,
        "can_view_all_workspaces": False
    }
    
    # Merge with provided permissions
    permissions = {**default_permissions, **(request.permissions or {})}
    
    # Create user
    new_user = User(
        username=request.username,
        email=request.email,
        password=request.password,  # Plain text
        full_name=request.full_name,
        is_admin=request.is_admin,
        is_active=True,
        permissions=permissions
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"Admin {current_user.username} created user: {new_user.username}")
    
    return {
        "id": new_user.id,
        "username": new_user.username,
        "email": new_user.email,
        "full_name": new_user.full_name,
        "is_active": new_user.is_active,
        "is_admin": new_user.is_admin,
        "permissions": new_user.permissions,
        "message": "User created successfully"
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update user information."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent admin from deactivating themselves
    if user.id == current_user.id and request.is_active == False:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    
    # Prevent removing admin from the only admin
    if user.id == current_user.id and request.is_admin == False:
        admin_count = db.query(User).filter(User.is_admin == True).count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove admin role from the only admin")
    
    # Check for duplicate username/email
    if request.username and request.username != user.username:
        existing = db.query(User).filter(User.username == request.username).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
    
    if request.email and request.email != user.email:
        existing = db.query(User).filter(User.email == request.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")
    
    # Update fields
    if request.username is not None:
        user.username = request.username
    if request.email is not None:
        user.email = request.email
    if request.password is not None:
        user.password = request.password  # Plain text
    if request.full_name is not None:
        user.full_name = request.full_name
    if request.is_active is not None:
        user.is_active = request.is_active
    if request.is_admin is not None:
        user.is_admin = request.is_admin
    if request.permissions is not None:
        # Merge permissions
        current_perms = user.permissions or {}
        user.permissions = {**current_perms, **request.permissions}
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"Admin {current_user.username} updated user: {user.username}")
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "permissions": user.permissions,
        "message": "User updated successfully"
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete a user."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent admin from deleting themselves
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    # Prevent deleting the only admin
    if user.is_admin:
        admin_count = db.query(User).filter(User.is_admin == True).count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the only admin")
    
    username = user.username
    db.delete(user)
    db.commit()
    
    logger.info(f"Admin {current_user.username} deleted user: {username}")
    
    return {"message": f"User '{username}' deleted successfully"}


@router.get("/users/{user_id}/workspaces")
async def get_user_workspaces(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all workspaces for a specific user."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    memberships = db.query(WorkspaceMember).filter(
        WorkspaceMember.user_id == user_id
    ).all()
    
    workspaces = []
    for membership in memberships:
        workspace = db.query(Workspace).filter(
            Workspace.id == membership.workspace_id
        ).first()
        if workspace:
            workspaces.append({
                "id": workspace.id,
                "name": workspace.name,
                "description": workspace.description,
                "is_active": workspace.is_active,
                "role": membership.role,
                "joined_at": membership.joined_at.isoformat() if membership.joined_at else None,
                "created_at": workspace.created_at.isoformat() if workspace.created_at else None
            })
    
    return {
        "user_id": user_id,
        "username": user.username,
        "workspaces": workspaces
    }


@router.get("/workspaces")
async def list_all_workspaces(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all workspaces (admin only)."""
    workspaces = db.query(Workspace).all()
    
    result = []
    for ws in workspaces:
        member_count = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == ws.id
        ).count()
        
        # Get creator info
        creator = db.query(User).filter(User.id == ws.created_by).first() if ws.created_by else None
        
        result.append({
            "id": ws.id,
            "name": ws.name,
            "description": ws.description,
            "is_active": ws.is_active,
            "member_count": member_count,
            "created_by": creator.username if creator else None,
            "created_at": ws.created_at.isoformat() if ws.created_at else None
        })
    
    return result


# ============== Permission Constants ==============

@router.get("/permissions/available")
async def get_available_permissions(
    current_user: User = Depends(require_admin)
):
    """Get list of available permissions that can be assigned to users."""
    return {
        "permissions": [
            {
                "key": "can_view_embeddings",
                "name": "View Embeddings",
                "description": "Allow user to view and manage embeddings"
            },
            {
                "key": "can_manage_workspaces",
                "name": "Manage Workspaces",
                "description": "Allow user to create and manage their own workspaces"
            },
            {
                "key": "can_manage_users",
                "name": "Manage Users",
                "description": "Allow user to manage other users (admin only)"
            },
            {
                "key": "can_view_all_workspaces",
                "name": "View All Workspaces",
                "description": "Allow user to view all workspaces in the system"
            },
            {
                "key": "can_ingest_data",
                "name": "Ingest Data",
                "description": "Allow user to ingest documents and data sources"
            },
            {
                "key": "can_query",
                "name": "Query Knowledge Base",
                "description": "Allow user to query the RAG system"
            }
        ]
    }


# ============== Backup Endpoints ==============

@router.post("/backup", response_model=Dict[str, Any])
async def create_backup(
    name: str = None,
    compress: bool = True,
    current_user: User = Depends(get_current_user)
):
    """
    Create a database backup.
    
    - **name**: Optional backup name (default: timestamp-based)
    - **compress**: Whether to compress the backup (default: True)
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    service = get_backup_service()
    result = service.create_backup(name=name, compress=compress)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Backup failed"))
    
    return result


@router.post("/backup/restore/{backup_name}", response_model=Dict[str, Any])
async def restore_backup(
    backup_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Restore database from a backup.
    
    **Warning**: This will replace the current database!
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    service = get_backup_service()
    result = service.restore_backup(backup_name)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Restore failed"))
    
    return result


@router.get("/backup/list", response_model=List[Dict[str, Any]])
async def list_backups(
    current_user: User = Depends(get_current_user)
):
    """List all available backups."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    service = get_backup_service()
    return service.list_backups()


@router.delete("/backup/{backup_name}", response_model=Dict[str, Any])
async def delete_backup(
    backup_name: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a specific backup."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    service = get_backup_service()
    result = service.delete_backup(backup_name)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error", "Backup not found"))
    
    return result


@router.post("/backup/cleanup", response_model=Dict[str, Any])
async def cleanup_backups(
    keep_count: int = 5,
    current_user: User = Depends(get_current_user)
):
    """
    Remove old backups, keeping only the most recent ones.
    
    - **keep_count**: Number of backups to keep (default: 5)
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    service = get_backup_service()
    return service.cleanup_old_backups(keep_count=keep_count)


@router.post("/backup/export", response_model=Dict[str, Any])
async def export_data(
    tables: List[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Export database data to JSON format.
    
    - **tables**: List of tables to export (default: all)
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    service = get_backup_service()
    return service.export_data(tables=tables)


# ============== Cache Endpoints ==============

@router.get("/cache/stats", response_model=Dict[str, Any])
async def get_cache_stats(
    current_user: User = Depends(get_current_user)
):
    """Get statistics from all caches."""
    return get_all_cache_stats()


@router.post("/cache/cleanup", response_model=Dict[str, Any])
async def cleanup_cache(
    current_user: User = Depends(get_current_user)
):
    """Remove expired entries from all caches."""
    removed = await cleanup_caches()
    return {"success": True, "removed_entries": removed}


@router.post("/cache/clear/embeddings", response_model=Dict[str, Any])
async def clear_embedding_cache(
    current_user: User = Depends(get_current_user)
):
    """Clear the embedding cache."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    cache = get_embedding_cache()
    cache._cache.clear()
    return {"success": True, "message": "Embedding cache cleared"}


@router.post("/cache/clear/queries", response_model=Dict[str, Any])
async def clear_query_cache(
    current_user: User = Depends(get_current_user)
):
    """Clear the query result cache."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    cache = get_query_cache()
    cache._search_cache.clear()
    cache._answer_cache.clear()
    return {"success": True, "message": "Query cache cleared"}


# ============== Service Registry Endpoints ==============

@router.get("/services/stats", response_model=Dict[str, Any])
async def get_service_stats(
    current_user: User = Depends(get_current_user)
):
    """Get statistics about registered services."""
    registry = get_registry()
    return registry.get_stats()


@router.get("/services/health", response_model=Dict[str, Any])
async def check_services_health(
    current_user: User = Depends(get_current_user)
):
    """Perform health check on all initialized services."""
    registry = get_registry()
    return await registry.health_check()


# ============== Background Tasks ==============

@router.post("/tasks/backup", response_model=Dict[str, Any])
async def schedule_backup_task(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Schedule a backup task to run in the background."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    background_tasks.add_task(scheduled_backup)
    return {"success": True, "message": "Backup task scheduled"}
