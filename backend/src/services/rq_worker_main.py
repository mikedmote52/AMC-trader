# backend/src/services/rq_worker_main.py
import os, time, signal, sys, logging
from rq import Connection, Worker, Queue
from redis import Redis
from datetime import datetime

# Use the same queue name constants the API enqueues to
from backend.src.constants import DISCOVERY_QUEUE, RESULT_TTL_SECONDS, JOB_TIMEOUT_SECONDS

# Heartbeat key so ops can see the worker is alive
HEARTBEAT_KEY = os.getenv("WORKER_HEARTBEAT_KEY", "amc:discovery:worker:heartbeat")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

log = logging.getLogger("rq_worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def write_heartbeat(r):
    r.set(HEARTBEAT_KEY, datetime.utcnow().isoformat(), ex=120)

def main():
    try:
        # Test Redis connection first
        log.info(f"Testing Redis connection to {REDIS_URL}")
        r = Redis.from_url(REDIS_URL, decode_responses=True)
        r.ping()  # Test connection
        log.info("✅ Redis connection successful")
        
        qname = DISCOVERY_QUEUE
        log.info(f"Starting RQ worker on queue '{qname}'")
        
        # Test that we can import the job function
        try:
            from backend.src.jobs.discovery_job import run_discovery_job
            log.info("✅ Discovery job function imported successfully")
        except ImportError as e:
            log.error(f"❌ Cannot import discovery job function: {e}")
            return 1
        
        # Setup signal handling
        running = True
        def _sigterm(*_):
            nonlocal running
            running = False
            log.info("Received shutdown signal")

        signal.signal(signal.SIGTERM, _sigterm)
        signal.signal(signal.SIGINT, _sigterm)

        with Connection(r):
            w = Worker([Queue(qname)])
            
            # Start heartbeat thread
            def _hb():
                while running:
                    try:
                        write_heartbeat(r)
                        log.info(f"💓 Heartbeat written to {HEARTBEAT_KEY}")
                    except Exception as e:
                        log.warning(f"heartbeat error: {e}")
                    time.sleep(30)
            
            import threading
            heartbeat_thread = threading.Thread(target=_hb, daemon=True)
            heartbeat_thread.start()
            
            log.info(f"🚀 Worker started and listening on queue: {qname}")
            log.info(f"Worker will stay alive and process jobs continuously...")
            
            # This should block and keep the worker alive
            w.work(with_scheduler=False, burst=False)
            
    except Exception as e:
        log.error(f"❌ Worker startup failed: {e}")
        return 1
    
    log.info("Worker shutting down...")
    return 0

if __name__ == "__main__":
    sys.exit(main() or 0)