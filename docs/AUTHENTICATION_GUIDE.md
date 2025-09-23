# WUTC Authentication System

## Overview

The WUTC application now includes a comprehensive authentication system that requires users to log in before accessing any features. Only users registered by an admin can access the application.

## Default Admin Account

On first run, a default admin account is automatically created:

- **Username:** `admin`
- **Password:** `admin123`
- **Email:** `admin@localhost`

⚠️ **IMPORTANT:** Change this password immediately after first login!

## Features

### For All Users

- **Secure Login:** Username/email and password authentication
- **Session Management:** 8-hour session timeout
- **Auto-redirect:** Unauthenticated users are redirected to login page
- **Logout:** Secure logout functionality available in sidebar

### For Admin Users

- **User Management:** Create, view, and deactivate user accounts
- **Admin Dashboard:** Access to admin-only features via sidebar
- **User Registration:** Register new users with or without admin privileges
- **Audit Logging:** All authentication events are logged

## How to Use

### First Time Setup

1. Start the application
2. You'll be redirected to the login page automatically
3. Log in with the default admin credentials above
4. Navigate to "User Management" in the sidebar (admin section)
5. Change the admin password (TODO: implement password change feature)
6. Create accounts for your users

### Creating New Users (Admin Only)

1. Log in as an admin
2. Go to "User Management" in the sidebar
3. Click "Add New User"
4. Fill in the registration form:
   - Username (must be unique)
   - Email address (must be unique)
   - Password (minimum 6 characters)
   - Confirm password
   - Check "Admin User" if they need admin privileges
5. Click "Register User"

### Regular User Login

1. Navigate to the application
2. Enter username/email and password on login page
3. Click "Login"
4. You'll be redirected to the home page
5. All application features are now accessible

### Logging Out

- Click the "Logout" button in the sidebar (bottom section)
- You'll be redirected to the login page
- Your session will be cleared

## Security Features

### Password Security

- Passwords are hashed using bcrypt with salt
- Plain text passwords are never stored
- Strong password validation (minimum 6 characters)

### Session Security

- Sessions expire after 8 hours of inactivity
- Secure session tokens
- Session validation on every request

### Database Security

- SQLite database with proper foreign key constraints
- SQL injection protection through parameterized queries
- User input validation and sanitization

### Audit Logging

- All login attempts (successful and failed) are logged
- User creation and deactivation events are tracked
- Timestamps and event details are recorded

## File Structure

### New Authentication Files

```
services/
├── auth_database.py      # Database operations for users and sessions
├── auth_service.py       # Main authentication service
└── auth_middleware.py    # Route protection and middleware

components/
└── login_page.py         # Login and user management UI components

assets/
└── auth.css             # Authentication-specific styles
```

### Database Files

- `auth.db` - SQLite database (created automatically)
  - `users` table - User accounts and profiles
  - `user_sessions` table - Active sessions (currently using Flask sessions)
  - `auth_audit_log` table - Authentication event logging

## Configuration

### Session Timeout

Default: 8 hours
Location: `services/auth_service.py` - `session_timeout_hours`

### Database Location

- Development: `{project_root}/auth.db`
- Production (PyInstaller): `{executable_directory}/auth.db`

## Admin Tasks

### User Management

- View all registered users
- See user status (active/inactive)
- Check admin privileges
- View last login times
- Deactivate problematic accounts

### Security Monitoring

- Review authentication logs in the database
- Monitor failed login attempts
- Track user activity patterns

## Troubleshooting

### Common Issues

**"Invalid username or password"**

- Verify credentials are correct
- Check if user account exists and is active
- Admin can check user status in User Management

**"Access Denied" for admin features**

- Ensure user has admin privileges
- Admin can update user permissions

**Session expired**

- Sessions expire after 8 hours
- Simply log in again

**Database issues**

- Delete `auth.db` to reset (will lose all users)
- Default admin will be recreated automatically

### Reset to Factory Settings

1. Stop the application
2. Delete the `auth.db` file
3. Restart the application
4. Default admin account will be recreated

## Security Best Practices

1. **Change default password immediately**
2. **Use strong, unique passwords**
3. **Regularly review user accounts**
4. **Remove access for inactive users**
5. **Monitor authentication logs**
6. **Keep the application updated**

## Technical Notes

### Dependencies Added

- `Flask-Login==0.6.3` - Flask session management
- `bcrypt==4.0.1` - Password hashing

### Database Schema

The authentication system uses three main tables:

- `users` - Core user information and credentials
- `user_sessions` - Session management (placeholder for future use)
- `auth_audit_log` - Security event logging

### Integration Points

The authentication system integrates with:

- Main app routing (`app.py`)
- Sidebar navigation (`components/sidebar.py`)
- All existing page components (via middleware)

This system provides enterprise-grade security while maintaining the simplicity of the existing WUTC application.
