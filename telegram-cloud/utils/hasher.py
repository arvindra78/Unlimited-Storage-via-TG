import hashlib

def calculate_sha256(data):
    """
    Calculate SHA-256 hash of a bytes object.
    """
    sha256_hash = hashlib.sha256()
    sha256_hash.update(data)
    return sha256_hash.hexdigest()

def calculate_file_hash(filepath):
    """
    Calculate SHA-256 of an entire file efficiently.
    """
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        # Read in 8k blocks for efficiency
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()
