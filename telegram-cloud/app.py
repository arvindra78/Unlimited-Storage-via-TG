import os
import sqlite3
import json
from flask import Flask, render_template, request, redirect, url_for, session, g, Response, jsonify, flash
from werkzeug.utils import secure_filename

from db import get_db, close_db, init_db
from auth import login_required, verify_password
from uploader import start_upload
import downloader
from telegram_client import TelegramClient
import dotenv
dotenv.load_dotenv()

print(os.getenv('ADMIN_PASSWORD'))


# Init App
app = Flask(__name__)
# Load config from .env effectively
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'temp_uploads')

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# DB Teardown
app.teardown_appcontext(close_db)

# Init DB on startup if needed (or manually via command, but for this app auto-init is fine)
with app.app_context():
    init_db()

@app.route('/')
@login_required
def index():
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        if verify_password(password):
            session['user'] = 'admin'
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    files = db.execute('SELECT * FROM files ORDER BY created_at DESC').fetchall()
    return render_template('dashboard.html', files=files)

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    if not filename:
        filename = "unnamed_file"

    # Save to temp
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(temp_path)

    # Create DB Entry (Strict Upload Flow Step 1)
    db = get_db()
    cursor = db.execute('''
        INSERT INTO files (filename, size, chunks, status, message_ids, chunk_hashes) 
        VALUES (?, 0, 0, 'uploading', '[]', '[]')
    ''', (filename,))
    db.commit()
    file_id = cursor.lastrowid

    # Start Background Upload (threaded)
    start_upload(file_id, temp_path, filename)

    return jsonify({'success': True, 'file_id': file_id})

@app.route('/files/<int:file_id>/download')
@login_required
def download_file(file_id):
    """
    Download route with proper context separation.
    
    CRITICAL PATTERN:
    1. Get database connection WITHIN request context
    2. Fetch ALL data needed for streaming
    3. Pass ONLY plain Python data to generator
    4. Generator runs OUTSIDE request context
    """
    try:
        # Step 1: Get DB connection (within Flask request context)
        db = get_db()
        
        # Step 2: Fetch all metadata BEFORE streaming
        download_data = downloader.prepare_download_data(file_id, db)
        
        # Step 3: Handle errors
        if download_data is None:
            return "File not found", 404
        
        if 'error' in download_data:
            return download_data['error'], download_data['code']
        
        # Step 4: Create response with generator
        # The generator receives ONLY plain data (no Flask globals)
        return Response(
            downloader.create_download_stream(download_data),
            mimetype='application/octet-stream',
            headers={
                "Content-Disposition": f"attachment; filename={download_data['filename']}",
                "Content-Length": str(download_data['size']),
                "Accept-Ranges": "none",  # Indicate no range support (for now)
                "Cache-Control": "no-cache"
            }
        )
    except Exception as e:
        print(f"[DownloadRoute] Error: {e}")
        return f"Download Error: {str(e)}", 500

@app.route('/files/<int:file_id>/delete', methods=['POST'])
@login_required
def delete_file(file_id):
    db = get_db()
    row = db.execute('SELECT * FROM files WHERE id = ?', (file_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Not found'}), 404
    
    status = row['status']
    if status not in ('completed', 'failed'):
         return jsonify({'error': 'Cannot delete file in progress'}), 400

    # Delete from Telegram
    try:
        message_ids = json.loads(row['message_ids'])
        client = TelegramClient()
        for msg_id in message_ids:
            try:
                client.delete_message(msg_id)
            except:
                pass # Ignore already missing
    except Exception as e:
        print(f"Error deleting messages: {e}")

    # Delete from DB
    db.execute('DELETE FROM files WHERE id = ?', (file_id,))
    db.commit()
    
    return jsonify({'success': True})

@app.route('/check_status/<int:file_id>')
@login_required
def check_status(file_id):
    db = get_db()
    row = db.execute('SELECT status, uploaded_chunks, chunks FROM files WHERE id = ?', (file_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'status': row['status'], 
        'uploaded': row['uploaded_chunks'], 
        'total': row['chunks']
    })

@app.route('/health')
@login_required
def health():
    db = get_db()
    total_files = db.execute('SELECT COUNT(*) FROM files').fetchone()[0]
    total_size = db.execute('SELECT SUM(size) FROM files').fetchone()[0] or 0
    return render_template('health.html', total_files=total_files, total_bytes=total_size)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
