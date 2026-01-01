"""
Database backup and restore functionality.
Supports SQLite and provides utilities for data migration.
"""
import os
import shutil
import sqlite3
import json
import gzip
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import structlog
import asyncio

from .config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class BackupService:
    """
    Service for database backup and restore operations.
    Supports full backups, incremental backups, and data export.
    """
    
    def __init__(self, backup_dir: str = None):
        self.backup_dir = Path(backup_dir or "./data/backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger()
    
    def _get_db_path(self) -> Path:
        """Extract database file path from URL."""
        url = settings.DATABASE_URL
        if url.startswith("sqlite:///"):
            return Path(url.replace("sqlite:///", ""))
        raise ValueError("Backup only supported for SQLite databases")
    
    def create_backup(self, name: str = None, compress: bool = True) -> Dict[str, Any]:
        """
        Create a full database backup.
        
        Args:
            name: Optional backup name (default: timestamp)
            compress: Whether to compress the backup
            
        Returns:
            Backup metadata
        """
        try:
            db_path = self._get_db_path()
            
            if not db_path.exists():
                return {"success": False, "error": "Database file not found"}
            
            # Generate backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = name or f"backup_{timestamp}"
            
            if compress:
                backup_file = self.backup_dir / f"{backup_name}.db.gz"
            else:
                backup_file = self.backup_dir / f"{backup_name}.db"
            
            # Create backup using SQLite backup API
            self.logger.info(f"Creating backup: {backup_file}")
            
            # Connect to source database
            source = sqlite3.connect(str(db_path))
            
            if compress:
                # Backup to memory, then compress
                memory_db = sqlite3.connect(":memory:")
                source.backup(memory_db)
                
                # Dump to bytes and compress
                dump = "\n".join(memory_db.iterdump())
                with gzip.open(backup_file, 'wt', encoding='utf-8') as f:
                    f.write(dump)
                memory_db.close()
            else:
                # Direct file backup
                dest = sqlite3.connect(str(backup_file))
                source.backup(dest)
                dest.close()
            
            source.close()
            
            # Get backup size
            backup_size = backup_file.stat().st_size
            
            # Create metadata file
            metadata = {
                "name": backup_name,
                "timestamp": timestamp,
                "source_db": str(db_path),
                "backup_file": str(backup_file),
                "compressed": compress,
                "size_bytes": backup_size,
                "created_at": datetime.now().isoformat()
            }
            
            metadata_file = self.backup_dir / f"{backup_name}.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            self.logger.info(f"Backup created successfully: {backup_file} ({backup_size} bytes)")
            
            return {
                "success": True,
                "backup_file": str(backup_file),
                "metadata": metadata
            }
            
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            return {"success": False, "error": str(e)}
    
    def restore_backup(self, backup_name: str, target_db: str = None) -> Dict[str, Any]:
        """
        Restore database from backup.
        
        Args:
            backup_name: Name of backup to restore
            target_db: Target database path (default: original location)
            
        Returns:
            Restore result
        """
        try:
            # Find backup file
            backup_file = None
            for ext in ['.db.gz', '.db']:
                candidate = self.backup_dir / f"{backup_name}{ext}"
                if candidate.exists():
                    backup_file = candidate
                    break
            
            if not backup_file:
                return {"success": False, "error": f"Backup not found: {backup_name}"}
            
            # Determine target
            if target_db:
                target_path = Path(target_db)
            else:
                target_path = self._get_db_path()
            
            # Create backup of current database before restore
            if target_path.exists():
                pre_restore_backup = target_path.with_suffix('.pre_restore.db')
                shutil.copy2(target_path, pre_restore_backup)
                self.logger.info(f"Created pre-restore backup: {pre_restore_backup}")
            
            self.logger.info(f"Restoring backup: {backup_file} -> {target_path}")
            
            if backup_file.suffix == '.gz':
                # Decompress and restore
                with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
                    sql_dump = f.read()
                
                # Remove existing database
                if target_path.exists():
                    target_path.unlink()
                
                # Create new database from dump
                conn = sqlite3.connect(str(target_path))
                conn.executescript(sql_dump)
                conn.close()
            else:
                # Direct file restore
                shutil.copy2(backup_file, target_path)
            
            self.logger.info(f"Backup restored successfully to {target_path}")
            
            return {
                "success": True,
                "restored_from": str(backup_file),
                "restored_to": str(target_path)
            }
            
        except Exception as e:
            self.logger.error(f"Restore failed: {e}")
            return {"success": False, "error": str(e)}
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups."""
        backups = []
        
        for metadata_file in self.backup_dir.glob("*.json"):
            try:
                with open(metadata_file) as f:
                    metadata = json.load(f)
                    
                # Check if backup file still exists
                backup_file = Path(metadata.get("backup_file", ""))
                metadata["exists"] = backup_file.exists()
                
                backups.append(metadata)
            except Exception as e:
                self.logger.warning(f"Failed to read backup metadata: {metadata_file}: {e}")
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return backups
    
    def delete_backup(self, backup_name: str) -> Dict[str, Any]:
        """Delete a backup."""
        try:
            deleted_files = []
            
            # Delete backup file
            for ext in ['.db.gz', '.db']:
                backup_file = self.backup_dir / f"{backup_name}{ext}"
                if backup_file.exists():
                    backup_file.unlink()
                    deleted_files.append(str(backup_file))
            
            # Delete metadata file
            metadata_file = self.backup_dir / f"{backup_name}.json"
            if metadata_file.exists():
                metadata_file.unlink()
                deleted_files.append(str(metadata_file))
            
            if deleted_files:
                self.logger.info(f"Deleted backup: {backup_name}")
                return {"success": True, "deleted_files": deleted_files}
            else:
                return {"success": False, "error": "Backup not found"}
                
        except Exception as e:
            self.logger.error(f"Delete backup failed: {e}")
            return {"success": False, "error": str(e)}
    
    def cleanup_old_backups(self, keep_count: int = 5) -> Dict[str, Any]:
        """
        Remove old backups, keeping only the most recent ones.
        
        Args:
            keep_count: Number of backups to keep
            
        Returns:
            Cleanup result
        """
        try:
            backups = self.list_backups()
            
            if len(backups) <= keep_count:
                return {"success": True, "deleted": 0, "kept": len(backups)}
            
            # Delete oldest backups
            to_delete = backups[keep_count:]
            deleted = 0
            
            for backup in to_delete:
                result = self.delete_backup(backup["name"])
                if result["success"]:
                    deleted += 1
            
            self.logger.info(f"Cleanup complete: deleted {deleted} old backups, kept {keep_count}")
            
            return {
                "success": True,
                "deleted": deleted,
                "kept": keep_count
            }
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return {"success": False, "error": str(e)}
    
    def export_data(self, output_file: str = None, tables: List[str] = None) -> Dict[str, Any]:
        """
        Export database data to JSON format.
        
        Args:
            output_file: Output file path
            tables: List of tables to export (default: all)
            
        Returns:
            Export result
        """
        try:
            db_path = self._get_db_path()
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get list of tables
            if tables is None:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
            
            # Export each table
            data = {}
            for table in tables:
                try:
                    cursor.execute(f"SELECT * FROM {table}")
                    rows = cursor.fetchall()
                    data[table] = [dict(row) for row in rows]
                except Exception as e:
                    self.logger.warning(f"Failed to export table {table}: {e}")
            
            conn.close()
            
            # Write to file
            if output_file is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = self.backup_dir / f"export_{timestamp}.json"
            
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            self.logger.info(f"Data exported to {output_file}")
            
            return {
                "success": True,
                "output_file": str(output_file),
                "tables_exported": list(data.keys()),
                "row_counts": {k: len(v) for k, v in data.items()}
            }
            
        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            return {"success": False, "error": str(e)}


# Singleton instance
_backup_service: Optional[BackupService] = None


def get_backup_service() -> BackupService:
    """Get or create backup service singleton."""
    global _backup_service
    if _backup_service is None:
        _backup_service = BackupService()
    return _backup_service


async def scheduled_backup():
    """
    Scheduled backup task.
    Can be called periodically by a scheduler.
    """
    service = get_backup_service()
    
    # Create backup
    result = service.create_backup(compress=True)
    
    if result["success"]:
        # Cleanup old backups
        service.cleanup_old_backups(keep_count=5)
    
    return result
