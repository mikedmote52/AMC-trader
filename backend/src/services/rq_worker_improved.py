#!/usr/bin/env python3
"""
Improved RQ Worker for AMC-TRADER Discovery
Fixes import issues and provides better error handling
"""
import os
import sys
import time
import signal
import logging
from pathlib import Path
from datetime import datetime

# Ensure proper Python path setup
current_dir = Path(__file__).parent
backend_src = current_dir.parent
project_root = backend_src.parent

# Add paths for imports
sys.path.insert(0, str(backend_src))
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('rq_worker_improved')

def setup_environment():
    """Validate and setup environment"""
    required_vars = ['REDIS_URL', 'POLYGON_API_KEY']
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        logger.error(f"❌ Missing required environment variables: {missing}")
        return False
        
    logger.info("✅ Environment variables validated")
    return True

def test_imports():
    """Test critical imports"""
    try:
        # Test RQ imports
        import redis
        from rq import Connection, Worker, Queue
        from rq.job import Job
        logger.info("✅ RQ imports successful")
        
        # Test job imports
        from jobs.discovery_job import run_discovery_job
        logger.info("✅ Discovery job import successful")
        
        # Test constants
        from constants import DISCOVERY_QUEUE
        logger.info(f"✅ Constants import successful, queue: {DISCOVERY_QUEUE}")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.info("🔧 Attempting alternative imports...")
        
        try:
            # Alternative import paths
            from backend.src.jobs.discovery_job import run_discovery_job
            from backend.src.constants import DISCOVERY_QUEUE
            logger.info("✅ Alternative imports successful")
            return True
        except ImportError as e2:
            logger.error(f"❌ Alternative imports also failed: {e2}")
            return False

def create_heartbeat_writer(redis_client, heartbeat_key="amc:discovery:worker:heartbeat"):
    """Create heartbeat writer function"""
    def write_heartbeat():
        try:
            heartbeat_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'pid': os.getpid(),
                'status': 'active'
            }
            redis_client.setex(heartbeat_key, 120, str(heartbeat_data))
            logger.info(f"💓 Heartbeat written: {heartbeat_key}")
        except Exception as e:
            logger.warning(f"⚠️ Heartbeat error: {e}")
    
    return write_heartbeat

def signal_handler(sig, frame):
    """Handle graceful shutdown"""
    logger.info(f"📡 Received signal {sig}, shutting down gracefully...")
    global running
    running = False

def main():
    """Main worker function with improved error handling"""
    global running
    running = True
    
    logger.info("🚀 Starting AMC-TRADER Discovery Worker (Improved)")
    
    # Step 1: Setup environment
    if not setup_environment():
        logger.error("❌ Environment setup failed")
        return 1
        
    # Step 2: Test imports
    if not test_imports():
        logger.error("❌ Import validation failed")
        return 1
    
    # Step 3: Setup Redis connection
    try:
        import redis
        from rq import Connection, Worker, Queue
        from constants import DISCOVERY_QUEUE
        
        redis_url = os.getenv('REDIS_URL')
        logger.info(f"🔌 Connecting to Redis: {redis_url.split('@')[-1] if '@' in redis_url else redis_url}")
        
        redis_client = redis.from_url(redis_url, decode_responses=True)
        redis_client.ping()
        logger.info("✅ Redis connection successful")
        
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return 1
    
    # Step 4: Setup signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Step 5: Setup heartbeat
    write_heartbeat = create_heartbeat_writer(redis_client)
    
    # Step 6: Start worker with heartbeat
    try:
        with Connection(redis_client):
            logger.info(f"🎯 Worker listening on queue: {DISCOVERY_QUEUE}")
            
            # Create worker
            worker = Worker(
                [Queue(DISCOVERY_QUEUE)],
                name=f"amc-discovery-worker-{os.getpid()}"
            )
            
            # Start heartbeat thread
            import threading
            def heartbeat_loop():
                while running:
                    write_heartbeat()
                    time.sleep(30)
            
            heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
            heartbeat_thread.start()
            
            logger.info("💓 Heartbeat thread started")
            logger.info("✅ Worker ready to process jobs")
            
            # Start processing jobs
            while running:
                try:
                    # Work with burst to allow checking running flag
                    worked = worker.work(burst=True, with_scheduler=False)
                    if not worked:
                        time.sleep(5)  # No jobs, wait a bit
                except KeyboardInterrupt:
                    logger.info("👋 Worker interrupted by user")
                    break
                except Exception as e:
                    logger.error(f"⚠️ Worker error: {e}")
                    time.sleep(10)  # Wait before retrying
                    
    except Exception as e:
        logger.error(f"❌ Worker failed: {e}")
        return 1
    
    logger.info("👋 Worker shutdown complete")
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)