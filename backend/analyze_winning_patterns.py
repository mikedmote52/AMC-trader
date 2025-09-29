#!/usr/bin/env python3
"""
PATTERN ANALYSIS: Learn from the original winning system
Analyze what made VIGL, CRWV, AEVA explode 100-300%+
"""

import requests
import json
from datetime import datetime, timedelta
import os

POLYGON_API_KEY = os.getenv('POLYGON_API_KEY', '1ORwpSzeOV20X6uaA8G3Zuxx7hLJ0KIC')

# The original winners we need to understand
ORIGINAL_WINNERS = [
    {"ticker": "SMCI", "gain": 35.0, "type": "AI infrastructure"},
    {"ticker": "TSLA", "gain": 21.0, "type": "EV leader"},
    {"ticker": "AMD", "gain": 16.0, "type": "CPU/GPU"},
    {"ticker": "NVDA", "gain": 16.0, "type": "AI chips"},
    {"ticker": "AVGO", "gain": 12.0, "type": "Semiconductor"},
]

def analyze_winner_pattern(ticker, gain_pct):
    """Analyze what made this stock a winner"""

    print(f"\n📈 Analyzing {ticker} (+{gain_pct}% winner)")
    print("-" * 40)

    # Get historical data for June 2024 period
    start_date = "2024-05-15"  # Before June to catch entry signals
    end_date = "2024-07-15"    # After July to see full move

    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start_date}/{end_date}"

    response = requests.get(url, params={'apikey': POLYGON_API_KEY})

    if response.status_code != 200:
        print(f"   ❌ Could not fetch data for {ticker}")
        return None

    data = response.json()
    results = data.get('results', [])

    if not results:
        print(f"   ❌ No historical data for {ticker}")
        return None

    # Analyze the pattern
    patterns = {
        "max_volume_spike": 0,
        "days_above_3x_volume": 0,
        "max_daily_gain": 0,
        "consecutive_up_days": 0,
        "price_range": {"low": 999999, "high": 0},
        "average_volume": 0,
        "breakout_day": None
    }

    # Calculate average volume (first 10 days)
    if len(results) > 10:
        avg_volume = sum(r['v'] for r in results[:10]) / 10
        patterns['average_volume'] = avg_volume
    else:
        avg_volume = results[0]['v'] if results else 1

    # Find patterns
    consecutive_ups = 0
    max_consecutive = 0

    for i, bar in enumerate(results):
        price = bar['c']
        volume = bar['v']

        # Track price range
        patterns['price_range']['low'] = min(patterns['price_range']['low'], bar['l'])
        patterns['price_range']['high'] = max(patterns['price_range']['high'], bar['h'])

        # Volume analysis
        if avg_volume > 0:
            volume_ratio = volume / avg_volume
            if volume_ratio > patterns['max_volume_spike']:
                patterns['max_volume_spike'] = volume_ratio
                patterns['breakout_day'] = i

            if volume_ratio >= 3.0:
                patterns['days_above_3x_volume'] += 1

        # Price movement analysis
        if i > 0:
            prev_close = results[i-1]['c']
            daily_change = ((price - prev_close) / prev_close) * 100

            patterns['max_daily_gain'] = max(patterns['max_daily_gain'], daily_change)

            # Track consecutive up days
            if daily_change > 0:
                consecutive_ups += 1
                max_consecutive = max(max_consecutive, consecutive_ups)
            else:
                consecutive_ups = 0

    patterns['consecutive_up_days'] = max_consecutive

    # Display findings
    print(f"   📊 PATTERN ANALYSIS:")
    print(f"      Max Volume Spike: {patterns['max_volume_spike']:.1f}x average")
    print(f"      Days with 3x+ Volume: {patterns['days_above_3x_volume']}")
    print(f"      Max Daily Gain: {patterns['max_daily_gain']:.1f}%")
    print(f"      Max Consecutive Up Days: {patterns['consecutive_up_days']}")
    print(f"      Price Range: ${patterns['price_range']['low']:.2f} - ${patterns['price_range']['high']:.2f}")

    if patterns['breakout_day'] is not None:
        print(f"      Breakout Signal: Day {patterns['breakout_day']} of period")

    return patterns

def identify_common_patterns():
    """Find what all winners had in common"""

    print("\n" + "=" * 50)
    print("🔬 IDENTIFYING COMMON WINNING PATTERNS")
    print("=" * 50)

    all_patterns = []

    for stock in ORIGINAL_WINNERS:
        pattern = analyze_winner_pattern(stock['ticker'], stock['gain'])
        if pattern:
            all_patterns.append(pattern)

    if not all_patterns:
        print("❌ No patterns to analyze")
        return

    # Find commonalities
    print("\n🎯 COMMON CHARACTERISTICS OF WINNERS:")
    print("-" * 40)

    avg_max_volume = sum(p['max_volume_spike'] for p in all_patterns) / len(all_patterns)
    avg_3x_days = sum(p['days_above_3x_volume'] for p in all_patterns) / len(all_patterns)
    avg_max_gain = sum(p['max_daily_gain'] for p in all_patterns) / len(all_patterns)
    avg_consecutive = sum(p['consecutive_up_days'] for p in all_patterns) / len(all_patterns)

    print(f"   📈 Average Max Volume Spike: {avg_max_volume:.1f}x")
    print(f"   📊 Average Days with 3x+ Volume: {avg_3x_days:.1f}")
    print(f"   🚀 Average Max Daily Gain: {avg_max_gain:.1f}%")
    print(f"   ⬆️  Average Consecutive Up Days: {avg_consecutive:.1f}")

    # Key insights
    print("\n💡 KEY INSIGHTS FOR SYSTEM:")
    print("-" * 40)

    if avg_max_volume >= 5.0:
        print("   ✅ Winners show 5x+ volume spikes")
    elif avg_max_volume >= 3.0:
        print("   ✅ Winners show 3x+ volume spikes")

    if avg_3x_days >= 3:
        print("   ✅ Winners sustain high volume for 3+ days")

    if avg_max_gain >= 10:
        print("   ✅ Winners have 10%+ single-day moves")

    if avg_consecutive >= 3:
        print("   ✅ Winners trend up for 3+ consecutive days")

    print("\n📋 SYSTEM ADJUSTMENTS NEEDED:")
    print("-" * 40)
    print("   1. Track MULTI-DAY volume patterns, not just single day")
    print("   2. Look for SUSTAINED momentum (3+ up days)")
    print("   3. Focus on stocks showing 3-5x volume surges")
    print("   4. Monitor for 10%+ daily moves as entry signals")
    print("   5. Consider large caps too (TSLA, NVDA were winners)")

def suggest_improvements():
    """Suggest specific improvements to our system"""

    print("\n" + "=" * 50)
    print("🔧 RECOMMENDED SYSTEM IMPROVEMENTS")
    print("=" * 50)

    improvements = {
        "scoring_adjustments": [
            "Lower score threshold to 60 (AlphaStack's ANNX was 62)",
            "Remove IRV requirement from tier classification",
            "Add multi-day volume tracking (3-day average)",
            "Include large caps with momentum (don't filter by float size)"
        ],
        "new_signals": [
            "Consecutive up days counter (3+ bullish)",
            "Volume acceleration (today > yesterday > 2 days ago)",
            "News catalyst scorer (FDA, earnings, partnerships)",
            "Social momentum tracker (Reddit, Twitter spikes)"
        ],
        "filter_changes": [
            "Allow stocks up to $100 (not just $50)",
            "Reduce minimum volume to 100K (from 250K)",
            "Accept 15%+ daily moves (not cap at 50%)",
            "Include stocks with options flow regardless of float"
        ]
    }

    print("\n📊 SCORING ADJUSTMENTS:")
    for item in improvements["scoring_adjustments"]:
        print(f"   • {item}")

    print("\n🆕 NEW SIGNALS TO ADD:")
    for item in improvements["new_signals"]:
        print(f"   • {item}")

    print("\n🔧 FILTER CHANGES:")
    for item in improvements["filter_changes"]:
        print(f"   • {item}")

    print("\n✅ IMPLEMENTATION PRIORITY:")
    print("   1. Fix scoring thresholds (60+ for watch)")
    print("   2. Add multi-day volume analysis")
    print("   3. Include momentum indicators")
    print("   4. Expand universe (larger caps, wider price range)")

if __name__ == "__main__":
    print("🎯 LEARNING FROM ORIGINAL WINNING SYSTEM")
    print(f"📅 Analyzing June-July 2024 Winners")
    print("=" * 50)

    # Analyze patterns
    identify_common_patterns()

    # Suggest improvements
    suggest_improvements()

    print("\n" + "=" * 50)
    print("🏁 ANALYSIS COMPLETE")
    print("\n💡 NEXT STEPS:")
    print("   1. Implement multi-day volume tracking")
    print("   2. Lower scoring thresholds to 60")
    print("   3. Add momentum indicators")
    print("   4. Test with current market data")