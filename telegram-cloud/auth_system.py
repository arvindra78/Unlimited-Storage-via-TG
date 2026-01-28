"""
Multi-user authentication system for TeleCloud.
Handles user registration, login, session management, and decorators.
"""

import bcrypt
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import session, redirect, url_for, g, request
from db import get_db, get_user, get_user_by_email, create_user

# Session configuration
SESSION_LIFETIME_HOURS = 24
MAX_LOGIN_ATTEMPTS = 3
LOGIN_ATTEMPT_WINDOW_MINUTES = 5

def hash_password(password):
    """Hash password with bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, password_hash):
    """Verify password against hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except:
        return False

def generate_session_token():
    """Generate secure random session token"""
    return secrets.token_urlsafe(32)

def create_session(user_id, ip_address=None, user_agent=None):
    """Create new session for user"""
    db = get_db()
    token = generate_session_token()
    expires_at = datetime.now() + timedelta(hours=SESSION_LIFETIME_HOURS)
    
    db.execute('''
        INSERT INTO sessions (user_id, session_token, ip_address, user_agent, expires_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, token, ip_address, user_agent, expires_at))
    db.commit()
    
    return token

def validate_session(session_token):
    """Validate session token and return user_id if valid"""
    db = get_db()
    session_data = db.execute('''
        SELECT user_id, expires_at FROM sessions 
        WHERE session_token = ?
    ''', (session_token,)).fetchone()
    
    if not session_data:
        return None
    
    # Check expiry
    expires_at = datetime.fromisoformat(session_data['expires_at'])
    if datetime.now() > expires_at:
        # Session expired, delete it
        db.execute('DELETE FROM sessions WHERE session_token = ?', (session_token,))
        db.commit()
        return None
    
    # Update last_active
    db.execute('''
        UPDATE sessions SET last_active = CURRENT_TIMESTAMP 
        WHERE session_token = ?
    ''', (session_token,))
    db.commit()
    
    return session_data['user_id']

def destroy_session(session_token):
    """Destroy a session"""
    db = get_db()
    db.execute('DELETE FROM sessions WHERE session_token = ?', (session_token,))
    db.commit()

def destroy_all_user_sessions(user_id):
    """Destroy all sessions for a user (logout everywhere)"""
    db = get_db()
    db.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
    db.commit()

def get_user_sessions(user_id):
    """Get all active sessions for a user"""
    db = get_db()
    sessions = db.execute('''
        SELECT id, ip_address, user_agent, created_at, last_active 
        FROM sessions 
        WHERE user_id = ? AND expires_at > CURRENT_TIMESTAMP
        ORDER BY last_active DESC
    ''', (user_id,)).fetchall()
    return [dict(s) for s in sessions]

def register_user(email, password, bot_token_encrypted=None, channel_id=None):
    """
    Register a new user.
    Returns (user_id, error) tuple. error is None on success.
    """
    # Validate email
    if not email or '@' not in email:
        return None, "Invalid email address"
    
    # Validate password
    if not password or len(password) < 6:
        return None, "Password must be at least 6 characters"
    
    # Check if email already exists
    existing_user = get_user_by_email(email)
    if existing_user:
        return None, "Email already registered"
    
    # Hash password and create user
    password_hash = hash_password(password)
    user_id = create_user(email, password_hash, bot_token_encrypted, channel_id)
    
    return user_id, None

def login_user(email, password):
    """
    Authenticate user and create session.
    Returns (user_id, session_token, error) tuple.
    """
    # Get user
    user = get_user_by_email(email)
    if not user:
        return None, None, "Invalid email or password"
    
    # Check account status
    if user.get('account_status') != 'active':
        return None, None, "Account is suspended"
    
    # Verify password
    if not verify_password(password, user['password_hash']):
        return None, None, "Invalid email or password"
    
    # Create session
    ip_address = request.remote_addr if request else None
    user_agent = request.headers.get('User-Agent') if request else None
    session_token = create_session(user['id'], ip_address, user_agent)
    
    # Update last_login
    db = get_db()
    db.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user['id'],))
    db.commit()
    
    return user['id'], session_token, None

def update_user_telegram_credentials(user_id, bot_token_encrypted, channel_id, verified=False):
    """Update user's Telegram credentials"""
    db = get_db()
    db.execute('''
        UPDATE users 
        SET bot_token_encrypted = ?, 
            channel_id = ?, 
            credentials_verified = ?,
            credentials_verified_at = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END
        WHERE id = ?
    ''', (bot_token_encrypted, channel_id, 1 if verified else 0, verified, user_id))
    db.commit()

def mark_credentials_verified(user_id, verified=True):
    """Mark user's Telegram credentials as verified or broken"""
    db = get_db()
    db.execute('''
        UPDATE users 
        SET credentials_verified = ?,
            credentials_verified_at = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END
        WHERE id = ?
    ''', (1 if verified else 0, verified, user_id))
    db.commit()

def mark_onboarding_complete(user_id):
    """Mark user's onboarding as complete"""
    db = get_db()
    db.execute('UPDATE users SET onboarding_completed = 1 WHERE id = ?', (user_id,))
    db.commit()

# Decorators

def login_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'session_token' not in session:
            return redirect(url_for('login'))
        
        user_id = validate_session(session['session_token'])
        if not user_id:
            session.clear()
            return redirect(url_for('login'))
        
        # Store in g for request context
        g.user_id = user_id
        g.user = get_user(user_id)
        
        return f(*args, **kwargs)
    return decorated_function

def onboarding_required(f):
    """Decorator to ensure onboarding is complete"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not g.user.get('onboarding_completed'):
            return redirect(url_for('onboarding'))
        return f(*args, **kwargs)
    return decorated_function

def credentials_required(f):
    """Decorator to ensure Telegram credentials are verified"""
    @wraps(f)
    @login_required
    @onboarding_required
    def decorated_function(*args, **kwargs):
        if not g.user.get('credentials_verified'):
            return redirect(url_for('settings_telegram'))
        return f(*args, **kwargs)
    return decorated_function
