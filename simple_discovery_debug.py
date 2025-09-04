#!/usr/bin/env python3
"""
Simple Discovery Debug - Test the actual discovery pipeline step by step
"""

import os
import asyncio
import httpx
import json
from datetime import datetime

async def debug_discovery_pipeline():
    """Run discovery pipeline with detailed debugging"""
    
    POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
    if not POLYGON_API_KEY:
        print("❌ POLYGON_API_KEY required")
        return
    
    print("🚀 AMC-TRADER DISCOVERY DEBUG")
    print("=" * 60)
    
    # Step 1: Load Universe
    print("📖 STEP 1: Loading Universe File")
    try:
        with open("data/universe.txt", "r") as f:
            lines = f.readlines()
        
        universe = [line.strip().upper() for line in lines 
                   if line.strip() and not line.strip().startswith('#')]
        
        print(f"✅ Universe loaded: {len(universe)} symbols")
        print(f"📊 First 10 symbols: {universe[:10]}")
        print(f"🔍 Contains ANTE: {'✅' if 'ANTE' in universe else '❌'}")
        print(f"🔍 Contains AAPL: {'✅' if 'AAPL' in universe else '❌'}")
        
    except Exception as e:
        print(f"❌ Failed to load universe: {e}")
        return
    
    # Step 2: Test specific symbols
    test_symbols = ['ANTE', 'AAPL', 'TSLA', 'UP', 'NAK', 'AMD']
    print(f"\n🧪 STEP 2: Testing Specific Symbols")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for symbol in test_symbols:
            print(f"\n🔍 Testing {symbol}:")
            
            # Check if in universe
            if symbol not in universe:
                print(f"   ❌ Not in universe file")
                continue
            print(f"   ✅ Found in universe")
            
            # Test Polygon API access
            try:
                # Get previous day data
                url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?apikey={POLYGON_API_KEY}"
                response = await client.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    if results:
                        price_data = results[0]
                        price = price_data.get('c', 0)
                        volume = price_data.get('v', 0)
                        print(f"   ✅ Polygon data: ${price:.2f}, vol={volume:,}")
                        
                        # Test historical data
                        hist_url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/2024-07-01/2025-09-02?apikey={POLYGON_API_KEY}"
                        hist_response = await client.get(hist_url)
                        if hist_response.status_code == 200:
                            hist_data = hist_response.json()
                            hist_results = hist_data.get('results', [])
                            print(f"   ✅ Historical data: {len(hist_results)} bars")
                            
                            if len(hist_results) >= 20:
                                # Calculate volume spike
                                recent_volume = hist_results[-1].get('v', 0)
                                avg_volume = sum(bar.get('v', 0) for bar in hist_results[-20:]) / 20
                                volume_spike = recent_volume / avg_volume if avg_volume > 0 else 0
                                print(f"   📊 Volume analysis: {recent_volume:,} vs avg {avg_volume:,.0f} = {volume_spike:.2f}x spike")
                                
                                # Check price range
                                if 0.50 <= price <= 50.0:
                                    print(f"   ✅ Price in range: ${price:.2f}")
                                else:
                                    print(f"   ❌ Price out of range: ${price:.2f} (target: $0.50-$50.00)")
                                
                                # Check volume spike
                                if volume_spike >= 2.0:
                                    print(f"   ⭐ VOLUME CANDIDATE: {volume_spike:.2f}x spike!")
                                else:
                                    print(f"   ⚠️  Low volume spike: {volume_spike:.2f}x (need >2.0x)")
                            else:
                                print(f"   ❌ Insufficient historical data: {len(hist_results)} bars")
                        else:
                            print(f"   ❌ Historical data failed: {hist_response.status_code}")
                    else:
                        print(f"   ❌ No results in Polygon response")
                else:
                    print(f"   ❌ Polygon API error: {response.status_code} - {response.text[:100]}")
                    
            except Exception as e:
                print(f"   ❌ API error: {e}")
    
    # Step 3: Check current live candidates
    print(f"\n🔴 STEP 3: Current Live Discovery Results")
    try:
        async with httpx.AsyncClient() as client:
            api_url = "https://amc-trader.onrender.com/discovery/squeeze-candidates?min_score=0.1"
            response = await client.get(api_url)
            if response.status_code == 200:
                data = response.json()
                candidates = data.get('candidates', [])
                print(f"✅ Live system found: {len(candidates)} candidates")
                for candidate in candidates:
                    symbol = candidate.get('symbol')
                    score = candidate.get('squeeze_score', 0)
                    price = candidate.get('price', 0)
                    print(f"   🎯 {symbol}: ${price:.2f}, score={score:.3f}")
                    
                # Check if our test symbols are there
                live_symbols = [c.get('symbol') for c in candidates]
                for test_symbol in test_symbols:
                    if test_symbol in live_symbols:
                        print(f"   ✅ {test_symbol} found in live results")
                    else:
                        print(f"   ❌ {test_symbol} missing from live results")
            else:
                print(f"❌ Live API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Live API error: {e}")
    
    # Step 4: Summary
    print(f"\n📊 DISCOVERY SUMMARY")
    print(f"Universe size: {len(universe)} symbols")
    print(f"Test symbols checked: {len(test_symbols)}")
    print(f"Next steps: Identify why specific symbols are being filtered out")

if __name__ == "__main__":
    asyncio.run(debug_discovery_pipeline())