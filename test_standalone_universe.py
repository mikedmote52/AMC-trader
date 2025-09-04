#!/usr/bin/env python3
"""
Standalone Dynamic Universe Test
"""

import os
import logging

def fetch_polygon_universe(api_key: str) -> list:
    """Standalone version of the dynamic universe fetch"""
    all_symbols = []
    next_url = None
    page = 1
    max_pages = 20  # Limit for testing
    
    try:
        import requests
        
        print("🌍 Fetching full stock universe from Polygon API...")
        
        while page <= max_pages:
            if next_url:
                url = f"https://api.polygon.io{next_url}&apikey={api_key}"
            else:
                url = f"https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&limit=1000&apikey={api_key}"
            
            print(f"🔄 Fetching universe page {page}...")
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                # Filter for tradeable stocks
                page_symbols = []
                for stock in results:
                    ticker = stock.get('ticker')
                    stock_type = stock.get('type', '')
                    exchange = stock.get('primary_exchange', '')
                    
                    # Include common stocks AND ADRCs (like ANTE)
                    if (ticker and 
                        stock_type in ['CS', 'ADRC'] and  # Common Stock + American Depositary Receipt
                        exchange in ['XNYS', 'XNAS', 'ARCX', 'BATS', 'XASE'] and  # Major exchanges
                        len(ticker) <= 6 and  # Reasonable ticker length
                        ticker.replace('.', '').isalpha()):  # Letters only
                        
                        all_symbols.append(ticker)
                        page_symbols.append(ticker)
                
                print(f"📊 Page {page}: {len(results)} raw stocks -> {len(page_symbols)} filtered -> {len(all_symbols)} total")
                
                # Show some examples from this page
                if page_symbols:
                    print(f"   Examples: {page_symbols[:10]}")
                
                # Check for next page
                next_url = data.get('next_url')
                if not next_url:
                    print("   ✅ Reached end of data")
                    break
                page += 1
            else:
                print(f"❌ Polygon API error on page {page}: {response.status_code}")
                if response.text:
                    print(f"   Error details: {response.text[:200]}")
                break
                
        # Deduplicate and sort
        unique_symbols = sorted(list(set(all_symbols)))
        print(f"✅ Polygon universe complete: {len(unique_symbols)} unique symbols")
        return unique_symbols
        
    except Exception as e:
        print(f"❌ Polygon universe fetch failed: {e}")
        return []

def main():
    """Test the dynamic universe system"""
    
    print("🧪 STANDALONE DYNAMIC UNIVERSE TEST")
    print("=" * 60)
    
    POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
    if not POLYGON_API_KEY:
        print("❌ POLYGON_API_KEY environment variable required")
        return
    
    # Fetch universe
    universe = fetch_polygon_universe(POLYGON_API_KEY)
    
    if universe:
        print(f"\n📊 UNIVERSE ANALYSIS:")
        print(f"   Total symbols: {len(universe):,}")
        print(f"   First 20: {universe[:20]}")
        print(f"   Last 10: {universe[-10:]}")
        
        # Check for specific symbols
        test_symbols = ['ANTE', 'AMC', 'GME', 'SNDL', 'UP', 'NAK', 'AAPL', 'TSLA']
        print(f"\n🎯 Symbol availability check:")
        found_count = 0
        for symbol in test_symbols:
            if symbol in universe:
                print(f"   ✅ {symbol}")
                found_count += 1
            else:
                print(f"   ❌ {symbol}")
        
        print(f"\n📈 DISCOVERY IMPROVEMENT:")
        print(f"   Old static universe: ~50 symbols")
        print(f"   New dynamic universe: {len(universe):,} symbols")
        print(f"   Improvement: {len(universe)/50:.1f}x more stocks to scan")
        print(f"   Test symbols found: {found_count}/{len(test_symbols)}")
        
        if found_count >= len(test_symbols) * 0.8:  # 80% success rate
            print(f"   ✅ DYNAMIC UNIVERSE WORKING - {found_count/len(test_symbols)*100:.0f}% symbol coverage")
        else:
            print(f"   ⚠️  NEEDS IMPROVEMENT - Only {found_count/len(test_symbols)*100:.0f}% symbol coverage")
    else:
        print("❌ Dynamic universe fetch completely failed")

if __name__ == "__main__":
    main()