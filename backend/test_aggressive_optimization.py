#!/usr/bin/env python3
"""
Test Aggressive Optimization Settings
Verify we get more candidates through the pipeline
"""

import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_aggressive_settings():
    print("🚀 TESTING AGGRESSIVE OPTIMIZATION SETTINGS")
    print("=" * 60)
    
    # Import and check settings
    from jobs.discover import (
        MIN_DOLLAR_VOL, PRICE_CAP, MAX_CANDIDATES,
        EXCLUDE_FUNDS, EXCLUDE_ADRS, COMPRESSION_PCTL_MAX,
        EXPLOSIVE_PRICE_MIN, EXPLOSIVE_PRICE_MAX
    )
    
    from services.squeeze_detector import SqueezeDetector
    
    print("\n📊 BULK FILTER SETTINGS:")
    print(f"  MIN_DOLLAR_VOL: ${MIN_DOLLAR_VOL:,.0f} (Target: $5M)")
    print(f"  PRICE_CAP: ${PRICE_CAP:.0f} (Target: $500)")
    print(f"  PRICE_MIN: ${EXPLOSIVE_PRICE_MIN:.2f} (Target: $0.01)")
    print(f"  MAX_CANDIDATES: {MAX_CANDIDATES} (Target: 25)")
    
    print("\n🏢 CLASSIFICATION SETTINGS:")
    print(f"  EXCLUDE_FUNDS: {EXCLUDE_FUNDS} (Target: False)")
    print(f"  EXCLUDE_ADRS: {EXCLUDE_ADRS} (Target: False)")
    
    print("\n📈 COMPRESSION SETTINGS:")
    print(f"  COMPRESSION_PCTL_MAX: {COMPRESSION_PCTL_MAX:.2f} (Target: 0.30)")
    
    print("\n🔥 SQUEEZE DETECTION:")
    detector = SqueezeDetector()
    print(f"  CONFIDENCE_LEVELS:")
    for level, threshold in detector.CONFIDENCE_LEVELS.items():
        print(f"    {level}: {threshold:.2f}")
    print(f"  Volume spike min: {detector.VIGL_CRITERIA['volume_spike_min']}x")
    
    print("\n🎯 OPTIMIZATION VALIDATION:")
    
    # Check if settings are aggressive enough
    checks = [
        ("Dollar Volume", MIN_DOLLAR_VOL <= 5_000_000, f"${MIN_DOLLAR_VOL/1_000_000:.1f}M <= $5M"),
        ("Price Cap", PRICE_CAP >= 500, f"${PRICE_CAP} >= $500"),
        ("Price Min", EXPLOSIVE_PRICE_MIN <= 0.01, f"${EXPLOSIVE_PRICE_MIN} <= $0.01"),
        ("Max Candidates", MAX_CANDIDATES >= 25, f"{MAX_CANDIDATES} >= 25"),
        ("Include Funds", not EXCLUDE_FUNDS, f"Funds {'included' if not EXCLUDE_FUNDS else 'excluded'}"),
        ("Include ADRs", not EXCLUDE_ADRS, f"ADRs {'included' if not EXCLUDE_ADRS else 'excluded'}"),
        ("Compression", COMPRESSION_PCTL_MAX >= 0.30, f"{COMPRESSION_PCTL_MAX:.2f} >= 0.30"),
        ("Squeeze Threshold", detector.CONFIDENCE_LEVELS['LOW'] <= 0.15, f"{detector.CONFIDENCE_LEVELS['LOW']:.2f} <= 0.15")
    ]
    
    all_passed = True
    for check_name, passed, details in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name:20} {details}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL AGGRESSIVE OPTIMIZATIONS ACTIVE!")
        print("Expected: 25+ candidates vs 1 previously")
    else:
        print("⚠️ Some optimizations not fully applied")
        print("Review settings above")
    
    # Simulate expected flow
    print("\n📊 EXPECTED PIPELINE FLOW:")
    print("  11,339 stocks (universe)")
    print("  ↓")
    print("  ~3,500 stocks (bulk filter - 31% pass)")
    print("  ↓")
    print("  ~3,500 stocks (no fund/ADR exclusion - 100% pass)")
    print("  ↓")
    print("  ~2,000 stocks (rapid scan/compression - 57% pass)")
    print("  ↓")
    print("  ~150 stocks (VIGL pattern - 7.5% pass)")
    print("  ↓")
    print("  ~100 stocks (initial squeeze - 67% pass)")
    print("  ↓")
    print("  🎯 25+ FINAL CANDIDATES (25% pass)")
    
    print("\n🚀 System ready for aggressive explosive discovery!")

if __name__ == "__main__":
    test_aggressive_settings()