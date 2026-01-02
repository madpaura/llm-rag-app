"""
Database configuration and models.
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Generator
import structlog

from .config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# Database setup with proper connection pooling for concurrent operations
def create_db_engine():
    """Create database engine based on configuration."""
    db_url = settings.DATABASE_URL
    
    if db_url.startswith("sqlite"):
        # SQLite-specific settings (for development/testing only)
        logger.warning("Using SQLite - not recommended for production with concurrent users")
        engine = create_engine(
            db_url,
            connect_args={
                "check_same_thread": False,
                "timeout": 30
            },
            pool_pre_ping=True,
            echo=False
        )
        
        # Enable WAL mode for better concurrent access
        from sqlalchemy import event
        
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()
    else:
        # PostgreSQL with optimized connection pooling for multi-user scenarios
        from sqlalchemy.pool import QueuePool
        
        engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_timeout=settings.DATABASE_POOL_TIMEOUT,
            pool_recycle=settings.DATABASE_POOL_RECYCLE,
            pool_pre_ping=True,  # Verify connections before use
            echo=False,
            # PostgreSQL-specific optimizations
            connect_args={
                "options": "-c timezone=utc"
            } if "postgresql" in db_url else {}
        )
        logger.info(f"PostgreSQL connection pool: size={settings.DATABASE_POOL_SIZE}, "
                   f"max_overflow={settings.DATABASE_MAX_OVERFLOW}")
    
    return engine

engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class User(Base):
    """User model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    workspaces = relationship("WorkspaceMember", back_populates="user")
    chat_sessions = relationship("ChatSession", back_populates="user")

class Workspace(Base):
    """Workspace model for project isolation."""
    __tablename__ = "workspaces"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    members = relationship("WorkspaceMember", back_populates="workspace")
    data_sources = relationship("DataSource", back_populates="workspace")
    chat_sessions = relationship("ChatSession", back_populates="workspace")

class WorkspaceMember(Base):
    """Workspace membership with roles."""
    __tablename__ = "workspace_members"
    
    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String, default="viewer")  # viewer, editor, admin
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", back_populates="workspaces")

class DataSource(Base):
    """Data sources for ingestion."""
    __tablename__ = "data_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    name = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # git, confluence, document
    source_url = Column(String, nullable=True)
    config = Column(JSON, nullable=True)  # Source-specific configuration
    status = Column(String, default="pending")  # pending, processing, completed, failed
    last_ingested = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    workspace = relationship("Workspace", back_populates="data_sources")
    documents = relationship("Document", back_populates="data_source")

class Document(Base):
    """Individual documents from data sources."""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    data_source_id = Column(Integer, ForeignKey("data_sources.id"))
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    file_path = Column(String, nullable=True)
    file_type = Column(String, nullable=True)
    doc_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    data_source = relationship("DataSource", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document")

class DocumentChunk(Base):
    """Document chunks for vector storage."""
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    chunk_metadata = Column(JSON, nullable=True)
    vector_id = Column(String, nullable=True)  # ID in vector database
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="chunks")

class ChatSession(Base):
    """Chat sessions for conversation history."""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    workspace = relationship("Workspace", back_populates="chat_sessions")
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session")

class ChatMessage(Base):
    """Individual chat messages."""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON, nullable=True)  # Sources, tokens, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")


class CodeUnit(Base):
    """Code units extracted from source files (functions, classes, files)."""
    __tablename__ = "code_units"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    unit_type = Column(String, nullable=False)  # function, method, class, struct, file
    name = Column(String, nullable=False)
    signature = Column(String, nullable=True)  # Function signature or class declaration
    code = Column(Text, nullable=False)  # Full source code of the unit
    summary = Column(Text, nullable=True)  # LLM-generated summary
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    parent_id = Column(Integer, ForeignKey("code_units.id"), nullable=True)  # Parent class/file
    language = Column(String, nullable=False)  # c, cpp
    vector_id = Column(String, nullable=True)  # ID in vector database
    unit_metadata = Column(JSON, nullable=True)  # Additional metadata (dependencies, patterns)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", backref="code_units")
    parent = relationship("CodeUnit", remote_side=[id], backref="children")


class CodeCallGraph(Base):
    """Call graph relationships between code units."""
    __tablename__ = "code_call_graph"
    
    id = Column(Integer, primary_key=True, index=True)
    caller_id = Column(Integer, ForeignKey("code_units.id"), nullable=False)
    callee_name = Column(String, nullable=False)  # Name of called function
    callee_id = Column(Integer, ForeignKey("code_units.id"), nullable=True)  # Resolved callee (if found)
    call_line = Column(Integer, nullable=True)  # Line number of the call
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    caller = relationship("CodeUnit", foreign_keys=[caller_id], backref="outgoing_calls")
    callee = relationship("CodeUnit", foreign_keys=[callee_id], backref="incoming_calls")

# Database dependency
def get_db() -> Generator[Session, None, None]:
    """Database dependency for FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def init_db():
    """Initialize database tables."""
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
