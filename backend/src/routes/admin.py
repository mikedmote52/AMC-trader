"""
Admin endpoints for cache management and maintenance tasks.
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
import structlog
import asyncio

logger = structlog.get_logger()
router = APIRouter()

# Track running jobs
_running_jobs = {}


@router.post("/admin/cache/refresh")
async def trigger_cache_refresh(
    background_tasks: BackgroundTasks,
    test_mode: bool = False
):
    """
    Trigger volume cache refresh in the background.

    Args:
        test_mode: If True, only refresh 100 stocks (for testing)

    Returns:
        Job status and estimated completion time
    """
    job_id = f"cache_refresh_{int(asyncio.get_event_loop().time())}"

    if "cache_refresh" in _running_jobs:
        raise HTTPException(
            status_code=409,
            detail="Cache refresh already running. Check /admin/cache/status for progress."
        )

    # Import here to avoid circular dependency
    from src.jobs.refresh_volume_cache import refresh_volume_cache

    # Mark job as running
    _running_jobs["cache_refresh"] = {
        "job_id": job_id,
        "started_at": asyncio.get_event_loop().time(),
        "test_mode": test_mode,
        "status": "running"
    }

    # Run in background
    async def run_refresh():
        try:
            if test_mode:
                await refresh_volume_cache(max_symbols=100)
            else:
                await refresh_volume_cache()

            _running_jobs["cache_refresh"]["status"] = "completed"
            _running_jobs["cache_refresh"]["completed_at"] = asyncio.get_event_loop().time()

        except Exception as e:
            logger.error("Cache refresh failed", error=str(e))
            _running_jobs["cache_refresh"]["status"] = "failed"
            _running_jobs["cache_refresh"]["error"] = str(e)

    background_tasks.add_task(run_refresh)

    return {
        "job_id": job_id,
        "status": "started",
        "test_mode": test_mode,
        "estimated_duration_minutes": 3 if test_mode else 45,
        "check_status_url": "/admin/cache/status"
    }


@router.get("/admin/cache/status")
async def get_cache_status():
    """
    Get current cache refresh job status.
    """
    import asyncpg
    import os

    # Get cache row count
    try:
        conn = await asyncpg.connect(os.environ['DATABASE_URL'])
        total_cached = await conn.fetchval("SELECT COUNT(*) FROM volume_averages")
        await conn.close()
    except Exception as e:
        total_cached = 0
        logger.error("Failed to get cache count", error=str(e))

    if "cache_refresh" not in _running_jobs:
        return {
            "job_running": False,
            "total_cached": total_cached,
            "last_job": None
        }

    job = _running_jobs["cache_refresh"]
    elapsed = asyncio.get_event_loop().time() - job["started_at"]

    return {
        "job_running": job["status"] == "running",
        "job_id": job["job_id"],
        "status": job["status"],
        "elapsed_seconds": int(elapsed),
        "test_mode": job.get("test_mode", False),
        "total_cached": total_cached,
        "estimated_remaining_minutes": max(0, 45 - int(elapsed / 60)) if not job.get("test_mode") else max(0, 3 - int(elapsed / 60))
    }


@router.get("/admin/cache/stats")
async def get_cache_stats():
    """
    Get detailed cache statistics.
    """
    import asyncpg
    import os

    try:
        conn = await asyncpg.connect(os.environ['DATABASE_URL'])

        total = await conn.fetchval("SELECT COUNT(*) FROM volume_averages")

        # Get freshness stats
        fresh = await conn.fetchval(
            "SELECT COUNT(*) FROM volume_averages WHERE last_updated > NOW() - INTERVAL '24 hours'"
        )

        stale = await conn.fetchval(
            "SELECT COUNT(*) FROM volume_averages WHERE last_updated <= NOW() - INTERVAL '24 hours'"
        )

        # Sample data
        sample = await conn.fetch(
            "SELECT symbol, avg_volume_20d, last_updated FROM volume_averages ORDER BY last_updated DESC LIMIT 10"
        )

        await conn.close()

        return {
            "total_cached": total,
            "fresh_count": fresh,
            "stale_count": stale,
            "cache_health": "excellent" if (fresh / total > 0.9) else "good" if (fresh / total > 0.7) else "needs_refresh",
            "sample_data": [
                {
                    "symbol": row["symbol"],
                    "avg_volume_20d": row["avg_volume_20d"],
                    "last_updated": row["last_updated"].isoformat()
                }
                for row in sample
            ]
        }

    except Exception as e:
        logger.error("Failed to get cache stats", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
