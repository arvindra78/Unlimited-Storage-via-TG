import os
import time
import json
import sqlite3
import threading
from utils.chunker import yield_chunks, calculate_total_chunks, get_file_size
from utils.hasher import calculate_sha256, calculate_file_hash
from telegram_client import TelegramClient
from db import DB_PATH

class UploadWorker(threading.Thread):
    def __init__(self, user_id, file_id, temp_path, filename, bot_token, channel_id):
        threading.Thread.__init__(self)
        self.user_id = user_id
        self.file_id = file_id
        self.temp_path = temp_path
        self.filename = filename
        self.client = TelegramClient(token=bot_token, channel_id=channel_id)


    def run(self):
        print(f"[UploadWorker] Starting upload for {self.filename} (ID: {self.file_id})")
        
        # New DB connection for thread
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        try:
            # 1. State: Uploading (Already set by caller, but we verify or update)
            # Verify channel first
            try:
                self.client.get_chat()
            except Exception as e:
                print(f"[UploadWorker] Channel verify failed: {e}")
                raise

            # Get total size and chunks
            size = get_file_size(self.temp_path)
            total_chunks = calculate_total_chunks(size)
            
            # Calculate full file hash (optional but good for integrity)
            full_hash = calculate_file_hash(self.temp_path)

            c.execute('UPDATE files SET size=?, chunks=?, file_hash=? WHERE id=?', 
                      (size, total_chunks, full_hash, self.file_id))
            conn.commit()

            message_ids = []
            chunk_hashes = []
            
            chunk_index = 0
            
            # 2. Loop Chunks
            for chunk_data in yield_chunks(self.temp_path):
                # Setup chunk filename
                chunk_index += 1
                chunk_name = f"{self.filename}.part{chunk_index:04d}"
                
                # Compute Hash
                chunk_hash = calculate_sha256(chunk_data)
                
                # Upload
                # We need a file-like object. memory is fine for 20MB.
                from io import BytesIO
                f = BytesIO(chunk_data)
                f.name = chunk_name # flask/requests might need this
                
                msg = self.client.send_document(f, chunk_name)
                msg_id = msg['message_id']
                
                # Update State
                message_ids.append(msg_id)
                chunk_hashes.append(chunk_hash)
                
                c.execute('''
                    UPDATE files 
                    SET uploaded_chunks=?, message_ids=?, chunk_hashes=? 
                    WHERE id=?
                ''', (chunk_index, json.dumps(message_ids), json.dumps(chunk_hashes), self.file_id))
                conn.commit()
                
                print(f"[UploadWorker] Uploaded chunk {chunk_index}/{total_chunks} for {self.filename}")
                
                # Rate Limit
                time.sleep(1.5)

            # 3. Completion
            c.execute("UPDATE files SET status='completed' WHERE id=?", (self.file_id,))
            conn.commit()
            print(f"[UploadWorker] Completed upload for {self.filename}")

        except Exception as e:
            print(f"[UploadWorker] Failed upload for {self.filename}: {e}")
            c.execute("UPDATE files SET status='failed' WHERE id=?", (self.file_id,))
            
            # Detect 401 Unauthorized or similar token issues
            if "401" in str(e) or "Unauthorized" in str(e):
                print(f"[UploadWorker] Detected invalid credentials for user {self.user_id}")
                c.execute("UPDATE users SET credentials_verified = 0 WHERE id = ?", (self.user_id,))
            
            conn.commit()
        finally:
            conn.close()
            # Clean up temp file
            if os.path.exists(self.temp_path):
                try:
                    os.remove(self.temp_path)
                except Exception as e:
                    print(f"Error removing temp file: {e}")

def start_upload(user_id, file_id, temp_path, filename, bot_token, channel_id):
    worker = UploadWorker(user_id, file_id, temp_path, filename, bot_token, channel_id)
    worker.start()

