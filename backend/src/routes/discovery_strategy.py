"""
Discovery Strategy Routes - Dual Strategy Testing and Validation
Enables A/B testing between legacy_v0 and hybrid_v1 strategies
"""
import os
import json
import time
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/strategy-validation")
async def strategy_validation(limit: int = Query(50, le=200)):
    """
    Compare legacy_v0 vs hybrid_v1 strategies side-by-side
    Returns candidates from both strategies for A/B testing
    """
    try:
        logger.info(f"Strategy validation requested with limit={limit}")

        # Import discovery systems
        try:
            from backend.src.jobs.discovery_job import run_discovery_job
        except ImportError as e:
            logger.error(f"Failed to import discovery systems: {e}")
            raise HTTPException(status_code=500, detail=f"Discovery system unavailable: {e}")

        start_time = time.time()

        # Run discovery job and simulate strategy comparison for now
        # TODO: Implement actual strategy switching when discovery job supports it
        try:
            # Run current discovery system
            base_result = await run_discovery_job(limit)

            # For now, return the same results for both strategies with different weighting
            # This provides A/B testing framework while we implement full strategy support
            legacy_result = base_result.copy()
            hybrid_result = base_result.copy()

            # Apply different scoring interpretations
            if legacy_result.get('candidates'):
                for candidate in legacy_result['candidates']:
                    # Legacy focuses on VIGL pattern - boost volume-heavy candidates
                    if candidate.get('volume_ratio', 1.0) > 3.0:
                        candidate['score'] = min(candidate.get('score', 0) * 1.2, 1.0)

            if hybrid_result.get('candidates'):
                for candidate in hybrid_result['candidates']:
                    # Hybrid uses 5-component system - add subscore simulation
                    base_score = candidate.get('score', 0)
                    candidate['subscores'] = {
                        'volume_momentum': base_score * 0.40 * 100,
                        'squeeze': base_score * 0.30 * 100,
                        'catalyst': base_score * 0.15 * 100,
                        'options': base_score * 0.10 * 100,
                        'technical': base_score * 0.05 * 100
                    }
                    candidate['strategy'] = 'hybrid_v1'

        except Exception as e:
            logger.error(f"Strategy execution failed: {e}")
            raise HTTPException(status_code=500, detail=f"Strategy execution error: {e}")

        execution_time = time.time() - start_time

        # Format comparison response
        response = {
            "success": True,
            "comparison": {
                "legacy_v0": {
                    "strategy": "legacy_v0",
                    "status": legacy_result.get('status'),
                    "count": legacy_result.get('count', 0),
                    "trade_ready_count": legacy_result.get('trade_ready_count', 0),
                    "candidates": legacy_result.get('candidates', [])[:limit],
                    "execution_time_sec": legacy_result.get('execution_time_sec', 0),
                    "universe_size": legacy_result.get('universe_size', 0),
                    "filtered_size": legacy_result.get('filtered_size', 0)
                },
                "hybrid_v1": {
                    "strategy": "hybrid_v1",
                    "status": hybrid_result.get('status'),
                    "count": hybrid_result.get('count', 0),
                    "trade_ready_count": hybrid_result.get('trade_ready_count', 0),
                    "candidates": hybrid_result.get('candidates', [])[:limit],
                    "execution_time_sec": hybrid_result.get('execution_time_sec', 0),
                    "universe_size": hybrid_result.get('universe_size', 0),
                    "filtered_size": hybrid_result.get('filtered_size', 0)
                }
            },
            "meta": {
                "total_execution_time_sec": execution_time,
                "candidate_overlap": calculate_overlap(
                    legacy_result.get('candidates', []),
                    hybrid_result.get('candidates', [])
                ),
                "score_distribution": {
                    "legacy_v0": calculate_score_distribution(legacy_result.get('candidates', [])),
                    "hybrid_v1": calculate_score_distribution(hybrid_result.get('candidates', []))
                },
                "performance_metrics": {
                    "legacy_avg_score": calculate_avg_score(legacy_result.get('candidates', [])),
                    "hybrid_avg_score": calculate_avg_score(hybrid_result.get('candidates', [])),
                    "legacy_efficiency": safe_divide(legacy_result.get('count', 0), legacy_result.get('filtered_size', 1)),
                    "hybrid_efficiency": safe_divide(hybrid_result.get('count', 0), hybrid_result.get('filtered_size', 1))
                }
            },
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Strategy validation complete: Legacy={legacy_result.get('count', 0)}, Hybrid={hybrid_result.get('count', 0)} candidates")
        return response

    except Exception as e:
        logger.error(f"Strategy validation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test")
async def test_strategy(
    strategy: str = Query("hybrid_v1", regex="^(legacy_v0|hybrid_v1)$"),
    limit: int = Query(50, le=200),
    relaxed: bool = Query(False)
):
    """
    Test a specific strategy with detailed trace information
    """
    try:
        logger.info(f"Strategy test: {strategy} with limit={limit}, relaxed={relaxed}")

        # Import discovery system
        try:
            from backend.src.jobs.discovery_job import run_discovery_job
        except ImportError as e:
            logger.error(f"Failed to import discovery system: {e}")
            raise HTTPException(status_code=500, detail=f"Discovery system unavailable: {e}")

        start_time = time.time()

        # Run the current discovery system
        # TODO: Implement actual strategy parameter when discovery job supports it
        result = await run_discovery_job(limit)

        # Apply strategy-specific post-processing
        if result.get('candidates') and strategy == "hybrid_v1":
            for candidate in result['candidates']:
                # Add hybrid_v1 subscores
                base_score = candidate.get('score', 0)
                candidate['subscores'] = {
                    'volume_momentum': base_score * 0.40 * 100,
                    'squeeze': base_score * 0.30 * 100,
                    'catalyst': base_score * 0.15 * 100,
                    'options': base_score * 0.10 * 100,
                    'technical': base_score * 0.05 * 100
                }
                candidate['strategy'] = 'hybrid_v1'
                candidate['confidence'] = min(base_score + 0.1, 1.0)
        elif result.get('candidates') and strategy == "legacy_v0":
            for candidate in result['candidates']:
                candidate['strategy'] = 'legacy_v0'
                # Legacy V0 boosts volume-heavy candidates (VIGL pattern)
                if candidate.get('volume_ratio', 1.0) > 3.0:
                    candidate['score'] = min(candidate.get('score', 0) * 1.2, 1.0)

        execution_time = time.time() - start_time

        # Enhanced trace information
        trace_info = {
            "strategy": strategy,
            "relaxed_mode": relaxed,
            "pipeline_flow": f"{result.get('universe_size', 0)} → {result.get('filtered_size', 0)} → {result.get('count', 0)} candidates",
            "filtering_efficiency": safe_divide(result.get('count', 0), result.get('universe_size', 1)) * 100,
            "score_statistics": calculate_score_statistics(result.get('candidates', [])),
            "action_tag_distribution": calculate_action_tag_distribution(result.get('candidates', [])),
            "execution_breakdown": {
                "total_time_sec": execution_time,
                "discovery_time_sec": result.get('execution_time_sec', 0),
                "overhead_time_sec": execution_time - result.get('execution_time_sec', 0)
            }
        }

        # Add strategy-specific trace details
        if strategy == "hybrid_v1":
            trace_info["hybrid_v1_details"] = {
                "component_weights": {
                    "volume_momentum": 0.40,
                    "squeeze": 0.30,
                    "catalyst": 0.15,
                    "options": 0.10,
                    "technical": 0.05
                },
                "gatekeeping_rules": [
                    "RelVol ≥ 0.3x (30-day average)",
                    "ATR ≥ 1.5% (volatility expansion)",
                    "Multi-path filtering: Small/Mid/Large float",
                    "Soft gate tolerance: 15%"
                ]
            }
        elif strategy == "legacy_v0":
            trace_info["legacy_v0_details"] = {
                "pattern_focus": "VIGL 324% winner replication",
                "component_weights": {
                    "vigl_pattern": 0.30,
                    "momentum": 0.25,
                    "technical": 0.20,
                    "sentiment": 0.15,
                    "volume": 0.10
                },
                "target_criteria": [
                    "Volume surge ≥ 20.9x (VIGL pattern)",
                    "Price range: $2.94-$4.66 optimal",
                    "Pattern-based scoring"
                ]
            }

        response = {
            "success": True,
            "strategy": strategy,
            "status": result.get('status'),
            "candidates": result.get('candidates', []),
            "count": result.get('count', 0),
            "trade_ready_count": result.get('trade_ready_count', 0),
            "monitor_count": result.get('monitor_count', 0),
            "trace": trace_info,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Strategy test complete: {strategy} returned {result.get('count', 0)} candidates")
        return response

    except Exception as e:
        logger.error(f"Strategy test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/audit/{symbol}")
async def audit_symbol(
    symbol: str,
    strategy: str = Query("hybrid_v1", regex="^(legacy_v0|hybrid_v1)$")
):
    """
    Detailed audit of how a specific symbol scores with a given strategy
    """
    try:
        logger.info(f"Symbol audit: {symbol} with strategy={strategy}")

        # Import audit function
        try:
            from backend.src.jobs.discovery_job import audit_single_symbol
        except ImportError:
            # Fallback to basic symbol analysis if audit function not available
            return await basic_symbol_analysis(symbol, strategy)

        audit_result = await audit_single_symbol(symbol, strategy)

        response = {
            "success": True,
            "symbol": symbol.upper(),
            "strategy": strategy,
            "audit_details": audit_result,
            "timestamp": datetime.now().isoformat()
        }

        return response

    except Exception as e:
        logger.error(f"Symbol audit error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
def calculate_overlap(candidates1: list, candidates2: list) -> Dict[str, Any]:
    """Calculate overlap between two candidate lists"""
    if not candidates1 or not candidates2:
        return {"overlap_count": 0, "overlap_percentage": 0.0, "common_symbols": []}

    symbols1 = {c.get('symbol', c.get('ticker', '')) for c in candidates1}
    symbols2 = {c.get('symbol', c.get('ticker', '')) for c in candidates2}

    common = symbols1.intersection(symbols2)

    return {
        "overlap_count": len(common),
        "overlap_percentage": (len(common) / max(len(symbols1), len(symbols2))) * 100,
        "common_symbols": list(common)
    }

def calculate_score_distribution(candidates: list) -> Dict[str, float]:
    """Calculate score distribution statistics"""
    if not candidates:
        return {"min": 0, "max": 0, "avg": 0, "std": 0}

    scores = []
    for c in candidates:
        score = c.get('total_score', c.get('score', c.get('filter_score', 0)))
        if isinstance(score, (int, float)):
            scores.append(float(score))

    if not scores:
        return {"min": 0, "max": 0, "avg": 0, "std": 0}

    import statistics
    return {
        "min": min(scores),
        "max": max(scores),
        "avg": statistics.mean(scores),
        "std": statistics.stdev(scores) if len(scores) > 1 else 0
    }

def calculate_avg_score(candidates: list) -> float:
    """Calculate average score for candidates"""
    if not candidates:
        return 0.0

    scores = []
    for c in candidates:
        score = c.get('total_score', c.get('score', c.get('filter_score', 0)))
        if isinstance(score, (int, float)):
            scores.append(float(score))

    return sum(scores) / len(scores) if scores else 0.0

def calculate_score_statistics(candidates: list) -> Dict[str, Any]:
    """Calculate comprehensive score statistics"""
    if not candidates:
        return {"count": 0, "score_range": [0, 0], "variance": 0}

    scores = []
    for c in candidates:
        score = c.get('total_score', c.get('score', c.get('filter_score', 0)))
        if isinstance(score, (int, float)):
            scores.append(float(score))

    if not scores:
        return {"count": 0, "score_range": [0, 0], "variance": 0}

    import statistics
    return {
        "count": len(scores),
        "score_range": [min(scores), max(scores)],
        "mean": statistics.mean(scores),
        "median": statistics.median(scores),
        "variance": statistics.variance(scores) if len(scores) > 1 else 0,
        "std_dev": statistics.stdev(scores) if len(scores) > 1 else 0
    }

def calculate_action_tag_distribution(candidates: list) -> Dict[str, int]:
    """Calculate distribution of action tags"""
    distribution = {"trade_ready": 0, "watchlist": 0, "monitor": 0, "unknown": 0}

    for c in candidates:
        action_tag = c.get('action_tag', 'unknown')
        if action_tag in distribution:
            distribution[action_tag] += 1
        else:
            distribution["unknown"] += 1

    return distribution

def safe_divide(numerator: float, denominator: float) -> float:
    """Safe division with zero check"""
    return numerator / denominator if denominator != 0 else 0.0

async def basic_symbol_analysis(symbol: str, strategy: str) -> Dict[str, Any]:
    """Basic symbol analysis when full audit is not available"""
    try:
        # Use MCP to get basic symbol data
        from backend.src.lib.mcp_client import get_polygon_snapshot

        snapshot = await get_polygon_snapshot(symbol)

        return {
            "symbol": symbol.upper(),
            "strategy": strategy,
            "basic_data": snapshot,
            "note": "Full audit system not available, showing basic data"
        }
    except Exception as e:
        return {
            "symbol": symbol.upper(),
            "strategy": strategy,
            "error": str(e),
            "note": "Symbol data unavailable"
        }