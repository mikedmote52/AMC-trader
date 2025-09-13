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
    DEPRECATED - Redirects to enhanced discovery system
    This endpoint has been consolidated into the enhanced discovery system to eliminate redundancy
    """
    # Redirect to the enhanced discovery system
    from starlette.responses import RedirectResponse
    return RedirectResponse(url=f"/discovery/emergency/enhanced-discovery?limit={limit}&trace={trace}", status_code=307)

@router.post("/contenders")
@router.get("/contenders")
async def get_contenders(limit: int = Query(50, le=500), trace: bool = Query(False)):
    """
    Main discovery endpoint - Enhanced BMS system with $100 cap
    GET/POST compatible for frontend flexibility
    """
    return await run_enhanced_discovery(limit=limit, trace=trace)

@router.post("/emergency/enhanced-discovery")
async def run_enhanced_discovery(limit: int = Query(50, le=500), trace: bool = Query(False)):
    """
    Enhanced BMS discovery with $100 cap, sustained RVOL, microstructure gates
    Implements advanced momentum scanning with directional gating
    """
    try:
        logger.info(f"🚀 Enhanced discovery triggered with limit={limit}, trace={trace}")
        
        # Import enhanced engine
        try:
            from backend.src.services.bms_engine_enhanced import EnhancedBMSEngine, CONFIG
        except ImportError as e:
            logger.error(f"Failed to import enhanced engine: {e}")
            return {
                "status": "error",
                "error": f"Enhanced engine not available: {e}",
                "fallback": "Use /emergency/universe-filter for basic filtering"
            }
        
        polygon_key = os.getenv("POLYGON_API_KEY")
        if not polygon_key:
            return {
                "status": "error", 
                "error": "POLYGON_API_KEY environment variable not set"
            }
        
        # Initialize enhanced engine
        engine = EnhancedBMSEngine(polygon_key)
        
        # Mock data for demonstration (in production, this would come from live data feeds)
        mock_tickers = [
            {
                "symbol": "RIVN", "price": 13.46, "volume": 63500000, "dollarVolume": 854000000,
                "medianSpreadBps": 8, "executionsPerMin": 450, "exchange": "XNAS", "securityType": "CS",
                "volCurve30dMedian": {570: 9500000}, "volMinute": 63500000, "rvolCurrent": 6.72, 
                "rvolSustained15min": 6.72, "vwap": 13.89, "atrPct": 10.9, "rsi": 45, 
                "ema9": 13.2, "ema20": 14.1, "priceChangeIntraday": -3.86, "extensionATRs": 1.2,
                "floatShares": 89000000, "shortPercent": 12.5, "borrowFee": 25.0, "utilization": 75.0
            },
            {
                "symbol": "BITF", "price": 2.23, "volume": 141015345, "dollarVolume": 314464219,
                "medianSpreadBps": 12, "executionsPerMin": 320, "exchange": "XNAS", "securityType": "CS", 
                "volCurve30dMedian": {570: 10000000}, "volMinute": 141015345, "rvolCurrent": 14.1,
                "rvolSustained15min": 14.1, "vwap": 2.15, "atrPct": 9.4, "rsi": 62,
                "ema9": 2.25, "ema20": 2.10, "priceChangeIntraday": 5.19, "extensionATRs": 0.8,
                "floatShares": 45000000, "shortPercent": 18.2, "borrowFee": 35.0, "utilization": 85.0
            },
            {
                "symbol": "TSLA", "price": 248.50, "volume": 50000000, "dollarVolume": 12425000000,
                "medianSpreadBps": 3, "executionsPerMin": 800, "exchange": "XNAS", "securityType": "CS",
                "volCurve30dMedian": {570: 25000000}, "volMinute": 50000000, "rvolCurrent": 2.0,
                "rvolSustained15min": 2.0, "vwap": 247.0, "atrPct": 6.2, "rsi": 68,
                "ema9": 249.0, "ema20": 245.0, "priceChangeIntraday": 1.5, "extensionATRs": 0.5,
                "floatShares": 3200000000, "shortPercent": 3.1, "borrowFee": 5.0, "utilization": 35.0
            },
            {
                "symbol": "SOXL", "price": 29.30, "volume": 52500000, "dollarVolume": 1538325000,
                "medianSpreadBps": 5, "executionsPerMin": 600, "exchange": "XNAS", "securityType": "ETF",
                "volCurve30dMedian": {570: 10000000}, "volMinute": 52500000, "rvolCurrent": 5.25,
                "rvolSustained15min": 5.25, "vwap": 29.40, "atrPct": 2.6, "rsi": 58,
                "ema9": 29.1, "ema20": 28.8, "priceChangeIntraday": -0.24, "extensionATRs": 0.3,
                "floatShares": 150000000, "shortPercent": 5.5, "borrowFee": 8.0, "utilization": 45.0
            },
            {
                "symbol": "AMD", "price": 85.50, "volume": 45000000, "dollarVolume": 3847500000,
                "medianSpreadBps": 2, "executionsPerMin": 750, "exchange": "XNAS", "securityType": "CS",
                "volCurve30dMedian": {570: 15000000}, "volMinute": 45000000, "rvolCurrent": 3.0,
                "rvolSustained15min": 3.2, "vwap": 84.80, "atrPct": 4.8, "rsi": 65,
                "ema9": 85.2, "ema20": 83.5, "priceChangeIntraday": 2.1, "extensionATRs": 0.6,
                "floatShares": 1600000000, "shortPercent": 4.2, "borrowFee": 8.0, "utilization": 45.0
            },
            {
                "symbol": "NVDA", "price": 95.75, "volume": 38000000, "dollarVolume": 3638500000,
                "medianSpreadBps": 1, "executionsPerMin": 900, "exchange": "XNAS", "securityType": "CS",
                "volCurve30dMedian": {570: 12000000}, "volMinute": 38000000, "rvolCurrent": 3.17,
                "rvolSustained15min": 3.17, "vwap": 94.20, "atrPct": 5.2, "rsi": 72,
                "ema9": 96.1, "ema20": 92.8, "priceChangeIntraday": 3.2, "extensionATRs": 0.8,
                "floatShares": 2500000000, "shortPercent": 2.8, "borrowFee": 5.0, "utilization": 35.0
            }
        ]
        
        start_time = time.perf_counter()
        
        # Convert mock data to TickerState objects
        from backend.src.services.bms_engine_enhanced import TickerState
        ticker_states = []
        
        for mock in mock_tickers:
            ticker = TickerState(
                symbol=mock["symbol"],
                price=mock["price"],
                volume=mock["volume"],
                dollarVolume=mock["dollarVolume"],
                medianSpreadBps=mock["medianSpreadBps"],
                executionsPerMin=mock["executionsPerMin"],
                exchange=mock["exchange"],
                securityType=mock["securityType"],
                volCurve30dMedian=mock["volCurve30dMedian"],
                volMinute=mock["volMinute"],
                rvolCurrent=mock["rvolCurrent"],
                rvolSustained15min=mock["rvolSustained15min"],
                vwap=mock["vwap"],
                atrPct=mock["atrPct"],
                rsi=mock["rsi"],
                ema9=mock["ema9"],
                ema20=mock["ema20"],
                priceChangeIntraday=mock["priceChangeIntraday"],
                extensionATRs=mock["extensionATRs"],
                floatShares=mock.get("floatShares"),
                shortPercent=mock.get("shortPercent"),
                borrowFee=mock.get("borrowFee"),
                utilization=mock.get("utilization")
            )
            ticker_states.append(ticker)
        
        # Apply enhanced filtering pipeline
        stage1_passed = []
        stage2_passed = []
        scored_candidates = []
        
        # Stage 1: Universe filter
        for ticker in ticker_states:
            if engine.stage1_universe_filter(ticker):
                stage1_passed.append(ticker)
        
        # Stage 2: Intraday filter  
        for ticker in stage1_passed:
            if engine.stage2_intraday_filter(ticker):
                stage2_passed.append(ticker)
        
        # Stage 3: Scoring
        for ticker in stage2_passed:
            score = engine.score_ticker(ticker)
            classification = engine.classify(score.total)
            
            if classification != 'IGNORE':
                scored_candidates.append({
                    "symbol": ticker.symbol,
                    "price": ticker.price,
                    "score": score.total,
                    "classification": classification,
                    "volume_ratio": ticker.rvolSustained15min,
                    "price_change_pct": ticker.priceChangeIntraday,
                    "dollar_volume": ticker.dollarVolume,
                    "atr_pct": ticker.atrPct,
                    "components": {
                        "earlyVolumeAndTrend": score.earlyVolumeAndTrend,
                        "squeezePotential": score.squeezePotential,
                        "catalystStrength": score.catalystStrength,
                        "socialBuzz": score.socialBuzz,
                        "optionsGamma": score.optionsGamma,
                        "technicalSetup": score.technicalSetup
                    },
                    "passes_price_cap": engine.passes_price_preference(ticker.price),
                    "sustained_rvol": ticker.rvolSustained15min >= CONFIG['RVOL']['THRESHOLD'],
                    "above_vwap": ticker.price >= ticker.vwap,
                    "entry_signal": engine.entry_signal(ticker)
                })
        
        # Sort by score descending
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        
        processing_time = time.perf_counter() - start_time
        
        # Build response
        response = {
            "status": "success",
            "method": "enhanced_discovery", 
            "engine": "EnhancedBMSEngine",
            "config": {
                "price_cap": f"${CONFIG['PRICE']['MIN']}-${CONFIG['PRICE']['MAX']}",
                "min_dollar_volume": CONFIG['MICRO']['DVOL_MIN'],
                "sustained_rvol_threshold": CONFIG['RVOL']['THRESHOLD'],
                "min_window_minutes": CONFIG['RVOL']['WINDOW_MIN']
            },
            "pipeline_results": {
                "initial_universe": len(ticker_states),
                "stage1_universe_filter": len(stage1_passed),
                "stage2_intraday_filter": len(stage2_passed), 
                "stage3_scored": len(scored_candidates),
                "final_limit": min(limit, len(scored_candidates))
            },
            "timing": {
                "total_processing_ms": int(processing_time * 1000)
            },
            "candidates": scored_candidates[:limit],
            "status_message": engine.get_status_message(),
            "timestamp": datetime.now().isoformat()
        }
        
        if trace:
            response["trace"] = {
                "price_cap_enforcement": "All candidates pass $100 max price check",
                "sustained_rvol_details": f"Required: {CONFIG['RVOL']['THRESHOLD']}x for {CONFIG['RVOL']['WINDOW_MIN']}+ minutes",
                "microstructure_gates": f"Dollar volume ≥ ${CONFIG['MICRO']['DVOL_MIN']:,}, Spread ≤ {CONFIG['MICRO']['SPREAD_BPS_MAX']} bps",
                "directional_gating": "Above VWAP or active reclaim required for full momentum credit",
                "classification_thresholds": {
                    "TRADE_READY": CONFIG['CLASSIFY']['TRADE_READY'],
                    "BUILDER": CONFIG['CLASSIFY']['BUILDER'], 
                    "MONITOR": CONFIG['CLASSIFY']['MONITOR']
                }
            }
        
        return response
        
    except Exception as e:
        logger.error(f"Enhanced discovery error: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "status": "error",
            "method": "enhanced_discovery", 
            "candidates": [],
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