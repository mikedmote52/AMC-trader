#!/usr/bin/env python3
"""
Test why AlphaStack v2 is giving 0 scores
"""

import sys
import os
sys.path.insert(0, 'src')

from scoring.alphastack_v2 import score_ticker

# Test with real-ish data for a cannabis stock
test_features = {
    'ticker': 'TLRY',
    'price': 1.57,
    'rel_vol_now': 10.5,  # High volume
    'rel_vol_5d': [8.0, 9.0, 10.0, 11.0, 10.5],
    'consecutive_up_days': 3,
    'daily_change_pct': 36.8,  # Big move
    'rsi': 75,  # Overbought
    'atr_pct': 0.15,  # High volatility
    'vwap': 1.50,
    'ema9': 1.48,
    'ema20': 1.45,
    'float_shares': 700000000,  # Large float
    'short_interest': 0.08,  # Low short interest
    'utilization': 0.6,
    'borrow_fee_pct': 0.3,
    'options_call_oi': 5000,
    'options_put_oi': 3000,
    'iv_percentile': 85,
    'catalyst_detected': True,
    'social_rank': 30
}

print("Testing AlphaStack v2 scoring...")
print(f"Input features for {test_features['ticker']}:")
print(f"  Price: ${test_features['price']}")
print(f"  Volume: {test_features['rel_vol_now']}x")
print(f"  Change: {test_features['daily_change_pct']}%")
print(f"  Consecutive ups: {test_features['consecutive_up_days']}")

try:
    result = score_ticker(test_features)
    print("\nScoring result:")
    print(f"  Regime: {result['regime']}")
    print(f"  Composite: {result['composite']}/100")
    print(f"  Action: {result['action']}")
    print(f"  Scores breakdown:")
    for component, score in result['scores'].items():
        print(f"    {component}: {score}")
    print(f"  Entry plan: {result['entry_plan']}")

    # Convert to 0-1 scale
    normalized = result['composite'] / 100.0
    print(f"\n✅ Normalized score (0-1 scale): {normalized:.3f}")

except Exception as e:
    print(f"\n❌ Error during scoring: {e}")
    import traceback
    traceback.print_exc()

# Test with minimal features (what discovery might actually send)
print("\n" + "="*50)
print("Testing with minimal features...")
minimal_features = {
    'ticker': 'AMC',
    'price': 4.35,
    'rel_vol_now': 3.5,
    'rel_vol_5d': [3.5] * 5,
    'consecutive_up_days': 1,
    'daily_change_pct': 5.2,
    'rsi': 65,
    'atr_pct': 0.05,
    'vwap': 4.30,
    'ema9': 4.28,
    'ema20': 4.25,
    'float_shares': 50000000,
    'short_interest': 0.15,
    'utilization': 0.8,
    'borrow_fee_pct': 0.5,
    'options_call_oi': 1000,
    'options_put_oi': 800,
    'iv_percentile': 50,
    'catalyst_detected': False,
    'social_rank': 10
}

try:
    result = score_ticker(minimal_features)
    print(f"{minimal_features['ticker']} scoring:")
    print(f"  Composite: {result['composite']}/100 = {result['composite']/100.0:.3f}")
    print(f"  Action: {result['action']}")
except Exception as e:
    print(f"❌ Error: {e}")