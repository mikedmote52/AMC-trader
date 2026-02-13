#!/usr/bin/env python3
"""Quick scan using Yahoo Finance gainers list"""

import requests
import json

print("🔍 Fetching top gainers from Yahoo Finance...\n")

try:
    # Yahoo Finance screener endpoint
    url = "https://query2.finance.yahoo.com/v1/finance/screener/predefined/saved"
    params = {
        "formatted": "true",
        "scrIds": "day_gainers",
        "count": 100
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    resp = requests.get(url, params=params, headers=headers)
    data = resp.json()
    
    quotes = data['finance']['result'][0]['quotes']
    
    print(f"Found {len(quotes)} top gainers\n")
    print("=" * 85)
    print(f"{'SYMBOL':<8} {'NAME':<25} {'PRICE':<10} {'CHANGE %':<12} {'VOLUME'}")
    print("=" * 85)
    
    setups = []
    
    for quote in quotes:
        try:
            symbol = quote.get('symbol', 'N/A')
            name = quote.get('shortName', 'N/A')[:24]
            price = quote.get('regularMarketPrice', 0)
            change = quote.get('regularMarketChangePercent', 0)
            volume = quote.get('regularMarketVolume', 0)
            
            # Our filters
            if not (0.50 <= price <= 100):
                continue
            if volume < 1_000_000:
                continue
            
            # Sweet spot: +3% to +20% (not chasing)
            if 3 <= change <= 20:
                setups.append((symbol, name, price, change, volume))
                status = "🟢"
            elif change > 20:
                status = "🔴"
            else:
                status = "⚪"
            
            vol_str = f"{volume:,}" if volume > 0 else "N/A"
            print(f"{symbol:<8} {name:<25} ${price:<9.2f} {change:>+6.2f}%    {vol_str:<15} {status}")
            
        except Exception as e:
            continue
    
    print("=" * 85)
    
    if setups:
        print(f"\n🎯 BEST SETUPS (+3% to +20%, not extended):\n")
        for i, (sym, name, price, chg, vol) in enumerate(setups[:15], 1):
            print(f"{i:2}. {sym:<6} ${price:>7.2f} (+{chg:>5.1f}%) - {name[:30]}")
    else:
        print("\n⚠️ No clean setups in the +3-20% zone")
        print("   Either market is quiet or everything is extended")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
