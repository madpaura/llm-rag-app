#!/usr/bin/env python3
"""
Reset database - drop all tables and recreate them.
WARNING: This will delete ALL data!
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import get_settings
from sqlalchemy import create_engine, text

settings = get_settings()


def reset_database():
    """Drop all tables and reset the database."""
    print("=" * 50)
    print("DATABASE RESET")
    print("=" * 50)
    print("\nWARNING: This will delete ALL data!")
    
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Drop all tables in public schema
        print("\nDropping all tables...")
        
        # Get all table names
        result = conn.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """))
        tables = [row[0] for row in result.fetchall()]
        
        if tables:
            print(f"Found {len(tables)} tables: {', '.join(tables)}")
            
            # Drop all tables with CASCADE to handle foreign keys
            for table in tables:
                print(f"  Dropping {table}...")
                conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
            
            conn.commit()
            
            print("\n✓ All tables dropped successfully!")
        else:
            print("No tables found in database.")
        
        print("\n" + "=" * 50)
        print("Database reset complete!")
        print("=" * 50)
        print("\nRestart the backend to recreate tables and admin user.")
        
        return True


if __name__ == "__main__":
    confirm = input("Are you sure you want to reset the database? (yes/no): ")
    if confirm.lower() == 'yes':
        try:
            reset_database()
        except Exception as e:
            print(f"Reset failed: {e}")
            sys.exit(1)
    else:
        print("Cancelled.")
