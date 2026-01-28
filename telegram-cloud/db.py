import sqlite3
import json
import os
from flask import g

DB_PATH = 'cloud.db'
SCHEMA_VERSION = 2  # Multi-user schema

def get_db():
    """Get database connection for current request"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

def close_db(e=None):
    """Close database connection"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def get_schema_version(conn):
    """Get current database schema version"""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT version FROM schema_version ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        return result[0] if result else 0
    except sqlite3.OperationalError:
        return 0

def set_schema_version(conn, version):
    """Set database schema version"""
    cursor = conn.cursor()
    cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
    conn.commit()

def backup_database():
    """Create backup before migration"""
    if os.path.exists(DB_PATH):
        backup_path = f"{DB_PATH}.backup"
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        print(f"✓ Database backed up to {backup_path}")
        return backup_path
    return None

def migrate_to_v1(conn):
    """Initial schema: Single-user files table"""
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            size INTEGER NOT NULL,
            chunks INTEGER NOT NULL,
            uploaded_chunks INTEGER DEFAULT 0,
            message_ids TEXT DEFAULT '[]',
            chunk_hashes TEXT DEFAULT '[]',
            file_hash TEXT,
            status TEXT DEFAULT 'uploading',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Add schema_version table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schema_version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version INTEGER NOT NULL,
            migrated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    print("✓ Migrated to schema v1 (single-user)")

def migrate_to_v2(conn):
    """Multi-user schema: Add users, sessions, rate_limits"""
    cursor = conn.cursor()
    
    # 1. Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            
            -- Telegram credentials (encrypted)
            bot_token_encrypted TEXT,
            channel_id TEXT,
            credentials_verified INTEGER DEFAULT 0,
            credentials_verified_at TIMESTAMP,
            
            -- Account state
            account_status TEXT DEFAULT 'active',
            onboarding_completed INTEGER DEFAULT 0,
            
            -- Limits (free tier defaults)
            max_concurrent_streams INTEGER DEFAULT 1,
            max_file_size_mb INTEGER DEFAULT 100,
            max_daily_uploads INTEGER DEFAULT 20
        )
    ''')
    
    # 2. Add user_id to files table (if not exists)
    cursor.execute("PRAGMA table_info(files)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'user_id' not in columns:
        cursor.execute('ALTER TABLE files ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE')
        print("✓ Added user_id column to files table")
    
    # 3. Create sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token)')
    
    # 4. Create rate_limits table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rate_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            limit_type TEXT NOT NULL,
            count INTEGER DEFAULT 0,
            window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_rate_limits_user_window ON rate_limits(user_id, limit_type, window_start)')
    
    # 5. Create system_messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            active INTEGER DEFAULT 1,
            dismissable INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
    ''')
    
    # 6. Create indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_user_id ON files(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_status ON files(status)')
    
    conn.commit()
    print("✓ Migrated to schema v2 (multi-user)")
    
    # 7. Create admin user from .env if no users exist
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        print("→ No users found, will create admin on first run")

def init_db():
    """
    Initialize database with migrations.
    Safely migrates from v0 (no schema) to current version.
    """
    print("Starting database initialization...")
    
    # Backup before any changes
    backup_path = backup_database()
    
    try:
        conn = sqlite3.connect(DB_PATH)
        current_version = get_schema_version(conn)
        
        print(f"Current schema version: v{current_version}")
        print(f"Target schema version: v{SCHEMA_VERSION}")
        
        # Apply migrations in order
        if current_version < 1:
            migrate_to_v1(conn)
            set_schema_version(conn, 1)
            current_version = 1
        
        if current_version < 2:
            migrate_to_v2(conn)
            set_schema_version(conn, 2)
            current_version = 2
        
        conn.close()
        print(f"✓ Database initialization complete (v{current_version})")
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        if backup_path:
            print(f"Restoring from backup: {backup_path}")
            import shutil
            shutil.copy2(backup_path, DB_PATH)
            print("✓ Database restored from backup")
        raise

# Helper functions for multi-user queries

def get_user(user_id):
    """Get user by ID"""
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    return dict(user) if user else None

def get_user_by_email(email):
    """Get user by email"""
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    return dict(user) if user else None

def create_user(email, password_hash, bot_token_encrypted=None, channel_id=None):
    """Create new user"""
    db = get_db()
    cursor = db.execute('''
        INSERT INTO users (email, password_hash, bot_token_encrypted, channel_id, onboarding_completed, credentials_verified)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (email, password_hash, bot_token_encrypted, channel_id, 
          1 if bot_token_encrypted else 0,
          1 if bot_token_encrypted else 0))
    db.commit()
    return cursor.lastrowid

def get_user_files(user_id, status=None):
    """Get all files for a user, optionally filtered by status"""
    db = get_db()
    if status:
        files = db.execute('SELECT * FROM files WHERE user_id = ? AND status = ? ORDER BY created_at DESC', 
                          (user_id, status)).fetchall()
    else:
        files = db.execute('SELECT * FROM files WHERE user_id = ? ORDER BY created_at DESC', 
                          (user_id,)).fetchall()
    return [dict(f) for f in files]

def get_user_file(user_id, file_id):
    """Get specific file for a user (ensures isolation)"""
    db = get_db()
    file = db.execute('SELECT * FROM files WHERE id = ? AND user_id = ?', (file_id, user_id)).fetchone()
    return dict(file) if file else None
