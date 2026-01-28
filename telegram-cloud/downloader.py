import json
import requests
import sqlite3
from telegram_client import TelegramClient
from utils.hasher import calculate_sha256

def prepare_download_data(file_id, db_connection):
    """
    Fetch all necessary data from the database BEFORE streaming begins.
    This function operates WITHIN the Flask request context.
    Returns a dict with all data needed for streaming.
    """
    row = db_connection.execute('SELECT * FROM files WHERE id = ?', (file_id,)).fetchone()
    
    if not row:
        return None
    
    if row['status'] != 'completed':
        return {'error': 'File not ready for download', 'code': 400}
        
    message_ids = json.loads(row['message_ids'])
    chunk_hashes = json.loads(row['chunk_hashes'])
    
    if not message_ids:
        return {'error': 'No chunks found for file', 'code': 500}
    
    # Return plain Python data - NO database connections or Flask globals
    return {
        'filename': row['filename'],
        'size': row['size'],
        'message_ids': message_ids,
        'chunk_hashes': chunk_hashes,
        'chunks': row['chunks']
    }

def create_download_stream(download_data):
    """
    Generator that streams file chunks.
    
    CRITICAL: This function executes OUTSIDE the Flask request context.
    It receives ONLY plain Python data structures (dicts, lists, strings).
    It NEVER accesses flask.g, current_app, or any Flask globals.
    
    Args:
        download_data: Dict containing message_ids, chunk_hashes, etc.
    
    Yields:
        bytes: Chunk data
    """
    message_ids = download_data['message_ids']
    chunk_hashes = download_data['chunk_hashes']
    
    # Create a NEW TelegramClient instance with credentials from environment
    # This does NOT rely on Flask context
    client = TelegramClient()
    
    for i, msg_id in enumerate(message_ids):
        try:
            # 1. Forward message to get fresh file_id
            forwarded_msg = client.forward_message(client.channel_id, client.channel_id, msg_id)
            
            if 'document' not in forwarded_msg:
                raise Exception(f"Chunk {i+1}: Forwarded message has no document")
                
            file_id_remote = forwarded_msg['document']['file_id']
            
            # 2. Delete temporary forwarded message
            client.delete_message(forwarded_msg['message_id'])
            
            # 3. Get download URL from Telegram
            file_path = client.get_file_path(file_id_remote)
            download_url = client.get_file_download_url(file_path)
            
            # 4. Download chunk (20MB in memory is acceptable)
            with requests.get(download_url, stream=True, timeout=60) as r:
                r.raise_for_status()
                chunk_data = r.content
                
            # 5. Verify Hash
            current_hash = calculate_sha256(chunk_data)
            expected_hash = chunk_hashes[i]
            
            if current_hash != expected_hash:
                raise Exception(f"Hash mismatch for chunk {i+1}. Expected {expected_hash}, got {current_hash}")
                
            # 6. Yield the verified chunk
            yield chunk_data
            
        except Exception as e:
            print(f"[DownloadStream] Error at chunk {i+1}/{len(message_ids)}: {e}")
            # Raising inside a generator terminates the stream
            raise e

def get_file_info(file_id, db_connection):
    """
    Retrieve file metadata from database.
    MUST be called within Flask request context.
    """
    row = db_connection.execute('SELECT * FROM files WHERE id = ?', (file_id,)).fetchone()
    return row
