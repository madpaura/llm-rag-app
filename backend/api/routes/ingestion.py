"""
Data ingestion endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import structlog
import aiofiles
import os
from pathlib import Path

from core.database import get_db, DataSource, Workspace
from core.config import get_settings
from services.ingestion_service import IngestionOrchestrator

logger = structlog.get_logger()
router = APIRouter()
security = HTTPBearer()
settings = get_settings()

class GitIngestionRequest(BaseModel):
    workspace_id: int
    name: str
    repo_url: str
    branch: Optional[str] = "main"
    username: Optional[str] = None
    token: Optional[str] = None

class ConfluenceIngestionRequest(BaseModel):
    workspace_id: int
    name: str
    space_key: str
    base_url: Optional[str] = None
    username: Optional[str] = None
    api_token: Optional[str] = None

class DataSourceResponse(BaseModel):
    id: int
    name: str
    source_type: str
    source_url: Optional[str]
    status: str
    last_ingested: Optional[str]
    created_at: str

@router.get("/sources/{workspace_id}", response_model=List[DataSourceResponse])
async def get_data_sources(
    workspace_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get all data sources for a workspace."""
    # TODO: Check user access to workspace
    
    sources = db.query(DataSource)\
        .filter(DataSource.workspace_id == workspace_id)\
        .order_by(DataSource.created_at.desc())\
        .all()
    
    result = []
    for source in sources:
        result.append(DataSourceResponse(
            id=source.id,
            name=source.name,
            source_type=source.source_type,
            source_url=source.source_url,
            status=source.status,
            last_ingested=source.last_ingested.isoformat() if source.last_ingested else None,
            created_at=source.created_at.isoformat()
        ))
    
    return result

@router.post("/git")
async def ingest_git_repository(
    request: GitIngestionRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Ingest a Git repository."""
    try:
        # Verify workspace exists and user has access
        workspace = db.query(Workspace).filter(Workspace.id == request.workspace_id).first()
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        # Create data source record
        config = {
            "branch": request.branch,
            "username": request.username,
            "token": request.token
        }
        
        data_source = DataSource(
            workspace_id=request.workspace_id,
            name=request.name,
            source_type="git",
            source_url=request.repo_url,
            config=config,
            status="pending"
        )
        db.add(data_source)
        db.commit()
        
        # Start ingestion process
        orchestrator = IngestionOrchestrator()
        result = await orchestrator.ingest_data_source(data_source.id)
        
        return {
            "success": result["success"],
            "data_source_id": data_source.id,
            "message": f"Git repository ingestion {'completed' if result['success'] else 'failed'}",
            "documents_count": result.get("documents_count", 0) if result["success"] else 0,
            "error": result.get("error") if not result["success"] else None
        }
        
    except Exception as e:
        logger.error(f"Error ingesting Git repository: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/confluence")
async def ingest_confluence_space(
    request: ConfluenceIngestionRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Ingest a Confluence space."""
    try:
        # Verify workspace exists and user has access
        workspace = db.query(Workspace).filter(Workspace.id == request.workspace_id).first()
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        # Create data source record
        config = {
            "space_key": request.space_key,
            "base_url": request.base_url,
            "username": request.username,
            "api_token": request.api_token
        }
        
        data_source = DataSource(
            workspace_id=request.workspace_id,
            name=request.name,
            source_type="confluence",
            source_url=f"{request.base_url}/spaces/{request.space_key}" if request.base_url else None,
            config=config,
            status="pending"
        )
        db.add(data_source)
        db.commit()
        
        # Start ingestion process
        orchestrator = IngestionOrchestrator()
        result = await orchestrator.ingest_data_source(data_source.id)
        
        return {
            "success": result["success"],
            "data_source_id": data_source.id,
            "message": f"Confluence space ingestion {'completed' if result['success'] else 'failed'}",
            "documents_count": result.get("documents_count", 0) if result["success"] else 0,
            "error": result.get("error") if not result["success"] else None
        }
        
    except Exception as e:
        logger.error(f"Error ingesting Confluence space: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/document")
async def ingest_document(
    workspace_id: int = Form(...),
    name: str = Form(...),
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Ingest a document file."""
    try:
        # Verify workspace exists and user has access
        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        # Check file size
        if file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE} bytes"
            )
        
        # Save uploaded file
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / f"{workspace_id}_{file.filename}"
        
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Create data source record
        config = {
            "original_filename": file.filename,
            "file_size": len(content)
        }
        
        data_source = DataSource(
            workspace_id=workspace_id,
            name=name,
            source_type="document",
            source_url=str(file_path),
            config=config,
            status="pending"
        )
        db.add(data_source)
        db.commit()
        
        # Start ingestion process
        orchestrator = IngestionOrchestrator()
        result = await orchestrator.ingest_data_source(data_source.id)
        
        # Clean up uploaded file if ingestion failed
        if not result["success"]:
            try:
                os.remove(file_path)
            except:
                pass
        
        return {
            "success": result["success"],
            "data_source_id": data_source.id,
            "message": f"Document ingestion {'completed' if result['success'] else 'failed'}",
            "documents_count": result.get("documents_count", 0) if result["success"] else 0,
            "error": result.get("error") if not result["success"] else None
        }
        
    except Exception as e:
        logger.error(f"Error ingesting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/status/{data_source_id}")
async def get_ingestion_status(
    data_source_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get ingestion status for a data source."""
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found"
        )
    
    # TODO: Check user access to workspace
    
    return {
        "id": data_source.id,
        "name": data_source.name,
        "source_type": data_source.source_type,
        "status": data_source.status,
        "last_ingested": data_source.last_ingested.isoformat() if data_source.last_ingested else None,
        "created_at": data_source.created_at.isoformat()
    }

@router.delete("/sources/{data_source_id}")
async def delete_data_source(
    data_source_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Delete a data source and its associated documents."""
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found"
        )
    
    # TODO: Check user access to workspace
    # TODO: Delete associated documents and vector embeddings
    
    db.delete(data_source)
    db.commit()
    
    return {"message": "Data source deleted successfully"}
