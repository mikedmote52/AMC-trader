"""
Discovery Routes - AlphaStack 4.1 Enhanced Integration
Provides backward-compatible discovery functions for existing routes
"""
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
import redis.asyncio as redis
import os

from constants import CACHE_KEY_CONTENDERS

logger = logging.getLogger(__name__)

async def get_contenders(limit: int = 50) -> Dict[str, Any]:
    """
    Get current discovery contenders from cache or run fresh discovery
    Backward-compatible function for existing routes
    """
    try:
        # Try to get from Redis cache first
        redis_client = redis.from_url(os.getenv('REDIS_URL'))
        cache_data = await redis_client.get(CACHE_KEY_CONTENDERS)
        await redis_client.close()
        
        if cache_data:
            try:
                cached_payload = json.loads(cache_data)
                candidates = cached_payload.get('candidates', [])
                
                # Limit results if requested
                if limit and len(candidates) > limit:
                    candidates = candidates[:limit]
                
                return {
                    "success": True,
                    "count": len(candidates),
                    "data": candidates,
                    "source": "cache",
                    "engine": cached_payload.get('engine', 'unknown'),
                    "timestamp": cached_payload.get('iso_timestamp', datetime.now().isoformat())
                }
            except json.JSONDecodeError:
                logger.warning("Corrupted cache data, running fresh discovery")
        
        # Cache miss or corrupted - run fresh discovery
        logger.info("Cache miss, running fresh AlphaStack 4.1 discovery")
        
        try:
            from jobs.discovery_job import run_discovery_job
            result = await run_discovery_job(limit)
            
            if result['status'] == 'success':
                return {
                    "success": True,
                    "count": result['count'],
                    "data": result['candidates'],
                    "source": "fresh_discovery",
                    "engine": result['engine'],
                    "execution_time_sec": result['execution_time_sec'],
                    "pipeline_stats": result['pipeline_stats'],
                    "timestamp": datetime.now().isoformat()
                }
            else:
                logger.error(f"Discovery job failed: {result.get('error')}")
                return {
                    "success": False,
                    "count": 0,
                    "data": [],
                    "error": result.get('error', 'Unknown discovery error'),
                    "source": "failed_discovery",
                    "timestamp": datetime.now().isoformat()
                }
                
        except ImportError as e:
            logger.error(f"Failed to import discovery job: {e}")
            return {
                "success": False,
                "count": 0,
                "data": [],
                "error": f"Discovery system not available: {e}",
                "source": "import_error",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"get_contenders failed: {e}")
        return {
            "success": False,
            "count": 0,
            "data": [],
            "error": str(e),
            "source": "exception",
            "timestamp": datetime.now().isoformat()
        }

async def get_discovery_status() -> Dict[str, Any]:
    """
    Get current discovery system status
    """
    try:
        redis_client = redis.from_url(os.getenv('REDIS_URL'))
        
        # Check cache status
        cache_data = await redis_client.get(CACHE_KEY_CONTENDERS)
        cache_info = {"exists": False}
        
        if cache_data:
            try:
                payload = json.loads(cache_data)
                cache_info = {
                    "exists": True,
                    "count": payload.get('count', 0),
                    "engine": payload.get('engine', 'unknown'),
                    "age_seconds": int(datetime.now().timestamp() - payload.get('timestamp', 0))
                }
            except json.JSONDecodeError:
                cache_info = {"exists": True, "corrupted": True}
        
        await redis_client.close()
        
        return {
            "success": True,
            "system": "AlphaStack 4.0 Unified Discovery",
            "cache": cache_info,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"get_discovery_status failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Legacy function aliases for backward compatibility
get_candidates = get_contenders  # Some routes might use this name
get_discovery_results = get_contenders  # Alternative name