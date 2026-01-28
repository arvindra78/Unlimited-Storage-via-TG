"""
Rate limiting system for TeleCloud.
Enforces free-tier limits: 20 uploads/day, 1 concurrent download, 100MB file size.
"""

from datetime import datetime, timedelta
from db import get_db

# Free tier limits
MAX_DAILY_UPLOADS = 20
MAX_CONCURRENT_DOWNLOADS = 1
MAX_FILE_SIZE_MB = 100

def check_daily_upload_limit(user_id):
    """
    Check if user can upload more files today.
    Returns (can_upload: bool, current_count: int, resets_in_hours: int)
    """
    db = get_db()
    
    # Count uploads today
    result = db.execute('''
        SELECT COUNT(*) as count FROM files 
        WHERE user_id = ? AND DATE(created_at) = DATE('now')
    ''', (user_id,)).fetchone()
    
    current_count = result['count'] if result else 0
    can_upload = current_count < MAX_DAILY_UPLOADS
    
    # Calculate hours until reset (midnight UTC)
    now = datetime.utcnow()
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    resets_in_hours = int((tomorrow - now).total_seconds() / 3600)
    
    return can_upload, current_count, resets_in_hours

def check_file_size_limit(file_size_bytes):
    """
    Check if file size is within limits.
    Returns (within_limit: bool, size_mb: float)
    """
    size_mb = file_size_bytes / (1024 * 1024)
    return size_mb <= MAX_FILE_SIZE_MB, size_mb

def get_active_downloads(user_id):
    """
    Get count of active downloads for user.
    Uses rate_limits table to track active downloads.
    """
    db = get_db()
    
    # Clean up old entries (older than 1 hour are considered stale)
    db.execute('''
        DELETE FROM rate_limits 
        WHERE user_id = ? 
        AND limit_type = 'download' 
        AND window_start < datetime('now', '-1 hour')
    ''', (user_id,))
    db.commit()
    
    # Count active downloads
    result = db.execute('''
        SELECT COUNT(*) as count FROM rate_limits 
        WHERE user_id = ? AND limit_type = 'download'
    ''', (user_id,)).fetchone()
    
    return result['count'] if result else 0

def register_download_start(user_id, file_id):
    """Register that a download has started"""
    db = get_db()
    db.execute('''
        INSERT INTO rate_limits (user_id, limit_type, count, window_start)
        VALUES (?, 'download', ?, CURRENT_TIMESTAMP)
    ''', (user_id, file_id))
    db.commit()

def register_download_end(user_id, file_id):
    """Register that a download has ended"""
    db = get_db()
    db.execute('''
        DELETE FROM rate_limits 
        WHERE user_id = ? AND limit_type = 'download' AND count = ?
    ''', (user_id, file_id))
    db.commit()

def check_concurrent_download_limit(user_id):
    """
    Check if user can start another download.
    Returns (can_download: bool, active_count: int)
    """
    active_count = get_active_downloads(user_id)
    can_download = active_count < MAX_CONCURRENT_DOWNLOADS
    return can_download, active_count

def get_user_limits_status(user_id):
    """
    Get complete limits status for user.
    Returns dict with all limit information.
    """
    can_upload, upload_count, resets_in = check_daily_upload_limit(user_id)
    can_download, download_count = check_concurrent_download_limit(user_id)
    
    return {
        'daily_uploads': {
            'current': upload_count,
            'max': MAX_DAILY_UPLOADS,
            'can_upload': can_upload,
            'resets_in_hours': resets_in,
            'percentage': int((upload_count / MAX_DAILY_UPLOADS) * 100)
        },
        'concurrent_downloads': {
            'current': download_count,
            'max': MAX_CONCURRENT_DOWNLOADS,
            'can_download': can_download,
            'percentage': int((download_count / MAX_CONCURRENT_DOWNLOADS) * 100)
        },
        'file_size_limit_mb': MAX_FILE_SIZE_MB
    }
