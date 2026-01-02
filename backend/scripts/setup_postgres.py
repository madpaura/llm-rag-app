#!/usr/bin/env python3
"""
PostgreSQL database setup script.
Creates the database, user, and initializes tables.

Usage:
    python scripts/setup_postgres.py

Prerequisites:
    - PostgreSQL server running
    - psycopg2-binary installed
    - Admin access to PostgreSQL (or use environment variables)
"""
import os
import sys
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_database(admin_user: str, admin_password: str, host: str, port: int,
                   db_name: str, db_user: str, db_password: str):
    """Create PostgreSQL database and user."""
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    
    print(f"Connecting to PostgreSQL as {admin_user}@{host}:{port}...")
    
    # Connect to default 'postgres' database as admin
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=admin_user,
        password=admin_password,
        database='postgres'
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    try:
        # Check if user exists
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (db_user,))
        if not cursor.fetchone():
            print(f"Creating user '{db_user}'...")
            cursor.execute(f"CREATE USER {db_user} WITH PASSWORD %s", (db_password,))
            print(f"User '{db_user}' created.")
        else:
            print(f"User '{db_user}' already exists.")
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        if not cursor.fetchone():
            print(f"Creating database '{db_name}'...")
            cursor.execute(f"CREATE DATABASE {db_name} OWNER {db_user}")
            print(f"Database '{db_name}' created.")
        else:
            print(f"Database '{db_name}' already exists.")
        
        # Grant privileges
        cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user}")
        print(f"Granted privileges to '{db_user}' on '{db_name}'.")
        
    finally:
        cursor.close()
        conn.close()
    
    print("Database setup complete!")


def init_tables():
    """Initialize database tables using SQLAlchemy models."""
    print("Initializing database tables...")
    
    from core.database import Base, engine
    from core.config import get_settings
    
    settings = get_settings()
    print(f"Using database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


def migrate_from_sqlite(sqlite_path: str):
    """
    Migrate data from SQLite to PostgreSQL.
    This is a basic migration - for production, use proper migration tools.
    """
    import sqlite3
    from sqlalchemy.orm import Session
    from core.database import engine, SessionLocal
    from core.database import User, Workspace, WorkspaceMember, DataSource, Document, DocumentChunk, ChatSession, ChatMessage
    
    print(f"Migrating data from SQLite: {sqlite_path}")
    
    if not os.path.exists(sqlite_path):
        print(f"SQLite database not found: {sqlite_path}")
        return
    
    # Connect to SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()
    
    # Get PostgreSQL session
    pg_session = SessionLocal()
    
    try:
        # Migration order matters due to foreign keys
        tables_to_migrate = [
            ('users', User),
            ('workspaces', Workspace),
            ('workspace_members', WorkspaceMember),
            ('data_sources', DataSource),
            ('documents', Document),
            ('document_chunks', DocumentChunk),
            ('chat_sessions', ChatSession),
            ('chat_messages', ChatMessage),
        ]
        
        for table_name, model_class in tables_to_migrate:
            print(f"Migrating table: {table_name}...")
            
            try:
                sqlite_cursor.execute(f"SELECT * FROM {table_name}")
                rows = sqlite_cursor.fetchall()
                
                if not rows:
                    print(f"  No data in {table_name}")
                    continue
                
                # Get column names
                columns = [description[0] for description in sqlite_cursor.description]
                
                for row in rows:
                    row_dict = dict(zip(columns, row))
                    
                    # Handle JSON columns (stored as text in SQLite)
                    import json
                    for col in ['config', 'doc_metadata', 'chunk_metadata', 'message_metadata', 'unit_metadata']:
                        if col in row_dict and row_dict[col]:
                            try:
                                if isinstance(row_dict[col], str):
                                    row_dict[col] = json.loads(row_dict[col])
                            except json.JSONDecodeError:
                                pass
                    
                    # Create model instance
                    obj = model_class(**row_dict)
                    pg_session.merge(obj)
                
                pg_session.commit()
                print(f"  Migrated {len(rows)} rows from {table_name}")
                
            except Exception as e:
                print(f"  Error migrating {table_name}: {e}")
                pg_session.rollback()
        
        print("Migration complete!")
        
    finally:
        sqlite_cursor.close()
        sqlite_conn.close()
        pg_session.close()


def main():
    parser = argparse.ArgumentParser(description='PostgreSQL database setup for RAG application')
    parser.add_argument('--admin-user', default='postgres', help='PostgreSQL admin username')
    parser.add_argument('--admin-password', default='', help='PostgreSQL admin password')
    parser.add_argument('--host', default='localhost', help='PostgreSQL host')
    parser.add_argument('--port', type=int, default=5432, help='PostgreSQL port')
    parser.add_argument('--db-name', default='rag_db', help='Database name to create')
    parser.add_argument('--db-user', default='rag_user', help='Database user to create')
    parser.add_argument('--db-password', default='rag_password', help='Database user password')
    parser.add_argument('--skip-create', action='store_true', help='Skip database/user creation')
    parser.add_argument('--migrate-sqlite', type=str, help='Path to SQLite database to migrate from')
    
    args = parser.parse_args()
    
    # Use environment variables if available
    admin_user = os.environ.get('POSTGRES_ADMIN_USER', args.admin_user)
    admin_password = os.environ.get('POSTGRES_ADMIN_PASSWORD', args.admin_password)
    host = os.environ.get('POSTGRES_HOST', args.host)
    port = int(os.environ.get('POSTGRES_PORT', args.port))
    db_name = os.environ.get('POSTGRES_DB', args.db_name)
    db_user = os.environ.get('POSTGRES_USER', args.db_user)
    db_password = os.environ.get('POSTGRES_PASSWORD', args.db_password)
    
    if not args.skip_create:
        if not admin_password:
            print("Warning: No admin password provided. Set POSTGRES_ADMIN_PASSWORD or use --admin-password")
            print("Attempting connection without password (peer authentication)...")
        
        try:
            create_database(admin_user, admin_password, host, port, db_name, db_user, db_password)
        except Exception as e:
            print(f"Error creating database: {e}")
            print("You may need to create the database manually or provide admin credentials.")
            print(f"\nManual setup commands:")
            print(f"  sudo -u postgres psql")
            print(f"  CREATE USER {db_user} WITH PASSWORD '{db_password}';")
            print(f"  CREATE DATABASE {db_name} OWNER {db_user};")
            print(f"  GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};")
            return 1
    
    # Initialize tables
    init_tables()
    
    # Migrate from SQLite if requested
    if args.migrate_sqlite:
        migrate_from_sqlite(args.migrate_sqlite)
    
    print("\n" + "="*50)
    print("Setup complete!")
    print("="*50)
    print(f"\nUpdate your .env file with:")
    print(f"DATABASE_URL=postgresql://{db_user}:{db_password}@{host}:{port}/{db_name}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
