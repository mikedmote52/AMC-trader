#!/usr/bin/env python3
"""
AMC-TRADER Discovery Worker
Processes discovery jobs in background using Redis Queue (RQ)
"""
import os
import sys
import logging
import signal
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(backend_path / 'src'))

import redis
from rq import Connection, Worker
from rq.logutils import setup_loggers

from backend.src.constants import DISCOVERY_QUEUE, validate_environment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def signal_handler(sig, frame):
    """Handle graceful shutdown"""
    logger.info(f"Received signal {sig}, shutting down gracefully...")
    sys.exit(0)

def main():
    """Start the discovery worker"""
    try:
        # Validate environment
        validate_environment()
        logger.info("✅ Environment validation passed")
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Connect to Redis
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        logger.info(f"Connecting to Redis: {redis_url.split('@')[-1]}")  # Don't log credentials
        
        r = redis.from_url(redis_url)
        
        # Test Redis connection
        r.ping()
        logger.info("✅ Redis connection successful")
        
        # Import job modules so RQ can find them
        logger.info("Importing job modules...")
        import backend.src.jobs.discovery_job  # noqa
        logger.info("✅ Job modules imported")
        
        # Set up RQ logging
        setup_loggers()
        
        # Start worker
        with Connection(r):
            logger.info(f"🚀 Starting worker for queue: {DISCOVERY_QUEUE}")
            logger.info("Worker ready to process discovery jobs...")
            
            worker = Worker(
                [DISCOVERY_QUEUE],
                name=f"discovery-worker-{os.getpid()}"
            )
            
            # Start processing jobs
            worker.work(
                logging_level="INFO",
                with_scheduler=False  # We don't need scheduled jobs
            )
            
    except KeyboardInterrupt:
        logger.info("👋 Worker shutdown by user")
    except Exception as e:
        logger.error(f"❌ Worker failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()