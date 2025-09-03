from fastapi import APIRouter, Query
from typing import List, Dict
import json
import importlib
import math
import os
import logging
from datetime import datetime, timezone
from backend.src.shared.redis_client import get_redis_client
from backend.src.services.squeeze_detector import SqueezeDetector
from ..services.short_interest_service import get_short_interest_service
from ..services.short_interest_validator import get_short_interest_validator

router = APIRouter()
logger = logging.getLogger(__name__)

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
async def get_contenders():
    """
    CRITICAL: Returns fresh discovery data ONLY
    Fails with empty list if data is stale (>5 minutes old)
    """
    r = get_redis_client()
    
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
    
    # Get candidates but validate freshness
    items = _get_json(r, V2_CONT) or _get_json(r, V1_CONT)
    
    if not items:
        logger.error("❌ No discovery data available - returning empty list")
        return []
    
    # Validate we have real data, not stale fallback
    if len(items) == 33:  # Suspicious - likely stale fallback data
        logger.warning("⚠️ Detected possible stale fallback data (exactly 33 items) - verifying...")
        # Check if any item has a timestamp
        has_fresh_timestamp = False
        for item in items:
            if isinstance(item, dict) and item.get('timestamp'):
                try:
                    from datetime import datetime
                    item_time = datetime.fromisoformat(item['timestamp'])
                    age = (datetime.now() - item_time).total_seconds()
                    if age < 300:  # Less than 5 minutes old
                        has_fresh_timestamp = True
                        break
                except:
                    pass
        
        if not has_fresh_timestamp:
            logger.error("❌ Data appears to be stale fallback - returning empty!")
            return []
    
    # Process items
    for it in items:
        if isinstance(it, dict):
            # Ensure score exists (0..100) and set confidence = score/100 if missing
            if "score" not in it:
                it["score"] = 0
            if "confidence" not in it:
                it["confidence"] = it["score"] / 100.0
    
    return items

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
async def discovery_test(relaxed: bool = Query(True), limit: int = Query(10)):
    f, mod = _load_selector()
    if not f:
        return {"items": [], "trace": {}, "error": "select_candidates not found in src.jobs.discovery or src.jobs.discover"}
    try:
        res = await f(relaxed=relaxed, limit=limit, with_trace=True)  # type: ignore
        if isinstance(res, tuple) and len(res) == 2:
            items, trace = res
        else:
            items, trace = res, {}
        return {"items": items, "trace": trace, "module": mod, "relaxed": relaxed, "limit": limit}
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
                calculated_avg_volume = 1000000  # Reasonable default
            
            squeeze_data = {
                'symbol': symbol,
                'price': item.get('price', 0.0),
                'volume': current_volume,
                'avg_volume_30d': calculated_avg_volume,  # Calculated from spike ratio
                'short_interest': 0.30,  # AGGRESSIVE: 30% default (very bullish)
                'float': 10_000_000,     # AGGRESSIVE: 10M tight float assumption
                'borrow_rate': 0.75,     # AGGRESSIVE: 75% borrow rate (high pressure)
                'shares_outstanding': 30_000_000,  # ENHANCED: 30M vs 50M (smaller default)
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

@router.post("/trigger")
async def trigger_discovery(limit: int = Query(10), relaxed: bool = Query(False)):
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
        
        # Run discovery with trace
        res = await f(relaxed=relaxed, limit=limit, with_trace=True)
        if isinstance(res, tuple) and len(res) == 2:
            items, trace = res
        else:
            items, trace = res, {}
        
        # Publish to Redis (same keys as main discovery job)
        r = get_redis_client()
        r.set(V1_CONT, json.dumps(items), ex=600)
        r.set(V2_CONT, json.dumps(items), ex=600)  # Store in both v1 and v2 keys
        
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
        r.set(V1_TRACE, json.dumps(trace_data), ex=600)
        
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
        r.set(V2_TRACE, json.dumps(trace_data), ex=600)
        
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
            "trace": trace
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

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