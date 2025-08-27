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

# Environment variables for live discovery
POLY_KEY = os.getenv("POLYGON_API_KEY")
AMC_PRICE_CAP = float(os.getenv("AMC_PRICE_CAP", "100"))
AMC_MIN_DOLLAR_VOL = float(os.getenv("AMC_MIN_DOLLAR_VOL", "20000000"))
LOOKBACK_DAYS = int(os.getenv("AMC_COMPRESSION_LOOKBACK", "60"))
COMPRESSION_PCTL_MAX = float(os.getenv("AMC_COMPRESSION_PCTL_MAX", "0.15"))  # tightest 15%
MAX_CANDIDATES = int(os.getenv("AMC_MAX_CANDIDATES", "15"))
UNIVERSE_FALLBACK = [s.strip().upper() for s in os.getenv("AMC_DISCOVERY_UNIVERSE","AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA,AMD,AVGO,PLTR,COIN,CRM,ORCL,ABNB,SNOW,UBER,NFLX,SHOP,INTC,MRVL,SMCI").split(",") if s.strip()]

# Strict classification (drop any non-equity when enabled)
EXCLUDE_FUNDS        = os.getenv("AMC_EXCLUDE_FUNDS","true").lower()=="true"
EXCLUDE_ADRS         = os.getenv("AMC_EXCLUDE_ADRS","true").lower()=="true"
EXCLUDE_FUNDS_STRICT = os.getenv("AMC_EXCLUDE_FUNDS_STRICT","1") in ("1","true","yes")
FUND_TYPES = {"ETF","ETN","FUND","INDEX","MUTUALFUND","TRUST","CEFT","BOND","ETFWRAP"}

# Known ETF/Fund symbols guard set (common funds that might slip through)
KNOWN_FUND_SYMBOLS = {
    # ETFs
    "SPY", "QQQ", "IWM", "DIA", "VOO", "VTI", "SCHB", "ITOT", "VEA", "IEMG", "VWO", "EFA", "AGG", "BND", 
    "GLD", "SLV", "USO", "XLE", "XLF", "XLK", "XLI", "XLU", "XLY", "XLP", "XLV", "XLB", "XLRE", "XLC",
    "ARKK", "ARKQ", "ARKW", "ARKG", "ARKF", "ARKX", "VUG", "VTV", "VIG", "VYM", "SCHD", "DVY", "HDV",
    "IVV", "IVE", "IVW", "IJH", "IJR", "MDY", "SLY", "VIXY", "UVXY", "SVXY", "VXX", "SQQQ", "TQQQ",
    "SPXU", "SPXL", "UPRO", "TMF", "TLT", "IEF", "SHY", "HYG", "JNK", "EMB", "LQD", "TIP", "VTIP",
    "BSV", "BIV", "BLV", "VCSH", "VCIT", "VCLT", "VGSH", "VGIT", "VGLT", "VMBS", "GOVT", "CORP",
    "EEM", "VEU", "VXUS", "IXUS", "ACWI", "ACWX", "EWJ", "EWZ", "EWY", "EWG", "EWU", "FXI", "INDA",
    "RSX", "EWC", "EWA", "EWT", "EWH", "EWS", "EWM", "EWP", "EWI", "EWQ", "EWN", "EWL", "ERUS",
    "JETS", "ICLN", "TAN", "FAN", "PBW", "QCLN", "LIT", "REMX", "PICK", "COPX", "GDX", "GDXJ", "SILJ",
    "KRE", "XLF", "KBE", "KIE", "IAK", "IYG", "VFH", "FAS", "FAZ", "XBI", "IBB", "LABU", "LABD", "CURE",
    "XRT", "RTH", "XHB", "ITB", "NAIL", "DRN", "SOXL", "SOXS", "SMH", "SOXX", "PSI", "QTEC", "IGV",
    "HACK", "CIBR", "FINX", "GNOM", "IDNA", "ROBO", "BOTZ", "CLOU", "SKYY", "HERO", "NERD", "ESPO",
    "UFO", "MOON", "KOMP", "KRBN", "DRIV", "IDRV", "KARS", "HAIL", "MJ", "YOLO", "THCX", "CNBS", "TOKE",
    "PEJ", "PBS", "PEY", "PID", "KBWB", "KCE", "KBWD", "KBWY", "KBWR", "IAI", "ITA", "PPA", "XAR",
    "DFEN", "IEO", "IEZ", "IHI", "IHF", "IYT", "IYC", "IYE", "IYF", "IYH", "IYJ", "IYK", "IYM", "IYR",
    "IYW", "IYZ", "VAW", "VCR", "VDC", "VDE", "VFH", "VGT", "VHT", "VIS", "VNQ", "VOX", "VPU", "VB",
    "VO", "VTWO", "VBR", "VBK", "VOE", "VOT", "VTV", "VUG", "VIOG", "VIOO", "VIOV", "VONE", "VTHR",
    "DFAS", "DFAU", "DFAC", "DFAT", "DFAX", "DFUS", "AVUS", "AVUV", "AVDV", "AVDE", "AVEM",
    "SCHO", "SCHP", "SCHQ", "SCHM", "SCHA", "SCHF", "SCHE", "SCHC", "SCHG", "SCHV", "SCHX", "SCHZ",
    "HIMU", "KSA", "KWT", "UAE", "QAT", "EGY", "GAF", "NGE", "AFK", "EZA", "FM", "FLZA",
    # Additional hardcoded guard symbols for leakage prevention
    "IYH", "VXX", "VNQ",
}

# Common fund/ETF name patterns
FUND_NAME_PATTERNS = ["ETF", "FUND", "INDEX", "TRUST", "BOND", "TREASURY", "NOTE", "BILL", "SHARES", "PROSHARES", "ISHARES", "VANGUARD", "SPDR", "INVESCO", "WISDOMTREE", "DIREXION", "VANECK", "GLOBAL X"]

# weights (renormalize to available factors)
W_VOLUME   = float(os.getenv("AMC_W_VOLUME",   "0.25"))
W_SHORT    = float(os.getenv("AMC_W_SHORT",    "0.20"))
W_CATALYST = float(os.getenv("AMC_W_CATALYST", "0.20"))
W_SENT     = float(os.getenv("AMC_W_SENT",     "0.15"))
W_OPTIONS  = float(os.getenv("AMC_W_OPTIONS",  "0.10"))
W_TECH     = float(os.getenv("AMC_W_TECH",     "0.10"))

# sector momentum knobs
AMC_ENABLE_SECTOR = bool(int(os.getenv("AMC_ENABLE_SECTOR","1")))
AMC_W_SECTOR      = float(os.getenv("AMC_W_SECTOR","0.10"))   # weight in 0..1, renormalized if disabled
# JSON map: theme -> ETF ticker (used only for momentum; ETFs are never candidates)
AMC_SECTOR_ETFS   = os.getenv("AMC_SECTOR_ETFS",
  '{"BIOTECH":"XBI","SEMIS":"SMH","AI_SOFTWARE":"IGV","EV":"CARZ","ENERGY":"XLE","URANIUM":"URA","GOLD_MINERS":"GDX","AIRLINES":"JETS","RETAIL":"XRT","SMALL_CAP":"IWM"}'
)

# thresholds
REL_VOL_MIN  = float(os.getenv("AMC_REL_VOL_MIN",  "3"))
ATR_PCT_MIN  = float(os.getenv("AMC_ATR_PCT_MIN",  "0.04"))
FLOAT_MAX    = float(os.getenv("AMC_FLOAT_MAX",    "50000000"))
BIG_FLOAT_MIN= float(os.getenv("AMC_BIG_FLOAT_MIN","150000000"))
SI_MIN       = float(os.getenv("AMC_SI_MIN",       "0.20"))
BORROW_MIN   = float(os.getenv("AMC_BORROW_MIN",   "0.20"))
UTIL_MIN     = float(os.getenv("AMC_UTIL_MIN",     "0.85"))
IV_PCTL_MIN  = float(os.getenv("AMC_IV_PCTL_MIN",  "0.80"))
PCR_MIN      = float(os.getenv("AMC_PCR_MIN",      "2.0"))

INTRADAY     = bool(int(os.getenv("AMC_INTRADAY", "0")))  # 1 to enable minute features

# ATR-based targets and brackets
R_MULT         = float(os.getenv("AMC_R_MULT", "2.0"))        # target = entry + R_MULT * risk
ATR_STOP_MULT  = float(os.getenv("AMC_ATR_STOP_MULT", "1.5")) # stop = entry - ATR_STOP_MULT * ATR_abs
MIN_STOP_PCT   = float(os.getenv("AMC_MIN_STOP_PCT", "0.02")) # 2% floor

# Pipeline versioning and Redis keys
PIPELINE_TAG = os.getenv("AMC_PIPELINE_TAG", "squeeze-v1")
REDIS_KEY_V2_CONT = "amc:discovery:v2:contenders.latest"
REDIS_KEY_V2_TRACE = "amc:discovery:v2:explain.latest"
REDIS_KEY_V1_CONT = "amc:discovery:contenders.latest"
REDIS_KEY_V1_TRACE = "amc:discovery:explain.latest"
REDIS_KEY_STATUS   = "amc:discovery:status"

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

# Cache for intraday data
_minute_cache = {}

async def _minute_bars_today(client, sym):
    """Fetch today's minute bars for VWAP and relative volume"""
    if sym in _minute_cache:
        return _minute_cache[sym]
    
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        data = await _poly_get(client, f"/v2/aggs/ticker/{sym}/range/1/minute/{today}/{today}", 
                               params={"adjusted":"true","limit":"2000"}, timeout=15)
        results = data.get("results") or []
        _minute_cache[sym] = results
        return results
    except Exception:
        _minute_cache[sym] = []
        return []

def _compute_vwap_relvol(minute_bars):
    """Compute VWAP and 30m relative volume from minute bars"""
    if not minute_bars or len(minute_bars) < 30:
        return None, None
    
    # VWAP calculation
    total_pv = sum(bar.get("c", 0) * bar.get("v", 0) for bar in minute_bars)
    total_vol = sum(bar.get("v", 0) for bar in minute_bars)
    vwap = total_pv / total_vol if total_vol > 0 else 0
    
    # Current price vs VWAP
    current_price = minute_bars[-1].get("c", 0) if minute_bars else 0
    above_vwap = current_price > vwap if vwap > 0 else False
    
    # 30-minute relative volume (approximate)
    last_30_bars = minute_bars[-30:] if len(minute_bars) >= 30 else minute_bars
    vol_30m = sum(bar.get("v", 0) for bar in last_30_bars)
    
    # For simplicity, assume average 30m volume is daily_volume / 13 (6.5 hour trading day / 0.5hr)
    # This is approximate - in production you'd use historical 30m averages
    avg_daily_vol = total_vol * (390 / len(minute_bars)) if minute_bars else 1
    avg_30m_vol = avg_daily_vol / 13 if avg_daily_vol > 0 else 1
    rel_vol_30m = vol_30m / avg_30m_vol if avg_30m_vol > 0 else 1.0
    
    return above_vwap, rel_vol_30m

async def _get_float_approx(client, sym):
    """Get approximate float from Polygon reference API"""
    try:
        data = await _poly_get(client, f"/v3/reference/tickers/{sym}", timeout=10)
        results = data.get("results", {})
        shares = results.get("shares_outstanding") or results.get("share_class_shares_outstanding")
        return float(shares) if shares else None
    except Exception:
        return None

async def _get_news_catalyst_score(client, sym):
    """Score news catalyst from last 5 days"""
    try:
        from_date = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")
        data = await _poly_get(client, f"/v2/reference/news", 
                               params={"ticker": sym, "published_utc.gte": from_date, "limit": "50"}, timeout=10)
        
        results = data.get("results") or []
        if not results:
            return "none", 0.0
        
        # Check for high-impact catalyst keywords
        high_impact_keywords = ["earnings beat", "fda approval", "m&a", "merger", "acquisition", "contract", "partnership"]
        catalyst_tag = "none"
        catalyst_score = 0.5  # Base score for having any news
        
        for article in results:
            title = (article.get("title") or "").lower()
            keywords = (article.get("keywords") or [])
            
            # Check title and keywords for catalysts
            all_text = title + " " + " ".join(str(k).lower() for k in keywords)
            for keyword in high_impact_keywords:
                if keyword in all_text:
                    catalyst_tag = keyword.replace(" ", "_")
                    catalyst_score = 1.0
                    break
            
            if catalyst_score == 1.0:
                break
        
        return catalyst_tag, catalyst_score
    except Exception:
        return "none", 0.0

async def _get_options_flow(client, sym):
    """Get options flow metrics from Polygon (if available)"""
    try:
        # This would use Polygon options API - simplified version
        # In production, you'd fetch actual options data
        data = await _poly_get(client, f"/v3/reference/options/contracts", 
                               params={"underlying_ticker": sym, "limit": "10"}, timeout=10)
        
        # Placeholder - would calculate actual metrics from options data
        # For now, return None to indicate unavailable
        return {"pcr": None, "iv_pctl": None, "call_oi_up": None}
    except Exception:
        return {"pcr": None, "iv_pctl": None, "call_oi_up": None}

def _compute_technical_indicators(rows):
    """Compute EMA cross, RSI zone, green streak from daily bars"""
    if len(rows) < 21:
        return False, False, 0
    
    # Simple EMA calculation
    closes = [r.get("c", 0) for r in rows[-21:]]
    if not all(closes):
        return False, False, 0
    
    # EMA 9 and 20 (simplified)
    ema9 = sum(closes[-9:]) / 9 if len(closes) >= 9 else closes[-1]
    ema20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else closes[-1]
    ema_cross = ema9 > ema20
    
    # RSI zone (simplified - just check if not oversold)
    recent_closes = closes[-14:] if len(closes) >= 14 else closes
    gains = [max(0, recent_closes[i] - recent_closes[i-1]) for i in range(1, len(recent_closes))]
    losses = [max(0, recent_closes[i-1] - recent_closes[i]) for i in range(1, len(recent_closes))]
    avg_gain = sum(gains) / len(gains) if gains else 0
    avg_loss = sum(losses) / len(losses) if losses else 1e-9
    rsi = 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss > 0 else 50
    rsi_zone_ok = 30 < rsi < 80  # Not oversold or overbought
    
    # Green streak (consecutive up days)
    green_streak = 0
    for i in range(len(rows)-1, 0, -1):
        if rows[i].get("c", 0) > rows[i-1].get("c", 0):
            green_streak += 1
        else:
            break
    
    return ema_cross, rsi_zone_ok, green_streak

async def _get_etf_momentum(client, etf_ticker, days=20):
    """Get ETF momentum score over specified period"""
    try:
        daily_bars = await _daily_bars(client, etf_ticker, limit=days+5)
        if len(daily_bars) < days:
            return None
        
        # Calculate momentum as % return over period
        start_price = daily_bars[-(days+1)].get("c", 0)
        end_price = daily_bars[-1].get("c", 0)
        
        if not start_price or not end_price:
            return None
            
        momentum = (end_price - start_price) / start_price
        return float(momentum)
    except Exception:
        return None

def _classify_stock_sector(symbol):
    """Classify individual stocks into sectors based on symbol patterns and known mappings"""
    symbol = symbol.upper()
    
    # Biotech indicators
    if any(x in symbol for x in ['BIO', 'GENE', 'CELL', 'THER', 'VAX', 'CURE', 'MEDI']):
        return "BIOTECH"
    
    # Semiconductor indicators  
    if any(x in symbol for x in ['SEMI', 'CHIP', 'NVDA', 'AMD', 'AVGO', 'QCOM', 'INTC', 'MRVL']):
        return "SEMIS"
    
    # AI/Software indicators
    if any(x in symbol for x in ['SOFT', 'DATA', 'CLOUD', 'AI']):
        return "AI_SOFTWARE"
    
    # Energy indicators
    if any(x in symbol for x in ['OIL', 'GAS', 'PETRO', 'ENGY', 'XOM', 'CVX', 'COP']):
        return "ENERGY"
    
    # Known tech giants
    if symbol in ['AAPL', 'MSFT', 'GOOGL', 'GOOG', 'META', 'AMZN', 'NFLX']:
        return "AI_SOFTWARE" 
    
    # EV indicators
    if any(x in symbol for x in ['TESLA', 'TSLA', 'EV', 'ELEC', 'AUTO']):
        return "EV"
    
    # Default to small cap for unclassified
    return "SMALL_CAP"

async def _compute_sector_momentum_score(client, symbol, etf_map):
    """Compute sector momentum score using ETF proxies"""
    try:
        # Classify the stock into a sector
        sector = _classify_stock_sector(symbol)
        
        # Get the ETF ticker for this sector
        etf_ticker = etf_map.get(sector)
        if not etf_ticker:
            # Fall back to small cap ETF
            etf_ticker = etf_map.get("SMALL_CAP", "IWM")
        
        # Get ETF momentum
        momentum = await _get_etf_momentum(client, etf_ticker, days=20)
        if momentum is None:
            return 0.5  # Neutral score if no data
        
        # Convert momentum to 0-1 score
        # Positive momentum = higher score
        # Scale: -20% = 0, +20% = 1.0, 0% = 0.5
        score = max(0.0, min(1.0, (momentum + 0.2) / 0.4))
        
        return float(score)
    except Exception:
        return 0.5  # Neutral score on error

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
    # simple "yesterday" in UTC; Polygon accepts previous session
    return (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

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

async def compute_factors(sym, redis_client, client=None):
    """Compute all factors for squeeze detection"""
    factors = {}
    
    timeout = httpx.Timeout(25.0, connect=6.0)
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
    
    # Use passed client or create new one  
    use_existing_client = client is not None
    
    if not use_existing_client:
        client = httpx.AsyncClient(timeout=timeout, limits=limits)
    
    try:
        # Get daily bars for technical analysis
        daily_rows = await _daily_bars(client, sym, limit=LOOKBACK_DAYS+25)
        
        # Basic price/volume data
        if daily_rows:
            current_price = daily_rows[-1].get("c", 0)
            factors["atr_pct"] = _atr_pct(daily_rows) or 0.0
            factors["rs_5d"] = _return(daily_rows, 5) or 0.0
            ema_cross, rsi_zone_ok, green_streak = _compute_technical_indicators(daily_rows)
            factors["ema_cross"] = ema_cross
            factors["rsi_zone_ok"] = rsi_zone_ok  
            factors["green_streak"] = green_streak
        else:
            factors.update({"atr_pct": 0.0, "rs_5d": 0.0, "ema_cross": False, "rsi_zone_ok": False, "green_streak": 0})
        
        # Intraday data (if enabled)
        if INTRADAY and daily_rows:
            minute_bars = await _minute_bars_today(client, sym)
            above_vwap, rel_vol_30m = _compute_vwap_relvol(minute_bars)
            factors["above_vwap"] = above_vwap if above_vwap is not None else False
            factors["rel_vol_30m"] = rel_vol_30m if rel_vol_30m is not None else 1.0
        else:
            factors["above_vwap"] = False
            factors["rel_vol_30m"] = 1.0  # Default to normal volume
            
        # Float data
        factors["float"] = await _get_float_approx(client, sym)
        
        # Catalyst scoring
        catalyst_tag, catalyst_score = await _get_news_catalyst_score(client, sym)
        factors["catalyst_tag"] = catalyst_tag
        factors["catalyst_score"] = catalyst_score
        
        # Options flow (if available)
        options_data = await _get_options_flow(client, sym)
        factors["pcr"] = options_data.get("pcr")
        factors["iv_pctl"] = options_data.get("iv_pctl") 
        factors["call_oi_up"] = options_data.get("call_oi_up")
        
    except Exception as e:
        logger.warning(f"Error fetching market data for {sym}: {e}")
        # Set defaults for failed fetches
        factors.update({
            "atr_pct": 0.0, "rs_5d": 0.0, "above_vwap": False, "rel_vol_30m": 1.0,
            "ema_cross": False, "rsi_zone_ok": False, "green_streak": 0,
            "float": None, "catalyst_tag": "none", "catalyst_score": 0.0,
            "pcr": None, "iv_pctl": None, "call_oi_up": None
        })
    finally:
        # Close client if we created it
        if not use_existing_client:
            await client.aclose()
    
    # Redis plugin data (sentiment and shorts)
    try:
        if redis_client:
            # Sentiment data
            sent_data = redis_client.get(f"amc:externals:sentiment:{sym}")
            if sent_data:
                sent_json = json.loads(sent_data)
                factors["sent_score"] = sent_json.get("score", 0.0)
                factors["trending"] = sent_json.get("tweet_spike", False)
            else:
                factors["sent_score"] = None
                factors["trending"] = None
                
            # Short data
            short_data = redis_client.get(f"amc:externals:shorts:{sym}")
            if short_data:
                short_json = json.loads(short_data)
                factors["si"] = short_json.get("si")
                factors["borrow"] = short_json.get("borrow")
                factors["util"] = short_json.get("util")
            else:
                factors["si"] = None
                factors["borrow"] = None
                factors["util"] = None
        else:
            factors.update({"sent_score": None, "trending": None, "si": None, "borrow": None, "util": None})
    except Exception as e:
        logger.warning(f"Error fetching Redis data for {sym}: {e}")
        factors.update({"sent_score": None, "trending": None, "si": None, "borrow": None, "util": None})
    
    # Compute factor scores (0-1 scale)
    factor_scores = {}
    
    # Volume score: combines relative volume, ATR, VWAP reclaim, green streak
    volume_components = []
    if factors["rel_vol_30m"] >= REL_VOL_MIN:
        volume_components.append(min(factors["rel_vol_30m"] / 10.0, 1.0))  # Cap at 10x volume
    if factors["atr_pct"] >= ATR_PCT_MIN:
        volume_components.append(min(factors["atr_pct"] / 0.1, 1.0))  # Cap at 10% ATR
    if factors["above_vwap"]:
        volume_components.append(0.3)
    if factors["green_streak"] >= 3:
        volume_components.append(0.4)
    factor_scores["volume"] = sum(volume_components) / 4.0 if volume_components else None
    
    # Short score: float size and short metrics
    if factors["float"] is not None:
        if factors["float"] <= FLOAT_MAX:
            factor_scores["short"] = 1.0  # Small float = automatic high score
        elif (factors["float"] > BIG_FLOAT_MIN and 
              factors.get("si") is not None and factors.get("borrow") is not None and factors.get("util") is not None):
            # Big float but high short metrics
            si_score = 1.0 if factors["si"] >= SI_MIN else factors["si"] / SI_MIN
            borrow_score = 1.0 if factors["borrow"] >= BORROW_MIN else factors["borrow"] / BORROW_MIN  
            util_score = 1.0 if factors["util"] >= UTIL_MIN else factors["util"] / UTIL_MIN
            factor_scores["short"] = (si_score + borrow_score + util_score) / 3.0
        else:
            factor_scores["short"] = 0.1  # Large float, no short data
    else:
        factor_scores["short"] = None
        
    # Catalyst score
    factor_scores["catalyst"] = factors["catalyst_score"] if factors["catalyst_score"] > 0 else None
    
    # Sentiment score  
    if factors["sent_score"] is not None:
        sent_base = factors["sent_score"]
        trending_boost = 0.2 if factors["trending"] else 0.0
        factor_scores["sent"] = min(sent_base + trending_boost, 1.0)
    else:
        factor_scores["sent"] = None
        
    # Options score
    options_components = []
    if factors["pcr"] is not None and factors["pcr"] >= PCR_MIN:
        options_components.append(min(factors["pcr"] / 5.0, 1.0))
    if factors["iv_pctl"] is not None and factors["iv_pctl"] >= IV_PCTL_MIN:
        options_components.append(factors["iv_pctl"])
    if factors["call_oi_up"] is not None and factors["call_oi_up"]:
        options_components.append(0.5)
    factor_scores["options"] = sum(options_components) / 3.0 if options_components else None
    
    # Technical score
    tech_components = []
    if factors["ema_cross"]:
        tech_components.append(0.4)
    if factors["rsi_zone_ok"]:
        tech_components.append(0.3)
    if factors["above_vwap"]:
        tech_components.append(0.3)
    factor_scores["tech"] = sum(tech_components) if tech_components else None
    
    # Sector momentum score (if enabled)
    if AMC_ENABLE_SECTOR:
        try:
            # Parse ETF map from environment
            etf_map = json.loads(AMC_SECTOR_ETFS)
            
            # Compute sector momentum score
            async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
                sector_score = await _compute_sector_momentum_score(client, sym, etf_map)
                factor_scores["sector"] = sector_score
                
                # Add audit fields
                sector_classification = _classify_stock_sector(sym)
                etf_ticker = etf_map.get(sector_classification, etf_map.get("SMALL_CAP", "IWM"))
                factors["sector_classification"] = sector_classification
                factors["sector_etf"] = etf_ticker
        except Exception as e:
            logger.warning(f"Error computing sector momentum for {sym}: {e}")
            factor_scores["sector"] = None
            factors["sector_classification"] = None
            factors["sector_etf"] = None
    else:
        factor_scores["sector"] = None
        factors["sector_classification"] = None
        factors["sector_etf"] = None
    
    # Combine raw features and factor scores
    result = {**factors, **factor_scores}
    return result

def score_from_factors(f):
    """Calculate weighted score from available factors"""
    weights = {"volume": W_VOLUME, "short": W_SHORT, "catalyst": W_CATALYST, 
               "sent": W_SENT, "options": W_OPTIONS, "tech": W_TECH}
    
    # Add sector weight if enabled and available
    if AMC_ENABLE_SECTOR:
        weights["sector"] = AMC_W_SECTOR
    
    avail = {k: w for k, w in weights.items() if f.get(k) is not None}
    Z = sum(avail.values()) or 1.0
    total = 100.0 * sum(f[k] * avail[k] for k in avail) / Z
    return round(total, 1), avail

def build_thesis(sym, f, item=None):
    """Build human-readable thesis string with comprehensive audit data"""
    float_m = int((f.get('float') or 0) / 1e6)
    si_pct = int((f.get('si') or 0) * 100)
    iv_pct = int((f.get('iv_pctl') or 0) * 100)
    
    # Get additional data from item if provided
    price = item.get('price', 0) if item else 0
    dollar_vol = item.get('dollar_vol', 0) if item else 0
    
    # Build comprehensive thesis with audit data
    thesis = (f"{sym}: ${price:.2f}, rel vol {f.get('rel_vol_30m', 1.0):.1f}×, "
              f"ATR {f.get('atr_pct', 0)*100:.1f}%, "
              f"{'VWAP reclaim' if f.get('above_vwap') else 'under VWAP'}, "
              f"float {float_m}M, SI {si_pct}%, "
              f"catalyst {f.get('catalyst_tag', 'none')}, "
              f"PCR {f.get('pcr', 'n/a')}, IV%ile {iv_pct}")
    
    # Add sector momentum info if available
    if f.get('sector_classification') and f.get('sector_etf'):
        sector_score = f.get('sector', 0.5)
        sector_pct = int((sector_score - 0.5) * 2 * 100)  # Convert 0.5-1.0 to -100% to +100%
        thesis += f", sector {f['sector_classification']} ({f['sector_etf']}) {sector_pct:+d}%"
    
    return thesis + "."

def current_policy_dict():
    """Return current policy settings for audit"""
    return {
        "price_cap": AMC_PRICE_CAP,
        "min_dollar_vol": AMC_MIN_DOLLAR_VOL,
        "rel_vol_min": REL_VOL_MIN,
        "atr_pct_min": ATR_PCT_MIN,
        "float_max": FLOAT_MAX,
        "big_float_min": BIG_FLOAT_MIN,
        "si_min": SI_MIN,
        "borrow_min": BORROW_MIN,
        "util_min": UTIL_MIN,
        "iv_pctl_min": IV_PCTL_MIN,
        "pcr_min": PCR_MIN,
        "compression_pctl_max": COMPRESSION_PCTL_MAX,
        "exclude_funds": EXCLUDE_FUNDS,
        "exclude_adrs": EXCLUDE_ADRS,
        "pipeline_tag": PIPELINE_TAG
    }

def thesis_string_from(factors):
    """Build thesis string from factors (alias for build_thesis)"""
    # Extract symbol from somewhere or use placeholder
    symbol = factors.get('symbol', 'SYM')
    return build_thesis(symbol, factors)

# In-process cache for symbol classifications
_symbol_cache = {}

async def _classify_symbol(sym: str, client: httpx.AsyncClient) -> str:
    """Robust symbol classification using Polygon v3 API with guard sets and caching"""
    if sym in _symbol_cache:
        return _symbol_cache[sym]
    
    # Check known fund symbols guard set FIRST (fast path)
    if sym.upper() in KNOWN_FUND_SYMBOLS:
        _symbol_cache[sym] = "fund"
        return "fund"
        
    try:
        r = await client.get(f"https://api.polygon.io/v3/reference/tickers/{sym}",
                             params={"apiKey": POLY_KEY})
        if r.status_code != 200:
            _symbol_cache[sym] = "unknown"
            return "unknown"
            
        j = (r.json() or {}).get("results") or {}
        ttype = (j.get("type") or "").upper()
        name  = (j.get("name") or "").upper()
        
        # Enhanced fund/ETF detection - return specific class names
        if ttype == "ETF" or "ETF" in name:
            _symbol_cache[sym] = "ETF"
            return "ETF"
        elif ttype in {"FUND", "MUTUALFUND"} or "FUND" in name:
            _symbol_cache[sym] = "FUND"
            return "FUND"
        elif ttype in {"INDEX"} or "INDEX" in name:
            _symbol_cache[sym] = "INDEX"
            return "INDEX"
        elif ttype in {"TRUST", "CEFT"} or "TRUST" in name:
            _symbol_cache[sym] = "TRUST" 
            return "TRUST"
        elif ttype == "ETN" or "ETN" in name:
            _symbol_cache[sym] = "ETN"
            return "ETN"
        elif sym.upper() in KNOWN_FUND_SYMBOLS or any(pattern in name for pattern in FUND_NAME_PATTERNS):
            _symbol_cache[sym] = "ETF"  # Default funds to ETF classification
            return "ETF"
            
        # Classify ADRs
        if ttype in {"ADRC","ADRR","ADRU","ADR"} or "ADR" in name or "DEPOSITARY" in name:
            _symbol_cache[sym] = "ADR"
            return "ADR"
            
        # Classify bonds explicitly
        if ttype in {"BOND", "NOTE", "BILL"} or any(term in name for term in ["BOND", "TREASURY", "NOTE", "BILL"]):
            _symbol_cache[sym] = "BOND"
            return "BOND"
            
        # Classify equities - only if explicitly common stock
        if ttype in {"CS","COMMON_STOCK","COMMON","STOCK"}:
            _symbol_cache[sym] = "equity"
            return "equity"
            
        # Default to other for uncertain cases (safer to exclude)
        _symbol_cache[sym] = "other"
        return "other"
        
    except Exception as e:
        logger.warning(f"Classification failed for {sym}: {e}")
        _symbol_cache[sym] = "unknown"
        return "unknown"

class DiscoveryPipeline:
    def __init__(self):
        self.polygon_api_key = os.getenv('POLYGON_API_KEY')
        self.universe_file = os.getenv('UNIVERSE_FILE', 'data/universe.txt')
        
        if not self.polygon_api_key:
            raise ValueError("POLYGON_API_KEY environment variable required")
            
        self.polygon_client = RESTClient(self.polygon_api_key)
        
    def read_universe(self) -> List[str]:
        """Read symbols from universe file"""
        try:
            universe_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', self.universe_file)
            with open(universe_path, 'r') as f:
                symbols = [line.strip().upper() for line in f if line.strip()]
            logger.info(f"Loaded {len(symbols)} symbols from universe file")
            return symbols
        except Exception as e:
            logger.error(f"Failed to read universe file: {e}")
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
                        logger.info(f"Fetched data for {symbol}: ${data.close}")
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
            g = await _poly_get(client, f"/v2/aggs/grouped/locale/us/market/stocks/{date}", params={"adjusted":"true"})
        rows = g.get("results") or []
        # cheap gates first
        pcap = AMC_PRICE_CAP * (1.2 if relaxed else 1.0)  # allow slight slack in relaxed mode
        dvmin = AMC_MIN_DOLLAR_VOL * (0.5 if relaxed else 1.0)
        
        # NUCLEAR OPTION: Absolute ETF/Fund rejection at universe stage
        import re
        ABSOLUTE_GUARDLIST = {"DFAS", "BSV", "JETS", "SCHO", "KSA", "IYH", "VNQ", "VXX"}
        ETF_PATTERN = re.compile(r'(ETF|FUND|ETN|INDEX|BOND|TRUST|ADR)', re.IGNORECASE)
        
        for r in rows:
            sym = r.get("T")
            c = float(r.get("c") or 0.0)
            v = float(r.get("v") or 0.0)
            dollar_vol = c * v
            if not sym or c <= 0:
                continue
                
            # Absolute guardlist rejection - prevents any further processing
            if sym.upper() in ABSOLUTE_GUARDLIST:
                rejected.append({"symbol": sym, "reason": "absolute_guardlist"})
                continue
                
            if c > pcap:
                rejected.append({"symbol": sym, "reason": "price_cap"})
            elif dollar_vol < dvmin:
                rejected.append({"symbol": sym, "reason": "dollar_vol_min"})
            else:
                kept_syms.append(sym)
    except Exception:
        # fallback to curated universe to stay real but lighter
        kept_syms = UNIVERSE_FALLBACK[:]
    trace.exit("universe", kept_syms, rejected)

    if not kept_syms:
        items = []
        return (items, trace.to_dict()) if with_trace else items

    # classify stage: strict fund/ADR removal - DROPS non-equities
    symbol_classifications = {}  # Store classifications for later use
    
    if EXCLUDE_FUNDS or EXCLUDE_ADRS or EXCLUDE_FUNDS_STRICT:
        trace.enter("classify", kept_syms)
        classify_kept = []
        classify_rejected = []
        
        async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
            for sym in kept_syms:
                try:
                    cla = await _classify_symbol(sym, client)
                    symbol_classifications[sym] = cla
                    
                    # Apply exclusion filters based on classification
                    reject_reason = None
                    
                    # NUCLEAR GUARDLIST - All known ETFs/funds immediately rejected
                    NUCLEAR_GUARDLIST = {"DFAS", "BSV", "JETS", "SCHO", "KSA", "IYH", "VNQ", "VXX"}
                    
                    if sym.upper() in NUCLEAR_GUARDLIST:
                        reject_reason = f"nuclear-guard-{sym}"
                        logger.warning(f"NUCLEAR GUARD: {sym} absolutely rejected")
                    
                    # REGEX-BASED CLASS REJECTION: Drop any class matching ETF|FUND|ETN|INDEX|BOND|TRUST|ADR
                    elif re.search(r'ETF|FUND|ETN|INDEX|BOND|TRUST|ADR', cla, re.IGNORECASE):
                        reject_reason = f"regex-class-{cla}"
                        logger.warning(f"REGEX REJECT: {sym} ({cla}) rejected by pattern match")
                    
                    # FALLBACK: Only EQUITY explicitly allowed
                    elif cla.upper() != "EQUITY":
                        reject_reason = f"non-equity-{cla}"
                        logger.warning(f"NON-EQUITY: {sym} ({cla}) rejected - only EQUITY allowed")
                    
                    if reject_reason:
                        classify_rejected.append({"symbol": sym, "reason": reject_reason, "class": cla})
                        continue
                    
                    # Passed all filters
                    classify_kept.append(sym)
                    
                except Exception as e:
                    logger.warning(f"Classification failed for {sym}: {e}")
                    # On error, default to keep (conservative) and mark as unknown
                    symbol_classifications[sym] = "unknown"
                    classify_kept.append(sym)
        
        kept_syms = classify_kept
        trace.exit("classify", kept_syms, classify_rejected)
        
        if not kept_syms:
            items = []
            return (items, trace.to_dict()) if with_trace else items
    
    else:
        # Even if no exclusion, still classify for API audit
        async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
            for sym in kept_syms:
                try:
                    symbol_classifications[sym] = await _classify_symbol(sym, client)
                except Exception:
                    symbol_classifications[sym] = "unknown"

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

    # cap survivors before expensive step
    prelimit = min(len(kept_syms), 400 if not relaxed else 800)
    kept_syms = kept_syms[:prelimit]

    pairs = await asyncio.gather(*[fetch_bars(s) for s in kept_syms])
    comp = {s:p for s,p in pairs if p is not None}
    trace.exit("compression_calc", list(comp.keys()),
               [{"symbol":s,"reason":"no_history"} for s,p in pairs if p is None])

    # choose tightest compression cohort
    cutoff = COMPRESSION_PCTL_MAX * (1.5 if relaxed else 1.0)
    tight = [{ "symbol": s, "compression_pct": p } for s,p in comp.items() if p <= cutoff]
    tight.sort(key=lambda x: x["compression_pct"])
    trace.exit("compression_filter", [t["symbol"] for t in tight])

    # prepare candidates for factor analysis 
    out = []
    for t in tight[: (limit or MAX_CANDIDATES)]:
        out.append({
            "symbol": t["symbol"],
            "compression_pctl": t["compression_pct"],  # keep compression, but do NOT use as score
            "reason": "compression",
        })
    trace.exit("score_and_take", [o["symbol"] for o in out])

    # squeeze-hunting pipeline with factor scoring
    trace.enter("squeeze_analysis", [o["symbol"] for o in out])
    
    # Get Redis client for plugin data
    redis_client = None
    try:
        redis_client = get_redis_client()
    except Exception:
        logger.warning("Redis not available for plugin data")
    
    # Compute factors for all candidates with semaphore for concurrency control
    semaphore = asyncio.Semaphore(10)  # Limit concurrent requests
    
    async def _analyze_squeeze_candidate(sym):
        async with semaphore:
            try:
                # Get current price/volume for gates and targets
                async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
                    g = await _poly_get(client, f"/v2/aggs/grouped/locale/us/market/stocks/{date}", params={"adjusted":"true"})
                    rows = g.get("results") or []
                    price_row = next((r for r in rows if r.get("T") == sym), None)
                    
                    if not price_row:
                        return None  # Skip if no price data
                        
                    price = float(price_row.get("c") or 0.0)
                    volume = float(price_row.get("v") or 0.0)
                    dollar_vol = price * volume
                
                # Compute all factors
                factors = await compute_factors(sym, redis_client)
                
                # Hard gates
                if factors["rel_vol_30m"] < REL_VOL_MIN:
                    return {"symbol": sym, "reason": "rel_vol_low", "gate_failed": True}
                if factors["atr_pct"] < ATR_PCT_MIN:
                    return {"symbol": sym, "reason": "atr_low", "gate_failed": True}  
                if price > AMC_PRICE_CAP:
                    return {"symbol": sym, "reason": "price_high", "gate_failed": True}
                
                # Float gate
                float_val = factors.get("float")
                if float_val is not None:
                    if not (float_val <= FLOAT_MAX or 
                           (float_val > BIG_FLOAT_MIN and 
                            factors.get("si", 0) >= SI_MIN and 
                            factors.get("borrow", 0) >= BORROW_MIN and 
                            factors.get("util", 0) >= UTIL_MIN)):
                        return {"symbol": sym, "reason": "float_gate", "gate_failed": True}
                
                # Score the candidate using composite factor scoring
                total, _w = score_from_factors(factors)  # 0..100
                
                if total < 70:  # Score gate
                    return {"symbol": sym, "reason": "score_low", "gate_failed": True}
                
                # Build thesis with symbol context
                factors["symbol"] = sym  # Add symbol to factors for thesis
                thesis = build_thesis(sym, factors)
                
                # Compute ATR-based targets
                atr_abs = factors["atr_pct"] * price
                risk_abs = max(ATR_STOP_MULT * atr_abs, MIN_STOP_PCT * price)
                stop_price = round(price - risk_abs, 2)
                take_profit_price = round(price + R_MULT * risk_abs, 2)
                stop_loss_pct = round((risk_abs / price) * 100, 1)
                take_profit_pct = round((R_MULT * risk_abs / price) * 100, 1)
                r_multiple = R_MULT
                
                # Get compression_pctl from original candidate
                compression_pctl = next((o.get("compression_pctl", 0.0) for o in out if o["symbol"] == sym), 0.0)
                
                # Final safety check: ensure no funds slip through
                sym_class = symbol_classifications.get(sym, "unknown")
                
                # NUCLEAR OPTION: Absolute guardlist check during analysis
                NUCLEAR_ANALYSIS_GUARD = {"DFAS", "BSV", "JETS", "SCHO", "KSA", "IYH", "VNQ", "VXX"}
                
                # Layer 1: Nuclear guardlist - immediate rejection
                if sym.upper() in NUCLEAR_ANALYSIS_GUARD:
                    logger.error(f"🚨 NUCLEAR GUARD: ETF {sym} slipped through - REJECTING")
                    return {"symbol": sym, "reason": f"nuclear-analysis-{sym}", "gate_failed": True}
                
                # Layer 2: Regex pattern matching on class
                import re
                if re.search(r'ETF|FUND|ETN|INDEX|BOND|TRUST|ADR', sym_class, re.IGNORECASE):
                    logger.error(f"🚨 REGEX GUARD: {sym} ({sym_class}) matches ETF pattern - REJECTING")
                    return {"symbol": sym, "reason": f"regex-analysis-{sym_class}", "gate_failed": True}
                
                # Layer 3: Only explicit EQUITY allowed
                if sym_class.upper() != "EQUITY":
                    logger.error(f"🚨 NON-EQUITY: {sym} ({sym_class}) not EQUITY - REJECTING")
                    return {"symbol": sym, "reason": f"not-equity-{sym_class}", "gate_failed": True}
                
                # Build discovery thesis with specific format
                bandwidth_pct = round(compression_pctl * 100, 1)
                rs_pct = round(factors.get("rs_5d", 0.0) * 100, 1) 
                atr_pct_val = round(factors.get("atr_pct", 0.0) * 100, 1)
                liquidity_m = dollar_vol / 1_000_000
                
                thesis = f"{sym} is in the tightest {bandwidth_pct}% of its 60d volatility band, 5d RS {rs_pct}%, ATR% {atr_pct_val}, liquidity ${liquidity_m:.2f}M"
                
                # Build comprehensive audit item
                item = {
                    "symbol": sym,
                    "price": price,
                    "last_price": price,  # alias for audit
                    "dollar_vol": dollar_vol,
                    "compression_pctl": compression_pctl,  # keep, but do NOT use as score
                    "score": round(total, 1),  # <-- the rank key from composite scoring
                    "confidence": round(total/100.0, 4),
                    "class": symbol_classifications.get(sym, "unknown"),  # add "class" for API double-check
                    "factors": factors,  # volume/short/catalyst/sent/options/tech/sector
                    "gates": current_policy_dict(),  # price/rel_vol/atr/etc used for audit
                    "thesis": thesis,  # Discovery-specific thesis format
                    "tradeable": total >= 75,
                    
                    # Full audit payload with all requested fields
                    "rel_vol_30m": factors.get("rel_vol_30m", None),
                    "atr_abs": atr_abs,
                    "atr_pct": factors.get("atr_pct", None),
                    "ema9": None,  # Not computed in current implementation
                    "ema20": None,  # Not computed in current implementation  
                    "rsi": None,  # Not computed separately in current implementation
                    "vwap_reclaim": factors.get("above_vwap", None),
                    "float": factors.get("float", None),
                    "si": factors.get("si", None),
                    "borrow": factors.get("borrow", None),
                    "util": factors.get("util", None),
                    "iv_pctl": factors.get("iv_pctl", None),
                    "pcr": factors.get("pcr", None),
                    "call_oi_up": factors.get("call_oi_up", None),
                    "sector": factors.get("sector_classification", None),
                    "sector_etf": factors.get("sector_etf", None),
                    "sector_score": factors.get("sector", None),
                    
                    # Backwards compatibility fields
                    "rs_5d": factors.get("rs_5d", 0.0),
                    "above_vwap": factors.get("above_vwap", False),
                    "ema_cross": factors.get("ema_cross", False),
                    "rsi_zone_ok": factors.get("rsi_zone_ok", False),
                    "catalyst_tag": factors.get("catalyst_tag"),
                    "catalyst_score": factors.get("catalyst_score"),
                    "sent_score": factors.get("sent_score"),
                    "trending": factors.get("trending"),
                    
                    # ATR targets
                    "stop_price": stop_price,
                    "take_profit_price": take_profit_price,
                    "stop_loss_pct": stop_loss_pct,
                    "take_profit_pct": take_profit_pct,
                    "r_multiple": r_multiple,
                    "gate_failed": False
                }
                
                return item
                
            except Exception as e:
                logger.warning(f"Squeeze analysis failed for {sym}: {e}")
                return {"symbol": sym, "reason": "analysis_failed", "gate_failed": True}
    
    # Analyze all candidates
    squeeze_results = await asyncio.gather(*[_analyze_squeeze_candidate(o["symbol"]) for o in out])
    
    # Filter out gate failures and None results
    passed_candidates = []
    gate_failures = []
    
    for result in squeeze_results:
        if result is None:
            continue
        elif result.get("gate_failed"):
            gate_failures.append({"symbol": result["symbol"], "reason": result["reason"]})
        else:
            passed_candidates.append(result)
    
    trace.exit("squeeze_analysis", [c["symbol"] for c in passed_candidates], gate_failures)
    
    # FINAL ETF/FUND ELIMINATION - Drop any candidate with ETF/fund class or in guardlist
    equity_candidates = []
    etf_leaks = []
    
    # FINAL NUCLEAR ELIMINATION - Last line of defense
    import re
    FINAL_NUCLEAR_GUARD = {"DFAS", "BSV", "JETS", "SCHO", "KSA", "IYH", "VNQ", "VXX"}
    ETF_CLASS_PATTERN = re.compile(r'ETF|FUND|ETN|INDEX|BOND|TRUST|ADR', re.IGNORECASE)
    
    for candidate in passed_candidates:
        symbol = candidate.get("symbol", "").upper()
        class_name = candidate.get("class", "").upper()
        
        # FINAL NUCLEAR CHECK 1: Absolute guardlist
        if symbol in FINAL_NUCLEAR_GUARD:
            etf_leaks.append({"symbol": symbol, "reason": "final-nuclear-guard", "class": class_name})
            logger.error(f"🚨 FINAL NUCLEAR: {symbol} in guardlist - REJECTING")
            continue
            
        # FINAL NUCLEAR CHECK 2: Regex pattern on class name
        if ETF_CLASS_PATTERN.search(class_name):
            etf_leaks.append({"symbol": symbol, "reason": f"final-regex-{class_name}", "class": class_name})
            logger.error(f"🚨 FINAL REGEX: {symbol} ({class_name}) matches ETF pattern - REJECTING")
            continue
            
        # FINAL NUCLEAR CHECK 3: Only explicit EQUITY allowed
        if class_name.upper() != "EQUITY":
            etf_leaks.append({"symbol": symbol, "reason": f"final-not-equity-{class_name}", "class": class_name})
            logger.error(f"🚨 FINAL NOT EQUITY: {symbol} ({class_name}) - REJECTING")
            continue
            
        # PASSED ALL NUCLEAR CHECKS - verified equity only
        logger.info(f"✅ EQUITY VERIFIED: {symbol} ({class_name}) score={candidate.get('score', 0)}")
        equity_candidates.append(candidate)
    
    trace.exit("etf_elimination", [c["symbol"] for c in equity_candidates], etf_leaks)
    
    # Sort by score DESC, then ATR_pct DESC, then RS_5d DESC
    def sort_key(candidate):
        score = -candidate.get("score", 0)  # Higher score first
        atr_pct = -candidate.get("atr_pct", 0)  # Higher ATR% first  
        rs_5d = -candidate.get("rs_5d", 0)  # Higher RS_5d first
        return (score, atr_pct, rs_5d)
    
    equity_candidates.sort(key=sort_key)
    logger.info(f"Sorted {len(equity_candidates)} equity candidates by score/ATR/RS")
    
    final_candidates = equity_candidates[:MAX_CANDIDATES]
    
    # FINAL VERIFICATION: Double-check no ETFs in final output
    verified_candidates = []
    for candidate in final_candidates:
        symbol = candidate.get("symbol", "").upper()
        class_name = candidate.get("class", "").upper()
        
        # Triple verification before adding to final output
        if symbol in FINAL_NUCLEAR_GUARD:
            logger.error(f"🚨 FINAL VERIFICATION FAILED: {symbol} in nuclear guard!")
            continue
        if ETF_CLASS_PATTERN.search(class_name):
            logger.error(f"🚨 FINAL VERIFICATION FAILED: {symbol} ({class_name}) matches ETF pattern!")
            continue
        if class_name != "EQUITY":
            logger.error(f"🚨 FINAL VERIFICATION FAILED: {symbol} ({class_name}) not EQUITY!")
            continue
            
        # Passed all final verification checks
        verified_candidates.append(candidate)
        logger.info(f"✅ FINAL VERIFIED: {symbol} ({class_name}) ready for Redis")
    
    trace.exit("final_selection", [c["symbol"] for c in verified_candidates])
    
    if len(verified_candidates) != len(final_candidates):
        logger.warning(f"VERIFICATION REMOVED {len(final_candidates) - len(verified_candidates)} candidates")

    return (verified_candidates, trace.to_dict()) if with_trace else verified_candidates

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
            
            # Build status and explain objects for v2 publishing
            now_iso = datetime.now(timezone.utc).isoformat() + "Z"
            explain = {
                "pipeline": PIPELINE_TAG,
                "stages": tr.get("stages", []) if isinstance(tr, dict) else [],
                "counts_in": tr.get("counts_in", {}) if isinstance(tr, dict) else {},
                "counts_out": tr.get("counts_out", {}) if isinstance(tr, dict) else {},
                "rejections": tr.get("rejections", {}) if isinstance(tr, dict) else {},
                "ts": now_iso,
                "count": len(items)
            }
            status = {"count": len(items), "ts": now_iso, "pipeline": PIPELINE_TAG}
            
            # Delete legacy keys before writing new data (prevents stale reads)
            from lib.redis_client import get_redis_client
            r = get_redis_client()
            try:
                r.delete(REDIS_KEY_V1_CONT, REDIS_KEY_V1_TRACE)
            except Exception:
                pass  # non-fatal
            
            # Add pipeline tag to each item and build blob
            blob = []
            for item in items:
                item["pipeline"] = PIPELINE_TAG
                blob.append(item)
            
            # Publish to both v2 and v1 keys for compatibility
            r.set(REDIS_KEY_V2_CONT, json.dumps(blob), ex=600)
            r.set(REDIS_KEY_V2_TRACE, json.dumps(explain), ex=600)
            r.set(REDIS_KEY_V1_CONT, json.dumps(blob), ex=600)
            r.set(REDIS_KEY_V1_TRACE, json.dumps(explain), ex=600)
            r.set(REDIS_KEY_STATUS, json.dumps(status), ex=600)
            
            # Log to stdout for verification in Render logs
            print(f"PUBLISH_OK pipeline={PIPELINE_TAG} count={len(blob)} ts={now_iso}")
            
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