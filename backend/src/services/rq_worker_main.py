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
    r = Redis.from_url(REDIS_URL, decode_responses=True)
    qname = DISCOVERY_QUEUE  # e.g., "amc_discovery"
    log.info(f"Starting RQ worker on {qname} REDIS={REDIS_URL}")

    # small background heartbeat
    running = True
    def _sigterm(*_):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, _sigterm)
    signal.signal(signal.SIGINT, _sigterm)

    with Connection(r):
        w = Worker([Queue(qname)])
        # async heartbeat loop
        def _hb():
            while running:
                try:
                    write_heartbeat(r)
                    log.info(f"Heartbeat written to {HEARTBEAT_KEY}")
                except Exception as e:
                    log.warning(f"heartbeat error: {e}")
                time.sleep(30)
        import threading
        threading.Thread(target=_hb, daemon=True).start()
        log.info(f"Worker started, listening on queue: {qname}")
        w.work(with_scheduler=False, burst=False)

if __name__ == "__main__":
    sys.exit(main() or 0)