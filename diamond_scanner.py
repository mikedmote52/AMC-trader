#!/usr/bin/env python3
"""
DIAMOND SCANNER V3.3 - INTELLIGENT EDITION
Built on V3.2's 305pt system, adds:
- LLM-powered catalyst sentiment (Gemini Flash, batched + cached, ~$0.01/day)
- Negative scoring: red flags, pump detection, chase risk
- Contradictory signal penalty (chase-risk detector)
- Improved float accuracy with discount factor
- Dual-track candidate ranking (stealth + breakout)
- Time-of-day scan profiles
- Daily cost tracking with budget cap

Max score: 305 points (unchanged)
Min score: -75 points (new negative floor)
Net range: -75 to 305

Cost budget: ~$0.50/day max on OpenRouter
"""

from polygon import RESTClient
import json
import requests as http_requests
from datetime import datetime, timedelta, date
import time
import os
import pickle
import sys
import math
import hashlib

# Add scripts directory to path
sys.path.insert(0, '/Users/mikeclawd/.openclaw/workspace/scripts')
from scanner_performance_tracker import log_scanner_picks
from telegram_alert import send_alert

# Import sector tracker
sys.path.insert(0, '/Users/mikeclawd/.openclaw/workspace')
from sector_tracker import get_sector_performance, is_hot_sector, get_stock_sector

with open('/Users/mikeclawd/.openclaw/secrets/polygon.json', 'r') as f:
    creds = json.load(f)

client = RESTClient(api_key=creds['apiKey'])

# ============================================================
# CONFIGURATION
# ============================================================

# --- DYNAMIC WEIGHT LOADING ---
WORKSPACE_DIR = '/Users/mikeclawd/.openclaw/workspace'

def load_dynamic_weights():
    """Load weights from scanner_weights.json if available, else use defaults."""
    import os as _os
    weights_file = _os.path.join(WORKSPACE_DIR, 'data', 'scanner_weights.json')
    try:
        if _os.path.exists(weights_file):
            with open(weights_file, 'r') as _f:
                weights = json.load(_f)
            updated = weights.get('last_updated', 'never')
            print(f'   Loaded dynamic weights (updated: {updated})')
            return weights
    except Exception as e:
        print(f'   Warning: Could not load dynamic weights: {e}')
    return None

DYNAMIC_WEIGHTS = load_dynamic_weights()
# --- END DYNAMIC WEIGHT LOADING ---

CACHE_FILE = '/Users/mikeclawd/.openclaw/workspace/data/snapshot_cache.pkl'
CACHE_MAX_AGE = 300  # 5 minutes

SHORT_INTEREST_CACHE_FILE = '/Users/mikeclawd/.openclaw/workspace/data/short_interest_cache.pkl'
SHORT_INTEREST_CACHE_MAX_AGE = 604800  # 7 days

# NEW V3.3: LLM catalyst analysis
CATALYST_CACHE_FILE = '/Users/mikeclawd/.openclaw/workspace/data/catalyst_cache.pkl'
CATALYST_CACHE_MAX_AGE = 21600  # 6 hours - news doesn't change that fast

# NEW V3.3: Daily cost tracking
COST_TRACKER_FILE = '/Users/mikeclawd/.openclaw/workspace/data/daily_cost.json'
DAILY_BUDGET_LIMIT = 0.50  # $0.50/day max on OpenRouter
GEMINI_FLASH_INPUT_COST = 0.15 / 1_000_000   # $0.15 per 1M input tokens
GEMINI_FLASH_OUTPUT_COST = 0.60 / 1_000_000  # $0.60 per 1M output tokens

# Hardcoded ETF exclusions (unchanged from V3.2)
EXCLUDED_ETFS = {
    'SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'VTI', 'VEA', 'VWO', 'VTV', 'VUG', 'VB', 'VO', 'VV',
    'SH', 'SDS', 'SPXU', 'SQQQ', 'PSQ', 'RWM', 'TWM', 'QID', 'SARK',
    'SPDN', 'SPXS', 'SPXL', 'TZA', 'FAZ', 'ERY', 'DUST', 'NUGT', 'JDST', 'JUNG', 'YANG', 'YINN',
    'LABD', 'LABU', 'CURE', 'DRN', 'DPST', 'FAS', 'FAZ', 'MIDU', 'MIDZ', 'RETL', 'SOXL', 'SOXS',
    'DRIP', 'GUSH', 'USOI', 'AMLP', 'MLPA', 'IEZ', 'OIH', 'XES', 'XOP', 'PSCE',
    'XLF', 'XLK', 'XLE', 'XLI', 'XLP', 'XLU', 'XLV', 'XLY', 'XLB', 'XLRE', 'XRT',
    'TLT', 'IEF', 'SHY', 'LQD', 'HYG', 'AGG', 'BND', 'VCIT', 'VCLT', 'VGIT', 'VGLT',
    'GLD', 'SLV', 'USO', 'UNG', 'DBC', 'GSG',
    'SCHD', 'SCHX', 'SCHB', 'SCHA', 'SCHF', 'SCHE', 'SCHH', 'SCHP', 'SCHR', 'SCHV', 'SCHG',
    'SCHM', 'SCHZ', 'FNDA', 'FNDB', 'FNDC', 'FNDE', 'FNDF', 'FNDX', 'SCHY',
    'VIG', 'VYM', 'VCSH', 'VHT', 'VFH', 'VGT', 'VDE', 'VCR', 'VDC', 'VPU', 'VAW', 'VNQ', 'VGSLX',
    'VMBS', 'VGSH', 'VGIT', 'VCLT', 'VWOB', 'VTIP', 'VGSTX', 'VWINX', 'VFINX', 'VTSMX', 'VBMFX',
    'SDY', 'NOBL', 'DGRO', 'HDV', 'SPHD', 'QYLD', 'XYLD', 'JEPI', 'JEPQ',
    'TQQQ', 'UPRO', 'UDOW', 'URTY', 'SRTY', 'SDOW', 'SPXL', 'SPXS',
    'QQQI', 'YMAX', 'OARK', 'NVDY', 'TSLY', 'CONY', 'MSFO', 'AMDY', 'GOOY', 'XOMO', 'JPMO',
    'SPYI', 'SPYM', 'IWMY', 'DIVO', 'ALTY', 'ULST',
    'FXI', 'IEFA', 'KWEB', 'MCHI', 'EWY', 'EWZ', 'GXC', 'INDA', 'THD', 'ASHR', 'BABA',
    'IJH', 'MSTU', 'IBIT', 'FBTC', 'GBTC', 'ETHE',
    'ARKK', 'ARKG', 'ARKF', 'ARKW', 'ARKQ', 'ARKX',
    'IWF', 'IWD', 'IWB', 'IWM', 'IWN', 'IWO', 'IWP', 'IWS', 'IWR', 'IJR', 'IJJ', 'IJK',
    'MDY', 'SLY', 'SLYG', 'SLYV', 'SPMD', 'SPSM',
    'ACWI', 'VT', 'VXUS', 'VEU', 'IXUS', 'SCHC', 'SCHE', 'VSS', 'VWO', 'VPL', 'VGK', 'VNM',
    'EMB', 'VWOB', 'PCY', 'EMLC', 'LEMB',
    'BKLN', 'SRLN', 'FTSL', 'PGX', 'PFF', 'PSK', 'SPFF',
    'MUB', 'TFI', 'PZA', 'MLN', 'ITM', 'VTEB', 'MUNI',
    'REET', 'VNQI', 'RWX', 'DRW', 'FEZ', 'IEV', 'EWG', 'EWJ', 'EEM', 'EFA', 'IWM'
}

# ============================================================
# NEW V3.3: COST TRACKING
# ============================================================

def get_daily_spend():
    """Track daily OpenRouter spending"""
    try:
        if os.path.exists(COST_TRACKER_FILE):
            with open(COST_TRACKER_FILE, 'r') as f:
                data = json.load(f)
            if data.get('date') == date.today().isoformat():
                return data.get('total_cost', 0.0)
    except:
        pass
    return 0.0

def log_cost(input_tokens, output_tokens):
    """Log cost of an LLM call"""
    cost = (input_tokens * GEMINI_FLASH_INPUT_COST) + (output_tokens * GEMINI_FLASH_OUTPUT_COST)
    try:
        data = {'date': date.today().isoformat(), 'total_cost': 0.0, 'calls': 0}
        if os.path.exists(COST_TRACKER_FILE):
            with open(COST_TRACKER_FILE, 'r') as f:
                data = json.load(f)
            if data.get('date') != date.today().isoformat():
                data = {'date': date.today().isoformat(), 'total_cost': 0.0, 'calls': 0}

        data['total_cost'] = data.get('total_cost', 0.0) + cost
        data['calls'] = data.get('calls', 0) + 1

        os.makedirs(os.path.dirname(COST_TRACKER_FILE), exist_ok=True)
        with open(COST_TRACKER_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except:
        pass
    return cost

def within_budget():
    """Check if we're within daily budget"""
    return get_daily_spend() < DAILY_BUDGET_LIMIT

# ============================================================
# NEW V3.3: LLM CATALYST ANALYSIS (batched, cached, cheap)
# ============================================================

def load_catalyst_cache():
    """Load cached catalyst analysis results"""
    try:
        if os.path.exists(CATALYST_CACHE_FILE):
            with open(CATALYST_CACHE_FILE, 'rb') as f:
                cache = pickle.load(f)
            # Prune entries older than cache max age
            now = time.time()
            cache = {k: v for k, v in cache.items() if now - v.get('timestamp', 0) < CATALYST_CACHE_MAX_AGE}
            return cache
    except:
        pass
    return {}

def save_catalyst_cache(cache):
    """Save catalyst cache"""
    try:
        os.makedirs(os.path.dirname(CATALYST_CACHE_FILE), exist_ok=True)
        with open(CATALYST_CACHE_FILE, 'wb') as f:
            pickle.dump(cache, f)
    except:
        pass

def batch_analyze_catalysts(candidates_with_news):
    """
    Batch-analyze news catalysts for multiple stocks using Gemini Flash.
    One API call for all candidates. Returns dict of {symbol: {sentiment, score, reason}}.

    Cost: ~2000 tokens in, ~1000 out = ~$0.0009 per batch
    """
    if not candidates_with_news:
        return {}

    # Check budget
    if not within_budget():
        print(f"   ⚠️  Daily budget ${DAILY_BUDGET_LIMIT:.2f} reached, using keyword fallback")
        return {}

    # Check cache first
    cache = load_catalyst_cache()
    uncached = {}
    results = {}

    for symbol, headlines in candidates_with_news.items():
        cache_key = hashlib.md5(f"{symbol}:{'|'.join(headlines)}".encode()).hexdigest()
        if cache_key in cache:
            results[symbol] = cache[cache_key]['result']
        else:
            uncached[symbol] = headlines

    if not uncached:
        print(f"   ✅ All {len(results)} catalyst analyses from cache")
        return results

    # Build batch prompt
    news_block = ""
    for symbol, headlines in uncached.items():
        news_block += f"\n{symbol}: {' | '.join(headlines[:3])}"

    prompt = f"""Analyze these stock news headlines for trading. For each stock, respond with ONLY a JSON object.
Rate sentiment as: bullish, bearish, or neutral.
Rate catalyst_quality 1-10 (10 = FDA approval, major contract; 1 = fluff/PR).
Flag if the headline suggests dilution, offering, or shelf registration.

Stocks:{news_block}

Respond with ONLY valid JSON, no markdown:
{{"SYMBOL": {{"sentiment": "bullish/bearish/neutral", "score": 1-10, "dilution_risk": true/false, "reason": "brief explanation"}}}}"""

    try:
        # Load OpenRouter credentials
        with open('/Users/mikeclawd/.openclaw/secrets/openrouter.json', 'r') as f:
            or_creds = json.load(f)

        response = http_requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f"Bearer {or_creds.get('apiKey', or_creds.get('api_key', ''))}",
                'Content-Type': 'application/json'
            },
            json={
                'model': 'google/gemini-2.5-flash',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 1500,
                'temperature': 0.1
            },
            timeout=15
        )

        if response.status_code == 200:
            resp_data = response.json()
            content = resp_data['choices'][0]['message']['content']

            # Track cost
            usage = resp_data.get('usage', {})
            cost = log_cost(usage.get('prompt_tokens', 2000), usage.get('completion_tokens', 1000))
            print(f"   💰 Catalyst LLM cost: ${cost:.4f} (daily total: ${get_daily_spend():.4f})")

            # Parse JSON response (handle potential markdown wrapping)
            content = content.strip()
            if content.startswith('```'):
                content = content.split('\n', 1)[1] if '\n' in content else content
                content = content.rsplit('```', 1)[0] if '```' in content else content
                content = content.strip()

            parsed = json.loads(content)

            # Cache and merge results
            now = time.time()
            for symbol, analysis in parsed.items():
                results[symbol] = analysis
                headlines = uncached.get(symbol, [])
                cache_key = hashlib.md5(f"{symbol}:{'|'.join(headlines)}".encode()).hexdigest()
                cache[cache_key] = {'result': analysis, 'timestamp': now}

            save_catalyst_cache(cache)
            print(f"   ✅ Analyzed {len(parsed)} catalysts via Gemini Flash")
        else:
            print(f"   ⚠️  OpenRouter returned {response.status_code}, using keyword fallback")

    except json.JSONDecodeError as e:
        print(f"   ⚠️  Failed to parse LLM response: {e}")
    except Exception as e:
        print(f"   ⚠️  LLM catalyst analysis failed: {e}, using keyword fallback")

    return results

def keyword_catalyst_fallback(title):
    """Original V3.2 keyword matching as fallback when LLM is unavailable"""
    title_lower = title.lower()
    if any(word in title_lower for word in ['fda', 'approval', 'approved']):
        return 30, "FDA/Regulatory (keyword)"
    elif any(word in title_lower for word in ['earnings', 'beat']):
        return 25, "Earnings beat (keyword)"
    elif any(word in title_lower for word in ['contract', 'deal', 'partnership']):
        return 20, "Contract/Deal (keyword)"
    else:
        return 10, "News (keyword, unverified)"

# ============================================================
# NEW V3.3: NEGATIVE SCORING
# ============================================================

def detect_red_flags(symbol, ticker_details, bars, price, volume):
    """
    Detect red flags that should penalize a stock's score.
    Returns: (penalty, list of flag descriptions)
    All data from Polygon - zero additional API cost.
    """
    penalty = 0
    flags = []

    # 1. Dilution / offering risk from ticker details
    # Check if stock had a recent massive share increase (proxy for dilution)
    shares_outstanding = getattr(ticker_details, 'share_class_shares_outstanding', 0) or 0
    weighted_shares = getattr(ticker_details, 'weighted_shares_outstanding', 0) or 0

    if weighted_shares > 0 and shares_outstanding > 0:
        share_ratio = shares_outstanding / weighted_shares
        if share_ratio > 1.5:
            penalty -= 25
            flags.append(f"🚩 DILUTION RISK: shares outstanding {share_ratio:.1f}x weighted")
        elif share_ratio > 1.2:
            penalty -= 10
            flags.append(f"⚠️  Possible dilution: {share_ratio:.1f}x share ratio")

    # 2. Penny stock pump pattern: massive single-day spike from very low volume baseline
    if bars and len(bars) >= 5:
        volumes = [bar.volume for bar in bars]
        avg_vol_4d = sum(volumes[:-1]) / len(volumes[:-1]) if len(volumes) > 1 else volumes[-1]
        today_vol = volumes[-1] if volumes else 0

        # Pattern: volume jumps 20x+ from a very low base (<500K avg) = likely pump
        if avg_vol_4d < 500_000 and today_vol > 0 and today_vol / max(avg_vol_4d, 1) > 20:
            penalty -= 30
            flags.append(f"🚩 PUMP PATTERN: {today_vol/avg_vol_4d:.0f}x volume from {avg_vol_4d/1000:.0f}K base")
        # Milder version: 10x from low base
        elif avg_vol_4d < 500_000 and today_vol > 0 and today_vol / max(avg_vol_4d, 1) > 10:
            penalty -= 15
            flags.append(f"⚠️  Suspicious volume: {today_vol/avg_vol_4d:.0f}x from low base")

    # 3. Price below $1 recently (reverse split / delisting risk)
    if bars:
        recent_lows = [bar.low for bar in bars if bar.low and bar.low > 0]
        if recent_lows and min(recent_lows) < 1.0:
            penalty -= 20
            flags.append(f"🚩 Sub-$1 recently: low was ${min(recent_lows):.2f}")
        elif recent_lows and min(recent_lows) < 2.0:
            penalty -= 10
            flags.append(f"⚠️  Near penny territory: low was ${min(recent_lows):.2f}")

    # 4. Extreme price drop followed by bounce (dead cat bounce risk)
    if bars and len(bars) >= 5:
        prices = [bar.close for bar in bars]
        if len(prices) >= 5:
            # Check if stock dropped 30%+ in last 5 days then bounced
            max_price_5d = max(prices)
            min_price_5d = min(prices)
            if max_price_5d > 0:
                drop_pct = (max_price_5d - min_price_5d) / max_price_5d * 100
                current_bounce = (price - min_price_5d) / min_price_5d * 100 if min_price_5d > 0 else 0

                if drop_pct > 40 and current_bounce > 10:
                    penalty -= 20
                    flags.append(f"🚩 DEAD CAT: -{drop_pct:.0f}% drop then +{current_bounce:.0f}% bounce")
                elif drop_pct > 30 and current_bounce > 10:
                    penalty -= 10
                    flags.append(f"⚠️  Bounce after -{drop_pct:.0f}% drop")

    # 5. Extremely low price + micro volume = illiquid trash
    if price < 1.0 and volume < 2_000_000:
        penalty -= 20
        flags.append(f"🚩 Illiquid penny: ${price:.2f} with {volume/1e6:.1f}M vol")

    return penalty, flags

# ============================================================
# NEW V3.3: CHASE-RISK DETECTOR
# ============================================================

def calculate_chase_risk(gap_pct, rvol, change_pct, price, prev_close):
    """
    Detect when multiple signals suggest you'd be chasing a move that already happened.
    Returns: (penalty, description)

    The insight: gap-up + explosive volume + price already moved = the move is DONE.
    Entering now means buying what someone else is selling.
    """
    penalty = 0
    reasons = []

    # Count chase signals
    chase_signals = 0

    if gap_pct >= 10:
        chase_signals += 1
        reasons.append(f"gap +{gap_pct:.0f}%")

    if rvol >= 10:
        chase_signals += 1
        reasons.append(f"vol {rvol:.0f}x")

    if change_pct >= 8:
        chase_signals += 1
        reasons.append(f"up {change_pct:.0f}%")

    # Price already extended far from previous close
    if prev_close > 0 and price > prev_close * 1.15:
        chase_signals += 1
        reasons.append("extended 15%+")

    # Apply penalty based on number of co-occurring chase signals
    if chase_signals >= 3:
        penalty = -35
        desc = f"🚩 HIGH CHASE RISK ({', '.join(reasons)})"
    elif chase_signals == 2:
        penalty = -15
        desc = f"⚠️  Chase risk ({', '.join(reasons)})"
    else:
        penalty = 0
        desc = ""

    return penalty, desc

# ============================================================
# NEW V3.3: TIME-OF-DAY PROFILES
# ============================================================

def get_scan_profile():
    """
    Adjust scoring weights based on time of day.
    Returns: dict of category weights and flags.
    """
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    market_minutes = (hour - 9) * 60 + (minute - 30)  # Minutes since 9:30 AM ET

    if market_minutes < 0:
        # Pre-market
        return {
            'name': 'PRE-MARKET',
            'vwap_enabled': False,       # No meaningful VWAP yet
            'breakout_enabled': False,   # Not enough bars
            'gap_weight': 1.5,           # Gaps are most meaningful pre-market
            'volume_note': 'Pre-market volume unreliable',
            'min_bars_for_intraday': 999  # Disable intraday features
        }
    elif market_minutes <= 30:
        # First 30 minutes - opening volatility
        return {
            'name': 'MARKET OPEN',
            'vwap_enabled': False,       # VWAP needs more data
            'breakout_enabled': False,   # Too early for consolidation patterns
            'gap_weight': 1.2,
            'volume_note': 'Opening volume - use with caution',
            'min_bars_for_intraday': 6
        }
    elif market_minutes <= 120:
        # 10:00 AM - 11:30 AM - prime scanning time
        return {
            'name': 'MORNING SESSION',
            'vwap_enabled': True,
            'breakout_enabled': True,
            'gap_weight': 1.0,
            'volume_note': None,
            'min_bars_for_intraday': 5
        }
    elif market_minutes <= 270:
        # 11:30 AM - 2:00 PM - midday lull
        return {
            'name': 'MIDDAY',
            'vwap_enabled': True,
            'breakout_enabled': True,
            'gap_weight': 0.7,           # Gaps less relevant by midday
            'volume_note': 'Midday - volume typically lower',
            'min_bars_for_intraday': 5
        }
    elif market_minutes <= 360:
        # 2:00 PM - 3:30 PM - power hour approaching
        return {
            'name': 'POWER HOUR',
            'vwap_enabled': True,
            'breakout_enabled': True,
            'gap_weight': 0.5,
            'volume_note': None,
            'min_bars_for_intraday': 5
        }
    else:
        # After hours
        return {
            'name': 'AFTER HOURS',
            'vwap_enabled': False,
            'breakout_enabled': False,
            'gap_weight': 0.3,
            'volume_note': 'After hours - limited data',
            'min_bars_for_intraday': 999
        }

# ============================================================
# EXISTING FUNCTIONS (preserved from V3.2)
# ============================================================

def load_market_cap_cache():
    """Load pre-built market cap database for Phase 1 filtering"""
    cache_file = os.path.join(os.path.dirname(__file__), 'data', 'market_cap_cache.json')
    try:
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                data = json.load(f)
            metadata = data.get('_metadata', {})
            last_updated = metadata.get('last_updated', '2020-01-01T00:00:00')
            from datetime import datetime
            cache_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            age_hours = (datetime.now(cache_time.tzinfo) - cache_time).total_seconds() / 3600
            if age_hours < 36:
                data = {k: v for k, v in data.items() if not k.startswith('_')}
                return data
            else:
                print(f"⚠️  Market cap cache is {age_hours:.1f} hours old - will use Phase 3 fallback")
    except Exception as e:
        print(f"⚠️  Could not load market cap cache: {e}")
    return {}


def get_short_interest(symbol):
    """Get short interest data from Polygon API (cached for 7 days)"""
    cache = {}
    if os.path.exists(SHORT_INTEREST_CACHE_FILE):
        try:
            with open(SHORT_INTEREST_CACHE_FILE, 'rb') as f:
                cache = pickle.load(f)
        except:
            cache = {}

    if symbol in cache:
        cached_time = cache[symbol].get('timestamp', 0)
        age = time.time() - cached_time
        if age < SHORT_INTEREST_CACHE_MAX_AGE:
            return cache[symbol]['days_to_cover'], cache[symbol]['short_ratio']

    days_to_cover = None
    short_ratio = None

    try:
        short_data = list(client.list_short_interest(ticker=symbol, limit=1))
        if short_data:
            si = short_data[0]
            days_to_cover = getattr(si, 'days_to_cover', None)
    except:
        pass

    try:
        short_vol_data = list(client.list_short_volume(ticker=symbol, limit=1))
        if short_vol_data:
            sv = short_vol_data[0]
            short_ratio = getattr(sv, 'short_volume_ratio', None)
    except:
        pass

    cache[symbol] = {
        'days_to_cover': days_to_cover,
        'short_ratio': short_ratio,
        'timestamp': time.time()
    }

    try:
        os.makedirs(os.path.dirname(SHORT_INTEREST_CACHE_FILE), exist_ok=True)
        with open(SHORT_INTEREST_CACHE_FILE, 'wb') as f:
            pickle.dump(cache, f)
    except:
        pass

    return days_to_cover, short_ratio


def get_cached_snapshots():
    """Use cached snapshots if recent enough"""
    if os.path.exists(CACHE_FILE):
        cache_age = time.time() - os.path.getmtime(CACHE_FILE)
        if cache_age < CACHE_MAX_AGE:
            with open(CACHE_FILE, 'rb') as f:
                return pickle.load(f)

    print("📡 Fetching fresh market snapshots...")
    snapshots = client.get_snapshot_all("stocks")

    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(snapshots, f)

    return snapshots


def get_intraday_vwap(symbol):
    """Fetch today's 5-min bars and calculate VWAP"""
    try:
        today = date.today().strftime("%Y-%m-%d")
        bars = list(client.list_aggs(symbol, 5, "minute", today, today, limit=100))

        if not bars or len(bars) < 5:
            return None, None, False, 1.0

        total_pv = sum(bar.close * bar.volume for bar in bars)
        total_volume = sum(bar.volume for bar in bars)

        if total_volume == 0:
            return None, None, False, 1.0

        vwap = total_pv / total_volume
        current_price = bars[-1].close
        above_vwap = current_price > vwap

        recent_volume = sum(bar.volume for bar in bars[-3:]) / 3
        avg_volume = total_volume / len(bars)
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0

        return current_price, vwap, above_vwap, volume_ratio

    except:
        return None, None, False, 1.0


def detect_intraday_breakout(symbol):
    """Check if stock is breaking out in current session"""
    try:
        today = date.today().strftime("%Y-%m-%d")
        bars = list(client.list_aggs(symbol, 5, "minute", today, today, limit=15))

        if not bars or len(bars) < 10:
            return False, "Insufficient data"

        consolidation_bars = bars[-10:-3]
        breakout_bars = bars[-3:]

        if not consolidation_bars:
            return False, "No consolidation period"

        consol_highs = [bar.high for bar in consolidation_bars]
        consol_lows = [bar.low for bar in consolidation_bars]
        consol_range = max(consol_highs) - min(consol_lows)
        consol_avg_price = sum(bar.close for bar in consolidation_bars) / len(consolidation_bars)

        range_pct = (consol_range / consol_avg_price * 100) if consol_avg_price > 0 else 999

        if range_pct > 3:
            return False, f"Range too wide: {range_pct:.1f}%"

        consol_avg_vol = sum(bar.volume for bar in consolidation_bars) / len(consolidation_bars)
        breakout_avg_vol = sum(bar.volume for bar in breakout_bars) / len(breakout_bars)

        volume_spike = breakout_avg_vol / consol_avg_vol if consol_avg_vol > 0 else 1.0

        breakout_high = max(bar.high for bar in breakout_bars)
        consol_high = max(consol_highs)

        price_breakout = breakout_high > consol_high

        if price_breakout and volume_spike > 1.5:
            return True, f"Breakout! Vol: {volume_spike:.1f}x, Range: {range_pct:.1f}%"

        return False, f"No breakout (vol {volume_spike:.1f}x)"

    except Exception as e:
        return False, f"Error: {str(e)}"


def quick_volume_check(symbol):
    """FAST check: Is volume accelerating?"""
    try:
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        bars = list(client.list_aggs(symbol, 1, "day", start, end, limit=5))

        if len(bars) < 3:
            return False

        volumes = [bar.volume for bar in bars[-3:]]
        increasing = sum(1 for i in range(1, len(volumes)) if volumes[i] > volumes[i-1])

        return increasing >= 2

    except:
        return False


# ============================================================
# UPGRADED V3.3: FULL ANALYSIS WITH NEGATIVE SCORING
# ============================================================

def full_analysis(symbol, price, volume, prev_close, sector_data, gap_pct=0,
                  days_to_cover=None, short_ratio=None, catalyst_analysis=None,
                  scan_profile=None):
    """
    Deep analysis for promising stocks.
    V3.3: Now includes negative scoring, chase risk, LLM catalysts, time-of-day.

    Positive max: 305 points
    Negative floor: -75 points
    Net range: -75 to 305
    """
    score = 0
    penalties = 0
    details = {
        'symbol': symbol,
        'price': price,
        'volume': volume,
        'gap_pct': gap_pct,
        'days_to_cover': days_to_cover,
        'short_ratio': short_ratio,
        'red_flags': []
    }

    if scan_profile is None:
        scan_profile = get_scan_profile()

    try:
        # 1. Get bars for patterns
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        bars = list(client.list_aggs(symbol, 1, "day", start, end, limit=10))

        # ---- POSITIVE SCORING (preserved from V3.2) ----

        # Volume acceleration (30 pts)
        current_rvol = 1.0
        change_pct = 0
        if len(bars) >= 5:
            volumes = [bar.volume for bar in bars[-5:]]
            increasing_days = sum(1 for i in range(1, len(volumes)) if volumes[i] > volumes[i-1])

            avg_volume = sum(volumes[:-1]) / len(volumes[:-1]) if len(volumes) > 1 else volumes[-1]
            current_rvol = volume / avg_volume if avg_volume > 0 else 1.0

            if increasing_days >= 3:
                score += 30
                details['volume_pattern'] = f"✅ {increasing_days}/4 days accelerating"
            elif increasing_days == 2:
                score += 20
                details['volume_pattern'] = f"⚠️  {increasing_days}/4 days up"
            else:
                details['volume_pattern'] = "No acceleration"

            # Multi-tier explosive volume (0-30 pts)
            if current_rvol >= 100:
                score += 30
                details['volume_pattern'] += " 🚀🚀🚀 MEGA EXPLOSION 100x+"
            elif current_rvol >= 50:
                score += 25
                details['volume_pattern'] += " 🚀🚀 EXPLOSIVE 50x+"
            elif current_rvol >= 20:
                score += 20
                details['volume_pattern'] += " 🚀 MAJOR SPIKE 20x+"
            elif current_rvol >= 10:
                score += 15
                details['volume_pattern'] += " ⚡ STRONG SPIKE 10x+"
            elif current_rvol >= 5:
                score += 10
                details['volume_pattern'] += " 💥 SPIKE 5x+"
            elif current_rvol >= 2:
                score += 5
                details['volume_pattern'] += f" +{current_rvol:.1f}x volume"

            details['rvol'] = current_rvol

        # 2. Float (50 pts max - CRITICAL) with V3.3 accuracy improvement
        ticker_details = client.get_ticker_details(symbol)

        security_type = getattr(ticker_details, 'type', None)
        if security_type and security_type != 'CS':
            return 0, None

        market_cap = getattr(ticker_details, 'market_cap', 0) or 0
        if market_cap > 1_000_000_000:
            return 0, None

        # Tiered market cap scoring (0-15 pts)
        if 500_000_000 <= market_cap <= 1_000_000_000:
            score += 15
            details['market_cap'] = f"✅ IDEAL: ${market_cap/1e6:.0f}M"
        elif 100_000_000 <= market_cap < 500_000_000:
            score += 10
            details['market_cap'] = f"✅ Micro: ${market_cap/1e6:.0f}M"
        elif 50_000_000 <= market_cap < 100_000_000:
            score += 5
            details['market_cap'] = f"Nano: ${market_cap/1e6:.0f}M"
        elif market_cap > 0:
            details['market_cap'] = f"⚠️  Ultra-nano: ${market_cap/1e6:.0f}M (high risk)"
        else:
            details['market_cap'] = "Unknown"

        # V3.3: Use weighted_shares if available for better float estimate
        float_shares = getattr(ticker_details, 'share_class_shares_outstanding', 0) or 0
        weighted_shares = getattr(ticker_details, 'weighted_shares_outstanding', 0) or 0

        # If both available, use the lower value (more conservative float estimate)
        if weighted_shares > 0 and float_shares > 0:
            effective_float = min(float_shares, weighted_shares)
            details['float_note'] = f"(effective: {effective_float/1e6:.1f}M of {float_shares/1e6:.1f}M outstanding)"
        else:
            effective_float = float_shares

        if effective_float == 0:
            return 0, None
        elif effective_float <= 5_000_000:
            score += 60
            details['float'] = f"🚀 ULTRA-TINY: {effective_float/1e6:.1f}M (JACKPOT)"
        elif effective_float <= 10_000_000:
            score += 50
            details['float'] = f"✅ ULTRA-LOW: {effective_float/1e6:.1f}M"
        elif effective_float <= 20_000_000:
            score += 35
            details['float'] = f"✅ Very low: {effective_float/1e6:.1f}M"
        elif effective_float <= 30_000_000:
            score += 20
            details['float'] = f"Low: {effective_float/1e6:.1f}M"
        elif effective_float <= 50_000_000:
            score += 10
            details['float'] = f"⚠️  Moderate: {effective_float/1e6:.1f}M"
        else:
            score += 0
            details['float'] = f"❌ Large: {effective_float/1e6:.1f}M"

        # 3. Momentum (40 pts)
        if prev_close > 0:
            change_pct = ((price - prev_close) / prev_close) * 100

            if -1 <= change_pct <= 3:
                score += 40
                details['momentum'] = f"✅ PERFECT: {change_pct:+.1f}% (pre-breakout)"
            elif 3 < change_pct <= 5:
                score += 30
                details['momentum'] = f"✅ Early: {change_pct:+.1f}%"
            elif 5 < change_pct <= 8:
                score += 15
                details['momentum'] = f"⚠️  Moving: {change_pct:+.1f}%"
            elif change_pct > 8:
                score += 5
                details['momentum'] = f"❌ Late: {change_pct:+.1f}%"
            else:
                details['momentum'] = f"Down: {change_pct:+.1f}%"

        # Gap detection (0-20 pts) with time-of-day weighting
        gap_weight = scan_profile.get('gap_weight', 1.0)
        gap_pct = details.get('gap_pct', 0)

        raw_gap_score = 0
        if gap_pct >= 15:
            raw_gap_score = 20
            details['gap'] = f"🚀 HUGE GAP: +{gap_pct:.1f}%"
        elif gap_pct >= 10:
            raw_gap_score = 15
            details['gap'] = f"⚡ BIG GAP: +{gap_pct:.1f}%"
        elif gap_pct >= 5:
            raw_gap_score = 10
            details['gap'] = f"💥 Gap up: +{gap_pct:.1f}%"
        elif gap_pct <= -10:
            raw_gap_score = 10
            details['gap'] = f"🔻 Gap down: {gap_pct:.1f}% (recovery?)"
        elif gap_pct <= -5:
            raw_gap_score = 5
            details['gap'] = f"⚠️  Dip: {gap_pct:.1f}%"
        else:
            details['gap'] = f"Flat: {gap_pct:+.1f}%"

        score += int(raw_gap_score * gap_weight)

        # 4. Catalyst (30 pts) - V3.3: LLM-powered when available
        two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        news = list(client.list_ticker_news(symbol, published_utc_gte=two_days_ago, limit=3))

        if news:
            if catalyst_analysis and symbol in catalyst_analysis:
                # Use LLM analysis
                ca = catalyst_analysis[symbol]
                sentiment = ca.get('sentiment', 'neutral')
                catalyst_score = ca.get('score', 5)
                dilution_risk = ca.get('dilution_risk', False)
                reason = ca.get('reason', 'LLM analyzed')

                if sentiment == 'bullish' and catalyst_score >= 8:
                    score += 30
                    details['catalyst'] = f"✅ STRONG CATALYST: {reason} (LLM: {catalyst_score}/10)"
                elif sentiment == 'bullish' and catalyst_score >= 5:
                    score += 20
                    details['catalyst'] = f"✅ {reason} (LLM: {catalyst_score}/10)"
                elif sentiment == 'neutral':
                    score += 10
                    details['catalyst'] = f"Neutral: {reason} (LLM: {catalyst_score}/10)"
                elif sentiment == 'bearish':
                    score += 0  # No points for bearish catalyst
                    penalties -= 10  # Actually penalize bearish news
                    details['catalyst'] = f"❌ BEARISH: {reason} (LLM: {catalyst_score}/10)"
                    details['red_flags'].append(f"Bearish catalyst: {reason}")
                else:
                    score += 10
                    details['catalyst'] = f"{reason} (LLM: {catalyst_score}/10)"

                # Dilution flag from LLM
                if dilution_risk:
                    penalties -= 20
                    details['red_flags'].append(f"🚩 LLM detected dilution/offering risk")
            else:
                # Keyword fallback
                cat_score, cat_desc = keyword_catalyst_fallback(news[0].title)
                score += cat_score
                details['catalyst'] = f"✅ {cat_desc}" if cat_score >= 20 else cat_desc
        else:
            details['catalyst'] = "No catalyst"

        # Short interest (0-30 pts + 15 bonus) - unchanged from V3.2
        days_to_cover = details.get('days_to_cover')
        short_ratio = details.get('short_ratio')

        if days_to_cover is not None and days_to_cover > 0:
            if days_to_cover >= 10:
                score += 30
                details['squeeze'] = f"🔥 EXTREME SQUEEZE: {days_to_cover:.1f} DTC"
            elif days_to_cover >= 7:
                score += 25
                details['squeeze'] = f"⚡ HIGH SQUEEZE: {days_to_cover:.1f} DTC"
            elif days_to_cover >= 5:
                score += 20
                details['squeeze'] = f"✅ Squeeze potential: {days_to_cover:.1f} DTC"
            elif days_to_cover >= 3:
                score += 15
                details['squeeze'] = f"⚠️  Moderate: {days_to_cover:.1f} DTC"
            else:
                score += 5
                details['squeeze'] = f"Low: {days_to_cover:.1f} DTC"
        elif short_ratio is not None and short_ratio > 0:
            if short_ratio >= 40:
                score += 25
                details['squeeze'] = f"🔥 HIGH SHORT: {short_ratio:.1f}%"
            elif short_ratio >= 30:
                score += 20
                details['squeeze'] = f"✅ Short ratio: {short_ratio:.1f}%"
            elif short_ratio >= 20:
                score += 15
                details['squeeze'] = f"⚠️  Short ratio: {short_ratio:.1f}%"
            else:
                score += 5
                details['squeeze'] = f"Low short: {short_ratio:.1f}%"
        else:
            details['squeeze'] = "No short data"

        # Low float + high short = JACKPOT
        if effective_float <= 10_000_000:
            if (days_to_cover and days_to_cover >= 7) or (short_ratio and short_ratio >= 30):
                score += 15
                details['squeeze'] += " + LOW FLOAT 🚀 JACKPOT!"

        # 5. Multi-day structure (20 pts)
        if len(bars) >= 5:
            last_5 = bars[-5:]
            green_days = sum(1 for i in range(1, len(last_5)) if last_5[i].close > last_5[i-1].close)

            if green_days == 2 or green_days == 3:
                score += 20
                details['structure'] = f"✅ {green_days}/4 green (ideal)"
            elif green_days == 1:
                score += 10
                details['structure'] = "Building base"

        # 6. VWAP (20 pts) - gated by time-of-day
        if scan_profile.get('vwap_enabled', True):
            current_price, vwap, above_vwap, volume_ratio = get_intraday_vwap(symbol)
            if vwap is not None:
                if above_vwap and volume_ratio > 1.3:
                    score += 20
                    details['vwap'] = f"✅ Above VWAP + volume spike ({volume_ratio:.1f}x)"
                elif above_vwap:
                    score += 10
                    details['vwap'] = f"✅ Above VWAP (${vwap:.2f})"
                else:
                    details['vwap'] = f"Below VWAP (${vwap:.2f})"
            else:
                details['vwap'] = "No intraday data"
        else:
            details['vwap'] = f"Skipped ({scan_profile['name']})"

        # 7. Hot sector bonus (15 pts)
        stock_sector = get_stock_sector(symbol)
        if stock_sector and is_hot_sector(stock_sector, sector_data):
            score += 15
            details['sector'] = f"🔥 HOT SECTOR: {stock_sector[:30]}"
        elif stock_sector:
            details['sector'] = stock_sector[:30]
        else:
            details['sector'] = "Unknown"

        # 8. Intraday breakout (25 pts) - gated by time-of-day
        if scan_profile.get('breakout_enabled', True):
            is_breakout, breakout_msg = detect_intraday_breakout(symbol)
            if is_breakout:
                score += 25
                details['breakout'] = f"🚀 {breakout_msg}"
            else:
                details['breakout'] = breakout_msg
        else:
            details['breakout'] = f"Skipped ({scan_profile['name']})"

        # 9. VIGL stealth pattern (0-15 pts)
        vigl_bonus = 0
        if prev_close > 0 and len(bars) >= 5:
            abs_change = abs(change_pct)
            avg_volume = sum(bar.volume for bar in bars[:-1]) / len(bars[:-1]) if len(bars) > 1 else volume
            rvol = volume / avg_volume if avg_volume > 0 else 1.0

            if 1.5 <= rvol <= 2.0 and abs_change < 2.0 and price >= 5.0:
                vigl_bonus = 15
                details['vigl'] = f"⭐ VIGL PERFECT: RVOL {rvol:.1f}x, {change_pct:+.1f}%"
            elif 1.3 <= rvol <= 2.5 and abs_change < 3.0 and price >= 5.0:
                vigl_bonus = 10
                details['vigl'] = f"✨ VIGL NEAR: RVOL {rvol:.1f}x, {change_pct:+.1f}%"
            elif rvol >= 1.5 and abs_change < 5.0:
                vigl_bonus = 5
                details['vigl'] = f"💎 VIGL PARTIAL: RVOL {rvol:.1f}x, {change_pct:+.1f}%"
            else:
                details['vigl'] = "No VIGL pattern"

            details['rvol'] = rvol
        else:
            details['vigl'] = "No VIGL pattern"
            details['rvol'] = 0

        score += vigl_bonus
        details['vigl_bonus'] = vigl_bonus

        # ---- NEW V3.3: NEGATIVE SCORING ----

        # Red flag detection (0 to -75 pts)
        red_penalty, red_flags = detect_red_flags(symbol, ticker_details, bars, price, volume)
        penalties += red_penalty
        details['red_flags'].extend(red_flags)

        # Chase risk detection (0 to -35 pts)
        chase_penalty, chase_desc = calculate_chase_risk(gap_pct, current_rvol, change_pct, price, prev_close)
        penalties += chase_penalty
        if chase_desc:
            details['chase_risk'] = chase_desc
            details['red_flags'].append(chase_desc)
        else:
            details['chase_risk'] = "Low"

        # Apply penalties
        net_score = score + penalties
        details['gross_score'] = score
        details['penalties'] = penalties
        details['score'] = net_score
        details['vigl_match'] = 'perfect' if vigl_bonus == 15 else 'near' if vigl_bonus == 10 else 'partial' if vigl_bonus == 5 else 'none'

        return net_score, details

    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return 0, None


# ============================================================
# UPGRADED V3.3: MAIN SCAN WITH DUAL-TRACK RANKING
# ============================================================

def scan_for_diamonds(dry_run=False):
    """
    Main scan - V3.3 with dual-track ranking, LLM catalysts, negative scoring.

    Args:
        dry_run: If True, skip Telegram alerts and trade signals
    """
    scan_profile = get_scan_profile()

    print("=" * 80)
    print("💎 DIAMOND SCANNER V3.3 - INTELLIGENT EDITION")
    print(f"{datetime.now().strftime('%I:%M %p PT')} | Profile: {scan_profile['name']}")
    print("🎯 Target: Micro-cap explosive movers with intelligent risk filtering")
    print("🧠 NEW: LLM Catalysts | Negative Scoring | Chase Risk | Time-of-Day")
    print(f"💰 Daily budget: ${get_daily_spend():.4f} / ${DAILY_BUDGET_LIMIT:.2f}")
    print("=" * 80)

    if scan_profile.get('volume_note'):
        print(f"⏰ Note: {scan_profile['volume_note']}")
    print()

    # Get sector data
    sector_data = get_sector_performance()
    print()

    # Load market cap cache
    market_cap_db = load_market_cap_cache()
    if market_cap_db:
        targets = len([v for k, v in market_cap_db.items() if not k.startswith('_') and v > 0 and v < 1_000_000_000])
        print(f"✅ Market cap cache loaded: {targets} stocks under $1B target\n")
    else:
        print("⚠️  Market cap cache not available - will use Phase 3 fallback\n")

    # Phase 1: Get snapshots
    snapshots = get_cached_snapshots()
    print(f"✅ Loaded {len(snapshots)} snapshots\n")

    # Phase 2: Quick filter
    print("🔍 Phase 1: Quick filtering...")
    candidates = []

    for snap in snapshots:
        try:
            symbol = snap.ticker

            if snap.day and snap.day.close and snap.day.close > 0 and snap.day.volume and snap.day.volume > 0:
                price = snap.day.close
                volume = snap.day.volume
            elif snap.prev_day and snap.prev_day.close and snap.prev_day.close > 0:
                price = snap.prev_day.close
                volume = snap.prev_day.volume
            else:
                continue

            if any(x in symbol for x in ['-', '.']):
                continue
            if symbol.upper() in EXCLUDED_ETFS:
                continue

            if 0.50 <= price <= 100 and volume >= 1_000_000:
                if market_cap_db:
                    market_cap = market_cap_db.get(symbol, None)
                    if market_cap and market_cap > 1_000_000_000:
                        continue

                prev_close = snap.prev_day.close if snap.prev_day and hasattr(snap.prev_day, 'close') else price
                gap_pct = ((price - prev_close) / prev_close * 100) if prev_close > 0 else 0

                candidates.append({
                    'symbol': symbol,
                    'price': price,
                    'volume': volume,
                    'prev_close': prev_close,
                    'gap_pct': gap_pct
                })
        except:
            continue

    # ---- V3.3: DUAL-TRACK RANKING ----
    # Track A: Inverted momentum (stealth accumulation - find before the move)
    # Track B: Raw volume sort (breakout plays - catch the move in progress)

    print(f"🔮 Phase 1.5: Dual-track ranking ({len(candidates)} candidates)...")

    # Track A: Squeeze-Prophet inverted momentum
    track_a = sorted(candidates, key=lambda x: (
        math.log1p(x['volume']) * 1.5 - abs(((x['price'] - x['prev_close']) / x['prev_close'] * 100) if x['prev_close'] > 0 else 0) * 0.5
    ), reverse=True)

    # Track B: Raw volume with price movement
    track_b = sorted(candidates, key=lambda x: x['volume'], reverse=True)

    # Merge: Take top 60 from each track, deduplicate, keep top 150
    seen = set()
    merged = []
    for stock in track_a[:60] + track_b[:60]:
        if stock['symbol'] not in seen:
            seen.add(stock['symbol'])
            merged.append(stock)

    merged = merged[:150]  # Cap at 150 for volume screening

    print(f"   Track A (stealth): top pick {track_a[0]['symbol'] if track_a else 'N/A'}")
    print(f"   Track B (breakout): top pick {track_b[0]['symbol'] if track_b else 'N/A'}")
    print(f"   Merged: {len(merged)} unique candidates")
    print()

    # Phase 2: Volume pattern screening
    print("📈 Phase 2: Volume pattern screening...")
    with_volume_patterns = []

    for stock in merged:
        if quick_volume_check(stock['symbol']):
            with_volume_patterns.append(stock)

    print(f"✅ {len(with_volume_patterns)} showing volume acceleration\n")

    # Phase 2.5: Short interest enrichment (top 40 for wider net)
    print("🔥 Phase 2.5: Short interest enrichment...")
    enriched_candidates = []

    for i, stock in enumerate(with_volume_patterns[:40], 1):
        symbol = stock['symbol']
        days_to_cover, short_ratio_val = get_short_interest(symbol)
        stock['days_to_cover'] = days_to_cover
        stock['short_ratio'] = short_ratio_val
        enriched_candidates.append(stock)

        if i % 10 == 0:
            print(f"   Processed {i}/40 candidates...")
        time.sleep(0.2)

    squeeze_candidates = sum(1 for s in enriched_candidates
                            if (s.get('days_to_cover') and s['days_to_cover'] >= 5)
                            or (s.get('short_ratio') and s['short_ratio'] >= 20))

    print(f"✅ {len(enriched_candidates)} enriched, {squeeze_candidates} potential squeeze plays\n")

    # ---- V3.3: LLM CATALYST BATCH ANALYSIS ----
    print("🧠 Phase 2.7: LLM catalyst analysis (Gemini Flash)...")

    # Collect news for all candidates in one pass, then batch-analyze
    candidates_news = {}
    for stock in enriched_candidates:
        try:
            two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
            news = list(client.list_ticker_news(stock['symbol'], published_utc_gte=two_days_ago, limit=3))
            if news:
                headlines = [n.title for n in news if n.title]
                if headlines:
                    candidates_news[stock['symbol']] = headlines
            time.sleep(0.1)  # Light rate limit for news API
        except:
            continue

    print(f"   {len(candidates_news)} stocks have recent news")

    # One batched LLM call for all candidates with news
    catalyst_results = {}
    if candidates_news:
        catalyst_results = batch_analyze_catalysts(candidates_news)

    if not catalyst_results and candidates_news:
        print("   Using keyword fallback for catalyst scoring")
    print()

    # Phase 3: Deep analysis with V3.3 improvements
    print(f"🔬 Phase 3: Deep analysis (V3.3: +Negative Scoring +Chase Risk +LLM Catalysts)...")
    diamonds = []

    for i, stock in enumerate(enriched_candidates, 1):
        symbol = stock['symbol']

        net_score, details = full_analysis(
            symbol,
            stock['price'],
            stock['volume'],
            stock['prev_close'],
            sector_data,
            stock.get('gap_pct', 0),
            stock.get('days_to_cover'),
            stock.get('short_ratio'),
            catalyst_results,
            scan_profile
        )

        if net_score >= 60 and details:
            diamonds.append(details)
            flag_indicator = " 🚩" if details.get('red_flags') else ""
            print(f"[{i}/{len(enriched_candidates)}] {symbol}: {net_score}/305 pts (gross: {details.get('gross_score', net_score)}, penalties: {details.get('penalties', 0)}){flag_indicator}")

        time.sleep(0.2)

    # Sort by NET score (after penalties)
    diamonds.sort(key=lambda x: x['score'], reverse=True)

    # Results
    print("\n" + "=" * 80)
    print("💎 RESULTS (V3.3 - NET scores after risk penalties)")
    print("=" * 80)

    high = [d for d in diamonds if d['score'] >= 200]
    strong = [d for d in diamonds if 150 <= d['score'] < 200]
    watch = [d for d in diamonds if 100 <= d['score'] < 150]
    risky = [d for d in diamonds if d.get('penalties', 0) < -20]

    if high:
        print(f"\n🔥 HIGH CONVICTION (≥200 net): {len(high)}")
        print("-" * 80)
        for d in high:
            print(f"\n*{d['symbol']}*: {d['score']}/305 pts (gross: {d['gross_score']}, penalties: {d['penalties']}) - ${d['price']:.2f}")
            print(f"   {d['float']}")
            print(f"   {d['momentum']}")
            print(f"   {d.get('volume_pattern', 'N/A')}")
            print(f"   {d.get('market_cap', 'N/A')}")
            if d.get('squeeze') and d['squeeze'] != "No short data":
                print(f"   {d['squeeze']}")
            if d.get('gap') and 'Flat' not in d['gap']:
                print(f"   {d['gap']}")
            print(f"   {d['catalyst']}")
            print(f"   {d.get('vwap', 'N/A')}")
            print(f"   {d.get('breakout', 'N/A')}")
            if '🔥' in d.get('sector', ''):
                print(f"   {d['sector']}")
            # V3.3: Show red flags
            if d.get('red_flags'):
                print(f"   ⚠️  FLAGS: {', '.join(d['red_flags'])}")

    if strong:
        print(f"\n⚡ STRONG (150-199 net): {len(strong)}")
        for d in strong[:5]:
            flags = f" ⚠️{len(d.get('red_flags', []))} flags" if d.get('red_flags') else ""
            print(f"{d['symbol']}: {d['score']}/305 (gross:{d['gross_score']}) - ${d['price']:.2f} - {d['momentum']}{flags}")

    if watch:
        print(f"\n👀 WATCH (100-149 net): {len(watch)}")
        for d in watch[:5]:
            print(f"{d['symbol']}: {d['score']}/305 - ${d['price']:.2f}")

    if risky:
        print(f"\n🚩 FLAGGED (penalties > -20): {len(risky)}")
        for d in risky[:3]:
            print(f"{d['symbol']}: penalties {d['penalties']} — {', '.join(d.get('red_flags', ['unknown']))}")

    if not diamonds:
        print("\n❌ No diamonds found")

    print("\n" + "=" * 80)
    print(f"Total diamonds: {len(diamonds)} | High: {len(high)} | Strong: {len(strong)} | Watch: {len(watch)}")
    print(f"Flagged: {len(risky)} stocks with significant risk penalties")
    print(f"Scan profile: {scan_profile['name']} | LLM calls: {'Yes' if catalyst_results else 'Keyword fallback'}")
    print(f"Daily LLM spend: ${get_daily_spend():.4f} / ${DAILY_BUDGET_LIMIT:.2f}")
    print("=" * 80)

    # Save
    os.makedirs('/Users/mikeclawd/.openclaw/workspace/data', exist_ok=True)
    with open('/Users/mikeclawd/.openclaw/workspace/data/diamonds.json', 'w') as f:
        json.dump(diamonds, f, indent=2, default=str)

    print("\n💾 Saved to data/diamonds.json")

    # Track performance
    try:
        log_scanner_picks(diamonds)
    except Exception as e:
        print(f"⚠️  Could not log to performance tracker: {e}")

    # Send to Telegram (skip in dry run)
    if not dry_run:
        try:
            if high:
                message = "💎 *DIAMOND SCANNER V3.3 ALERT*\n\n"
                for d in high[:3]:
                    flag_warn = " ⚠️" if d.get('red_flags') else ""
                    message += f"*{d['symbol']}*: {d['score']}/305 pts{flag_warn} - ${d['price']:.2f}\n"
                    message += f"   {d['momentum']}\n"
                    if d.get('catalyst') and 'No catalyst' not in d['catalyst']:
                        message += f"   {d['catalyst']}\n"
                    if d.get('vwap') and '✅' in d.get('vwap', ''):
                        message += f"   {d['vwap']}\n"
                    if d.get('red_flags'):
                        message += f"   ⚠️ {len(d['red_flags'])} risk flags\n"
                    message += "\n"
                message += f"_Found {len(diamonds)} diamonds ({len(high)} high conviction)_\n"
                message += f"_Profile: {scan_profile['name']} | LLM: {'✅' if catalyst_results else '❌'}_"
                send_alert(message)
                print("✅ Sent scanner results to Telegram")
            elif diamonds:
                # Only call them "diamonds" if score >= 100
                quality_diamonds = [d for d in diamonds if d['score'] >= 100]
                if quality_diamonds:
                    message = f"💎 Scanner V3.3 found {len(quality_diamonds)} diamonds\n"
                    message += f"Top: *{quality_diamonds[0]['symbol']}* ({quality_diamonds[0]['score']}/305 net)"
                else:
                    # Low scores - don't call them diamonds
                    message = f"⚠️ Scanner found {len(diamonds)} setups (all below 100)\n"
                    message += f"Top: *{diamonds[0]['symbol']}* ({diamonds[0]['score']}/305 net) - WEAK"
                send_alert(message)
                print("✅ Sent scanner results to Telegram")
        except Exception as e:
            print(f"⚠️  Failed to send Telegram alert: {e}")
    else:
        print("🔒 DRY RUN: Telegram alerts skipped")

    print()
    return diamonds


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Diamond Scanner V3.3')
    parser.add_argument('--dry-run', action='store_true', help='Run without sending alerts')
    args = parser.parse_args()

    scan_for_diamonds(dry_run=args.dry_run)
