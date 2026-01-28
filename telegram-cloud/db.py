import sqlite3
import json
import os
from flask import g

DB_PATH = 'cloud.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

def close_db(e=None):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """
    Initialize DB and ensure schema safety.
    Auto-migrates missing columns but NEVER drops tables.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create table if not exists
    c.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            size INTEGER NOT NULL,
            chunks INTEGER NOT NULL,
            uploaded_chunks INTEGER DEFAULT 0,
            message_ids TEXT DEFAULT '[]', -- JSON array
            chunk_hashes TEXT DEFAULT '[]', -- JSON array
            file_hash TEXT,
            status TEXT DEFAULT 'uploading',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Migration Safety Check: Ensure all columns exist
    c.execute("PRAGMA table_info(files)")
    existing_cols = {row[1] for row in c.fetchall()}
    
    required_cols = {
        'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
        'filename': 'TEXT NOT NULL',
        'size': 'INTEGER NOT NULL',
        'chunks': 'INTEGER NOT NULL',
        'uploaded_chunks': 'INTEGER DEFAULT 0',
        'message_ids': "TEXT DEFAULT '[]'",
        'chunk_hashes': "TEXT DEFAULT '[]'",
        'file_hash': 'TEXT',
        'status': "TEXT DEFAULT 'uploading'",
        'created_at': "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    }

    for col, definition in required_cols.items():
        if col not in existing_cols:
            print(f"Migrating: Adding missing column '{col}'")
            # Note: SQLite ALTER TABLE limits (cannot add PRIMARY KEY etc easily), 
            # but for non-PK columns it's fine.
            # Simplified ALTER for basic columns:
            try:
                # Extract type and default from definition roughly
                # This is a basic migration for expected columns.
                type_def = definition.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'INTEGER')
                c.execute(f"ALTER TABLE files ADD COLUMN {col} {type_def}")
            except Exception as e:
                print(f"Migration warning for {col}: {e}")

    conn.commit()
    conn.close()
    print("Database initialized and verified.")
