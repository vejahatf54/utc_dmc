"""
Authentication Service for WUTC application.
Handles user authentication, session management, and security.
"""

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from flask import session, request
from services.auth_database import AuthDatabase
from logging_config import get_logger

logger = get_logger(__name__)


class AuthenticationService:
    """Service for handling user authentication and session management."""
    
    def __init__(self):
        """Initialize the authentication service."""
        self.db = AuthDatabase()
        self.session_timeout_hours = 8  # Session timeout in hours
        
        # Create default admin if this is first run
        self.db.create_default_admin()
    
    def login(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate user and create session.
        
        Args:
            username: Username or email
            password: Plain text password
            
        Returns:
            User information if successful, None if failed
        """
        user_info = self.db.authenticate_user(username, password)
        
        if user_info:
            # Create Flask session
            session['user_id'] = user_info['id']
            session['username'] = user_info['username']
            session['is_admin'] = user_info['is_admin']
            session['must_change_password'] = user_info['must_change_password']
            session['login_time'] = datetime.now().isoformat()
            session.permanent = True
            
            logger.info(f"User session created: {user_info['username']}")
            return user_info
        
        return None
    
    def logout(self) -> bool:
        """
        Logout user and clear session.
        
        Returns:
            True if successful
        """
        username = session.get('username', 'Unknown')
        
        # Clear Flask session
        session.clear()
        
        logger.info(f"User logged out: {username}")
        return True
    
    def is_authenticated(self) -> bool:
        """
        Check if current user is authenticated.
        
        Returns:
            True if user is authenticated and session is valid
        """
        user_id = session.get('user_id')
        login_time_str = session.get('login_time')
        
        if not user_id or not login_time_str:
            return False
        
        try:
            # Check if session has expired
            login_time = datetime.fromisoformat(login_time_str)
            if datetime.now() - login_time > timedelta(hours=self.session_timeout_hours):
                logger.info(f"Session expired for user ID: {user_id}")
                session.clear()
                return False
            
            # Verify user still exists and is active
            user_info = self.db.get_user_by_id(user_id)
            if not user_info:
                logger.warning(f"User not found or inactive: {user_id}")
                session.clear()
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking authentication: {e}")
            session.clear()
            return False
    
    def is_admin(self) -> bool:
        """
        Check if current user is an admin.
        
        Returns:
            True if user is authenticated and has admin privileges
        """
        return self.is_authenticated() and session.get('is_admin', False)
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """
        Get current authenticated user information.
        
        Returns:
            User information if authenticated, None otherwise
        """
        if not self.is_authenticated():
            return None
        
        user_id = session.get('user_id')
        return self.db.get_user_by_id(user_id)
    
    def require_authentication(self) -> bool:
        """
        Check if authentication is required and user is authenticated.
        Used as a decorator or middleware function.
        
        Returns:
            True if user is authenticated, False if redirect to login is needed
        """
        return self.is_authenticated()
    
    def require_admin(self) -> bool:
        """
        Check if admin privileges are required and user has them.
        
        Returns:
            True if user is admin, False if access denied
        """
        return self.is_admin()
    
    def create_user_by_admin(self, username: str, email: str, password: str, is_admin: bool = False) -> Optional[int]:
        """
        Create a new user (admin only).
        
        Args:
            username: Unique username
            email: User's email address
            password: Plain text password
            is_admin: Whether the user should have admin privileges
            
        Returns:
            User ID if successful, None if failed
        """
        if not self.is_admin():
            logger.warning("Unauthorized attempt to create user")
            return None
        
        # New users created by admin must change their password on first login
        return self.db.create_user(username, email, password, is_admin, must_change_password=True)
    
    def list_all_users(self) -> list:
        """
        List all users (admin only). Admins only see non-admin users plus themselves.
        
        Returns:
            List of user information dicts
        """
        if not self.is_admin():
            logger.warning("Unauthorized attempt to list users")
            return []
        
        all_users = self.db.list_users()
        current_user_id = session.get('user_id')
        
        # Filter: show current admin + all non-admin users
        filtered_users = [
            user for user in all_users 
            if not user['is_admin'] or user['id'] == current_user_id
        ]
        
        return filtered_users
    
    def deactivate_user_by_admin(self, user_id: int) -> bool:
        """
        Deactivate a user account (admin only).
        
        Args:
            user_id: ID of user to deactivate
            
        Returns:
            True if successful
        """
        if not self.is_admin():
            logger.warning("Unauthorized attempt to deactivate user")
            return False
        
        # Don't allow admin to deactivate themselves
        current_user_id = session.get('user_id')
        if user_id == current_user_id:
            logger.warning("Admin attempted to deactivate themselves")
            return False
        
        return self.db.deactivate_user(user_id)
    
    def delete_user_by_admin(self, user_id: int) -> bool:
        """
        Permanently delete a user from the database (admin only).
        
        Args:
            user_id: ID of user to delete
            
        Returns:
            True if successful
        """
        if not self.is_admin():
            logger.warning("Unauthorized attempt to delete user")
            return False
        
        # Don't allow admin to delete themselves
        current_user_id = session.get('user_id')
        if user_id == current_user_id:
            logger.warning("Admin attempted to delete themselves")
            return False
        
        return self.db.delete_user(user_id)
    
    def change_password(self, current_password: str, new_password: str) -> bool:
        """
        Change current user's password.
        
        Args:
            current_password: Current password for verification
            new_password: New password
            
        Returns:
            True if successful
        """
        if not self.is_authenticated():
            return False
        
        username = session.get('username')
        user_info = self.db.authenticate_user(username, current_password)
        
        if user_info:
            success = self.db.update_password(user_info['id'], new_password, clear_must_change=True)
            if success:
                # Update session to clear must_change_password flag
                session['must_change_password'] = False
                logger.info(f"Password changed for user: {username}")
            return success
        
        return False
    
    def must_change_password(self) -> bool:
        """
        Check if current user must change their password.
        
        Returns:
            True if password change is required
        """
        if not self.is_authenticated():
            return False
        
        return session.get('must_change_password', False)
    
    def change_password_forced(self, new_password: str) -> bool:
        """
        Change password without requiring current password (for forced changes).
        
        Args:
            new_password: New password
            
        Returns:
            True if successful
        """
        if not self.is_authenticated():
            return False
        
        user_id = session.get('user_id')
        success = self.db.update_password(user_id, new_password, clear_must_change=True)
        if success:
            # Update session to clear must_change_password flag
            session['must_change_password'] = False
            username = session.get('username')
            logger.info(f"Forced password change for user: {username}")
        return success
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        Get current session information for debugging/display.
        
        Returns:
            Session information dict
        """
        if not self.is_authenticated():
            return {'authenticated': False}
        
        login_time_str = session.get('login_time')
        login_time = datetime.fromisoformat(login_time_str) if login_time_str else None
        time_remaining = None
        
        if login_time:
            expires_at = login_time + timedelta(hours=self.session_timeout_hours)
            time_remaining = expires_at - datetime.now()
        
        return {
            'authenticated': True,
            'username': session.get('username'),
            'is_admin': session.get('is_admin'),
            'login_time': login_time.isoformat() if login_time else None,
            'time_remaining_minutes': int(time_remaining.total_seconds() / 60) if time_remaining else None
        }


# Global authentication service instance
auth_service = AuthenticationService()