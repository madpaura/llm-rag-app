"""
Embeddings API routes for viewing and navigating document embeddings.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import structlog

from core.database import get_db, DataSource, Document, DocumentChunk, Workspace, CodeUnit

logger = structlog.get_logger()
router = APIRouter()
security = HTTPBearer()


@router.get("/workspace/{workspace_id}")
async def get_workspace_embeddings(
    workspace_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get all documents with embedding info for a workspace.
    
    For code files (C/C++), shows code units (functions, classes, files) instead of simple chunks.
    """
    try:
        # Verify workspace exists
        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        # Get all data sources for the workspace
        data_sources = db.query(DataSource).filter(
            DataSource.workspace_id == workspace_id
        ).all()
        
        data_source_map = {ds.id: ds.name for ds in data_sources}
        data_source_ids = list(data_source_map.keys())
        
        if not data_source_ids:
            return []
        
        # Get all documents with chunk counts
        documents = db.query(Document).filter(
            Document.data_source_id.in_(data_source_ids)
        ).all()
        
        result = []
        for doc in documents:
            # Check if this is a code file with code units
            code_unit_count = db.query(CodeUnit).filter(
                CodeUnit.document_id == doc.id
            ).count()
            
            # Count regular chunks
            chunk_count = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc.id
            ).count()
            
            # Determine if this uses semantic code chunking
            is_code_file = code_unit_count > 0
            
            result.append({
                "id": doc.id,
                "title": doc.title or doc.file_path,
                "file_path": doc.file_path or "",
                "file_type": doc.file_type or "unknown",
                "chunk_count": code_unit_count if is_code_file else chunk_count,
                "chunk_type": "code_units" if is_code_file else "text_chunks",
                "data_source_id": doc.data_source_id,
                "data_source_name": data_source_map.get(doc.data_source_id, "Unknown"),
                "created_at": doc.created_at.isoformat() if doc.created_at else None
            })
        
        # Sort by data source name, then by file path
        result.sort(key=lambda x: (x["data_source_name"], x["file_path"]))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workspace embeddings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/document/{document_id}/chunks")
async def get_document_chunks(
    document_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get all chunks/code units for a document.
    
    For code files with AST-based parsing, returns code units (functions, classes, files)
    with their summaries. For other files, returns simple text chunks.
    """
    try:
        # Verify document exists
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check if this document has code units (AST-based parsing)
        code_units = db.query(CodeUnit).filter(
            CodeUnit.document_id == document_id
        ).order_by(CodeUnit.start_line).all()
        
        if code_units:
            # Return code units with summaries
            result = []
            for idx, unit in enumerate(code_units):
                metadata = unit.unit_metadata or {}
                result.append({
                    "id": unit.id,
                    "chunk_index": idx,
                    "chunk_type": "code_unit",
                    "unit_type": unit.unit_type,
                    "name": unit.name,
                    "signature": unit.signature,
                    "content": unit.code,
                    "summary": unit.summary,
                    "start_line": unit.start_line,
                    "end_line": unit.end_line,
                    "language": unit.language,
                    "metadata": {
                        "unit_type": unit.unit_type,
                        "name": unit.name,
                        "signature": unit.signature,
                        "language": unit.language,
                        "parent_id": unit.parent_id,
                        **metadata
                    }
                })
            return result
        
        # Fall back to regular document chunks
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).order_by(DocumentChunk.chunk_index).all()
        
        result = []
        for chunk in chunks:
            metadata = chunk.chunk_metadata or {}
            result.append({
                "id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "chunk_type": "text_chunk",
                "content": chunk.content,
                "start_line": metadata.get("start_line"),
                "end_line": metadata.get("end_line"),
                "metadata": metadata
            })
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document chunks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/stats/{workspace_id}")
async def get_embedding_stats(
    workspace_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get embedding statistics for a workspace."""
    try:
        # Verify workspace exists
        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        # Get all data sources for the workspace
        data_sources = db.query(DataSource).filter(
            DataSource.workspace_id == workspace_id
        ).all()
        
        data_source_ids = [ds.id for ds in data_sources]
        
        if not data_source_ids:
            return {
                "total_documents": 0,
                "total_chunks": 0,
                "by_source": [],
                "by_type": {}
            }
        
        # Count documents
        total_documents = db.query(Document).filter(
            Document.data_source_id.in_(data_source_ids)
        ).count()
        
        # Count chunks
        documents = db.query(Document).filter(
            Document.data_source_id.in_(data_source_ids)
        ).all()
        
        doc_ids = [doc.id for doc in documents]
        total_chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id.in_(doc_ids)
        ).count() if doc_ids else 0
        
        # Stats by source
        by_source = []
        for ds in data_sources:
            ds_docs = db.query(Document).filter(Document.data_source_id == ds.id).all()
            ds_doc_ids = [d.id for d in ds_docs]
            ds_chunks = db.query(DocumentChunk).filter(
                DocumentChunk.document_id.in_(ds_doc_ids)
            ).count() if ds_doc_ids else 0
            
            by_source.append({
                "name": ds.name,
                "source_type": ds.source_type,
                "documents": len(ds_docs),
                "chunks": ds_chunks
            })
        
        # Stats by file type
        by_type = {}
        for doc in documents:
            file_type = doc.file_type or "unknown"
            if file_type not in by_type:
                by_type[file_type] = {"documents": 0, "chunks": 0}
            by_type[file_type]["documents"] += 1
            
            doc_chunks = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc.id
            ).count()
            by_type[file_type]["chunks"] += doc_chunks
        
        return {
            "total_documents": total_documents,
            "total_chunks": total_chunks,
            "by_source": by_source,
            "by_type": by_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting embedding stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
