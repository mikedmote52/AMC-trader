#!/usr/bin/env python3
"""
Test Full Polygon Universe - See what we should actually be scanning
"""

import os
import asyncio
import httpx
import json
from datetime import datetime

async def test_full_polygon_universe():
    """Test the full Polygon universe to see scale"""
    
    POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
    if not POLYGON_API_KEY:
        print("❌ POLYGON_API_KEY required")
        return
    
    print("🌍 TESTING FULL POLYGON STOCK UNIVERSE")
    print("=" * 60)
    
    total_stocks = 0
    pages_fetched = 0
    next_url = None
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        while pages_fetched < 10:  # Limit to 10 pages for testing
            try:
                if next_url:
                    # Use the next_url from pagination
                    url = f"https://api.polygon.io{next_url}&apikey={POLYGON_API_KEY}"
                else:
                    # Initial request for ALL US stocks
                    url = f"https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&limit=1000&apikey={POLYGON_API_KEY}"
                
                print(f"📡 Fetching page {pages_fetched + 1}...")
                response = await client.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    
                    print(f"   📊 Page {pages_fetched + 1}: {len(results)} stocks")
                    
                    # Show sample of what we're getting
                    if pages_fetched == 0:
                        print(f"   📋 Sample stocks from page 1:")
                        for i, stock in enumerate(results[:10]):
                            ticker = stock.get('ticker')
                            name = stock.get('name', 'N/A')[:30]
                            stock_type = stock.get('type')
                            exchange = stock.get('primary_exchange')
                            print(f"      {i+1:2d}. {ticker:6s} | {name:30s} | {stock_type:5s} | {exchange}")
                    
                    # Count different types
                    if pages_fetched == 0:
                        type_counts = {}
                        exchange_counts = {}
                        for stock in results:
                            stock_type = stock.get('type', 'Unknown')
                            exchange = stock.get('primary_exchange', 'Unknown')
                            type_counts[stock_type] = type_counts.get(stock_type, 0) + 1
                            exchange_counts[exchange] = exchange_counts.get(exchange, 0) + 1
                        
                        print(f"   📈 Stock types in first 1000:")
                        for stock_type, count in sorted(type_counts.items()):
                            print(f"      {stock_type}: {count}")
                        
                        print(f"   🏛️  Exchanges in first 1000:")
                        for exchange, count in sorted(exchange_counts.items()):
                            print(f"      {exchange}: {count}")
                    
                    total_stocks += len(results)
                    pages_fetched += 1
                    
                    # Check for next page
                    next_url = data.get('next_url')
                    if not next_url:
                        print("   ✅ Reached end of data")
                        break
                else:
                    print(f"   ❌ API error: {response.status_code}")
                    break
                    
            except Exception as e:
                print(f"   ❌ Request failed: {e}")
                break
        
        print(f"\n📊 POLYGON UNIVERSE SUMMARY:")
        print(f"   Pages fetched: {pages_fetched}")
        print(f"   Total stocks found: {total_stocks:,}")
        print(f"   Estimated full universe: {total_stocks * 10:,}+ stocks")
        
        # Now test filtering criteria
        print(f"\n🔍 TESTING DISCOVERY CRITERIA:")
        
        # Test our current universe size vs what we should have
        with open("data/universe.txt", "r") as f:
            current_universe = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        
        print(f"   Current universe file: {len(current_universe)} stocks")
        print(f"   Should be scanning: {total_stocks:,}+ stocks")
        print(f"   Missing potential: {total_stocks - len(current_universe):,}+ stocks")
        
        # Test specific missing stocks
        print(f"\n🎯 CHECKING KNOWN GOOD PERFORMERS:")
        test_symbols = ['ANTE', 'VIGL', 'MMAT', 'GNUS', 'SNDL', 'AMC', 'GME']
        
        for symbol in test_symbols:
            try:
                url = f"https://api.polygon.io/v3/reference/tickers/{symbol}?apikey={POLYGON_API_KEY}"
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', {})
                    if results:
                        name = results.get('name', 'N/A')
                        stock_type = results.get('type', 'N/A')
                        exchange = results.get('primary_exchange', 'N/A')
                        active = results.get('active', False)
                        print(f"   ✅ {symbol:6s}: {name[:30]:30s} | {stock_type:5s} | {exchange:8s} | Active: {active}")
                    else:
                        print(f"   ❌ {symbol:6s}: No data found")
                else:
                    print(f"   ❌ {symbol:6s}: API error {response.status_code}")
            except Exception as e:
                print(f"   ❌ {symbol:6s}: Error {e}")

if __name__ == "__main__":
    asyncio.run(test_full_polygon_universe())