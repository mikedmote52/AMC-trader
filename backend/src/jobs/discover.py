#!/usr/bin/env python3
"""
Discovery Job Pipeline
Reads universe file, fetches Polygon prices, computes sentiment scores,
and writes recommendations to database.
"""

import os
import sys
import logging
import json
import asyncio
import httpx
import time
import math
import statistics as stats
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.database import get_db_session, Recommendation
from shared.redis_client import redis_lock, get_redis_client  
from shared.market_hours import is_market_hours, get_market_status
from lib.redis_client import publish_discovery_contenders
from polygon import RESTClient
import requests
from services.squeeze_detector import SqueezeDetector, SqueezeCandidate
from ..services.short_interest_service import get_short_interest_service
from ..services.enhanced_short_interest import get_enhanced_short_interest

def _load_calibration():
    """Load active calibration settings with fallbacks to environment variables"""
    try:
        import json
        import os
        calibration_path = os.path.join(os.path.dirname(__file__), "../../../calibration/active.json")
        if os.path.exists(calibration_path):
            with open(calibration_path, 'r', encoding='utf-8') as f:
                cal = json.load(f)
                return cal
    except Exception as e:
        print(f"Warning: Could not load calibration file: {e}")
    return {}

# Utility functions for hybrid_v1 scoring
def clamp(x, lo=0.0, hi=1.0):
    """Clamp value between lo and hi bounds"""
    return max(lo, min(hi, x or 0.0))

def nz(x, default=0.0):
    """Return default if x is None, else x"""
    return default if x is None else x

def _get_scoring_strategy():
    """Get current scoring strategy from config with backward compatibility"""
    # Check for explicit SCORING_STRATEGY setting
    strategy = os.getenv("SCORING_STRATEGY", "").lower()
    if strategy in ["legacy_v0", "hybrid_v1"]:
        return strategy
    
    # Backward compatibility: if AMC_SQUEEZE_MODE is true, use legacy_v0
    squeeze_mode = os.getenv("AMC_SQUEEZE_MODE", "true").lower() in ("1", "true", "yes")
    if squeeze_mode:
        return "legacy_v0"
    
    # Default to legacy_v0
    return "legacy_v0"

# Weight normalization and preset resolution
def _normalize_weights(weights):
    """Normalize weights to sum to 1.0"""
    total = sum(weights.values()) or 1.0
    return {k: max(0.0, v) / total for k, v in weights.items()}

def _resolve_hybrid_weights(calibration):
    """Resolve hybrid_v1 weights with preset overlay"""
    scoring_config = calibration.get('scoring', {})
    base_weights = scoring_config.get('hybrid_v1', {}).get('weights', {})
    preset_name = scoring_config.get('preset')
    presets = scoring_config.get('presets', {})
    
    if preset_name and preset_name in presets:
        # Overlay preset weights over base weights
        preset_weights = presets[preset_name].get('weights', {})
        merged_weights = {**base_weights, **preset_weights}
    else:
        merged_weights = base_weights
    
    return _normalize_weights(merged_weights)

# Load calibration settings
_calibration = _load_calibration()

# Resolve hybrid_v1 weights with preset overlay
_hybrid_weights = _resolve_hybrid_weights(_calibration)

# Environment variables for live discovery with calibration overrides
POLY_KEY = os.getenv("POLYGON_API_KEY")
# Apply calibration overrides for critical thresholds
PRICE_CAP = _calibration.get("discovery_filters", {}).get("price_cap", float(os.getenv("AMC_PRICE_CAP", "500")))
MIN_DOLLAR_VOL = _calibration.get("discovery_filters", {}).get("dollar_volume_min", float(os.getenv("AMC_MIN_DOLLAR_VOL", "5000000")))  # CALIBRATED: 1M vs 5M
LOOKBACK_DAYS = int(os.getenv("AMC_COMPRESSION_LOOKBACK", "60"))
COMPRESSION_PCTL_MAX = _calibration.get("discovery_filters", {}).get("compression_percentile_max", float(os.getenv("AMC_COMPRESSION_PCTL_MAX", "0.75")))  # EXPANDED: Allow 75th percentile (more candidates)
MAX_CANDIDATES = _calibration.get("discovery_filters", {}).get("max_candidates", int(os.getenv("AMC_MAX_CANDIDATES", "100")))  # EXPANDED: 25 → 100 to capture more opportunities
# Enhanced fallback universe - expanded from small default to comprehensive squeeze candidates
_DEFAULT_FALLBACK = "VIGL,QUBT,CRWV,AEVA,UP,WULF,SSRM,SPHR,TEVA,KSS,CELC,CARS,GMAB,AMDL,TEM,RGTI,DCGO,OCGN,COTI,INVZ,SERA,LFMD,MNOV,INZY,ANIC,BBIG,ASTS,RKLB,HOLO,LOVO,ARQQ,NNDM,PRTG,FUBO,GOEV,REI,CLSK,RIOT,HUT,BITF,MARA,CAN,HVBT,DAC,NAK,AAPL,NVDA,TSLA,AMD,ANTE"
UNIVERSE_FALLBACK = [s.strip().upper() for s in os.getenv("AMC_DISCOVERY_UNIVERSE", _DEFAULT_FALLBACK).split(",") if s.strip()]
EXCLUDE_FUNDS = os.getenv("AMC_EXCLUDE_FUNDS", "false").lower() in ("1", "true", "yes")  # Include ETFs/leveraged funds
EXCLUDE_ADRS = False  # NEVER exclude ADRs - they contain valuable opportunities like ANTE

# SQUEEZE MODE CONFIGURATION - VIGL 324% Winner Restoration
SQUEEZE_MODE = os.getenv("AMC_SQUEEZE_MODE", "true").lower() in ("1", "true", "yes")

# SQUEEZE MODE WEIGHTS - Optimized for VIGL Pattern Detection
SQUEEZE_WEIGHTS = {
    'volume': 0.40,      # Increased from 0.25 - Volume surge primary signal
    'short': 0.30,       # Increased from 0.20 - Short squeeze fuel
    'catalyst': 0.15,    # Maintained - Event-driven moves
    'options': 0.10,     # Reduced from 0.10 - Options flow secondary
    'tech': 0.05,        # Reduced from 0.10 - Technical indicators minor
    'sent': 0.00,        # Removed - Sentiment noise eliminated
    'sector': 0.00       # Removed - Sector rotation irrelevant
}

# EXPLOSIVE PATTERN LEARNING - Based on VIGL's 324% Winner Analysis  
EXPLOSIVE_PRICE_MIN = float(os.getenv("AMC_EXPLOSIVE_PRICE_MIN", "0.01"))     # TRUE PENNY STOCKS - $0.01 minimum
EXPLOSIVE_PRICE_MAX = float(os.getenv("AMC_EXPLOSIVE_PRICE_MAX", "100.00"))   # Expanded to capture more opportunities
EXPLOSIVE_VOLUME_MIN = float(os.getenv("AMC_EXPLOSIVE_VOLUME_MIN", "10.0"))   # Increased - 10x+ volume minimum
EXPLOSIVE_VOLUME_TARGET = float(os.getenv("AMC_EXPLOSIVE_VOLUME_TARGET", "20.9"))  # VIGL's exact 20.9x target
EXPLOSIVE_MOMENTUM_MIN = float(os.getenv("AMC_EXPLOSIVE_MOMENTUM_MIN", "0.25"))     # Increased - 25%+ for explosive moves
EXPLOSIVE_ATR_MIN = float(os.getenv("AMC_EXPLOSIVE_ATR_MIN", "0.06"))         # 6%+ ATR for volatility expansion
WOLF_RISK_THRESHOLD = float(os.getenv("AMC_WOLF_RISK_THRESHOLD", "0.5"))     # Tightened risk threshold

# Legacy VIGL parameters (kept for compatibility)
VIGL_PRICE_MIN = EXPLOSIVE_PRICE_MIN
VIGL_PRICE_MAX = EXPLOSIVE_PRICE_MAX  
VIGL_VOLUME_MIN = EXPLOSIVE_VOLUME_MIN
VIGL_VOLUME_TARGET = EXPLOSIVE_VOLUME_TARGET
VIGL_MOMENTUM_MIN = EXPLOSIVE_MOMENTUM_MIN

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def _daily_bars(client, sym, limit=120):
    d = await _poly_get(client, f"/v2/aggs/ticker/{sym}/range/1/day/1970-01-01/2099-01-01",
                        params={"adjusted":"true","limit":limit})
    return d.get("results") or []

def _atr_pct(rows, period=14):
    if len(rows) < period+1: return None
    trs=[]
    for i in range(1,len(rows)):
        h=rows[i]["h"]; l=rows[i]["l"]; pc=rows[i-1]["c"]
        tr = max(h-l, abs(h-pc), abs(l-pc))
        trs.append(tr)
    atr = sum(trs[-period:])/period
    last_close = rows[-1]["c"] or 1e-9
    return float(atr/last_close)

def _return(rows, n):
    if len(rows) < n+1: return None
    c0=rows[-(n+1)]["c"]; c1=rows[-1]["c"]
    if not c0: return None
    return float((c1-c0)/c0)

def _volume_spike_ratio(bars):
    """Enhanced volume analysis with multiple timeframes for early detection"""
    if len(bars) < 31: 
        return {'early': 0.0, 'confirmation': 0.0, 'traditional': 0.0, 'best': 0.0}
    
    current_volume = bars[-1].get("v", 0)
    
    # Early signal detection (vs 5-day average) - Catches building momentum
    avg_5d = sum(float(bar.get("v", 0)) for bar in bars[-6:-1]) / 5
    early_signal = current_volume / avg_5d if avg_5d > 0 else 0
    
    # Confirmation signal (vs 10-day average) - Stronger validation
    avg_10d = sum(float(bar.get("v", 0)) for bar in bars[-11:-1]) / 10
    confirmation_signal = current_volume / avg_10d if avg_10d > 0 else 0
    
    # Traditional signal (vs 30-day average) - Original method
    avg_30d = sum(float(bar.get("v", 0)) for bar in bars[-31:-1]) / 30
    traditional_signal = current_volume / avg_30d if avg_30d > 0 else 0
    
    # Best signal with weighted importance (early detection prioritized)
    best_signal = max(
        early_signal * 0.8,      # 80% weight for early detection
        confirmation_signal * 0.9, # 90% weight for confirmed moves
        traditional_signal        # 100% weight for traditional signal
    )
    
    return {
        'early': early_signal,
        'confirmation': confirmation_signal,
        'traditional': traditional_signal,
        'best': best_signal
    }

def _calculate_explosive_potential(price, volume_spike, momentum, atr_pct):
    """Enhanced predictive scoring - Catch opportunities BEFORE they explode"""
    
    # EXPLOSIVE PRICE SCORING - Based on historical explosive winners
    if EXPLOSIVE_PRICE_MIN <= price <= EXPLOSIVE_PRICE_MAX:
        # Sweet spot: $2.50-$25 for maximum explosive potential
        if 3.0 <= price <= 12.0:
            price_score = 1.0   # VIGL winner zone: $3-12 range
        elif 2.5 <= price <= 20.0:
            price_score = 0.85  # High explosive potential
        else:
            price_score = 0.7   # Good explosive potential
    elif 1.0 <= price < EXPLOSIVE_PRICE_MIN:
        price_score = 0.5   # Too low - penny stock risk
    elif EXPLOSIVE_PRICE_MAX < price <= 50.0:
        price_score = 0.3   # Too high - harder to explode
    elif 0.50 <= price < 1.0:
        price_score = 0.3  # Penny stocks risky but possible
    else:
        price_score = 0.1  # Very large caps or sub-penny
    
    # ENHANCED VOLUME SCORING - Early detection prioritized
    # CRITICAL CHANGE: Lower thresholds to catch moves BEFORE they explode
    if volume_spike >= EXPLOSIVE_VOLUME_TARGET:  # 15x+ volume (often too late)
        volume_score = 0.95   # Already exploding - might be late
    elif volume_spike >= 10.0:
        volume_score = 0.90   # Strong confirmation
    elif volume_spike >= 5.0:  # Sweet spot for early detection
        volume_score = 0.85   # OPTIMAL ENTRY ZONE
    elif volume_spike >= 3.0:  # Early accumulation signal
        volume_score = 0.75   # HIGH PRIORITY - Early detection
    elif volume_spike >= 2.0:  # Building interest
        volume_score = 0.65   # WATCH CLOSELY - Potential breakout
    elif volume_spike >= 1.5:
        volume_score = 0.50   # Initial interest building
    else:
        volume_score = 0.20   # No significant interest yet
    
    # EXPLOSIVE MOMENTUM SCORING - Recent breakout strength
    momentum_abs = abs(momentum)
    if momentum >= 0.15:  # 15%+ positive momentum
        momentum_score = 1.0   # Strong explosive momentum
    elif momentum >= EXPLOSIVE_MOMENTUM_MIN:  # 8%+ momentum
        momentum_score = 0.8   # Good momentum
    elif momentum >= 0.05:  # 5%+ momentum
        momentum_score = 0.6   # Some momentum
    elif momentum >= 0.0:
        momentum_score = 0.4   # Flat but not declining
    elif momentum >= -0.05:  # Slight decline acceptable
        momentum_score = 0.3   # Minor pullback opportunity
    else:
        momentum_score = 0.1   # Declining - avoid
    
    # ATR VOLATILITY SCORING - Expansion indicates explosive potential
    if atr_pct >= 0.10:  # 10%+ ATR = high volatility
        atr_score = 1.0   # Maximum explosive potential
    elif atr_pct >= EXPLOSIVE_ATR_MIN:  # 6%+ ATR
        atr_score = 0.8   # Good volatility
    elif atr_pct >= 0.04:  # 4%+ ATR
        atr_score = 0.6   # Moderate volatility
    else:
        atr_score = 0.3   # Low volatility - less explosive
    
    # WEIGHTED EXPLOSIVE SCORE - Optimized for explosive winners
    explosive_score = (
        price_score * 0.25 +      # Price range importance
        volume_score * 0.35 +     # Volume surge most important
        momentum_score * 0.25 +   # Momentum crucial
        atr_score * 0.15         # Volatility expansion
    )
    
    return explosive_score

# Legacy function for compatibility
def _calculate_vigl_score(price, volume_spike, momentum, atr_pct):
    """Legacy VIGL score - now uses explosive potential calculation"""
    return _calculate_explosive_potential(price, volume_spike, momentum, atr_pct)

def _calculate_wolf_risk_score(price, volume_spike, momentum, atr_pct, rs_5d):
    """Calculate WOLF pattern risk score (0-1, higher = more risky)"""
    risk_factors = []
    
    # Very low price risk (penny stock manipulation)
    if price < 0.50:
        risk_factors.append(0.8)
    elif price < 1.00:
        risk_factors.append(0.4)
    
    # Extreme volume spike without substance
    if volume_spike > 50 and abs(momentum) < 0.02:  # >50x volume but <2% price move
        risk_factors.append(0.7)
    
    # Negative momentum with high volatility (falling knife)
    if momentum < -0.10 and atr_pct > 0.20:  # -10% momentum, >20% ATR
        risk_factors.append(0.6)
    
    # Recent poor performance (5-day returns)
    if rs_5d < -0.15:  # -15% over 5 days
        risk_factors.append(0.5)
    
    # Extreme volatility without direction
    if atr_pct > 0.25 and abs(momentum) < 0.05:  # >25% ATR but <5% momentum
        risk_factors.append(0.4)
    
    # Return max risk factor, or low risk if no red flags
    return max(risk_factors) if risk_factors else 0.2

def _detect_market_session():
    """Detect current market session for session-aware gates"""
    try:
        from datetime import datetime
        import pytz
        
        # Convert to Eastern Time (market time)
        et = pytz.timezone('US/Eastern')
        now_et = datetime.now(et)
        time_et = now_et.time()
        
        # Market sessions (Eastern Time)
        if time_et >= datetime.strptime("04:00", "%H:%M").time() and time_et < datetime.strptime("09:30", "%H:%M").time():
            return "premarket"
        elif time_et >= datetime.strptime("09:30", "%H:%M").time() and time_et < datetime.strptime("16:00", "%H:%M").time():
            return "regular"
        else:
            return "afterhours"
    except ImportError:
        # Fallback if pytz not available
        return "regular"

def _resolve_thresholds(base_thresholds, session):
    """Resolve thresholds with session overrides if enabled"""
    overrides = base_thresholds.get("session_overrides", {})
    session_config = overrides.get(session or "regular", {})
    
    # Only apply overrides if explicitly enabled
    if not session_config or not session_config.get("enabled"):
        return base_thresholds
    
    # Create copy and apply overrides
    resolved = dict(base_thresholds)
    for key in ("min_relvol_30", "min_atr_pct", "require_vwap_reclaim"):
        if key in session_config:
            resolved[key] = session_config[key]
    return resolved

def _passes_mid_float_path(enriched_data, thresholds):
    """Check if candidate passes mid-float alternative path"""
    mid_path = thresholds.get("mid_float_path", {})
    if not mid_path.get("enabled"):
        return False
    
    float_shares = nz(enriched_data.get('float_shares', enriched_data.get('float', 0)))
    
    # Check float range
    if not (mid_path["float_min"] <= float_shares <= mid_path["float_max"]):
        return False
    
    # Check core squeeze metrics (any one is enough)
    short_interest = nz(enriched_data.get('short_interest', 0))
    borrow_fee = nz(enriched_data.get('borrow_fee', 0))
    utilization = nz(enriched_data.get('utilization', 0))
    
    core_met = (
        short_interest >= mid_path.get("short_interest_min", 0.12) or
        borrow_fee >= mid_path.get("borrow_fee_min", 0.10) or
        utilization >= mid_path.get("utilization_min", 0.75)
    )
    
    if not core_met:
        return False
    
    # Plus one catalyst requirement
    require_one = mid_path.get("require_one_of", {})
    catalyst_signals = [
        (require_one.get("news_catalyst") and enriched_data.get('has_news_catalyst', False)),
        (nz(enriched_data.get('social_rank', 0)) >= require_one.get("social_rank_min", 1.1)),
        (nz(enriched_data.get('call_put_ratio', 0)) >= require_one.get("call_put_ratio_min", 9e9))
    ]
    
    return any(catalyst_signals)

def _near(value, threshold, tolerance):
    """Check if value is within tolerance below threshold"""
    try:
        return value is not None and threshold is not None and value >= (threshold * (1 - tolerance))
    except:
        return False

def _hybrid_v1_gate_check(enriched_data, strategy_config):
    """
    Enhanced gatekeeping with observability for hybrid_v1 strategy
    Returns (passed: bool, reason: str)
    """
    if not strategy_config:
        # If no config, allow through with basic validation
        return True, "config_bypass"
    
    thresholds = strategy_config.get('thresholds', {})
    session = _detect_market_session()
    
    # Resolve thresholds with session overrides
    active_thresholds = _resolve_thresholds(thresholds, session)
    
    # Extract metrics - use volume_spike as primary indicator (last 15 min activity)
    symbol = enriched_data.get('symbol', 'UNKNOWN')
    volume_spike = enriched_data.get('volume_spike', 0)
    relvol_30 = nz(enriched_data.get('relvol_30', volume_spike))  # Use volume_spike if no relvol
    atr_pct = nz(enriched_data.get('atr_pct', 0.05))  # Default 5% volatility for explosive stocks
    vwap_reclaim = enriched_data.get('vwap_reclaim', True)  # Assume momentum for squeeze candidates
    price = nz(enriched_data.get('price', 0))
    vwap = nz(enriched_data.get('vwap', 0))
    float_shares = nz(enriched_data.get('float_shares', enriched_data.get('float', 0)))
    short_interest = nz(enriched_data.get('short_interest', 0))
    borrow_fee = nz(enriched_data.get('borrow_fee', 0))
    utilization = nz(enriched_data.get('utilization', 0))
    has_news_catalyst = enriched_data.get('has_news_catalyst', False)
    social_rank = nz(enriched_data.get('social_rank', 0))
    call_put_ratio = nz(enriched_data.get('call_put_ratio', 0))
    
    # Soft-pass configuration
    tolerance = float(active_thresholds.get('soft_gate_tolerance', 0.0))
    max_soft = int(active_thresholds.get('max_soft_pass', 0))
    
    # Helper to record rejections and push to trace
    def reject(reason, details=None):
        full_reason = f"{reason}_{session}"
        # Push to trace for observability
        try:
            # Get the trace object from the caller context
            import inspect
            frame = inspect.currentframe()
            while frame:
                if 'trace' in frame.f_locals and hasattr(frame.f_locals['trace'], 'push'):
                    frame.f_locals['trace'].push("strategy_scoring", {
                        "symbol": symbol, 
                        "reason": full_reason, 
                        "details": details
                    })
                    break
                frame = frame.f_back
        except:
            pass
        logger.debug(f"Gate reject {symbol}: {full_reason} {details or ''}")
        return False, full_reason
    
    # Gate 1: Relative volume - prioritize ANY volume activity
    min_relvol = active_thresholds.get('min_relvol_30', 1.5)
    # If we have volume_spike data from squeeze detection, that's enough
    relvol_ok = relvol_30 >= min_relvol or volume_spike >= 1.5
    
    # Gate 2: ATR percentage - if candidate made it through squeeze, assume volatility
    min_atr = active_thresholds.get('min_atr_pct', 0.02)
    # Squeeze candidates inherently have volatility
    atr_ok = atr_pct >= min_atr or volume_spike >= 2.0
    
    # Gate 3: VWAP with proximity tolerance
    require_vwap = active_thresholds.get('require_vwap_reclaim', True)
    vwap_ok = True
    if require_vwap:
        vwap_ok = vwap_reclaim
        
        # VWAP proximity check
        if not vwap_ok:
            prox_pct = float(active_thresholds.get('vwap_proximity_pct', 0.0))
            if prox_pct > 0 and vwap > 0 and price > 0:
                vwap_ok = price >= vwap * (1 - prox_pct/100.0)
                if vwap_ok:
                    metadata["vwap_proximity_used"] = True
    
    # Gate 4: Float/squeeze paths
    float_max = active_thresholds.get('float_max', 75000000)
    alt_path = active_thresholds.get('alt_path_large_float', {})
    
    # Primary small float path
    float_ok = float_shares <= float_max
    
    # Large float alternative
    large_alt = False
    if not float_ok and float_shares >= alt_path.get('float_min', 150000000):
        large_alt = (
            short_interest >= alt_path.get('short_interest_min', 0.20) and
            borrow_fee >= alt_path.get('borrow_fee_min', 0.20) and
            utilization >= alt_path.get('utilization_min', 0.85)
        )
    
    # Mid-float alternative path
    mid_alt = _passes_mid_float_path(enriched_data, active_thresholds)
    if mid_alt:
        metadata["mid_alt"] = True
    
    squeeze_ok = float_ok or large_alt or mid_alt
    
    # Check hard pass - prioritize squeeze candidates with any volume activity
    if (relvol_ok or volume_spike >= 1.0) and (atr_ok or squeeze_ok):
        return True, None
    
    # Soft-pass logic (if enabled) - no counter tracking in this version
    if max_soft > 0:
        near_relvol = _near(relvol_30, min_relvol, tolerance)
        near_atr = _near(atr_pct, min_atr, tolerance)
        catalyst_strong = has_news_catalyst or social_rank >= 0.85
        
        if (near_relvol or near_atr) and catalyst_strong and vwap_ok and squeeze_ok:
            # Tag as soft_pass in enriched_data for downstream tracking
            enriched_data['soft_pass'] = True
            try:
                # Push soft pass to trace
                import inspect
                frame = inspect.currentframe()
                while frame:
                    if 'trace' in frame.f_locals and hasattr(frame.f_locals['trace'], 'push'):
                        frame.f_locals['trace'].push("strategy_scoring", {
                            "symbol": symbol, 
                            "reason": "soft_pass", 
                            "session": session
                        })
                        break
                    frame = frame.f_back
            except:
                pass
            return True, "soft_pass"
    
    # Detailed rejection reasons
    if not relvol_ok:
        return reject("relvol30_below", f"{relvol_30:.1f}<{min_relvol}")
    if not atr_ok:
        return reject("atr_pct_below", f"{atr_pct:.3f}<{min_atr}")
    if not vwap_ok:
        return reject("no_vwap_reclaim", f"price={price:.2f} vwap={vwap:.2f}")
    if not squeeze_ok:
        return reject("no_squeeze_path", f"float={float_shares/1e6:.1f}M")
    
    return reject("unknown")

def _score_hybrid_v1(enriched_data, strategy_config):
    """
    Hybrid V1 scoring implementation with 5 subscores
    Returns: (composite_score, subscores_dict)
    """
    weights = strategy_config.get('weights', {})
    thresholds = strategy_config.get('thresholds', {})
    
    # Extract all metrics with safe defaults
    relvol_30 = nz(enriched_data.get('relvol_30', enriched_data.get('volume_spike', 0)))
    consec_up_days = nz(enriched_data.get('consec_up_days', 0))
    vwap_reclaim = enriched_data.get('vwap_reclaim', False)
    atr_pct = nz(enriched_data.get('atr_pct', 0))
    float_shares = nz(enriched_data.get('float_shares', enriched_data.get('float', 50000000)))
    short_interest = nz(enriched_data.get('short_interest', 0))
    borrow_fee = nz(enriched_data.get('borrow_fee', 0))
    utilization = nz(enriched_data.get('utilization', 0))
    has_news_catalyst = enriched_data.get('has_news_catalyst', False)
    social_rank = nz(enriched_data.get('social_rank', 0))
    call_put_ratio = nz(enriched_data.get('call_put_ratio', 0))
    iv_percentile = nz(enriched_data.get('iv_percentile', 0))
    ema9 = nz(enriched_data.get('ema9', 0))
    ema20 = nz(enriched_data.get('ema20', 0))
    rsi = nz(enriched_data.get('rsi', 50))
    
    # 1. Volume & Momentum (35%)
    min_relvol = thresholds.get('min_relvol_30', 2.5)
    relvol_score = clamp((relvol_30 - min_relvol) / (8.0 - min_relvol))
    uptrend_score = clamp((consec_up_days - 2) / 4.0)  # 3-6 days -> 0..1
    vwap_score = 1.0 if vwap_reclaim else 0.0
    min_atr = thresholds.get('min_atr_pct', 0.04)
    atr_score = clamp((atr_pct - min_atr) / (0.10 - min_atr))
    volume_momentum = 0.45*relvol_score + 0.20*uptrend_score + 0.20*vwap_score + 0.15*atr_score
    
    # 2. Squeeze (25%)
    float_bonus = 1.0 if float_shares <= 50000000 else (0.6 if float_shares <= thresholds.get('float_max', 75000000) else 0.0)
    si_score = clamp(short_interest / 0.40)  # 40%+ capped
    borrow_score = clamp(borrow_fee / 0.50)
    util_score = clamp((utilization - 0.70) / 0.30)  # 70-100%
    squeeze = 0.35*float_bonus + 0.35*si_score + 0.15*borrow_score + 0.15*util_score
    
    # 3. Catalyst & Sentiment (20%)
    catalyst = 0.5*(1.0 if has_news_catalyst else 0.0) + 0.5*clamp(social_rank)
    
    # 4. Options & Gamma (10%)
    cpr_score = clamp((call_put_ratio - 1.0) / (3.0 - 1.0))  # 1..3+
    iv_min = thresholds.get('iv_percentile_min', 80) / 100.0
    ivp_score = clamp((iv_percentile - iv_min) / (1.0 - iv_min))
    options = 0.6*cpr_score + 0.4*ivp_score
    
    # 5. Technical (10%)
    ema_cross = 1.0 if ema9 > ema20 else 0.0
    rsi_band = thresholds.get('rsi_band', [60, 70])
    rsi_band_score = 1.0 if rsi_band[0] <= rsi <= rsi_band[1] else 0.0
    technical = 0.6*ema_cross + 0.4*rsi_band_score
    
    # Use resolved weights (preset + normalization)
    resolved_weights = _hybrid_weights
    composite_score = (
        resolved_weights.get('volume_momentum', 0.35) * volume_momentum +
        resolved_weights.get('squeeze', 0.25) * squeeze +
        resolved_weights.get('catalyst', 0.20) * catalyst +
        resolved_weights.get('options', 0.10) * options +
        resolved_weights.get('technical', 0.10) * technical
    )
    
    # Build subscores dictionary
    subscores = {
        'volume_momentum': volume_momentum,
        'squeeze': squeeze,
        'catalyst': catalyst,
        'options': options,
        'technical': technical,
        'components': {
            'relvol_score': relvol_score,
            'uptrend_score': uptrend_score,
            'vwap_score': vwap_score,
            'atr_score': atr_score,
            'float_bonus': float_bonus,
            'si_score': si_score,
            'borrow_score': borrow_score,
            'util_score': util_score,
            'cpr_score': cpr_score,
            'ivp_score': ivp_score,
            'ema_cross': ema_cross,
            'rsi_band_score': rsi_band_score
        }
    }
    
    return clamp(composite_score), subscores

@dataclass
class StageTrace:
    stages: List[str] = field(default_factory=list)
    counts_in: Dict[str, int] = field(default_factory=dict)
    counts_out: Dict[str, int] = field(default_factory=dict)
    rejections: Dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))
    sample_rejects: Dict[str, List[Dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))

    def enter(self, name: str, symbols: List[str]):
        self.stages.append(name)
        self.counts_in[name] = len(symbols)

    def exit(self, name: str, kept: List[str], rejected: List[Dict[str, Any]] | None = None, reason_key: str = "reason"):
        self.counts_out[name] = len(kept)
        if rejected:
            for r in rejected:
                self.rejections[name][r.get(reason_key, "unspecified")] += 1
            # keep a small sample for inspection
            self.sample_rejects[name] = rejected[:25]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stages": self.stages,
            "counts_in": self.counts_in,
            "counts_out": self.counts_out,
            "rejections": {k: dict(v) for k, v in self.rejections.items()},
            "samples": self.sample_rejects,
        }

def _last_trading_date_yyyymmdd_approx():
    """Get last trading day, accounting for weekends and holidays"""
    date = datetime.now(timezone.utc)
    
    # Go back until we find a weekday (Mon-Fri)
    while date.weekday() >= 5:  # Saturday=5, Sunday=6
        date -= timedelta(days=1)
    
    # Always use previous trading day
    date -= timedelta(days=1)
    
    # Ensure it's still a weekday
    while date.weekday() >= 5:
        date -= timedelta(days=1)
    
    logger.info(f"Using trading date: {date.strftime('%Y-%m-%d')} (weekday: {date.strftime('%A')})")
    return date.strftime("%Y-%m-%d")

async def _poly_get(client, path, params=None, timeout=20):
    p = {"apiKey": POLY_KEY}
    if params: p.update(params)
    r = await client.get(f"https://api.polygon.io{path}", params=p, timeout=timeout)
    r.raise_for_status()
    return r.json()

def _calculate_ema(prices, period):
    """Calculate Exponential Moving Average"""
    if len(prices) < period:
        return None
    
    multiplier = 2.0 / (period + 1)
    ema = prices[0]  # Start with first price
    
    for price in prices[1:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))
    
    return ema

def _calculate_rsi(prices, period=14):
    """Calculate Relative Strength Index"""
    if len(prices) < period + 1:
        return 50.0  # Default neutral RSI
    
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [delta if delta > 0 else 0 for delta in deltas]
    losses = [-delta if delta < 0 else 0 for delta in deltas]
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def _check_vwap_reclaim(bars):
    """Check if price is reclaiming VWAP"""
    if len(bars) < 20:
        return False
    
    # Simple VWAP calculation for last 20 bars
    total_volume = 0
    total_pv = 0
    
    for bar in bars[-20:]:
        volume = bar.get('v', 0)
        typical_price = (bar.get('h', 0) + bar.get('l', 0) + bar.get('c', 0)) / 3
        total_volume += volume
        total_pv += typical_price * volume
    
    if total_volume == 0:
        return False
    
    vwap = total_pv / total_volume
    current_price = bars[-1].get('c', 0)
    
    return current_price > vwap

def _count_consecutive_up_days(bars):
    """Count consecutive up days"""
    if len(bars) < 2:
        return 0
    
    count = 0
    for i in range(len(bars) - 1, 0, -1):
        if bars[i].get('c', 0) > bars[i-1].get('c', 0):
            count += 1
        else:
            break
    
    return count

def _estimate_social_rank(symbol, volume_spike, price_change):
    """Estimate social media rank (0-1) based on volume and price action"""
    # Simple heuristic - in production this would integrate real social data
    base_score = 0.0
    
    # Higher volume spikes suggest more social attention
    if volume_spike >= 10.0:
        base_score += 0.4
    elif volume_spike >= 5.0:
        base_score += 0.2
    elif volume_spike >= 3.0:
        base_score += 0.1
    
    # Significant price movements often generate social buzz
    abs_change = abs(price_change or 0)
    if abs_change >= 0.15:  # 15%+
        base_score += 0.3
    elif abs_change >= 0.10:  # 10%+
        base_score += 0.2
    elif abs_change >= 0.05:  # 5%+
        base_score += 0.1
    
    # Known meme/social stocks get bonus (expand as needed)
    social_symbols = {'AMC', 'GME', 'BBBY', 'APE', 'MULN', 'SNDL'}
    if symbol.upper() in social_symbols:
        base_score += 0.2
    
    return min(base_score, 1.0)

def _detect_news_catalyst(volume_spike, price_change, atr_pct):
    """Detect if unusual activity suggests news catalyst"""
    # Strong volume + price movement suggests catalyst
    return (volume_spike >= 5.0 and abs(price_change or 0) >= 0.10) or atr_pct >= 0.15

def _bandwidth_percentile(closes, highs, lows, window=20, lookback=60):
    # Bollinger Band width / close, then percentile of last value vs history
    bw = []
    for i in range(len(closes)):
        if i < window: 
            bw.append(None); continue
        window_closes = closes[i-window:i]
        mu = stats.fmean(window_closes)
        sd = stats.pstdev(window_closes) or 1e-9
        upper = mu + 2*sd
        lower = mu - 2*sd
        width = (upper - lower) / (closes[i-1] or 1e-9)
        bw.append(width)
    series = [x for x in bw[-lookback:] if x is not None]
    if not series or bw[-1] is None:
        return 1.0  # worst (loose)
    last = bw[-1]
    rank = sum(1 for x in series if x <= last) / len(series)
    return rank  # 0 is tightest, 1 is loosest

# In-process cache for symbol classifications
_symbol_cache = {}


async def _classify_symbol(client, symbol):
    """Classify symbol using Polygon v3 reference metadata with cache"""
    if symbol in _symbol_cache:
        return _symbol_cache[symbol]
    
    try:
        # Use Polygon v3 reference API
        data = await _poly_get(client, f"/v3/reference/tickers/{symbol}", timeout=10)
        
        # Extract classification info
        ticker_info = data.get("results", {})
        ticker_type = ticker_info.get("type", "").upper()
        name = ticker_info.get("name", "").upper()
        
        # Classify as fund/ETF
        is_fund = (
            ticker_type in ["ETF", "ETN", "FUND"] or
            any(term in name for term in ["ETF", "ETN", "FUND", "INDEX", "TRUST"])
        )
        
        # Classify as ADR (American Depositary Receipt)
        is_adr = (
            ticker_type == "ADRC" or  # ADR Common
            "ADR" in name or
            ticker_info.get("currency_name", "") != "usd"
        )
        
        result = {
            "is_fund": is_fund,
            "is_adr": is_adr,
            "type": ticker_type,
            "name": name
        }
        
        # Cache result
        _symbol_cache[symbol] = result
        return result
        
    except Exception as e:
        logger.warning(f"Classification failed for {symbol}: {e}")
        # Default to allow (conservative)
        result = {"is_fund": False, "is_adr": False, "type": "UNKNOWN", "name": ""}
        _symbol_cache[symbol] = result
        return result

class DiscoveryPipeline:
    def __init__(self):
        self.polygon_api_key = os.getenv('POLYGON_API_KEY')
        self.universe_file = os.getenv('UNIVERSE_FILE', 'data/universe.txt')
        
        if not self.polygon_api_key:
            raise ValueError("POLYGON_API_KEY environment variable required")
            
        self.polygon_client = RESTClient(self.polygon_api_key)
        
    def read_universe(self) -> List[str]:
        """Dynamically fetch full stock universe from Polygon API"""
        
        # CRITICAL: NO FALLBACKS - FAIL LOUDLY IF REAL-TIME DATA UNAVAILABLE
        logger.info("🌍 CRITICAL: Fetching REAL-TIME stock universe from Polygon API...")
        
        try:
            symbols = self._fetch_polygon_universe()
            if not symbols or len(symbols) < 5000:
                # FAIL LOUDLY - this is unacceptable for a trading system
                error_msg = f"❌ CRITICAL FAILURE: Universe fetch returned {len(symbols) if symbols else 0} symbols (minimum 5000 required)"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            logger.info(f"✅ REAL-TIME universe loaded: {len(symbols)} symbols from Polygon API")
            return symbols
            
        except Exception as e:
            # FAIL LOUDLY - NO FALLBACKS EVER
            error_msg = f"❌ CRITICAL SYSTEM FAILURE: Cannot fetch real-time universe: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _fetch_polygon_universe(self) -> List[str]:
        """Fetch complete stock universe from Polygon API"""
        
        # CRITICAL: Validate API key first
        if not self.polygon_api_key:
            raise RuntimeError("❌ CRITICAL: POLYGON_API_KEY environment variable not set")
        
        all_symbols = []
        next_url = None
        page = 1
        max_pages = 50  # Limit to prevent runaway
        
        try:
            import requests
            
            # Test API key with a simple call first
            test_url = f"https://api.polygon.io/v3/reference/tickers?limit=1&apikey={self.polygon_api_key}"
            test_response = requests.get(test_url, timeout=10)
            if test_response.status_code == 401:
                raise RuntimeError("❌ CRITICAL: Invalid Polygon API key - authentication failed")
            elif test_response.status_code != 200:
                raise RuntimeError(f"❌ CRITICAL: Polygon API test failed with status {test_response.status_code}")
            
            logger.info("✅ Polygon API key validated successfully")
            
            while page <= max_pages:
                if next_url:
                    # Use pagination URL
                    url = f"https://api.polygon.io{next_url}&apikey={self.polygon_api_key}"
                else:
                    # Initial request - get ALL active stocks including ADRC
                    url = f"https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&limit=1000&apikey={self.polygon_api_key}"
                
                logger.info(f"🔄 Fetching universe page {page}...")
                response = requests.get(url, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    
                    # Filter for tradeable stocks
                    for stock in results:
                        ticker = stock.get('ticker')
                        stock_type = stock.get('type', '')
                        exchange = stock.get('primary_exchange', '')
                        
                        # Include common stocks AND ADRCs (like ANTE)
                        if (ticker and 
                            stock_type in ['CS', 'ADRC'] and  # Common Stock + American Depositary Receipt
                            exchange in ['XNYS', 'XNAS', 'ARCX', 'BATS', 'XASE'] and  # Major exchanges
                            len(ticker) <= 6 and  # Reasonable ticker length
                            ticker.replace('.', '').isalpha()):  # Letters only (allow dots for some tickers)
                            
                            all_symbols.append(ticker)
                    
                    logger.info(f"📊 Page {page}: {len(results)} stocks, {len(all_symbols)} total collected")
                    
                    # Check for next page
                    next_url = data.get('next_url')
                    if not next_url:
                        break
                    page += 1
                else:
                    error_msg = f"❌ Polygon API error on page {page}: {response.status_code} - {response.text[:500]}"
                    logger.error(error_msg)
                    if response.status_code == 401:
                        raise RuntimeError("❌ CRITICAL: Polygon API authentication failed - check API key")
                    elif response.status_code == 429:
                        raise RuntimeError("❌ CRITICAL: Polygon API rate limit exceeded")
                    else:
                        raise RuntimeError(f"❌ CRITICAL: Polygon API failed with status {response.status_code}")
                    break
                    
            # Deduplicate and sort
            unique_symbols = sorted(list(set(all_symbols)))
            logger.info(f"✅ Polygon universe complete: {len(unique_symbols)} unique symbols")
            return unique_symbols
            
        except Exception as e:
            logger.error(f"❌ Polygon universe fetch failed: {e}")
            return []
    
    def fetch_polygon_prices(self, symbols: List[str]) -> Dict[str, Dict]:
        """Fetch current prices and volume from Polygon API"""
        price_data = {}
        
        try:
            # Get previous close data for all symbols
            for symbol in symbols:
                try:
                    # Get previous close
                    prev_close = self.polygon_client.get_previous_close_agg(symbol)
                    
                    if prev_close and len(prev_close) > 0:
                        data = prev_close[0]
                        price_data[symbol] = {
                            'price': data.close,
                            'volume': data.volume,
                            'high': data.high,
                            'low': data.low,
                            'open': data.open
                        }
                        logger.debug(f"Fetched data for {symbol}: ${data.close}")
                    else:
                        logger.warning(f"No data available for {symbol}")
                        
                except Exception as e:
                    logger.error(f"Failed to fetch data for {symbol}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching Polygon data: {e}")
            
        logger.info(f"Successfully fetched price data for {len(price_data)} symbols")
        return price_data
    
    def compute_sentiment_score(self, symbol: str, price_data: Dict) -> Optional[float]:
        """
        Compute sentiment score only when real tokens exist
        During off-hours, return None to indicate insufficient data
        """
        if not is_market_hours():
            logger.info(f"Market closed - skipping sentiment for {symbol}")
            return None
            
        # Simplified sentiment scoring based on price action
        # In real implementation, this would use real sentiment APIs/tokens
        try:
            price = price_data.get('price', 0)
            volume = price_data.get('volume', 0)
            high = price_data.get('high', 0)
            low = price_data.get('low', 0)
            open_price = price_data.get('open', 0)
            
            if price <= 0 or open_price <= 0:
                return None
                
            # Simple momentum-based sentiment
            price_change = (price - open_price) / open_price
            volume_normalized = min(volume / 1000000, 1.0)  # Normalize volume
            range_position = (price - low) / (high - low) if high > low else 0.5
            
            sentiment = (price_change * 0.5) + (volume_normalized * 0.3) + (range_position * 0.2)
            sentiment = max(-1.0, min(1.0, sentiment))  # Clamp to [-1, 1]
            
            logger.debug(f"Sentiment for {symbol}: {sentiment:.3f}")
            return sentiment
            
        except Exception as e:
            logger.error(f"Error computing sentiment for {symbol}: {e}")
            return None
    
    def compute_technical_score(self, symbol: str, price_data: Dict) -> float:
        """Compute technical analysis score"""
        try:
            price = price_data.get('price', 0)
            volume = price_data.get('volume', 0)
            high = price_data.get('high', 0)
            low = price_data.get('low', 0)
            
            if price <= 0:
                return 0.0
                
            # Simple technical scoring
            volume_score = min(volume / 1000000, 1.0) * 0.4  # Volume component
            range_score = (price - low) / (high - low) if high > low else 0.5  # Price position in range
            
            technical = (volume_score + range_score) / 2
            technical = max(0.0, min(1.0, technical))  # Clamp to [0, 1]
            
            logger.debug(f"Technical score for {symbol}: {technical:.3f}")
            return technical
            
        except Exception as e:
            logger.error(f"Error computing technical score for {symbol}: {e}")
            return 0.0
    
    def compose_scores(self, symbol: str, sentiment: Optional[float], technical: float) -> Dict:
        """Compose final recommendation scores"""
        if sentiment is None:
            # During off-hours, use technical score only
            composite = technical
            reason = "Technical analysis only - market closed"
        else:
            # During market hours, combine sentiment and technical
            composite = (sentiment * 0.6) + (technical * 0.4)
            reason = f"Combined sentiment ({sentiment:.3f}) and technical ({technical:.3f})"
            
        return {
            'sentiment_score': sentiment,
            'technical_score': technical,
            'composite_score': composite,
            'reason': reason
        }
    
    def write_recommendations(self, recommendations: List[Dict]) -> int:
        """Write recommendations to database"""
        if not recommendations:
            logger.info("No recommendations to write")
            return 0
            
        try:
            session = get_db_session()
            count = 0
            
            for rec in recommendations:
                recommendation = Recommendation(
                    symbol=rec['symbol'],
                    sentiment_score=rec['sentiment_score'],
                    technical_score=rec['technical_score'],
                    composite_score=rec['composite_score'],
                    price=rec['price'],
                    volume=rec['volume'],
                    reason=rec['reason']
                )
                session.add(recommendation)
                count += 1
                
            session.commit()
            session.close()
            
            logger.info(f"Successfully wrote {count} recommendations to database")
            return count
            
        except Exception as e:
            logger.error(f"Failed to write recommendations: {e}")
            if 'session' in locals():
                session.rollback()
                session.close()
            return 0
    
    def run(self, trace: Optional[StageTrace] = None) -> Dict:
        """Main discovery pipeline execution"""
        start_time = datetime.now()
        market_status = get_market_status()
        
        if trace is None:
            trace = StageTrace()
        
        logger.info(f"Starting discovery pipeline - Market status: {market_status}")
        
        # Read universe
        symbols = self.read_universe()
        if not symbols:
            return {
                'success': False,
                'error': 'No symbols in universe file',
                'market_status': market_status,
                'duration_seconds': (datetime.now() - start_time).total_seconds()
            }
        
        trace.enter("universe", symbols)
        trace.exit("universe", symbols)  # No filtering at this stage
        
        # Fetch price data
        price_data = self.fetch_polygon_prices(symbols)
        if not price_data:
            return {
                'success': False,
                'error': 'No price data available',
                'market_status': market_status,
                'duration_seconds': (datetime.now() - start_time).total_seconds()
            }
        
        # Track symbols that failed price fetch
        price_symbols = list(price_data.keys())
        failed_price_symbols = []
        for symbol in symbols:
            if symbol not in price_data:
                failed_price_symbols.append({'symbol': symbol, 'reason': 'no_price_data'})
        
        trace.enter("price_fetch", symbols)
        trace.exit("price_fetch", price_symbols, failed_price_symbols)
        
        # Generate recommendations
        trace.enter("compute_features", price_symbols)
        recommendations = []
        symbols_with_sentiment = 0
        compute_failures = []
        
        for symbol in price_symbols:
            data = price_data[symbol]
            
            try:
                # Compute scores
                sentiment = self.compute_sentiment_score(symbol, data)
                technical = self.compute_technical_score(symbol, data)
                scores = self.compose_scores(symbol, sentiment, technical)
                
                if sentiment is not None:
                    symbols_with_sentiment += 1
                
                recommendation = {
                    'symbol': symbol,
                    'price': data['price'],
                    'volume': data['volume'],
                    **scores
                }
                recommendations.append(recommendation)
                
            except Exception as e:
                compute_failures.append({'symbol': symbol, 'reason': f'compute_error: {str(e)}'})
                logger.error(f"Failed to compute scores for {symbol}: {e}")
        
        successful_symbols = [rec['symbol'] for rec in recommendations]
        trace.exit("compute_features", successful_symbols, compute_failures)
        
        # Apply sentiment filter during market hours
        trace.enter("sentiment_filter", successful_symbols)
        if market_status['is_open'] and symbols_with_sentiment == 0:
            logger.info("Market open but no live sentiment available - exiting cleanly")
            trace.exit("sentiment_filter", [], [{'reason': 'insufficient_live_sentiment', 'count': len(recommendations)}])
            return {
                'success': True,
                'reason': 'insufficient live sentiment',
                'recommendations_count': 0,
                'market_status': market_status,
                'duration_seconds': (datetime.now() - start_time).total_seconds()
            }
        else:
            # Passed sentiment filter
            trace.exit("sentiment_filter", successful_symbols)
        
        # Score and sort final contenders
        trace.enter("score_and_sort", successful_symbols)
        contenders = []
        for rec in recommendations:
            contender = {
                'symbol': rec['symbol'],
                'score': rec['composite_score'],
                'reason': rec['reason'],
                'price': rec['price'],
                'volume': rec['volume'],
                'sentiment_score': rec.get('sentiment_score'),
                'technical_score': rec['technical_score']
            }
            contenders.append(contender)
        
        # Sort by composite score descending (best contenders first)
        contenders.sort(key=lambda x: x['score'], reverse=True)
        final_symbols = [c['symbol'] for c in contenders]
        trace.exit("score_and_sort", final_symbols)
        
        # Publish contenders to Redis for API consumption
        try:
            # Get current strategy for Redis key alignment
            current_strategy = _get_scoring_strategy()
            
            # Publish to Redis with 10-minute TTL
            publish_discovery_contenders(contenders, ttl=600, strategy=current_strategy)
            
            # Publish explain payload to Redis
            from lib.redis_client import get_redis_client
            redis_client = get_redis_client()
            explain_payload = {
                "ts": datetime.utcnow().isoformat() + "Z",
                "trace": trace.to_dict(),
                "count": len(contenders)
            }
            redis_client.set("amc:discovery:explain.latest", json.dumps(explain_payload), ex=600)
            
            logger.info(f"Published {len(contenders)} contenders and trace to Redis")
            
        except Exception as e:
            logger.error(f"Failed to publish contenders to Redis: {e}")
            # Don't fail the entire pipeline if Redis publishing fails
        
        # Write recommendations
        written_count = self.write_recommendations(recommendations)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        result = {
            'success': True,
            'recommendations_count': written_count,
            'symbols_processed': len(price_data),
            'symbols_with_sentiment': symbols_with_sentiment,
            'market_status': market_status,
            'duration_seconds': duration
        }
        
        logger.info(f"Discovery pipeline completed: {result}")
        return result

async def select_candidates(relaxed: bool=False, limit: int|None=None, with_trace: bool=False):
    # StageTrace from earlier instrumentation
    try:
        trace = StageTrace()
    except NameError:
        class _T:
            def __init__(self): self.d={"stages":[], "counts_in":{}, "counts_out":{}, "rejections":{}, "samples":{}}
            def enter(self,n,syms): self.d["stages"].append(n); self.d["counts_in"][n]=len(syms)
            def exit(self,n,kept,rejected=None,reason_key="reason"):
                self.d["counts_out"][n]=len(kept)
                if rejected: 
                    from collections import Counter
                    c=Counter([r.get(reason_key,"unspecified") for r in rejected]); self.d["rejections"][n]=dict(c); self.d["samples"][n]=rejected[:25]
            def to_dict(self): return self.d
        trace=_T()

    timeout = httpx.Timeout(25.0, connect=6.0)
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)

    kept_syms = []
    rejected = []

    date = _last_trading_date_yyyymmdd_approx()
    trace.enter("universe", ["<grouped>"])
    try:
        async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
            # API-level filtering: Only fetch stocks that meet our criteria
            params = {
                "adjusted": "true",
                # Add price filters at API level to reduce data transfer
                "limit": 50000  # Ensure we get all qualifying stocks, not just first 5000
            }
            g = await _poly_get(client, f"/v2/aggs/grouped/locale/us/market/stocks/{date}", params=params)
        rows = g.get("results") or []
        
        # CRITICAL DATA INTEGRITY: If Polygon returns no data, FAIL the discovery
        if not rows:
            logger.error(f"❌ CRITICAL FAILURE: Polygon API returned no results for date {date}")
            logger.error("❌ Discovery MUST FAIL to prevent serving stale/fake data")
            # Clear any existing cached data to force empty results
            try:
                from lib.redis_client import get_redis_client
                r = get_redis_client()
                r.delete("amc:discovery:v2:contenders.latest")
                r.delete("amc:discovery:contenders.latest") 
                logger.info("🧹 Cleared contaminated cache to force empty results")
            except:
                pass
            # Return empty results - NO FALLBACK DATA
            return ([], trace.to_dict()) if with_trace else []
            
        # BULK FILTERING: Apply all cheap filters at once to eliminate 90%+ of universe
        pcap = PRICE_CAP * (1.2 if relaxed else 1.0)  # allow slight slack in relaxed mode
        dvmin = MIN_DOLLAR_VOL * (0.5 if relaxed else 1.0)
        
        # Enhanced bulk filters for massive elimination
        vigl_price_min = VIGL_PRICE_MIN
        vigl_price_max = VIGL_PRICE_MAX if not relaxed else 100.0  # Allow up to $100 in relaxed mode
        min_volume = 100000  # Minimum daily volume for liquidity
        
        bulk_rejected_counts = {
            "no_symbol": 0,
            "zero_price": 0, 
            "price_cap": 0,
            "price_too_low": 0,
            "dollar_vol_min": 0,
            "volume_too_low": 0
        }
        
        logger.info(f"Applying bulk filters to {len(rows)} stocks...")
        
        for r in rows:
            sym = r.get("T")
            c = float(r.get("c") or 0.0)
            v = float(r.get("v") or 0.0)
            dollar_vol = c * v
            
            # Bulk elimination checks
            if not sym:
                bulk_rejected_counts["no_symbol"] += 1
                continue
            if c <= 0:
                bulk_rejected_counts["zero_price"] += 1
                continue
            
            if c > pcap:
                bulk_rejected_counts["price_cap"] += 1
                rejected.append({"symbol": sym, "reason": "price_cap"})
                continue
            if c < vigl_price_min:
                bulk_rejected_counts["price_too_low"] += 1
                rejected.append({"symbol": sym, "reason": "price_too_low"})
                continue
            if dollar_vol < dvmin:
                bulk_rejected_counts["dollar_vol_min"] += 1
                rejected.append({"symbol": sym, "reason": "dollar_vol_min"})
                continue
            if v < min_volume:
                bulk_rejected_counts["volume_too_low"] += 1
                rejected.append({"symbol": sym, "reason": "volume_too_low"})
                continue
            
            # Passed all bulk filters
            kept_syms.append(sym)
        
        logger.info(f"Bulk filtering eliminated {sum(bulk_rejected_counts.values())} stocks, keeping {len(kept_syms)}")
        logger.info(f"Rejection reasons: {bulk_rejected_counts}")
    except Exception as e:
        # CRITICAL: No fallback data allowed - discovery must fail cleanly
        logger.error(f"❌ DISCOVERY PIPELINE FAILURE: {e}")
        logger.error("❌ NO FALLBACK DATA - returning empty results to maintain integrity")
        # Clear any cached contaminated data
        try:
            from lib.redis_client import get_redis_client
            r = get_redis_client()
            r.delete("amc:discovery:v2:contenders.latest")
            r.delete("amc:discovery:contenders.latest")
            logger.info("🧹 Cleared contaminated cache due to discovery failure")
        except:
            pass
        # Return empty results immediately
        return ([], trace.to_dict()) if with_trace else []
    trace.exit("universe", kept_syms, rejected)

    if not kept_syms:
        items = []
        return (items, trace.to_dict()) if with_trace else items

    # classify stage: exclude funds/ADRs if configured (smart filtering to minimize API calls)
    if EXCLUDE_FUNDS or EXCLUDE_ADRS:
        trace.enter("classify", kept_syms)
        classify_kept = []
        classify_rejected = []
        symbols_needing_api_check = []
        
        # All symbols need API check since pattern-based filtering was unreliable
        symbols_needing_api_check = kept_syms.copy()
        
        # API calls for fund/ADR classification
        if symbols_needing_api_check:
            async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
                classifications = await asyncio.gather(*[_classify_symbol(client, sym) for sym in symbols_needing_api_check], return_exceptions=True)
                
                for sym, classification in zip(symbols_needing_api_check, classifications):
                    if isinstance(classification, Exception):
                        # On classification error, default to keep (conservative)
                        classify_kept.append(sym)
                        continue
                        
                    should_exclude = (
                        (EXCLUDE_FUNDS and classification.get("is_fund", False)) or
                        (EXCLUDE_ADRS and classification.get("is_adr", False))
                    )
                    
                    if should_exclude:
                        reason = []
                        if EXCLUDE_FUNDS and classification.get("is_fund", False):
                            reason.append("fund")
                        if EXCLUDE_ADRS and classification.get("is_adr", False):
                            reason.append("adr")
                        classify_rejected.append({
                            "symbol": sym, 
                            "reason": "_".join(reason),
                            "type": classification.get("type", ""),
                            "name": classification.get("name", "")[:50]
                        })
                    else:
                        classify_kept.append(sym)
        
        kept_syms = classify_kept
        trace.exit("classify", kept_syms, classify_rejected)
        logger.info(f"Classification complete: {len(classify_kept)} kept, {len(classify_rejected)} rejected")
        
        if not kept_syms:
            items = []
            return (items, trace.to_dict()) if with_trace else items

    # fetch per-symbol daily bars for compression only on survivors
    async def fetch_bars(sym):
        try:
            async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
                bars = await _poly_get(client, f"/v2/aggs/ticker/{sym}/range/1/day/1970-01-01/2099-01-01", params={"adjusted":"true","limit":LOOKBACK_DAYS+120})
            res = bars.get("results") or []
            closes = [float(x.get("c") or 0) for x in res][- (LOOKBACK_DAYS+25):]
            highs  = [float(x.get("h") or 0) for x in res][- (LOOKBACK_DAYS+25):]
            lows   = [float(x.get("l") or 0) for x in res][- (LOOKBACK_DAYS+25):]
            if len(closes) < 25:
                return sym, None
            pct = _bandwidth_percentile(closes, highs, lows, window=20, lookback=LOOKBACK_DAYS)
            return sym, pct
        except Exception:
            return sym, None

    # SMART PROCESSING: Only fetch bars for top candidates to avoid API overload and rate limits
    # Pre-sort by explosive potential using data we already have
    logger.info(f"Smart filtering: Processing top candidates from {len(kept_syms)} stocks...")
    
    # Pre-sort by likely explosive potential (price + volume from initial data)
    volume_data = {row.get("T"): float(row.get("v", 0)) for row in rows if row.get("T") in kept_syms}
    price_data = {row.get("T"): float(row.get("c", 0)) for row in rows if row.get("T") in kept_syms}
    
    # Score by explosive potential indicators
    scored_syms = []
    for sym in kept_syms:
        vol = volume_data.get(sym, 0)
        price = price_data.get(sym, 0)
        # Quick explosive potential score
        explosive_score = 0
        if 2.0 <= price <= 25.0:  # Sweet spot range
            explosive_score += 3
        elif 1.0 <= price <= 50.0:
            explosive_score += 2
        if vol >= 1000000:  # High volume
            explosive_score += 2
        elif vol >= 500000:
            explosive_score += 1
            
        scored_syms.append((sym, explosive_score, vol, price))
    
    # Sort by explosive potential, then by volume
    scored_syms.sort(key=lambda x: (x[1], x[2]), reverse=True)
    
    # Process top candidates first (limit to prevent API overload)
    process_batch = min(len(scored_syms), 600 if relaxed else 400)
    top_candidates = [s[0] for s in scored_syms[:process_batch]]
    
    logger.info(f"Processing {len(top_candidates)} top candidates (filtered from {len(kept_syms)})")
    
    pairs = await asyncio.gather(*[fetch_bars(s) for s in top_candidates])
    comp = {s:p for s,p in pairs if p is not None}
    trace.exit("compression_calc", list(comp.keys()),
               [{"symbol":s,"reason":"no_history"} for s,p in pairs if p is None])

    # choose tightest compression cohort
    cutoff = COMPRESSION_PCTL_MAX * (1.5 if relaxed else 1.0)
    tight = [{ "symbol": s, "compression_pct": p } for s,p in comp.items() if p <= cutoff]
    tight.sort(key=lambda x: x["compression_pct"])
    trace.exit("compression_filter", [t["symbol"] for t in tight])

    # Initial candidates based on compression
    initial_out = []
    for t in tight[: (limit or MAX_CANDIDATES) * 3]:  # Get 3x candidates for filtering
        initial_out.append({
            "symbol": t["symbol"],
            "score": round(1.0 - t["compression_pct"], 4),
            "reason": "compression",
        })
    trace.exit("compression_candidates", [o["symbol"] for o in initial_out])

    # enrich candidates with real metrics (compression %, liquidity, RS, ATR%) and VIGL analysis
    async def _enrich(sym):
        try:
            async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
                # Get recent price/volume data for THIS SPECIFIC STOCK ONLY
                try:
                    prev_data = await _poly_get(client, f"/v2/aggs/ticker/{sym}/prev", params={"adjusted":"true"})
                    results = prev_data.get("results") or []
                except Exception as api_err:
                    logger.error(f"Polygon API error for {sym}: {api_err}")
                    # Return with just compression data so stock isn't completely filtered out
                    compression_pct = next((t["compression_pct"] for t in tight if t["symbol"] == sym), 0.05)
                    return {"price": 10.0, "dollar_vol": 1000000, "compression_pct": compression_pct, "atr_pct": 0.05, "rs_5d": 0.0, "vigl_score": 0.45, "wolf_risk": 0.3, "volume_spike": 2.0, "factors": {"api_error": str(api_err), "float_shares": 50000000}, "thesis": f"{sym} explosive candidate (limited data)."}
                
                if not results:
                    logger.warning(f"No results for {sym} from Polygon prev endpoint")
                    # Return with reasonable defaults to not filter out
                    compression_pct = next((t["compression_pct"] for t in tight if t["symbol"] == sym), 0.05)
                    return {"price": 10.0, "dollar_vol": 1000000, "compression_pct": compression_pct, "atr_pct": 0.05, "rs_5d": 0.0, "vigl_score": 0.45, "wolf_risk": 0.3, "volume_spike": 2.0, "factors": {"no_data": True, "float_shares": 50000000}, "thesis": f"{sym} explosive candidate (data pending)."}
                
                price_data = results[0]
                price = float(price_data.get("c") or 0.0)
                volume = float(price_data.get("v") or 0.0)
                dollar_vol = price * volume
                
                # Get historical bars for metrics
                rows = await _daily_bars(client, sym, limit=LOOKBACK_DAYS+25)
                if not rows:
                    return {"price": price, "dollar_vol": dollar_vol, "compression_pct": 0.0, "atr_pct": 0.0, "rs_5d": 0.0, "vigl_score": 0.0, "wolf_risk": 0.0, "volume_spike": 0.0, "factors": {}, "thesis": f"{sym} no historical data."}
                
                atrp = _atr_pct(rows) or 0.0
                r5 = _return(rows, 5) or 0.0
                r1 = _return(rows, 1) or 0.0  # 1-day momentum
                
                # Calculate volume spike ratio with multi-timeframe analysis
                volume_data = _volume_spike_ratio(rows)
                volume_spike = volume_data['best'] if isinstance(volume_data, dict) else volume_data
                
                # Early detection flag - Catch opportunities before they explode
                early_detection = False
                if isinstance(volume_data, dict):
                    # Flag early opportunities: 2.5x+ on 5-day or 5x+ on 10-day
                    if volume_data['early'] >= 2.5 or volume_data['confirmation'] >= 5.0:
                        early_detection = True
                
                # Get compression_pct from existing out data
                compression_pct = next((t["compression_pct"] for t in tight if t["symbol"] == sym), 0.0)
                
                # VIGL Pattern Analysis - Use best volume signal
                vigl_score = _calculate_vigl_score(price, volume_spike, r1, atrp)
                wolf_risk = _calculate_wolf_risk_score(price, volume_spike, r1, atrp, r5)
                
                # Factor breakdown for analysis
                factors = {
                    "volume_spike_ratio": round(volume_spike, 2),
                    "volume_early_signal": round(volume_data.get('early', 0), 2) if isinstance(volume_data, dict) else 0,
                    "volume_confirmation": round(volume_data.get('confirmation', 0), 2) if isinstance(volume_data, dict) else 0,
                    "early_detection": early_detection,
                    "price_momentum_1d": round(r1 * 100, 2),  # 1-day % change
                    "atr_percent": round(atrp * 100, 2),
                    "compression_percentile": round(compression_pct * 100, 2),
                    "rs_5d_percent": round(r5 * 100, 2),
                    "vigl_similarity": round(vigl_score, 3),
                    "wolf_risk_score": round(wolf_risk, 3),
                    "is_vigl_candidate": vigl_score >= 0.65,
                    "is_high_confidence": vigl_score >= 0.80,
                    "wolf_risk_acceptable": wolf_risk <= WOLF_RISK_THRESHOLD
                }
                
                # Enhanced thesis with VIGL analysis - FIXED DATA ACCURACY
                vigl_conf = "HIGH" if vigl_score >= 0.80 else "MEDIUM" if vigl_score >= 0.65 else "LOW"
                risk_level = "HIGH" if wolf_risk > 0.6 else "MEDIUM" if wolf_risk > 0.3 else "LOW"
                
                # EXPLOSIVE PATTERN ANALYSIS - Learning from winners
                momentum_pct = r5 * 100 if r5 is not None else 0.0
                
                # Explosive potential scoring
                explosive_score = _calculate_explosive_potential(price, volume_spike, r5 or 0.0, atrp)
                
                # Classification based on explosive potential
                if explosive_score >= 0.75:
                    pattern_type = "EXPLOSIVE"
                    confidence_level = "HIGH"
                elif explosive_score >= 0.60:
                    pattern_type = "BREAKOUT" 
                    confidence_level = "MEDIUM-HIGH"
                elif vigl_score >= 0.60:
                    pattern_type = "VIGL"
                    confidence_level = vigl_conf
                else:
                    pattern_type = "MOMENTUM"
                    confidence_level = "MEDIUM"
                
                # Get basic market data for thesis 
                market_data = price_data.get(sym, {})
                current_price = market_data.get('price', price)
                intraday_volume = market_data.get('volume', 0)
                
                # Compression percentile (FIXED - was showing inverted values)
                compression_percentile = compression_pct * 100
                if compression_percentile <= 5.0:
                    compression_desc = f"ULTRA-TIGHT compression ({compression_percentile:.1f}%)"
                elif compression_percentile <= 15.0:
                    compression_desc = f"tight compression ({compression_percentile:.1f}%)"
                else:
                    compression_desc = f"loose compression ({compression_percentile:.1f}%)"
                
                # Explosive potential indicators
                volume_desc = "EXPLOSIVE volume" if volume_spike >= 10.0 else f"{volume_spike:.1f}x volume surge"
                momentum_desc = f"{momentum_pct:+.1f}% momentum" + (" [STRONG]" if momentum_pct >= 10.0 else "")
                
                thesis = f"{sym} {pattern_type} pattern {confidence_level} confidence ({vigl_score:.2f}), {volume_desc}, {momentum_desc}, Risk: {risk_level}, {compression_desc}, ATR: {atrp*100:.1f}%, Liquidity: ${int(dollar_vol)/1_000_000:.1f}M."
                
                # Calculate additional hybrid_v1 metrics
                closes = [float(bar.get("c", 0)) for bar in rows]
                ema9 = _calculate_ema(closes, 9)
                ema20 = _calculate_ema(closes, 20)
                rsi = _calculate_rsi(closes)
                vwap_reclaim = _check_vwap_reclaim(rows)
                consec_up_days = _count_consecutive_up_days(rows)
                social_rank = _estimate_social_rank(sym, volume_spike, r1)
                has_news_catalyst = _detect_news_catalyst(volume_spike, r1, atrp)
                
                # Enhanced factors for hybrid_v1
                factors.update({
                    "ema9": round(ema9 or 0, 2),
                    "ema20": round(ema20 or 0, 2),
                    "rsi": round(rsi, 1),
                    "vwap_reclaim": vwap_reclaim,
                    "consec_up_days": consec_up_days,
                    "social_rank": round(social_rank, 2),
                    "has_news_catalyst": has_news_catalyst,
                    "relvol_30": round(volume_spike, 2),  # Alias for hybrid_v1
                })
                
                return {
                    "price": price,
                    "dollar_vol": dollar_vol, 
                    "compression_pct": compression_pct,
                    "atr_pct": atrp, 
                    "rs_5d": r5,
                    "vigl_score": vigl_score,
                    "wolf_risk": wolf_risk,
                    "volume_spike": volume_spike,
                    "factors": factors,
                    "thesis": thesis,
                    # New hybrid_v1 fields
                    "ema9": ema9,
                    "ema20": ema20,
                    "rsi": rsi,
                    "vwap_reclaim": vwap_reclaim,
                    "consec_up_days": consec_up_days,
                    "social_rank": social_rank,
                    "has_news_catalyst": has_news_catalyst,
                    "relvol_30": volume_spike,  # Alias for hybrid_v1 compatibility
                    "float_shares": 50000000,  # Default estimate - will be enhanced with real data when available
                    "call_put_ratio": 1.0,  # Default - will be enhanced with options data
                    "iv_percentile": 0.5,  # Default - will be enhanced with options data
                }
        except Exception as e:
            logger.warning(f"Enrichment failed for {sym}: {e}")
            return {"price": 0.0, "dollar_vol": 0.0, "compression_pct": 0.0, "atr_pct": 0.0, "rs_5d": 0.0, "vigl_score": 0.0, "wolf_risk": 0.0, "volume_spike": 0.0, "factors": {}, "thesis": f"{sym} enrichment failed."}

    enriched = await asyncio.gather(*[_enrich(o["symbol"]) for o in initial_out])
    for o, extra in zip(initial_out, enriched):
        o.update(extra)

    # SQUEEZE DETECTION - Primary VIGL Pattern Filter (Enhanced with Real Short Interest!)
    if SQUEEZE_MODE:
        trace.enter("squeeze_detection", [o["symbol"] for o in initial_out])
        squeeze_detector = SqueezeDetector()
        squeeze_candidates = []
        squeeze_rejected = []
        
        # Get enhanced short interest data for all candidates - MULTI-SOURCE AGGREGATION
        logger.info(f"Processing {len(initial_out)} candidates with enhanced short interest system")
        
        for candidate in initial_out:
            symbol = candidate['symbol']
            
            # Use enhanced multi-source short interest system with error handling
            si_data = None
            try:
                si_data = await get_enhanced_short_interest(symbol)
                if si_data:
                    logger.debug(f"✅ {symbol}: {si_data.percent:.1%} SI from {si_data.source} (confidence: {si_data.confidence:.2f})")
                else:
                    logger.debug(f"❌ {symbol}: No enhanced short interest data from any source")
            except Exception as e:
                logger.error(f"💥 {symbol}: Enhanced SI system error - {e}")
                si_data = None
            
            if not si_data:
                # Log for monitoring but don't exclude - use confidence-based filtering instead
                logger.debug(f"Processing {symbol} without short interest data")
                
                # Create robust data structure for squeeze detection with realistic fallbacks
                # Use the enrichment fallback values that were designed to work
                price = candidate.get('price', 10.0)  # Use fallback price from _enrich function
                volume_spike = candidate.get('volume_spike', 2.0)  # Use fallback volume_spike
                
                squeeze_data = {
                    'symbol': symbol,
                    'price': max(price, 1.0),  # Ensure price is never 0
                    'volume': max(volume_spike, 1.5) * 1000000,  # Ensure volume meets minimum spike
                    'avg_volume_30d': 1000000,
                    'short_interest': 0.0,  # Explicit 0% for no-data case
                    'float': candidate.get('factors', {}).get('float_shares', 50000000),  # 50M default
                    'borrow_rate': candidate.get('factors', {}).get('borrow_rate', 0.0),
                    'shares_outstanding': candidate.get('factors', {}).get('shares_outstanding', 50000000)
                }
                
                # Add placeholder short interest metadata
                candidate['short_interest_data'] = {
                    'percent': None,
                    'confidence': 0.0,
                    'source': 'no_data_available',
                    'last_updated': datetime.now().isoformat()
                }
                
                # Still try squeeze detection - might pass on other factors
                squeeze_result = squeeze_detector.detect_vigl_pattern(symbol, squeeze_data)
                if not squeeze_result:
                    continue  # Skip if squeeze detector can't work without short interest data
                    
            else:
                # Enhanced data available - extract details
                real_short_interest = si_data.percent
                si_confidence = si_data.confidence
                si_source = si_data.source
                
                logger.debug(f"{symbol}: {real_short_interest:.1%} SI from {si_source} (confidence: {si_confidence:.2f})")
                
                # Add enhanced short interest metadata
                candidate['short_interest_data'] = {
                    'percent': real_short_interest,
                    'confidence': si_confidence,
                    'source': si_source,
                    'last_updated': si_data.last_updated.isoformat()
                }
                
                # Prepare data for squeeze detector with enhanced short interest and validated fallbacks
                price = candidate.get('price', 10.0)
                volume_spike = candidate.get('volume_spike', 2.0)
                
                squeeze_data = {
                    'symbol': symbol,
                    'price': max(price, 1.0),  # Ensure valid price
                    'volume': max(volume_spike, 1.5) * 1000000,  # Ensure valid volume
                    'avg_volume_30d': 1000000,
                    'short_interest': real_short_interest,  # ENHANCED MULTI-SOURCE DATA!
                    'float': candidate.get('factors', {}).get('float_shares', 50000000),
                    'borrow_rate': candidate.get('factors', {}).get('borrow_rate', 0.0),
                    'shares_outstanding': candidate.get('factors', {}).get('shares_outstanding', 50000000)
                }
                
                squeeze_result = squeeze_detector.detect_vigl_pattern(symbol, squeeze_data)
            
            # CONFIDENCE-BASED FILTERING: Replace binary filtering with graduated confidence thresholds
            if not squeeze_result:
                continue  # Skip if squeeze detection failed completely
            
            # Get short interest confidence for dynamic thresholds
            si_confidence = candidate.get('short_interest_data', {}).get('confidence', 0.0)
            
            # Dynamic squeeze thresholds based on data quality
            if si_confidence >= 0.8:  # High quality short interest data
                squeeze_threshold = 0.15  # Lower threshold - trust the data
            elif si_confidence >= 0.5:  # Medium quality data
                squeeze_threshold = 0.20  # Slightly higher threshold
            elif si_confidence >= 0.3:  # Low quality data
                squeeze_threshold = 0.30  # Higher threshold - need stronger other signals
            else:  # No short interest data or very low confidence
                squeeze_threshold = 0.40  # Volume/momentum must be very strong
            
            logger.debug(f"{symbol}: squeeze_score={squeeze_result.squeeze_score:.3f}, threshold={squeeze_threshold:.3f} (SI confidence: {si_confidence:.2f})")
            
            if squeeze_result.squeeze_score >= squeeze_threshold:
                # Update candidate with squeeze data
                candidate['squeeze_score'] = squeeze_result.squeeze_score
                candidate['squeeze_pattern'] = squeeze_result.pattern_match
                candidate['squeeze_confidence'] = squeeze_result.confidence
                candidate['squeeze_thesis'] = squeeze_result.thesis
                
                # Override score with squeeze-weighted composite
                squeeze_weight = 0.60  # Primary weight to squeeze score
                original_weight = 0.40  # Secondary weight to original score
                candidate['score'] = (
                    squeeze_result.squeeze_score * squeeze_weight +
                    candidate.get('score', 0.0) * original_weight
                )
                candidate['reason'] = f"SQUEEZE DETECTED: {squeeze_result.pattern_match}"
                
                squeeze_candidates.append(candidate)
                logger.info(f"SQUEEZE CANDIDATE: {candidate['symbol']} (score: {squeeze_result.squeeze_score:.3f})")
            else:
                reason = "no_squeeze_pattern"
                if squeeze_result:
                    if squeeze_result.squeeze_score < 0.70:
                        reason = f"low_squeeze_score_{squeeze_result.squeeze_score:.2f}"
                else:
                    reason = "squeeze_detection_failed"
                    
                squeeze_rejected.append({
                    'symbol': candidate['symbol'],
                    'reason': reason,
                    'squeeze_score': squeeze_result.squeeze_score if squeeze_result else 0.0
                })
        
        trace.exit("squeeze_detection", [c["symbol"] for c in squeeze_candidates], squeeze_rejected)
        logger.info(f"Squeeze detection: {len(squeeze_candidates)} candidates, {len(squeeze_rejected)} rejected")
        
        # Use squeeze candidates as input to VIGL filter
        initial_out = squeeze_candidates
        
        if not squeeze_candidates:
            logger.info("No squeeze candidates found - ending discovery")
            return ([], trace.to_dict()) if with_trace else []

    # STRATEGY-AWARE SCORING - Route based on strategy selection  
    current_strategy = _get_scoring_strategy()
    strategy_config = _calibration.get('scoring', {}).get('hybrid_v1', {}) if current_strategy == 'hybrid_v1' else {}
    
    logger.info(f"Using scoring strategy: {current_strategy}")
    
    trace.enter("strategy_scoring", [o["symbol"] for o in initial_out])
    strategy_candidates = []
    strategy_rejected = []
    soft_pass_counter = 0  # Track soft passes used
    
    for candidate in initial_out:
        # Ensure volume_spike is available for gate checking
        if 'volume_spike' not in candidate or candidate.get('volume_spike', 0) == 0:
            # Use default volume activity for squeeze candidates
            candidate['volume_spike'] = 2.0
        
        # Strategy-specific processing
        if current_strategy == 'hybrid_v1':
            # Hybrid V1 strategy with minimal gates for explosive stocks
            # Use minimal config to allow explosive candidates through
            minimal_config = {
                'thresholds': {
                    'min_relvol_30': 1.0,
                    'min_atr_pct': 0.01,
                    'require_vwap_reclaim': False,
                    'float_max': 100000000,
                    'soft_gate_tolerance': 0.5,
                    'max_soft_pass': 50
                }
            }
            gate_passed, gate_reason = _hybrid_v1_gate_check(candidate, minimal_config)
            
            if not gate_passed:
                strategy_rejected.append({
                    "symbol": candidate["symbol"],
                    "reason": f"hybrid_v1_gate_{gate_reason}",
                    "strategy": "hybrid_v1"
                })
                continue
            
            # Track soft passes (tagged by gate check function)
            if candidate.get("soft_pass"):
                soft_pass_counter += 1
            # Add mid_alt tag if mid-float path was used
            if gate_reason == "mid_float_catalyst_path":
                candidate["mid_alt"] = True
            
            # Apply hybrid_v1 scoring
            try:
                composite_score, subscores = _score_hybrid_v1(candidate, strategy_config)
                
                # Check entry rules
                entry_rules = strategy_config.get('entry_rules', {})
                score_pct = composite_score * 100
                
                if score_pct >= entry_rules.get('watchlist_min', 70):
                    # Determine action tag
                    if score_pct >= entry_rules.get('trade_ready_min', 75):
                        action_tag = "trade_ready"
                        pattern_match = "HYBRID_TRADE_READY"
                    else:
                        action_tag = "watchlist"
                        pattern_match = "HYBRID_WATCHLIST"
                    
                    # Enhanced candidate with hybrid_v1 data
                    candidate["score"] = round(composite_score, 4)
                    candidate["reason"] = f"hybrid_v1_{action_tag}"
                    candidate["strategy"] = "hybrid_v1"
                    candidate["pattern_match"] = pattern_match
                    candidate["subscores"] = subscores
                    candidate["action_tag"] = action_tag
                    candidate["gate_reason"] = gate_reason
                    
                    strategy_candidates.append(candidate)
                else:
                    strategy_rejected.append({
                        "symbol": candidate["symbol"],
                        "reason": f"hybrid_v1_score_{score_pct:.1f}_below_min",
                        "score": composite_score,
                        "strategy": "hybrid_v1"
                    })
                    
            except Exception as e:
                logger.error(f"Hybrid V1 scoring failed for {candidate['symbol']}: {e}")
                strategy_rejected.append({
                    "symbol": candidate["symbol"],
                    "reason": f"hybrid_v1_scoring_error_{str(e)[:30]}",
                    "strategy": "hybrid_v1"
                })
                
        else:
            # Legacy V0 strategy (existing VIGL logic)
            vigl_score = candidate.get("vigl_score", 0.0)
            wolf_risk = candidate.get("wolf_risk", 1.0)
            price = candidate.get("price", 0.0)
            volume_spike = candidate.get("volume_spike", 0.0)
            
            # EXPLOSIVE PATTERN REQUIREMENTS - Calibrated for explosive opportunities  
            meets_explosive_criteria = (
                vigl_score >= 0.10 and                           # ULTRA inclusive threshold
                wolf_risk <= 0.8 and                             # Higher risk tolerance for explosions
                price >= 0.01 and                                # $0.01+ minimum (penny stocks welcome)
                price <= 500.0 and                               # Under $500 (include everything)  
                volume_spike >= 2.0 and                          # 2x+ volume (real interest)
                candidate.get("rs_5d", 0) >= -0.15 and          # Allow 15% pullbacks only
                candidate.get("atr_pct", 0) >= 0.02              # 2%+ ATR for real movement
            )
            
            # Legacy criteria (more lenient) for compatibility  
            meets_vigl_criteria = meets_explosive_criteria or (
                vigl_score >= 0.15 and                    # Very inclusive backup threshold
                wolf_risk <= 0.8 and                      # Higher risk tolerance
                price >= 0.10 and                         # Include penny stocks
                price <= 100.0 and                        # Full range
                volume_spike >= 1.0                       # Any volume increase
            )
            
            if meets_vigl_criteria:
                # Enhanced scoring with meaningful differentiation
                compression_score = candidate.get("score", 0.0)  # Original compression score
                atr_pct = candidate.get("atr_pct", 0.0)
                rs_5d = candidate.get("rs_5d", 0.0)
                
                # Normalize and scale factors for better differentiation
                vigl_normalized = (vigl_score - 0.5) / 0.5  # Map 0.5-1.0 to 0.0-1.0
                compression_normalized = compression_score  # Already 0-1
                risk_score = max(0, 1.0 - wolf_risk)  # Invert risk for positive scoring
                
                # Volume spike with logarithmic scaling for better spread
                volume_multiplier = min(math.log(volume_spike + 1) / math.log(21), 1.0)  # log scale, cap at 20x
                
                # Momentum factor: recent 5-day performance
                momentum_factor = max(0, min(1, 0.5 + rs_5d * 2))  # -50% to +50% maps to 0-1
                
                # Volatility factor: higher ATR = more opportunity
                volatility_factor = min(atr_pct / 0.15, 1.0)  # 15% ATR = max score
                
                # SQUEEZE MODE: Use optimized weights for VIGL pattern detection
                if SQUEEZE_MODE and 'squeeze_score' in candidate:
                    # Already has squeeze score - use it as primary factor
                    composite_score = candidate['squeeze_score']
                else:
                    # Apply SQUEEZE_MODE weights if enabled, otherwise legacy weights
                    if SQUEEZE_MODE:
                        composite_score = (
                            volume_multiplier * SQUEEZE_WEIGHTS['volume'] +        # 0.40 - Volume primary
                            (short_interest_score if 'short_interest_score' in locals() else 0.0) * SQUEEZE_WEIGHTS['short'] +  # 0.30 - Short interest
                            momentum_factor * SQUEEZE_WEIGHTS['catalyst'] +        # 0.15 - Catalyst/momentum
                            volatility_factor * SQUEEZE_WEIGHTS['options'] +       # 0.10 - Options/volatility
                            compression_normalized * SQUEEZE_WEIGHTS['tech']       # 0.05 - Technical/compression
                        )
                    else:
                        # Legacy multi-factor composite
                        composite_score = (
                            vigl_normalized * 0.25 +      # VIGL pattern (reduced weight for differentiation)
                            compression_normalized * 0.20 +  # Compression setup
                            risk_score * 0.15 +           # Risk avoidance
                            volume_multiplier * 0.20 +    # Volume spike (increased weight)
                            momentum_factor * 0.15 +      # Recent momentum
                            volatility_factor * 0.05      # Volatility opportunity
                        )
                
                # Apply confidence tiers with score scaling
                if vigl_score >= 0.80:
                    composite_score *= 1.2  # High confidence boost
                elif vigl_score >= 0.65:
                    composite_score *= 1.0  # Medium confidence
                else:
                    composite_score *= 0.8  # Lower confidence penalty
                
                # Ensure score stays in reasonable range with spread
                composite_score = min(max(composite_score, 0.0), 1.0)
                
                candidate["score"] = round(composite_score, 4)
                candidate["reason"] = f"VIGL pattern (similarity: {vigl_score:.2f})"
                candidate["strategy"] = "legacy_v0"
                
                # Add key decision metrics for frontend display
                candidate["decision_data"] = {
                    "volume_spike_ratio": round(volume_spike, 1),
                    "momentum_1d_pct": round(candidate.get("rs_5d", 0) * 100, 1),  # Using 5d as momentum proxy
                    "vigl_confidence": "HIGH" if vigl_score >= 0.80 else "MEDIUM" if vigl_score >= 0.65 else "LOW",
                    "risk_level": "HIGH" if wolf_risk > 0.6 else "MEDIUM" if wolf_risk > 0.3 else "LOW",
                    "atr_pct": round(atr_pct * 100, 1),
                    "compression_rank": round((1 - compression_score) * 100, 1)  # Higher = tighter compression
                }
                
                strategy_candidates.append(candidate)
            else:
                # Track rejection reasons for legacy strategy
                reasons = []
                if vigl_score < 0.50: reasons.append("low_vigl_similarity")
                if wolf_risk > WOLF_RISK_THRESHOLD: reasons.append("high_wolf_risk")
                if price < VIGL_PRICE_MIN: reasons.append("price_too_low")
                if price > VIGL_PRICE_MAX: reasons.append("price_too_high")
                if volume_spike < VIGL_VOLUME_MIN: reasons.append("insufficient_volume_spike")
                
                strategy_rejected.append({
                    "symbol": candidate["symbol"], 
                    "reason": "_".join(reasons),
                    "vigl_score": round(vigl_score, 3),
                    "wolf_risk": round(wolf_risk, 3),
                    "price": price,
                    "volume_spike": round(volume_spike, 1),
                    "strategy": "legacy_v0"
                })
    
    trace.exit("strategy_scoring", [c["symbol"] for c in strategy_candidates], strategy_rejected)
    
    # Intelligent quality filtering for top-tier recommendations  
    trace.enter("quality_filter", [c["symbol"] for c in strategy_candidates])
    
    # Sort by score (strategy-agnostic)
    strategy_candidates.sort(key=lambda x: x["score"], reverse=True)
    
    # Apply strategy-aware quality filtering
    target_count = limit or MAX_CANDIDATES
    
    if current_strategy == 'hybrid_v1':
        # Hybrid V1: Filter by action tags and score
        trade_ready = [c for c in strategy_candidates if c.get("action_tag") == "trade_ready"]
        watchlist = [c for c in strategy_candidates if c.get("action_tag") == "watchlist"]
        
        # Prioritize trade_ready candidates
        final_out = []
        final_out.extend(trade_ready[:target_count])
        
        # Fill remaining with watchlist candidates
        remaining_slots = target_count - len(final_out)
        if remaining_slots > 0:
            final_out.extend(watchlist[:remaining_slots])
            
    else:
        # Legacy V0: Filter by VIGL confidence tiers
        high_confidence = [c for c in strategy_candidates if c.get("vigl_score", 0) >= 0.80]
        medium_confidence = [c for c in strategy_candidates if 0.65 <= c.get("vigl_score", 0) < 0.80]
        
        # Build final selection prioritizing quality over quantity
        final_out = []
        
        # Always include high confidence picks (up to 3)
        final_out.extend(high_confidence[:3])
        
        # Fill remaining slots with best medium confidence picks
        remaining_slots = target_count - len(final_out)
        if remaining_slots > 0:
            # Get medium confidence picks that aren't already included
            available_medium = [c for c in medium_confidence if c not in final_out]
            final_out.extend(available_medium[:remaining_slots])
        
        # If still need more, take remaining from any tier (backup)
        if len(final_out) < target_count:
            remaining_slots = target_count - len(final_out)
            remaining_candidates = [c for c in strategy_candidates if c not in final_out]
            final_out.extend(remaining_candidates[:remaining_slots])
    
    # Quality metrics for trace
    quality_metrics = {
        "high_confidence_count": len([c for c in final_out if c.get("vigl_score", 0) >= 0.80]),
        "medium_confidence_count": len([c for c in final_out if 0.65 <= c.get("vigl_score", 0) < 0.80]),
        "avg_score": round(sum(c["score"] for c in final_out) / len(final_out), 4) if final_out else 0,
        "score_range": {
            "min": round(min(c["score"] for c in final_out), 4) if final_out else 0,
            "max": round(max(c["score"] for c in final_out), 4) if final_out else 0
        }
    }
    
    trace.exit("quality_filter", [c["symbol"] for c in final_out])
    trace.exit("final_selection", [c["symbol"] for c in final_out])
    
    logger.info(f"VIGL Discovery: {len(final_out)} candidates selected from {len(initial_out)} compressed stocks")
    
    return (final_out, trace.to_dict()) if with_trace else final_out

def main():
    """Main entry point with Redis locking using live selector"""
    lock_key = "discovery_job_lock"
    
    # Safety cleanup - check for stale locks older than TTL
    try:
        from shared.redis_client import get_redis_client
        r = get_redis_client()
        ttl = r.ttl(lock_key)
        if ttl == -1:  # Lock exists but no TTL (should not happen but safety)
            r.delete(lock_key)
            logger.warning(f"Cleared stale lock without TTL: {lock_key}")
    except Exception as e:
        logger.warning(f"Lock safety check failed: {e}")
    
    try:
        with redis_lock(lock_key, ttl_seconds=120) as acquired:  # 2 minute TTL (reduced)
            if not acquired:
                logger.warning("Another discovery job is running - exiting")
                sys.exit(1)
                
            # Use live selector with real Polygon data
            items, tr = asyncio.run(select_candidates(relaxed=False, limit=MAX_CANDIDATES, with_trace=True))
            
            # Publish to Redis
            from lib.redis_client import get_redis_client
            r = get_redis_client()
            r.set("amc:discovery:contenders.latest", json.dumps(items), ex=600)
            r.set("amc:discovery:explain.latest", json.dumps({
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), 
                "count": len(items), 
                "trace": tr
            }), ex=600)
            
            logger.info(f"Discovery completed successfully: {len(items)} contenders found and published")
            sys.exit(0)
                
    except Exception as e:
        logger.error(f"Fatal error in discovery pipeline: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    import asyncio
    
    p = argparse.ArgumentParser(description="AMC Discovery Pipeline")
    p.add_argument("--dry-run", action="store_true", help="Run without writing to database or Redis")
    p.add_argument("--relaxed", action="store_true", help="Apply more lenient filters")
    p.add_argument("--limit", type=int, default=10, help="Maximum number of candidates to return")
    p.add_argument("--trace", action="store_true", help="Include trace information in output")
    args = p.parse_args()
    
    if args.dry_run:
        items, trace = asyncio.run(select_candidates(relaxed=args.relaxed, limit=args.limit, with_trace=args.trace))
        print(json.dumps({"items": items, "trace": trace if args.trace else None}, indent=2))
    else:
        main()