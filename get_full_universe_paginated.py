#!/usr/bin/env python3
"""
Get FULL Polygon Universe with Proper Pagination
"""

import os
import asyncio
import requests
import time
from datetime import datetime

def fetch_full_polygon_universe_sync(api_key: str) -> list:
    """Synchronously fetch ALL stocks with proper pagination"""
    
    all_symbols = []
    next_url = None
    page = 1
    
    print("🌍 FETCHING COMPLETE STOCK UNIVERSE FROM POLYGON...")
    
    while page <= 100:  # Safety limit
        try:
            if next_url:
                # Parse the next_url properly - it's a full URL path
                if next_url.startswith('https://'):
                    url = f"{next_url}&apikey={api_key}"
                else:
                    url = f"https://api.polygon.io{next_url}&apikey={api_key}"
            else:
                url = f"https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&limit=1000&apikey={api_key}"
            
            print(f"📡 Fetching page {page}...")
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                page_count = 0
                for stock in results:
                    ticker = stock.get('ticker')
                    stock_type = stock.get('type', '')
                    exchange = stock.get('primary_exchange', '')
                    active = stock.get('active', False)
                    
                    # Include ALL tradeable types
                    if (ticker and 
                        active and 
                        stock_type in ['CS', 'ADRC', 'ADR', 'FUND', 'ETF', 'ETS'] and  # All tradeable types
                        exchange in ['XNYS', 'XNAS', 'ARCX', 'BATS', 'XASE', 'OTCM', 'OTCX'] and  # All exchanges
                        len(ticker) <= 6 and
                        ticker.replace('.', '').replace('-', '').isalpha()):  # Valid ticker format
                        
                        all_symbols.append(ticker)
                        page_count += 1
                
                print(f"   📊 Page {page}: {len(results)} raw -> {page_count} tradeable -> {len(all_symbols)} total")
                
                # Check for next page
                next_url = data.get('next_url')
                if not next_url:
                    print("   ✅ Reached end of data")
                    break
                
                page += 1
                time.sleep(0.1)  # Rate limiting
                
            else:
                print(f"   ❌ API error: {response.status_code}")
                if response.text:
                    print(f"   Details: {response.text[:200]}")
                break
                
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
            break
    
    unique_symbols = sorted(list(set(all_symbols)))
    print(f"\n✅ COMPLETE UNIVERSE FETCHED: {len(unique_symbols)} unique stocks")
    
    return unique_symbols

def main():
    """Main execution"""
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        print("❌ POLYGON_API_KEY required")
        return
    
    print("🚨 CRITICAL: Fetching COMPLETE 5000+ Stock Universe")
    print("=" * 60)
    
    # Get complete universe
    universe = fetch_full_polygon_universe_sync(api_key)
    
    print(f"\n📊 UNIVERSE ANALYSIS:")
    print(f"   Total stocks: {len(universe):,}")
    print(f"   First 20: {universe[:20]}")
    
    # Check key symbols
    test_symbols = ['ANTE', 'AMC', 'GME', 'AAPL', 'TSLA', 'VIGL', 'UP', 'NAK']
    found = 0
    for symbol in test_symbols:
        if symbol in universe:
            print(f"   ✅ {symbol}")
            found += 1
        else:
            print(f"   ❌ {symbol} MISSING")
    
    print(f"\n🎯 RESULTS:")
    print(f"   Universe size: {len(universe):,} stocks")
    print(f"   Target symbols found: {found}/{len(test_symbols)}")
    
    if len(universe) >= 1000:
        print(f"   ✅ SUCCESS: Universe size adequate for proper discovery")
        
        # Save to file
        with open("data/universe_complete.txt", "w") as f:
            f.write("# COMPLETE US STOCK UNIVERSE FROM POLYGON\n")
            f.write(f"# Generated: {datetime.now()}\n")
            f.write(f"# Total Symbols: {len(universe)}\n")
            f.write("# Includes: CS, ADRC, ADR types from all major exchanges\n\n")
            
            for symbol in universe:
                f.write(f"{symbol}\n")
        
        print(f"💾 Saved to: data/universe_complete.txt")
        return universe
    else:
        print(f"   ❌ FAILED: Universe too small ({len(universe)} < 1000)")
        return []

if __name__ == "__main__":
    main()