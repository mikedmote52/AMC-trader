#!/usr/bin/env python3
"""
Live test of hybrid_v1 gates with relaxed settings
Shows impact of observability enhancements
"""

import sys
import json
from datetime import datetime

print("\n=== HYBRID V1 GATE TESTING - THURSDAY 10:30 AM ===\n")

# Load configuration
with open('calibration/active.json', 'r') as f:
    config = json.load(f)

thresholds = config['scoring']['hybrid_v1']['thresholds']

# Simulate typical Thursday morning candidates
test_candidates = [
    {
        "symbol": "AAPL",
        "relvol_30": 1.8,  # Below old threshold (2.5) but near new (2.0)
        "atr_pct": 0.032,  # Below old (0.04) but near new (0.035)
        "vwap": 180,
        "price": 179,      # Within 1% of VWAP
        "float_shares": 15_000_000_000,  # Large cap
        "has_news_catalyst": True
    },
    {
        "symbol": "QUBT", 
        "relvol_30": 2.2,  # Passes new threshold
        "atr_pct": 0.038,  # Passes new threshold
        "vwap": 5.0,
        "price": 4.97,     # Within 1% of VWAP
        "float_shares": 90_000_000,  # Mid-float range
        "short_interest": 0.13,
        "has_news_catalyst": True
    },
    {
        "symbol": "SOUN",
        "relvol_30": 1.95, # Just below 2.0 (soft-pass candidate)
        "atr_pct": 0.045,  # Good ATR
        "vwap": 8.5,
        "price": 8.48,
        "float_shares": 45_000_000,  # Small float
        "social_rank": 0.90,  # High social buzz
        "has_news_catalyst": True
    }
]

print("Test Candidates Analysis:")
print("-" * 60)

for candidate in test_candidates:
    symbol = candidate["symbol"]
    print(f"\n{symbol}:")
    
    # Check against OLD thresholds (2.5 relvol, 0.04 ATR, VWAP required)
    old_pass = (
        candidate.get("relvol_30", 0) >= 2.5 and
        candidate.get("atr_pct", 0) >= 0.04 and
        candidate.get("price", 0) > candidate.get("vwap", 0)
    )
    
    # Check against NEW relaxed thresholds
    new_relvol_ok = candidate.get("relvol_30", 0) >= thresholds["min_relvol_30"]
    new_atr_ok = candidate.get("atr_pct", 0) >= thresholds["min_atr_pct"]
    
    # VWAP proximity check
    vwap_prox = thresholds["vwap_proximity_pct"]
    price = candidate.get("price", 0)
    vwap = candidate.get("vwap", 0)
    vwap_ok = price > vwap or (vwap > 0 and price >= vwap * (1 - vwap_prox/100))
    
    # Mid-float path check
    float_shares = candidate.get("float_shares", 0)
    mid_float_ok = False
    if thresholds["mid_float_path"]["enabled"]:
        if 75_000_000 <= float_shares <= 150_000_000:
            if candidate.get("short_interest", 0) >= 0.12 and candidate.get("has_news_catalyst"):
                mid_float_ok = True
    
    # Soft-pass check
    soft_pass_eligible = False
    if thresholds["max_soft_pass"] > 0:
        near_relvol = candidate.get("relvol_30", 0) >= thresholds["min_relvol_30"] * 0.9
        near_atr = candidate.get("atr_pct", 0) >= thresholds["min_atr_pct"] * 0.9
        catalyst = candidate.get("has_news_catalyst") or candidate.get("social_rank", 0) >= 0.85
        if (near_relvol or near_atr) and catalyst:
            soft_pass_eligible = True
    
    print(f"  RelVol: {candidate.get('relvol_30'):.1f} (need {thresholds['min_relvol_30']}) - {'✓' if new_relvol_ok else '✗'}")
    print(f"  ATR: {candidate.get('atr_pct'):.3f} (need {thresholds['min_atr_pct']}) - {'✓' if new_atr_ok else '✗'}")
    print(f"  VWAP: ${price:.2f} vs ${vwap:.2f} - {'✓ proximity' if vwap_ok and price <= vwap else '✓' if vwap_ok else '✗'}")
    
    if mid_float_ok:
        print(f"  Float: {float_shares/1e6:.0f}M - ✓ mid-float path")
    elif float_shares <= 75_000_000:
        print(f"  Float: {float_shares/1e6:.0f}M - ✓ small float")
    else:
        print(f"  Float: {float_shares/1e6:.0f}M - ✗")
    
    # Result
    if old_pass:
        result = "PASS (even with old gates)"
    elif new_relvol_ok and new_atr_ok and vwap_ok:
        result = "✅ PASS (new relaxed gates)"
    elif mid_float_ok and vwap_ok:
        result = "✅ PASS (mid-float path)"
    elif soft_pass_eligible and vwap_ok:
        result = "✅ SOFT PASS (catalyst + near miss)"
    else:
        failures = []
        if not new_relvol_ok: failures.append("relvol")
        if not new_atr_ok: failures.append("atr")
        if not vwap_ok: failures.append("vwap")
        result = f"❌ FAIL ({', '.join(failures)})"
    
    print(f"  Result: {result}")

print("\n" + "=" * 60)
print("\n📊 Summary of Enhancements:\n")
print("1. VWAP Proximity (1%): Allows stocks within 1% of VWAP")
print("2. Relaxed Thresholds: RelVol 2.0 (was 2.5), ATR 3.5% (was 4%)")
print("3. Mid-Float Path: Enabled for 75-150M float stocks with catalysts")
print("4. Soft-Pass: Up to 10 near-misses with strong catalysts")
print("\n✨ Result: More nuanced filtering without compromising quality")
print("          Enhanced observability shows exactly why stocks fail")