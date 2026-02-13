#!/usr/bin/env python3
"""Quick mover scan using Alpaca screener"""

import json
import requests
from datetime import datetime

# Load credentials
with open('/Users/mikeclawd/.openclaw/secrets/alpaca.json') as f:
    creds = json.load(f)

headers = {
    'APCA-API-KEY-ID': creds['apiKey'],
    'APCA-API-SECRET-KEY': creds['apiSecret']
}

base_url = 'https://paper-api.alpaca.markets'

print(f"🔍 Scanning for movers - {datetime.now().strftime('%I:%M %p PT')}\n")

# Get most active stocks
print("Fetching most active stocks from Alpaca...\n")

try:
    # Get screener data - most active
    resp = requests.get(
        f'{base_url}/v1beta1/screener/stocks/most-actives',
        headers=headers,
        params={'top': 50}
    )
    
    if resp.status_code != 200:
        print(f"❌ Error: {resp.status_code} - {resp.text}")
    else:
        actives = resp.json()
        
        print("=" * 80)
        print(f"{'SYMBOL':<8} {'PRICE':<10} {'CHANGE %':<12} {'VOLUME':<15} {'STATUS'}")
        print("=" * 80)
        
        # Filter for our criteria
        setups = []
        
        for stock in actives:
            try:
                symbol = stock.get('symbol', 'N/A')
                price = float(stock.get('price', 0))
                change = float(stock.get('change', 0))
                volume = int(stock.get('volume', 0))
                
                # Our filters
                if not (0.50 <= price <= 100):
                    continue
                if volume < 1_000_000:
                    continue
                
                # Categorize
                if 3 <= change <= 20:
                    status = "🟢 SETUP"
                    setups.append((symbol, price, change, volume))
                elif change > 20:
                    status = "🔴 TOO HOT"
                elif change < -10:
                    status = "⚠️ FALLING"
                else:
                    status = "⚪ NEUTRAL"
                
                vol_str = f"{volume:,}"
                print(f"{symbol:<8} ${price:<9.2f} {change:>+6.2f}%    {vol_str:>12}  {status}")
                
            except Exception as e:
                continue
        
        print("=" * 80)
        
        if setups:
            print(f"\n🎯 POTENTIAL SETUPS ({len(setups)}):\n")
            for sym, price, chg, vol in setups:
                print(f"   {sym} @ ${price:.2f} (+{chg:.1f}%) - Vol: {vol:,}")
        else:
            print("\n⚠️ No setups found in the +3% to +20% range")
            print("   Market might be quiet or extended today")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
