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

from ..services.bms_engine_simple import BMSEngine

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize BMS Engine
polygon_key = os.getenv('POLYGON_API_KEY', '1ORwpSzeOV20X6uaA8G3Zuxx7hLJ0KIC')
bms_engine = BMSEngine(polygon_key)

@router.get("/candidates")
async def get_candidates(
    limit: int = Query(20, description="Maximum number of candidates to return"),
    action_filter: Optional[str] = Query(None, description="Filter by action: TRADE_READY, MONITOR")
):
    """
    Get current BMS candidates
    
    Replaces: /discovery/contenders, /discovery/squeeze-candidates
    Returns: Clean candidate list with BMS scores
    """
    try:
        logger.info(f"Fetching BMS candidates (limit: {limit})")
        
        # Get candidates from BMS engine
        candidates = await bms_engine.discover_candidates(limit=limit * 2)  # Get more to filter
        
        # Apply action filter if specified
        if action_filter:
            candidates = [c for c in candidates if c['action'] == action_filter]
        
        # Limit results
        candidates = candidates[:limit]
        
        response = {
            'candidates': candidates,
            'count': len(candidates),
            'timestamp': datetime.now().isoformat(),
            'engine': 'BMS v1.0',
            'filters_applied': {
                'limit': limit,
                'action_filter': action_filter
            }
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting candidates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/candidates/trade-ready")
async def get_trade_ready_candidates(limit: int = Query(10, description="Max trade-ready candidates")):
    """
    Get only TRADE_READY candidates (score 75+)
    Quick endpoint for immediate execution opportunities
    """
    return await get_candidates(limit=limit, action_filter="TRADE_READY")

@router.get("/candidates/monitor")
async def get_monitor_candidates(limit: int = Query(15, description="Max monitor candidates")):
    """
    Get only MONITOR candidates (score 60-74)
    Watchlist opportunities to track
    """
    return await get_candidates(limit=limit, action_filter="MONITOR")

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
        market_data = await bms_engine.fetch_market_data(symbol)
        if not market_data:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        
        # Calculate BMS score
        analysis = bms_engine.calculate_bms_score(market_data)
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
        u = bms_engine.config["universe"]
        
        # Add API connectivity tests
        try:
            # Quick Polygon API test
            test_data = await bms_engine.get_market_data_polygon('AAPL')
            api_health = "healthy" if test_data else "degraded"
        except:
            api_health = "error"
        
        return {
            'status': 'healthy',
            'engine': health_status['engine'],
            'price_bounds': {'min': u['min_price'], 'max': u['max_price']},
            'dollar_volume_min_m': u['min_dollar_volume_m'],
            'options_required': u['require_liquid_options'],
            'components': {
                'bms_engine': 'healthy',
                'polygon_api': api_health,
                'config': 'loaded'
            },
            'config_summary': {
                'scoring_weights': health_status['config']['weights'],
                'thresholds': health_status['config']['thresholds'],
                'action_levels': health_status['config']['scoring']
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
        candidates = await bms_engine.discover_candidates(limit=limit)
        
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
        # Historical winners from portfolio
        winners = [
            {'symbol': 'VIGL', 'gain_pct': 324.0},
            {'symbol': 'CRWV', 'gain_pct': 171.0},
            {'symbol': 'AEVA', 'gain_pct': 162.0},
            {'symbol': 'CRDO', 'gain_pct': 108.0},
            {'symbol': 'SEZL', 'gain_pct': 66.0},
            {'symbol': 'SMCI', 'gain_pct': 35.0},
            {'symbol': 'TSLA', 'gain_pct': 21.0},
            {'symbol': 'REKR', 'gain_pct': 17.0},
            {'symbol': 'AMD', 'gain_pct': 16.0},
            {'symbol': 'NVDA', 'gain_pct': 16.0},
            {'symbol': 'QUBT', 'gain_pct': 15.5},
            {'symbol': 'AVGO', 'gain_pct': 12.0},
            {'symbol': 'RGTI', 'gain_pct': 12.0},
            {'symbol': 'SPOT', 'gain_pct': 7.0},
            {'symbol': 'WOLF', 'gain_pct': -25.0}  # The one loser
        ]
        
        # Analyze current scores for these symbols
        analysis_results = []
        for winner in winners:
            try:
                market_data = await bms_engine.fetch_market_data(winner['symbol'])
                if market_data:
                    current_score = bms_engine.calculate_bms_score(market_data)
                    if current_score:
                        analysis_results.append({
                            'symbol': winner['symbol'],
                            'historical_gain': winner['gain_pct'],
                            'current_bms_score': current_score['bms_score'],
                            'current_action': current_score['action'],
                            'would_catch_now': current_score['bms_score'] >= 60
                        })
            except Exception as e:
                logger.error(f"Error analyzing {winner['symbol']}: {e}")
        
        # Summary statistics
        total_analyzed = len(analysis_results)
        would_catch = len([r for r in analysis_results if r['would_catch_now']])
        big_winners = [r for r in analysis_results if r['historical_gain'] > 100]
        big_winners_caught = len([r for r in big_winners if r['would_catch_now']])
        
        return {
            'analysis_summary': {
                'total_symbols': total_analyzed,
                'would_catch_now': would_catch,
                'catch_rate': (would_catch / total_analyzed * 100) if total_analyzed > 0 else 0,
                'big_winners_total': len(big_winners),
                'big_winners_caught': big_winners_caught,
                'big_winner_catch_rate': (big_winners_caught / len(big_winners) * 100) if big_winners else 0
            },
            'symbol_analysis': analysis_results,
            'timestamp': datetime.now().isoformat(),
            'validation_note': 'This compares current BMS scores to historical June-July 2025 performance'
        }
        
    except Exception as e:
        logger.error(f"Winners analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Add some basic stats endpoints
@router.get("/stats")
async def get_discovery_stats():
    """Get basic discovery statistics"""
    try:
        candidates = await bms_engine.discover_candidates(limit=50)
        
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