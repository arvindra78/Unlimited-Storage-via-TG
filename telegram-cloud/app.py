import os
import sqlite3
import json
from flask import Flask, render_template, request, redirect, url_for, session, g, Response, jsonify, flash
from werkzeug.utils import secure_filename

from db import get_db, close_db, init_db, get_user, get_user_files, get_user_file
from auth_system import (
    login_required, onboarding_required, credentials_required,
    register_user, login_user, destroy_session, destroy_all_user_sessions,
    get_user_sessions, mark_onboarding_complete, update_user_telegram_credentials,
    mark_credentials_verified
)
from encryption import encrypt_bot_token, decrypt_bot_token
from rate_limiter import (
    check_daily_upload_limit, check_file_size_limit,
    check_concurrent_download_limit, register_download_start,
    register_download_end, get_user_limits_status
)
from uploader import start_upload
import downloader
from telegram_client import TelegramClient
import dotenv
dotenv.load_dotenv()

# Init App
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-CHANGE-IN-PRODUCTION')
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'temp_uploads')

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# DB Teardown
app.teardown_appcontext(close_db)

# Init DB on startup
with app.app_context():
    init_db()

# ==================== PUBLIC ROUTES ====================

@app.route('/')
def index():
    """Landing page - redirect based on auth status"""
    if 'session_token' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User registration"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('signup.html')
        
        # Register user
        user_id, error = register_user(email, password)
        if error:
            flash(error, 'error')
            return render_template('signup.html')
        
        # Auto-login after signup
        session['session_token'] = login_user(email, password)[1]
        
        flash('Account created successfully!', 'success')
        return redirect(url_for('onboarding'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_id, session_token, error = login_user(email, password)
        if error:
            flash(error, 'error')
            return render_template('login.html')
        
        # Store session token
        session['session_token'] = session_token
        
        # Check onboarding status
        user = get_user(user_id)
        if not user.get('onboarding_completed'):
            return redirect(url_for('onboarding'))
        
        flash('Welcome back!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Logout current session"""
    if 'session_token' in session:
        destroy_session(session['session_token'])
        session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

# ==================== ONBOARDING ====================

@app.route('/onboarding')
@login_required
def onboarding():
    """Onboarding wizard entry point"""
    # If already completed, redirect to dashboard
    if g.user.get('onboarding_completed'):
        return redirect(url_for('dashboard'))
    
    return render_template('onboarding/wizard.html')

@app.route('/onboarding/verify', methods=['POST'])
@login_required
def onboarding_verify():
    """Verify Telegram credentials during onboarding"""
    bot_token = request.form.get('bot_token')
    channel_id = request.form.get('channel_id')
    
    if not bot_token or not channel_id:
        return jsonify({'error': 'Bot token and channel ID are required'}), 400
    
    # Verify credentials by attempting to connect
    try:
        client = TelegramClient(token=bot_token, channel_id=channel_id)
        # Try to get channel info as verification
        if not client.verify_access():
            return jsonify({'error': 'Bot cannot access channel. Make sure bot is admin.'}), 400
    except Exception as e:
        return jsonify({'error': f'Connection failed: {str(e)}'}), 400
    
    # Save encrypted credentials
    encrypted_token = encrypt_bot_token(bot_token)
    update_user_telegram_credentials(g.user_id, encrypted_token, channel_id, verified=True)
    mark_onboarding_complete(g.user_id)
    
    return jsonify({'success': True})

# ==================== DASHBOARD & FILES ====================

@app.route('/dashboard')
@login_required
@onboarding_required
def dashboard():
    """User dashboard with files and stats"""
    files = get_user_files(g.user_id)
    
    # Calculate stats
    total_files = len(files)
    total_size = sum(f['size'] or 0 for f in files)
    completed_files = sum(1 for f in files if f['status'] == 'completed')
    
    # Get limits status
    limits = get_user_limits_status(g.user_id)
    
    # Check if credentials are verified
    credentials_ok = g.user.get('credentials_verified', 0) == 1
    
    return render_template('dashboard.html', 
                         files=files[:20],  # Show recent 20
                         total_files=total_files,
                         total_size=total_size,
                         completed_files=completed_files,
                         limits=limits,
                         credentials_ok=credentials_ok)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
@onboarding_required
@credentials_required
def upload():
    """Dedicated upload screen"""
    if request.method == 'GET':
        limits = get_user_limits_status(g.user_id)
        return render_template('upload.html', limits=limits)
    
    # POST: Handle file upload
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Check rate limits
    can_upload, current_count, resets_in = check_daily_upload_limit(g.user_id)
    if not can_upload:
        return jsonify({
            'error': 'Daily upload limit reached',
            'message': f'You have uploaded {current_count}/20 files today. Limit resets in {resets_in} hours.'
        }), 429
    
    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    within_limit, size_mb = check_file_size_limit(file_size)
    if not within_limit:
        return jsonify({
            'error': 'File too large',
            'message': f'File is {size_mb:.1f} MB. Free plan allows max 100 MB per file.'
        }), 400

    filename = secure_filename(file.filename)
    if not filename:
        filename = "unnamed_file"

    # Save to temp
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{g.user_id}_{filename}")
    file.save(temp_path)

    # Create DB Entry with user_id
    db = get_db()
    cursor = db.execute('''
        INSERT INTO files (user_id, filename, size, chunks, status, message_ids, chunk_hashes) 
        VALUES (?, ?, ?, 0, 'uploading', '[]', '[]')
    ''', (g.user_id, filename, file_size))
    db.commit()
    file_id = cursor.lastrowid

    # Get user's decrypted bot token
    encrypted_token = g.user.get('bot_token_encrypted')
    bot_token = decrypt_bot_token(encrypted_token)
    channel_id = g.user.get('channel_id')

    # Start Background Upload (threaded)
    try:
        start_upload(g.user_id, file_id, temp_path, filename, bot_token, channel_id)
    except Exception as e:
        # If upload start fails, mark credentials as broken
        mark_credentials_verified(g.user_id, verified=False)
        return jsonify({
            'error': 'Telegram connection failed',
            'message': 'Could not start upload. Your credentials may be invalid.'
        }), 500

    return jsonify({'success': True, 'file_id': file_id})

@app.route('/files')
@login_required
@onboarding_required
def files():
    """All files screen with search/filter"""
    status_filter = request.args.get('status')
    search_query = request.args.get('q', '').lower()
    
    all_files = get_user_files(g.user_id, status=status_filter)
    
    # Client-side search simulation
    if search_query:
        all_files = [f for f in all_files if search_query in f['filename'].lower()]
    
    return render_template('files.html', files=all_files)

@app.route('/files/<int:file_id>/download')
@login_required
def download_file(file_id):
    """Download file with streaming"""
    # Check concurrent download limit
    can_download, active_count = check_concurrent_download_limit(g.user_id)
    if not can_download:
        flash('Too many active downloads. Wait for current download to finish.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get file with user isolation
    file = get_user_file(g.user_id, file_id)
    if not file:
        return "File not found", 404
    
    # Register download start
    register_download_start(g.user_id, file_id)
    
    try:
        db = get_db()
        
        # Get user's credentials
        encrypted_token = g.user.get('bot_token_encrypted')
        bot_token = decrypt_bot_token(encrypted_token)
        channel_id = g.user.get('channel_id')
        
        # Prepare download with user's Telegram client
        download_data = downloader.prepare_download_data(file_id, db, bot_token, channel_id)
        
        if download_data is None:
            return "File not found", 404
        
        if 'error' in download_data:
            return download_data['error'], download_data['code']
        
        response = Response(
            downloader.create_download_stream(download_data),
            mimetype='application/octet-stream',
            headers={
                "Content-Disposition": f"attachment; filename=\"{download_data['filename']}\"",
                "Content-Length": str(download_data['size']),
                "Accept-Ranges": "none",
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "X-Accel-Buffering": "no",
            }
        )
        
        response.direct_passthrough = True
        
        # Register download end when response completes
        # Note: This is approximate, actual completion tracking would need streaming wrapper
        register_download_end(g.user_id, file_id)
        
        return response
        
    except Exception as e:
        register_download_end(g.user_id, file_id)
        print(f"[DownloadRoute] Error: {e}")
        return f"Download Error: {str(e)}", 500

@app.route('/files/<int:file_id>/delete', methods=['POST'])
@login_required
def delete_file(file_id):
    """Delete file (user-isolated)"""
    file = get_user_file(g.user_id, file_id)
    if not file:
        return jsonify({'error': 'Not found'}), 404
    
    status = file['status']
    if status not in ('completed', 'failed'):
        return jsonify({'error': 'Cannot delete file in progress'}), 400

    # Delete from Telegram using user's credentials
    try:
        encrypted_token = g.user.get('bot_token_encrypted')
        bot_token = decrypt_bot_token(encrypted_token)
        channel_id = g.user.get('channel_id')
        
        message_ids = json.loads(file['message_ids'])
        client = TelegramClient(token=bot_token, channel_id=channel_id)
        
        for msg_id in message_ids:
            try:
                client.delete_message(msg_id)
            except:
                pass  # Ignore already missing
    except Exception as e:
        print(f"Error deleting messages: {e}")

    # Delete from DB
    db = get_db()
    db.execute('DELETE FROM files WHERE id = ? AND user_id = ?', (file_id, g.user_id))
    db.commit()
    
    return jsonify({'success': True})

@app.route('/check_status/<int:file_id>')
@login_required
def check_status(file_id):
    """Check upload status (user-isolated)"""
    file = get_user_file(g.user_id, file_id)
    if not file:
        return jsonify({'error': 'Not found'}), 404
    
    return jsonify({
        'status': file['status'], 
        'uploaded': file['uploaded_chunks'], 
        'total': file['chunks']
    })

# ==================== SETTINGS ====================

@app.route('/settings')
@login_required
def settings():
    """Settings hub"""
    return render_template('settings/index.html')

@app.route('/settings/telegram')
@login_required
def settings_telegram():
    """Telegram credentials settings"""
    # Mask bot token for display
    encrypted_token = g.user.get('bot_token_encrypted')
    if encrypted_token:
        decrypted = decrypt_bot_token(encrypted_token)
        masked_token = decrypted[:8] + '•' * 20 if decrypted else None
    else:
        masked_token = None
    
    return render_template('settings/telegram.html', 
                         masked_token=masked_token,
                         channel_id=g.user.get('channel_id'),
                         verified=g.user.get('credentials_verified', 0) == 1,
                         verified_at=g.user.get('credentials_verified_at'))

@app.route('/settings/telegram/verify', methods=['POST'])
@login_required
def settings_telegram_verify():
    """Re-verify existing credentials"""
    encrypted_token = g.user.get('bot_token_encrypted')
    bot_token = decrypt_bot_token(encrypted_token)
    channel_id = g.user.get('channel_id')
    
    if not bot_token or not channel_id:
        return jsonify({'error': 'No credentials configured'}), 400
    
    try:
        client = TelegramClient(token=bot_token, channel_id=channel_id)
        if not client.verify_access():
            return jsonify({'error': 'Verification failed'}), 400
        
        mark_credentials_verified(g.user_id, verified=True)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/settings/telegram/update', methods=['POST'])
@login_required
def settings_telegram_update():
    """Update Telegram credentials"""
    bot_token = request.form.get('bot_token')
    channel_id = request.form.get('channel_id') or g.user.get('channel_id')
    
    if not bot_token:
        return jsonify({'error': 'Bot token required'}), 400
    
    # Verify new credentials
    try:
        client = TelegramClient(token=bot_token, channel_id=channel_id)
        if not client.verify_access():
            return jsonify({'error': 'Cannot verify credentials'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    # Save encrypted
    encrypted_token = encrypt_bot_token(bot_token)
    update_user_telegram_credentials(g.user_id, encrypted_token, channel_id, verified=True)
    
    flash('Telegram credentials updated successfully', 'success')
    return jsonify({'success': True})

@app.route('/settings/account')
@login_required
def settings_account():
    """Account settings"""
    sessions = get_user_sessions(g.user_id)
    return render_template('settings/account.html', sessions=sessions)

@app.route('/settings/account/password', methods=['POST'])
@login_required
def settings_account_password():
    """Change password"""
    from auth_system import hash_password, verify_password as verify_pw
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    
    # Verify current password
    if not verify_pw(current_password, g.user['password_hash']):
        flash('Current password is incorrect', 'error')
        return redirect(url_for('settings_account'))
    
    # Update password
    new_hash = hash_password(new_password)
    db = get_db()
    db.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, g.user_id))
    db.commit()
    
    flash('Password changed successfully', 'success')
    return redirect(url_for('settings_account'))

@app.route('/settings/sessions/<int:session_id>/revoke', methods=['POST'])
@login_required
def revoke_session(session_id):
    """Revoke specific session"""
    db = get_db()
    db.execute('DELETE FROM sessions WHERE id = ? AND user_id = ?', (session_id, g.user_id))
    db.commit()
    
    return jsonify({'success': True})

@app.route('/settings/sessions/revoke_all', methods=['POST'])
@login_required
def revoke_all_sessions():
    """Logout everywhere"""
    destroy_all_user_sessions(g.user_id)
    session.clear()
    flash('Logged out from all devices', 'success')
    return redirect(url_for('login'))

@app.route('/settings/limits')
@login_required
def settings_limits():
    """Limits & usage settings"""
    limits = get_user_limits_status(g.user_id)
    
    # Get usage stats
    db = get_db()
    total_files = db.execute('SELECT COUNT(*) FROM files WHERE user_id = ?', (g.user_id,)).fetchone()[0]
    total_size = db.execute('SELECT SUM(size) FROM files WHERE user_id = ?', (g.user_id,)).fetchone()[0] or 0
    
    return render_template('settings/limits.html', 
                         limits=limits, 
                         total_files=total_files,
                         total_size=total_size)

# ==================== SYSTEM ====================

@app.route('/health')
def health():
    """System health (public, no auth)"""
    db = get_db()
    total_users = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    total_files = db.execute('SELECT COUNT(*) FROM files').fetchone()[0]
    total_size = db.execute('SELECT SUM(size) FROM files').fetchone()[0] or 0
    
    return render_template('health.html', 
                         total_users=total_users,
                         total_files=total_files, 
                         total_bytes=total_size)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
