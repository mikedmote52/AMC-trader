"""
Discovery Admin Routes - Manual triggers and cache inspection
Open endpoints for discovery management
"""
import json
import logging
import os
import asyncio
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException
import redis.asyncio as redis

from backend.src.constants import CACHE_KEY_CONTENDERS

logger = logging.getLogger(__name__)

router = APIRouter()

async def run_discovery_inline() -> Dict[str, Any]:
    """Run discovery job inline and return summary"""
    try:
        # Import the discovery module
        from backend.src.jobs.discover_no_fallback import DiscoverySystem

        # Create and run discovery system
        discovery = DiscoverySystem()
        await discovery.run()

        # Check what was written to cache
        redis_client = redis.from_url(os.getenv('REDIS_URL'))
        cache_data = await redis_client.get(CACHE_KEY_CONTENDERS)
        ttl = await redis_client.ttl(CACHE_KEY_CONTENDERS)
        await redis_client.close()

        if cache_data:
            payload = json.loads(cache_data)
            written = payload.get('count', 0)
        else:
            written = 0

        # Emit socket event on successful cache update
        if written > 0:
            try:
                from backend.src.sockets import emit_cache_update
                await emit_cache_update("candidate")
            except Exception as e:
                logger.warning(f"Socket emit failed (non-blocking): {e}")

        return {
            "written": written,
            "key": CACHE_KEY_CONTENDERS,
            "ttl": ttl if ttl > 0 else None,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Inline discovery failed: {e}")
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")

@router.post("/api/discovery/run-now")
async def trigger_discovery_now():
    """Run discovery job immediately and return summary"""
    logger.info("🚀 Manual discovery trigger initiated")
    result = await run_discovery_inline()
    logger.info(f"✅ Manual discovery complete: {result['written']} candidates written")
    return result

@router.post("/api/discovery/clear-cache")
async def clear_discovery_cache():
    """Clear discovery cache"""
    try:
        redis_client = redis.from_url(os.getenv('REDIS_URL'))
        deleted = await redis_client.delete(CACHE_KEY_CONTENDERS)
        await redis_client.close()

        logger.info(f"🗑️ Discovery cache cleared: {deleted} keys deleted")
        return {"deleted": deleted}

    except Exception as e:
        logger.error(f"Cache clear failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cache clear failed: {str(e)}")

@router.get("/api/discovery/cache/peek")
async def peek_discovery_cache():
    """Inspect discovery cache contents"""
    try:
        redis_client = redis.from_url(os.getenv('REDIS_URL'))

        # Check if key exists
        exists = await redis_client.exists(CACHE_KEY_CONTENDERS)

        if not exists:
            await redis_client.close()
            return {
                "exists": False,
                "ttl": None,
                "len": 0,
                "sample": []
            }

        # Get TTL and data
        ttl = await redis_client.ttl(CACHE_KEY_CONTENDERS)
        cache_data = await redis_client.get(CACHE_KEY_CONTENDERS)
        await redis_client.close()

        if cache_data:
            try:
                payload = json.loads(cache_data)
                candidates = payload.get('candidates', [])
                sample = candidates[:3] if candidates else []

                return {
                    "exists": True,
                    "ttl": ttl if ttl > 0 else None,
                    "len": len(candidates),
                    "sample": sample
                }
            except json.JSONDecodeError:
                return {
                    "exists": True,
                    "ttl": ttl if ttl > 0 else None,
                    "len": 0,
                    "sample": [],
                    "error": "corrupted_data"
                }
        else:
            return {
                "exists": False,
                "ttl": None,
                "len": 0,
                "sample": []
            }

    except Exception as e:
        logger.error(f"Cache peek failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cache peek failed: {str(e)}")