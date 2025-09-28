"""
Squeeze Detection Routes - AlphaStack v2 Integration
Provides squeeze candidate discovery for frontend monitoring
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

# Import the discovery system
from .discovery_optimized import ExplosiveDiscoveryEngine

logger = logging.getLogger(__name__)

router = APIRouter()

# Create discovery engine instance
discovery_engine = ExplosiveDiscoveryEngine()

@router.get("/candidates")
async def get_squeeze_candidates(
    limit: int = Query(default=20, ge=1, le=100),
    min_score: float = Query(default=0.60, ge=0.0, le=1.0),
    regime: Optional[str] = Query(default=None, regex="^(builder|spike|all)$")
) -> Dict[str, Any]:
    """
    Get squeeze candidates with AlphaStack v2 scoring

    Parameters:
    - limit: Maximum number of candidates to return (1-100)
    - min_score: Minimum AlphaStack score filter (0.0-1.0)
    - regime: Filter by regime type (builder/spike/all)
    """
    try:
        logger.info(f"Fetching squeeze candidates: limit={limit}, min_score={min_score}, regime={regime}")

        # Get candidates from discovery engine
        result = await discovery_engine.run_discovery(limit=limit * 2)  # Get extra for filtering

        if not result.get('success', False):
            logger.error(f"Discovery failed: {result.get('error', 'Unknown error')}")
            return {
                "success": False,
                "error": result.get('error', 'Discovery failed'),
                "candidates": [],
                "count": 0,
                "timestamp": datetime.now().isoformat()
            }

        candidates = result.get('candidates', [])

        # Filter for squeeze characteristics
        squeeze_candidates = []
        for candidate in candidates:
            # Check if score meets minimum
            score = candidate.get('total_score', 0)
            if score < min_score:
                continue

            # Filter by regime if specified
            if regime and regime != 'all':
                candidate_regime = candidate.get('alphastack_regime', '').lower()
                if candidate_regime != regime:
                    continue

            # Enhance with squeeze-specific data
            candidate['squeeze_potential'] = calculate_squeeze_potential(candidate)
            candidate['squeeze_rank'] = get_squeeze_rank(candidate)

            squeeze_candidates.append(candidate)

        # Sort by squeeze potential
        squeeze_candidates.sort(key=lambda x: x.get('squeeze_potential', 0), reverse=True)

        # Limit results
        squeeze_candidates = squeeze_candidates[:limit]

        return {
            "success": True,
            "candidates": squeeze_candidates,
            "count": len(squeeze_candidates),
            "filters": {
                "min_score": min_score,
                "regime": regime or "all"
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting squeeze candidates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monitor")
async def squeeze_monitor(
    watchlist_only: bool = Query(default=False),
    include_stats: bool = Query(default=True)
) -> Dict[str, Any]:
    """
    Get squeeze monitoring data with statistics
    """
    try:
        # Get all candidates
        candidates_result = await get_squeeze_candidates(limit=50, min_score=0.60)

        if not candidates_result.get('success'):
            return candidates_result

        candidates = candidates_result.get('candidates', [])

        # Separate by action level
        trade_ready = [c for c in candidates if c.get('total_score', 0) >= 0.75]
        watchlist = [c for c in candidates if 0.60 <= c.get('total_score', 0) < 0.75]

        # Filter if watchlist only
        if watchlist_only:
            display_candidates = watchlist
        else:
            display_candidates = candidates

        response = {
            "success": True,
            "candidates": display_candidates,
            "count": len(display_candidates),
            "timestamp": datetime.now().isoformat()
        }

        # Add statistics if requested
        if include_stats:
            response["stats"] = {
                "total_candidates": len(candidates),
                "trade_ready": len(trade_ready),
                "watchlist": len(watchlist),
                "avg_score": sum(c.get('total_score', 0) for c in candidates) / len(candidates) if candidates else 0,
                "top_squeeze": candidates[0].get('ticker') if candidates else None,
                "regimes": {
                    "builder": len([c for c in candidates if c.get('alphastack_regime') == 'builder']),
                    "spike": len([c for c in candidates if c.get('alphastack_regime') == 'spike'])
                }
            }

        return response

    except Exception as e:
        logger.error(f"Error in squeeze monitor: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts")
async def get_squeeze_alerts(
    min_change: float = Query(default=5.0),
    min_volume_ratio: float = Query(default=2.0)
) -> Dict[str, Any]:
    """
    Get real-time squeeze alerts for stocks meeting criteria
    """
    try:
        # Get candidates with high scores
        candidates_result = await get_squeeze_candidates(limit=100, min_score=0.70)

        if not candidates_result.get('success'):
            return candidates_result

        candidates = candidates_result.get('candidates', [])

        # Filter for alert criteria
        alerts = []
        for candidate in candidates:
            change_pct = abs(candidate.get('change_pct', 0))
            volume_ratio = candidate.get('intraday_relative_volume', 0)

            if change_pct >= min_change and volume_ratio >= min_volume_ratio:
                alert = {
                    "ticker": candidate.get('ticker'),
                    "alert_type": determine_alert_type(candidate),
                    "score": candidate.get('total_score', 0) * 100,
                    "change_pct": change_pct,
                    "volume_ratio": volume_ratio,
                    "price": candidate.get('price', 0),
                    "squeeze_potential": candidate.get('squeeze_potential', 0),
                    "message": generate_alert_message(candidate),
                    "timestamp": datetime.now().isoformat()
                }
                alerts.append(alert)

        # Sort by urgency (score * volume)
        alerts.sort(key=lambda x: x['score'] * x['volume_ratio'], reverse=True)

        return {
            "success": True,
            "alerts": alerts,
            "count": len(alerts),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting squeeze alerts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

def calculate_squeeze_potential(candidate: Dict[str, Any]) -> float:
    """Calculate squeeze potential score (0-100)"""

    # Get component scores
    score = candidate.get('total_score', 0)
    irv = candidate.get('intraday_relative_volume', 1.0)
    consecutive_ups = candidate.get('consecutive_up_days', 0)

    # Get subscore components if available
    subscores = candidate.get('subscores', {})
    squeeze_score = subscores.get('squeeze', 0)
    volume_score = subscores.get('volume_momentum', 0)

    # Calculate squeeze potential
    # Base on AlphaStack score
    base_potential = score * 50

    # Add volume surge bonus
    volume_bonus = min(irv * 5, 25)

    # Add momentum bonus
    momentum_bonus = min(consecutive_ups * 3, 15)

    # Add squeeze subscore
    squeeze_bonus = squeeze_score * 0.5

    total_potential = base_potential + volume_bonus + momentum_bonus + squeeze_bonus

    return min(total_potential, 100)

def get_squeeze_rank(candidate: Dict[str, Any]) -> str:
    """Determine squeeze rank based on potential"""

    potential = candidate.get('squeeze_potential', 0)

    if potential >= 80:
        return "EXTREME"
    elif potential >= 60:
        return "HIGH"
    elif potential >= 40:
        return "MODERATE"
    else:
        return "LOW"

def determine_alert_type(candidate: Dict[str, Any]) -> str:
    """Determine the type of squeeze alert"""

    score = candidate.get('total_score', 0)
    regime = candidate.get('alphastack_regime', '')
    irv = candidate.get('intraday_relative_volume', 0)

    if score >= 0.85 and irv >= 5:
        return "EXPLOSIVE"
    elif score >= 0.75 and regime == 'spike':
        return "BREAKOUT"
    elif score >= 0.75 and regime == 'builder':
        return "MOMENTUM"
    elif irv >= 10:
        return "VOLUME_SPIKE"
    else:
        return "WATCH"

def generate_alert_message(candidate: Dict[str, Any]) -> str:
    """Generate alert message for squeeze candidate"""

    ticker = candidate.get('ticker', 'UNKNOWN')
    score = candidate.get('total_score', 0) * 100
    irv = candidate.get('intraday_relative_volume', 0)
    change = candidate.get('change_pct', 0)
    regime = candidate.get('alphastack_regime', 'unknown')

    if score >= 85:
        return f"🚨 {ticker} EXPLOSIVE SQUEEZE: {score:.0f} score, {irv:.1f}x volume!"
    elif regime == 'spike' and irv >= 5:
        return f"⚡ {ticker} SPIKE DETECTED: {change:+.1f}% on {irv:.1f}x volume"
    elif regime == 'builder' and score >= 75:
        return f"📈 {ticker} BUILDING SQUEEZE: {score:.0f} score, momentum accelerating"
    else:
        return f"👀 {ticker} SQUEEZE WATCH: {score:.0f} score, {irv:.1f}x volume"

@router.get("/health")
async def squeeze_health() -> Dict[str, str]:
    """Health check for squeeze endpoints"""
    return {
        "status": "healthy",
        "service": "squeeze-monitor",
        "version": "2.0.0",
        "engine": "AlphaStack v2"
    }