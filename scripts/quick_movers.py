#!/usr/bin/env python3
"""Quick scan of top gainers from Polygon"""

from polygon import RESTClient
import json
from datetime import datetime, timedelta

# Load creds
with open('/Users/mikeclawd/.openclaw/secrets/polygon.json') as f:
    creds = json.load(f)

client = RESTClient(api_key=creds['apiKey'])

print("🔍 Scanning top gainers today...\n")

try:
    # Get snapshot of all stocks
    response = client.get_snapshot_all("stocks")
    
    if hasattr(response, 'tickers'):
        snapshots = response.tickers
    else:
        snapshots = response
    
    # Filter and rank
    candidates = []
    
    for snap in snapshots:
        try:
            if not snap.day or not snap.prevDay:
                continue
            
            symbol = snap.ticker
            price = snap.day.close
            prev_close = snap.prevDay.close
            volume = snap.day.volume
            
            # Skip if outside range
            if price < 0.50 or price > 100:
                continue
            if volume < 1_000_000:
                continue
            
            # Calculate gain
            gain_pct = ((price - prev_close) / prev_close) * 100
            
            # Only movers (but not crazy extended)
            if 3 <= gain_pct <= 25:
                candidates.append({
                    'symbol': symbol,
                    'price': price,
                    'gain': gain_pct,
                    'volume': volume
                })
        except:
            continue
    
    # Sort by gain
    candidates.sort(key=lambda x: x['gain'], reverse=True)
    
    print(f"Found {len(candidates)} movers (+3% to +25%, $0.50-$100, vol >1M)\n")
    print("=" * 70)
    print(f"{'SYMBOL':<8} {'PRICE':<10} {'GAIN %':<10} {'VOLUME':<15}")
    print("=" * 70)
    
    for c in candidates[:30]:  # Top 30
        vol_str = f"{c['volume']:,}"
        print(f"{c['symbol']:<8} ${c['price']:<9.2f} {c['gain']:>+6.1f}%    {vol_str:>12}")
    
    print("=" * 70)
    print(f"\nTop picks (need deeper analysis):")
    
    for i, c in enumerate(candidates[:10], 1):
        print(f"{i}. {c['symbol']} @ ${c['price']:.2f} (+{c['gain']:.1f}%)")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
