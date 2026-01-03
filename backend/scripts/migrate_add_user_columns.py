#!/usr/bin/env python3
"""
Migration script to add password and permissions columns to users table.
Run this once to update existing database schema.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import get_settings
from sqlalchemy import create_engine, text

settings = get_settings()


def migrate():
    """Add missing columns to users table."""
    print("=" * 50)
    print("User Table Migration")
    print("=" * 50)
    
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Check if password column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'password'
        """))
        password_exists = result.fetchone() is not None
        
        # Check if permissions column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'permissions'
        """))
        permissions_exists = result.fetchone() is not None
        
        if password_exists and permissions_exists:
            print("✓ All columns already exist. No migration needed.")
            return True
        
        # Add password column if missing
        if not password_exists:
            print("Adding 'password' column...")
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN password VARCHAR NOT NULL DEFAULT 'changeme'
            """))
            print("✓ Added 'password' column with default value 'changeme'")
        else:
            print("✓ 'password' column already exists")
        
        # Add permissions column if missing
        if not permissions_exists:
            print("Adding 'permissions' column...")
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN permissions JSON DEFAULT '{}'
            """))
            print("✓ Added 'permissions' column")
        else:
            print("✓ 'permissions' column already exists")
        
        conn.commit()
        
        print("\n" + "=" * 50)
        print("Migration complete!")
        print("=" * 50)
        print("\nIMPORTANT: Update passwords for existing users!")
        print("Default password for existing users is: 'changeme'")
        
        return True


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)
