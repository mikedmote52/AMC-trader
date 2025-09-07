"""
Advanced Ranking API Routes for AMC-TRADER
Provides endpoints for filtering candidates to top money-makers
"""

from fastapi import APIRouter, Query, HTTPException, Request
from typing import List, Dict, Any, Optional
import json
import logging
from datetime import datetime, timezone

from ..services.advanced_ranking_system import rank_top_candidates, AdvancedRankingSystem
from ..shared.redis_client import get_redis_client

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/rank")
async def get_ranked_candidates(
    request: Request,
    max_results: int = Query(5, ge=1, le=10, description="Maximum candidates to return"),
    min_score: float = Query(0.50, ge=0.0, le=1.0, description="Minimum advanced score threshold")
):
    """
    Get top-ranked trading candidates from current discovery results
    
    Transforms 20+ raw candidates into 3-5 highest-probability money-makers
    with complete trading recommendations
    """
    try:
        r = get_redis_client()
        
        # Get current discovery candidates from Redis
        v2_cont_key = "amc:discovery:v2:contenders.latest"
        v1_cont_key = "amc:discovery:contenders.latest"
        
        # Try both Redis keys for compatibility
        raw_candidates = None
        for key in [v2_cont_key, v1_cont_key]:
            data = r.get(key)
            if data:
                raw_candidates = json.loads(data)
                break
        
        if not raw_candidates:
            return {
                "success": False,
                "error": "No discovery candidates available",
                "ranked_candidates": [],
                "count": 0
            }
        
        # Apply advanced ranking system
        ranking_system = AdvancedRankingSystem()
        ranked_candidates = ranking_system.rank_candidates(raw_candidates, max_results)
        
        # Filter by minimum score
        filtered_candidates = [
            c for c in ranked_candidates 
            if c.advanced_score >= min_score
        ]
        
        # Convert to API response format
        response_candidates = []
        for candidate in filtered_candidates:
            response_candidates.append({
                "symbol": candidate.symbol,
                "price": candidate.price,
                "advanced_score": round(candidate.advanced_score, 3),
                "success_probability": round(candidate.success_probability, 2),
                "action": candidate.action,
                "vigl_similarity": round(candidate.vigl_similarity, 3),
                "position_size_pct": round(candidate.position_size_pct, 3),
                "entry_price": candidate.entry_price,
                "stop_loss": candidate.stop_loss, 
                "target_price": candidate.target_price,
                "risk_reward_ratio": candidate.risk_reward_ratio,
                "ranking_factors": {
                    k: round(v, 3) for k, v in candidate.ranking_factors.items()
                },
                "thesis": candidate.thesis
            })
        
        return {
            "success": True,
            "ranked_candidates": response_candidates,
            "count": len(response_candidates),
            "raw_candidates_processed": len(raw_candidates),
            "filter_threshold": min_score,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ranking_metadata": {
                "algorithm_version": "advanced_v1",
                "vigl_pattern_based": True,
                "multi_factor_components": 6,
                "max_position_size": "8%",
                "min_risk_reward_ratio": 2.5
            }
        }
        
    except Exception as e:
        logger.error(f"Error in advanced ranking: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Advanced ranking failed: {str(e)}"
        )


@router.get("/rank/top")
async def get_top_candidate(
    request: Request,
    action_filter: str = Query("", description="Filter by action: STRONG_BUY, BUY, WATCH")
):
    """
    Get the single highest-ranked candidate for immediate action
    
    Returns the best money-making opportunity with full trading plan
    """
    try:
        # Get all ranked candidates
        ranked_response = await get_ranked_candidates(request, max_results=10, min_score=0.0)
        
        if not ranked_response["success"]:
            return ranked_response
        
        candidates = ranked_response["ranked_candidates"]
        
        # Filter by action if specified
        if action_filter:
            candidates = [
                c for c in candidates 
                if c["action"] == action_filter.upper()
            ]
        
        if not candidates:
            return {
                "success": False,
                "error": f"No candidates found with action: {action_filter}",
                "top_candidate": None
            }
        
        # Return top candidate with enhanced metadata
        top_candidate = candidates[0]
        top_candidate["ranking_position"] = 1
        top_candidate["outperformed_candidates"] = len(ranked_response["ranked_candidates"]) - 1
        
        return {
            "success": True,
            "top_candidate": top_candidate,
            "recommendation": _generate_trading_recommendation(top_candidate),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting top candidate: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Top candidate retrieval failed: {str(e)}"
        )


@router.get("/rank/summary")
async def get_ranking_summary(request: Request):
    """
    Get summary statistics of current ranking results
    
    Provides overview of candidate quality distribution and recommendations
    """
    try:
        # Get ranked candidates
        ranked_response = await get_ranked_candidates(request, max_results=10, min_score=0.0)
        
        if not ranked_response["success"]:
            return ranked_response
        
        candidates = ranked_response["ranked_candidates"]
        
        if not candidates:
            return {
                "success": True,
                "summary": {
                    "total_candidates": 0,
                    "message": "No candidates pass advanced ranking criteria"
                }
            }
        
        # Calculate summary statistics
        scores = [c["advanced_score"] for c in candidates]
        action_counts = {}
        for candidate in candidates:
            action = candidate["action"]
            action_counts[action] = action_counts.get(action, 0) + 1
        
        # Position sizing recommendations
        total_recommended_allocation = sum(c["position_size_pct"] for c in candidates)
        
        summary = {
            "total_candidates": len(candidates),
            "score_distribution": {
                "highest": max(scores),
                "lowest": min(scores),
                "average": round(sum(scores) / len(scores), 3)
            },
            "action_breakdown": action_counts,
            "portfolio_allocation": {
                "total_recommended_pct": round(total_recommended_allocation, 1),
                "diversification": len(candidates),
                "max_single_position": round(max(c["position_size_pct"] for c in candidates), 1)
            },
            "trading_readiness": {
                "immediate_buy_signals": action_counts.get("STRONG_BUY", 0),
                "good_opportunities": action_counts.get("BUY", 0),
                "watch_candidates": action_counts.get("WATCH", 0)
            }
        }
        
        return {
            "success": True,
            "summary": summary,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating ranking summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ranking summary failed: {str(e)}"
        )


@router.post("/rank/test")
async def test_ranking_system(
    request: Request,
    test_data: List[Dict[str, Any]] = None
):
    """
    Test the advanced ranking system with custom candidate data
    
    Useful for validation and calibration of the ranking algorithm
    """
    try:
        # Use provided test data or fetch real market data
        if not test_data:
            try:
                from ..services.bms_engine_real import RealBMSEngine
                import os
                
                polygon_key = os.getenv('POLYGON_API_KEY', '1ORwpSzeOV20X6uaA8G3Zuxx7hLJ0KIC')
                bms_engine = RealBMSEngine(polygon_key)
                
                # Get current candidates instead of hardcoded test data
                candidates = await bms_engine.discover_real_candidates(limit=10)
                test_data = candidates if candidates else []
                
            except Exception as e:
                logger.error(f"Error fetching real test data: {e}")
                return {"error": "Unable to fetch real market data for testing", "timestamp": datetime.now().isoformat()}
        
        if not test_data:
            test_data = [
                {
                    'symbol': 'TEST1',
                    'price': 5.50,
                    'factors': {
                        'vigl_similarity': 0.75,
                        'volume_spike_ratio': 8.5,
                        'volume_early_signal': 6.2,
                        'volume_confirmation': 7.1,
                        'price_momentum_1d': -5.2,
                        'rs_5d_percent': -8.1,
                        'atr_percent': 0.08,
                        'compression_percentile': 3.0,
                        'has_news_catalyst': True,
                        'social_rank': 0.7,
                        'wolf_risk_score': 0.3
                    }
                },
                {
                    'symbol': 'TEST2', 
                    'price': 15.20,
                    'factors': {
                        'vigl_similarity': 0.45,
                        'volume_spike_ratio': 2.1,
                        'volume_early_signal': 1.8,
                        'volume_confirmation': 2.3,
                        'price_momentum_1d': 12.5,
                        'rs_5d_percent': 18.2,
                        'atr_percent': 0.05,
                        'compression_percentile': 25.0,
                        'has_news_catalyst': False,
                        'social_rank': 0.2,
                        'wolf_risk_score': 0.2
                    }
                }
            ]
        
        # Apply ranking system
        ranked_candidates = rank_top_candidates(test_data, max_results=10)
        
        # Format response
        test_results = []
        for candidate in ranked_candidates:
            test_results.append({
                "symbol": candidate.symbol,
                "advanced_score": round(candidate.advanced_score, 3),
                "action": candidate.action,
                "success_probability": round(candidate.success_probability, 2),
                "position_size_pct": round(candidate.position_size_pct, 3),
                "risk_reward_ratio": candidate.risk_reward_ratio,
                "ranking_factors": candidate.ranking_factors,
                "thesis": candidate.thesis
            })
        
        return {
            "success": True,
            "test_results": test_results,
            "candidates_tested": len(test_data),
            "candidates_passed": len(ranked_candidates),
            "pass_rate": round(len(ranked_candidates) / len(test_data), 2) if test_data else 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in ranking test: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ranking test failed: {str(e)}"
        )


def _generate_trading_recommendation(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Generate detailed trading recommendation for a candidate"""
    
    action = candidate["action"]
    symbol = candidate["symbol"]
    score = candidate["advanced_score"]
    
    if action == "STRONG_BUY":
        recommendation = {
            "urgency": "HIGH",
            "confidence": "Very High",
            "timeframe": "Enter immediately at market open",
            "rationale": f"Exceptional setup with {score:.1%} advanced score matching VIGL winner pattern",
            "risk_level": "Moderate (managed with tight stops)"
        }
    elif action == "BUY":
        recommendation = {
            "urgency": "MEDIUM",
            "confidence": "High", 
            "timeframe": "Enter within 1-2 trading sessions",
            "rationale": f"Strong opportunity with {score:.1%} advanced score and good risk/reward",
            "risk_level": "Moderate"
        }
    elif action == "WATCH":
        recommendation = {
            "urgency": "LOW",
            "confidence": "Moderate",
            "timeframe": "Monitor for volume/momentum confirmation",
            "rationale": f"Potential setup with {score:.1%} score - needs catalyst confirmation",
            "risk_level": "Higher (wait for better setup)"
        }
    else:
        recommendation = {
            "urgency": "NONE",
            "confidence": "Low",
            "timeframe": "Pass on this opportunity",
            "rationale": f"Insufficient setup quality ({score:.1%} score)",
            "risk_level": "High"
        }
    
    # Add position management guidance
    recommendation["position_management"] = {
        "entry_strategy": "Market order at recommended entry price",
        "stop_placement": f"Strict stop at ${candidate['stop_loss']} ({((candidate['entry_price'] - candidate['stop_loss']) / candidate['entry_price'] * 100):.1f}% risk)",
        "profit_target": f"Initial target ${candidate['target_price']} ({candidate['risk_reward_ratio']}:1 R/R)",
        "position_sizing": f"{candidate['position_size_pct']:.1%} of total portfolio"
    }
    
    return recommendation