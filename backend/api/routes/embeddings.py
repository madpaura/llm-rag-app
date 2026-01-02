"""
Embeddings API routes for viewing and navigating document embeddings.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import structlog

from core.database import get_db, DataSource, Document, DocumentChunk, Workspace

logger = structlog.get_logger()
router = APIRouter()
security = HTTPBearer()


@router.get("/workspace/{workspace_id}")
async def get_workspace_embeddings(
    workspace_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get all documents with embedding info for a workspace."""
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
            # Count chunks for this document
            chunk_count = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc.id
            ).count()
            
            result.append({
                "id": doc.id,
                "title": doc.title or doc.file_path,
                "file_path": doc.file_path or "",
                "file_type": doc.file_type or "unknown",
                "chunk_count": chunk_count,
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
    """Get all chunks for a document."""
    try:
        # Verify document exists
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Get all chunks for the document
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).order_by(DocumentChunk.chunk_index).all()
        
        result = []
        for chunk in chunks:
            metadata = chunk.chunk_metadata or {}
            result.append({
                "id": chunk.id,
                "chunk_index": chunk.chunk_index,
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
