"""
BMS Discovery API Routes
Clean unified discovery system based on June-July winner patterns
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict
import logging
import asyncio
from datetime import datetime
import os

from ..services.bms_engine_real import RealBMSEngine as BMSEngine
from ..services.discovery_worker import get_worker

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize BMS Engine
polygon_key = os.getenv('POLYGON_API_KEY', '1ORwpSzeOV20X6uaA8G3Zuxx7hLJ0KIC')
bms_engine = BMSEngine(polygon_key)

@router.get("/candidates")
async def get_candidates(
    limit: int = Query(20, description="Maximum number of candidates to return"),
    action_filter: Optional[str] = Query(None, description="Filter by action: TRADE_READY, MONITOR"),
    force_refresh: bool = Query(False, description="Force fresh discovery (bypasses cache)")
):
    """
    Get current BMS candidates - returns cached results for speed
    
    Replaces: /discovery/contenders, /discovery/squeeze-candidates
    Returns: Clean candidate list with BMS scores and cache metadata
    """
    return await _get_candidates_impl(limit, action_filter, force_refresh)

@router.get("/contenders")  
async def get_contenders_alias(
    limit: int = Query(20, description="Maximum number of contenders to return"),
    action_filter: Optional[str] = Query(None, description="Filter by action: TRADE_READY, MONITOR"),
    force_refresh: bool = Query(False, description="Force fresh discovery (bypasses cache)")
):
    """
    Compatibility alias for /candidates endpoint
    Maintains backward compatibility with existing frontend code
    """
    return await _get_candidates_impl(limit, action_filter, force_refresh)

async def _get_candidates_impl(
    limit: int = 20,
    action_filter: Optional[str] = None,
    force_refresh: bool = False
):
    """
    Get current BMS candidates - returns cached results for speed
    
    Replaces: /discovery/contenders, /discovery/squeeze-candidates
    Returns: Clean candidate list with BMS scores and cache metadata
    """
    try:
        worker = get_worker()
        
        # Try cache first unless force refresh requested
        if not force_refresh and worker:
            cached_result = await worker.get_cached_candidates(action_filter, limit)
            if cached_result.get('cached') and cached_result.get('candidates'):
                logger.info(f"Returning {len(cached_result['candidates'])} cached candidates")
                
                response = {
                    'candidates': cached_result['candidates'],
                    'count': cached_result['count'],
                    'engine': 'BMS v1.1 - Cached',
                    'cached': True,
                    'updated_at': cached_result.get('updated_at'),
                    'duration_ms': cached_result.get('duration_ms'),
                    'filters_applied': {
                        'limit': limit,
                        'action_filter': action_filter
                    },
                    'universe': cached_result.get('universe_counts', {}),
                    'timings_ms': cached_result.get('stage_timings', {})
                }
                
                return response
        
        # Fallback to live discovery
        logger.info(f"Running live discovery (limit: {limit}, force: {force_refresh})")
        
        candidates = await bms_engine.discover_real_candidates(limit=limit * 2, enable_early_stop=True)
        
        # Apply action filter if specified
        if action_filter:
            candidates = [c for c in candidates if c['action'] == action_filter]
        
        # Limit results
        candidates = candidates[:limit]
        
        response = {
            'candidates': candidates,
            'count': len(candidates),
            'timestamp': datetime.now().isoformat(),
            'engine': 'BMS v1.1 - Live',
            'cached': False,
            'duration_ms': bms_engine.stage_timings.total_ms,
            'filters_applied': {
                'limit': limit,
                'action_filter': action_filter
            },
            'universe': bms_engine.last_universe_counts,
            'timings_ms': {
                'prefilter': bms_engine.stage_timings.prefilter_ms,
                'intraday': bms_engine.stage_timings.intraday_ms,
                'scoring': bms_engine.stage_timings.scoring_ms,
                'total': bms_engine.stage_timings.total_ms
            }
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting candidates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/candidates/trade-ready")
async def get_trade_ready_candidates(
    limit: int = Query(10, description="Max trade-ready candidates"),
    force_refresh: bool = Query(False, description="Force fresh discovery")
):
    """
    Get only TRADE_READY candidates (score 75+)
    Quick endpoint for immediate execution opportunities
    """
    return await get_candidates(limit=limit, action_filter="TRADE_READY", force_refresh=force_refresh)

@router.get("/candidates/monitor")
async def get_monitor_candidates(
    limit: int = Query(15, description="Max monitor candidates"),
    force_refresh: bool = Query(False, description="Force fresh discovery")
):
    """
    Get only MONITOR candidates (score 60-74)
    Watchlist opportunities to track
    """
    return await get_candidates(limit=limit, action_filter="MONITOR", force_refresh=force_refresh)

@router.get("/audit/{symbol}")
async def audit_symbol(symbol: str):
    """
    Detailed analysis of a specific symbol
    
    Replaces: /discovery/audit/{symbol}
    Returns: Complete BMS breakdown for symbol
    """
    try:
        symbol = symbol.upper()
        logger.info(f"Auditing symbol: {symbol}")
        
        # Fetch comprehensive data
        market_data = await bms_engine.get_real_market_data(symbol)
        if not market_data:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        
        # Calculate BMS score
        analysis = bms_engine._calculate_real_bms_score(market_data)
        if not analysis:
            raise HTTPException(status_code=500, detail=f"Failed to analyze {symbol}")
        
        # Enhanced audit response
        audit_data = {
            'symbol': symbol,
            'analysis': analysis,
            'market_data': market_data,
            'bms_breakdown': {
                'volume_surge': {
                    'score': analysis['component_scores']['volume_surge'],
                    'weight': bms_engine.config['weights']['volume_surge'],
                    'contribution': analysis['component_scores']['volume_surge'] * bms_engine.config['weights']['volume_surge'],
                    'current_relvol': market_data['rel_volume_30d'],
                    'threshold': bms_engine.config['thresholds']['min_volume_surge']
                },
                'price_momentum': {
                    'score': analysis['component_scores']['price_momentum'],
                    'weight': bms_engine.config['weights']['price_momentum'],
                    'contribution': analysis['component_scores']['price_momentum'] * bms_engine.config['weights']['price_momentum'],
                    'momentum_1d': market_data['momentum_1d'],
                    'momentum_5d': market_data['momentum_5d'],
                    'momentum_30d': market_data['momentum_30d']
                },
                'volatility_expansion': {
                    'score': analysis['component_scores']['volatility_expansion'],
                    'weight': bms_engine.config['weights']['volatility_expansion'],
                    'contribution': analysis['component_scores']['volatility_expansion'] * bms_engine.config['weights']['volatility_expansion'],
                    'current_atr': market_data['atr_pct'],
                    'threshold': bms_engine.config['thresholds']['min_atr_pct']
                },
                'risk_filter': {
                    'score': analysis['component_scores']['risk_filter'],
                    'weight': bms_engine.config['weights']['risk_filter'],
                    'contribution': analysis['component_scores']['risk_filter'] * bms_engine.config['weights']['risk_filter'],
                    'float_shares': market_data['float_shares'],
                    'short_ratio': market_data['short_ratio']
                }
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return audit_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error auditing {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """
    System health check
    
    Replaces: /discovery/health, /discovery/status
    Returns: Clean system status including price bounds
    """
    try:
        health_status = bms_engine.get_health_status()
        
        # Safely access config
        u = getattr(bms_engine, 'config', {}).get('universe', {
            'min_price': 0.5, 
            'max_price': 100.0, 
            'min_dollar_volume_m': 10.0
        })
        
        # Add API connectivity tests
        try:
            # Quick Polygon API test
            test_data = await bms_engine.get_real_market_data('AAPL')
            api_health = "healthy" if test_data else "degraded"
        except:
            api_health = "error"
        
        # Get worker health if available
        worker = get_worker()
        worker_health = await worker.health_check() if worker else {'worker_running': False}
        
        return {
            'status': 'healthy',
            'engine': health_status['engine'],
            'price_bounds': {'min': u.get('min_price', 0.5), 'max': u.get('max_price', 100.0)},
            'dollar_volume_min_m': u.get('min_dollar_volume_m', 10.0),
            'universe': health_status.get('universe', {}),
            'performance': health_status.get('performance', {}),
            'timings_ms': health_status.get('timings_ms', {}),
            'components': {
                'bms_engine': 'healthy',
                'polygon_api': api_health,
                'config': 'loaded',
                'background_worker': 'running' if worker_health.get('worker_running') else 'stopped',
                'redis_cache': 'connected' if worker_health.get('redis_connected') else 'disconnected'
            },
            'cache_status': {
                'last_update': worker_health.get('last_cache_update'),
                'candidates_count': worker_health.get('cached_candidates', 0),
                'age_seconds': worker_health.get('cache_age_seconds')
            },
            'config_summary': {
                'scoring_weights': health_status.get('config', {}).get('weights', {}),
                'thresholds': health_status.get('config', {}).get('thresholds', {}),
                'action_levels': health_status.get('config', {}).get('scoring', {})
            },
            'time': datetime.utcnow().isoformat() + 'Z'
        }
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

@router.post("/trigger")
async def trigger_discovery(
    limit: int = Query(25, description="Number of candidates to discover"),
    force_refresh: bool = Query(False, description="Force fresh data fetch")
):
    """
    Manually trigger discovery scan
    
    Replaces: /discovery/trigger
    Returns: Fresh candidate scan results
    """
    try:
        logger.info(f"Manual discovery trigger (limit: {limit}, force: {force_refresh})")
        
        # Force fresh discovery
        candidates = await bms_engine.discover_real_candidates(limit=limit)
        
        # Summary stats
        trade_ready = [c for c in candidates if c['action'] == 'TRADE_READY']
        monitor = [c for c in candidates if c['action'] == 'MONITOR']
        
        return {
            'trigger_time': datetime.now().isoformat(),
            'scan_results': {
                'total_found': len(candidates),
                'trade_ready': len(trade_ready),
                'monitor': len(monitor),
                'avg_score': sum(c['bms_score'] for c in candidates) / len(candidates) if candidates else 0
            },
            'candidates': candidates,
            'forced_refresh': force_refresh
        }
        
    except Exception as e:
        logger.error(f"Discovery trigger error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/progress")
async def get_discovery_progress():
    """
    Get real-time discovery progress
    
    Returns current scan progress for UI progress bars
    """
    try:
        worker = get_worker()
        
        if worker:
            # Get cache metadata for progress info
            cached_meta = await worker.get_cached_candidates(limit=1)
            if cached_meta.get('cached'):
                return {
                    'status': 'cached',
                    'updated_at': cached_meta.get('updated_at'),
                    'candidates_found': cached_meta.get('count', 0),
                    'trade_ready': cached_meta.get('trade_ready', 0),
                    'monitor': cached_meta.get('monitor', 0),
                    'duration_ms': cached_meta.get('duration_ms', 0),
                    'universe_counts': cached_meta.get('universe_counts', {}),
                    'stage_timings': cached_meta.get('stage_timings', {}),
                    'next_cycle_seconds': worker.cycle_seconds
                }
        
        # Fallback to current engine state
        return {
            'status': 'live',
            'engine': 'BMS v1.1',
            'universe_counts': bms_engine.last_universe_counts,
            'timings_ms': {
                'prefilter': bms_engine.stage_timings.prefilter_ms,
                'intraday': bms_engine.stage_timings.intraday_ms,
                'scoring': bms_engine.stage_timings.scoring_ms,
                'total': bms_engine.stage_timings.total_ms
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting progress: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

@router.get("/config")
async def get_configuration():
    """
    Get current BMS engine configuration
    
    Returns: All scoring weights, thresholds, and settings
    """
    try:
        config = bms_engine.config.copy()
        config['timestamp'] = datetime.now().isoformat()
        config['version'] = 'BMS v1.0'
        config['description'] = 'Breakout Momentum Score based on June-July 2025 winners'
        
        return config
        
    except Exception as e:
        logger.error(f"Config fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/backtest/{symbol}")
async def backtest_symbol(
    symbol: str,
    date: Optional[str] = Query(None, description="Historical date (YYYY-MM-DD)")
):
    """
    Backtest how a symbol would have scored historically
    
    New endpoint for validation against June-July winners
    """
    try:
        symbol = symbol.upper()
        
        if not date:
            # Use current data
            return await audit_symbol(symbol)
        
        # For historical backtesting, we'd need historical data
        # For now, return current analysis with note
        current_analysis = await audit_symbol(symbol)
        current_analysis['backtest_note'] = f"Historical backtest for {date} would require time-series data"
        current_analysis['backtest_date_requested'] = date
        
        return current_analysis
        
    except Exception as e:
        logger.error(f"Backtest error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/winners-analysis")
async def analyze_historical_winners():
    """
    Analyze the June-July 2025 winner patterns
    
    New endpoint to validate system against known successful trades
    """
    try:
        # This endpoint is deprecated - historical analysis should use real portfolio data
        # For security and privacy, no hardcoded portfolio data is included
        return {
            'message': 'Historical winners analysis has been removed for production security',
            'status': 'deprecated',
            'alternative': 'Use /discovery/candidates to find current opportunities based on real market data',
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Winners analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Add some basic stats endpoints
@router.get("/stats")
async def get_discovery_stats():
    """Get basic discovery statistics"""
    try:
        candidates = await bms_engine.discover_real_candidates(limit=50)
        
        if not candidates:
            return {'message': 'No candidates found', 'timestamp': datetime.now().isoformat()}
        
        scores = [c['bms_score'] for c in candidates]
        
        return {
            'candidate_stats': {
                'total_candidates': len(candidates),
                'avg_score': sum(scores) / len(scores),
                'max_score': max(scores),
                'min_score': min(scores),
                'trade_ready': len([c for c in candidates if c['action'] == 'TRADE_READY']),
                'monitor': len([c for c in candidates if c['action'] == 'MONITOR'])
            },
            'top_3': candidates[:3],
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))