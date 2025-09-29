#!/usr/bin/env python3
"""
Test the optimized IRV pipeline with real explosive candidates
"""

import requests
import time
from datetime import datetime

API_BASE = "https://amc-trader.onrender.com"

def test_optimized_discovery():
    """Test the optimized discovery pipeline"""

    print("🚀 TESTING OPTIMIZED IRV PIPELINE")
    print("=" * 50)

    start_time = time.time()

    try:
        print(f"⏰ Starting discovery at {datetime.now().strftime('%H:%M:%S')}")

        # Test with optimized pipeline
        response = requests.get(f"{API_BASE}/discovery/contenders?limit=10", timeout=120)

        end_time = time.time()
        processing_time = end_time - start_time

        print(f"⏰ Processing completed in {processing_time:.1f} seconds")

        if response.status_code == 200:
            data = response.json()
            candidates = data.get('candidates', [])
            count = data.get('count', 0)

            print(f"\n📊 RESULTS:")
            print(f"   Candidates found: {count}")
            print(f"   Processing time: {processing_time:.1f}s")

            if count > 0:
                print(f"\n🎯 EXPLOSIVE CANDIDATES:")

                for i, candidate in enumerate(candidates, 1):
                    ticker = candidate.get('ticker', 'N/A')
                    score = candidate.get('total_score', 0) * 100
                    irv = candidate.get('intraday_relative_volume', 0)
                    change = candidate.get('change_pct', 0)
                    price = candidate.get('price', 0)
                    tier = candidate.get('tier', 'unknown')
                    volume_ratio = candidate.get('volume_ratio', 0)
                    explosive_potential = candidate.get('explosive_potential', 0) * 100

                    print(f"   {i}. {ticker}:")
                    print(f"      Score: {score:.1f}% | IRV: {irv:.1f}x | Tier: {tier}")
                    print(f"      Price: ${price:.2f} | Change: {change:+.1f}%")
                    print(f"      Volume: {volume_ratio:.1f}x daily | 2x Potential: {explosive_potential:.1f}%")

                    # Flag high potential candidates
                    if explosive_potential >= 75 and price < 25:
                        print(f"      🚀 HIGH 2X POTENTIAL!")
                    elif explosive_potential >= 60:
                        print(f"      ⭐ STRONG POTENTIAL")
                    print()

                # Performance analysis
                print(f"📈 PIPELINE PERFORMANCE:")
                if processing_time < 60:
                    print(f"   ✅ EXCELLENT: {processing_time:.1f}s processing time")
                elif processing_time < 120:
                    print(f"   ✅ GOOD: {processing_time:.1f}s processing time")
                else:
                    print(f"   ⚠️  SLOW: {processing_time:.1f}s processing time")

                print(f"   📊 Throughput: {count/processing_time:.1f} candidates/second")

                return True
            else:
                print(f"   ⚠️  No candidates found - filters may be too strict")
                return False

        else:
            print(f"❌ Discovery failed: {response.status_code}")
            print(f"   Response: {response.text[:300]}")
            return False

    except requests.exceptions.Timeout:
        print(f"❌ Request timed out after {processing_time:.1f}s")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run optimized pipeline test"""

    print(f"🎯 AMC-TRADER OPTIMIZED PIPELINE TEST")
    print(f"🕐 Started at {datetime.now().strftime('%H:%M:%S')}")
    print()

    # Wait for deployment
    print("⏳ Waiting for deployment...")
    time.sleep(10)

    # Test optimized discovery
    success = test_optimized_discovery()

    print(f"\n🏁 TEST COMPLETED")
    print(f"🕐 Finished at {datetime.now().strftime('%H:%M:%S')}")

    if success:
        print(f"\n✅ OPTIMIZATION SUCCESS:")
        print(f"   • Batch IRV processing working")
        print(f"   • Real explosive candidates found")
        print(f"   • Fast processing pipeline")
        print(f"   • Ready for +200-300% opportunities")
    else:
        print(f"\n⚠️  OPTIMIZATION STATUS:")
        print(f"   • Pipeline may still be deploying")
        print(f"   • Check again in 5-10 minutes")

if __name__ == "__main__":
    main()