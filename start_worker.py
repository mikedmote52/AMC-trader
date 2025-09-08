#!/usr/bin/env python3
"""
RQ Worker startup script for Render
Handles module path and Redis connection properly
"""

import os
import sys
import redis
from rq import Connection, Worker
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# IMPORTANT: import registers task callables so RQ can resolve them
# Add backend source to Python path first
backend_path = os.path.join(os.getcwd(), 'backend', 'src')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Import the worker module to register the discovery tasks
try:
    import backend.src.worker  # This registers run_discovery function
    logger.info("✅ Imported worker module successfully")
except Exception as e:
    logger.error(f"❌ Failed to import worker module: {e}")
    sys.exit(1)

QUEUES = ["discovery"]

def main():
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        logger.error("❌ REDIS_URL environment variable is required")
        sys.exit(1)
        
    logger.info(f"Connecting to Redis: {redis_url.split('@')[-1]}")  # Hide credentials
    
    try:
        # Test Redis connection
        r = redis.from_url(redis_url, decode_responses=True)
        ping_result = r.ping()
        logger.info(f"✅ Redis ping: {ping_result}")
        
        # Check initial queue status
        from rq import Queue
        q = Queue("discovery", connection=r)
        logger.info(f"📊 Initial queue length: {len(q)}")
        
        # Start worker with connection context
        logger.info(f"🚀 Starting RQ worker for queues: {QUEUES}")
        with Connection(r):
            Worker(QUEUES).work(logging_level="INFO")
        
    except KeyboardInterrupt:
        logger.info("🛑 Worker stopped by user")
    except Exception as e:
        logger.error(f"❌ Worker startup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()