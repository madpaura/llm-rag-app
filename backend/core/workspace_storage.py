"""
Workspace-isolated storage management.
Provides utilities for managing workspace-specific directories and files.
"""
import os
import shutil
from pathlib import Path
from typing import Optional
import structlog

from .config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class WorkspaceStorage:
    """Manages workspace-isolated storage directories."""
    
    def __init__(self, workspace_id: int):
        self.workspace_id = workspace_id
        self.base_path = Path(settings.DATA_BASE_DIR) / str(workspace_id)
    
    @property
    def uploads_dir(self) -> Path:
        """Get workspace uploads directory."""
        path = self.base_path / "uploads"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def git_repos_dir(self) -> Path:
        """Get workspace git repos directory."""
        path = self.base_path / "git_repos"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def faiss_index_path(self) -> str:
        """Get workspace FAISS index path (without extension)."""
        path = self.base_path / "faiss_index"
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)
    
    @property
    def temp_dir(self) -> Path:
        """Get workspace temp directory for processing."""
        path = self.base_path / "temp"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_upload_path(self, filename: str) -> Path:
        """Get full path for an uploaded file."""
        return self.uploads_dir / filename
    
    def get_git_repo_path(self, repo_name: str) -> Path:
        """Get full path for a cloned git repository."""
        # Sanitize repo name
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in repo_name)
        return self.git_repos_dir / safe_name
    
    def ensure_directories(self):
        """Ensure all workspace directories exist."""
        self.uploads_dir
        self.git_repos_dir
        self.temp_dir
        logger.info(f"Ensured workspace directories for workspace {self.workspace_id}")
    
    def cleanup_temp(self):
        """Clean up temporary files."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Cleaned up temp directory for workspace {self.workspace_id}")
    
    def delete_workspace_data(self):
        """Delete all workspace data (use with caution)."""
        if self.base_path.exists():
            shutil.rmtree(self.base_path)
            logger.warning(f"Deleted all data for workspace {self.workspace_id}")
    
    def get_storage_stats(self) -> dict:
        """Get storage statistics for the workspace."""
        def get_dir_size(path: Path) -> int:
            total = 0
            if path.exists():
                for entry in path.rglob("*"):
                    if entry.is_file():
                        total += entry.stat().st_size
            return total
        
        return {
            "workspace_id": self.workspace_id,
            "uploads_size_bytes": get_dir_size(self.uploads_dir),
            "git_repos_size_bytes": get_dir_size(self.git_repos_dir),
            "faiss_index_size_bytes": get_dir_size(self.base_path / "faiss_index*") if (self.base_path / "faiss_index.index").exists() else 0,
            "total_size_bytes": get_dir_size(self.base_path)
        }


def get_workspace_storage(workspace_id: int) -> WorkspaceStorage:
    """Get workspace storage manager."""
    return WorkspaceStorage(workspace_id)


def migrate_legacy_data(workspace_id: int):
    """
    Migrate data from legacy non-isolated storage to workspace-isolated storage.
    Call this once per workspace during migration.
    """
    storage = get_workspace_storage(workspace_id)
    storage.ensure_directories()
    
    # Legacy paths (if they exist)
    legacy_uploads = Path("./data/uploads")
    legacy_git_repos = Path("./data/git_repos")
    legacy_faiss = Path("./data/faiss_index")
    
    # Note: Actual migration would need to filter by workspace_id from database
    # This is a placeholder for the migration logic
    logger.info(f"Migration placeholder for workspace {workspace_id}")
    logger.info("To migrate legacy data, you need to:")
    logger.info("1. Query documents/data_sources for this workspace from DB")
    logger.info("2. Copy relevant files to workspace-isolated directories")
    logger.info("3. Update file paths in database records")
    logger.info("4. Rebuild FAISS index for this workspace")
