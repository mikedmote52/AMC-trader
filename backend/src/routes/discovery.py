from fastapi import APIRouter, Query, HTTPException, Body, Request, Response
from typing import List, Dict, Optional
import json
import importlib
import math
import os
import logging
from datetime import datetime, timezone
from pydantic import BaseModel
from backend.src.shared.redis_client import get_redis_client
from backend.src.services.squeeze_detector import SqueezeDetector
from ..services.short_interest_service import get_short_interest_service
from ..services.short_interest_validator import get_short_interest_validator
from ..strategy_resolver import resolve_effective_strategy, get_strategy_metadata

router = APIRouter()
logger = logging.getLogger(__name__)

# Pydantic models for request validation
class WeightsUpdate(BaseModel):
    volume_momentum: float = None
    squeeze: float = None  
    catalyst: float = None
    options: float = None
    technical: float = None

# Global calibration reference (will be updated by tuning endpoints)
_calibration_cache = None

def _load_calibration_config():
    """Load calibration config with caching"""
    global _calibration_cache
    try:
        import os
        calibration_path = os.path.join(os.path.dirname(__file__), "../../../calibration/active.json")
        if os.path.exists(calibration_path):
            with open(calibration_path, 'r') as f:
                _calibration_cache = json.load(f)
                return _calibration_cache
    except Exception as e:
        logger.error(f"Could not load calibration config: {e}")
    return _calibration_cache or {}

def _save_calibration_config(config):
    """Save calibration config to file"""
    global _calibration_cache
    try:
        import os
        calibration_path = os.path.join(os.path.dirname(__file__), "../../../calibration/active.json")
        with open(calibration_path, 'w') as f:
            json.dump(config, f, indent=2)
        _calibration_cache = config
        return True
    except Exception as e:
        logger.error(f"Could not save calibration config: {e}")
        return False

def _normalize_weights(weights):
    """Normalize weights to sum to 1.0"""
    total = sum(weights.values()) or 1.0
    return {k: max(0.0, v) / total for k, v in weights.items()}

def _invalidate_redis_cache():
    """Invalidate strategy-specific Redis cache"""
    try:
        r = get_redis_client()
        # Clear hybrid_v1 specific caches
        pattern_keys = [
            "amc:discovery:v2:contenders.latest:hybrid_v1",
            "amc:discovery:v2:explain.latest:hybrid_v1", 
            "amc:discovery:contenders.latest:hybrid_v1",
            "amc:discovery:explain.latest:hybrid_v1"
        ]
        for key in pattern_keys:
            if r.exists(key):
                r.delete(key)
        return True
    except Exception as e:
        logger.error(f"Could not invalidate Redis cache: {e}")
        return False

# Redis keys
V2_CONT = "amc:discovery:v2:contenders.latest"
V2_TRACE = "amc:discovery:v2:explain.latest"
V1_CONT = "amc:discovery:contenders.latest"
V1_TRACE = "amc:discovery:explain.latest"
STATUS = "amc:discovery:status"

def _get_json(r, key):
    raw = r.get(key)
    return json.loads(raw) if raw else None

def _load_selector():
    """Load select_candidates function from available jobs modules"""
    for mod in ("backend.src.jobs.discover", "backend.src.jobs.discovery", "src.jobs.discover", "src.jobs.discovery"):
        try:
            m = importlib.import_module(mod)
            f = getattr(m, "select_candidates", None)
            if callable(f):
                return f, mod
        except Exception as e:
            print(f"Failed to import {mod}: {e}")  # Debug logging
            continue
    return None, None

@router.get("/contenders")
async def get_contenders(
    request: Request,
    response: Response,
    strategy: str = Query("", description="Scoring strategy: legacy_v0 or hybrid_v1"),
    session: str = Query("regular", description="Market session: premarket, regular, afterhours")
):
    """
    PRODUCTION ENDPOINT: Returns live market data only with system state monitoring
    Enforces data freshness, drops stale symbols, and provides diagnostic headers
    """
    from datetime import datetime, timezone
    import time
    
    # Set cache control headers
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    # Resolve effective strategy (production enforcement)
    effective_strategy = resolve_effective_strategy(strategy)
    
    r = get_redis_client()
    
    # Strategy-aware Redis keys
    strategy_suffix = f":{effective_strategy}" if effective_strategy and effective_strategy in ["legacy_v0", "hybrid_v1"] else ""
    v2_cont_key = f"{V2_CONT}{strategy_suffix}"
    v2_trace_key = f"{V2_TRACE}{strategy_suffix}"
    v1_cont_key = f"{V1_CONT}{strategy_suffix}"
    v1_trace_key = f"{V1_TRACE}{strategy_suffix}"
    
    # CRITICAL INTEGRITY CHECK: Validate discovery pipeline execution
    trace = _get_json(r, v2_trace_key) or _get_json(r, v2_trace_key) or _get_json(r, V2_TRACE) or _get_json(r, V1_TRACE)
    if trace:
        initial_universe = trace.get("counts_in", {}).get("universe", 0)
        
        # CRITICAL: If initial universe is empty/tiny, discovery failed - return empty
        if initial_universe < 100:
            logger.error(f"❌ CRITICAL FAILURE: Initial universe only {initial_universe} stocks - discovery failed!")
            logger.error("❌ Returning empty list to prevent serving stale/fake data")
            return []
    
    # Check data freshness FIRST
    status = _get_json(r, STATUS)
    if status:
        last_run = status.get('last_run')
        if last_run:
            try:
                from datetime import datetime
                last_run_time = datetime.fromisoformat(last_run.replace('Z', '+00:00'))
                age_seconds = (datetime.now(timezone.utc) - last_run_time).total_seconds()
                
                # CRITICAL: Reject data older than 5 minutes
                if age_seconds > 300:
                    logger.warning(f"❌ Discovery data is {age_seconds:.0f}s old - TOO STALE! Returning empty.")
                    return []
            except:
                pass
    
    # Get candidates but validate freshness (try strategy-specific first, then fallback)
    items = _get_json(r, v2_cont_key) or _get_json(r, v1_cont_key) or _get_json(r, V2_CONT) or _get_json(r, V1_CONT)
    
    if not items:
        logger.error("❌ No discovery data available - returning empty list")
        return []
    
    # CRITICAL DATA INTEGRITY: Check for contaminated fake data
    contaminated_count = 0
    for item in items:
        if isinstance(item, dict):
            si_data = item.get('short_interest_data', {})
            # Count items with fake sector_fallback data
            if si_data.get('source') == 'sector_fallback':
                contaminated_count += 1
    
    # ABSOLUTE REJECTION: Never serve data with ANY fake short interest
    if contaminated_count > 0:
        logger.error(f"❌ CONTAMINATED DATA DETECTED: {contaminated_count}/{len(items)} items have fake sector_fallback data!")
        logger.error("❌ ABSOLUTE REJECTION: Returning empty list to maintain data integrity")
        return []
    
    # Validate we have real data, not stale fallback patterns
    if len(items) == 33 or len(items) == 20:  # Suspicious - likely stale fallback data
        logger.warning(f"⚠️ Detected suspicious data pattern ({len(items)} items) - verifying integrity...")
        
        # Additional integrity checks
        fake_patterns = 0
        for item in items:
            if isinstance(item, dict):
                # Check for fake 15% short interest pattern
                si_data = item.get('short_interest_data', {})
                if (si_data.get('percent', 0) == 0.15 and 
                    si_data.get('confidence', 1) == 0.3):
                    fake_patterns += 1
        
        # If >50% of data shows fake patterns, reject it
        if fake_patterns > len(items) * 0.5:
            logger.error(f"❌ FAKE DATA PATTERN: {fake_patterns}/{len(items)} items show 15%/0.3 fake pattern!")
            logger.error("❌ INTEGRITY FAILURE: Returning empty list")
            return []
    
    # Final validation: Ensure all items have real, verified data
    validated_items = []
    for item in items:
        if isinstance(item, dict):
            si_data = item.get('short_interest_data', {})
            
            # Only include items with real, verified short interest data
            if (si_data.get('source') and 
                si_data.get('source') not in ['sector_fallback', 'default_fallback'] and
                si_data.get('confidence', 0) > 0.3):
                
                # Ensure score exists (0..100) and set confidence = score/100 if missing
                if "score" not in item:
                    item["score"] = 0
                if "confidence" not in item:
                    item["confidence"] = item["score"] / 100.0
                    
                validated_items.append(item)
    
    # Return only validated items with real data
    if not validated_items:
        logger.error("❌ NO REAL DATA: All items failed validation - returning empty list")
        return []
    
    # Get current configuration for telemetry
    try:
        config = _load_calibration_config()
        scoring_config = config.get("scoring", {})
        preset_name = scoring_config.get("preset")
        hybrid_weights = scoring_config.get("hybrid_v1", {}).get("weights", {})
        weights_hash = hash(frozenset(hybrid_weights.items()))
    except:
        preset_name = None
        weights_hash = None
    
    # Calculate thresholds hash for metadata
    try:
        thresholds = config.get("scoring", {}).get("hybrid_v1", {}).get("thresholds", {})
        thresholds_hash = hash(frozenset(str(thresholds).encode()))
    except:
        thresholds_hash = None
    
    # Add telemetry metadata to response
    response_data = {
        "candidates": validated_items,
        "count": len(validated_items),
        "strategy": effective_strategy,
        "filtered_from": len(items),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "meta": {
            "strategy": effective_strategy,
            "preset": preset_name,
            "weights_hash": weights_hash,
            "thresholds_hash": thresholds_hash,
            "session": session,
            "telemetry": {
                "latency_ms": None,  # Will be calculated by caller
                "score_distribution": {
                    "min": min((item.get("score", 0) for item in validated_items), default=0),
                    "max": max((item.get("score", 0) for item in validated_items), default=0),
                    "avg": sum(item.get("score", 0) for item in validated_items) / len(validated_items) if validated_items else 0
                }
            }
        }
    }
    
    # Add system state headers for frontend monitoring
    system_state = "HEALTHY"
    reason_stats = {"stale": 0, "gate": 0, "error": 0, "scored": len(validated_items)}
    
    # Check for stale data
    if status and status.get('last_run'):
        try:
            last_run_time = datetime.fromisoformat(status['last_run'].replace('Z', '+00:00'))
            age_seconds = (datetime.now(timezone.utc) - last_run_time).total_seconds()
            if age_seconds > 300:  # 5 minutes
                system_state = "DEGRADED"
        except:
            system_state = "DEGRADED"
    
    if contaminated_count > 0:
        system_state = "DEGRADED"
        reason_stats["stale"] = contaminated_count
    
    # Set response headers
    response.headers["X-System-State"] = system_state
    response.headers["X-Reason-Stats"] = json.dumps(reason_stats)
    
    logger.info(f"✅ Serving {len(validated_items)} validated items with real data (filtered from {len(items)})")
    return response_data

@router.get("/contenders/debug")
async def debug_contenders(
    request: Request,
    strategy: str = Query("", description="Scoring strategy to debug")
):
    """
    Debug endpoint to explain why contenders endpoint may be returning empty results
    """
    from datetime import datetime, timezone
    import time
    
    effective_strategy = resolve_effective_strategy(strategy)
    r = get_redis_client()
    
    # Get Redis keys
    strategy_suffix = f":{effective_strategy}" if effective_strategy and effective_strategy in ["legacy_v0", "hybrid_v1"] else ""
    v2_cont_key = f"{V2_CONT}{strategy_suffix}"
    v2_trace_key = f"{V2_TRACE}{strategy_suffix}"
    v1_cont_key = f"{V1_CONT}{strategy_suffix}"
    v1_trace_key = f"{V1_TRACE}{strategy_suffix}"
    
    # Check data availability
    items = _get_json(r, v2_cont_key) or _get_json(r, v1_cont_key) or _get_json(r, V2_CONT) or _get_json(r, V1_CONT)
    trace = _get_json(r, v2_trace_key) or _get_json(r, V2_TRACE) or _get_json(r, V1_TRACE)
    status = _get_json(r, STATUS)
    
    # Analyze drop reasons
    drop_reasons = []
    symbols_in = 0
    after_freshness = 0
    watchlist = 0
    trade_ready = 0
    
    if trace:
        counts = trace.get("counts_out", {})
        symbols_in = counts.get("universe", 0)
        after_freshness = symbols_in  # Assume no freshness filtering for now
        
        rejections = trace.get("rejections", {})
        for stage, reasons in rejections.items():
            if isinstance(reasons, dict):
                for reason, count in reasons.items():
                    drop_reasons.append({"reason": f"{stage}_{reason}", "count": count})
    
    # Check data freshness
    data_age_seconds = 0
    system_state = "HEALTHY"
    if status and status.get('last_run'):
        try:
            last_run_time = datetime.fromisoformat(status['last_run'].replace('Z', '+00:00'))
            data_age_seconds = (datetime.now(timezone.utc) - last_run_time).total_seconds()
            if data_age_seconds > 300:  # 5 minutes
                system_state = "DEGRADED"
        except:
            system_state = "DEGRADED"
    
    # Count stale data
    stale_count = 0
    if items:
        for item in items:
            si_data = item.get('short_interest_data', {})
            if si_data.get('source') in ['sector_fallback', 'default_fallback']:
                stale_count += 1
        
        if stale_count > len(items) * 0.4:  # >40% stale
            system_state = "DEGRADED"
    
    # Load current configuration
    try:
        config = _load_calibration_config()
        hybrid_config = config.get("scoring", {}).get("hybrid_v1", {})
        entry_rules = hybrid_config.get("entry_rules", {})
        watchlist_min = entry_rules.get("watchlist_min", 50)
        trade_ready_min = entry_rules.get("trade_ready_min", 55)
    except:
        watchlist_min = 50
        trade_ready_min = 55
    
    return {
        "system_state": system_state,
        "summary": {
            "symbols_in": symbols_in,
            "after_freshness": after_freshness,
            "watchlist": len(items) if items else 0,
            "trade_ready": len([i for i in (items or []) if i.get('score', 0) >= trade_ready_min/100])
        },
        "drop_reasons": sorted(drop_reasons, key=lambda x: x['count'], reverse=True)[:10],
        "config_snapshot": {
            "freshness": {"quotes": 60, "bars_1m": 120},
            "gates": {"watchlist_min": watchlist_min, "trade_ready_min": trade_ready_min}
        },
        "data_diagnostics": {
            "redis_keys_checked": [v2_cont_key, v1_cont_key, V2_CONT, V1_CONT],
            "items_found": len(items) if items else 0,
            "stale_items": stale_count,
            "data_age_seconds": data_age_seconds,
            "effective_strategy": effective_strategy
        }
    }

@router.get("/health")
async def discovery_health():
    """Minimal health endpoint for system monitoring"""
    r = get_redis_client()
    
    # Check universe availability
    universe_status = "DOWN"
    try:
        status = _get_json(r, STATUS)
        if status and status.get('last_run'):
            from datetime import datetime, timezone
            last_run_time = datetime.fromisoformat(status['last_run'].replace('Z', '+00:00'))
            age_seconds = (datetime.now(timezone.utc) - last_run_time).total_seconds()
            if age_seconds < 600:  # 10 minutes
                universe_status = "LIVE"
            else:
                universe_status = "FALLBACK"
    except:
        universe_status = "DOWN"
    
    # Check market data (simplified)
    market_data = "LIVE"  # Assume live unless proven otherwise
    
    # Overall system state
    system_state = "HEALTHY" if universe_status == "LIVE" else "DEGRADED"
    
    return {
        "universe": universe_status,
        "market_data": market_data,
        "system_state": system_state
    }

@router.get("/short-interest")
async def get_short_interest(symbols: str = Query("UP,SPHR,NAK", description="Comma-separated symbols")):
    """Get real short interest data for specified symbols"""
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        short_interest_service = await get_short_interest_service()
        
        results = await short_interest_service.get_bulk_short_interest(symbol_list)
        
        response_data = {}
        for symbol, si_data in results.items():
            if si_data:
                response_data[symbol] = {
                    "short_percent_float": si_data.short_percent_float,
                    "short_percent_display": f"{si_data.short_percent_float:.1%}",
                    "short_ratio": si_data.short_ratio,
                    "shares_short": si_data.shares_short,
                    "source": si_data.source,
                    "confidence": si_data.confidence,
                    "last_updated": si_data.last_updated.isoformat(),
                    "settlement_date": si_data.settlement_date.isoformat() if si_data.settlement_date else None
                }
            else:
                response_data[symbol] = {
                    "error": "No short interest data available",
                    "source": "error"
                }
        
        return {
            "success": True,
            "data": response_data,
            "symbols_requested": len(symbol_list),
            "symbols_found": len([k for k, v in response_data.items() if "error" not in v])
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {}
        }

@router.post("/refresh-short-interest")
async def refresh_short_interest(symbols: str = Query("", description="Comma-separated symbols, empty for all")):
    """Force refresh short interest data"""
    try:
        short_interest_service = await get_short_interest_service()
        
        if symbols.strip():
            symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        else:
            # Use discovery fallback universe if no symbols specified
            from backend.src.jobs.discover import UNIVERSE_FALLBACK
            symbol_list = UNIVERSE_FALLBACK[:20]  # Limit to first 20 to avoid rate limits
        
        results = await short_interest_service.refresh_all_short_interest(symbol_list)
        
        success_count = sum(results.values())
        total_count = len(results)
        
        return {
            "success": True,
            "message": f"Short interest refresh complete: {success_count}/{total_count} successful",
            "results": results,
            "success_rate": success_count / total_count if total_count > 0 else 0.0
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "results": {}
        }

@router.get("/validate-short-interest")
async def validate_short_interest(symbol: str = Query("UP", description="Symbol to validate")):
    """Debug and validate short interest data accuracy for a specific symbol"""
    try:
        validator = await get_short_interest_validator()
        
        # Run comprehensive validation
        validation_result = await validator.validate_against_known_values(symbol)
        alternative_calc = await validator.test_alternative_calculation(symbol)
        
        return {
            "success": True,
            "symbol": symbol,
            "validation_result": validation_result,
            "alternative_calculations": alternative_calc,
            "recommendation": alternative_calc.get("recommendation", "Unknown"),
            "timestamp": validation_result.get("timestamp")
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "symbol": symbol
        }

@router.post("/run-short-interest-diagnostics")
async def run_short_interest_diagnostics():
    """Run comprehensive short interest validation across multiple symbols"""
    try:
        validator = await get_short_interest_validator()
        results = await validator.run_comprehensive_validation()
        
        return {
            "success": True,
            "comprehensive_validation": results,
            "data_quality_assessment": results["summary"]["data_quality"],
            "match_rate": f"{results['summary']['match_rate']:.1%}",
            "recommendations": {
                "immediate_action": "Review individual symbol results for data discrepancies",
                "data_quality": results["summary"]["data_quality"],
                "next_steps": "Consider alternative data sources if match rate < 80%"
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/debug-universe")
async def debug_universe():
    """Debug universe file loading"""
    import os
    try:
        # List actual files and directories
        app_contents = []
        try:
            app_contents = os.listdir('/app')
        except:
            pass
            
        data_contents = []
        try:
            data_contents = os.listdir('/app/data') if os.path.exists('/app/data') else []
        except:
            pass
        
        # Try different possible paths
        paths_to_try = [
            'data/universe.txt',
            '../data/universe.txt', 
            '../../data/universe.txt',
            '../../../data/universe.txt',
            '/app/data/universe.txt',
            os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data/universe.txt'),
            os.path.join(os.getcwd(), 'data/universe.txt')
        ]
        
        results = {}
        for path in paths_to_try:
            try:
                full_path = os.path.abspath(path)
                exists = os.path.exists(full_path)
                results[path] = {
                    "full_path": full_path,
                    "exists": exists,
                    "is_file": os.path.isfile(full_path) if exists else False,
                    "size": os.path.getsize(full_path) if exists and os.path.isfile(full_path) else 0
                }
                if exists and os.path.isfile(full_path):
                    with open(full_path, 'r') as f:
                        lines = f.readlines()[:5]  # First 5 lines
                        results[path]["sample_lines"] = [line.strip() for line in lines]
                        results[path]["total_lines"] = len(f.readlines()) + 5
            except Exception as e:
                results[path] = {"error": str(e)}
        
        return {
            "current_working_directory": os.getcwd(),
            "script_directory": os.path.dirname(__file__),
            "app_directory_contents": app_contents,
            "data_directory_exists": os.path.exists('/app/data'),
            "data_directory_contents": data_contents,
            "universe_paths_tested": results,
            "environment_universe_file": os.getenv('UNIVERSE_FILE', 'data/universe.txt')
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/diagnostics")
async def get_discovery_diagnostics():
    """Get detailed diagnostic status of the discovery pipeline"""
    r = get_redis_client()
    
    # Get the latest discovery trace/explain data
    trace_data = _get_json(r, V2_TRACE) or _get_json(r, V1_TRACE) or {}
    status_data = _get_json(r, STATUS) or {}
    
    # Get current contenders count
    contenders = _get_json(r, V2_CONT) or _get_json(r, V1_CONT) or []
    
    # Build diagnostic response
    return {
        "discovery_status": {
            "last_run": status_data.get("last_run"),
            "status": status_data.get("status", "unknown"),
            "total_stocks_scanned": trace_data.get("total_stocks", 0),
            "candidates_found": len(contenders),
            "processing_time": status_data.get("processing_time"),
            "error": status_data.get("error"),
        },
        "filtering_breakdown": {
            "initial_universe": trace_data.get("initial_count", 0),
            "after_price_filter": trace_data.get("price_filtered", 0),
            "after_volume_filter": trace_data.get("volume_filtered", 0),
            "after_momentum_filter": trace_data.get("momentum_filtered", 0),
            "after_pattern_matching": trace_data.get("pattern_matched", 0),
            "after_confidence_filter": trace_data.get("confidence_filtered", 0),
            "final_candidates": len(contenders)
        },
        "current_thresholds": {
            "min_price": trace_data.get("min_price", 1.0),
            "max_price": trace_data.get("max_price", 100.0),
            "min_volume": trace_data.get("min_volume", 1000000),
            "min_confidence": trace_data.get("min_confidence", 0.75),
            "min_score": trace_data.get("min_score", 50)
        },
        "pipeline_stage_results": trace_data.get("stages", []),
        "reasons_for_no_results": _analyze_no_results(trace_data, contenders)
    }

def _analyze_no_results(trace_data: dict, contenders: list) -> list:
    """Analyze why no results were found"""
    reasons = []
    
    if not trace_data:
        reasons.append("No discovery trace data available - discovery may not have run recently")
        return reasons
    
    initial = trace_data.get("initial_count", 0)
    if initial == 0:
        reasons.append("No stocks in initial universe - data source issue")
        return reasons
    
    # Check each filtering stage
    if trace_data.get("price_filtered", 0) < initial * 0.1:
        reasons.append(f"Price filter too restrictive: eliminated {initial - trace_data.get('price_filtered', 0)} stocks")
    
    if trace_data.get("volume_filtered", 0) < trace_data.get("price_filtered", 0) * 0.1:
        reasons.append(f"Volume filter too restrictive: need >{trace_data.get('min_volume', 1000000):,} volume")
    
    if trace_data.get("pattern_matched", 0) < trace_data.get("volume_filtered", 0) * 0.05:
        reasons.append("Few stocks matching VIGL/squeeze patterns - market conditions not favorable")
    
    if len(contenders) < trace_data.get("pattern_matched", 0):
        reasons.append(f"Confidence threshold too high: {trace_data.get('min_confidence', 0.75):.0%} required")
    
    if not reasons:
        reasons.append("All filtering stages working normally - market simply has no high-quality opportunities right now")
    
    return reasons

@router.get("/explain")
async def explain():
    r = get_redis_client()
    return _get_json(r, V2_TRACE) or _get_json(r, V1_TRACE) or {"stages":[], "counts_in":{}, "counts_out":{}}

@router.get("/status")
async def status():
    r = get_redis_client()
    s = _get_json(r, STATUS)
    if s: return s
    tr = _get_json(r, V2_TRACE) or _get_json(r, V1_TRACE)
    return {"count": (tr or {}).get("count", 0), "ts": (tr or {}).get("ts")}

@router.get("/policy")
async def policy():
    # echo live env gates/weights so you can see what the job used
    env = {
      "PRICE_CAP": float(os.getenv("AMC_PRICE_CAP","100")),
      "REL_VOL_MIN": float(os.getenv("AMC_REL_VOL_MIN","3")),
      "ATR_PCT_MIN": float(os.getenv("AMC_ATR_PCT_MIN","0.04")),
      "FLOAT_MAX": float(os.getenv("AMC_FLOAT_MAX","50000000")),
      "BIG_FLOAT_MIN": float(os.getenv("AMC_BIG_FLOAT_MIN","150000000")),
      "SI_MIN": float(os.getenv("AMC_SI_MIN","0.20")),
      "BORROW_MIN": float(os.getenv("AMC_BORROW_MIN","0.20")),
      "UTIL_MIN": float(os.getenv("AMC_UTIL_MIN","0.85")),
      "IV_PCTL_MIN": float(os.getenv("AMC_IV_PCTL_MIN","0.80")),
      "PCR_MIN": float(os.getenv("AMC_PCR_MIN","2.0")),
      "ENABLE_SECTOR": int(os.getenv("AMC_ENABLE_SECTOR","0")),
      "SECTOR_ETFS": os.getenv("AMC_SECTOR_ETFS","XLF,XLK,XLV,XLE,XLI,XLP,XLY,XLU,XLB,XLRE,XLC"),
      "W": {
        "volume": float(os.getenv("AMC_W_VOLUME","0.25")),
        "short":  float(os.getenv("AMC_W_SHORT","0.20")),
        "catalyst":float(os.getenv("AMC_W_CATALYST","0.20")),
        "sent":   float(os.getenv("AMC_W_SENT","0.15")),
        "options":float(os.getenv("AMC_W_OPTIONS","0.10")),
        "tech":   float(os.getenv("AMC_W_TECH","0.10")),
        "sector": float(os.getenv("AMC_W_SECTOR","0.05")),
      },
      "INTRADAY": int(os.getenv("AMC_INTRADAY","0")),
      "LOOKBACK_DAYS": int(os.getenv("LOOKBACK_DAYS","60")),
      "R_MULT": float(os.getenv("AMC_R_MULT","2.0")),
      "ATR_STOP_MULT": float(os.getenv("AMC_ATR_STOP_MULT","1.5")),
      "MIN_STOP_PCT": float(os.getenv("AMC_MIN_STOP_PCT","0.02")),
    }
    return env

@router.get("/audit")
async def discovery_audit():
    """Returns list of candidates with factors, score, thesis"""
    try:
        r = get_redis_client()
        items = _get_json(r, V2_CONT) or _get_json(r, V1_CONT) or []
        result = []
        for item in items:
            if isinstance(item, dict):
                # Build stable frontend shape
                audit_item = {
                    "symbol": item.get("symbol"),
                    "price": item.get("price"),
                    "thesis": item.get("thesis"),
                    "score": item.get("score", 0),
                    "confidence": item.get("confidence") or (item.get("score", 0) / 100.0),
                    "factors": item.get("factors", {}),
                    "weights_used": {
                        "volume": float(os.getenv("AMC_W_VOLUME", "0.25")),
                        "short": float(os.getenv("AMC_W_SHORT", "0.20")),
                        "catalyst": float(os.getenv("AMC_W_CATALYST", "0.20")),
                        "sent": float(os.getenv("AMC_W_SENT", "0.15")),
                        "options": float(os.getenv("AMC_W_OPTIONS", "0.10")),
                        "tech": float(os.getenv("AMC_W_TECH", "0.10")),
                        "sector": float(os.getenv("AMC_W_SECTOR", "0.05"))
                    }
                }
                result.append(audit_item)
        return result
    except Exception:
        return []

@router.get("/audit/{symbol}")
async def discovery_audit_symbol(symbol: str):
    """Returns single full record including factors and latest trace slice"""
    try:
        r = get_redis_client()
        items = _get_json(r, V2_CONT) or _get_json(r, V1_CONT) or []
        
        # Find the symbol
        item = None
        for i in items:
            if isinstance(i, dict) and i.get("symbol") == symbol:
                item = i
                break
        
        if not item:
            return {
                "symbol": symbol, 
                "price": None,
                "thesis": None,
                "score": 0,
                "confidence": 0.0,
                "factors": {}, 
                "weights_used": {}
            }
        
        # Build stable frontend shape with full record
        result = {
            "symbol": symbol,
            "price": item.get("price"),
            "thesis": item.get("thesis"),
            "score": item.get("score", 0),
            "confidence": item.get("confidence") or (item.get("score", 0) / 100.0),
            "factors": item.get("factors", {}),
            "weights_used": {
                "volume": float(os.getenv("AMC_W_VOLUME", "0.25")),
                "short": float(os.getenv("AMC_W_SHORT", "0.20")),
                "catalyst": float(os.getenv("AMC_W_CATALYST", "0.20")),
                "sent": float(os.getenv("AMC_W_SENT", "0.15")),
                "options": float(os.getenv("AMC_W_OPTIONS", "0.10")),
                "tech": float(os.getenv("AMC_W_TECH", "0.10")),
                "sector": float(os.getenv("AMC_W_SECTOR", "0.05"))
            }
        }
        
        # Add latest trace slice if available
        trace = _get_json(r, V2_TRACE) or _get_json(r, V1_TRACE)
        if trace:
            result["trace"] = trace
            
        return result
    except Exception:
        return {
            "symbol": symbol, 
            "price": None,
            "thesis": None,
            "score": 0,
            "confidence": 0.0,
            "factors": {}, 
            "weights_used": {}
        }

@router.get("/test")
async def discovery_test(
    request: Request,
    relaxed: bool = Query(True), 
    limit: int = Query(10), 
    strategy: str = Query("", description="Scoring strategy to test"),
    session: str = Query("regular", description="Market session for testing")
):
    # Restrict test endpoint to development environment only
    import os
    if os.getenv("ENVIRONMENT", "development") not in ["development", "dev", "local"]:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=403, 
            detail="Test endpoint restricted to development environment only"
        )
    f, mod = _load_selector()
    if not f:
        return {"items": [], "trace": {}, "error": "select_candidates not found in src.jobs.discovery or src.jobs.discover"}
    try:
        # Resolve effective strategy (production enforcement)
        effective_strategy = resolve_effective_strategy(strategy)
        
        # Temporarily override strategy for testing
        original_strategy = os.getenv("SCORING_STRATEGY")
        os.environ["SCORING_STRATEGY"] = effective_strategy
        
        try:
            res = await f(relaxed=relaxed, limit=limit, with_trace=True)  # type: ignore
            if isinstance(res, tuple) and len(res) == 2:
                items, trace = res
            else:
                items, trace = res, {}
            
            return {
                "items": items, 
                "trace": trace, 
                "module": mod, 
                "relaxed": relaxed, 
                "limit": limit,
                "strategy": effective_strategy,
                "requested_strategy": strategy,
                "effective_strategy": effective_strategy
            }
        finally:
            # Restore original strategy
            if original_strategy:
                os.environ["SCORING_STRATEGY"] = original_strategy
            elif strategy:
                # Remove the temporary override
                os.environ.pop("SCORING_STRATEGY", None)
    except Exception as e:
        return {"items": [], "trace": {}, "module": mod, "error": str(e)}

@router.get("/squeeze-candidates")
async def get_squeeze_candidates(min_score: float = Query(0.25, ge=0.0, le=1.0)):
    """
    VIGL Squeeze Pattern Detection Endpoint
    
    Returns only stocks with squeeze_score > min_score threshold
    Designed to identify explosive opportunities like VIGL (+324%)
    
    Args:
        min_score: Minimum squeeze score (0.0-1.0), default 0.25 for maximum candidates
        
    Returns:
        List of high-confidence squeeze candidates with detailed analysis
    """
    try:
        r = get_redis_client()
        
        # Get current discovery contenders
        items = _get_json(r, V2_CONT) or _get_json(r, V1_CONT) or []
        
        squeeze_candidates = []
        squeeze_detector = SqueezeDetector()
        
        for item in items:
            if not isinstance(item, dict):
                continue
                
            symbol = item.get("symbol")
            if not symbol:
                continue
            
            # Extract data for squeeze detection
            # Fix data mapping - calculate missing values from available data
            price = item.get('price', 0.0)
            dollar_volume = item.get('dollar_vol', 0.0)
            
            # Calculate share volume from dollar volume and price
            current_volume = dollar_volume / price if price > 0 else 0.0
            volume_spike_ratio = item.get('volume_spike', 1.0)
            
            # Reverse calculate avg_volume_30d from current volume and spike ratio
            if volume_spike_ratio and volume_spike_ratio > 0 and current_volume > 0:
                calculated_avg_volume = max(current_volume / volume_spike_ratio, 100000)
            else:
                # Skip symbols without sufficient volume data
                logger.debug(f"Excluding {symbol} - insufficient volume history")
                continue
            
            squeeze_data = {
                'symbol': symbol,
                'price': item.get('price', 0.0),
                'volume': current_volume,
                'avg_volume_30d': calculated_avg_volume,  # Calculated from spike ratio
                # NO DEFAULTS - Skip stocks without real market data
                'short_interest': None,  # Must have real short interest data
                'float': None,          # Must have real float data
                'borrow_rate': None,    # Must have real borrow rate data
                'shares_outstanding': None,  # Must have real shares outstanding data
                # Market cap based on enhanced tight float estimate
                'market_cap': item.get('price', 0.0) * 15_000_000  # Using tighter float
            }
            
            # Detect squeeze pattern
            squeeze_result = squeeze_detector.detect_vigl_pattern(symbol, squeeze_data)
            
            if squeeze_result and squeeze_result.squeeze_score >= min_score:
                # Build enhanced candidate record
                candidate = {
                    'symbol': symbol,
                    'price': squeeze_result.price,
                    'squeeze_score': squeeze_result.squeeze_score,
                    'squeeze_pattern': squeeze_result.pattern_match,
                    'confidence': squeeze_result.confidence,
                    'volume_spike': squeeze_result.volume_spike,
                    'short_interest': squeeze_result.short_interest * 100,  # Convert to percentage
                    'float_shares': squeeze_result.float_shares,
                    'borrow_rate': squeeze_result.borrow_rate * 100,  # Convert to percentage
                    'thesis': squeeze_result.thesis,
                    
                    # Preserve original discovery data
                    'original_score': item.get('score', 0.0),
                    'original_reason': item.get('reason', ''),
                    'factors': item.get('factors', {}),
                    
                    # Add VIGL classification
                    'is_vigl_class': squeeze_result.squeeze_score >= 0.85,
                    'is_high_confidence': squeeze_result.squeeze_score >= 0.75,
                    'explosive_potential': 'EXTREME' if squeeze_result.squeeze_score >= 0.85 else 'HIGH'
                }
                
                squeeze_candidates.append(candidate)
        
        # Sort by squeeze score descending (best first)
        squeeze_candidates.sort(key=lambda x: x['squeeze_score'], reverse=True)
        
        # Add metadata
        response = {
            'candidates': squeeze_candidates,
            'count': len(squeeze_candidates),
            'min_score_threshold': min_score,
            'vigl_class_count': len([c for c in squeeze_candidates if c['is_vigl_class']]),
            'high_confidence_count': len([c for c in squeeze_candidates if c['is_high_confidence']]),
            'avg_squeeze_score': round(sum(c['squeeze_score'] for c in squeeze_candidates) / len(squeeze_candidates), 3) if squeeze_candidates else 0.0,
            'squeeze_weights': {
                'volume_surge': 40,  # 40% weight
                'short_interest': 30,  # 30% weight 
                'float_tightness': 20,  # 20% weight
                'borrow_pressure': 10   # 10% weight
            },
            'criteria': {
                'price_range': '$2.00 - $10.00',
                'volume_min': '10x average',
                'volume_target': '20.9x (VIGL level)',
                'float_max': '50M shares',
                'short_interest_min': '20%',
                'market_cap_max': '$500M'
            }
        }
        
        return response
        
    except Exception as e:
        return {
            'candidates': [],
            'count': 0,
            'error': str(e),
            'min_score_threshold': min_score
        }

@router.post("/purge-cache")
async def purge_contaminated_cache():
    """
    EMERGENCY CACHE PURGE: Clear all contaminated discovery data
    Forces system to return empty results until fresh data is available
    """
    try:
        r = get_redis_client()
        
        # Clear all discovery cache keys
        keys_to_clear = [V2_CONT, V2_TRACE, V1_CONT, V1_TRACE, STATUS]
        cleared_keys = []
        
        for key in keys_to_clear:
            if r.exists(key):
                r.delete(key)
                cleared_keys.append(key)
        
        logger.info(f"🧹 CACHE PURGED: Cleared {len(cleared_keys)} contaminated cache keys")
        
        return {
            "success": True,
            "message": "Contaminated cache purged successfully",
            "keys_cleared": cleared_keys,
            "note": "System will now return empty results until fresh discovery data is generated"
        }
        
    except Exception as e:
        logger.error(f"Failed to purge cache: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/trigger")
async def trigger_discovery(
    request: Request,
    limit: int = Query(10), 
    relaxed: bool = Query(False), 
    strategy: str = Query("", description="Strategy to use for discovery")
):
    """
    Manual discovery trigger for production deployment
    
    Runs discovery job and populates Redis with fresh market data
    """
    try:
        import asyncio
        from backend.src.shared.redis_client import get_redis_client
        import json
        import time
        
        start_time = time.time()
        
        # Load and run discovery
        f, mod = _load_selector()
        if not f:
            return {"success": False, "error": "select_candidates not found"}
        
        # Resolve effective strategy (production enforcement)
        effective_strategy = resolve_effective_strategy(strategy)
        
        # Temporarily override strategy for discovery
        original_strategy = os.getenv("SCORING_STRATEGY")
        os.environ["SCORING_STRATEGY"] = effective_strategy
        
        try:
            # Run discovery with trace
            res = await f(relaxed=relaxed, limit=limit, with_trace=True)
            if isinstance(res, tuple) and len(res) == 2:
                items, trace = res
            else:
                items, trace = res, {}
        finally:
            # Restore original strategy
            if original_strategy:
                os.environ["SCORING_STRATEGY"] = original_strategy
            elif strategy:
                os.environ.pop("SCORING_STRATEGY", None)
        
        # Publish to Redis with strategy-aware keys
        r = get_redis_client()
        strategy_suffix = f":{effective_strategy}" if effective_strategy and effective_strategy in ["legacy_v0", "hybrid_v1"] else ""
        
        # Store with strategy-specific keys AND fallback keys for backward compatibility
        r.set(f"{V1_CONT}{strategy_suffix}", json.dumps(items), ex=600)
        r.set(f"{V2_CONT}{strategy_suffix}", json.dumps(items), ex=600)
        r.set(V1_CONT, json.dumps(items), ex=600)  # Fallback
        r.set(V2_CONT, json.dumps(items), ex=600)  # Fallback
        
        # Store trace data for diagnostics
        trace_data = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "count": len(items),
            "total_stocks": trace.get("total_stocks", 0),
            "initial_count": trace.get("initial_universe", 0),
            "price_filtered": trace.get("after_price_filter", 0),
            "volume_filtered": trace.get("after_volume_filter", 0),
            "momentum_filtered": trace.get("after_momentum_filter", 0),
            "pattern_matched": trace.get("after_pattern_matching", 0),
            "confidence_filtered": trace.get("after_confidence_filter", 0),
            "min_price": 1.0,
            "max_price": 100.0,
            "min_volume": 1000000,
            "min_confidence": 0.75,
            "min_score": 50,
            "stages": trace.get("stages", [])
        }
        r.set(f"{V1_TRACE}{strategy_suffix}", json.dumps(trace_data), ex=600)
        r.set(V1_TRACE, json.dumps(trace_data), ex=600)  # Fallback
        
        # MONITORING INTEGRATION - Zero disruption monitoring
        try:
            from ..services.discovery_monitor import get_discovery_monitor
            from ..services.recommendation_tracker import get_recommendation_tracker
            
            # Track discovery pipeline flow (non-blocking)
            monitor = get_discovery_monitor()
            flow_stats = await monitor.track_discovery_run(trace, items)
            
            # Track all recommendations for learning (non-blocking)
            tracker = get_recommendation_tracker()
            for item in items:
                if isinstance(item, dict) and item.get('symbol'):
                    await tracker.save_recommendation(item, from_portfolio=False)
                    
        except Exception as monitor_error:
            # Monitoring errors don't break discovery - just log them
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Discovery monitoring error (non-critical): {monitor_error}")
        # END MONITORING INTEGRATION
        r.set(f"{V2_TRACE}{strategy_suffix}", json.dumps(trace_data), ex=600)
        r.set(V2_TRACE, json.dumps(trace_data), ex=600)  # Fallback
        
        # Store status for diagnostics
        status_data = {
            "last_run": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": "completed",
            "total_stocks_scanned": trace.get("total_stocks", 0),
            "candidates_found": len(items),
            "processing_time": f"{time.time() - start_time:.2f}s",
            "error": None
        }
        r.set(STATUS, json.dumps(status_data), ex=600)
        
        return {
            "success": True,
            "candidates_found": len(items),
            "published_to_redis": True,
            "module": mod,
            "strategy": effective_strategy,
            "requested_strategy": strategy,
            "effective_strategy": effective_strategy,
            "trace": trace
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/strategy-validation")
async def validate_strategy_scoring():
    """
    Validate hybrid_v1 strategy against legacy_v0 strategy
    
    Returns comparison metrics and sample scoring for validation
    """
    try:
        # Test both strategies on the same candidate set
        f, mod = _load_selector()
        if not f:
            return {"validation_complete": False, "error": "select_candidates not found"}
        
        results = {
            "validation_complete": True,
            "strategies": {},
            "comparison": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Test each strategy
        for strategy in ["legacy_v0", "hybrid_v1"]:
            original_strategy = os.getenv("SCORING_STRATEGY")
            os.environ["SCORING_STRATEGY"] = strategy
            
            try:
                res = await f(relaxed=True, limit=10, with_trace=True)
                if isinstance(res, tuple) and len(res) == 2:
                    items, trace = res
                else:
                    items, trace = res, {}
                
                results["strategies"][strategy] = {
                    "candidates_found": len(items),
                    "sample_candidates": [
                        {
                            "symbol": item.get("symbol"),
                            "score": item.get("score"),
                            "strategy": item.get("strategy"),
                            "action_tag": item.get("action_tag"),
                            "pattern_match": item.get("pattern_match"),
                            "reason": item.get("reason")
                        } for item in items[:3]
                    ],
                    "avg_score": sum(item.get("score", 0) for item in items) / len(items) if items else 0,
                    "trace_summary": {
                        "initial_universe": trace.get("counts_in", {}).get("universe", 0),
                        "final_candidates": len(items)
                    }
                }
                
            finally:
                if original_strategy:
                    os.environ["SCORING_STRATEGY"] = original_strategy
                else:
                    os.environ.pop("SCORING_STRATEGY", None)
        
        # Generate comparison metrics
        legacy_count = results["strategies"].get("legacy_v0", {}).get("candidates_found", 0)
        hybrid_count = results["strategies"].get("hybrid_v1", {}).get("candidates_found", 0)
        
        results["comparison"] = {
            "candidate_count_diff": hybrid_count - legacy_count,
            "legacy_avg_score": results["strategies"].get("legacy_v0", {}).get("avg_score", 0),
            "hybrid_avg_score": results["strategies"].get("hybrid_v1", {}).get("avg_score", 0),
            "strategy_working": legacy_count > 0 and hybrid_count > 0
        }
        
        return results
        
    except Exception as e:
        return {
            "validation_complete": False,
            "error": str(e)
        }

@router.get("/squeeze-validation")
async def validate_squeeze_detector():
    """
    Validate SqueezeDetector against historical winners
    
    Returns validation results for VIGL, CRWV, AEVA patterns
    """
    try:
        detector = SqueezeDetector()
        validation_result = detector.validate_historical_winners()
        
        # Add current detector configuration
        validation_result['current_config'] = {
            'vigl_criteria': detector.VIGL_CRITERIA,
            'confidence_levels': detector.CONFIDENCE_LEVELS,
            'algorithm_version': 'v1.0_vigl_restoration'
        }
        
        return validation_result
        
    except Exception as e:
        return {
            'validation_complete': False,
            'error': str(e)
        }

@router.patch("/calibration/hybrid_v1/preset")
async def set_preset(name: str = Query(..., description="Preset name to activate")):
    """
    One-click preset switching for hybrid_v1 strategy
    
    Available presets: squeeze_aggressive, catalyst_heavy, balanced_default
    """
    try:
        config = _load_calibration_config()
        presets = config.get("scoring", {}).get("presets", {})
        
        if name not in presets:
            available = list(presets.keys())
            raise HTTPException(
                status_code=400, 
                detail=f"Unknown preset '{name}'. Available: {available}"
            )
        
        # Update preset in config
        config["scoring"]["preset"] = name
        
        if not _save_calibration_config(config):
            raise HTTPException(status_code=500, detail="Failed to save configuration")
        
        # Invalidate cache
        _invalidate_redis_cache()
        
        # Get resolved weights for response
        preset_weights = presets[name].get("weights", {})
        base_weights = config.get("scoring", {}).get("hybrid_v1", {}).get("weights", {})
        resolved_weights = _normalize_weights({**base_weights, **preset_weights})
        
        return {
            "success": True,
            "preset": name,
            "resolved_weights": resolved_weights,
            "cache_invalidated": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preset switch failed: {str(e)}")

@router.patch("/calibration/hybrid_v1")
async def update_calibration(request_body: Dict = Body(...)):
    """
    Update hybrid_v1 thresholds and/or weights
    
    Pass {"thresholds": {...}} to update thresholds
    Pass {"weights": {...}} to update weights (will be normalized)
    """
    try:
        config = _load_calibration_config()
        thresholds = request_body.get("thresholds")
        weights = request_body.get("weights")
        
        if thresholds:
            # Update thresholds
            current_thresholds = config.get("scoring", {}).get("hybrid_v1", {}).get("thresholds", {})
            updated_thresholds = {**current_thresholds, **thresholds}
            config["scoring"]["hybrid_v1"]["thresholds"] = updated_thresholds
        
        if weights:
            # Update and normalize weights
            current_weights = config.get("scoring", {}).get("hybrid_v1", {}).get("weights", {})
            updated_weights = {**current_weights, **weights}
            normalized_weights = _normalize_weights(updated_weights)
            config["scoring"]["hybrid_v1"]["weights"] = normalized_weights
            config["scoring"]["preset"] = None  # Clear preset when using explicit weights
        
        if not _save_calibration_config(config):
            raise HTTPException(status_code=500, detail="Failed to save configuration")
        
        # Invalidate cache
        _invalidate_redis_cache()
        
        return {
            "success": True,
            "thresholds_updated": thresholds is not None,
            "weights_updated": weights is not None,
            "cache_invalidated": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Configuration update failed: {str(e)}")

# Alias endpoint - maps to same handler
@router.patch("/discovery/calibration/hybrid_v1")
async def update_calibration_alias(request_body: Dict = Body(...)):
    """Alias for /calibration/hybrid_v1 to prevent 404s"""
    return await update_calibration(request_body)

@router.patch("/calibration/hybrid_v1/weights")
async def set_weights(weights: WeightsUpdate):
    """
    Live weight tuning for hybrid_v1 strategy (legacy endpoint)
    
    Updates weights and normalizes to sum to 1.0. Overrides preset.
    """
    try:
        config = _load_calibration_config()
        
        # Get current hybrid_v1 weights
        current_weights = config.get("scoring", {}).get("hybrid_v1", {}).get("weights", {})
        
        # Update with provided weights (skip None values)
        update_data = weights.dict(exclude_unset=True, exclude_none=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No weights provided for update")
        
        updated_weights = {**current_weights, **update_data}
        normalized_weights = _normalize_weights(updated_weights)
        
        # Apply updates
        config["scoring"]["hybrid_v1"]["weights"] = normalized_weights
        config["scoring"]["preset"] = None  # Clear preset when using explicit weights
        
        if not _save_calibration_config(config):
            raise HTTPException(status_code=500, detail="Failed to save configuration")
        
        # Invalidate cache
        _invalidate_redis_cache()
        
        return {
            "success": True,
            "weights": normalized_weights,
            "preset_cleared": True,
            "cache_invalidated": True,
            "changes": update_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Weight update failed: {str(e)}")

@router.get("/calibration/hybrid_v1/config")
async def get_current_config():
    """
    Get current hybrid_v1 configuration including resolved weights
    """
    try:
        config = _load_calibration_config()
        scoring_config = config.get("scoring", {})
        hybrid_config = scoring_config.get("hybrid_v1", {})
        
        # Resolve weights with preset overlay
        base_weights = hybrid_config.get("weights", {})
        preset_name = scoring_config.get("preset")
        presets = scoring_config.get("presets", {})
        
        if preset_name and preset_name in presets:
            preset_weights = presets[preset_name].get("weights", {})
            resolved_weights = _normalize_weights({**base_weights, **preset_weights})
        else:
            resolved_weights = _normalize_weights(base_weights)
        
        return {
            "strategy": scoring_config.get("strategy", "legacy_v0"),
            "active_preset": preset_name,
            "available_presets": list(presets.keys()),
            "base_weights": base_weights,
            "resolved_weights": resolved_weights,
            "thresholds": hybrid_config.get("thresholds", {}),
            "entry_rules": hybrid_config.get("entry_rules", {}),
            "weights_hash": hash(frozenset(resolved_weights.items())),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Config retrieval failed: {str(e)}")

@router.post("/calibration/hybrid_v1/reset") 
async def reset_to_defaults():
    """
    Reset hybrid_v1 configuration to balanced_default preset
    """
    try:
        config = _load_calibration_config()
        
        # Reset to balanced_default
        config["scoring"]["preset"] = "balanced_default"
        
        if not _save_calibration_config(config):
            raise HTTPException(status_code=500, detail="Failed to save configuration")
        
        # Invalidate cache
        _invalidate_redis_cache()
        
        return {
            "success": True,
            "reset_to": "balanced_default",
            "cache_invalidated": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")

@router.post("/calibration/emergency/force-legacy")
async def emergency_force_legacy():
    """
    EMERGENCY: Force legacy_v0 strategy for 15 minutes
    
    Use this if hybrid_v1 is causing issues in production
    """
    try:
        # Set emergency override environment variable
        os.environ["SCORING_STRATEGY"] = "legacy_v0"
        os.environ["EMERGENCY_OVERRIDE"] = str(int(datetime.now(timezone.utc).timestamp() + 900))  # 15 minutes
        
        # Invalidate cache
        _invalidate_redis_cache()
        
        logger.warning("🚨 EMERGENCY: Forced legacy_v0 strategy for 15 minutes")
        
        return {
            "success": True,
            "strategy_forced": "legacy_v0",
            "expires_at": datetime.fromtimestamp(int(os.environ["EMERGENCY_OVERRIDE"]), timezone.utc).isoformat(),
            "duration_minutes": 15,
            "cache_invalidated": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Emergency override failed: {str(e)}")

@router.get("/calibration/status")
async def get_calibration_status():
    """
    Get comprehensive calibration and system status
    """
    try:
        config = _load_calibration_config()
        
        # Check for emergency override
        emergency_override = os.getenv("EMERGENCY_OVERRIDE")
        emergency_active = False
        emergency_expires = None
        
        if emergency_override:
            try:
                expire_time = int(emergency_override)
                if datetime.now(timezone.utc).timestamp() < expire_time:
                    emergency_active = True
                    emergency_expires = datetime.fromtimestamp(expire_time, timezone.utc).isoformat()
                else:
                    # Clean up expired override
                    os.environ.pop("EMERGENCY_OVERRIDE", None)
            except:
                pass
        
        # Get Redis cache status
        cache_status = {}
        try:
            r = get_redis_client()
            cache_keys = [
                "amc:discovery:v2:contenders.latest",
                "amc:discovery:v2:contenders.latest:hybrid_v1",
                "amc:discovery:v2:contenders.latest:legacy_v0"
            ]
            for key in cache_keys:
                cache_status[key] = r.exists(key)
        except:
            cache_status = {"error": "Redis unavailable"}
        
        # Calculate weights and thresholds hashes
        weights = config.get("scoring", {}).get("hybrid_v1", {}).get("weights", {})
        weights_hash = hash(frozenset(weights.items())) if weights else None
        
        thresholds = config.get("scoring", {}).get("hybrid_v1", {}).get("thresholds", {})
        # Create a simplified thresholds snapshot without nested objects
        thresholds_snapshot = {
            "min_relvol_30": thresholds.get("min_relvol_30"),
            "min_atr_pct": thresholds.get("min_atr_pct"),
            "require_vwap_reclaim": thresholds.get("require_vwap_reclaim"),
            "vwap_proximity_pct": thresholds.get("vwap_proximity_pct", 0.0),
            "max_soft_pass": thresholds.get("max_soft_pass", 0),
            "mid_float_enabled": thresholds.get("mid_float_path", {}).get("enabled", False),
            "session_overrides_enabled": {
                "premarket": thresholds.get("session_overrides", {}).get("premarket", {}).get("enabled", False),
                "afterhours": thresholds.get("session_overrides", {}).get("afterhours", {}).get("enabled", False),
                "regular": thresholds.get("session_overrides", {}).get("regular", {}).get("enabled", False)
            }
        }
        
        # Get strategy metadata
        strategy_meta = get_strategy_metadata()
        
        return {
            "effective_strategy": strategy_meta["effective_strategy"],
            "preset": config.get("scoring", {}).get("preset"),
            "weights_hash": weights_hash,
            "thresholds_snapshot": thresholds_snapshot,
            "emergency_flag": strategy_meta["emergency_active"],
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "strategy_resolution": {
                "force_strategy": strategy_meta["force_strategy"],
                "allow_override": strategy_meta["allow_override"],
                "env_strategy": strategy_meta["env_strategy"],
                "emergency_expires": strategy_meta["emergency_expires"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@router.post("/calibration/hybrid_v1/limit")
async def set_safety_limits(max_candidates: int = Query(100, ge=1, le=500), max_latency_ms: int = Query(15000, ge=1000, le=60000)):
    """
    Update safety guardrails for hybrid_v1 strategy
    """
    try:
        config = _load_calibration_config()
        
        # Update safety limits
        if "safety_guardrails" not in config.get("scoring", {}).get("hybrid_v1", {}):
            config["scoring"]["hybrid_v1"]["safety_guardrails"] = {}
        
        config["scoring"]["hybrid_v1"]["safety_guardrails"]["max_candidates"] = max_candidates
        config["scoring"]["hybrid_v1"]["safety_guardrails"]["max_latency_ms"] = max_latency_ms
        
        if not _save_calibration_config(config):
            raise HTTPException(status_code=500, detail="Failed to save configuration")
        
        return {
            "success": True,
            "limits_updated": {
                "max_candidates": max_candidates,
                "max_latency_ms": max_latency_ms
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Safety limit update failed: {str(e)}")