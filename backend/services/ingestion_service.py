"""
Data ingestion service for Git repositories, Confluence, and documents.
"""
from typing import List, Dict, Any, Optional
import os
import tempfile
import shutil
from pathlib import Path
import asyncio
import aiofiles
import structlog
from git import Repo, GitCommandError
import requests
from bs4 import BeautifulSoup
import PyPDF2
from docx import Document as DocxDocument

from core.config import get_settings
from core.database import get_db, DataSource, Document, DocumentChunk
from services.vector_service import VectorService

logger = structlog.get_logger()
settings = get_settings()

class TextChunker:
    """Service for chunking text into smaller pieces."""
    
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
    
    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks."""
        if not text.strip():
            return []
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]
            
            # Try to break at sentence boundaries
            if end < len(text):
                last_period = chunk_text.rfind('.')
                last_newline = chunk_text.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > start + self.chunk_size // 2:
                    chunk_text = text[start:start + break_point + 1]
                    end = start + break_point + 1
            
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata.update({
                'chunk_index': chunk_index,
                'start_char': start,
                'end_char': end
            })
            
            chunks.append({
                'content': chunk_text.strip(),
                'metadata': chunk_metadata
            })
            
            start = end - self.chunk_overlap
            chunk_index += 1
        
        return chunks

class GitIngestionService:
    """Service for ingesting Git repositories."""
    
    def __init__(self):
        self.clone_dir = Path(settings.GIT_CLONE_DIR)
        self.clone_dir.mkdir(parents=True, exist_ok=True)
        self.chunker = TextChunker()
    
    async def ingest_repository(self, repo_url: str, workspace_id: int, branch: str = "main") -> Dict[str, Any]:
        """Clone and ingest a Git repository."""
        try:
            logger.info(f"Starting Git ingestion for {repo_url}")
            
            # Create temporary directory for cloning
            with tempfile.TemporaryDirectory() as temp_dir:
                repo_path = Path(temp_dir) / "repo"
                
                # Clone repository
                try:
                    repo = Repo.clone_from(repo_url, repo_path, branch=branch, depth=1)
                    logger.info(f"Cloned repository to {repo_path}")
                except GitCommandError as e:
                    logger.error(f"Failed to clone repository: {e}")
                    return {"success": False, "error": str(e)}
                
                # Process files
                documents = []
                supported_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', 
                                      '.md', '.txt', '.rst', '.json', '.yaml', '.yml'}
                
                for file_path in repo_path.rglob('*'):
                    if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                        try:
                            content = await self._read_file(file_path)
                            if content:
                                relative_path = file_path.relative_to(repo_path)
                                documents.append({
                                    'title': str(relative_path),
                                    'content': content,
                                    'file_path': str(relative_path),
                                    'file_type': file_path.suffix.lower(),
                                    'source_type': 'git',
                                    'workspace_id': workspace_id,
                                    'metadata': {
                                        'repo_url': repo_url,
                                        'branch': branch,
                                        'file_size': file_path.stat().st_size
                                    }
                                })
                        except Exception as e:
                            logger.warning(f"Failed to read file {file_path}: {e}")
                
                logger.info(f"Processed {len(documents)} files from repository")
                return {"success": True, "documents": documents}
                
        except Exception as e:
            logger.error(f"Error ingesting Git repository: {e}")
            return {"success": False, "error": str(e)}
    
    async def _read_file(self, file_path: Path) -> Optional[str]:
        """Read file content safely."""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = await f.read()
                return content
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return None

class ConfluenceIngestionService:
    """Service for ingesting Confluence pages."""
    
    def __init__(self):
        self.chunker = TextChunker()
    
    async def ingest_space(self, space_key: str, workspace_id: int, 
                          base_url: str = None, username: str = None, 
                          api_token: str = None) -> Dict[str, Any]:
        """Ingest pages from a Confluence space."""
        try:
            base_url = base_url or settings.CONFLUENCE_BASE_URL
            username = username or settings.CONFLUENCE_USERNAME
            api_token = api_token or settings.CONFLUENCE_API_TOKEN
            
            if not all([base_url, username, api_token]):
                return {"success": False, "error": "Missing Confluence credentials"}
            
            logger.info(f"Starting Confluence ingestion for space {space_key}")
            
            # Get pages from space
            pages = await self._get_space_pages(base_url, space_key, username, api_token)
            
            documents = []
            for page in pages:
                try:
                    content = await self._get_page_content(base_url, page['id'], username, api_token)
                    if content:
                        documents.append({
                            'title': page['title'],
                            'content': content,
                            'file_path': f"confluence/{space_key}/{page['id']}",
                            'file_type': 'confluence',
                            'source_type': 'confluence',
                            'workspace_id': workspace_id,
                            'metadata': {
                                'space_key': space_key,
                                'page_id': page['id'],
                                'page_url': f"{base_url}/pages/viewpage.action?pageId={page['id']}"
                            }
                        })
                except Exception as e:
                    logger.warning(f"Failed to process page {page['id']}: {e}")
            
            logger.info(f"Processed {len(documents)} pages from Confluence space")
            return {"success": True, "documents": documents}
            
        except Exception as e:
            logger.error(f"Error ingesting Confluence space: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_space_pages(self, base_url: str, space_key: str, 
                              username: str, api_token: str) -> List[Dict[str, Any]]:
        """Get all pages from a Confluence space."""
        pages = []
        start = 0
        limit = 50
        
        while True:
            url = f"{base_url}/rest/api/content"
            params = {
                'spaceKey': space_key,
                'type': 'page',
                'status': 'current',
                'start': start,
                'limit': limit
            }
            
            response = requests.get(url, params=params, auth=(username, api_token))
            response.raise_for_status()
            
            data = response.json()
            pages.extend(data['results'])
            
            if len(data['results']) < limit:
                break
            
            start += limit
        
        return pages
    
    async def _get_page_content(self, base_url: str, page_id: str, 
                               username: str, api_token: str) -> Optional[str]:
        """Get content of a specific Confluence page."""
        try:
            url = f"{base_url}/rest/api/content/{page_id}"
            params = {'expand': 'body.storage'}
            
            response = requests.get(url, params=params, auth=(username, api_token))
            response.raise_for_status()
            
            data = response.json()
            html_content = data['body']['storage']['value']
            
            # Convert HTML to plain text
            soup = BeautifulSoup(html_content, 'html.parser')
            text_content = soup.get_text(separator='\n', strip=True)
            
            return text_content
            
        except Exception as e:
            logger.warning(f"Failed to get content for page {page_id}: {e}")
            return None

class DocumentIngestionService:
    """Service for ingesting PDF and Word documents."""
    
    def __init__(self):
        self.chunker = TextChunker()
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def ingest_document(self, file_path: str, workspace_id: int, 
                             original_filename: str = None) -> Dict[str, Any]:
        """Ingest a document file."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return {"success": False, "error": "File not found"}
            
            logger.info(f"Starting document ingestion for {file_path}")
            
            # Extract text based on file type
            if file_path.suffix.lower() == '.pdf':
                content = await self._extract_pdf_text(file_path)
            elif file_path.suffix.lower() in ['.docx', '.doc']:
                content = await self._extract_docx_text(file_path)
            else:
                # Try to read as text file
                async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = await f.read()
            
            if not content:
                return {"success": False, "error": "Could not extract text from document"}
            
            documents = [{
                'title': original_filename or file_path.name,
                'content': content,
                'file_path': str(file_path),
                'file_type': file_path.suffix.lower(),
                'source_type': 'document',
                'workspace_id': workspace_id,
                'metadata': {
                    'original_filename': original_filename,
                    'file_size': file_path.stat().st_size
                }
            }]
            
            logger.info(f"Extracted text from document: {len(content)} characters")
            return {"success": True, "documents": documents}
            
        except Exception as e:
            logger.error(f"Error ingesting document: {e}")
            return {"success": False, "error": str(e)}
    
    async def _extract_pdf_text(self, file_path: Path) -> str:
        """Extract text from PDF file."""
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return ""
    
    async def _extract_docx_text(self, file_path: Path) -> str:
        """Extract text from Word document."""
        try:
            doc = DocxDocument(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting DOCX text: {e}")
            return ""

class IngestionOrchestrator:
    """Main ingestion service that coordinates all ingestion types."""
    
    def __init__(self):
        self.git_service = GitIngestionService()
        self.confluence_service = ConfluenceIngestionService()
        self.document_service = DocumentIngestionService()
        self.vector_service = VectorService()
        self.chunker = TextChunker()
    
    async def ingest_data_source(self, data_source_id: int) -> Dict[str, Any]:
        """Ingest data from a data source."""
        try:
            # Get data source from database
            db = next(get_db())
            data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
            
            if not data_source:
                return {"success": False, "error": "Data source not found"}
            
            # Update status to processing
            data_source.status = "processing"
            db.commit()
            
            # Ingest based on source type
            if data_source.source_type == "git":
                result = await self.git_service.ingest_repository(
                    data_source.source_url, 
                    data_source.workspace_id,
                    data_source.config.get('branch', 'main') if data_source.config else 'main'
                )
            elif data_source.source_type == "confluence":
                config = data_source.config or {}
                result = await self.confluence_service.ingest_space(
                    config.get('space_key'),
                    data_source.workspace_id,
                    config.get('base_url'),
                    config.get('username'),
                    config.get('api_token')
                )
            elif data_source.source_type == "document":
                result = await self.document_service.ingest_document(
                    data_source.source_url,  # File path for documents
                    data_source.workspace_id,
                    data_source.config.get('original_filename') if data_source.config else None
                )
            else:
                result = {"success": False, "error": f"Unsupported source type: {data_source.source_type}"}
            
            if result["success"]:
                # Process and store documents
                documents = result["documents"]
                await self._process_documents(documents, data_source_id, db)
                
                # Update status to completed
                data_source.status = "completed"
                data_source.last_ingested = func.now()
                db.commit()
                
                logger.info(f"Successfully ingested {len(documents)} documents from data source {data_source_id}")
                return {"success": True, "documents_count": len(documents)}
            else:
                # Update status to failed
                data_source.status = "failed"
                db.commit()
                return result
                
        except Exception as e:
            logger.error(f"Error in ingestion orchestrator: {e}")
            return {"success": False, "error": str(e)}
    
    async def _process_documents(self, documents: List[Dict[str, Any]], 
                               data_source_id: int, db) -> None:
        """Process documents: chunk, embed, and store."""
        try:
            all_chunks = []
            
            for doc_data in documents:
                # Create document record
                document = Document(
                    data_source_id=data_source_id,
                    title=doc_data['title'],
                    content=doc_data['content'],
                    file_path=doc_data.get('file_path'),
                    file_type=doc_data.get('file_type'),
                    metadata=doc_data.get('metadata', {})
                )
                db.add(document)
                db.flush()  # Get the ID
                
                # Chunk the document
                chunks = self.chunker.chunk_text(doc_data['content'], doc_data.get('metadata', {}))
                
                for chunk_data in chunks:
                    chunk = DocumentChunk(
                        document_id=document.id,
                        chunk_index=chunk_data['metadata']['chunk_index'],
                        content=chunk_data['content'],
                        metadata=chunk_data['metadata']
                    )
                    db.add(chunk)
                    db.flush()
                    
                    # Prepare for vector storage
                    all_chunks.append({
                        'id': f"chunk_{chunk.id}",
                        'content': chunk_data['content'],
                        'title': doc_data['title'],
                        'source': doc_data.get('file_path', ''),
                        'workspace_id': doc_data['workspace_id'],
                        'document_id': document.id,
                        'chunk_id': chunk.id,
                        **chunk_data['metadata']
                    })
            
            # Add to vector store
            if all_chunks:
                success = await self.vector_service.add_documents(all_chunks)
                if not success:
                    logger.error("Failed to add documents to vector store")
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error processing documents: {e}")
            raise
