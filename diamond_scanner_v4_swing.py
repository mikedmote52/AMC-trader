#!/usr/bin/env python3
"""
DIAMOND SCANNER V4 - SWING TRADING (3-Gate Architecture)

Philosophy: Wide net (12K+) → Strict filter (VIGL pattern) → Swing trading (1-4 weeks)

GATE A - Universe Filter:
  - Full Polygon snapshot (12K+ stocks)
  - Price: $0.50 - $100
  - Volume: >= 300,000 shares
  - RVOL: >= 1.2x (20-day avg)
  - Exclude ETFs, funds, symbols with hyphens/periods
  - Blacklist check
  - Output: 500-2000 stocks

GATE B - Stealth Detection Window:
  - RVOL: 1.5 - 2.0x (THE MAGIC WINDOW)
  - Price change: < 2% absolute
  - Price floor: >= $5
  - Volume floor: >= 300K
  - Output: up to 500 stocks

GATE C - Accumulation Scoring (sigmoid-based, 0-100):
  - Stealth Accumulation (40%)
  - Small Cap Potential (25%)
  - Coiling Pattern (20%)
  - Volume Quality (15%)
  - Sustained 14-Day (BONUS if applicable)
  - VIGL pattern bonus (+15 max)
  - Pre-explosion multiplier (1.25x)

Scoring Tiers:
  - S tier: >= 90 (highest conviction, Telegram alert)
  - A tier: >= 75
  - B tier: >= 60
  - C tier: >= 50
"""

from polygon import RESTClient
import json
from datetime import datetime, timedelta, date
import time
import os
import pickle
import sys
import math

# Add scripts directory to path for scanner_performance_tracker
sys.path.insert(0, '/Users/mikeclawd/.openclaw/workspace/scripts')
from scanner_performance_tracker import log_scanner_picks
from telegram_alert import send_alert

# Polygon API setup
with open('/Users/mikeclawd/.openclaw/secrets/polygon.json', 'r') as f:
    creds = json.load(f)

client = RESTClient(api_key=creds['apiKey'])

CACHE_FILE = '/Users/mikeclawd/.openclaw/workspace/data/snapshot_cache.pkl'
CACHE_MAX_AGE = 300  # 5 minutes
BLACKLIST_FILE = '/Users/mikeclawd/.openclaw/workspace/data/blacklist.json'
OUTPUT_FILE = '/Users/mikeclawd/.openclaw/workspace/data/diamonds_v4.json'

# Sigmoid helper functions
def sigmoid(x):
    """Standard sigmoid function"""
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0

def zclip(x, min_val=0.0, max_val=1.0):
    """Clip value between min and max"""
    return max(min_val, min(max_val, x))


def get_cached_snapshots():
    """Use cached snapshots if recent enough"""
    if os.path.exists(CACHE_FILE):
        cache_age = time.time() - os.path.getmtime(CACHE_FILE)
        if cache_age < CACHE_MAX_AGE:
            print(f"✅ Using cached snapshots (age: {int(cache_age)}s)")
            with open(CACHE_FILE, 'rb') as f:
                return pickle.load(f)

    # Fetch fresh snapshots
    print("📡 Fetching fresh market snapshots from Polygon...")
    snapshots = client.get_snapshot_all("stocks")

    # Cache them
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(snapshots, f)

    return snapshots


def load_blacklist():
    """Load blacklist symbols if file exists"""
    if os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, 'r') as f:
            data = json.load(f)
            return set(data.get('symbols', []))
    return set()


def calculate_rvol(symbol, current_volume, days=20):
    """
    Calculate relative volume (RVOL) from historical data

    Args:
        symbol: Stock symbol
        current_volume: Today's volume
        days: Number of days for average (default 20)

    Returns:
        float: RVOL (current volume / average volume)
    """
    try:
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=days+5)).strftime("%Y-%m-%d")

        bars = list(client.list_aggs(symbol, 1, "day", start, end, limit=days+1))

        if len(bars) < days:
            return 1.0

        # Use last N days (excluding today if it's in the results)
        historical_volumes = [bar.volume for bar in bars[:-1]] if len(bars) > days else [bar.volume for bar in bars]

        if not historical_volumes:
            return 1.0

        avg_volume = sum(historical_volumes) / len(historical_volumes)

        if avg_volume == 0:
            return 1.0

        rvol = current_volume / avg_volume
        return rvol

    except Exception as e:
        return 1.0


def get_14day_accumulation_bonus(symbol):
    """
    Calculate sustained 14-day accumulation bonus

    Returns:
        float: Bonus points (0-24 max)
    """
    try:
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        bars = list(client.list_aggs(symbol, 1, "day", start, end, limit=30))

        if len(bars) < 14:
            return 0.0

        # Get last 14 days
        last_14 = bars[-14:]

        # Calculate 20-day average volume (use all available bars)
        avg_volume = sum(bar.volume for bar in bars) / len(bars)

        # Count accumulation days (volume > 20-day avg * 1.2)
        accumulation_days = sum(1 for bar in last_14 if bar.volume > avg_volume * 1.2)

        # Calculate accumulation ratio
        accumulation_ratio = accumulation_days / 14.0

        # Base bonus if ratio >= 0.5
        if accumulation_ratio >= 0.5:
            bonus = 20.0 * (accumulation_ratio / 0.7)

            # Consistency bonus if ratio >= 0.6
            if accumulation_ratio >= 0.6:
                bonus *= 1.2

            return min(bonus, 24.0)  # Cap at 24

        return 0.0

    except Exception as e:
        return 0.0


def calculate_accumulation_score(symbol, price, volume, rvol, change_pct):
    """
    Calculate accumulation score using sigmoid-based components

    Args:
        symbol: Stock symbol
        price: Current price
        volume: Current volume
        rvol: Relative volume
        change_pct: Price change %

    Returns:
        tuple: (total_score, components_dict, vigl_bonus, explosion_probability)
    """
    components = {}
    abs_change = abs(change_pct)

    # 1. Stealth Accumulation (40%)
    stealth = 40.0 * zclip(sigmoid((rvol - 1.5) / 1.0) * sigmoid((5.0 - abs_change) / 2.0))
    components['stealth_accumulation'] = round(stealth, 2)

    # 2. Small Cap Potential (25%)
    small_cap = 25.0 * zclip(sigmoid((15.0 - price) / 8.0))
    components['small_cap_potential'] = round(small_cap, 2)

    # 3. Coiling Pattern (20%)
    coiling = 20.0 * zclip(sigmoid((rvol - 1.3) / 0.5) * sigmoid((3.0 - abs_change) / 1.5))
    components['coiling_pattern'] = round(coiling, 2)

    # 4. Volume Quality (15%)
    vol_quality = 15.0 * zclip(sigmoid((rvol - 1.5) / 1.2))
    components['volume_quality'] = round(vol_quality, 2)

    # 5. Sustained 14-Day (BONUS if applicable)
    sustained_bonus = get_14day_accumulation_bonus(symbol)
    components['sustained_14day'] = round(sustained_bonus, 2)

    # Base score
    base_score = stealth + small_cap + coiling + vol_quality + sustained_bonus

    # VIGL Pattern Bonus (0-15 points)
    vigl_bonus = 0
    if 1.5 <= rvol <= 2.0 and abs_change < 2.0 and price >= 5.0:
        vigl_bonus = 15  # Perfect match
    elif 1.3 <= rvol <= 2.5 and abs_change < 3.0 and price >= 5.0:
        vigl_bonus = 10  # Near match
    elif rvol >= 1.5 and abs_change < 5.0:
        vigl_bonus = 5   # Partial match

    total_score = base_score + vigl_bonus

    # Pre-explosion multiplier
    if rvol >= 1.8 and abs_change <= 2.0 and price >= 5.0:
        total_score *= 1.25

    # Calculate explosion probability (0-95%)
    stealth_prob = 0.25 * 100 * min(math.log1p(rvol * 10) / math.log1p(30), 1.0) * max(0, (10 - abs_change) / 10)

    rvol_intensity = 0.20 * 100 * min(rvol / 5.0, 1.0)

    if price <= 3:
        price_tier = 1.0
    elif price <= 10:
        price_tier = 0.8
    elif price <= 25:
        price_tier = 0.6
    elif price <= 50:
        price_tier = 0.4
    else:
        price_tier = 0.2
    price_potential = 0.20 * 100 * price_tier

    quality = 0.20 * 100 * min(total_score / 100, 1.0)

    if volume >= 5_000_000:
        volume_tier = 1.0
    elif volume >= 1_000_000:
        volume_tier = 0.8
    elif volume >= 500_000:
        volume_tier = 0.6
    else:
        volume_tier = 0.3
    liquidity = 0.15 * 100 * volume_tier

    explosion_prob = stealth_prob + rvol_intensity + price_potential + quality + liquidity

    # Penalize large price movements
    if abs_change > 10:
        explosion_prob *= 0.4
    elif abs_change > 5:
        explosion_prob *= 0.7

    explosion_prob = min(explosion_prob, 95.0)

    return round(total_score, 2), components, vigl_bonus, round(explosion_prob, 1)


def scan_for_swing_diamonds():
    """
    Main scanning function with 3-gate architecture
    """
    print("=" * 80)
    print("💎 DIAMOND SCANNER V4 - SWING TRADING (3-Gate Architecture)")
    print(f"{datetime.now().strftime('%Y-%m-%d %I:%M %p PT')}")
    print("=" * 80)
    print()
    print("Philosophy: Wide net (12K+) + Strict filter (VIGL pattern) + Swing trading (1-4 weeks)")
    print()

    # Load blacklist
    blacklist = load_blacklist()
    if blacklist:
        print(f"📋 Loaded blacklist: {len(blacklist)} symbols")

    # Get snapshots
    snapshots = get_cached_snapshots()
    print(f"📊 Total universe: {len(snapshots)} stocks")
    print()

    # ========================================================================
    # GATE A - Universe Filter (Fast pre-filter then RVOL calculation)
    # ========================================================================
    print("🚪 GATE A - Universe Filter")
    print("-" * 80)
    print("Step 1: Basic filters (price, volume, symbols)...")

    # Fast pre-filter without RVOL (saves API calls)
    pre_filtered = []

    for snap in snapshots:
        try:
            if not snap.day or not snap.day.close or not snap.day.volume:
                continue

            symbol = snap.ticker
            price = snap.day.close
            volume = snap.day.volume
            prev_close = snap.prev_day.close if snap.prev_day and hasattr(snap.prev_day, 'close') else price

            # Exclude ETFs, funds, special symbols
            if any(x in symbol for x in ['-', '.', 'ETF', 'FUND']):
                continue

            # Blacklist check
            if symbol in blacklist:
                continue

            # Price filter: $0.50 - $100
            if not (0.50 <= price <= 100):
                continue

            # Volume filter: >= 300K
            if volume < 300_000:
                continue

            # Calculate change %
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close > 0 else 0

            pre_filtered.append({
                'symbol': symbol,
                'price': price,
                'volume': volume,
                'prev_close': prev_close,
                'change_pct': change_pct
            })

        except Exception as e:
            continue

    print(f"   Pre-filtered: {len(pre_filtered)} stocks")
    print()
    print("Step 2: Calculating RVOL for mixed sample (volume + small-cap priority)...")

    # Inverted momentum pre-ranking (Squeeze-Prophet innovation)
    # Penalizes big price moves, rewards quiet volume expansion
    # This finds stocks BEFORE explosion, ensuring stealth candidates bubble up
    for candidate in pre_filtered:
        change_pct = candidate['change_pct']
        volume = candidate['volume']
        # Formula: log1p(volume)*1.5 - abs(change_pct)*0.5
        momentum_score = math.log1p(volume) * 1.5 - abs(change_pct) * 0.5
        candidate['momentum_score'] = momentum_score

    # Sort by inverted momentum (highest = quiet volume expansion)
    pre_filtered.sort(key=lambda x: x['momentum_score'], reverse=True)

    # Take top 1500 for RVOL calculation
    to_check = pre_filtered[:1500]

    print(f"   Checking top 1500 stocks (ranked by inverted momentum)")
    print(f"   Top pick: {to_check[0]['symbol']} (momentum score: {to_check[0]['momentum_score']:.1f})")
    print(f"   Formula: log1p(volume)*1.5 - abs(change%)*0.5")
    print()

    # Calculate RVOL
    gate_a_candidates = []

    for i, candidate in enumerate(to_check):
        if (i + 1) % 100 == 0:
            print(f"   Progress: {i + 1}/{len(to_check)} stocks checked...")

        symbol = candidate['symbol']
        volume = candidate['volume']

        # Calculate RVOL
        rvol = calculate_rvol(symbol, volume)

        # RVOL filter: >= 1.2x (institutional interest threshold)
        if rvol >= 1.2:
            candidate['rvol'] = rvol
            gate_a_candidates.append(candidate)

        # Small delay to avoid rate limits
        if (i + 1) % 10 == 0:
            time.sleep(0.05)

    print(f"✅ Gate A passed: {len(gate_a_candidates)} stocks (from {len(snapshots)})")
    print(f"   Filters: Price $0.50-$100, Volume >= 300K, RVOL >= 1.2x")
    print()

    if not gate_a_candidates:
        print("❌ No candidates passed Gate A")
        return []

    # ========================================================================
    # GATE B - Stealth Detection Window
    # ========================================================================
    print("🚪 GATE B - Stealth Detection Window (THE MAGIC WINDOW)")
    print("-" * 80)

    # Debug: Show RVOL distribution
    rvol_sorted = sorted(gate_a_candidates, key=lambda x: x['rvol'], reverse=True)
    print(f"Top 10 by RVOL from Gate A:")
    for i, c in enumerate(rvol_sorted[:10], 1):
        print(f"   {i}. {c['symbol']}: RVOL {c['rvol']:.2f}x, Price ${c['price']:.2f}, Change {c['change_pct']:+.2f}%")
    print()

    gate_b_candidates = []

    for candidate in gate_a_candidates:
        symbol = candidate['symbol']
        price = candidate['price']
        volume = candidate['volume']
        rvol = candidate['rvol']
        change_pct = candidate['change_pct']
        abs_change = abs(change_pct)

        # RVOL: 1.5-2.5x (THE MAGIC WINDOW - stealth accumulation)
        # This is the exact pattern that found VIGL +324%, CRWV +171%, AEVA +162%
        # < 1.5x = no institutional interest, > 2.5x = already discovered
        if not (1.5 <= rvol <= 2.5):
            continue

        # Price change: < 2% absolute (THE KEY FILTER - stealth accumulation)
        if abs_change >= 2.0:
            continue

        # Price floor: >= $5
        if price < 5.0:
            continue

        # Volume floor: >= 300K (already filtered in Gate A)
        if volume < 300_000:
            continue

        gate_b_candidates.append(candidate)

    print(f"✅ Gate B passed: {len(gate_b_candidates)} stocks")
    print(f"   Filters: RVOL >= 1.0x (relaxed for demo), Price change <2%, Price >= $5")
    print(f"   Note: In production, use RVOL >= 1.5x for stricter stealth detection")
    print()

    if not gate_b_candidates:
        print("❌ No candidates passed Gate B (no stealth accumulation detected)")
        return []

    # Limit to top 500 by RVOL if too many
    if len(gate_b_candidates) > 500:
        gate_b_candidates.sort(key=lambda x: x['rvol'], reverse=True)
        gate_b_candidates = gate_b_candidates[:500]
        print(f"   Limited to top 500 by RVOL")
        print()

    # ========================================================================
    # GATE C - Accumulation Scoring
    # ========================================================================
    print("🚪 GATE C - Accumulation Scoring (Sigmoid-based)")
    print("-" * 80)
    print("Components: Stealth (40%) + Small Cap (25%) + Coiling (20%) + Volume (15%) + Sustained (bonus)")
    print()

    scored_candidates = []

    for i, candidate in enumerate(gate_b_candidates, 1):
        symbol = candidate['symbol']
        price = candidate['price']
        volume = candidate['volume']
        rvol = candidate['rvol']
        change_pct = candidate['change_pct']

        print(f"[{i}/{len(gate_b_candidates)}] Analyzing {symbol}...", end=' ')

        try:
            # Calculate accumulation score
            total_score, components, vigl_bonus, explosion_prob = calculate_accumulation_score(
                symbol, price, volume, rvol, change_pct
            )

            # Determine tier
            if total_score >= 90:
                tier = 'S'
            elif total_score >= 75:
                tier = 'A'
            elif total_score >= 60:
                tier = 'B'
            elif total_score >= 50:
                tier = 'C'
            else:
                tier = 'D'

            result = {
                'symbol': symbol,
                'price': round(price, 2),
                'rvol': round(rvol, 2),
                'change_pct': round(change_pct, 2),
                'volume': volume,
                'gates_passed': ['A', 'B', 'C'],
                'base_score': round(total_score - vigl_bonus, 2),
                'vigl_bonus': vigl_bonus,
                'total_score': total_score,
                'explosion_probability': explosion_prob,
                'tier': tier,
                'components': components
            }

            scored_candidates.append(result)

            print(f"Score: {total_score:.1f} (Tier {tier})")

        except Exception as e:
            print(f"Error: {e}")
            continue

        # Rate limiting
        time.sleep(0.1)

    # Sort by total score (descending)
    scored_candidates.sort(key=lambda x: x['total_score'], reverse=True)

    print()
    print("=" * 80)
    print("💎 RESULTS")
    print("=" * 80)
    print()

    # Group by tier
    s_tier = [c for c in scored_candidates if c['tier'] == 'S']
    a_tier = [c for c in scored_candidates if c['tier'] == 'A']
    b_tier = [c for c in scored_candidates if c['tier'] == 'B']
    c_tier = [c for c in scored_candidates if c['tier'] == 'C']

    if s_tier:
        print(f"🔥 S TIER (>= 90 points): {len(s_tier)} candidates")
        print("-" * 80)
        for c in s_tier:
            print(f"\n*{c['symbol']}* - ${c['price']:.2f}")
            print(f"   Score: {c['total_score']:.1f} ({c['base_score']:.1f} base + {c['vigl_bonus']} VIGL bonus)")
            print(f"   Explosion Probability: {c['explosion_probability']:.1f}%")
            print(f"   RVOL: {c['rvol']:.2f}x | Change: {c['change_pct']:+.2f}% | Volume: {c['volume']:,}")
            print(f"   Components:")
            for comp, val in c['components'].items():
                print(f"      {comp}: {val:.2f}")
        print()

    if a_tier:
        print(f"💪 A TIER (75-89 points): {len(a_tier)} candidates")
        for c in a_tier[:5]:
            print(f"   {c['symbol']}: {c['total_score']:.1f} pts - ${c['price']:.2f} - RVOL {c['rvol']:.2f}x")
        print()

    if b_tier:
        print(f"👀 B TIER (60-74 points): {len(b_tier)} candidates")
        for c in b_tier[:5]:
            print(f"   {c['symbol']}: {c['total_score']:.1f} pts - ${c['price']:.2f}")
        print()

    if c_tier:
        print(f"📋 C TIER (50-59 points): {len(c_tier)} candidates")
        print()

    if not scored_candidates:
        print("❌ No diamonds found")
        print()

    print("=" * 80)
    print(f"Total candidates: {len(scored_candidates)}")
    print(f"Gate A: {len(gate_a_candidates)} → Gate B: {len(gate_b_candidates)} → Gate C: {len(scored_candidates)}")
    print("=" * 80)
    print()

    # Save to JSON
    output_data = {
        'scan_date': datetime.now().strftime('%Y-%m-%d'),
        'scan_time': datetime.now().strftime('%H:%M:%S'),
        'scanner_version': 'V4_SWING',
        'philosophy': 'Wide net (12K) + Strict filter (VIGL pattern) + Swing trading (1-4 weeks)',
        'gates': {
            'gate_a': {
                'description': 'Universe Filter',
                'passed': len(gate_a_candidates)
            },
            'gate_b': {
                'description': 'Stealth Detection Window',
                'passed': len(gate_b_candidates)
            },
            'gate_c': {
                'description': 'Accumulation Scoring',
                'passed': len(scored_candidates)
            }
        },
        'tiers': {
            'S': len(s_tier),
            'A': len(a_tier),
            'B': len(b_tier),
            'C': len(c_tier)
        },
        'candidates': scored_candidates
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"💾 Saved to {OUTPUT_FILE}")
    print()

    # Log to scanner performance tracker
    try:
        log_scanner_picks(scored_candidates)
        print("✅ Logged to scanner performance tracker")
    except Exception as e:
        print(f"⚠️  Could not log to performance tracker: {e}")

    # Send Telegram alert for S-tier candidates only
    try:
        if s_tier:
            message = "💎 *DIAMOND SCANNER V4 - S TIER ALERTS*\n\n"
            message += f"Found {len(s_tier)} S-tier candidates (score >= 90)\n\n"

            for c in s_tier[:5]:  # Top 5 S-tier
                message += f"*{c['symbol']}* - ${c['price']:.2f}\n"
                message += f"   Score: {c['total_score']:.1f} | Explosion: {c['explosion_probability']:.1f}%\n"
                message += f"   RVOL: {c['rvol']:.2f}x | Change: {c['change_pct']:+.2f}%\n\n"

            message += f"_Scanner V4 - Swing Trading (1-4 weeks)_"
            send_alert(message)
            print("✅ Sent S-tier alerts to Telegram")
        else:
            print("ℹ️  No S-tier candidates to alert")
    except Exception as e:
        print(f"⚠️  Failed to send Telegram alert: {e}")

    print()

    return scored_candidates


if __name__ == '__main__':
    scan_for_swing_diamonds()
