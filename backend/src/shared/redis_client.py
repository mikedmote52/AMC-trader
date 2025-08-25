import redis
import os
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

def get_redis_client():
    """Get Redis client with configuration from environment"""
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    return redis.from_url(redis_url, decode_responses=True)

@contextmanager
def redis_lock(lock_key, ttl_seconds=240):  # 4 minutes default
    """
    Redis-based distributed lock to prevent job overlap
    
    Args:
        lock_key (str): Unique key for the lock
        ttl_seconds (int): Time to live for the lock in seconds (default 4 minutes)
    
    Yields:
        bool: True if lock acquired, False otherwise
    """
    client = get_redis_client()
    lock_acquired = False
    
    try:
        # Try to acquire lock with TTL
        lock_acquired = client.set(lock_key, "locked", nx=True, ex=ttl_seconds)
        
        if lock_acquired:
            logger.info(f"Lock acquired: {lock_key}")
            yield True
        else:
            logger.warning(f"Lock already exists: {lock_key}")
            yield False
            
    except Exception as e:
        logger.error(f"Redis lock error: {e}")
        yield False
        
    finally:
        if lock_acquired:
            try:
                client.delete(lock_key)
                logger.info(f"Lock released: {lock_key}")
            except Exception as e:
                logger.error(f"Failed to release lock {lock_key}: {e}")