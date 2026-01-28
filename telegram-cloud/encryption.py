"""
Encryption utilities for TeleCloud.
Encrypts bot tokens at rest using Fernet (symmetric encryption).
"""

from cryptography.fernet import Fernet
import base64
import hashlib
import os

def get_encryption_key():
    """
    Derive encryption key from SECRET_KEY in environment.
    Uses consistent key derivation so same SECRET_KEY = same encryption key.
    """
    secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Derive 32-byte key from secret using SHA256
    key_material = hashlib.sha256(secret_key.encode()).digest()
    # Fernet requires base64-encoded 32-byte key
    return base64.urlsafe_b64encode(key_material)

def encrypt_bot_token(plaintext_token):
    """
    Encrypt bot token for storage.
    Returns base64-encoded encrypted string.
    """
    if not plaintext_token:
        return None
    
    key = get_encryption_key()
    f = Fernet(key)
    encrypted = f.encrypt(plaintext_token.encode())
    return encrypted.decode()

def decrypt_bot_token(encrypted_token):
    """
    Decrypt bot token for use.
    Returns plaintext token string.
    """
    if not encrypted_token:
        return None
    
    try:
        key = get_encryption_key()
        f = Fernet(key)
        decrypted = f.decrypt(encrypted_token.encode())
        return decrypted.decode()
    except Exception as e:
        print(f"Decryption error: {e}")
        return None
