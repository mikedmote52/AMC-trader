"""
AMC-TRADER Async Discovery API Routes
Non-blocking discovery using RQ background jobs
"""

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import logging
import json
import time
import os
import asyncio
import redis
import rq
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

# Redis and RQ setup
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(REDIS_URL, decode_responses=True)
q = rq.Queue("discovery", connection=r)

# Cache settings
CACHE_KEY = "disc:candidates"
CACHE_TTL = int(os.getenv("DISCOVERY_CACHE_TTL", "60"))

def _cache_get(key: str) -> Optional[Dict]:
    """Get data from Redis cache"""
    try:
        val = r.get(key)
        return json.loads(val) if val else None
    except Exception as e:
        logger.error(f"Cache get error: {e}")
        return None

def _cache_set(key: str, value: Dict, ttl: int = CACHE_TTL) -> bool:
    """Set data in Redis cache"""
    try:
        r.set(key, json.dumps(value, default=str), ex=ttl)
        return True
    except Exception as e:
        logger.error(f"Cache set error: {e}")
        return False

@router.get("/candidates")
async def get_candidates(
    limit: int = Query(50, description="Maximum number of candidates to return"),
    task: Optional[str] = Query(None, description="Job ID to check progress"),
    force_refresh: bool = Query(False, description="Force new discovery job")
):
    """
    Get BMS candidates with async processing
    
    Flow:
    1. If cached data exists and not force_refresh -> return immediately
    2. If task ID provided -> return job progress/results
    3. If no cache and no task -> enqueue new job and return 202 with task ID
    """
    try:
        # 1. Check cache first (unless force refresh)
        if not force_refresh and not task:
            cached = _cache_get(CACHE_KEY)
            if cached and cached.get('candidates'):
                candidates = cached['candidates'][:limit]
                logger.info(f"Returning {len(candidates)} cached candidates")
                return {
                    "status": "cached",
                    "candidates": candidates,
                    "count": len(candidates),
                    "timestamp": cached.get('timestamp'),
                    "engine": "BMS v1.1 - Cached",
                    "cached": True,
                    "cache_age_seconds": time.time() - cached.get('timestamp', 0)
                }
        
        # 2. If task ID provided, check job status
        if task:
            try:
                job = rq.job.Job.fetch(task, connection=r)
                job_status = job.get_status()
                meta = job.meta or {}
                
                if job_status == "finished":
                    # Job completed, cache results and return
                    result = job.result
                    if result:
                        cache_data = {
                            'candidates': result,
                            'count': len(result),
                            'timestamp': time.time(),
                            'cached': True,
                            'engine': 'BMS v1.1 - Fresh'
                        }
                        _cache_set(CACHE_KEY, cache_data)
                        
                        candidates = result[:limit]
                        return {
                            "status": "ready",
                            "candidates": candidates,
                            "count": len(candidates),
                            "timestamp": datetime.now().isoformat(),
                            "engine": "BMS v1.1 - Fresh",
                            "cached": False
                        }
                
                elif job_status == "failed":
                    error_msg = str(job.exc_info) if job.exc_info else "Unknown error"
                    return JSONResponse(
                        status_code=500,
                        content={
                            "status": "failed",
                            "error": error_msg,
                            "task": task
                        }
                    )
                
                else:
                    # Job still running
                    return {
                        "status": job_status,
                        "progress": meta.get("progress", 0),
                        "stage": meta.get("stage", "unknown"),
                        "task": task,
                        "poll_url": f"/discovery/candidates?task={task}"
                    }
                    
            except rq.exceptions.NoSuchJobError:
                return JSONResponse(
                    status_code=404,
                    content={"status": "not_found", "error": f"Job {task} not found"}
                )
            except Exception as e:
                logger.error(f"Error checking job {task}: {e}")
                return JSONResponse(
                    status_code=500,
                    content={"status": "error", "error": str(e)}
                )
        
        # 3. No cache, no active job -> check if workers are available
        logger.info(f"No cached data available (limit={limit}, force_refresh={force_refresh})")
        
        # Check for active workers
        workers = rq.Worker.all(connection=r)
        active_workers = [w for w in workers if w.get_state() == 'busy']
        
        if len(workers) == 0:
            # FALLBACK: No workers available, run discovery directly in web process
            logger.warning("No RQ workers available, running discovery directly in web process")
            
            try:
                # Import and run discovery function directly
                from backend.src.worker import run_discovery
                candidates = await asyncio.to_thread(run_discovery, limit)
                
                # Cache results immediately
                cache_data = {
                    'candidates': candidates,
                    'count': len(candidates),
                    'timestamp': time.time(),
                    'cached': True,
                    'engine': 'BMS v1.1 - Direct (No Workers)'
                }
                _cache_set(CACHE_KEY, cache_data)
                
                return {
                    "status": "ready",
                    "candidates": candidates[:limit],
                    "count": len(candidates[:limit]),
                    "timestamp": datetime.now().isoformat(),
                    "engine": "BMS v1.1 - Direct (No Workers)",
                    "cached": False,
                    "fallback_mode": True
                }
                
            except Exception as e:
                logger.error(f"Direct discovery failed: {e}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error", 
                        "error": f"Discovery failed: {str(e)}",
                        "fallback_attempted": True
                    }
                )
        else:
            # Normal path: enqueue job for worker processing
            logger.info(f"Enqueueing discovery job for {len(workers)} available workers")
            
            job = q.enqueue(
                "backend.src.worker.run_discovery",
                limit,
                job_timeout=600,  # 10 minute timeout
                result_ttl=300,   # Keep results for 5 minutes
                failure_ttl=60    # Keep failure info for 1 minute
            )
            
            response = {
                "status": "queued",
                "task": job.id,
                "poll_url": f"/discovery/candidates?task={job.id}",
                "message": "Discovery job started. Use task ID to check progress.",
                "estimated_time_seconds": 30
            }
            
            return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=response)
        
    except Exception as e:
        logger.error(f"Error in get_candidates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/candidates/trade-ready")
async def get_trade_ready_candidates(
    limit: int = Query(10, description="Max trade-ready candidates"),
    task: Optional[str] = Query(None, description="Job ID to check progress")
):
    """Get only TRADE_READY candidates (BMS score >= 75)"""
    # Get all candidates first
    result = await get_candidates(limit=limit * 2, task=task)
    
    if isinstance(result, JSONResponse):
        return result
    
    if result.get("status") == "cached" or result.get("status") == "ready":
        candidates = result.get("candidates", [])
        trade_ready = [c for c in candidates if c.get("action") == "TRADE_READY"][:limit]
        
        result["candidates"] = trade_ready
        result["count"] = len(trade_ready)
        result["filter"] = "TRADE_READY"
        
    return result

@router.get("/progress/{task_id}")
async def get_discovery_progress(task_id: str):
    """Get detailed progress for a discovery job"""
    try:
        job = rq.job.Job.fetch(task_id, connection=r)
        meta = job.meta or {}
        
        return {
            "task": task_id,
            "status": job.get_status(),
            "progress": meta.get("progress", 0),
            "stage": meta.get("stage", "unknown"),
            "candidates_found": meta.get("candidates_found"),
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
            "error": meta.get("error") if job.get_status() == "failed" else None
        }
    except rq.exceptions.NoSuchJobError:
        raise HTTPException(status_code=404, detail=f"Job {task_id} not found")
    except Exception as e:
        logger.error(f"Error getting progress for {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cache")
async def clear_cache():
    """Clear the discovery cache (force fresh discovery)"""
    try:
        result = r.delete(CACHE_KEY)
        return {"cache_cleared": bool(result), "key": CACHE_KEY}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/queue")
async def clear_queue():
    """Clear the job queue (emergency cleanup)"""
    try:
        from rq import Queue
        q = Queue("discovery", connection=r)
        cleared = q.empty()
        return {
            "queue_cleared": True, 
            "jobs_removed": cleared,
            "message": "All pending discovery jobs removed"
        }
    except Exception as e:
        logger.error(f"Error clearing queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queue-status")
async def get_queue_status():
    """Get RQ queue status and worker information"""
    try:
        queue_length = len(q)
        jobs_info = []
        
        # Get recent jobs
        for job in q.jobs[:5]:  # Last 5 jobs
            jobs_info.append({
                "id": job.id,
                "status": job.get_status(),
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "meta": job.meta
            })
        
        # Check for active workers
        workers = rq.Worker.all(connection=r)
        worker_info = []
        for worker in workers:
            worker_info.append({
                "name": worker.name,
                "state": worker.get_state(),
                "current_job": worker.get_current_job_id(),
                "last_heartbeat": worker.last_heartbeat.isoformat() if worker.last_heartbeat else None
            })
        
        return {
            "queue_length": queue_length,
            "recent_jobs": jobs_info,
            "workers": worker_info,
            "worker_count": len(worker_info)
        }
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/contenders")
async def get_contenders(
    limit: int = Query(50, description="Maximum number of contenders to return"),
    task: Optional[str] = Query(None, description="Job ID to check progress") 
):
    """Legacy alias for candidates endpoint"""
    return await get_candidates(limit=limit, task=task)

@router.get("/diagnostics")
async def get_diagnostics():
    """Legacy diagnostics endpoint"""
    health_data = await discovery_health()
    
    # Transform to expected format
    return {
        "workers": health_data["components"]["workers"],
        "pending_jobs": health_data["components"]["queue"],
        "cache_size": health_data["cache_status"]["candidate_count"],
        "redis_connected": health_data["components"]["redis"] == "connected",
        "last_update": health_data["timestamp"]
    }

@router.post("/trigger")
async def trigger_discovery(
    limit: int = Query(25, description="Number of candidates to discover")
):
    """Manually trigger a fresh discovery job"""
    return await get_candidates(limit=limit, force_refresh=True)

# Compatibility with existing health endpoint
@router.get("/health")
async def discovery_health():
    """Discovery system health check"""
    try:
        # Check Redis connection
        redis_ok = r.ping()
        
        # Check cache status
        cached = _cache_get(CACHE_KEY)
        cache_age = None
        cache_count = 0
        
        if cached:
            cache_age = time.time() - cached.get('timestamp', 0)
            cache_count = len(cached.get('candidates', []))
        
        # Check queue status
        queue_length = len(q)
        workers = rq.Worker.all(connection=r)
        active_workers = [w for w in workers if w.get_state() == 'busy']
        
        health_status = {
            "status": "healthy" if redis_ok else "degraded",
            "engine": "BMS v1.1 - Async",
            "components": {
                "redis": "connected" if redis_ok else "disconnected",
                "queue": f"{queue_length} jobs pending",
                "workers": f"{len(active_workers)}/{len(workers)} active",
                "cache": f"{cache_count} candidates" if cached else "empty"
            },
            "cache_status": {
                "exists": cached is not None,
                "age_seconds": cache_age,
                "candidate_count": cache_count,
                "ttl_seconds": CACHE_TTL
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Discovery health check error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }