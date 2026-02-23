#!/usr/bin/env python3
"""
Test script for alpha calculation functionality

Tests the get_spy_return function with known dates to verify it works correctly.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from scanner_performance_tracker import get_spy_return

def test_spy_return():
    """Test SPY return calculation with various date ranges"""

    print("Testing Alpha Calculation Functionality\n")
    print("=" * 60)

    # Test case 1: Recent date range (1 week)
    print("\nTest 1: Recent 1-week period")
    start = "2026-02-10"
    end = "2026-02-17"
    spy_return = get_spy_return(start, end)

    if spy_return is not None:
        print(f"✅ SPY return from {start} to {end}: {spy_return:+.2f}%")
    else:
        print(f"❌ Failed to get SPY data for {start} to {end}")

    # Test case 2: Longer period (1 month)
    print("\nTest 2: 1-month period")
    start = "2026-01-15"
    end = "2026-02-15"
    spy_return = get_spy_return(start, end)

    if spy_return is not None:
        print(f"✅ SPY return from {start} to {end}: {spy_return:+.2f}%")
    else:
        print(f"❌ Failed to get SPY data for {start} to {end}")

    # Test case 3: Single day (edge case)
    print("\nTest 3: Single day (edge case)")
    start = "2026-02-18"
    end = "2026-02-18"
    spy_return = get_spy_return(start, end)

    if spy_return is not None:
        print(f"✅ SPY return from {start} to {end}: {spy_return:+.2f}%")
        print("   (Should be ~0% for same day)")
    else:
        print(f"❌ Failed to get SPY data for {start} to {end}")

    # Test case 4: Example alpha calculation
    print("\n" + "=" * 60)
    print("Example Alpha Calculation:")
    print("=" * 60)

    stock_return = 15.0
    start = "2026-02-10"
    end = "2026-02-15"
    spy_return = get_spy_return(start, end)

    if spy_return is not None:
        alpha = stock_return - spy_return
        print(f"Stock Return: {stock_return:+.1f}%")
        print(f"SPY Return:   {spy_return:+.1f}%")
        print(f"Alpha:        {alpha:+.1f}%")

        if alpha > 0:
            print(f"\n✅ Positive alpha! Strategy outperformed market by {alpha:.1f}%")
        else:
            print(f"\n⚠️  Negative alpha. Strategy underperformed market by {abs(alpha):.1f}%")
    else:
        print("❌ Could not calculate alpha (SPY data unavailable)")

    print("\n" + "=" * 60)
    print("Testing Complete!")

if __name__ == '__main__':
    test_spy_return()
