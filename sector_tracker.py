#!/usr/bin/env python3
"""
Sector Rotation Tracker
Identifies hot sectors for the diamond scanner
"""

from polygon import RESTClient
import json
from collections import defaultdict
from datetime import datetime

with open('/Users/mikeclawd/.openclaw/secrets/polygon.json', 'r') as f:
    creds = json.load(f)

client = RESTClient(api_key=creds['apiKey'])

# Cache sector data to avoid repeated API calls
_sector_cache = {}
_sector_cache_time = None
SECTOR_CACHE_DURATION = 600  # 10 minutes

def get_sector_performance():
    """
    Analyze all sectors and return hot ones
    Returns: dict of {sector: {'pct_green': 0.65, 'avg_gain': 3.2, 'count': 10}}
    """
    global _sector_cache, _sector_cache_time

    # Return cached data if fresh
    if _sector_cache and _sector_cache_time:
        age = (datetime.now() - _sector_cache_time).total_seconds()
        if age < SECTOR_CACHE_DURATION:
            return _sector_cache

    print("📊 Analyzing sector performance...")

    sector_stocks = defaultdict(list)

    try:
        # Get all stock snapshots
        snapshots = client.get_snapshot_all("stocks")

        processed = 0
        for snap in snapshots:
            try:
                if not snap.day or not snap.day.close or not snap.prev_day or not snap.prev_day.close:
                    continue

                symbol = snap.ticker

                # Skip ETFs
                if any(x in symbol for x in ['-', '.', 'ETF', 'FUND']):
                    continue

                # Calculate daily change
                current = snap.day.close
                prev = snap.prev_day.close
                change_pct = ((current - prev) / prev) * 100

                # Get sector (try from ticker details)
                try:
                    details = client.get_ticker_details(symbol)
                    sector = getattr(details, 'sic_description', None)

                    if not sector:
                        continue

                    sector_stocks[sector].append(change_pct)
                    processed += 1

                    # Limit to avoid rate limiting
                    if processed >= 100:
                        break

                except:
                    continue

            except:
                continue

        # Analyze each sector
        sector_data = {}
        for sector, changes in sector_stocks.items():
            if len(changes) < 3:  # Need at least 3 stocks
                continue

            pct_green = sum(1 for c in changes if c > 0) / len(changes)
            avg_gain = sum(changes) / len(changes)

            sector_data[sector] = {
                'pct_green': pct_green,
                'avg_gain': avg_gain,
                'count': len(changes)
            }

        # Cache the results
        _sector_cache = sector_data
        _sector_cache_time = datetime.now()

        # Print hot sectors
        hot_sectors = [(s, d) for s, d in sector_data.items() if is_hot_sector(s, sector_data)]
        if hot_sectors:
            print(f"🔥 Found {len(hot_sectors)} hot sectors:")
            for sector, data in sorted(hot_sectors, key=lambda x: x[1]['avg_gain'], reverse=True)[:3]:
                print(f"   {sector}: {data['pct_green']*100:.0f}% green, avg {data['avg_gain']:+.1f}%")

        return sector_data

    except Exception as e:
        print(f"⚠️  Sector analysis error: {e}")
        return {}

def is_hot_sector(sector, sector_data):
    """
    Check if sector is currently hot
    Hot = >60% stocks green + avg gain >2%
    """
    if sector not in sector_data:
        return False

    data = sector_data[sector]
    return data['pct_green'] > 0.6 and data['avg_gain'] > 2.0

def get_stock_sector(symbol):
    """Get sector for a specific stock"""
    try:
        details = client.get_ticker_details(symbol)
        return getattr(details, 'sic_description', None)
    except:
        return None

if __name__ == '__main__':
    # Test the sector tracker
    sectors = get_sector_performance()
    print(f"\n✅ Analyzed {len(sectors)} sectors")

    hot = [(s, d) for s, d in sectors.items() if is_hot_sector(s, sectors)]
    print(f"🔥 {len(hot)} hot sectors found")
