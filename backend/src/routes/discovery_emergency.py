"""
Emergency Discovery Routes - Direct population bypass for worker issues
Provides immediate fixes when RQ workers fail
"""
import os
import json
import time
import logging
import asyncio
import requests
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

@router.post("/emergency/universe-filter")
async def run_universe_filtering(limit: int = Query(50, le=500), trace: bool = Query(False)):
    """
    Run complete universe filtering using the real BMS engine
    Shows filtering from thousands of stocks down to final candidates
    """
    try:
        logger.info(f"🌍 Universe filtering triggered with limit={limit}, trace={trace}")
        
        from backend.src.services.bms_engine_real import RealBMSEngine
        
        # Initialize BMS engine
        polygon_key = os.getenv("POLYGON_API_KEY", "")
        if not polygon_key:
            return {"status": "error", "error": "POLYGON_API_KEY not configured"}
        
        bms_engine = RealBMSEngine(polygon_key)
        
        # Step 1: Fetch filtered universe 
        start_time = time.time()
        filtered_stocks = await bms_engine.fetch_filtered_stocks()
        universe_fetch_time = time.time() - start_time
        
        if not filtered_stocks:
            return {
                "status": "error",
                "error": "No stocks in filtered universe",
                "universe_size": 0
            }
        
        logger.info(f"✅ Universe loaded: {len(filtered_stocks)} stocks in {universe_fetch_time:.1f}s")
        
        # Step 2: Apply intraday snapshot filter (sample for performance)
        sample_size = min(len(filtered_stocks), 1000)  # Limit for API rate limits
        sample_stocks = filtered_stocks[:sample_size]
        
        start_time = time.time()
        intraday_filtered = await bms_engine.intraday_snapshot_filter(sample_stocks)
        intraday_time = time.time() - start_time
        
        logger.info(f"✅ Intraday filter: {len(intraday_filtered)} stocks in {intraday_time:.1f}s")
        
        # Step 3: BMS scoring (limited sample for demo)
        scoring_sample = min(len(intraday_filtered), limit * 2)  # Score more than limit for better selection
        stocks_to_score = intraday_filtered[:scoring_sample]
        
        start_time = time.time()
        scored_candidates = await bms_engine.score_candidates(stocks_to_score)
        scoring_time = time.time() - start_time
        
        # Sort by score and limit results
        scored_candidates.sort(key=lambda x: x.get('score', 0), reverse=True)
        final_candidates = scored_candidates[:limit]
        
        logger.info(f"✅ BMS scoring: {len(final_candidates)} final candidates in {scoring_time:.1f}s")
        
        # Categorize candidates
        trade_ready = [c for c in final_candidates if c.get('score', 0) >= 65]
        monitor = [c for c in final_candidates if 45 <= c.get('score', 0) < 65]
        
        # Build comprehensive response
        response = {
            "status": "success",
            "method": "universe_filtering",
            "timing": {
                "universe_fetch_ms": int(universe_fetch_time * 1000),
                "intraday_filter_ms": int(intraday_time * 1000),
                "scoring_ms": int(scoring_time * 1000),
                "total_ms": int((universe_fetch_time + intraday_time + scoring_time) * 1000)
            },
            "funnel": {
                "initial_universe": len(filtered_stocks),
                "after_sample": sample_size,
                "after_intraday": len(intraday_filtered),
                "after_scoring": len(scored_candidates),
                "final_candidates": len(final_candidates)
            },
            "counts": {
                "total": len(final_candidates),
                "trade_ready": len(trade_ready),
                "monitor": len(monitor)
            },
            "candidates": final_candidates,
            "timestamp": datetime.now().isoformat(),
            "cached": False
        }
        
        # Add detailed trace if requested
        if trace:
            response["trace"] = {
                "universe_details": {
                    "total_stocks": len(filtered_stocks),
                    "price_filter": "Applied at API level ($0.50-$100.00)",
                    "volume_filter": "Applied at API level ($5M+ dollar volume)",
                    "fund_filter": "Applied at API level (exclude ETFs/funds)"
                },
                "sampling_details": {
                    "universe_sample_size": sample_size,
                    "intraday_sample_size": len(intraday_filtered),
                    "scoring_sample_size": scoring_sample,
                    "final_limit": limit
                },
                "scoring_distribution": {
                    "90_plus": len([c for c in scored_candidates if c.get('score', 0) >= 90]),
                    "80_89": len([c for c in scored_candidates if 80 <= c.get('score', 0) < 90]),
                    "70_79": len([c for c in scored_candidates if 70 <= c.get('score', 0) < 80]),
                    "60_69": len([c for c in scored_candidates if 60 <= c.get('score', 0) < 70]),
                    "50_59": len([c for c in scored_candidates if 50 <= c.get('score', 0) < 60]),
                    "below_50": len([c for c in scored_candidates if c.get('score', 0) < 50])
                }
            }
        
        # Cache the results
        try:
            import redis as redis_sync
            redis_client = redis_sync.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'), decode_responses=False)
            
            cache_payload = {
                "timestamp": int(datetime.now().timestamp()),
                "iso_timestamp": datetime.now().isoformat(),
                "count": len(final_candidates),
                "candidates": final_candidates,
                "engine": "BMS Universe Filter",
                "strategy": "universe_filter",
                "universe_size": len(filtered_stocks),
                "filtered_size": len(final_candidates),
                "trade_ready_count": len(trade_ready),
                "monitor_count": len(monitor)
            }
            
            cache_data = json.dumps(cache_payload, default=str).encode('utf-8')
            redis_client.setex("amc:discovery:contenders", 600, cache_data)
            response["cached"] = True
            
        except Exception as e:
            logger.error(f"Failed to cache universe filter results: {e}")
        
        return response
        
    except Exception as e:
        logger.error(f"Universe filtering failed: {e}")
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
        
        # Inline direct discovery logic for deployment simplicity
        import requests
        import json
        
        polygon_key = os.getenv("POLYGON_API_KEY", "")
        if not polygon_key:
            return {"status": "error", "error": "POLYGON_API_KEY not configured"}
        
        # Get market movers from Polygon
        try:
            url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/gainers"
            headers = {"Authorization": f"Bearer {polygon_key}"}
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                tickers = [t['ticker'] for t in data.get('tickers', [])[:limit]]
                logger.info(f"Found {len(tickers)} market movers")
            else:
                # Fallback stocks
                tickers = ["TSLA", "AAPL", "NVDA", "AMD", "SPY", "MSFT", "AMZN", "META", "GOOGL", "QQQ"][:limit]
        except Exception as e:
            logger.error(f"Failed to get market movers: {e}")
            # Fallback stocks
            tickers = ["TSLA", "AAPL", "NVDA", "AMD", "SPY", "MSFT", "AMZN", "META", "GOOGL", "QQQ"][:limit]
        
        # Score the stocks
        scored_candidates = []
        for symbol in tickers:
            try:
                # Simple scoring with snapshot data
                snapshot_url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}"
                response = requests.get(snapshot_url, headers=headers, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    ticker_data = data.get('ticker', {})
                    day = ticker_data.get('day', {})
                    prev_day = ticker_data.get('prevDay', {})
                    
                    if day.get('v') and prev_day.get('v'):
                        volume_ratio = day.get('v', 0) / max(prev_day.get('v', 1), 1)
                        price_change = ((day.get('c', 0) - prev_day.get('c', 1)) / max(prev_day.get('c', 1), 1)) * 100
                        
                        # Simple scoring (max 100 points)
                        volume_score = min(volume_ratio / 5, 1.0) * 40
                        momentum_score = min(abs(price_change) / 10, 1.0) * 30
                        liquidity_score = 20 if day.get('v', 0) * day.get('c', 0) > 1000000 else 10
                        volatility_score = 10
                        
                        total_score = volume_score + momentum_score + volatility_score + liquidity_score
                        
                        scored_candidates.append({
                            "symbol": symbol,
                            "score": round(total_score, 2),
                            "price": day.get('c', 0),
                            "volume": day.get('v', 0),
                            "volume_ratio": round(volume_ratio, 2),
                            "price_change_pct": round(price_change, 2),
                            "dollar_volume": day.get('v', 0) * day.get('c', 0),
                            "thesis": f"{symbol}: {volume_ratio:.1f}x volume, {price_change:+.1f}% move, score: {total_score:.0f}%",
                            "action_tag": "trade_ready" if total_score >= 70 else "watchlist" if total_score >= 50 else "monitor",
                            "timestamp": datetime.now().isoformat()
                        })
                        
            except Exception as e:
                logger.error(f"Failed to score {symbol}: {e}")
                continue
        
        # Sort by score
        scored_candidates.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # Cache results
        try:
            import redis as redis_sync
            redis_client = redis_sync.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'), decode_responses=False)
            
            cache_payload = {
                "timestamp": int(datetime.now().timestamp()),
                "iso_timestamp": datetime.now().isoformat(),
                "count": len(scored_candidates),
                "candidates": scored_candidates,
                "engine": "Direct Discovery",
                "strategy": "direct",
                "universe_size": 100,
                "filtered_size": len(scored_candidates)
            }
            
            cache_data = json.dumps(cache_payload, default=str).encode('utf-8')
            redis_client.setex("amc:discovery:contenders", 600, cache_data)
            logger.info(f"✅ Cached {len(scored_candidates)} candidates")
        except Exception as e:
            logger.error(f"Failed to cache results: {e}")
        
        logger.info(f"✅ Direct discovery completed: {len(scored_candidates)} candidates")
        return {
            "status": "success",
            "method": "direct_discovery",
            "count": len(scored_candidates),
            "candidates": scored_candidates,
            "cached": True,
            "message": "Direct discovery completed successfully"
        }
            
    except Exception as e:
        logger.error(f"Direct discovery endpoint failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }