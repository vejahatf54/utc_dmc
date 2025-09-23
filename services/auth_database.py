"""
Authentication Database Service
Handles user database operations for the WUTC application.
"""

import sqlite3
import bcrypt
from datetime import datetime, timedelta
from pathlib import Path
import sys
from typing import Optional, Dict, Any
from logging_config import get_logger

logger = get_logger(__name__)


class AuthDatabase:
    """Database service for user authentication."""
    
    def __init__(self, db_path: str = None):
        """
        Initialize the authentication database.
        
        Args:
            db_path: Path to the SQLite database file. Defaults to auth.db in app directory.
        """
        if db_path is None:
            # When running as a PyInstaller executable, create database next to the .exe file
            if hasattr(sys, '_MEIPASS'):
                executable_dir = Path(sys.executable).parent
                db_path = executable_dir / "auth.db"
            else:
                # Running in development mode
                app_root = Path(__file__).parent.parent
                db_path = app_root / "auth.db"
        
        self.db_path = Path(db_path)
        self._initialize_database()
    
    def _initialize_database(self):
        """Create the database tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        is_admin BOOLEAN NOT NULL DEFAULT 0,
                        is_active BOOLEAN NOT NULL DEFAULT 1,
                        must_change_password BOOLEAN NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP
                    )
                ''')
                
                # Create sessions table for managing user sessions
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        session_token TEXT UNIQUE NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')
                
                # Create audit log table for tracking authentication events
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS auth_audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        event_type TEXT NOT NULL,
                        event_details TEXT,
                        ip_address TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
                    )
                ''')
                
                # Add must_change_password column if it doesn't exist (migration)
                cursor.execute("PRAGMA table_info(users)")
                columns = [column[1] for column in cursor.fetchall()]
                if 'must_change_password' not in columns:
                    cursor.execute('ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 0')
                    logger.info("Added must_change_password column to users table")
                
                conn.commit()
                logger.info("Authentication database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize authentication database: {e}")
            raise
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def create_user(self, username: str, email: str, password: str, is_admin: bool = False, must_change_password: bool = True) -> Optional[int]:
        """
        Create a new user.
        
        Args:
            username: Unique username
            email: User's email address
            password: Plain text password (will be hashed)
            is_admin: Whether the user should have admin privileges
            must_change_password: Whether user must change password on first login
            
        Returns:
            User ID if successful, None if failed
        """
        try:
            password_hash = self.hash_password(password)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (username, email, password_hash, is_admin, must_change_password)
                    VALUES (?, ?, ?, ?, ?)
                ''', (username, email, password_hash, is_admin, must_change_password))
                
                user_id = cursor.lastrowid
                conn.commit()
                
                # Log the user creation event
                self.log_auth_event(user_id, "USER_CREATED", f"User {username} created")
                
                logger.info(f"User created successfully: {username} (ID: {user_id})")
                return user_id
                
        except sqlite3.IntegrityError as e:
            if "username" in str(e):
                logger.warning(f"Username already exists: {username}")
            elif "email" in str(e):
                logger.warning(f"Email already exists: {email}")
            return None
        except Exception as e:
            logger.error(f"Failed to create user {username}: {e}")
            return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate a user with username and password.
        
        Args:
            username: Username or email
            password: Plain text password
            
        Returns:
            User information dict if successful, None if failed
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, username, email, password_hash, is_admin, is_active, must_change_password
                    FROM users 
                    WHERE (username = ? OR email = ?) AND is_active = 1
                ''', (username, username))
                
                user_row = cursor.fetchone()
                
                if user_row and self.verify_password(password, user_row[3]):
                    user_info = {
                        'id': user_row[0],
                        'username': user_row[1],
                        'email': user_row[2],
                        'is_admin': bool(user_row[4]),
                        'is_active': bool(user_row[5]),
                        'must_change_password': bool(user_row[6])
                    }
                    
                    # Update last login timestamp
                    cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user_info['id'],))
                    conn.commit()
                    
                    # Log successful login
                    self.log_auth_event(user_info['id'], "LOGIN_SUCCESS", f"User {username} logged in")
                    
                    logger.info(f"User authenticated successfully: {username}")
                    return user_info
                else:
                    # Log failed login attempt
                    self.log_auth_event(None, "LOGIN_FAILED", f"Failed login attempt for {username}")
                    logger.warning(f"Authentication failed for user: {username}")
                    return None
                    
        except Exception as e:
            logger.error(f"Authentication error for user {username}: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, username, email, is_admin, is_active, created_at, last_login
                    FROM users 
                    WHERE id = ? AND is_active = 1
                ''', (user_id,))
                
                user_row = cursor.fetchone()
                
                if user_row:
                    return {
                        'id': user_row[0],
                        'username': user_row[1],
                        'email': user_row[2],
                        'is_admin': bool(user_row[3]),
                        'is_active': bool(user_row[4]),
                        'created_at': user_row[5],
                        'last_login': user_row[6]
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            return None
    
    def list_users(self) -> list:
        """Get a list of all users (admin only)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, username, email, is_admin, is_active, created_at, last_login
                    FROM users 
                    ORDER BY created_at DESC
                ''')
                
                users = []
                for row in cursor.fetchall():
                    users.append({
                        'id': row[0],
                        'username': row[1],
                        'email': row[2],
                        'is_admin': bool(row[3]),
                        'is_active': bool(row[4]),
                        'created_at': row[5],
                        'last_login': row[6]
                    })
                
                return users
                
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []
    
    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user account."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
                conn.commit()
                
                if cursor.rowcount > 0:
                    self.log_auth_event(user_id, "USER_DEACTIVATED", f"User ID {user_id} deactivated")
                    logger.info(f"User deactivated: ID {user_id}")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Error deactivating user {user_id}: {e}")
            return False
    
    def delete_user(self, user_id: int) -> bool:
        """Permanently delete a user from the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # First get user info for logging
                cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
                user_info = cursor.fetchone()
                
                if not user_info:
                    logger.warning(f"Attempted to delete non-existent user ID {user_id}")
                    return False
                
                username = user_info[0]
                
                # Log the deletion before deleting
                self.log_auth_event(user_id, "USER_DELETED", f"User {username} (ID {user_id}) permanently deleted")
                
                # Delete the user (this will cascade to sessions due to foreign key constraints)
                cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"User permanently deleted: {username} (ID {user_id})")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            return False
    
    def log_auth_event(self, user_id: Optional[int], event_type: str, event_details: str, ip_address: str = None):
        """Log an authentication event."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO auth_audit_log (user_id, event_type, event_details, ip_address)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, event_type, event_details, ip_address))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error logging auth event: {e}")
    
    def is_first_run(self) -> bool:
        """Check if this is the first run (no users exist)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM users')
                count = cursor.fetchone()[0]
                return count == 0
                
        except Exception as e:
            logger.error(f"Error checking first run: {e}")
            return True
    
    def update_password(self, user_id: int, new_password: str, clear_must_change: bool = True) -> bool:
        """
        Update a user's password.
        
        Args:
            user_id: User ID to update
            new_password: New plain text password (will be hashed)
            clear_must_change: Whether to clear the must_change_password flag
            
        Returns:
            True if successful
        """
        try:
            password_hash = self.hash_password(new_password)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if clear_must_change:
                    cursor.execute(
                        'UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?', 
                        (password_hash, user_id)
                    )
                else:
                    cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
                conn.commit()
                
                if cursor.rowcount > 0:
                    self.log_auth_event(user_id, "PASSWORD_CHANGED", f"User ID {user_id} changed password")
                    logger.info(f"Password updated for user ID: {user_id}")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Error updating password for user {user_id}: {e}")
            return False

    def create_default_admin(self, username: str = "admin", password: str = "admin123", email: str = "admin@localhost"):
        """Create a default admin user if no users exist."""
        if self.is_first_run():
            # Default admin should also change password on first login for security
            user_id = self.create_user(username, email, password, is_admin=True, must_change_password=True)
            if user_id:
                logger.warning(f"Default admin user created: {username} (Must change password on first login!)")
                return True
        return False