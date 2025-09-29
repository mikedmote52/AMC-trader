#!/usr/bin/env python3
"""
Debug filter performance to see where each stock gets filtered out
"""

import asyncio
import sys
import httpx
import os
from typing import Dict, List, Any

sys.path.append('backend/src')

class FilterPerformanceDebugger:
    def __init__(self):
        self.api_key = os.getenv('POLYGON_API_KEY', '1ORwpSzeOV20X6uaA8G3Zuxx7hLJ0KIC')
        self.filter_stats = {
            'total_input': 0,
            'ticker_format': 0,
            'no_trading_data': 0,
            'price_filter': 0,
            'volume_filter': 0,
            'volume_ratio_filter': 0,
            'daily_change_null': 0,
            'daily_change_range': 0,
            'passed_pre_filter': 0,
            'enrichment_failed': 0,
            'scoring_failed': 0,
            'invalid_score': 0,
            'no_tier_match': 0,
            'elite_tier': 0,
            'near_miss_tier': 0
        }

    async def debug_full_pipeline(self):
        """Debug the complete filter pipeline with real data"""
        print("🔍 FILTER PERFORMANCE DEBUG")
        print("="*50)

        try:
            # Get raw market data
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = "https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers"
                response = await client.get(url, params={'apikey': self.api_key})

                if response.status_code != 200:
                    print(f"❌ API failed: {response.status_code}")
                    return

                data = response.json()
                raw_stocks = data.get('tickers', [])
                self.filter_stats['total_input'] = len(raw_stocks)

                print(f"📥 Raw input: {len(raw_stocks)} stocks")

            # Apply each filter and track performance
            filtered_stocks = []

            for stock in raw_stocks:
                ticker = stock.get('ticker', '')

                # Filter 1: Ticker format
                if not ticker or len(ticker) > 5 or any(char in ticker for char in ['.', '-']) or ticker.endswith('W'):
                    self.filter_stats['ticker_format'] += 1
                    continue

                # Filter 2: Trading data
                day_data = stock.get('day', {})
                if not day_data:
                    self.filter_stats['no_trading_data'] += 1
                    continue

                price = day_data.get('c', 0)
                volume = day_data.get('v', 0)

                # Filter 3: Price range
                if not (0.50 <= price <= 100.0):
                    self.filter_stats['price_filter'] += 1
                    continue

                # Filter 4: Volume minimum
                if volume < 500000:
                    self.filter_stats['volume_filter'] += 1
                    continue

                # Filter 5: Volume ratio
                prev_day_data = stock.get('prevDay', {})
                prev_volume = prev_day_data.get('v', 0)
                if prev_volume > 0:
                    volume_ratio = volume / prev_volume
                    if volume_ratio < 1.3:
                        self.filter_stats['volume_ratio_filter'] += 1
                        continue
                    stock['volume_ratio'] = volume_ratio
                else:
                    self.filter_stats['volume_ratio_filter'] += 1
                    continue

                # Filter 6: Daily change null
                daily_change = stock.get('todaysChangePerc', 0)
                if daily_change is None:
                    self.filter_stats['daily_change_null'] += 1
                    continue

                # Filter 7: Daily change range (7-20%)
                if daily_change < 7.0 or daily_change > 20.0:
                    self.filter_stats['daily_change_range'] += 1
                    continue

                # Passed all pre-filters
                self.filter_stats['passed_pre_filter'] += 1
                filtered_stocks.append(stock)

            print(f"\n📊 PRE-FILTER PERFORMANCE:")
            print(f"   Input stocks: {self.filter_stats['total_input']:,}")
            print(f"   Ticker format: -{self.filter_stats['ticker_format']:,}")
            print(f"   No trading data: -{self.filter_stats['no_trading_data']:,}")
            print(f"   Price filter ($0.50-$100): -{self.filter_stats['price_filter']:,}")
            print(f"   Volume filter (<500K): -{self.filter_stats['volume_filter']:,}")
            print(f"   Volume ratio (<1.3x): -{self.filter_stats['volume_ratio_filter']:,}")
            print(f"   Daily change null: -{self.filter_stats['daily_change_null']:,}")
            print(f"   Daily change range (not 7-20%): -{self.filter_stats['daily_change_range']:,}")
            print(f"   ✅ Passed pre-filters: {self.filter_stats['passed_pre_filter']}")

            if filtered_stocks:
                print(f"\n🎯 STOCKS THAT PASSED PRE-FILTERS:")
                for i, stock in enumerate(filtered_stocks[:10]):
                    ticker = stock.get('ticker')
                    price = stock.get('day', {}).get('c', 0)
                    change = stock.get('todaysChangePerc', 0)
                    volume = stock.get('day', {}).get('v', 0)
                    vr = stock.get('volume_ratio', 0)
                    print(f"   {i+1}. {ticker}: ${price:.2f} | {change:+.1f}% | {volume:,.0f} vol | {vr:.1f}x VR")

                # Calculate pre-filter efficiency
                efficiency = (self.filter_stats['passed_pre_filter'] / self.filter_stats['total_input']) * 100
                print(f"\n📈 Pre-filter efficiency: {efficiency:.2f}%")

            else:
                print("\n❌ No stocks passed pre-filters")

        except Exception as e:
            print(f"❌ Debug failed: {e}")

if __name__ == "__main__":
    debugger = FilterPerformanceDebugger()
    asyncio.run(debugger.debug_full_pipeline())