"""
Redis client singleton for AMC trading system.
Provides a single Redis connection instance using REDIS_URL from environment.
"""

import os
import redis
from typing import Optional
import structlog
from datetime import datetime

logger = structlog.get_logger()

class RedisClient:
    """Singleton Redis client"""
    
    _instance: Optional[redis.Redis] = None
    _initialized: bool = False
    
    @classmethod
    def get_instance(cls) -> redis.Redis:
        """Get singleton Redis client instance"""
        if not cls._initialized:
            cls._initialize()
        return cls._instance
    
    @classmethod
    def _initialize(cls):
        """Initialize Redis connection from REDIS_URL environment variable"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            cls._instance = redis.from_url(redis_url, decode_responses=True)
            
            # Test connection
            cls._instance.ping()
            logger.info("Redis client initialized successfully", url=redis_url.split('@')[-1] if '@' in redis_url else redis_url)
            cls._initialized = True
            
        except Exception as e:
            logger.error("Failed to initialize Redis client", error=str(e))
            raise RuntimeError(f"Redis initialization failed: {e}")
    
    @classmethod
    def publish_discovery_contenders(cls, contenders: list, ttl: int = 600, strategy: str = None):
        """
        Publish discovery contenders to Redis for API consumption
        
        Args:
            contenders: List of contender dictionaries with symbol, score, reason, etc.
            ttl: Time to live in seconds (default 600 = 10 minutes)
            strategy: Strategy identifier (legacy_v0, hybrid_v1, etc.)
        """
        import json
        from datetime import datetime
        
        client = cls.get_instance()
        
        try:
            contenders_json = json.dumps(contenders)
            
            # Detect strategy from contenders if not provided
            if not strategy and contenders:
                detected_strategy = contenders[0].get('strategy', 'legacy_v0')
                strategy = detected_strategy
            
            strategy = strategy or 'legacy_v0'
            
            # Strategy-specific keys (new format expected by API readers)
            v2_cont_key = f"amc:discovery:v2:contenders.latest:{strategy}"
            v1_cont_key = f"amc:discovery:contenders.latest:{strategy}"
            
            # Legacy fallback keys
            v2_fallback = "amc:discovery:v2:contenders.latest"
            v1_fallback = "amc:discovery:contenders.latest"
            
            # Publish to all expected keys
            keys_written = []
            for key in [v2_cont_key, v1_cont_key, v2_fallback, v1_fallback]:
                client.set(key, contenders_json, ex=ttl)
                keys_written.append(key)
            
            # Publish status with count and timestamp
            status_key = "amc:discovery:status"
            status = {
                "count": len(contenders),
                "ts": datetime.utcnow().isoformat() + "Z",
                "strategy": strategy
            }
            status_json = json.dumps(status)
            client.set(status_key, status_json, ex=ttl)
            
            logger.info(
                "Published discovery results to Redis",
                contenders_count=len(contenders),
                strategy=strategy,
                ttl_seconds=ttl,
                keys_written=keys_written,
                status_key=status_key
            )
            
        except Exception as e:
            logger.error("Failed to publish discovery results to Redis", error=str(e))
            raise

# Convenience function for easy import
def get_redis_client() -> redis.Redis:
    """Get Redis client instance"""
    return RedisClient.get_instance()

def publish_discovery_contenders(contenders: list, ttl: int = 600, strategy: str = None):
    """Publish discovery contenders to Redis"""
    RedisClient.publish_discovery_contenders(contenders, ttl, strategy)