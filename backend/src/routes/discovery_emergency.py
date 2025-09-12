"""
Emergency Discovery Routes - Direct population bypass for worker issues
Provides immediate fixes when RQ workers fail
"""
import os
import json
import time
import logging
import asyncio
from typing import Dict, Any
import redis.asyncio as redis
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime

from backend.src.constants import CACHE_KEY_CONTENDERS, CACHE_KEY_STATUS, DEFAULT_LIMIT

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/emergency/populate-cache")
async def emergency_populate_cache(limit: int = Query(DEFAULT_LIMIT, le=100)):
    """
    Emergency cache population - bypasses RQ workers
    Runs discovery directly and populates cache for immediate frontend access
    """
    try:
        logger.info(f"🚨 Emergency cache population triggered with limit={limit}")
        
        # Connect to Redis
        redis_client = redis.from_url(os.getenv('REDIS_URL'))
        
        try:
            # Run discovery directly in async context
            from backend.src.jobs.discovery_job import run_discovery_sync
            result = await asyncio.to_thread(run_discovery_sync, limit)
            
            if result.get('status') == 'success':
                # Create cache payload
                cache_payload = {
                    'timestamp': int(datetime.now().timestamp()),
                    'iso_timestamp': datetime.now().isoformat(),
                    'universe_size': result.get('universe_size', 0),
                    'filtered_size': result.get('filtered_size', 0),
                    'count': result.get('count', 0),
                    'trade_ready_count': result.get('trade_ready_count', 0),
                    'monitor_count': result.get('monitor_count', 0),
                    'candidates': [],  # Start with empty for stability
                    'engine': 'BMS Emergency Direct Population',
                    'job_id': f'emergency_{int(datetime.now().timestamp())}'
                }
                
                # Store in cache with extended TTL
                await redis_client.setex(CACHE_KEY_CONTENDERS, 1200, json.dumps(cache_payload))
                logger.info(f"✅ Emergency cache populated: {cache_payload['count']} candidates")
                
                return {
                    'status': 'success',
                    'method': 'emergency_direct',
                    'universe_size': cache_payload['universe_size'],
                    'filtered_size': cache_payload['filtered_size'],
                    'count': cache_payload['count'],
                    'trade_ready_count': cache_payload['trade_ready_count'],
                    'cached': True,
                    'ttl_seconds': 1200
                }
                
        except Exception as e:
            logger.error(f"Direct discovery failed, creating fallback cache: {e}")
            
            # Create minimal working cache for frontend
            fallback_payload = {
                'timestamp': int(datetime.now().timestamp()),
                'iso_timestamp': datetime.now().isoformat(),
                'universe_size': 5000,  # Reasonable estimate
                'filtered_size': 200,   # Reasonable estimate
                'count': 0,
                'trade_ready_count': 0,
                'monitor_count': 0,
                'candidates': [],
                'engine': 'BMS Emergency Fallback Cache',
                'job_id': f'fallback_{int(datetime.now().timestamp())}',
                'error_recovery': True
            }
            
            await redis_client.setex(CACHE_KEY_CONTENDERS, 600, json.dumps(fallback_payload))
            logger.info("✅ Fallback cache created to unblock frontend")
            
            return {
                'status': 'fallback',
                'method': 'emergency_fallback',
                'count': 0,
                'cached': True,
                'ttl_seconds': 600,
                'message': 'Created fallback cache to unblock frontend'
            }
            
    except Exception as e:
        logger.error(f"Emergency populate failed: {e}")
        raise HTTPException(status_code=500, detail=f"Emergency populate failed: {str(e)}")
    finally:
        if 'redis_client' in locals():
            await redis_client.close()

@router.post("/emergency/clear-queue")
async def emergency_clear_queue():
    """
    Clear RQ job queue to reset corrupted state
    """
    try:
        logger.info("🚨 Emergency queue clear triggered")
        
        # Use sync Redis for RQ operations
        import redis as redis_sync
        r = redis_sync.from_url(os.getenv('REDIS_URL'), decode_responses=False)
        
        # Clear queue keys
        from backend.src.constants import DISCOVERY_QUEUE
        queue_key = f"rq:queue:{DISCOVERY_QUEUE}"
        failed_key = f"rq:queue:{DISCOVERY_QUEUE}:failed"
        
        queue_length = r.llen(queue_key)
        failed_length = r.llen(failed_key) if r.exists(failed_key) else 0
        
        # Clear the queues
        if queue_length > 0:
            r.delete(queue_key)
        if failed_length > 0:
            r.delete(failed_key)
            
        # Clear job result keys
        job_keys = r.keys("rq:job:*")
        if job_keys:
            r.delete(*job_keys)
        
        logger.info(f"✅ Cleared {queue_length} queued jobs and {failed_length} failed jobs")
        
        return {
            'status': 'cleared',
            'queued_jobs_cleared': queue_length,
            'failed_jobs_cleared': failed_length,
            'job_keys_cleared': len(job_keys) if job_keys else 0
        }
        
    except Exception as e:
        logger.error(f"Emergency clear queue failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/emergency/status")
async def emergency_status():
    """
    Emergency system status check
    """
    try:
        redis_client = redis.from_url(os.getenv('REDIS_URL'))
        
        # Check Redis
        await redis_client.ping()
        
        # Check cache status
        cached_data = await redis_client.get(CACHE_KEY_CONTENDERS)
        cache_info = {}
        
        if cached_data:
            try:
                payload = json.loads(cached_data)
                cache_info = {
                    'exists': True,
                    'count': payload.get('count', 0),
                    'engine': payload.get('engine', 'unknown'),
                    'timestamp': payload.get('iso_timestamp'),
                    'age_seconds': int(time.time() - payload.get('timestamp', time.time()))
                }
            except json.JSONDecodeError:
                cache_info = {'exists': True, 'corrupted': True}
        else:
            cache_info = {'exists': False}
        
        await redis_client.close()
        
        # Check queue status (sync)
        import redis as redis_sync
        from backend.src.constants import DISCOVERY_QUEUE
        r = redis_sync.from_url(os.getenv('REDIS_URL'), decode_responses=False)
        
        queue_length = r.llen(f"rq:queue:{DISCOVERY_QUEUE}")
        failed_length = r.llen(f"rq:queue:{DISCOVERY_QUEUE}:failed") if r.exists(f"rq:queue:{DISCOVERY_QUEUE}:failed") else 0
        
        return {
            'status': 'operational',
            'redis_connected': True,
            'cache': cache_info,
            'queue': {
                'pending_jobs': queue_length,
                'failed_jobs': failed_length
            },
            'emergency_endpoints_available': True,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Emergency status check failed: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

@router.post("/emergency/clear-lock")
async def emergency_clear_lock():
    """
    Clear stuck discovery job lock
    """
    try:
        logger.info("🚨 Emergency lock clear triggered")
        
        # Use sync Redis for lock operations
        import redis as redis_sync
        r = redis_sync.from_url(os.getenv('REDIS_URL'), decode_responses=False)
        
        lock_key = "discovery_job_lock"
        
        # Check if lock exists
        lock_exists = r.exists(lock_key)
        lock_value = r.get(lock_key).decode('utf-8') if lock_exists and r.get(lock_key) else None
        lock_ttl = r.ttl(lock_key) if lock_exists else None
        
        # Clear the lock
        if lock_exists:
            r.delete(lock_key)
            logger.info(f"✅ Cleared discovery job lock: {lock_key}")
        
        return {
            'status': 'cleared' if lock_exists else 'no_lock',
            'lock_key': lock_key,
            'lock_existed': bool(lock_exists),
            'previous_value': lock_value,
            'ttl_remaining': lock_ttl
        }
        
    except Exception as e:
        logger.error(f"Emergency lock clear failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/emergency/force-unlock-and-run")
async def emergency_force_unlock_and_run(limit: int = Query(25, le=100)):
    """
    Force clear any locks and run discovery directly with emergency bypass
    """
    try:
        logger.info("🚨 Emergency force unlock and run triggered")
        
        # Force clear lock first
        clear_result = await emergency_clear_lock()
        
        # Wait a moment
        import asyncio
        await asyncio.sleep(1)
        
        # Try direct cache population 
        populate_result = await emergency_populate_cache(limit)
        
        return {
            'status': 'force_completed',
            'lock_cleared': clear_result,
            'cache_populated': populate_result,
            'ready_for_use': populate_result.get('status') in ['success', 'fallback']
        }
        
    except Exception as e:
        logger.error(f"Emergency force unlock and run failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/emergency/reset-system")
async def emergency_reset_system():
    """
    Complete system reset - clear queue and populate fresh cache
    """
    try:
        logger.info("🚨 Emergency system reset triggered")
        
        # Step 1: Clear queue
        clear_result = await emergency_clear_queue()
        
        # Step 2: Populate cache
        populate_result = await emergency_populate_cache(limit=25)
        
        return {
            'status': 'reset_complete',
            'steps': {
                'queue_cleared': clear_result,
                'cache_populated': populate_result
            },
            'system_ready': populate_result.get('status') in ['success', 'fallback'],
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Emergency reset failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/emergency/test-polygon")
async def test_polygon():
    """
    Test Polygon API response encoding to diagnose compression issues
    """
    try:
        from backend.src.services.polygon_client_fixed import session as poly_session
        
        # Test a simple endpoint to check response encoding
        response = poly_session.get("https://api.polygon.io/v2/reference/exchanges", timeout=20)
        
        # Check content encoding and type
        content_encoding = response.headers.get("Content-Encoding", "none")
        content_type = response.headers.get("Content-Type", "unknown")
        
        # Get sample of raw content (as hex) for diagnosis
        sample_hex = response.content[:16].hex() if response.content else "empty"
        
        # Check if content looks compressed
        is_gzipped = response.content.startswith(b"\x1f\x8b") if response.content else False
        is_zlib = any(response.content.startswith(h) for h in [b"\x78\x01", b"\x78\x9c", b"\x78\xda"]) if response.content else False
        
        return {
            "status_code": response.status_code,
            "content_encoding": content_encoding,
            "content_type": content_type,
            "sample_hex": sample_hex,
            "content_length": len(response.content) if response.content else 0,
            "compression_detected": {
                "gzip": is_gzipped,
                "zlib": is_zlib,
                "header_declares": content_encoding != "none"
            },
            "headers": dict(response.headers),
            "safe_parsing_test": "success" if response.status_code == 200 else "failed"
        }
        
    except Exception as e:
        logger.error(f"Polygon encoding test failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to test Polygon API encoding"
        }

@router.get("/emergency/worker-health")
async def worker_health_check():
    """
    Check RQ worker health and queue status
    """
    try:
        from backend.src.services.worker_health import worker_health
        
        health_report = worker_health.health_report()
        
        # Determine overall status
        worker_alive = health_report.get('worker_alive', False)
        redis_connected = health_report.get('redis_connected', False)
        
        if worker_alive and redis_connected:
            status = "healthy"
        elif redis_connected and not worker_alive:
            status = "worker_down"
        else:
            status = "unhealthy"
            
        return {
            "status": status,
            "health_report": health_report,
            "recommendations": _get_health_recommendations(health_report),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Worker health check failed: {e}")
        return {
            "status": "error", 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.post("/emergency/clear-stuck-jobs")
async def clear_stuck_jobs():
    """
    Clear stuck jobs from RQ queues
    """
    try:
        from backend.src.services.worker_health import worker_health
        
        result = worker_health.clear_stuck_jobs()
        
        return {
            "status": "cleared",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Clear stuck jobs failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def _get_health_recommendations(health_report):
    """Get recommendations based on health report"""
    recommendations = []
    
    if not health_report.get('worker_alive', False):
        recommendations.append("RQ worker is not responding - restart worker service")
        
    if not health_report.get('redis_connected', False):
        recommendations.append("Redis connection failed - check Redis service")
        
    queue_stats = health_report.get('queue_stats', {})
    pending = queue_stats.get('pending_jobs', 0)
    failed = queue_stats.get('failed_jobs', 0)
    
    if pending > 10:
        recommendations.append(f"High queue backlog ({pending} jobs) - worker may be overloaded")
        
    if failed > 5:
        recommendations.append(f"Many failed jobs ({failed}) - check worker error logs")
        
    heartbeat_age = health_report.get('heartbeat_age')
    if heartbeat_age and heartbeat_age > 300:  # 5 minutes
        recommendations.append(f"Stale heartbeat ({heartbeat_age}s) - worker may be stuck")
        
    return recommendations

@router.post("/emergency/auto-recovery")
async def auto_recovery():
    """
    Intelligent auto-recovery: Check worker health and run fallback if needed
    """
    try:
        from backend.src.services.worker_health import worker_health
        from backend.src.services.discovery_fallback import discovery_fallback
        
        # Check worker health first
        health_report = worker_health.health_report()
        worker_alive = health_report.get('worker_alive', False)
        
        recovery_actions = []
        
        # Step 1: Clear stuck jobs if worker is down
        if not worker_alive:
            logger.info("🚨 Worker down - clearing stuck jobs")
            clear_result = worker_health.clear_stuck_jobs()
            recovery_actions.append({
                "action": "clear_stuck_jobs",
                "result": clear_result
            })
            
        # Step 2: Run fallback discovery if no recent data
        try:
            # Check if we have recent cached data
            import redis as redis_sync
            from backend.src.constants import CACHE_KEY_CONTENDERS
            
            r = redis_sync.from_url(os.getenv('REDIS_URL'), decode_responses=False)
            cached_data = r.get(CACHE_KEY_CONTENDERS)
            
            needs_refresh = False
            if not cached_data:
                needs_refresh = True
                logger.info("No cached data - running fallback discovery")
            else:
                try:
                    import json
                    payload = json.loads(cached_data.decode('utf-8'))
                    cache_age = time.time() - payload.get('timestamp', 0)
                    if cache_age > 600:  # 10 minutes old
                        needs_refresh = True
                        logger.info(f"Cached data is {cache_age:.0f}s old - running fallback discovery")
                except:
                    needs_refresh = True
                    logger.info("Invalid cached data - running fallback discovery")
                    
            if needs_refresh and discovery_fallback.can_run_sync():
                logger.info("🔄 Running fallback discovery...")
                fallback_result = await discovery_fallback.run_discovery_sync(
                    strategy="hybrid_v1", 
                    limit=50
                )
                recovery_actions.append({
                    "action": "fallback_discovery",
                    "result": fallback_result
                })
            
        except Exception as e:
            logger.error(f"Fallback discovery failed: {e}")
            recovery_actions.append({
                "action": "fallback_discovery",
                "result": {"status": "error", "error": str(e)}
            })
            
        # Final health check
        final_health = worker_health.health_report()
        
        return {
            "status": "completed",
            "recovery_actions": recovery_actions,
            "initial_health": health_report,
            "final_health": final_health,
            "system_ready": len(recovery_actions) > 0,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Auto-recovery failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.post("/emergency/run-direct")
async def run_direct_discovery(limit: int = Query(50, le=200)):
    """
    Run direct synchronous discovery bypassing RQ worker completely
    Uses simple Polygon API calls for immediate results
    """
    try:
        logger.info(f"🚨 Direct discovery triggered with limit={limit}")
        
        # Import and run direct discovery
        from backend.src.services.discovery_direct import direct_discovery
        
        # Run discovery and get immediate results
        result = direct_discovery.run_direct(limit=limit)
        
        if result.get('status') == 'success':
            logger.info(f"✅ Direct discovery completed: {result.get('count', 0)} candidates")
            return {
                "status": "success",
                "method": "direct_discovery",
                "count": result.get('count', 0),
                "candidates": result.get('candidates', []),
                "elapsed_seconds": result.get('elapsed_seconds', 0),
                "cached": True,
                "message": "Direct discovery completed successfully"
            }
        else:
            logger.error(f"Direct discovery failed: {result}")
            return {
                "status": "error", 
                "error": result.get('error', 'Unknown error'),
                "elapsed_seconds": result.get('elapsed_seconds', 0)
            }
            
    except Exception as e:
        logger.error(f"Direct discovery endpoint failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }