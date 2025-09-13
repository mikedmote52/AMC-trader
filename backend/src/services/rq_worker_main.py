# backend/src/services/rq_worker_main.py
import os, time, signal, sys, logging, threading
from rq import Worker, Queue
from rq.connections import push_connection, pop_connection
from redis import Redis
from backend.src.constants import DISCOVERY_QUEUE
from backend.src.services.worker_health import worker_health

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("rq_worker")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
HEARTBEAT_KEY = os.getenv("WORKER_HEARTBEAT_KEY", "amc:discovery:worker:heartbeat")

def hb():
    while True:
        try:
            worker_health.update_heartbeat()
            queue_stats = worker_health.get_queue_stats()
            log.info(f"💓 HEARTBEAT OK - Worker alive, {queue_stats.get('pending_jobs', 0)} jobs pending")
            print(f"💓 HEARTBEAT OK - Worker alive, {queue_stats.get('pending_jobs', 0)} jobs pending at {time.ctime()}")
        except Exception as e:
            log.error(f"❌ HEARTBEAT ERROR: {e}")
            print(f"❌ HEARTBEAT ERROR: {e}")
        time.sleep(30)

def main():
    log.info(f"🚀 BOOT WORKER: redis={REDIS_URL} queue={DISCOVERY_QUEUE}")
    print(f"🚀 BOOT WORKER: redis={REDIS_URL} queue={DISCOVERY_QUEUE}")
    
    # Test Redis URL scheme for Render
    if "rediss://" in REDIS_URL:
        log.info("✅ Using rediss:// (TLS) for Render/Upstash")
        print("✅ Using rediss:// (TLS) for Render/Upstash")
    else:
        log.info(f"⚠️  Using Redis scheme: {REDIS_URL.split('://')[0]}")
        print(f"⚠️  Using Redis scheme: {REDIS_URL.split('://')[0]}")
    
    # Test job import BEFORE starting worker
    try:
        from backend.src.jobs.discovery_job import run_discovery_job  # noqa
        log.info("✅ IMPORT run_discovery_job OK")
        print("✅ IMPORT run_discovery_job OK")
    except Exception as e:
        log.exception(f"❌ IMPORT run_discovery_job FAILED: {e}")
        print(f"❌ IMPORT run_discovery_job FAILED: {e}")
        print("⏰ Sleeping 10s to show error in logs")
        time.sleep(10)
        return 1
    
    running = True
    def stop(*_): 
        nonlocal running
        running = False
        log.info("🛑 SHUTDOWN SIGNAL RECEIVED")
        print("🛑 SHUTDOWN SIGNAL RECEIVED")

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    # FOREVER LOOP - CANNOT EXIT
    while running:
        try:
            log.info("🔗 CONNECTING TO REDIS...")
            print("🔗 CONNECTING TO REDIS...")
            r = Redis.from_url(REDIS_URL)
            
            # Prove connectivity early
            r.ping()
            log.info("✅ REDIS CONNECTION OK")
            print("✅ REDIS CONNECTION OK")
            
            # Start heartbeat thread
            threading.Thread(target=hb, daemon=True).start()
            
            push_connection(r)
            try:
                q = Queue(DISCOVERY_QUEUE)
                log.info(f"📋 STARTING RQ WORKER ON QUEUE='{q.name}' (exact match required)")
                print(f"📋 STARTING RQ WORKER ON QUEUE='{q.name}' (exact match required)")
                
                # Show queue state
                queue_length = len(q)
                log.info(f"📊 QUEUE LENGTH: {queue_length} jobs waiting")
                print(f"📊 QUEUE LENGTH: {queue_length} jobs waiting")
                
                w = Worker([q])
                log.info("🎯 WORKER.WORK() STARTING - THIS SHOULD BLOCK FOREVER")
                print("🎯 WORKER.WORK() STARTING - THIS SHOULD BLOCK FOREVER")
                
                # This should NEVER return if burst=False
                w.work(with_scheduler=False, burst=False)
                
                # If we reach here, something is wrong
                log.warning("⚠️  WORKER.WORK() RETURNED UNEXPECTEDLY - RETRYING IN 5s")
                print("⚠️  WORKER.WORK() RETURNED UNEXPECTEDLY - RETRYING IN 5s")
                time.sleep(5)
            finally:
                pop_connection()
                
        except Exception as e:
            log.exception(f"💥 WORKER LOOP CRASHED: {e}")
            print(f"💥 WORKER LOOP CRASHED: {e}")
            log.info("⏰ RETRYING IN 5 SECONDS...")
            print("⏰ RETRYING IN 5 SECONDS...")
            time.sleep(5)
    
    log.info("🏁 WORKER SHUTDOWN REQUESTED")
    print("🏁 WORKER SHUTDOWN REQUESTED")
    return 0

if __name__ == "__main__":
    print("🎬 WORKER MAIN STARTING...")
    sys.exit(main())