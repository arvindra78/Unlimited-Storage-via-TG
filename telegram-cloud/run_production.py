# Production Deployment with Waitress (Optimized)

from waitress import serve
from app import app
import os

if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    
    # PERFORMANCE TUNING
    threads = int(os.getenv('THREADS', 8))  # Increased for parallel downloads
    channel_timeout = int(os.getenv('CHANNEL_TIMEOUT', 300))  # 5 min for large files
    recv_bytes = int(os.getenv('RECV_BYTES', 262144))  # 256KB buffer
    send_bytes = int(os.getenv('SEND_BYTES', 262144))  # 256KB buffer
    
    print("=" * 60)
    print("🚀 Unlimited Storage Production Server")
    print("=" * 60)
    print(f"Host: {host}:{port}")
    print(f"Threads: {threads} (optimized for parallel downloads)")
    print(f"Channel Timeout: {channel_timeout}s")
    print(f"Recv Buffer: {recv_bytes // 1024}KB")
    print(f"Send Buffer: {send_bytes // 1024}KB")
    print("=" * 60)
    print("PERFORMANCE FEATURES:")
    print("  ✓ Parallel chunk prefetching (3-4 chunks ahead)")
    print("  ✓ Background hash verification")
    print("  ✓ Direct streaming (no buffering)")
    print("  ✓ IDM compatible headers")
    print("=" * 60)
    
    serve(
        app,
        host=host,
        port=port,
        threads=threads,
        channel_timeout=channel_timeout,
        recv_bytes=recv_bytes,
        send_bytes=send_bytes,
        # Disable output buffering for streaming
        asyncore_use_poll=True,
        # Connection handling
        backlog=512,
        # Expose server header
        ident='Waitress/Unlimited-Storage'
    )
