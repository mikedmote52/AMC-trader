"""
Discovery Fallback System - Run discovery synchronously when worker is down
Ensures the system always works even if RQ worker fails
"""
import os
import time
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class DiscoveryFallback:
    """Synchronous fallback for discovery when RQ worker is down"""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
    async def run_discovery_sync(self, strategy: str = "hybrid_v1", limit: int = 50) -> Dict[str, Any]:
        """
        Run discovery pipeline synchronously without RQ worker
        This is the fallback when worker is down
        """
        start_time = time.time()
        
        try:
            logger.info(f"🚨 FALLBACK: Running discovery sync - strategy={strategy}, limit={limit}")
            
            # Import here to avoid circular imports
            from backend.src.jobs.discover import select_candidates
            from backend.src.constants import CACHE_KEY_CONTENDERS
            
            # Run discovery directly
            result = await asyncio.to_thread(select_candidates, limit, strategy)
            
            if not result or result.get('status') != 'success':
                logger.error(f"Discovery sync failed: {result}")
                return {
                    "status": "error",
                    "message": "Sync discovery failed",
                    "elapsed_seconds": time.time() - start_time
                }
                
            # Cache the results
            await self._cache_results(result, strategy)
            
            elapsed_seconds = time.time() - start_time
            
            return {
                "status": "success",
                "method": "sync_fallback",
                "strategy": strategy,
                "universe_size": result.get('universe_size', 0),
                "filtered_size": result.get('filtered_size', 0),
                "count": result.get('count', 0),
                "candidates": result.get('candidates', []),
                "elapsed_seconds": elapsed_seconds,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.exception(f"Discovery sync fallback failed: {e}")
            return {
                "status": "error",
                "message": f"Sync fallback failed: {str(e)}",
                "elapsed_seconds": time.time() - start_time
            }
            
    async def _cache_results(self, result: Dict[str, Any], strategy: str) -> bool:
        """Cache discovery results to Redis"""
        try:
            import redis.asyncio as redis
            from backend.src.constants import CACHE_KEY_CONTENDERS, CACHE_TTL_SECONDS
            
            redis_client = redis.from_url(self.redis_url, decode_responses=False)
            
            # Create cache payload
            cache_payload = {
                'timestamp': int(datetime.now().timestamp()),
                'iso_timestamp': datetime.now().isoformat(),
                'strategy': strategy,
                'universe_size': result.get('universe_size', 0),
                'filtered_size': result.get('filtered_size', 0),
                'count': result.get('count', 0),
                'candidates': result.get('candidates', []),
                'engine': 'Discovery Sync Fallback',
                'job_id': f'sync_fallback_{int(time.time())}'
            }
            
            # Store with strategy-specific key
            cache_key = f"{CACHE_KEY_CONTENDERS}:{strategy}"
            cache_data = json.dumps(cache_payload, default=str).encode('utf-8')
            
            await redis_client.setex(cache_key, CACHE_TTL_SECONDS, cache_data)
            
            # Also store in main key for compatibility
            await redis_client.setex(CACHE_KEY_CONTENDERS, CACHE_TTL_SECONDS, cache_data)
            
            await redis_client.close()
            
            logger.info(f"✅ Cached {result.get('count', 0)} candidates with strategy {strategy}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache sync results: {e}")
            return False
            
    def can_run_sync(self) -> bool:
        """Check if we can run synchronous discovery"""
        try:
            # Check if required modules are available
            from backend.src.jobs.discover import select_candidates
            from backend.src.services.bms_engine_real import RealBMSEngine
            return True
        except ImportError as e:
            logger.error(f"Cannot run sync discovery - missing modules: {e}")
            return False
            
    async def health_check(self) -> Dict[str, Any]:
        """Check fallback system health"""
        return {
            "can_run_sync": self.can_run_sync(),
            "redis_url_configured": bool(self.redis_url),
            "timestamp": datetime.now().isoformat()
        }

# Global singleton
discovery_fallback = DiscoveryFallback()