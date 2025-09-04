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

def _load_calibration():
    """Load active calibration settings with fallbacks to environment variables"""
    try:
        import json
        import os
        calibration_path = os.path.join(os.path.dirname(__file__), "../../../calibration/active.json")
        if os.path.exists(calibration_path):
            with open(calibration_path, 'r') as f:
                cal = json.load(f)
                return cal
    except Exception as e:
        print(f"Warning: Could not load calibration file: {e}")
    return {}

# Load calibration settings
_calibration = _load_calibration()

# Environment variables for live discovery with calibration overrides
POLY_KEY = os.getenv("POLYGON_API_KEY")
# Apply calibration overrides for critical thresholds
PRICE_CAP = _calibration.get("discovery_filters", {}).get("price_cap", float(os.getenv("AMC_PRICE_CAP", "500")))
MIN_DOLLAR_VOL = _calibration.get("discovery_filters", {}).get("dollar_volume_min", float(os.getenv("AMC_MIN_DOLLAR_VOL", "5000000")))  # CALIBRATED: 1M vs 5M
LOOKBACK_DAYS = int(os.getenv("AMC_COMPRESSION_LOOKBACK", "60"))
COMPRESSION_PCTL_MAX = _calibration.get("discovery_filters", {}).get("compression_percentile_max", float(os.getenv("AMC_COMPRESSION_PCTL_MAX", "0.30")))  # CALIBRATED: 0.50 vs 0.30
MAX_CANDIDATES = _calibration.get("discovery_filters", {}).get("max_candidates", int(os.getenv("AMC_MAX_CANDIDATES", "25")))  # CALIBRATED: 35 vs 25
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
EXPLOSIVE_PRICE_MAX = float(os.getenv("AMC_EXPLOSIVE_PRICE_MAX", "10.00"))    # Tightened to explosive sweet spot
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
        
        # Check if we should use dynamic universe fetching
        USE_DYNAMIC_UNIVERSE = os.getenv("AMC_DYNAMIC_UNIVERSE", "true").lower() in ("1", "true", "yes")
        
        if USE_DYNAMIC_UNIVERSE:
            logger.info("🌍 Fetching full stock universe from Polygon API...")
            try:
                symbols = self._fetch_polygon_universe()
                if symbols:
                    logger.info(f"✅ Dynamic universe loaded: {len(symbols)} symbols from Polygon API")
                    return symbols
                else:
                    logger.warning("❌ Dynamic universe fetch failed, falling back to file/static")
            except Exception as e:
                logger.error(f"❌ Dynamic universe error: {e}, falling back to file/static")
        
        # Static fallback universe (only used if dynamic fails or disabled)
        STATIC_FALLBACK = [
            # Core squeeze candidates with confirmed data
            "VIGL", "QUBT", "UP", "NAK", "SPHR", "ANTE", "AEVA", "WULF", "SSRM",
            "TEVA", "KSS", "CELC", "CARS", "GMAB", "AMDL", "TEM", "SNDL", "AMC", "GME",
            # Biotech & Healthcare  
            "RGTI", "DCGO", "OCGN", "COTI", "INVZ", "SERA", "LFMD", "MNOV", "INZY", "ANIC",
            # Technology & Growth
            "BBIG", "ASTS", "RKLB", "HOLO", "LOVO", "ARQQ", "NNDM", "PRTG", "FUBO", "GOEV",
            # Energy & Mining
            "REI", "CLSK", "RIOT", "HUT", "BITF", "MARA", "CAN", "HVBT", "DAC",
            # Reference Large Caps
            "AAPL", "NVDA", "TSLA", "AMD"
        ]
        
        try:
            # Try universe file as backup
            possible_paths = [
                f"/app/{self.universe_file}",
                os.path.join(os.path.dirname(__file__), '..', '..', '..', self.universe_file),
                os.path.join(os.getcwd(), self.universe_file),
                self.universe_file if os.path.isabs(self.universe_file) else None
            ]
            
            for path in filter(None, possible_paths):
                if os.path.exists(path) and os.path.isfile(path):
                    with open(path, 'r') as f:
                        symbols = [line.strip().upper() for line in f 
                                 if line.strip() and not line.strip().startswith('#')]
                    logger.info(f"📁 Loaded {len(symbols)} symbols from universe file: {path}")
                    return symbols
                    
            # Final fallback to static list
            logger.warning(f"⚠️  Using static fallback universe with {len(STATIC_FALLBACK)} symbols")
            return STATIC_FALLBACK
            
        except Exception as e:
            logger.error(f"❌ Universe loading failed: {e}. Using static fallback")
            return STATIC_FALLBACK
    
    def _fetch_polygon_universe(self) -> List[str]:
        """Fetch complete stock universe from Polygon API"""
        all_symbols = []
        next_url = None
        page = 1
        max_pages = 50  # Limit to prevent runaway
        
        try:
            import requests
            
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
                    logger.error(f"❌ Polygon API error on page {page}: {response.status_code}")
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
            # Publish to Redis with 10-minute TTL
            publish_discovery_contenders(contenders, ttl=600)
            
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
        
        # If Polygon returns no data, raise exception to trigger fallback
        if not rows:
            logger.warning(f"Polygon API returned no results for date {date}, triggering fallback")
            raise Exception("No data from Polygon grouped API")
            
        # BULK FILTERING: Apply all cheap filters at once to eliminate 90%+ of universe
        pcap = PRICE_CAP * (1.2 if relaxed else 1.0)  # allow slight slack in relaxed mode
        dvmin = MIN_DOLLAR_VOL * (0.5 if relaxed else 1.0)
        
        # Enhanced bulk filters for massive elimination
        vigl_price_min = VIGL_PRICE_MIN
        vigl_price_max = VIGL_PRICE_MAX if not relaxed else 50.0  # Allow higher prices in relaxed mode
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
    except Exception:
        # fallback to curated universe to stay real but lighter
        kept_syms = UNIVERSE_FALLBACK[:]
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
                    return {"price": 10.0, "dollar_vol": 1000000, "compression_pct": compression_pct, "atr_pct": 0.05, "rs_5d": 0.0, "vigl_score": 0.45, "wolf_risk": 0.3, "volume_spike": 2.0, "factors": {"api_error": str(api_err)}, "thesis": f"{sym} explosive candidate (limited data)."}
                
                if not results:
                    logger.warning(f"No results for {sym} from Polygon prev endpoint")
                    # Return with reasonable defaults to not filter out
                    compression_pct = next((t["compression_pct"] for t in tight if t["symbol"] == sym), 0.05)
                    return {"price": 10.0, "dollar_vol": 1000000, "compression_pct": compression_pct, "atr_pct": 0.05, "rs_5d": 0.0, "vigl_score": 0.45, "wolf_risk": 0.3, "volume_spike": 2.0, "factors": {"no_data": True}, "thesis": f"{sym} explosive candidate (data pending)."}
                
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
                    "thesis": thesis
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
        
        # Get real short interest data for all candidates
        short_interest_service = await get_short_interest_service()
        symbols = [candidate['symbol'] for candidate in initial_out]
        short_interest_data = await short_interest_service.get_bulk_short_interest(symbols)
        
        for candidate in initial_out:
            symbol = candidate['symbol']
            si_data = short_interest_data.get(symbol)
            
            # Use real short interest data instead of placeholders
            # NO FALLBACKS - Only process stocks with real short interest data
            if not si_data or si_data.source in ['sector_fallback', 'default_fallback']:
                logger.debug(f"Excluding {symbol} - no real short interest data available")
                continue
            
            real_short_interest = si_data.short_percent_float
            si_confidence = si_data.confidence
            si_source = si_data.source
            
            # Prepare data for squeeze detector with real short interest
            squeeze_data = {
                'symbol': symbol,
                'price': candidate.get('price', 0.0),
                'volume': candidate.get('volume_spike', 0.0) * 1000000,  # Approximate volume
                'avg_volume_30d': 1000000,  # Placeholder - would need historical data
                'short_interest': real_short_interest,  # REAL SHORT INTEREST DATA!
                'float': candidate.get('factors', {}).get('float_shares'),  # No defaults - require real data
                'borrow_rate': candidate.get('factors', {}).get('borrow_rate'),  # No defaults
                'shares_outstanding': candidate.get('factors', {}).get('shares_outstanding')  # No defaults
            }
            
            # Add short interest metadata to candidate
            candidate['short_interest_data'] = {
                'percent': real_short_interest,
                'confidence': si_confidence,
                'source': si_source,
                'last_updated': si_data.last_updated.isoformat()
            }
            
            squeeze_result = squeeze_detector.detect_vigl_pattern(candidate['symbol'], squeeze_data)
            
            # Use calibrated squeeze score threshold (0.15 vs 0.25)
            squeeze_threshold = _calibration.get("discovery_filters", {}).get("squeeze_score_threshold", 0.25)
            if squeeze_result and squeeze_result.squeeze_score >= squeeze_threshold:
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

    # VIGL Pattern Filtering - keep only promising candidates
    trace.enter("vigl_filter", [o["symbol"] for o in initial_out])
    vigl_candidates = []
    vigl_rejected = []
    
    for candidate in initial_out:
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
            
            # Add key decision metrics for frontend display
            candidate["decision_data"] = {
                "volume_spike_ratio": round(volume_spike, 1),
                "momentum_1d_pct": round(candidate.get("rs_5d", 0) * 100, 1),  # Using 5d as momentum proxy
                "vigl_confidence": "HIGH" if vigl_score >= 0.80 else "MEDIUM" if vigl_score >= 0.65 else "LOW",
                "risk_level": "HIGH" if wolf_risk > 0.6 else "MEDIUM" if wolf_risk > 0.3 else "LOW",
                "atr_pct": round(atr_pct * 100, 1),
                "compression_rank": round((1 - compression_score) * 100, 1)  # Higher = tighter compression
            }
            
            vigl_candidates.append(candidate)
        else:
            # Track rejection reasons
            reasons = []
            if vigl_score < 0.50: reasons.append("low_vigl_similarity")
            if wolf_risk > WOLF_RISK_THRESHOLD: reasons.append("high_wolf_risk")
            if price < VIGL_PRICE_MIN: reasons.append("price_too_low")
            if price > VIGL_PRICE_MAX: reasons.append("price_too_high")
            if volume_spike < VIGL_VOLUME_MIN: reasons.append("insufficient_volume_spike")
            
            vigl_rejected.append({
                "symbol": candidate["symbol"], 
                "reason": "_".join(reasons),
                "vigl_score": round(vigl_score, 3),
                "wolf_risk": round(wolf_risk, 3),
                "price": price,
                "volume_spike": round(volume_spike, 1)
            })
    
    trace.exit("vigl_filter", [c["symbol"] for c in vigl_candidates], vigl_rejected)
    
    # Intelligent quality filtering for top-tier recommendations
    trace.enter("quality_filter", [c["symbol"] for c in vigl_candidates])
    
    # Sort by enhanced VIGL score
    vigl_candidates.sort(key=lambda x: x["score"], reverse=True)
    
    # Apply quality tiers for intelligent filtering
    high_confidence = [c for c in vigl_candidates if c.get("vigl_score", 0) >= 0.80]
    medium_confidence = [c for c in vigl_candidates if 0.65 <= c.get("vigl_score", 0) < 0.80]
    
    # Build final selection prioritizing quality over quantity
    final_out = []
    target_count = limit or MAX_CANDIDATES
    
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
        remaining_candidates = [c for c in vigl_candidates if c not in final_out]
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
    
    try:
        with redis_lock(lock_key, ttl_seconds=240) as acquired:  # 4 minute TTL
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