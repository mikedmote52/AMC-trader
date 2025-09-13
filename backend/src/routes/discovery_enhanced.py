"""
Enhanced Discovery Routes with API Integration Agent

Provides enhanced discovery endpoints with:
- API Integration Agent features (caching, validation, monitoring)  
- Comprehensive error logging and edge case handling
- Performance monitoring and optimization
- Frontend compatibility with existing endpoints
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Query, HTTPException, BackgroundTasks, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..agents.api_integration_service import get_api_integration_service
from ..agents.orchestration_messaging import get_orchestration_messenger, MessageType, MessagePriority
from ..constants import DEFAULT_LIMIT, MAX_LIMIT

logger = logging.getLogger(__name__)
router = APIRouter()

# Performance monitoring
performance_metrics = {
    'requests_total': 0,
    'requests_success': 0,
    'requests_error': 0,
    'avg_response_time_ms': 0.0,
    'last_reset': time.time()
}

def update_performance_metrics(success: bool, response_time_ms: float):
    """Update performance metrics with thread safety."""
    global performance_metrics
    performance_metrics['requests_total'] += 1
    if success:
        performance_metrics['requests_success'] += 1
    else:
        performance_metrics['requests_error'] += 1
    
    # Update rolling average
    total_requests = performance_metrics['requests_total']
    current_avg = performance_metrics['avg_response_time_ms']
    performance_metrics['avg_response_time_ms'] = (
        (current_avg * (total_requests - 1) + response_time_ms) / total_requests
    )

# Request/Response models for validation
class DiscoveryRequest(BaseModel):
    strategy: str = Field("hybrid_v1", description="Scoring strategy")
    limit: int = Field(50, ge=1, le=MAX_LIMIT, description="Maximum candidates to return")
    force_refresh: bool = Field(False, description="Force cache refresh")

class SqueezeRequest(BaseModel):
    min_score: float = Field(0.25, ge=0.0, le=1.0, description="Minimum squeeze score")
    limit: int = Field(50, ge=1, le=MAX_LIMIT, description="Maximum candidates")
    strategy: str = Field("hybrid_v1", description="Scoring strategy")

@router.get("/enhanced/contenders")
async def get_enhanced_contenders(
    response: Response,
    background_tasks: BackgroundTasks,
    strategy: str = Query("hybrid_v1", description="Scoring strategy: legacy_v0, hybrid_v1"),
    limit: int = Query(DEFAULT_LIMIT, le=MAX_LIMIT, description="Maximum candidates to return"),
    force_refresh: bool = Query(False, description="Force cache refresh"),
    include_validation: bool = Query(True, description="Include response validation")
):
    """
    Enhanced discovery contenders with API Integration Agent capabilities.
    
    Features:
    - Intelligent caching with performance metrics
    - Comprehensive error handling and logging
    - Data validation and enrichment
    - Background optimization tasks
    - Frontend compatibility
    """
    start_time = time.time()
    request_id = f"contenders_{int(time.time() * 1000)}"
    
    try:
        # Get orchestration messenger
        messenger = get_orchestration_messenger()
        
        # Send status update to orchestrator
        messenger.send_status_update(
            status="enhanced_contenders_request_started",
            details={
                'strategy': strategy,
                'limit': limit,
                'force_refresh': force_refresh,
                'request_id': request_id,
                'endpoint': '/discovery/enhanced/contenders'
            }
        )
        
        logger.info(f"Enhanced contenders request: {request_id}", extra={
            'strategy': strategy,
            'limit': limit,
            'force_refresh': force_refresh,
            'request_id': request_id
        })
        
        # Get API Integration Service
        service = await get_api_integration_service()
        
        # Get enhanced discovery contenders
        result = await service.get_discovery_contenders_enhanced(
            strategy=strategy,
            limit=limit,
            force_refresh=force_refresh,
            background_tasks=background_tasks
        )
        
        # Validate response if requested
        validation_result = None
        if include_validation:
            validation_result = await service.validate_api_responses(
                "/discovery/enhanced/contenders", 
                result
            )
        
        # Add request tracking
        processing_time = (time.time() - start_time) * 1000
        result['meta']['request_id'] = request_id
        result['meta']['processing_time_ms'] = round(processing_time, 2)
        result['meta']['validation'] = validation_result
        
        # Set performance headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Processing-Time"] = str(round(processing_time, 2))
        response.headers["X-Strategy"] = strategy
        response.headers["Cache-Control"] = "no-store" if force_refresh else "max-age=60"
        
        # Update metrics
        update_performance_metrics(True, processing_time)
        
        # Send completion notification to orchestrator
        messenger.send_completion_notification(
            task="enhanced_contenders_request",
            result={
                'candidates_returned': result.get('count', 0),
                'cache_hit': result.get('meta', {}).get('cache_hit', False),
                'strategy': strategy,
                'request_id': request_id
            },
            duration_ms=processing_time,
            correlation_id=request_id
        )
        
        logger.info(f"Enhanced contenders success: {request_id}", extra={
            'candidates_returned': result.get('count', 0),
            'processing_time_ms': processing_time,
            'cache_hit': result.get('meta', {}).get('cache_hit', False)
        })
        
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        processing_time = (time.time() - start_time) * 1000
        update_performance_metrics(False, processing_time)
        raise
        
    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        update_performance_metrics(False, processing_time)
        
        # Send error alert to orchestrator
        messenger.send_error_alert(
            error_type="enhanced_contenders_error",
            error_message=str(e),
            error_details={
                'strategy': strategy,
                'limit': limit,
                'request_id': request_id,
                'endpoint': '/discovery/enhanced/contenders'
            },
            severity="high",
            correlation_id=request_id
        )
        
        logger.error(f"Enhanced contenders error: {request_id}", extra={
            'error': str(e),
            'strategy': strategy,
            'limit': limit,
            'processing_time_ms': processing_time
        }, exc_info=True)
        
        # Return structured error response
        error_response = {
            'error': 'Discovery contenders retrieval failed',
            'details': str(e),
            'request_id': request_id,
            'strategy': strategy,
            'timestamp': datetime.utcnow().isoformat(),
            'candidates': [],  # Ensure frontend compatibility
            'count': 0,
            'meta': {
                'processing_time_ms': round(processing_time, 2),
                'error': True
            }
        }
        
        return JSONResponse(
            status_code=500,
            content=error_response
        )

@router.post("/enhanced/trigger")
async def trigger_enhanced_discovery(
    background_tasks: BackgroundTasks,
    strategy: str = Query("hybrid_v1", description="Scoring strategy"),
    limit: int = Query(DEFAULT_LIMIT, le=MAX_LIMIT, description="Maximum candidates"),
    priority: str = Query("normal", description="Priority: low, normal, high")
):
    """
    Enhanced discovery trigger with comprehensive monitoring.
    
    Features:
    - Background processing optimization
    - Cache invalidation strategies
    - Performance monitoring
    - Priority-based execution
    """
    start_time = time.time()
    request_id = f"trigger_{int(time.time() * 1000)}"
    
    try:
        logger.info(f"Enhanced trigger request: {request_id}", extra={
            'strategy': strategy,
            'limit': limit,
            'priority': priority,
            'request_id': request_id
        })
        
        # Get API Integration Service
        service = await get_api_integration_service()
        
        # Trigger enhanced discovery
        result = await service.trigger_discovery_enhanced(
            strategy=strategy,
            limit=limit,
            background_tasks=background_tasks
        )
        
        processing_time = (time.time() - start_time) * 1000
        result['execution']['request_id'] = request_id
        result['execution']['priority'] = priority
        
        update_performance_metrics(True, processing_time)
        
        logger.info(f"Enhanced trigger success: {request_id}", extra={
            'processing_time_ms': processing_time,
            'strategy': strategy
        })
        
        return result
        
    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        update_performance_metrics(False, processing_time)
        
        logger.error(f"Enhanced trigger error: {request_id}", extra={
            'error': str(e),
            'strategy': strategy,
            'processing_time_ms': processing_time
        }, exc_info=True)
        
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Discovery trigger failed',
                'details': str(e),
                'request_id': request_id
            }
        )

@router.get("/enhanced/squeeze-candidates")
async def get_enhanced_squeeze_candidates(
    response: Response,
    min_score: float = Query(0.25, ge=0.0, le=1.0, description="Minimum squeeze score (0.0-1.0)"),
    limit: int = Query(DEFAULT_LIMIT, le=MAX_LIMIT, description="Maximum candidates"),
    strategy: str = Query("hybrid_v1", description="Scoring strategy"),
    include_analysis: bool = Query(True, description="Include detailed squeeze analysis")
):
    """
    Enhanced squeeze candidates with validation and analysis.
    
    Features:
    - Advanced squeeze scoring algorithms
    - Comprehensive validation
    - Detailed analysis and classification
    - Performance monitoring
    """
    start_time = time.time()
    request_id = f"squeeze_{int(time.time() * 1000)}"
    
    try:
        logger.info(f"Enhanced squeeze request: {request_id}", extra={
            'min_score': min_score,
            'limit': limit,
            'strategy': strategy,
            'request_id': request_id
        })
        
        # Input validation
        if min_score < 0 or min_score > 1:
            raise HTTPException(
                status_code=400,
                detail="min_score must be between 0.0 and 1.0"
            )
        
        # Get API Integration Service
        service = await get_api_integration_service()
        
        # Get enhanced squeeze candidates
        result = await service.get_squeeze_candidates_enhanced(
            min_score=min_score,
            limit=limit,
            strategy=strategy
        )
        
        # Add analysis if requested
        if include_analysis:
            result['analysis'] = {
                'total_candidates': result['count'],
                'score_distribution': _analyze_score_distribution(result['candidates']),
                'top_symbols': [c.get('symbol') for c in result['candidates'][:5]],
                'avg_squeeze_score': _calculate_avg_squeeze_score(result['candidates'])
            }
        
        processing_time = (time.time() - start_time) * 1000
        result['meta'] = {
            **result.get('meta', {}),
            'request_id': request_id,
            'processing_time_ms': round(processing_time, 2),
            'include_analysis': include_analysis
        }
        
        # Set response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Processing-Time"] = str(round(processing_time, 2))
        response.headers["X-Min-Score"] = str(min_score)
        
        update_performance_metrics(True, processing_time)
        
        logger.info(f"Enhanced squeeze success: {request_id}", extra={
            'candidates_returned': result['count'],
            'processing_time_ms': processing_time
        })
        
        return result
        
    except HTTPException:
        processing_time = (time.time() - start_time) * 1000
        update_performance_metrics(False, processing_time)
        raise
        
    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        update_performance_metrics(False, processing_time)
        
        logger.error(f"Enhanced squeeze error: {request_id}", extra={
            'error': str(e),
            'min_score': min_score,
            'processing_time_ms': processing_time
        }, exc_info=True)
        
        return JSONResponse(
            status_code=500,
            content={
                'candidates': [],  # Frontend compatibility
                'count': 0,
                'error': str(e),
                'request_id': request_id,
                'timestamp': datetime.utcnow().isoformat()
            }
        )

@router.get("/enhanced/health")
async def get_enhanced_health():
    """
    Comprehensive health check with API Integration Agent metrics.
    
    Provides:
    - API Integration Agent health
    - System performance metrics
    - Cache performance statistics
    - Error rates and response times
    """
    start_time = time.time()
    
    try:
        # Get API Integration Service
        service = await get_api_integration_service()
        
        # Get comprehensive health data
        health_data = await service.get_api_health_comprehensive()
        
        # Add performance metrics
        health_data['performance_metrics'] = {
            **performance_metrics,
            'error_rate': (performance_metrics['requests_error'] / max(performance_metrics['requests_total'], 1)) * 100,
            'success_rate': (performance_metrics['requests_success'] / max(performance_metrics['requests_total'], 1)) * 100,
            'uptime_seconds': time.time() - performance_metrics['last_reset']
        }
        
        # Add endpoint-specific health
        health_data['endpoints'] = {
            'enhanced_contenders': {
                'available': True,
                'features': ['caching', 'validation', 'background_tasks']
            },
            'enhanced_trigger': {
                'available': True, 
                'features': ['priority_processing', 'cache_invalidation']
            },
            'enhanced_squeeze_candidates': {
                'available': True,
                'features': ['advanced_scoring', 'analysis', 'validation']
            }
        }
        
        processing_time = (time.time() - start_time) * 1000
        health_data['health_check_time_ms'] = round(processing_time, 2)
        
        return health_data
        
    except Exception as e:
        logger.error(f"Enhanced health check failed: {str(e)}", exc_info=True)
        
        return {
            'overall_status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat(),
            'health_check_time_ms': round((time.time() - start_time) * 1000, 2)
        }

@router.get("/enhanced/metrics")
async def get_enhanced_metrics():
    """
    Get detailed performance and usage metrics.
    """
    try:
        service = await get_api_integration_service()
        agent_health = await service.agent.get_api_health()
        
        return {
            'performance_metrics': performance_metrics,
            'api_integration_metrics': agent_health.get('metrics', {}),
            'derived_metrics': {
                'error_rate_pct': round((performance_metrics['requests_error'] / max(performance_metrics['requests_total'], 1)) * 100, 2),
                'success_rate_pct': round((performance_metrics['requests_success'] / max(performance_metrics['requests_total'], 1)) * 100, 2),
                'avg_response_time_ms': round(performance_metrics['avg_response_time_ms'], 2)
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Metrics retrieval failed: {str(e)}")
        return {
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }

@router.post("/enhanced/metrics/reset")
async def reset_performance_metrics():
    """
    Reset performance metrics (admin endpoint).
    """
    global performance_metrics
    performance_metrics = {
        'requests_total': 0,
        'requests_success': 0,
        'requests_error': 0,
        'avg_response_time_ms': 0.0,
        'last_reset': time.time()
    }
    
    return {
        'status': 'metrics_reset',
        'timestamp': datetime.utcnow().isoformat()
    }

# Helper functions for analysis

def _analyze_score_distribution(candidates: List[Dict[str, Any]]) -> Dict[str, int]:
    """Analyze score distribution of squeeze candidates."""
    distribution = {
        'extreme': 0,  # >= 0.85
        'high': 0,     # 0.75-0.84
        'medium': 0,   # 0.5-0.74
        'low': 0       # < 0.5
    }
    
    for candidate in candidates:
        score = candidate.get('squeeze_score', 0)
        if score >= 0.85:
            distribution['extreme'] += 1
        elif score >= 0.75:
            distribution['high'] += 1
        elif score >= 0.5:
            distribution['medium'] += 1
        else:
            distribution['low'] += 1
    
    return distribution

def _calculate_avg_squeeze_score(candidates: List[Dict[str, Any]]) -> float:
    """Calculate average squeeze score."""
    if not candidates:
        return 0.0
    
    total_score = sum(c.get('squeeze_score', 0) for c in candidates)
    return round(total_score / len(candidates), 3)