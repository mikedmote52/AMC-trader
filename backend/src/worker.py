#!/usr/bin/env python3
"""
AMC-TRADER Background Worker
Runs discovery tasks asynchronously using RQ
"""

import os
import json
import time
import redis
from rq import get_current_job
from typing import Dict, List, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis connection
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(REDIS_URL, decode_responses=True)

# Cache settings
CACHE_KEY = "disc:candidates"
CACHE_TTL = int(os.getenv("DISCOVERY_CACHE_TTL", "60"))

def run_discovery(limit: int = 50) -> List[Dict]:
    """
    Run full discovery process and cache results
    This is the main worker function that RQ will execute
    """
    job = get_current_job()
    logger.info(f"Starting discovery job {job.id if job else 'manual'} with limit={limit}")
    
    try:
        # Progress tracking
        if job:
            job.meta["progress"] = 5
            job.meta["stage"] = "initializing"
            job.save_meta()
        
        # Import the BMS engine
        from backend.src.services.bms_engine_real import RealBMSEngine
        
        # Initialize engine
        polygon_key = os.getenv('POLYGON_API_KEY')
        if not polygon_key:
            raise ValueError("POLYGON_API_KEY not found")
            
        bms_engine = RealBMSEngine(polygon_key)
        
        if job:
            job.meta["progress"] = 10
            job.meta["stage"] = "engine_initialized"
            job.save_meta()
        
        # Run discovery
        logger.info("Running BMS discovery...")
        start_time = time.time()
        
        if job:
            job.meta["progress"] = 20
            job.meta["stage"] = "discovery_started"
            job.save_meta()
        
        # Use the existing discover_real_candidates method
        candidates = bms_engine.discover_real_candidates(limit=limit * 2)  # Get extra for filtering
        
        if job:
            job.meta["progress"] = 80
            job.meta["stage"] = "discovery_complete"
            job.save_meta()
        
        # Limit and sort results
        ranked = sorted(candidates, key=lambda x: x.get("bms_score", 0), reverse=True)[:limit]
        
        # Cache the results
        cache_data = {
            'candidates': ranked,
            'count': len(ranked),
            'timestamp': time.time(),
            'duration_seconds': time.time() - start_time,
            'cached': True,
            'engine': 'BMS v1.1 - Cached'
        }
        
        r.set(CACHE_KEY, json.dumps(cache_data, default=str), ex=CACHE_TTL)
        logger.info(f"Cached {len(ranked)} candidates with TTL={CACHE_TTL}s")
        
        if job:
            job.meta["progress"] = 100
            job.meta["stage"] = "complete"
            job.meta["candidates_found"] = len(ranked)
            job.save_meta()
        
        logger.info(f"Discovery job completed in {time.time() - start_time:.2f}s, found {len(ranked)} candidates")
        return ranked
        
    except Exception as e:
        logger.error(f"Discovery job failed: {e}")
        if job:
            job.meta["progress"] = -1
            job.meta["stage"] = "error"
            job.meta["error"] = str(e)
            job.save_meta()
        raise

def health_check() -> Dict:
    """Worker health check"""
    try:
        # Check Redis connection
        ping_result = r.ping()
        
        # Check cache
        cached = r.get(CACHE_KEY)
        cache_age = None
        if cached:
            cache_data = json.loads(cached)
            cache_age = time.time() - cache_data.get('timestamp', 0)
        
        return {
            'redis_connected': ping_result,
            'cache_exists': cached is not None,
            'cache_age_seconds': cache_age,
            'worker_healthy': True
        }
    except Exception as e:
        return {
            'redis_connected': False,
            'cache_exists': False,
            'cache_age_seconds': None,
            'worker_healthy': False,
            'error': str(e)
        }

if __name__ == "__main__":
    # Allow manual testing
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    print(f"Running manual discovery with limit={limit}")
    results = run_discovery(limit)
    print(f"Found {len(results)} candidates")
    for i, candidate in enumerate(results[:5]):
        print(f"{i+1}. {candidate['symbol']}: {candidate.get('bms_score', 0):.1f}")