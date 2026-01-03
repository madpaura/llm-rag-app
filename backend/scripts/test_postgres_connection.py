#!/usr/bin/env python3
"""
PostgreSQL connectivity test script.
Tests database connection, permissions, and basic operations.

Usage:
    python scripts/test_postgres_connection.py
    python scripts/test_postgres_connection.py --verbose
"""
import os
import sys
import argparse
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_connection(verbose: bool = False):
    """Test basic database connection."""
    print("\n" + "="*60)
    print("PostgreSQL Connection Test")
    print("="*60 + "\n")
    
    from core.config import get_settings
    
    settings = get_settings()
    db_url = settings.DATABASE_URL
    
    # Mask password in output
    if '@' in db_url:
        parts = db_url.split('@')
        user_pass = parts[0].split('://')[-1]
        if ':' in user_pass:
            user = user_pass.split(':')[0]
            masked_url = db_url.replace(user_pass, f"{user}:****")
        else:
            masked_url = db_url
    else:
        masked_url = db_url
    
    print(f"Database URL: {masked_url}\n")
    
    # Test 1: Basic Connection
    print("Test 1: Basic Connection")
    print("-" * 40)
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        if not db_url.startswith("postgresql://"):
            print("❌ FAILED: DATABASE_URL must be a PostgreSQL connection string")
            print(f"   Current: {db_url}")
            return False
        
        parsed = urlparse(db_url)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:]  # Remove leading '/'
        )
        
        print(f"✓ Connected to PostgreSQL")
        print(f"  Host: {parsed.hostname}")
        print(f"  Port: {parsed.port or 5432}")
        print(f"  Database: {parsed.path[1:]}")
        print(f"  User: {parsed.username}")
        
        # Get PostgreSQL version
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"  Version: {version.split(',')[0]}")
        
        cursor.close()
        conn.close()
        print("✓ Connection closed successfully\n")
        
    except ImportError:
        print("❌ FAILED: psycopg2 not installed")
        print("   Install with: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ FAILED: {e}\n")
        return False
    
    # Test 2: Database Permissions
    print("Test 2: Database Permissions")
    print("-" * 40)
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        parsed = urlparse(db_url)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:]
        )
        cursor = conn.cursor()
        
        # Test CREATE TABLE permission
        test_table = f"_test_permissions_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        cursor.execute(f"""
            CREATE TABLE {test_table} (
                id SERIAL PRIMARY KEY,
                test_data VARCHAR(100)
            )
        """)
        print("✓ CREATE TABLE permission")
        
        # Test INSERT permission
        cursor.execute(f"INSERT INTO {test_table} (test_data) VALUES (%s)", ("test",))
        print("✓ INSERT permission")
        
        # Test SELECT permission
        cursor.execute(f"SELECT * FROM {test_table}")
        result = cursor.fetchone()
        print("✓ SELECT permission")
        
        # Test UPDATE permission
        cursor.execute(f"UPDATE {test_table} SET test_data = %s WHERE id = %s", ("updated", result[0]))
        print("✓ UPDATE permission")
        
        # Test DELETE permission
        cursor.execute(f"DELETE FROM {test_table} WHERE id = %s", (result[0],))
        print("✓ DELETE permission")
        
        # Test DROP TABLE permission
        cursor.execute(f"DROP TABLE {test_table}")
        print("✓ DROP TABLE permission")
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✓ All permissions verified\n")
        
    except Exception as e:
        print(f"❌ FAILED: {e}\n")
        try:
            conn.rollback()
            cursor.execute(f"DROP TABLE IF EXISTS {test_table}")
            conn.commit()
        except:
            pass
        return False
    
    # Test 3: SQLAlchemy Connection
    print("Test 3: SQLAlchemy Connection")
    print("-" * 40)
    try:
        from sqlalchemy import create_engine, text
        
        engine = create_engine(db_url, pool_pre_ping=True)
        
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✓ SQLAlchemy connection successful")
            
            # Test connection pool
            print(f"  Pool size: {settings.DATABASE_POOL_SIZE}")
            print(f"  Max overflow: {settings.DATABASE_MAX_OVERFLOW}")
            print(f"  Pool timeout: {settings.DATABASE_POOL_TIMEOUT}s")
        
        engine.dispose()
        print("✓ Connection pool closed\n")
        
    except Exception as e:
        print(f"❌ FAILED: {e}\n")
        return False
    
    # Test 4: Check Tables
    print("Test 4: Database Schema")
    print("-" * 40)
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        parsed = urlparse(db_url)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:]
        )
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        tables = cursor.fetchall()
        
        if tables:
            print(f"✓ Found {len(tables)} tables:")
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                count = cursor.fetchone()[0]
                print(f"  - {table[0]}: {count} rows")
        else:
            print("⚠ No tables found (database not initialized)")
            print("  Run: python scripts/setup_postgres.py")
        
        cursor.close()
        conn.close()
        print()
        
    except Exception as e:
        print(f"❌ FAILED: {e}\n")
        return False
    
    # Test 5: Async Connection (asyncpg)
    print("Test 5: Async Connection (asyncpg)")
    print("-" * 40)
    try:
        import asyncio
        import asyncpg
        from urllib.parse import urlparse
        
        async def test_async():
            parsed = urlparse(db_url)
            conn = await asyncpg.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path[1:]
            )
            
            version = await conn.fetchval("SELECT version()")
            print(f"✓ Async connection successful")
            print(f"  Version: {version.split(',')[0]}")
            
            await conn.close()
        
        asyncio.run(test_async())
        print("✓ Async connection closed\n")
        
    except ImportError:
        print("⚠ SKIPPED: asyncpg not installed")
        print("  Install with: pip install asyncpg\n")
    except Exception as e:
        print(f"❌ FAILED: {e}\n")
        return False
    
    # Test 6: Performance Test
    if verbose:
        print("Test 6: Performance Test")
        print("-" * 40)
        try:
            import psycopg2
            from urllib.parse import urlparse
            import time
            
            parsed = urlparse(db_url)
            
            # Test connection time
            start = time.time()
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path[1:]
            )
            connect_time = (time.time() - start) * 1000
            print(f"✓ Connection time: {connect_time:.2f}ms")
            
            cursor = conn.cursor()
            
            # Test query time
            start = time.time()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            query_time = (time.time() - start) * 1000
            print(f"✓ Simple query time: {query_time:.2f}ms")
            
            # Test bulk insert
            test_table = f"_test_performance_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            cursor.execute(f"""
                CREATE TABLE {test_table} (
                    id SERIAL PRIMARY KEY,
                    data VARCHAR(100)
                )
            """)
            
            start = time.time()
            for i in range(100):
                cursor.execute(f"INSERT INTO {test_table} (data) VALUES (%s)", (f"test_{i}",))
            conn.commit()
            insert_time = (time.time() - start) * 1000
            print(f"✓ 100 inserts time: {insert_time:.2f}ms ({insert_time/100:.2f}ms per insert)")
            
            # Cleanup
            cursor.execute(f"DROP TABLE {test_table}")
            conn.commit()
            
            cursor.close()
            conn.close()
            print()
            
        except Exception as e:
            print(f"❌ FAILED: {e}\n")
            return False
    
    # Summary
    print("="*60)
    print("✓ All tests passed!")
    print("="*60)
    print("\nDatabase is ready for use.")
    print("\nNext steps:")
    print("  1. Start the application: python main.py")
    print("  2. Add users: python scripts/add_postgres_user.py add --username admin --email admin@example.com --admin")
    print("  3. Check API: http://localhost:8000/docs")
    print()
    
    return True


def main():
    parser = argparse.ArgumentParser(description='Test PostgreSQL database connectivity')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Run additional performance tests')
    
    args = parser.parse_args()
    
    try:
        success = test_connection(verbose=args.verbose)
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
