import os

# 20MB Strict Limit
CHUNK_SIZE_BYTES = 20 * 1024 * 1024 

def get_file_size(filepath):
    return os.path.getsize(filepath)

def yield_chunks(filepath):
    """
    Generator that yields chunks of bytes from a file.
    Ensures memory efficiency by reading only CHUNK_SIZE at a time.
    """
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(CHUNK_SIZE_BYTES)
            if not chunk:
                break
            yield chunk

def calculate_total_chunks(file_size):
    return (file_size + CHUNK_SIZE_BYTES - 1) // CHUNK_SIZE_BYTES
