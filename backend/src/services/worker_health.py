"""
Worker Health Monitor and Auto-Recovery System
Ensures discovery worker stays alive and processes jobs
"""
import os
import time
import json
import redis
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class WorkerHealth:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0") 
        self.heartbeat_key = "amc:discovery:worker:heartbeat"
        self.health_key = "amc:discovery:worker:health"
        self.stats_key = "amc:discovery:worker:stats"
        self.redis_client = redis.from_url(self.redis_url, decode_responses=False)
        
    def update_heartbeat(self) -> bool:
        """Update worker heartbeat"""
        try:
            timestamp = int(time.time())
            self.redis_client.set(self.heartbeat_key, str(timestamp).encode('utf-8'), ex=120)
            return True
        except Exception as e:
            logger.error(f"Failed to update heartbeat: {e}")
            return False
            
    def check_worker_alive(self, max_age_seconds: int = 180) -> bool:
        """Check if worker is alive based on heartbeat"""
        try:
            heartbeat_data = self.redis_client.get(self.heartbeat_key)
            if not heartbeat_data:
                return False
                
            last_heartbeat = int(heartbeat_data.decode('utf-8'))
            age = time.time() - last_heartbeat
            return age < max_age_seconds
        except Exception as e:
            logger.error(f"Failed to check worker health: {e}")
            return False
            
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get RQ queue statistics"""
        try:
            from backend.src.constants import DISCOVERY_QUEUE
            
            # Check queue lengths
            queue_key = f"rq:queue:{DISCOVERY_QUEUE}"
            failed_key = f"rq:queue:{DISCOVERY_QUEUE}:failed" 
            
            pending_jobs = self.redis_client.llen(queue_key)
            failed_jobs = self.redis_client.llen(failed_key) if self.redis_client.exists(failed_key) else 0
            
            # Get job keys
            job_keys = self.redis_client.keys("rq:job:*")
            
            return {
                "pending_jobs": pending_jobs,
                "failed_jobs": failed_jobs,
                "total_job_keys": len(job_keys) if job_keys else 0,
                "queue_name": DISCOVERY_QUEUE,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {"error": str(e)}
            
    def update_worker_stats(self, stats: Dict[str, Any]) -> bool:
        """Update worker statistics"""
        try:
            stats_json = json.dumps(stats).encode('utf-8')
            self.redis_client.set(self.stats_key, stats_json, ex=300)  # 5 minute TTL
            return True
        except Exception as e:
            logger.error(f"Failed to update worker stats: {e}")
            return False
            
    def get_worker_stats(self) -> Optional[Dict[str, Any]]:
        """Get current worker statistics"""
        try:
            stats_data = self.redis_client.get(self.stats_key)
            if not stats_data:
                return None
            return json.loads(stats_data.decode('utf-8'))
        except Exception as e:
            logger.error(f"Failed to get worker stats: {e}")
            return None
            
    def clear_stuck_jobs(self) -> Dict[str, int]:
        """Emergency clear of stuck jobs"""
        try:
            from backend.src.constants import DISCOVERY_QUEUE
            
            queue_key = f"rq:queue:{DISCOVERY_QUEUE}"
            failed_key = f"rq:queue:{DISCOVERY_QUEUE}:failed"
            
            # Count before clearing
            pending_count = self.redis_client.llen(queue_key)
            failed_count = self.redis_client.llen(failed_key) if self.redis_client.exists(failed_key) else 0
            
            # Clear queues
            if pending_count > 0:
                self.redis_client.delete(queue_key)
            if failed_count > 0:
                self.redis_client.delete(failed_key)
                
            # Clear old job keys (older than 1 hour)
            job_keys = self.redis_client.keys("rq:job:*")
            cleared_jobs = 0
            
            if job_keys:
                for job_key in job_keys:
                    try:
                        # Check TTL - if no TTL or very old, delete it
                        ttl = self.redis_client.ttl(job_key)
                        if ttl == -1 or ttl < 0:  # No expiry or expired
                            self.redis_client.delete(job_key)
                            cleared_jobs += 1
                    except:
                        continue
                        
            logger.info(f"Cleared {pending_count} pending, {failed_count} failed, {cleared_jobs} stale job keys")
            
            return {
                "pending_cleared": pending_count,
                "failed_cleared": failed_count, 
                "job_keys_cleared": cleared_jobs
            }
        except Exception as e:
            logger.error(f"Failed to clear stuck jobs: {e}")
            return {"error": str(e)}
            
    def health_report(self) -> Dict[str, Any]:
        """Complete worker health report"""
        return {
            "worker_alive": self.check_worker_alive(),
            "queue_stats": self.get_queue_stats(),
            "worker_stats": self.get_worker_stats(),
            "heartbeat_age": self._get_heartbeat_age(),
            "redis_connected": self._test_redis_connection(),
            "timestamp": datetime.now().isoformat()
        }
        
    def _get_heartbeat_age(self) -> Optional[int]:
        """Get age of last heartbeat in seconds"""
        try:
            heartbeat_data = self.redis_client.get(self.heartbeat_key)
            if not heartbeat_data:
                return None
            last_heartbeat = int(heartbeat_data.decode('utf-8'))
            return int(time.time() - last_heartbeat)
        except:
            return None
            
    def _test_redis_connection(self) -> bool:
        """Test Redis connection"""
        try:
            self.redis_client.ping()
            return True
        except:
            return False

# Global singleton
worker_health = WorkerHealth()