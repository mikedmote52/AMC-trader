#!/usr/bin/env python3
"""
Market Cap Cache Builder for Diamond Scanner
============================================

Builds a daily cache of market capitalization data for all active stocks.
This enables Phase 1 filtering in the scanner without API overhead.

Schedule: Run daily at 8:00 AM PT (before market open)
Runtime: ~40 minutes for 10,000 stocks
Output: data/market_cap_cache.json

Usage:
    python3 scripts/build_market_cap_cache.py

Cron example (8am PT = 4pm UTC):
    0 16 * * * cd ~/.openclaw/workspace && python3 scripts/build_market_cap_cache.py
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from polygon import RESTClient

# Configuration
CACHE_FILE = Path(__file__).parent.parent / 'data' / 'market_cap_cache.json'
POLYGON_SECRETS = Path.home() / '.openclaw' / 'secrets' / 'polygon.json'
RATE_LIMIT_DELAY = 0.21  # 5 req/sec = 0.2s, add buffer
MAX_STOCKS = 15000  # Process up to 15k stocks


def load_polygon_client():
    """Load Polygon API client from secrets"""
    try:
        with open(POLYGON_SECRETS, 'r') as f:
            creds = json.load(f)
        return RESTClient(api_key=creds['apiKey'])
    except Exception as e:
        print(f"❌ Failed to load Polygon credentials: {e}")
        print(f"   Expected file: {POLYGON_SECRETS}")
        exit(1)


def get_all_common_stocks(client):
    """Fetch all active common stocks using Polygon"""
    print("📊 Fetching all active common stocks...")

    stocks = []
    try:
        # Use list_tickers with type="CS" (Common Stock only)
        for ticker in client.list_tickers(
            market="stocks",
            type="CS",  # Common stock only - no ETFs
            active=True,
            limit=1000
        ):
            stocks.append(ticker.ticker)

            if len(stocks) >= MAX_STOCKS:
                print(f"⚠️  Reached max limit of {MAX_STOCKS} stocks")
                break

        print(f"✅ Found {len(stocks)} active common stocks")
        return stocks

    except Exception as e:
        print(f"❌ Error fetching stock list: {e}")
        return []


def build_market_cap_cache(client, stocks):
    """Build market cap cache for all stocks"""
    print(f"\n🔨 Building market cap cache for {len(stocks)} stocks...")
    print(f"   Estimated time: {len(stocks) * RATE_LIMIT_DELAY / 60:.1f} minutes")
    print(f"   Rate limit: {1/RATE_LIMIT_DELAY:.1f} req/sec\n")

    cache = {}
    success_count = 0
    error_count = 0
    start_time = time.time()

    for i, symbol in enumerate(stocks, 1):
        try:
            # Get ticker details (includes market_cap)
            details = client.get_ticker_details(symbol)
            market_cap = getattr(details, 'market_cap', None)

            if market_cap and market_cap > 0:
                cache[symbol] = market_cap
                success_count += 1
            else:
                # Store 0 for missing market cap (better than None)
                cache[symbol] = 0
                error_count += 1

            # Progress update every 100 stocks
            if i % 100 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                remaining = (len(stocks) - i) / rate if rate > 0 else 0

                print(f"   Progress: {i}/{len(stocks)} ({i/len(stocks)*100:.1f}%) "
                      f"- {success_count} success, {error_count} missing "
                      f"- ETA: {remaining/60:.1f} min")

            # Rate limiting
            time.sleep(RATE_LIMIT_DELAY)

        except Exception as e:
            error_count += 1
            if error_count < 10:  # Only show first 10 errors
                print(f"⚠️  Error fetching {symbol}: {e}")
            continue

    elapsed_time = time.time() - start_time

    print(f"\n✅ Cache build complete!")
    print(f"   Total stocks: {len(stocks)}")
    print(f"   Successful: {success_count}")
    print(f"   Missing data: {error_count}")
    print(f"   Time elapsed: {elapsed_time/60:.1f} minutes")
    print(f"   Average rate: {len(stocks)/elapsed_time:.1f} stocks/sec")

    return cache


def save_cache(cache):
    """Save market cap cache to JSON file"""
    print(f"\n💾 Saving cache to {CACHE_FILE}...")

    # Ensure data directory exists
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Add metadata
    cache_data = {
        '_metadata': {
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'stock_count': len([v for v in cache.values() if v > 0]),
            'total_entries': len(cache),
            'version': '1.0'
        }
    }

    # Add all market cap data
    cache_data.update(cache)

    # Save to file
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)

        file_size = CACHE_FILE.stat().st_size / 1024  # KB
        print(f"✅ Cache saved successfully!")
        print(f"   File: {CACHE_FILE}")
        print(f"   Size: {file_size:.1f} KB")
        print(f"   Entries: {len(cache)}")

    except Exception as e:
        print(f"❌ Error saving cache: {e}")
        exit(1)


def show_stats(cache):
    """Show market cap distribution statistics"""
    print("\n📈 Market Cap Distribution:")

    # Filter out zero values
    valid_caps = [v for v in cache.values() if v > 0]

    if not valid_caps:
        print("   No valid market cap data")
        return

    # Count by tier
    nano = len([v for v in valid_caps if v < 50_000_000])
    micro = len([v for v in valid_caps if 50_000_000 <= v < 300_000_000])
    small = len([v for v in valid_caps if 300_000_000 <= v < 2_000_000_000])
    mid = len([v for v in valid_caps if 2_000_000_000 <= v < 10_000_000_000])
    large = len([v for v in valid_caps if v >= 10_000_000_000])

    print(f"   Nano-cap (<$50M):      {nano:5d} ({nano/len(valid_caps)*100:4.1f}%)")
    print(f"   Micro-cap ($50M-$300M): {micro:5d} ({micro/len(valid_caps)*100:4.1f}%)")
    print(f"   Small-cap ($300M-$2B): {small:5d} ({small/len(valid_caps)*100:4.1f}%)")
    print(f"   Mid-cap ($2B-$10B):    {mid:5d} ({mid/len(valid_caps)*100:4.1f}%)")
    print(f"   Large-cap (>$10B):     {large:5d} ({large/len(valid_caps)*100:4.1f}%)")

    # Scanner target (< $1B)
    scanner_targets = len([v for v in valid_caps if v < 1_000_000_000])
    print(f"\n   Scanner targets (<$1B): {scanner_targets:5d} ({scanner_targets/len(valid_caps)*100:4.1f}%)")


def main():
    """Main execution"""
    print("=" * 70)
    print("Market Cap Cache Builder - Diamond Scanner V3.2")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Load Polygon client
    client = load_polygon_client()

    # Get all common stocks
    stocks = get_all_common_stocks(client)

    if not stocks:
        print("❌ No stocks found. Exiting.")
        exit(1)

    # Build cache
    cache = build_market_cap_cache(client, stocks)

    # Save cache
    save_cache(cache)

    # Show statistics
    show_stats(cache)

    print("\n" + "=" * 70)
    print("✅ Market cap cache build complete!")
    print("   The scanner can now filter by market cap in Phase 1")
    print("   Next scheduled run: Tomorrow at 8:00 AM PT")
    print("=" * 70)


if __name__ == "__main__":
    main()
