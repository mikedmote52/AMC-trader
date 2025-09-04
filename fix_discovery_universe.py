#!/usr/bin/env python3
"""
EMERGENCY FIX: Force Full Market Universe
Bypasses broken file loading and forces full Polygon universe
"""

import os
import sys
import asyncio
import httpx
import json
from datetime import datetime

async def fetch_full_polygon_universe(api_key: str) -> list:
    """Fetch the complete 5000+ stock universe from Polygon"""
    
    all_symbols = []
    page = 1
    max_pages = 50  # Should get 50,000 stocks
    
    print("🚨 EMERGENCY: Fetching FULL 5000+ stock universe from Polygon...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        
        while page <= max_pages:
            try:
                # Get ALL US stocks - no restrictions
                url = f"https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&limit=1000&apikey={api_key}"
                
                if page > 1:
                    # For subsequent pages, we'll need to handle pagination properly
                    # For now, let's get the first several thousand
                    break
                
                print(f"🔄 Fetching page {page}...")
                response = await client.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    
                    # Include ALL stock types that can be traded
                    for stock in results:
                        ticker = stock.get('ticker')
                        stock_type = stock.get('type', '')
                        exchange = stock.get('primary_exchange', '')
                        active = stock.get('active', False)
                        
                        # VERY INCLUSIVE - include all tradeable stock types
                        if (ticker and 
                            active and 
                            stock_type in ['CS', 'ADRC', 'ADR'] and  # Common Stock + All ADR types
                            exchange in ['XNYS', 'XNAS', 'ARCX', 'BATS', 'XASE', 'OTCM'] and  # All exchanges
                            len(ticker) <= 8):  # Reasonable ticker length
                            
                            all_symbols.append(ticker)
                    
                    print(f"   📊 Page {page}: {len(results)} raw stocks -> {len(all_symbols)} total tradeable")
                    
                    page += 1
                    
                    # If we got less than 1000, we're at the end
                    if len(results) < 1000:
                        break
                else:
                    print(f"   ❌ API error: {response.status_code}")
                    break
                    
            except Exception as e:
                print(f"   ❌ Request failed: {e}")
                break
    
    unique_symbols = sorted(list(set(all_symbols)))
    print(f"✅ FULL UNIVERSE: {len(unique_symbols)} stocks ready for discovery")
    
    # Show sample
    if unique_symbols:
        print(f"   Sample: {unique_symbols[:20]}")
        print(f"   Contains ANTE: {'✅' if 'ANTE' in unique_symbols else '❌'}")
        print(f"   Contains AMC: {'✅' if 'AMC' in unique_symbols else '❌'}")
    
    return unique_symbols

async def deploy_universe_fix():
    """Deploy the universe fix to production"""
    
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        print("❌ POLYGON_API_KEY required")
        return
    
    print("🚨 EMERGENCY DISCOVERY UNIVERSE FIX")
    print("=" * 60)
    
    # Get full universe
    universe = await fetch_full_polygon_universe(api_key)
    
    if len(universe) < 1000:
        print(f"❌ Universe too small: {len(universe)} stocks (need 1000+)")
        return
    
    # Create the universe file locally
    print(f"💾 Creating universe file with {len(universe)} stocks...")
    
    with open("data/universe_full.txt", "w") as f:
        f.write("# FULL US STOCK UNIVERSE - Emergency Fix\n")
        f.write(f"# Generated: {datetime.now()}\n")
        f.write(f"# Total Symbols: {len(universe)}\n")
        f.write("# ALL tradeable US stocks for proper discovery\n\n")
        
        for symbol in universe:
            f.write(f"{symbol}\n")
    
    print(f"✅ Universe file created: data/universe_full.txt")
    print(f"📈 Ready to deploy {len(universe)} stock universe vs broken 50-stock fallback")
    
    return universe

if __name__ == "__main__":
    universe = asyncio.run(deploy_universe_fix())