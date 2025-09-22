#!/usr/bin/env python3
"""
Debug script to examine the actual price data from the Polygon API
to understand why 99.9% of stocks are being filtered as "price_too_low"
"""
import asyncio
import logging
import os
import sys
from pathlib import Path
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Set environment
os.environ['POLYGON_API_KEY'] = '1ORwpSzeOV20X6uaA8G3Zuxx7hLJ0KIC'
os.environ['REDIS_URL'] = 'redis://localhost:6379'

# Add backend path
backend_path = Path(__file__).parent / "backend" / "src"
sys.path.insert(0, str(backend_path))

async def examine_price_data():
    """Examine actual price data from Polygon API"""
    print("🔍 Examining Price Data from Polygon API")
    print("=" * 40)

    try:
        from discovery.unified_discovery import UnifiedDiscoverySystem
        discovery = UnifiedDiscoverySystem()

        # Get a small sample of the universe
        universe = await discovery.get_market_universe()
        print(f"📊 Total universe size: {len(universe)}")

        # Examine first 10 stocks in detail
        print("\n📋 Sample Stock Data Analysis:")
        print("=" * 35)

        for i, ticker_data in enumerate(universe[:10]):
            symbol = ticker_data.get('ticker', 'N/A')

            # Extract price data the same way the filter does
            price = ticker_data.get('day', {}).get('c', 0)
            daily_change_pct = ticker_data.get('todaysChangePerc', 0)
            volume = ticker_data.get('day', {}).get('v', 0)
            prev_volume = ticker_data.get('prevDay', {}).get('v', 1)

            # Show the raw data structure for the first few
            if i < 3:
                print(f"\n📈 {symbol} - RAW DATA:")
                print(json.dumps(ticker_data, indent=2)[:500] + "...")

            print(f"\n📈 {symbol}:")
            print(f"  💰 Price: ${price}")
            print(f"  📊 Change: {daily_change_pct:.2f}%")
            print(f"  📦 Volume: {volume:,}")
            print(f"  📦 Prev Volume: {prev_volume:,}")
            print(f"  📏 Volume Ratio: {volume/max(prev_volume, 1):.2f}x")

            # Check filter results
            filter_result = "✅ PASS"
            reasons = []

            if abs(daily_change_pct) > 20.0:
                reasons.append(f"post-explosion ({daily_change_pct:.1f}%)")
            if price > 50.00:
                reasons.append(f"price too high (${price:.2f})")
            if price < 0.50:
                reasons.append(f"price too low (${price:.2f})")
            if volume/max(prev_volume, 1) < 2.0:
                reasons.append(f"low volume ({volume/max(prev_volume, 1):.2f}x)")
            if volume/max(prev_volume, 1) > 15.0:
                reasons.append(f"volume explosion ({volume/max(prev_volume, 1):.2f}x)")

            if reasons:
                filter_result = "❌ FILTERED: " + ", ".join(reasons)

            print(f"  🔍 Filter: {filter_result}")

        # Check for data structure issues
        print("\n🔧 Data Structure Analysis:")
        print("=" * 30)

        # Count how many have valid price data
        valid_prices = 0
        zero_prices = 0
        missing_day_data = 0

        for ticker_data in universe[:100]:  # Check first 100
            if 'day' not in ticker_data:
                missing_day_data += 1
                continue

            price = ticker_data.get('day', {}).get('c', 0)
            if price > 0:
                valid_prices += 1
            else:
                zero_prices += 1

        print(f"📊 Valid prices (>$0): {valid_prices}/100")
        print(f"📊 Zero prices: {zero_prices}/100")
        print(f"📊 Missing 'day' data: {missing_day_data}/100")

        if zero_prices > 80:
            print("❌ CRITICAL: Most stocks have zero prices - API data structure issue!")
        elif valid_prices > 80:
            print("✅ Good: Most stocks have valid price data")
        else:
            print("⚠️  Mixed: Some data quality issues detected")

    except Exception as e:
        print(f"❌ Failed to examine price data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(examine_price_data())