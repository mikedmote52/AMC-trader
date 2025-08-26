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
PRICE_CAP = float(os.getenv("AMC_PRICE_CAP", "100"))             # keep ≤ 100 by default
MIN_DOLLAR_VOL = float(os.getenv("AMC_MIN_DOLLAR_VOL", "20000000"))  # $20M
LOOKBACK_DAYS = int(os.getenv("AMC_COMPRESSION_LOOKBACK", "60"))
COMPRESSION_PCTL_MAX = float(os.getenv("AMC_COMPRESSION_PCTL_MAX", "0.15"))  # tightest 15%
MAX_CANDIDATES = int(os.getenv("AMC_MAX_CANDIDATES", "15"))
UNIVERSE_FALLBACK = [s.strip().upper() for s in os.getenv("AMC_DISCOVERY_UNIVERSE","AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA,AMD,AVGO,PLTR,COIN,CRM,ORCL,ABNB,SNOW,UBER,NFLX,SHOP,INTC,MRVL,SMCI").split(",") if s.strip()]
EXCLUDE_FUNDS = os.getenv("AMC_EXCLUDE_FUNDS", "true").lower() in ("1", "true", "yes")
EXCLUDE_ADRS = os.getenv("AMC_EXCLUDE_ADRS", "true").lower() in ("1", "true", "yes")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        pcap = PRICE_CAP * (1.2 if relaxed else 1.0)  # allow slight slack in relaxed mode
        dvmin = MIN_DOLLAR_VOL * (0.5 if relaxed else 1.0)
        for r in rows:
            sym = r.get("T")
            c = float(r.get("c") or 0.0)
            v = float(r.get("v") or 0.0)
            dollar_vol = c * v
            if not sym or c <= 0:
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

    # classify stage: exclude funds/ADRs if configured
    if EXCLUDE_FUNDS or EXCLUDE_ADRS:
        trace.enter("classify", kept_syms)
        classify_kept = []
        classify_rejected = []
        
        async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
            # Classify all symbols
            classifications = await asyncio.gather(*[_classify_symbol(client, sym) for sym in kept_syms], return_exceptions=True)
            
            for sym, classification in zip(kept_syms, classifications):
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

    # simple score: tighter is better. extend later with short interest, catalysts.
    out = []
    for t in tight[: (limit or MAX_CANDIDATES)]:
        out.append({
            "symbol": t["symbol"],
            "score": round(1.0 - t["compression_pct"], 4),
            "reason": "compression",
        })
    trace.exit("score_and_take", [o["symbol"] for o in out])

    return (out, trace.to_dict()) if with_trace else out

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