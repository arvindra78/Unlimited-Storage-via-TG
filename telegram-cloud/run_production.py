# Production Deployment with Waitress

from waitress import serve
from app import app
import os

if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    threads = int(os.getenv('THREADS', 4))
    
    print(f"Starting Waitress server on {host}:{port} with {threads} threads")
    print("This is a PRODUCTION server, not Flask dev server")
    
    serve(app, host=host, port=port, threads=threads)
