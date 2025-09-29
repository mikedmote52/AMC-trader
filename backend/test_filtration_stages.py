#!/usr/bin/env python3
"""
STEP-BY-STEP FILTRATION ANALYSIS
Shows exactly how many stocks are eliminated at each filter stage
"""

import requests
import os

POLYGON_API_KEY = os.getenv('POLYGON_API_KEY', '1ORwpSzeOV20X6uaA8G3Zuxx7hLJ0KIC')

def analyze_filtration_stages():
    """Analyze how many stocks pass each filter stage"""

    print("🔬 STEP-BY-STEP FILTRATION ANALYSIS")
    print("=" * 60)

    # Get raw universe
    url = "https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers"
    response = requests.get(url, params={'apikey': POLYGON_API_KEY}, timeout=30)

    if response.status_code != 200:
        print(f"❌ Failed to get universe: {response.status_code}")
        return

    data = response.json()
    raw_tickers = data.get('tickers', [])

    print(f"📊 STARTING UNIVERSE: {len(raw_tickers):,} stocks")

    # Apply each filter and count
    step1_tickers = []  # Basic ticker format
    step2_price = []    # Price filter
    step3_volume = []   # Volume filter
    step4_vol_ratio = [] # Volume ratio filter
    step5_change = []   # Daily change filter

    # Step 1: Basic ticker format
    for stock in raw_tickers:
        ticker = stock.get('ticker', '')
        if not ticker or len(ticker) > 5:
            continue
        if any(char in ticker for char in ['.', '-']):
            continue
        if ticker.endswith('W'):
            continue
        step1_tickers.append(stock)

    print(f"📋 AFTER TICKER FILTER: {len(step1_tickers):,} stocks (-{len(raw_tickers) - len(step1_tickers):,})")

    # Step 2: Price filter
    for stock in step1_tickers:
        day_data = stock.get('day', {})
        if not day_data:
            continue
        price = day_data.get('c', 0)
        if 0.50 <= price <= 50.0:  # Current price range
            step2_price.append(stock)

    print(f"💰 AFTER PRICE FILTER ($0.50-$50): {len(step2_price):,} stocks (-{len(step1_tickers) - len(step2_price):,})")

    # Step 3: Volume filter
    for stock in step2_price:
        day_data = stock.get('day', {})
        volume = day_data.get('v', 0)
        if volume >= 500000:  # 500K minimum
            step3_volume.append(stock)

    print(f"📈 AFTER VOLUME FILTER (500K+): {len(step3_volume):,} stocks (-{len(step2_price) - len(step3_volume):,})")

    # Step 4: Volume ratio filter
    for stock in step3_volume:
        day_data = stock.get('day', {})
        prev_day_data = stock.get('prevDay', {})
        volume = day_data.get('v', 0)
        prev_volume = prev_day_data.get('v', 0)

        if prev_volume > 0:
            volume_ratio = volume / prev_volume
            if volume_ratio >= 1.3:  # 30% volume increase
                step4_vol_ratio.append(stock)

    print(f"🔥 AFTER VOLUME RATIO FILTER (1.3x+): {len(step4_vol_ratio):,} stocks (-{len(step3_volume) - len(step4_vol_ratio):,})")

    # Step 5: Daily change filter
    for stock in step4_vol_ratio:
        daily_change = stock.get('todaysChangePerc', 0)
        if daily_change is not None and 5.0 <= daily_change <= 50.0:  # 5-50% range
            step5_change.append(stock)

    print(f"📊 AFTER CHANGE FILTER (5-50%): {len(step5_change):,} stocks (-{len(step4_vol_ratio) - len(step5_change):,})")

    # Show sample candidates if any
    if step5_change:
        print(f"\n🎯 SAMPLE FILTERED CANDIDATES:")
        for i, stock in enumerate(step5_change[:10], 1):
            ticker = stock.get('ticker')
            price = stock.get('day', {}).get('c', 0)
            volume = stock.get('day', {}).get('v', 0)
            change = stock.get('todaysChangePerc', 0)
            prev_volume = stock.get('prevDay', {}).get('v', 1)
            vol_ratio = volume / prev_volume if prev_volume > 0 else 0

            print(f"   {i}. {ticker}: ${price:.2f} | {change:+.1f}% | Vol {volume:,} ({vol_ratio:.1f}x)")
    else:
        print(f"\n❌ NO STOCKS PASS ALL FILTERS")
        print(f"🔧 FILTER ANALYSIS:")
        print(f"   • 500K+ volume requirement eliminates {len(step2_price) - len(step3_volume):,} stocks")
        print(f"   • 1.3x volume ratio eliminates {len(step3_volume) - len(step4_vol_ratio):,} stocks")
        print(f"   • 5%+ daily change eliminates {len(step4_vol_ratio) - len(step5_change):,} stocks")

    # Suggest relaxed filters
    print(f"\n💡 SUGGESTED RELAXED FILTERS:")

    # Test relaxed volume
    relaxed_vol = [s for s in step2_price if s.get('day', {}).get('v', 0) >= 100000]  # 100K
    print(f"   Volume 100K+ instead of 500K+: {len(relaxed_vol):,} stocks")

    # Test relaxed volume ratio
    relaxed_ratio = []
    for stock in step3_volume:
        day_data = stock.get('day', {})
        prev_day_data = stock.get('prevDay', {})
        volume = day_data.get('v', 0)
        prev_volume = prev_day_data.get('v', 0)

        if prev_volume > 0:
            volume_ratio = volume / prev_volume
            if volume_ratio >= 1.1:  # 10% increase instead of 30%
                relaxed_ratio.append(stock)

    print(f"   Volume ratio 1.1x+ instead of 1.3x+: {len(relaxed_ratio):,} stocks")

    # Test relaxed change
    relaxed_change = [s for s in step4_vol_ratio if s.get('todaysChangePerc', 0) >= 2.0]  # 2%+
    print(f"   Daily change 2%+ instead of 5%+: {len(relaxed_change):,} stocks")

if __name__ == "__main__":
    analyze_filtration_stages()