#!/usr/bin/env python3
"""
RQ Worker startup script for Render
Handles module path and Redis connection properly
"""

import os
import sys
import redis
import rq
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Add backend source to Python path
    backend_path = os.path.join(os.getcwd(), 'backend', 'src')
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    logger.info(f"Python path: {sys.path[:3]}")  # Show first 3 entries
    
    # Get Redis URL
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    logger.info(f"Connecting to Redis: {redis_url.split('@')[-1]}")  # Hide credentials
    
    try:
        # Test Redis connection
        r = redis.from_url(redis_url, decode_responses=True)
        ping_result = r.ping()
        logger.info(f"Redis ping: {ping_result}")
        
        # Create queue
        q = rq.Queue("discovery", connection=r)
        logger.info(f"Queue length: {len(q)}")
        
        # Create and start worker
        worker = rq.Worker([q], connection=r)
        logger.info("Starting RQ worker for 'discovery' queue...")
        
        # Start worker (this blocks)
        worker.work(logging_level=logging.INFO)
        
    except Exception as e:
        logger.error(f"Worker startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()