"""
Admin API routes for backup, cache management, and system monitoring.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict, Any, List
import structlog

from core.backup import get_backup_service, scheduled_backup
from core.cache import get_all_cache_stats, cleanup_caches, get_embedding_cache, get_query_cache
from core.service_registry import get_registry
from api.routes.auth import get_current_user
from core.database import User

logger = structlog.get_logger()
router = APIRouter()


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
