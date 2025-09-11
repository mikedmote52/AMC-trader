"""
Discovery API Routes - Non-blocking with Redis caching
Implements 202 Accepted → 200 OK polling pattern for fast UI responses
"""
import os
import json
import time
import logging
from typing import Dict, Any, Optional
import redis.asyncio as redis
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from rq import Queue
from rq.job import Job

from backend.src.constants import (
    DISCOVERY_QUEUE, CACHE_KEY_CONTENDERS, CACHE_KEY_STATUS,
    DEFAULT_LIMIT, MAX_LIMIT, JOB_TIMEOUT_SECONDS, RESULT_TTL_SECONDS
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Redis connection for synchronous RQ operations
import redis as redis_sync_lib
redis_sync = redis_sync_lib.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'), decode_responses=False)

@router.get("/contenders")
@router.get("/candidates")  # Frontend expects this endpoint
async def get_contenders(limit: int = Query(DEFAULT_LIMIT, le=MAX_LIMIT)):
    """
    Get discovery candidates with non-blocking pattern:
    - If cached results exist: Return 200 with data immediately
    - If no cache: Enqueue job and return 202 with job ID for polling
    """
    try:
        # Check for cached results first
        redis_client = redis.from_url(os.getenv('REDIS_URL'))
        cached_data = await redis_client.get(CACHE_KEY_CONTENDERS)
        await redis_client.close()
        
        if cached_data:
            try:
                payload = json.loads(cached_data.decode('utf-8') if isinstance(cached_data, bytes) else cached_data)
                
                # Apply limit to cached data
                candidates = payload.get('candidates', [])[:limit]
                
                response_data = {
                    'status': 'ready',
                    'timestamp': payload.get('iso_timestamp'),
                    'universe_size': payload.get('universe_size', 0),
                    'filtered_size': payload.get('filtered_size', 0),
                    'count': len(candidates),
                    'candidates': candidates,
                    'trade_ready_count': len([c for c in candidates if c.get('action') == 'TRADE_READY']),
                    'monitor_count': len([c for c in candidates if c.get('action') == 'MONITOR']),
                    'engine': payload.get('engine', 'BMS Cached Results'),
                    'cached': True,
                    'cache_age_seconds': int(time.time() - payload.get('timestamp', time.time()))
                }
                
                logger.info(f"✅ Returning cached results: {len(candidates)} candidates")
                return response_data
                
            except json.JSONDecodeError:
                logger.warning("Cached data corrupted, triggering fresh discovery")
        
        # No valid cache - enqueue background job
        logger.info("No cached results, enqueueing discovery job...")
        
        try:
            queue = Queue(DISCOVERY_QUEUE, connection=redis_sync)
            job = queue.enqueue(
                'backend.src.jobs.discovery_job.run_discovery_job',
                max(limit, 300),  # Cache extra results for future requests
                job_timeout=JOB_TIMEOUT_SECONDS,
                result_ttl=RESULT_TTL_SECONDS,
                job_id=f"discovery_{int(time.time())}"
            )
            
            logger.info(f"📋 Enqueued discovery job: {job.id}")
            
            return JSONResponse(
                status_code=202,
                content={
                    'status': 'queued',
                    'job_id': job.id,
                    'message': 'Discovery analysis started - poll /discovery/status for progress',
                    'estimated_completion_seconds': 120,
                    'poll_url': f'/discovery/status?job_id={job.id}'
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to enqueue job: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to start discovery: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error in get_contenders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/candidates/trade-ready")  # Frontend expects this endpoint
async def get_trade_ready_candidates(limit: int = Query(DEFAULT_LIMIT, le=MAX_LIMIT)):
    """Get only TRADE_READY candidates - frontend specific endpoint"""
    # Get cached results first  
    redis_client = redis.from_url(os.getenv('REDIS_URL'))
    cached_data = await redis_client.get(CACHE_KEY_CONTENDERS)
    await redis_client.close()
    
    if cached_data:
        try:
            payload = json.loads(cached_data.decode('utf-8') if isinstance(cached_data, bytes) else cached_data)
            all_candidates = payload.get('candidates', [])
            
            # Filter for trade-ready only
            trade_ready = [c for c in all_candidates if c.get('action') == 'TRADE_READY'][:limit]
            
            return {
                'status': 'ready',
                'timestamp': payload.get('iso_timestamp'),
                'universe_size': payload.get('universe_size', 0),
                'filtered_size': payload.get('filtered_size', 0), 
                'count': len(trade_ready),
                'candidates': trade_ready,
                'trade_ready_count': len(trade_ready),
                'monitor_count': 0,
                'engine': f"{payload.get('engine', 'BMS')} - Trade Ready Filter",
                'cached': True,
                'filter': 'TRADE_READY'
            }
        except json.JSONDecodeError:
            pass
    
    # No cache - enqueue job
    try:
        queue = Queue(DISCOVERY_QUEUE, connection=redis_sync)
        job = queue.enqueue(
            'backend.src.jobs.discovery_job.run_discovery_job',
            max(limit, 100),  # Cache extra for future requests
            job_timeout=JOB_TIMEOUT_SECONDS,
            result_ttl=RESULT_TTL_SECONDS,
            job_id=f"trade_ready_{int(time.time())}"
        )
        
        return JSONResponse(
            status_code=202,
            content={
                'status': 'queued', 
                'job_id': job.id,
                'message': 'Trade-ready discovery started',
                'filter': 'TRADE_READY',
                'poll_url': f'/discovery/status?job_id={job.id}'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/contenders/last")
@router.get("/candidates/last")  # Frontend alias  
async def get_last_contenders(limit: int = Query(DEFAULT_LIMIT, le=MAX_LIMIT)):
    """
    Get last known results (even if stale) - never returns empty/error
    Used as fallback when polling times out
    """
    try:
        redis_client = redis.from_url(os.getenv('REDIS_URL'))
        cached_data = await redis_client.get(CACHE_KEY_CONTENDERS)
        await redis_client.close()
        
        if not cached_data:
            return {
                'status': 'ready',
                'timestamp': None,
                'universe_size': 0,
                'filtered_size': 0,
                'count': 0,
                'candidates': [],
                'trade_ready_count': 0,
                'monitor_count': 0,
                'engine': 'No cached results available',
                'cached': False,
                'message': 'No previous discovery results found'
            }
        
        try:
            payload = json.loads(cached_data.decode('utf-8') if isinstance(cached_data, bytes) else cached_data)
            candidates = payload.get('candidates', [])[:limit]
            
            return {
                'status': 'ready',
                'timestamp': payload.get('iso_timestamp'),
                'universe_size': payload.get('universe_size', 0),
                'filtered_size': payload.get('filtered_size', 0),
                'count': len(candidates),
                'candidates': candidates,
                'trade_ready_count': len([c for c in candidates if c.get('action') == 'TRADE_READY']),
                'monitor_count': len([c for c in candidates if c.get('action') == 'MONITOR']),
                'engine': payload.get('engine', 'BMS Last Known Results'),
                'cached': True,
                'cache_age_seconds': int(time.time() - payload.get('timestamp', time.time())),
                'stale': True
            }
            
        except json.JSONDecodeError:
            logger.warning("Cached data corrupted in last results")
            return {
                'status': 'ready',
                'count': 0,
                'candidates': [],
                'message': 'Cached data corrupted',
                'cached': False
            }
    
    except Exception as e:
        logger.error(f"Error in get_last_contenders: {e}")
        # Never fail - return empty results
        return {
            'status': 'ready',
            'count': 0,
            'candidates': [],
            'message': f'Error accessing cache: {str(e)}',
            'cached': False
        }

@router.get("/status")
async def get_discovery_status(job_id: str = Query(...)):
    """Get status of a running discovery job"""
    try:
        # Get job status from RQ
        job = Job.fetch(job_id, connection=redis_sync)
        job_status = job.get_status()
        
        # Get detailed status from Redis if available
        redis_client = redis.from_url(os.getenv('REDIS_URL'))
        status_data = await redis_client.get(CACHE_KEY_STATUS)
        await redis_client.close()
        
        detailed_status = {}
        if status_data:
            try:
                detailed_status = json.loads(status_data.decode('utf-8') if isinstance(status_data, bytes) else status_data)
            except json.JSONDecodeError:
                pass
        
        response = {
            'job_id': job_id,
            'status': job_status,
            'rq_status': job_status,
            'progress': detailed_status.get('progress', 0),
            'message': detailed_status.get('message', ''),
            'stats': detailed_status.get('stats', {}),
            'elapsed_seconds': detailed_status.get('elapsed_seconds', 0)
        }
        
        # Add result if job is finished
        if job_status == 'finished' and job.result:
            response['result'] = job.result
        elif job_status == 'failed':
            response['error'] = job.exc_info
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting job status for {job_id}: {e}")
        return {
            'job_id': job_id,
            'status': 'unknown',
            'error': str(e)
        }

@router.post("/trigger")
async def trigger_discovery(limit: int = Query(DEFAULT_LIMIT, le=MAX_LIMIT)):
    """
    Manually trigger discovery scan
    Always enqueues a new job regardless of cache state
    """
    try:
        logger.info(f"🔥 Manual discovery trigger with limit={limit}")
        
        queue = Queue(DISCOVERY_QUEUE, connection=redis_sync)
        job = queue.enqueue(
            'backend.src.jobs.discovery_job.run_discovery_job',
            limit,
            job_timeout=JOB_TIMEOUT_SECONDS,
            result_ttl=RESULT_TTL_SECONDS,
            job_id=f"manual_{int(time.time())}"
        )
        
        return {
            'status': 'triggered',
            'job_id': job.id,
            'message': f'Manual discovery started for {limit} candidates',
            'poll_url': f'/discovery/status?job_id={job.id}'
        }
        
    except Exception as e:
        logger.error(f"Error triggering discovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def discovery_health():
    """Discovery system health check"""
    try:
        redis_client = redis.from_url(os.getenv('REDIS_URL'))
        
        # Check Redis connectivity
        await redis_client.ping()
        
        # Check cache status
        cached_data = await redis_client.get(CACHE_KEY_CONTENDERS)
        status_data = await redis_client.get(CACHE_KEY_STATUS)
        
        await redis_client.close()
        
        cache_info = {}
        if cached_data:
            try:
                payload = json.loads(cached_data.decode('utf-8') if isinstance(cached_data, bytes) else cached_data)
                cache_info = {
                    'cached_results': True,
                    'cache_timestamp': payload.get('iso_timestamp'),
                    'cache_count': payload.get('count', 0),
                    'cache_age_seconds': int(time.time() - payload.get('timestamp', time.time()))
                }
            except:
                cache_info = {'cached_results': False, 'cache_corrupted': True}
        else:
            cache_info = {'cached_results': False}
        
        status_info = {}
        if status_data:
            try:
                status = json.loads(status_data.decode('utf-8') if isinstance(status_data, bytes) else status_data)
                status_info = {
                    'last_job_status': status.get('status'),
                    'last_job_timestamp': status.get('timestamp')
                }
            except:
                status_info = {'status_corrupted': True}
        
        # Check queue status
        try:
            queue = Queue(DISCOVERY_QUEUE, connection=redis_sync)
            queue_info = {
                'queue_length': len(queue),
                'failed_jobs': len(queue.failed_job_registry)
            }
        except Exception as e:
            queue_info = {'error': str(e)}
        
        return {
            'status': 'healthy',
            'engine': 'Discovery Cached API v2.0',
            'redis_connected': True,
            'cache': cache_info,
            'job_status': status_info,
            'queue': queue_info,
            'timestamp': time.time()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time()
        }

@router.get("/cache/peek")
async def peek_cache():
    """Debug endpoint to inspect cache contents"""
    try:
        redis_client = redis.from_url(os.getenv('REDIS_URL'))
        cached_data = await redis_client.get(CACHE_KEY_CONTENDERS)
        await redis_client.close()
        
        if not cached_data:
            return {'exists': False, 'size_bytes': 0}
        
        try:
            payload = json.loads(cached_data.decode('utf-8') if isinstance(cached_data, bytes) else cached_data)
            return {
                'exists': True,
                'size_bytes': len(cached_data),
                'timestamp': payload.get('iso_timestamp'),
                'count': payload.get('count', 0),
                'universe_size': payload.get('universe_size', 0),
                'trade_ready_count': payload.get('trade_ready_count', 0),
                'job_id': payload.get('job_id'),
                'engine': payload.get('engine')
            }
        except json.JSONDecodeError:
            return {
                'exists': True,
                'size_bytes': len(cached_data),
                'corrupted': True
            }
            
    except Exception as e:
        return {
            'error': str(e),
            'exists': False
        }

@router.post("/cache/populate") 
async def populate_cache_emergency():
    """Emergency endpoint - provides minimal mock data until worker starts"""
    try:
        logger.info("🚨 Emergency cache population - providing demo data")
        
        # Create minimal mock payload to satisfy frontend
        mock_payload = {
            'timestamp': int(time.time()),
            'iso_timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'universe_size': 5247,
            'filtered_size': 892,
            'processed': 50,
            'count': 12,
            'trade_ready_count': 5,
            'monitor_count': 7,
            'candidates': [
                {
                    'symbol': 'DEMO',
                    'price': 15.45,
                    'change_pct': 2.34,
                    'volume_mil': 8.2,
                    'rel_vol': 3.4,
                    'bms_score': 78.5,
                    'action': 'TRADE_READY',
                    'tier': 'Tier 1',
                    'thesis': 'Demo candidate while system initializes'
                }
            ],
            'stats': {'demo': True},
            'job_id': 'emergency_demo',
            'engine': 'Emergency Demo Data - Worker Starting Up',
            'elapsed_seconds': 1
        }
        
        # Cache the demo data
        redis_client = redis.from_url(os.getenv('REDIS_URL'))
        await redis_client.setex(
            CACHE_KEY_CONTENDERS,
            300,  # 5 minute TTL
            json.dumps(mock_payload)
        )
        await redis_client.close()
        
        logger.info("✅ Emergency demo data cached")
        
        return {
            'status': 'success',
            'message': 'Emergency demo data cached - worker will replace with real data',
            'demo': True
        }
        
    except Exception as e:
        logger.error(f"Emergency cache population failed: {e}")
        return {
            'status': 'failed',
            'error': str(e)
        }

@router.get("/squeeze-candidates")
async def get_squeeze_candidates(
    min_score: float = Query(0.25, ge=0.0, le=100.0), 
    limit: int = Query(DEFAULT_LIMIT, le=MAX_LIMIT),
    strategy: str = Query("", description="Scoring strategy: legacy_v0, hybrid_v1")
):
    """Squeeze candidates from cached discovery results - FIXED to use correct Redis keys"""
    try:
        # Get cached results from CORRECT Redis keys
        redis_client = redis.from_url(os.getenv('REDIS_URL'))
        
        # Strategy-aware key lookup (matching discovery.py pattern)
        strategy_suffix = f":{strategy}" if strategy and strategy in ["legacy_v0", "hybrid_v1"] else ""
        
        redis_keys_to_try = [
            f"amc:discovery:v2:contenders.latest{strategy_suffix}",  # V2 key with strategy
            f"amc:discovery:contenders.latest{strategy_suffix}",     # V1 key with strategy
            "amc:discovery:v2:contenders.latest",                    # V2 fallback (no strategy)
            "amc:discovery:contenders.latest",                       # V1 fallback (no strategy)
            CACHE_KEY_CONTENDERS                                     # Original cached key (might still work)
        ]
        
        cached_data = None
        found_key = None
        
        for key in redis_keys_to_try:
            test_data = await redis_client.get(key)
            if test_data:
                cached_data = test_data
                found_key = key
                break
        
        await redis_client.close()
        
        if cached_data:
            try:
                # Handle different data formats
                if found_key == CACHE_KEY_CONTENDERS:
                    # Original cached format
                    payload = json.loads(cached_data.decode('utf-8') if isinstance(cached_data, bytes) else cached_data)
                    all_candidates = payload.get('candidates', [])
                else:
                    # Discovery.py format - direct array
                    all_candidates = json.loads(cached_data.decode('utf-8') if isinstance(cached_data, bytes) else cached_data)
                    if not isinstance(all_candidates, list):
                        all_candidates = []
                
                # Helper function to normalize min_score input
                def normalize_min_score(score):
                    if score is None:
                        return 0
                    # Handle both 0-1 and 0-100 scale inputs
                    return score * 100 if score <= 1 else score
                
                # Helper function to extract candidate score (handle different formats)
                def get_candidate_score(candidate):
                    # Try different score field names and normalize to 0-100 scale
                    score = candidate.get('score') or candidate.get('meta_score') or candidate.get('bms_score', 0)
                    # Normalize to 0-100 if needed
                    return score * 100 if score <= 1 else score
                
                min_score_pct = normalize_min_score(min_score)
                
                # Filter for squeeze candidates with score above threshold
                squeeze_candidates = []
                for candidate in all_candidates:
                    candidate_score = get_candidate_score(candidate)
                    
                    if candidate_score >= min_score_pct:
                        # Normalize candidate for response 
                        normalized_candidate = dict(candidate)  # Copy original data
                        
                        # Ensure consistent score format (0-100)
                        normalized_candidate['score'] = candidate_score
                        normalized_candidate['squeeze_score'] = candidate_score / 100.0  # 0-1 for squeeze_score
                        normalized_candidate['squeeze_tier'] = (
                            'High' if candidate_score >= 70 else 
                            'Medium' if candidate_score >= 50 else 
                            'Low'
                        )
                        squeeze_candidates.append(normalized_candidate)
                
                # Sort by score descending and limit results
                squeeze_candidates.sort(key=lambda x: x.get('score', 0), reverse=True)
                squeeze_candidates = squeeze_candidates[:limit]
                
                return {
                    'status': 'ready',
                    'timestamp': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    'count': len(squeeze_candidates),
                    'candidates': squeeze_candidates,  # Frontend expects 'candidates' 
                    'strategy': strategy if strategy else 'default',
                    'min_score': min_score,
                    'min_score_pct': min_score_pct,
                    'found_key': found_key,  # Debug info
                    'engine': 'Discovery Redis - Squeeze Filter (FIXED)',
                    'cached': True
                }
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for key {found_key}: {e}")
        
        # No cache - return empty results with guidance
        return {
            'status': 'ready',
            'timestamp': None,
            'count': 0,
            'candidates': [],  # Frontend expects 'candidates'
            'strategy': strategy if strategy else 'default',
            'min_score': min_score,
            'message': 'No discovery results found in Redis - trigger discovery first',
            'keys_tried': redis_keys_to_try,
            'cached': False
        }
        
    except Exception as e:
        logger.error(f"Error in get_squeeze_candidates: {e}")
        raise HTTPException(status_code=500, detail=str(e))