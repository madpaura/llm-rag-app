#!/usr/bin/env python3
"""
PostgreSQL user management script.
Add, remove, or modify PostgreSQL users for the RAG application.

Usage:
    python scripts/add_postgres_user.py add --username john --email john@example.com
    python scripts/add_postgres_user.py remove --username john
    python scripts/add_postgres_user.py list
    python scripts/add_postgres_user.py grant --username john --role admin
"""
import os
import sys
import argparse
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def connect_to_db():
    """Connect to PostgreSQL database."""
    import psycopg2
    from core.config import get_settings
    
    settings = get_settings()
    db_url = settings.DATABASE_URL
    
    # Parse DATABASE_URL
    # Format: postgresql://user:password@host:port/database
    if not db_url.startswith("postgresql://"):
        print("Error: DATABASE_URL must be a PostgreSQL connection string")
        print(f"Current: {db_url}")
        sys.exit(1)
    
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        parsed = urlparse(db_url)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:]  # Remove leading '/'
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)


def add_user(username: str, email: str, full_name: Optional[str] = None, 
             is_admin: bool = False, is_active: bool = True):
    """Add a new user to the database."""
    conn = connect_to_db()
    cursor = conn.cursor()
    
    try:
        # Check if user already exists
        cursor.execute("SELECT id, email, username FROM users WHERE username = %s OR email = %s", 
                      (username, email))
        existing = cursor.fetchone()
        
        if existing:
            print(f"Error: User already exists!")
            print(f"  ID: {existing[0]}, Email: {existing[1]}, Username: {existing[2]}")
            return False
        
        # Insert new user
        cursor.execute("""
            INSERT INTO users (username, email, full_name, is_admin, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING id, username, email
        """, (username, email, full_name, is_admin, is_active))
        
        user_id, username, email = cursor.fetchone()
        conn.commit()
        
        print(f"✓ User created successfully!")
        print(f"  ID: {user_id}")
        print(f"  Username: {username}")
        print(f"  Email: {email}")
        print(f"  Admin: {is_admin}")
        print(f"  Active: {is_active}")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"Error adding user: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def remove_user(username: str):
    """Remove a user from the database."""
    conn = connect_to_db()
    cursor = conn.cursor()
    
    try:
        # Check if user exists
        cursor.execute("SELECT id, email FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        if not user:
            print(f"Error: User '{username}' not found")
            return False
        
        user_id, email = user
        
        # Delete user (cascading deletes will handle related records)
        cursor.execute("DELETE FROM users WHERE username = %s", (username,))
        conn.commit()
        
        print(f"✓ User removed successfully!")
        print(f"  Username: {username}")
        print(f"  Email: {email}")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"Error removing user: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def list_users():
    """List all users in the database."""
    conn = connect_to_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT id, username, email, full_name, is_admin, is_active, created_at
            FROM users
            ORDER BY created_at DESC
        """)
        
        users = cursor.fetchall()
        
        if not users:
            print("No users found in database")
            return
        
        print(f"\nTotal users: {len(users)}\n")
        print(f"{'ID':<6} {'Username':<20} {'Email':<30} {'Admin':<8} {'Active':<8} {'Created'}")
        print("-" * 100)
        
        for user in users:
            user_id, username, email, full_name, is_admin, is_active, created_at = user
            admin_str = "Yes" if is_admin else "No"
            active_str = "Yes" if is_active else "No"
            created_str = created_at.strftime("%Y-%m-%d %H:%M") if created_at else "N/A"
            
            print(f"{user_id:<6} {username:<20} {email:<30} {admin_str:<8} {active_str:<8} {created_str}")
        
    except Exception as e:
        print(f"Error listing users: {e}")
    finally:
        cursor.close()
        conn.close()


def grant_role(username: str, role: str):
    """Grant admin role to a user."""
    conn = connect_to_db()
    cursor = conn.cursor()
    
    try:
        # Check if user exists
        cursor.execute("SELECT id, is_admin FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        if not user:
            print(f"Error: User '{username}' not found")
            return False
        
        user_id, current_admin = user
        
        if role.lower() == "admin":
            if current_admin:
                print(f"User '{username}' is already an admin")
                return True
            
            cursor.execute("UPDATE users SET is_admin = TRUE WHERE username = %s", (username,))
            conn.commit()
            print(f"✓ Admin role granted to '{username}'")
            
        elif role.lower() == "user":
            if not current_admin:
                print(f"User '{username}' is already a regular user")
                return True
            
            cursor.execute("UPDATE users SET is_admin = FALSE WHERE username = %s", (username,))
            conn.commit()
            print(f"✓ Admin role revoked from '{username}'")
        else:
            print(f"Error: Invalid role '{role}'. Use 'admin' or 'user'")
            return False
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"Error updating user role: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def toggle_active(username: str, active: bool):
    """Activate or deactivate a user."""
    conn = connect_to_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        if not user:
            print(f"Error: User '{username}' not found")
            return False
        
        cursor.execute("UPDATE users SET is_active = %s WHERE username = %s", (active, username))
        conn.commit()
        
        status = "activated" if active else "deactivated"
        print(f"✓ User '{username}' {status}")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"Error updating user status: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='PostgreSQL user management for RAG application')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Add user command
    add_parser = subparsers.add_parser('add', help='Add a new user')
    add_parser.add_argument('--username', required=True, help='Username')
    add_parser.add_argument('--email', required=True, help='Email address')
    add_parser.add_argument('--full-name', help='Full name')
    add_parser.add_argument('--admin', action='store_true', help='Make user an admin')
    add_parser.add_argument('--inactive', action='store_true', help='Create user as inactive')
    
    # Remove user command
    remove_parser = subparsers.add_parser('remove', help='Remove a user')
    remove_parser.add_argument('--username', required=True, help='Username to remove')
    
    # List users command
    subparsers.add_parser('list', help='List all users')
    
    # Grant role command
    grant_parser = subparsers.add_parser('grant', help='Grant or revoke admin role')
    grant_parser.add_argument('--username', required=True, help='Username')
    grant_parser.add_argument('--role', required=True, choices=['admin', 'user'], 
                             help='Role to grant (admin or user)')
    
    # Toggle active status
    activate_parser = subparsers.add_parser('activate', help='Activate a user')
    activate_parser.add_argument('--username', required=True, help='Username')
    
    deactivate_parser = subparsers.add_parser('deactivate', help='Deactivate a user')
    deactivate_parser.add_argument('--username', required=True, help='Username')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    if args.command == 'add':
        success = add_user(
            username=args.username,
            email=args.email,
            full_name=args.full_name,
            is_admin=args.admin,
            is_active=not args.inactive
        )
        return 0 if success else 1
        
    elif args.command == 'remove':
        success = remove_user(args.username)
        return 0 if success else 1
        
    elif args.command == 'list':
        list_users()
        return 0
        
    elif args.command == 'grant':
        success = grant_role(args.username, args.role)
        return 0 if success else 1
        
    elif args.command == 'activate':
        success = toggle_active(args.username, True)
        return 0 if success else 1
        
    elif args.command == 'deactivate':
        success = toggle_active(args.username, False)
        return 0 if success else 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
