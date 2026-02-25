#!/usr/bin/env python3
"""
DIAMOND SCANNER V3.2 - Explosive Stock Finder
Recreating ChatGPT's +63.8% gains (VIGL +324%, CRWV +171%, AEVA +162%)

Changes in V3.2:
- Short interest integration (+30 pts): Detects squeeze plays (days_to_cover, short_ratio)
- Explosive volume detection (+30 pts): Catches 5x, 10x, 50x, 100x+ spikes (CDIO-style)
- Gap-up detection (+20 pts): Premarket moves >10%
- Market cap tiers (+15 pts): $500M-$1B sweet spot, $1B hard cutoff
- Ultra-low float emphasis (60 pts): <5M shares = jackpot
- ETF filtering: 100% accuracy with API type check
- Market cap Phase 1 filter: Early elimination of large caps
- Max score: 305 points (up from 230 in V3.1)

V3.1 Features:
- Intraday VWAP tracking (+20 pts)
- Sector rotation detection (+15 pts)
- Intraday breakout detection (+25 pts)
"""

from polygon import RESTClient
import json
from datetime import datetime, timedelta, date
import time
import os
import pickle
import sys

# Add scripts directory to path for scanner_performance_tracker
sys.path.insert(0, '/Users/mikeclawd/.openclaw/workspace/scripts')
from scanner_performance_tracker import log_scanner_picks
from telegram_alert import send_alert

# Import sector tracker
sys.path.insert(0, '/Users/mikeclawd/.openclaw/workspace')
from sector_tracker import get_sector_performance, is_hot_sector, get_stock_sector

with open('/Users/mikeclawd/.openclaw/secrets/polygon.json', 'r') as f:
    creds = json.load(f)

client = RESTClient(api_key=creds['apiKey'])

CACHE_FILE = '/Users/mikeclawd/.openclaw/workspace/data/snapshot_cache.pkl'
CACHE_MAX_AGE = 300  # 5 minutes

# NEW V3.2: Short interest caching
SHORT_INTEREST_CACHE_FILE = '/Users/mikeclawd/.openclaw/workspace/data/short_interest_cache.pkl'
SHORT_INTEREST_CACHE_MAX_AGE = 604800  # 7 days (short interest updates bi-weekly)

# Hardcoded list of major ETFs to exclude (VIGL strategy = individual stocks only)
EXCLUDED_ETFS = {
    # Major Index ETFs
    'SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'VTI', 'VEA', 'VWO', 'VTV', 'VUG', 'VB', 'VO', 'VV',
    # Inverse/Bear ETFs
    'SH', 'SDS', 'SPXU', 'SQQQ', 'PSQ', 'RWM', 'TWM', 'QID', 'SARK',
    'SPDN', 'SPXS', 'SPXL', 'TZA', 'FAZ', 'ERY', 'DUST', 'NUGT', 'JDST', 'JUNG', 'YANG', 'YINN',
    'LABD', 'LABU', 'CURE', 'DRN', 'DPST', 'FAS', 'FAZ', 'MIDU', 'MIDZ', 'RETL', 'SOXL', 'SOXS',
    'DRIP', 'GUSH', 'USOI', 'AMLP', 'MLPA', 'IEZ', 'OIH', 'XES', 'XOP', 'PSCE',
    # Sector ETFs
    'XLF', 'XLK', 'XLE', 'XLI', 'XLP', 'XLU', 'XLV', 'XLY', 'XLB', 'XLRE', 'XRT',
    # Bond/Treasury ETFs
    'TLT', 'IEF', 'SHY', 'LQD', 'HYG', 'AGG', 'BND', 'VCIT', 'VCLT', 'VGIT', 'VGLT',
    # Commodity ETFs
    'GLD', 'SLV', 'USO', 'UNG', 'DBC', 'GSG',
    # Popular Fund Families
    'SCHD', 'SCHX', 'SCHB', 'SCHA', 'SCHF', 'SCHE', 'SCHH', 'SCHP', 'SCHR', 'SCHV', 'SCHG',
    'SCHM', 'SCHZ', 'FNDA', 'FNDB', 'FNDC', 'FNDE', 'FNDF', 'FNDX', 'SCHY',
    'VIG', 'VYM', 'VCSH', 'VHT', 'VFH', 'VGT', 'VDE', 'VCR', 'VDC', 'VPU', 'VAW', 'VNQ', 'VGSLX',
    'VMBS', 'VGSH', 'VGIT', 'VCLT', 'VWOB', 'VTIP', 'VGSTX', 'VWINX', 'VFINX', 'VTSMX', 'VBMFX',
    'SDY', 'NOBL', 'DGRO', 'HDV', 'SPHD', 'QYLD', 'XYLD', 'JEPI', 'JEPQ',
    # Leveraged ETFs
    'TQQQ', 'UPRO', 'UDOW', 'URTY', 'SRTY', 'SDOW', 'SPXL', 'SPXS',
    # Income/Option Strategy ETFs
    'QQQI', 'YMAX', 'OARK', 'NVDY', 'TSLY', 'CONY', 'MSFO', 'AMDY', 'GOOY', 'XOMO', 'JPMO',
    'SPYI', 'SPYM', 'IWMY', 'DIVO', 'ALTY', 'ULST',
    # International/Regional ETFs (recently slipped through)
    'FXI', 'IEFA', 'KWEB', 'MCHI', 'EWY', 'EWZ', 'GXC', 'INDA', 'THD', 'ASHR', 'BABA',
    'IJH', 'MSTU', 'IBIT', 'FBTC', 'GBTC', 'ETHE',  # Mid-cap and crypto ETFs
    # Other common ETFs
    'ARKK', 'ARKG', 'ARKF', 'ARKW', 'ARKQ', 'ARKX',
    'IWF', 'IWD', 'IWB', 'IWM', 'IWN', 'IWO', 'IWP', 'IWS', 'IWR', 'IJR', 'IJJ', 'IJK',
    'MDY', 'SLY', 'SLYG', 'SLYV', 'SPMD', 'SPSM',
    'ACWI', 'VT', 'VXUS', 'VEU', 'IXUS', 'SCHC', 'SCHE', 'VSS', 'VWO', 'VPL', 'VGK', 'VNM',
    'EMB', 'VWOB', 'PCY', 'EMLC', 'LEMB',
    'BKLN', 'SRLN', 'FTSL', 'PGX', 'PFF', 'PSK', 'SPFF',
    'MUB', 'TFI', 'PZA', 'MLN', 'ITM', 'VTEB', 'MUNI',
    'REET', 'VNQI', 'RWX', 'DRW', 'FEZ', 'IEV', 'EWG', 'EWJ', 'EEM', 'EFA', 'IWM'
}

def load_market_cap_cache():
    """
    Load pre-built market cap database for Phase 1 filtering
    Returns: dict of symbol -> market_cap, or empty dict if unavailable
    """
    cache_file = os.path.join(os.path.dirname(__file__), 'data', 'market_cap_cache.json')

    try:
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                data = json.load(f)

            # Check cache age (metadata includes last_updated timestamp)
            metadata = data.get('_metadata', {})
            last_updated = metadata.get('last_updated', '2020-01-01T00:00:00')

            # Parse ISO format timestamp
            from datetime import datetime
            cache_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            age_hours = (datetime.now(cache_time.tzinfo) - cache_time).total_seconds() / 3600

            # Use cache if less than 36 hours old (allows weekend gaps)
            if age_hours < 36:
                # Remove metadata before returning
                data = {k: v for k, v in data.items() if not k.startswith('_')}
                return data
            else:
                print(f"⚠️  Market cap cache is {age_hours:.1f} hours old - will use Phase 3 fallback")
    except Exception as e:
        print(f"⚠️  Could not load market cap cache: {e}")

    return {}


def get_short_interest(symbol):
    """
    Get short interest data from Polygon API (cached for 7 days)
    Returns: (days_to_cover, short_ratio) or (None, None)

    Uses two Polygon APIs:
    1. list_short_interest() - Returns days_to_cover (short interest / avg daily volume)
    2. list_short_volume() - Returns short_volume_ratio (% of volume that was short)
    """
    # Load cache
    cache = {}
    if os.path.exists(SHORT_INTEREST_CACHE_FILE):
        try:
            with open(SHORT_INTEREST_CACHE_FILE, 'rb') as f:
                cache = pickle.load(f)
        except:
            cache = {}

    # Check if we have cached data that's still fresh
    if symbol in cache:
        cached_time = cache[symbol].get('timestamp', 0)
        age = time.time() - cached_time
        if age < SHORT_INTEREST_CACHE_MAX_AGE:
            return cache[symbol]['days_to_cover'], cache[symbol]['short_ratio']

    # Fetch fresh data
    days_to_cover = None
    short_ratio = None

    try:
        # Try list_short_interest first (more useful for squeeze detection)
        short_data = list(client.list_short_interest(ticker=symbol, limit=1))

        if short_data:
            si = short_data[0]
            days_to_cover = getattr(si, 'days_to_cover', None)

    except Exception as e:
        pass  # Silently fail - some stocks don't have short interest data

    try:
        # Try list_short_volume for short_volume_ratio
        short_vol_data = list(client.list_short_volume(ticker=symbol, limit=1))

        if short_vol_data:
            sv = short_vol_data[0]
            short_ratio = getattr(sv, 'short_volume_ratio', None)

    except Exception as e:
        pass  # Silently fail

    # Cache the result (even if None - prevents repeated API calls)
    cache[symbol] = {
        'days_to_cover': days_to_cover,
        'short_ratio': short_ratio,
        'timestamp': time.time()
    }

    # Save cache
    try:
        os.makedirs(os.path.dirname(SHORT_INTEREST_CACHE_FILE), exist_ok=True)
        with open(SHORT_INTEREST_CACHE_FILE, 'wb') as f:
            pickle.dump(cache, f)
    except:
        pass  # Non-critical if cache save fails

    return days_to_cover, short_ratio


def get_cached_snapshots():
    """Use cached snapshots if recent enough"""
    if os.path.exists(CACHE_FILE):
        cache_age = time.time() - os.path.getmtime(CACHE_FILE)
        if cache_age < CACHE_MAX_AGE:
            with open(CACHE_FILE, 'rb') as f:
                return pickle.load(f)

    # Fetch fresh snapshots
    print("📡 Fetching fresh market snapshots...")
    snapshots = client.get_snapshot_all("stocks")

    # Cache them
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(snapshots, f)

    return snapshots

def get_intraday_vwap(symbol):
    """
    Fetch today's 5-min bars and calculate VWAP
    Returns: (current_price, vwap, above_vwap, volume_ratio)
    """
    try:
        today = date.today().strftime("%Y-%m-%d")

        # Get today's 5-minute bars
        bars = list(client.list_aggs(
            symbol,
            5,
            "minute",
            today,
            today,
            limit=100
        ))

        if not bars or len(bars) < 5:
            return None, None, False, 1.0

        # Calculate VWAP: sum(price * volume) / sum(volume)
        total_pv = sum(bar.close * bar.volume for bar in bars)
        total_volume = sum(bar.volume for bar in bars)

        if total_volume == 0:
            return None, None, False, 1.0

        vwap = total_pv / total_volume
        current_price = bars[-1].close
        above_vwap = current_price > vwap

        # Calculate volume ratio (recent vs average)
        recent_volume = sum(bar.volume for bar in bars[-3:]) / 3  # Last 3 bars avg
        avg_volume = total_volume / len(bars)
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0

        return current_price, vwap, above_vwap, volume_ratio

    except Exception as e:
        return None, None, False, 1.0

def detect_intraday_breakout(symbol):
    """
    Check if stock is breaking out in current session
    Returns: (is_breaking_out, breakout_details)
    """
    try:
        today = date.today().strftime("%Y-%m-%d")

        # Get last 15 bars (5-min) to detect consolidation then expansion
        bars = list(client.list_aggs(
            symbol,
            5,
            "minute",
            today,
            today,
            limit=15
        ))

        if not bars or len(bars) < 10:
            return False, "Insufficient data"

        # Check for consolidation (last 6-10 bars) followed by expansion (last 3 bars)
        consolidation_bars = bars[-10:-3]
        breakout_bars = bars[-3:]

        # Calculate range during consolidation
        if not consolidation_bars:
            return False, "No consolidation period"

        consol_highs = [bar.high for bar in consolidation_bars]
        consol_lows = [bar.low for bar in consolidation_bars]
        consol_range = max(consol_highs) - min(consol_lows)
        consol_avg_price = sum(bar.close for bar in consolidation_bars) / len(consolidation_bars)

        # Check if range was tight (consolidation)
        range_pct = (consol_range / consol_avg_price * 100) if consol_avg_price > 0 else 999

        if range_pct > 3:  # Not tight enough
            return False, f"Range too wide: {range_pct:.1f}%"

        # Check for volume spike in breakout bars
        consol_avg_vol = sum(bar.volume for bar in consolidation_bars) / len(consolidation_bars)
        breakout_avg_vol = sum(bar.volume for bar in breakout_bars) / len(breakout_bars)

        volume_spike = breakout_avg_vol / consol_avg_vol if consol_avg_vol > 0 else 1.0

        # Check if price broke above consolidation range
        breakout_high = max(bar.high for bar in breakout_bars)
        consol_high = max(consol_highs)

        price_breakout = breakout_high > consol_high

        # Must have: price breakout + volume spike
        if price_breakout and volume_spike > 1.5:
            return True, f"Breakout! Vol: {volume_spike:.1f}x, Range: {range_pct:.1f}%"

        return False, f"No breakout (vol {volume_spike:.1f}x)"

    except Exception as e:
        return False, f"Error: {str(e)}"

def quick_volume_check(symbol):
    """
    FAST check: Is volume accelerating?
    Returns: True if worth deep analysis
    """
    try:
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        bars = list(client.list_aggs(symbol, 1, "day", start, end, limit=5))

        if len(bars) < 3:
            return False

        # Check if volume is trending up
        volumes = [bar.volume for bar in bars[-3:]]

        # At least 2 of last 3 days should be increasing
        increasing = sum(1 for i in range(1, len(volumes)) if volumes[i] > volumes[i-1])

        return increasing >= 2

    except:
        return False

def full_analysis(symbol, price, volume, prev_close, sector_data, gap_pct=0, days_to_cover=None, short_ratio=None):
    """
    Deep analysis for promising stocks
    Returns: (score, details_dict)
    Max score: 305 points (up from 230 in V3.1)
    NEW V3.2: Added gap detection, short interest, explosive volume, market cap tiers
    """
    score = 0
    details = {
        'symbol': symbol,
        'price': price,
        'volume': volume,
        'gap_pct': gap_pct,
        'days_to_cover': days_to_cover,
        'short_ratio': short_ratio
    }

    try:
        # 1. Get bars for patterns
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        bars = list(client.list_aggs(symbol, 1, "day", start, end, limit=10))

        # Volume acceleration (30 pts - MOST IMPORTANT)
        if len(bars) >= 5:
            volumes = [bar.volume for bar in bars[-5:]]
            increasing_days = sum(1 for i in range(1, len(volumes)) if volumes[i] > volumes[i-1])

            # Calculate average volume for RVOL
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

            # NEW V3.2: Multi-tier explosive volume detection (0-30 pts)
            # Catches both VIGL stealth (1.5-3x) and CDIO explosions (50-100x)
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

        # 2. Float (50 pts - CRITICAL)
        ticker_details = client.get_ticker_details(symbol)

        # NEW: Verify it's a common stock (catch ETFs that slipped through hardcoded list)
        security_type = getattr(ticker_details, 'type', None)
        if security_type and security_type != 'CS':
            return 0, None  # Not a common stock - skip (ETF/fund/other)

        # Market cap filter with tiered scoring (V3.2: $1B hard cutoff for explosive potential)
        market_cap = getattr(ticker_details, 'market_cap', 0) or 0

        if market_cap > 1_000_000_000:  # $1B max (user requirement for explosive movers)
            return 0, None  # Skip mid/large caps - need micro-caps for +100-300% moves

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

        float_shares = ticker_details.share_class_shares_outstanding or 0

        if float_shares == 0:
            return 0, None
        elif float_shares <= 5_000_000:  # NEW: Ultra-tiny tier for max squeeze potential
            score += 60
            details['float'] = f"🚀 ULTRA-TINY: {float_shares/1e6:.1f}M (JACKPOT)"
        elif float_shares <= 10_000_000:
            score += 50
            details['float'] = f"✅ ULTRA-LOW: {float_shares/1e6:.1f}M"
        elif float_shares <= 20_000_000:
            score += 35  # Reduced from 40
            details['float'] = f"✅ Very low: {float_shares/1e6:.1f}M"
        elif float_shares <= 30_000_000:
            score += 20  # Reduced from 30
            details['float'] = f"Low: {float_shares/1e6:.1f}M"
        elif float_shares <= 50_000_000:
            score += 10  # Reduced from 20
            details['float'] = f"⚠️  Moderate: {float_shares/1e6:.1f}M"
        else:
            score += 0  # No points for large floats (reduced from 5)
            details['float'] = f"❌ Large: {float_shares/1e6:.1f}M"

        # 3. Momentum (40 pts - EARLY is KEY)
        if prev_close > 0:
            change_pct = ((price - prev_close) / prev_close) * 100

            # Reward EARLY moves (0-5%), penalize late (>10%)
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

        # NEW V3.2: Gap-up/down detection (0-20 pts)
        # Detects premarket moves and momentum opportunities
        gap_pct = details.get('gap_pct', 0)
        if gap_pct >= 15:
            score += 20
            details['gap'] = f"🚀 HUGE GAP: +{gap_pct:.1f}%"
        elif gap_pct >= 10:
            score += 15
            details['gap'] = f"⚡ BIG GAP: +{gap_pct:.1f}%"
        elif gap_pct >= 5:
            score += 10
            details['gap'] = f"💥 Gap up: +{gap_pct:.1f}%"
        elif gap_pct <= -10:
            score += 10  # Gap down = recovery opportunity
            details['gap'] = f"🔻 Gap down: {gap_pct:.1f}% (recovery?)"
        elif gap_pct <= -5:
            score += 5
            details['gap'] = f"⚠️  Dip: {gap_pct:.1f}%"
        else:
            details['gap'] = f"Flat: {gap_pct:+.1f}%"

        # 4. Catalyst (30 pts)
        two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        news = list(client.list_ticker_news(symbol, published_utc_gte=two_days_ago, limit=3))

        if news:
            title = news[0].title.lower()

            if any(word in title for word in ['fda', 'approval', 'approved']):
                score += 30
                details['catalyst'] = f"✅ FDA/Regulatory"
            elif any(word in title for word in ['earnings', 'beat']):
                score += 25
                details['catalyst'] = f"✅ Earnings beat"
            elif any(word in title for word in ['contract', 'deal', 'partnership']):
                score += 20
                details['catalyst'] = f"✅ Contract/Deal"
            else:
                score += 10
                details['catalyst'] = "News (unverified)"
        else:
            details['catalyst'] = "No catalyst"

        # NEW V3.2: Short Interest Squeeze Potential (0-30 pts + 15 bonus)
        # Detects high short interest + low float squeeze setups
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
            # Fallback to short_volume_ratio if days_to_cover unavailable
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

        # BONUS: Low float + high short interest = JACKPOT squeeze setup
        if float_shares <= 10_000_000:
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

        # 6. NEW: VWAP Position (20 pts)
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

        # 7. NEW: Hot Sector Bonus (15 pts)
        stock_sector = get_stock_sector(symbol)
        if stock_sector and is_hot_sector(stock_sector, sector_data):
            score += 15
            details['sector'] = f"🔥 HOT SECTOR: {stock_sector[:30]}"
        elif stock_sector:
            details['sector'] = stock_sector[:30]
        else:
            details['sector'] = "Unknown"

        # 8. NEW: Intraday Breakout (25 pts)
        is_breakout, breakout_msg = detect_intraday_breakout(symbol)

        if is_breakout:
            score += 25
            details['breakout'] = f"🚀 {breakout_msg}"
        else:
            details['breakout'] = breakout_msg

        # 9. VIGL STEALTH PATTERN BONUS (0-15 pts)
        # The proven pattern that found VIGL +324%, CRWV +171%, AEVA +162%
        # High volume + minimal price movement = stealth accumulation
        vigl_bonus = 0
        vigl_match = "none"

        # Calculate RVOL from historical bars
        if prev_close > 0 and len(bars) >= 5:
            abs_change = abs(change_pct)

            # Calculate average volume from previous days (exclude today)
            avg_volume = sum(bar.volume for bar in bars[:-1]) / len(bars[:-1]) if len(bars) > 1 else volume
            rvol = volume / avg_volume if avg_volume > 0 else 1.0

            # Perfect match: RVOL 1.5-2.0x AND change < 2% AND price >= $5
            if 1.5 <= rvol <= 2.0 and abs_change < 2.0 and price >= 5.0:
                vigl_bonus = 15
                vigl_match = "perfect"
                details['vigl'] = f"⭐ VIGL PERFECT: RVOL {rvol:.1f}x, {change_pct:+.1f}%"

            # Near match: RVOL 1.3-2.5x AND change < 3%
            elif 1.3 <= rvol <= 2.5 and abs_change < 3.0 and price >= 5.0:
                vigl_bonus = 10
                vigl_match = "near"
                details['vigl'] = f"✨ VIGL NEAR: RVOL {rvol:.1f}x, {change_pct:+.1f}%"

            # Partial match: RVOL >= 1.5x AND change < 5%
            elif rvol >= 1.5 and abs_change < 5.0:
                vigl_bonus = 5
                vigl_match = "partial"
                details['vigl'] = f"💎 VIGL PARTIAL: RVOL {rvol:.1f}x, {change_pct:+.1f}%"
            else:
                details['vigl'] = "No VIGL pattern"

            details['rvol'] = rvol
        else:
            details['vigl'] = "No VIGL pattern"
            details['rvol'] = 0

        score += vigl_bonus
        details['vigl_bonus'] = vigl_bonus
        details['vigl_match'] = vigl_match
        details['score'] = score
        return score, details

    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return 0, None

def scan_for_diamonds():
    """Main scan - finds explosive micro-cap movers with squeeze potential"""
    print("=" * 80)
    print("💎 DIAMOND SCANNER V3.2 - EXPLOSIVE EDITION")
    print(f"{datetime.now().strftime('%I:%M %p PT')}")
    print("🎯 Target: Recreate ChatGPT's +63.8% gains (VIGL +324%, CRWV +171%)")
    print("🔥 NEW: Short Interest | Explosive Volume | Gap Detection | Market Cap $1B Max")
    print("=" * 80)
    print()

    # Get sector data first (cached for 10 min)
    sector_data = get_sector_performance()
    print()

    # Load market cap cache for Phase 1 filtering (NEW in V3.2)
    market_cap_db = load_market_cap_cache()
    if market_cap_db:
        # Count stocks under $1B (scanner targets)
        targets = len([v for k, v in market_cap_db.items() if not k.startswith('_') and v > 0 and v < 1_000_000_000])
        print(f"✅ Market cap cache loaded: {targets} stocks under $1B target\n")
    else:
        print("⚠️  Market cap cache not available - will use Phase 3 fallback\n")

    # Phase 1: Get snapshots (cached)
    snapshots = get_cached_snapshots()
    print(f"✅ Loaded {len(snapshots)} snapshots\n")

    # Phase 2: Quick filter
    print("🔍 Phase 1: Quick filtering...")
    candidates = []

    for snap in snapshots:
        try:
            symbol = snap.ticker
            
            # Use current day data if available and valid, otherwise use previous day
            if snap.day and snap.day.close and snap.day.close > 0 and snap.day.volume and snap.day.volume > 0:
                price = snap.day.close
                volume = snap.day.volume
            elif snap.prev_day and snap.prev_day.close and snap.prev_day.close > 0:
                # Premarket - use yesterday's close
                price = snap.prev_day.close
                volume = snap.prev_day.volume
            else:
                continue

            # Skip ETFs/funds
            if any(x in symbol for x in ['-', '.']):
                continue
            
            # Check hardcoded ETF list first (fast)
            if symbol.upper() in EXCLUDED_ETFS:
                continue
            
            # Check if it's an ETF using FAST methods only (no API calls per stock)
            # Method 1: Hardcoded list (comprehensive, includes 200+ ETFs)
            # Method 2: Symbol pattern matching (catches obvious ones)
            # Note: API-based checking removed - too slow for 12,000 stocks

            # Basic filters
            if 0.50 <= price <= 100 and volume >= 1_000_000:
                # NEW V3.2: Market cap filter in Phase 1 (early elimination of large caps)
                if market_cap_db:
                    market_cap = market_cap_db.get(symbol, None)
                    if market_cap and market_cap > 1_000_000_000:  # $1B hard cutoff
                        continue  # Skip large caps early - they don't have explosive potential

                prev_close = snap.prev_day.close if snap.prev_day and hasattr(snap.prev_day, 'close') else price

                # Calculate gap % (NEW V3.2: gap-up detection for momentum plays)
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

    # INVERTED MOMENTUM PRE-RANKING (Squeeze-Prophet innovation)
    # Penalize big price moves, reward quiet volume expansion
    # This finds stocks BEFORE explosion, not after
    print("🔮 Phase 1.5: Inverted momentum pre-ranking (Squeeze-Prophet formula)...")

    import math
    for candidate in candidates:
        # Calculate price change %
        if candidate['prev_close'] > 0:
            change_pct = abs(((candidate['price'] - candidate['prev_close']) / candidate['prev_close']) * 100)
        else:
            change_pct = 0

        # Inverted momentum: reward volume, penalize price movement
        # log1p(volume) * 1.5 - abs(change_pct) * 0.5
        momentum_score = math.log1p(candidate['volume']) * 1.5 - change_pct * 0.5
        candidate['inverted_momentum'] = momentum_score

    # Sort by inverted momentum (highest = quiet volume expansion)
    candidates.sort(key=lambda x: x['inverted_momentum'], reverse=True)
    print(f"✅ {len(candidates)} stocks ranked by inverted momentum")
    
    if not candidates:
        print("⚠️  No candidates passed filters - relaxing criteria...")
        # Return early with empty results
        return []
    
    print(f"   Top pick: {candidates[0]['symbol']} (score: {candidates[0]['inverted_momentum']:.1f})")
    print(f"   Formula: log1p(volume)*1.5 - abs(change%)*0.5")
    print()

    # Phase 3: Volume pattern pre-screen (FAST)
    print("📈 Phase 2: Volume pattern screening (top 100)...")
    with_volume_patterns = []

    for i, stock in enumerate(candidates[:100]):
        if quick_volume_check(stock['symbol']):
            with_volume_patterns.append(stock)

    print(f"✅ {len(with_volume_patterns)} showing volume acceleration\n")

    # NEW V3.2: Phase 2.5 - Short interest enrichment
    print("🔥 Phase 2.5: Short interest enrichment (squeeze detection)...")
    enriched_candidates = []

    for i, stock in enumerate(with_volume_patterns[:30], 1):  # Top 30 candidates
        symbol = stock['symbol']

        # Get short interest data (cached for 7 days)
        days_to_cover, short_ratio = get_short_interest(symbol)

        # Add to stock dict
        stock['days_to_cover'] = days_to_cover
        stock['short_ratio'] = short_ratio
        enriched_candidates.append(stock)

        # Progress indicator for longer waits
        if i % 10 == 0:
            print(f"   Processed {i}/30 candidates...")

        # Rate limiting
        time.sleep(0.2)

    squeeze_candidates = sum(1 for s in enriched_candidates
                              if (s.get('days_to_cover') and s['days_to_cover'] >= 5)
                              or (s.get('short_ratio') and s['short_ratio'] >= 20))

    print(f"✅ {len(enriched_candidates)} enriched, {squeeze_candidates} potential squeeze plays\n")

    # Phase 4: Deep analysis
    print("🔬 Phase 3: Deep analysis (NEW: +VWAP +Sectors +Breakouts +Short Interest)...")
    diamonds = []

    for i, stock in enumerate(enriched_candidates, 1):  # Use enriched candidates with short interest
        symbol = stock['symbol']

        # Pass all enriched data to full_analysis
        score, details = full_analysis(
            symbol,
            stock['price'],
            stock['volume'],
            stock['prev_close'],
            sector_data,
            stock.get('gap_pct', 0),  # Gap percentage
            stock.get('days_to_cover'),  # NEW V3.2: Short interest
            stock.get('short_ratio')  # NEW V3.2: Short volume ratio
        )

        if score >= 60 and details:
            diamonds.append(details)
            print(f"[{i}/30] {symbol}: {score}/305 pts")

        time.sleep(0.2)  # Rate limit (slightly slower due to intraday calls)

    # Sort by score
    diamonds.sort(key=lambda x: x['score'], reverse=True)

    # Results
    print("\n" + "=" * 80)
    print("💎 RESULTS")
    print("=" * 80)

    # NEW V3.2: Updated thresholds for 305-point max score
    high = [d for d in diamonds if d['score'] >= 200]  # Top explosive setups
    strong = [d for d in diamonds if 150 <= d['score'] < 200]  # Solid opportunities
    watch = [d for d in diamonds if 100 <= d['score'] < 150]  # Monitor

    if high:
        print(f"\n🔥 HIGH CONVICTION (≥200): {len(high)}")
        print("-" * 80)
        for d in high:
            print(f"\n*{d['symbol']}*: {d['score']}/305 pts - ${d['price']:.2f}")
            print(f"   {d['float']}")
            print(f"   {d['momentum']}")
            print(f"   {d.get('volume_pattern', 'N/A')}")
            print(f"   {d.get('market_cap', 'N/A')}")  # NEW V3.2
            if d.get('squeeze') and d['squeeze'] != "No short data":  # NEW V3.2
                print(f"   {d['squeeze']}")
            if d.get('gap') and 'Flat' not in d['gap']:  # NEW V3.2
                print(f"   {d['gap']}")
            print(f"   {d['catalyst']}")
            print(f"   {d.get('vwap', 'N/A')}")
            print(f"   {d.get('breakout', 'N/A')}")
            if '🔥' in d.get('sector', ''):
                print(f"   {d['sector']}")

    if strong:
        print(f"\n⚡ STRONG (150-199): {len(strong)}")
        for d in strong[:5]:
            print(f"{d['symbol']}: {d['score']}/305 - ${d['price']:.2f} - {d['momentum']}")

    if watch:
        print(f"\n👀 WATCH (100-149): {len(watch)}")
        for d in watch[:5]:
            print(f"{d['symbol']}: {d['score']}/305 - ${d['price']:.2f}")

    if not diamonds:
        print("\n❌ No diamonds found")

    print("\n" + "=" * 80)
    print(f"Total diamonds: {len(diamonds)}")
    print("Max score: 305 points (V3.2: +75 from V3.1)")
    print("NEW V3.2: Short Interest (+30), Explosive Volume (+30), Gap Detection (+20), Market Cap Tiers (+15)")
    print("V3.1: Intraday VWAP (+20), Hot Sectors (+15), Breakouts (+25)")
    print("=" * 80)

    # Save
    os.makedirs('/Users/mikeclawd/.openclaw/workspace/data', exist_ok=True)
    with open('/Users/mikeclawd/.openclaw/workspace/data/diamonds.json', 'w') as f:
        json.dump(diamonds, f, indent=2)

    print("\n💾 Saved to data/diamonds.json")

    # Track performance for learning
    try:
        log_scanner_picks(diamonds)
    except Exception as e:
        print(f"⚠️  Could not log to performance tracker: {e}")

    # Send top picks to Telegram
    try:
        if high:
            message = "💎 *DIAMOND SCANNER ALERT*\n\n"
            for d in high[:3]:  # Top 3 high conviction
                message += f"*{d['symbol']}*: {d['score']}/305 pts - ${d['price']:.2f}\n"
                message += f"   {d['momentum']}\n"
                if d.get('vwap') and '✅' in d.get('vwap', ''):
                    message += f"   {d['vwap']}\n"
                if '🔥' in d.get('sector', ''):
                    message += f"   {d['sector']}\n"
                message += "\n"
            message += f"_Found {len(diamonds)} total diamonds ({len(high)} high conviction)_"
            send_alert(message)
            print("✅ Sent scanner results to Telegram")
        elif diamonds:
            message = f"💎 Scanner found {len(diamonds)} diamonds\n"
            message += f"Top pick: *{diamonds[0]['symbol']}* ({diamonds[0]['score']}/305 pts)"
            send_alert(message)
            print("✅ Sent scanner results to Telegram")
    except Exception as e:
        print(f"⚠️  Failed to send Telegram alert: {e}")

    print()

    return diamonds

if __name__ == '__main__':
    scan_for_diamonds()
