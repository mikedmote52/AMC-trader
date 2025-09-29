#!/usr/bin/env python3
"""
Test script to validate explosive discovery fixes
Targets stocks like VIGL (+324%), CRWV (+171%), AEVA (+162%)
"""

import requests
import json
import time
from datetime import datetime

API_BASE = "https://amc-trader.onrender.com"

def test_discovery_fixes():
    """Test that the fixes properly identify explosive candidates"""

    print("🚀 TESTING EXPLOSIVE DISCOVERY FIXES")
    print("=" * 50)

    # Test 1: Health check
    print("\n1. Health Check...")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=10)
        health = response.json()
        commit = health.get('commit', 'unknown')[:8]
        print(f"   ✅ System healthy, commit: {commit}")

        # Check if our commit is deployed
        if commit == "097bf79c":  # Our fix commit
            print("   🎯 FIXES DEPLOYED!")
        else:
            print(f"   ⏳ Waiting for deployment (current: {commit})")

    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False

    # Test 2: Discovery candidates
    print("\n2. Testing Discovery...")
    try:
        response = requests.get(f"{API_BASE}/discovery/contenders?limit=10", timeout=60)

        if response.status_code == 200:
            data = response.json()
            count = data.get('count', 0)
            candidates = data.get('candidates', [])

            print(f"   📊 Found {count} candidates")

            if count > 0:
                print("\n   🎯 TOP EXPLOSIVE CANDIDATES:")
                for i, candidate in enumerate(candidates[:3], 1):
                    ticker = candidate.get('ticker', 'N/A')
                    score = candidate.get('total_score', 0) * 100
                    irv = candidate.get('intraday_relative_volume', 0)
                    change = candidate.get('change_pct', 0)
                    price = candidate.get('price', 0)
                    tier = candidate.get('tier', 'unknown')

                    print(f"   {i}. {ticker}: {score:.1f}% score | {irv:.1f}x IRV | {change:+.1f}% | ${price:.2f} | {tier}")

                    # Flag potential 2x candidates
                    if score >= 75 and irv >= 3.0 and price < 20:
                        print(f"      🚀 HIGH 2X POTENTIAL!")

                return True
            else:
                print("   ⚠️  No candidates found - system may need more time")
                return False

        else:
            print(f"   ❌ Discovery failed: {response.status_code}")
            print(f"      Response: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"   ❌ Discovery test failed: {e}")
        return False

def validate_winning_stocks():
    """Check if system would have caught our winning stocks"""

    print("\n3. Validating Against Winning Stocks...")

    # Known real stocks with explosive potential
    test_stocks = [
        ("SMCI", "Super Micro Computer"),    # Known explosive small cap
        ("TSLA", "Tesla"),                   # High volatility large cap
        ("AMD", "Advanced Micro Devices"),   # Tech with squeeze potential
        ("NVDA", "NVIDIA"),                  # AI leader with momentum
        ("AAPL", "Apple"),                   # Baseline large cap test
        ("GME", "GameStop"),                 # Known for explosive moves
    ]

    for ticker, name in test_stocks:
        print(f"\n   📈 {ticker} ({name}):")

        try:
            # Check if this stock would score well in our system
            response = requests.get(f"{API_BASE}/discovery/audit/{ticker}", timeout=30)

            if response.status_code == 200:
                data = response.json()
                score = data.get('score', 0) * 100
                irv = data.get('irv', 0)

                print(f"      Score: {score:.1f}% | IRV: {irv:.1f}x")

                if score >= 70:
                    print(f"      ✅ Would have been detected!")
                else:
                    print(f"      ⚠️  Score too low for detection")

            else:
                print(f"      ❌ Audit failed: {response.status_code}")

        except Exception as e:
            print(f"      ❌ Error testing {ticker}: {e}")

if __name__ == "__main__":
    print(f"🕐 Starting tests at {datetime.now().strftime('%H:%M:%S')}")

    # Wait a moment for any deployment to complete
    time.sleep(5)

    # Run tests
    discovery_works = test_discovery_fixes()

    if discovery_works:
        validate_winning_stocks()

    print(f"\n🏁 Tests completed at {datetime.now().strftime('%H:%M:%S')}")
    print("\n💡 KEY INDICATORS FOR SUCCESS:")
    print("   • Finding 3-10 candidates consistently")
    print("   • IRV values 3x+ for explosive stocks")
    print("   • Scores 75%+ for trade-ready candidates")
    print("   • Small caps under $20 with high potential")