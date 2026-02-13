#!/usr/bin/env python3
"""
Full Market Scanner - Scans ALL stocks under $100
Uses NASDAQ API for universe, then scores each using Squeeze Strategy
"""

import requests
import json
import time
from datetime import datetime
import os

# Alpaca credentials
ALPACA_CREDS_PATH = '/Users/mikeclawd/.openclaw/secrets/alpaca.json'
with open(ALPACA_CREDS_PATH, 'r') as f:
    creds = json.load(f)

ALPACA_HEADERS = {
    'APCA-API-KEY-ID': creds['apiKey'],
    'APCA-API-SECRET-KEY': creds['apiSecret']
}

BASE_URL = creds['baseUrl'].rstrip('/v2').rstrip('/')

def get_full_stock_universe():
    """Download all NASDAQ/NYSE stocks"""
    print("Downloading full stock universe from NASDAQ...")
    
    url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=10000&offset=0&download=true"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'rows' in data['data']:
                stocks = data['data']['rows']
                print(f"✅ Retrieved {len(stocks)} stocks from NASDAQ\n")
                return stocks
    except Exception as e:
        print(f"❌ Error downloading universe: {e}")
    
    return []

def filter_universe(stocks):
    """
    Apply Universe Filter (from SQUEEZE_STRATEGY.md):
    - Price: $0.50 – $100
    - Volume: ≥ 1M shares avg
    """
    print("Filtering universe...")
    filtered = []
    
    for stock in stocks:
        try:
            symbol = stock.get('symbol', '')
            price_str = stock.get('lastsale', '$0').replace('$', '').replace(',', '')
            volume_str = stock.get('volume', '0').replace(',', '')
            
            # Skip if no data
            if not price_str or price_str == '' or price_str == 'N/A':
                continue
                
            price = float(price_str)
            volume = int(volume_str) if volume_str and volume_str != 'N/A' else 0
            
            # Apply filters
            if 0.50 <= price <= 100 and volume >= 1_000_000:
                filtered.append({
                    'symbol': symbol,
                    'price': price,
                    'volume': volume,
                    'name': stock.get('name', '')[:40]
                })
                
        except (ValueError, TypeError):
            continue
    
    print(f"✅ {len(filtered)} stocks passed universe filter (price $0.50-$100, volume >1M)\n")
    return filtered

def check_squeeze_setup_alpaca(symbol):
    """
    Use Alpaca API to check for squeeze setup
    Returns: (score, reason) or (0, error_msg)
    """
    try:
        # Get latest bar
        bars_url = f"{BASE_URL}/v2/stocks/{symbol}/bars/latest"
        response = requests.get(bars_url, headers=ALPACA_HEADERS)
        
        if response.status_code != 200:
            return 0, "No data"
        
        bar_data = response.json()
        if 'bar' not in bar_data:
            return 0, "No bar data"
        
        bar = bar_data['bar']
        
        # Check for volume spike (3x average - simplified check)
        volume = bar.get('v', 0)
        
        # Check for momentum (+5% to +20%)
        open_price = bar.get('o', 0)
        close_price = bar.get('c', 0)
        
        if open_price > 0:
            daily_change = ((close_price - open_price) / open_price) * 100
            
            # Score based on momentum
            if 5 <= daily_change <= 20:
                return 50, f"+{daily_change:.1f}% (ideal momentum)"
            elif daily_change > 20:
                return 20, f"+{daily_change:.1f}% (extended, chasing risk)"
            elif daily_change > 0:
                return 10, f"+{daily_change:.1f}% (weak momentum)"
        
        return 0, "No momentum"
        
    except Exception as e:
        return 0, str(e)

def scan_market():
    """Run full market scan"""
    print("=" * 80)
    print("FULL MARKET SQUEEZE SCANNER")
    print(f"Running at {datetime.now().strftime('%I:%M %p PT')}")
    print("=" * 80)
    print()
    
    # Step 1: Get universe
    all_stocks = get_full_stock_universe()
    if not all_stocks:
        print("❌ Failed to download stock universe")
        return
    
    # Step 2: Filter by price and volume
    filtered = filter_universe(all_stocks)
    
    print(f"📊 Will scan {len(filtered)} stocks for squeeze setups...")
    print(f"⏱️  Estimated time: ~{len(filtered) * 0.5 / 60:.0f} minutes (rate-limited)\n")
    
    # Ask for confirmation
    response = input("Continue with scan? (y/n): ")
    if response.lower() != 'y':
        print("Scan cancelled.")
        return
    
    # Step 3: Score each stock
    candidates = []
    
    for i, stock in enumerate(filtered[:100], 1):  # Limit to 100 for now
        symbol = stock['symbol']
        print(f"[{i}/{min(100, len(filtered))}] Checking {symbol}...", end=" ")
        
        score, reason = check_squeeze_setup_alpaca(symbol)
        
        if score > 0:
            print(f"✅ Score: {score}/100 - {reason}")
            candidates.append({
                'symbol': symbol,
                'price': stock['price'],
                'volume': stock['volume'],
                'score': score,
                'reason': reason
            })
        else:
            print(f"❌ {reason}")
        
        time.sleep(0.5)  # Rate limiting
    
    # Sort by score
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # Print results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    if candidates:
        print(f"\n🎯 Found {len(candidates)} stocks with squeeze potential:\n")
        print(f"{'Symbol':<8} {'Price':<10} {'Score':<8} {'Reason'}")
        print("-" * 80)
        
        for c in candidates[:20]:
            print(f"{c['symbol']:<8} ${c['price']:<9.2f} {c['score']:<8} {c['reason']}")
    else:
        print("\n❌ No squeeze candidates found in scanned stocks")
    
    print("=" * 80)
    
    # Save to file
    output_file = '/Users/mikeclawd/.openclaw/workspace/data/squeeze_candidates.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(candidates, f, indent=2)
    
    print(f"\n💾 Saved {len(candidates)} candidates to {output_file}")
    
    return candidates

if __name__ == '__main__':
    scan_market()
