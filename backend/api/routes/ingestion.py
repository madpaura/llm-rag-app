"""
Data ingestion endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import structlog
import aiofiles
import os
from pathlib import Path
from datetime import datetime
import asyncio

from core.database import get_db, DataSource, Workspace, Document, DocumentChunk, CodeUnit, CodeCallGraph, User, WorkspaceMember
from core.config import get_settings
from services.ingestion_service import IngestionOrchestrator
from services.code_ingestion_service import CodeIngestionService
from api.routes.auth import get_current_user

logger = structlog.get_logger()
router = APIRouter()
settings = get_settings()


def check_workspace_access(workspace_id: int, user: User, db: Session) -> Workspace:
    """Check if user has access to workspace."""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    if user.is_admin:
        return workspace
    
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

# In-memory progress tracking store
_ingestion_progress: Dict[int, Dict[str, Any]] = {}

# In-memory cancellation flag store
_cancellation_flags: Dict[int, bool] = {}

def update_progress(data_source_id: int, stage: str, stage_num: int, total_stages: int,
                   current: int = 0, total: int = 0, message: str = ""):
    """Update ingestion progress for a data source."""
    _ingestion_progress[data_source_id] = {
        "stage": stage,
        "stage_num": stage_num,
        "total_stages": total_stages,
        "current": current,
        "total": total,
        "message": message,
        "percent": int((current / total * 100) if total > 0 else 0),
        "updated_at": datetime.utcnow().isoformat()
    }
    logger.info(f"[PROGRESS] DS {data_source_id}: Stage {stage_num}/{total_stages} - {stage} ({current}/{total}) {message}")

def get_progress(data_source_id: int) -> Optional[Dict[str, Any]]:
    """Get ingestion progress for a data source."""
    return _ingestion_progress.get(data_source_id)

def clear_progress(data_source_id: int):
    """Clear progress tracking for a data source."""
    if data_source_id in _ingestion_progress:
        del _ingestion_progress[data_source_id]
    if data_source_id in _cancellation_flags:
        del _cancellation_flags[data_source_id]

def request_cancellation(data_source_id: int):
    """Request cancellation of an ingestion job."""
    _cancellation_flags[data_source_id] = True
    logger.info(f"[CANCEL] Cancellation requested for data source {data_source_id}")

def is_cancelled(data_source_id: int) -> bool:
    """Check if cancellation has been requested for a data source."""
    return _cancellation_flags.get(data_source_id, False)

class GitIngestionRequest(BaseModel):
    workspace_id: int
    name: str
    repo_url: str
    branch: Optional[str] = "main"
    username: Optional[str] = None
    token: Optional[str] = None
    language_filter: Optional[str] = None  # Filter by language: 'all', 'c_cpp', 'python', 'javascript', 'java', 'docs'
    max_depth: Optional[int] = None  # Max directory depth to scan

class ConfluenceIngestionRequest(BaseModel):
    workspace_id: int
    name: str
    space_key: str
    base_url: Optional[str] = None
    username: Optional[str] = None
    api_token: Optional[str] = None
    page_ids: Optional[List[str]] = None  # Specific page IDs to ingest
    max_depth: Optional[int] = None  # Max depth for child pages (None = all)
    include_children: bool = True  # Include child pages


class JiraIngestionRequest(BaseModel):
    workspace_id: int
    name: str
    project_key: str
    base_url: Optional[str] = None
    username: Optional[str] = None
    api_token: Optional[str] = None
    issue_types: Optional[List[str]] = None  # Filter: ['Story', 'Epic', 'Bug', 'Task']
    specific_tickets: Optional[List[str]] = None  # Specific ticket keys like ['PROJ-123']
    max_results: Optional[int] = None  # Max number of issues to fetch


class CodeIngestionRequest(BaseModel):
    workspace_id: int
    name: str
    directory_path: Optional[str] = None  # For local directory ingestion
    max_depth: Optional[int] = None  # Max directory depth to scan (None = unlimited)
    include_headers: bool = True  # Include header files (.h, .hpp, etc.)

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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all data sources for a workspace."""
    check_workspace_access(workspace_id, current_user, db)
    
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

@router.get("/progress/{data_source_id}")
async def get_ingestion_progress(
    data_source_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the progress of an ongoing ingestion job."""
    # Check if data source exists
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found"
        )
    
    progress = get_progress(data_source_id)
    
    if progress:
        return {
            "data_source_id": data_source_id,
            "status": data_source.status,
            "in_progress": True,
            **progress
        }
    else:
        # No active progress, return status from DB
        return {
            "data_source_id": data_source_id,
            "status": data_source.status,
            "in_progress": False,
            "stage": "Completed" if data_source.status == "completed" else data_source.status.title(),
            "stage_num": 4 if data_source.status == "completed" else 0,
            "total_stages": 4,
            "current": 0,
            "total": 0,
            "percent": 100 if data_source.status == "completed" else 0,
            "message": ""
        }

@router.post("/cancel/{data_source_id}")
async def cancel_ingestion(
    data_source_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel an ongoing ingestion job."""
    # Check if data source exists
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found"
        )
    
    # Check if ingestion is in progress
    progress = get_progress(data_source_id)
    if not progress and data_source.status not in ["pending", "processing"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active ingestion to cancel"
        )
    
    # Request cancellation
    request_cancellation(data_source_id)
    
    # Update status to cancelled
    data_source.status = "cancelled"
    db.commit()
    
    # Update progress to show cancellation
    update_progress(data_source_id, "Cancelled", 0, 4, 0, 0, "Ingestion cancelled by user")
    
    return {
        "success": True,
        "data_source_id": data_source_id,
        "message": "Ingestion cancellation requested"
    }

@router.get("/active/{workspace_id}")
async def get_active_ingestions(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all active/in-progress ingestion jobs for a workspace."""
    check_workspace_access(workspace_id, current_user, db)
    
    # Get data sources that are processing
    active_sources = db.query(DataSource).filter(
        DataSource.workspace_id == workspace_id,
        DataSource.status.in_(["pending", "processing"])
    ).all()
    
    result = []
    for source in active_sources:
        progress = get_progress(source.id)
        result.append({
            "data_source_id": source.id,
            "name": source.name,
            "source_type": source.source_type,
            "status": source.status,
            "in_progress": progress is not None,
            "progress": progress
        })
    
    return result

@router.post("/git")
async def ingest_git_repository(
    request: GitIngestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Ingest a Git repository."""
    try:
        # Verify workspace exists and user has access
        workspace = check_workspace_access(request.workspace_id, current_user, db)
        
        # Create data source record
        config = {
            "branch": request.branch,
            "username": request.username,
            "token": request.token,
            "language_filter": request.language_filter,
            "max_depth": request.max_depth
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
        
        # Initialize progress tracking
        update_progress(data_source.id, "Initializing", 1, 4, 0, 1, "Starting ingestion...")
        
        # Start ingestion process in background
        async def run_ingestion():
            try:
                orchestrator = IngestionOrchestrator()
                result = await orchestrator.ingest_data_source(data_source.id, progress_callback=update_progress)
                
                if not result["success"]:
                    logger.error(f"Ingestion failed for data source {data_source.id}: {result.get('error')}")
                
                # Clear progress on completion (after a short delay so frontend can see final state)
                await asyncio.sleep(2)
                clear_progress(data_source.id)
            except Exception as e:
                logger.error(f"Background ingestion error: {e}")
                clear_progress(data_source.id)
        
        # Start the background task
        asyncio.create_task(run_ingestion())
        
        return {
            "success": True,
            "data_source_id": data_source.id,
            "message": "Git repository ingestion started",
            "documents_count": 0,
            "in_progress": True
        }
        
    except Exception as e:
        logger.error(f"Error starting Git repository ingestion: {e}")
        if 'data_source' in locals():
            clear_progress(data_source.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/confluence")
async def ingest_confluence_space(
    request: ConfluenceIngestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Ingest a Confluence space."""
    try:
        # Verify workspace exists and user has access
        workspace = check_workspace_access(request.workspace_id, current_user, db)
        
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


@router.post("/jira")
async def ingest_jira_project(
    request: JiraIngestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Ingest issues from a JIRA project."""
    try:
        # Verify workspace exists and user has access
        workspace = check_workspace_access(request.workspace_id, current_user, db)
        
        # Create data source record
        config = {
            "project_key": request.project_key,
            "base_url": request.base_url,
            "username": request.username,
            "api_token": request.api_token,
            "issue_types": request.issue_types,
            "specific_tickets": request.specific_tickets,
            "max_results": request.max_results
        }
        
        data_source = DataSource(
            workspace_id=request.workspace_id,
            name=request.name,
            source_type="jira",
            source_url=f"{request.base_url}/projects/{request.project_key}" if request.base_url else None,
            config=config,
            status="pending"
        )
        db.add(data_source)
        db.commit()
        
        # Initialize progress tracking
        update_progress(data_source.id, "Initializing", 1, 4, 0, 1, "Starting JIRA ingestion...")
        
        # Start ingestion process in background
        async def run_jira_ingestion():
            try:
                orchestrator = IngestionOrchestrator()
                result = await orchestrator.ingest_data_source(data_source.id, progress_callback=update_progress)
                
                if not result["success"]:
                    logger.error(f"JIRA ingestion failed for data source {data_source.id}: {result.get('error')}")
                
                # Clear progress on completion
                await asyncio.sleep(2)
                clear_progress(data_source.id)
            except Exception as e:
                logger.error(f"Background JIRA ingestion error: {e}")
                clear_progress(data_source.id)
        
        # Start the background task
        asyncio.create_task(run_jira_ingestion())
        
        return {
            "success": True,
            "data_source_id": data_source.id,
            "message": "JIRA project ingestion started",
            "documents_count": 0,
            "in_progress": True
        }
        
    except Exception as e:
        logger.error(f"Error starting JIRA project ingestion: {e}")
        if 'data_source' in locals():
            clear_progress(data_source.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/document")
async def ingest_document(
    workspace_id: int = Form(...),
    name: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Ingest a document file."""
    try:
        # Verify workspace exists and user has access
        workspace = check_workspace_access(workspace_id, current_user, db)
        
        # Check file size
        if file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE} bytes"
            )
        
        # Save uploaded file to workspace-isolated directory
        upload_dir = Path(settings.DATA_BASE_DIR) / str(workspace_id) / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / file.filename
        
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get ingestion status for a data source."""
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found"
        )
    
    # Check user access to workspace
    check_workspace_access(data_source.workspace_id, current_user, db)
    
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a data source and its associated documents."""
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found"
        )
    
    # Check user access to workspace
    check_workspace_access(data_source.workspace_id, current_user, db)
    # TODO: Delete associated documents and vector embeddings
    
    db.delete(data_source)
    db.commit()
    
    return {"message": "Data source deleted successfully"}


@router.get("/documents/{document_id}")
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a document with its content for viewing."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Get document content split into lines for navigation
    content = document.content or ""
    lines = content.split('\n')
    
    return {
        "id": document.id,
        "title": document.title,
        "file_path": document.file_path,
        "file_type": document.file_type,
        "content": content,
        "lines": lines,
        "total_lines": len(lines),
        "metadata": document.doc_metadata,
        "created_at": document.created_at.isoformat()
    }


@router.get("/documents/{document_id}/chunk/{chunk_id}")
async def get_document_chunk(
    document_id: int,
    chunk_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific chunk with its location in the document."""
    chunk = db.query(DocumentChunk).filter(
        DocumentChunk.id == chunk_id,
        DocumentChunk.document_id == document_id
    ).first()
    
    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk not found"
        )
    
    document = db.query(Document).filter(Document.id == document_id).first()
    
    # Get chunk metadata for navigation
    chunk_meta = chunk.chunk_metadata or {}
    
    return {
        "chunk_id": chunk.id,
        "document_id": document_id,
        "document_title": document.title if document else "Unknown",
        "file_path": document.file_path if document else None,
        "chunk_index": chunk.chunk_index,
        "content": chunk.content,
        "start_line": chunk_meta.get('start_line', 1),
        "end_line": chunk_meta.get('end_line', 1),
        "start_char": chunk_meta.get('start_char', 0),
        "end_char": chunk_meta.get('end_char', 0),
        "page_number": chunk_meta.get('page_number'),
        "metadata": chunk_meta
    }


@router.get("/documents/by-workspace/{workspace_id}")
async def get_workspace_documents(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all documents for a workspace."""
    check_workspace_access(workspace_id, current_user, db)
    
    # Get all data sources for the workspace
    data_sources = db.query(DataSource).filter(DataSource.workspace_id == workspace_id).all()
    data_source_ids = [ds.id for ds in data_sources]
    
    if not data_source_ids:
        return []
    
    # Get all documents for these data sources
    documents = db.query(Document).filter(Document.data_source_id.in_(data_source_ids)).all()
    
    return [
        {
            "id": doc.id,
            "title": doc.title,
            "file_path": doc.file_path,
            "file_type": doc.file_type,
            "created_at": doc.created_at.isoformat()
        }
        for doc in documents
    ]


@router.post("/code")
async def ingest_code_files(
    workspace_id: int = Form(...),
    name: str = Form(...),
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ingest C/C++ source code files with AST-based parsing.
    
    Extracts functions, classes, structs and generates LLM summaries
    for each code unit. Creates embeddings at function/class/file level.
    
    Supported extensions: .c, .h, .cpp, .cc, .cxx, .hpp, .hxx, .hh
    """
    try:
        # Verify workspace exists and user has access
        workspace = check_workspace_access(workspace_id, current_user, db)
        
        # Filter supported files
        supported_extensions = {'.c', '.h', '.cpp', '.cc', '.cxx', '.hpp', '.hxx', '.hh'}
        code_files = []
        
        for file in files:
            ext = Path(file.filename).suffix.lower()
            if ext in supported_extensions:
                content = await file.read()
                code_files.append({
                    "path": file.filename,
                    "content": content.decode('utf-8', errors='replace')
                })
        
        if not code_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No supported C/C++ files found. Supported: .c, .h, .cpp, .cc, .cxx, .hpp, .hxx, .hh"
            )
        
        # Create data source
        data_source = DataSource(
            workspace_id=workspace_id,
            name=name,
            source_type="code",
            status="processing",
            config={"file_count": len(code_files)}
        )
        db.add(data_source)
        db.commit()
        
        # Process code files
        code_service = CodeIngestionService()
        stats = await code_service.ingest_code_files(
            files=code_files,
            workspace_id=workspace_id,
            data_source_id=data_source.id,
            db=db
        )
        
        # Update data source status
        from datetime import datetime
        data_source.status = "completed" if not stats["errors"] else "completed_with_errors"
        data_source.last_ingested = datetime.utcnow()
        db.commit()
        
        return {
            "success": True,
            "data_source_id": data_source.id,
            "message": f"Processed {stats['files_processed']} files",
            "stats": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Code ingestion failed: {e}")
        if 'data_source' in locals():
            data_source.status = "failed"
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/code/directory")
async def ingest_code_directory(
    request: CodeIngestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ingest C/C++ source code from a local directory.
    
    Recursively scans the directory for C/C++ files and processes them
    with AST-based parsing and LLM summary generation.
    """
    try:
        # Verify workspace exists and user has access
        workspace = check_workspace_access(request.workspace_id, current_user, db)
        
        # Verify directory exists
        if not request.directory_path or not os.path.isdir(request.directory_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid directory path"
            )
        
        # Create data source
        data_source = DataSource(
            workspace_id=request.workspace_id,
            name=request.name,
            source_type="code",
            source_url=request.directory_path,
            status="processing",
            config={
                "max_depth": request.max_depth,
                "include_headers": request.include_headers
            }
        )
        db.add(data_source)
        db.commit()
        
        # Process directory
        code_service = CodeIngestionService()
        stats = await code_service.ingest_code_directory(
            directory=request.directory_path,
            workspace_id=request.workspace_id,
            data_source_id=data_source.id,
            db=db,
            max_depth=request.max_depth,
            include_headers=request.include_headers
        )
        
        # Update data source status
        from datetime import datetime
        data_source.status = "completed" if not stats["errors"] else "completed_with_errors"
        data_source.last_ingested = datetime.utcnow()
        db.commit()
        
        return {
            "success": True,
            "data_source_id": data_source.id,
            "message": f"Processed {stats['files_processed']} files",
            "stats": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Code directory ingestion failed: {e}")
        if 'data_source' in locals():
            data_source.status = "failed"
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/code/units/{document_id}")
async def get_code_units(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all code units for a document."""
    units = db.query(CodeUnit).filter(CodeUnit.document_id == document_id).all()
    
    return [
        {
            "id": unit.id,
            "unit_type": unit.unit_type,
            "name": unit.name,
            "signature": unit.signature,
            "summary": unit.summary,
            "start_line": unit.start_line,
            "end_line": unit.end_line,
            "language": unit.language,
            "parent_id": unit.parent_id
        }
        for unit in units
    ]


@router.get("/code/units/{unit_id}/detail")
async def get_code_unit_detail(
    unit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about a code unit including code and call graph."""
    unit = db.query(CodeUnit).filter(CodeUnit.id == unit_id).first()
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Code unit not found"
        )
    
    # Get outgoing calls
    outgoing = db.query(CodeCallGraph).filter(CodeCallGraph.caller_id == unit_id).all()
    
    # Get incoming calls
    incoming = db.query(CodeCallGraph).filter(CodeCallGraph.callee_id == unit_id).all()
    
    return {
        "id": unit.id,
        "unit_type": unit.unit_type,
        "name": unit.name,
        "signature": unit.signature,
        "code": unit.code,
        "summary": unit.summary,
        "start_line": unit.start_line,
        "end_line": unit.end_line,
        "language": unit.language,
        "parent_id": unit.parent_id,
        "metadata": unit.unit_metadata,
        "calls": [{"name": c.callee_name, "line": c.call_line, "resolved": c.callee_id is not None} for c in outgoing],
        "called_by": [{"caller_id": c.caller_id, "line": c.call_line} for c in incoming]
    }


@router.get("/code/call-graph/{workspace_id}")
async def get_workspace_call_graph(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the call graph for all code in a workspace."""
    check_workspace_access(workspace_id, current_user, db)
    
    # Get all documents in workspace
    data_sources = db.query(DataSource).filter(
        DataSource.workspace_id == workspace_id,
        DataSource.source_type == "code"
    ).all()
    
    if not data_sources:
        return {"nodes": [], "edges": []}
    
    ds_ids = [ds.id for ds in data_sources]
    documents = db.query(Document).filter(Document.data_source_id.in_(ds_ids)).all()
    doc_ids = [d.id for d in documents]
    
    # Get all code units
    units = db.query(CodeUnit).filter(
        CodeUnit.document_id.in_(doc_ids),
        CodeUnit.unit_type.in_(['function', 'method'])
    ).all()
    
    unit_ids = [u.id for u in units]
    
    # Get call graph edges
    calls = db.query(CodeCallGraph).filter(CodeCallGraph.caller_id.in_(unit_ids)).all()
    
    nodes = [
        {
            "id": u.id,
            "name": u.name,
            "type": u.unit_type,
            "file": u.document.title if u.document else "unknown"
        }
        for u in units
    ]
    
    edges = [
        {
            "source": c.caller_id,
            "target": c.callee_id,
            "target_name": c.callee_name,
            "resolved": c.callee_id is not None
        }
        for c in calls
    ]
    
    return {"nodes": nodes, "edges": edges}
