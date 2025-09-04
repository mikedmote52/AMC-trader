#!/usr/bin/env python3
"""
Debug Discovery Pipeline
Runs the full discovery system with detailed filtering analysis
"""

import os
import sys
import json
import asyncio
import httpx
from datetime import datetime, timedelta
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend/src'))

# Import discovery components
from jobs.discover import DiscoveryService
from polygon import RESTClient

class DebugDiscoveryService(DiscoveryService):
    """Enhanced discovery service with detailed debug output"""
    
    def __init__(self):
        super().__init__()
        self.debug_stats = {
            'universe_size': 0,
            'polygon_data_fetched': 0,
            'polygon_failures': 0,
            'price_filtered': 0,
            'volume_filtered': 0,
            'final_candidates': 0,
            'filter_steps': []
        }
    
    def read_universe(self):
        """Read universe with debug info"""
        symbols = super().read_universe()
        self.debug_stats['universe_size'] = len(symbols)
        print(f"📊 UNIVERSE LOADED: {len(symbols)} symbols")
        print(f"🔍 First 10 symbols: {symbols[:10]}")
        print(f"🎯 Looking for ANTE: {'✅ FOUND' if 'ANTE' in symbols else '❌ MISSING'}")
        return symbols
    
    async def debug_single_symbol(self, symbol):
        """Debug a single symbol through the pipeline"""
        print(f"\n🔍 DEBUGGING SYMBOL: {symbol}")
        
        # Step 1: Check if in universe
        universe = self.read_universe()
        if symbol not in universe:
            print(f"❌ {symbol} not in universe file")
            return None
        print(f"✅ {symbol} found in universe")
        
        # Step 2: Try to get Polygon data
        try:
            # Get current price data
            async with httpx.AsyncClient() as client:
                poly_url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?apikey={self.polygon_api_key}"
                response = await client.get(poly_url)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    if results:
                        price_data = results[0]
                        print(f"✅ {symbol} Polygon data: Price=${price_data.get('c')}, Volume={price_data.get('v'):,}")
                    else:
                        print(f"❌ {symbol} No results in Polygon response")
                        return None
                else:
                    print(f"❌ {symbol} Polygon API error: {response.status_code}")
                    return None
        except Exception as e:
            print(f"❌ {symbol} Polygon fetch failed: {e}")
            return None
        
        # Step 3: Get historical data for analysis
        try:
            bars = await self._daily_bars(None, symbol, limit=60)
            if len(bars) < 30:
                print(f"❌ {symbol} Insufficient historical data: {len(bars)} bars")
                return None
            print(f"✅ {symbol} Historical data: {len(bars)} bars")
            
            # Calculate key metrics
            current_price = bars[-1]['c']
            current_volume = bars[-1]['v']
            avg_volume_20d = sum(bar['v'] for bar in bars[-20:]) / 20
            volume_spike = current_volume / avg_volume_20d if avg_volume_20d > 0 else 0
            
            print(f"📊 {symbol} Metrics:")
            print(f"   Price: ${current_price:.2f}")
            print(f"   Volume: {current_volume:,}")
            print(f"   20D Avg Volume: {avg_volume_20d:,.0f}")
            print(f"   Volume Spike: {volume_spike:.2f}x")
            
            return {
                'symbol': symbol,
                'price': current_price,
                'volume_spike': volume_spike,
                'bars': len(bars)
            }
            
        except Exception as e:
            print(f"❌ {symbol} Analysis failed: {e}")
            return None

async def run_debug_discovery():
    """Run full discovery with debug output"""
    print("🚀 STARTING DEBUG DISCOVERY PIPELINE")
    print("=" * 60)
    
    debug_service = DebugDiscoveryService()
    
    # Test specific symbols
    test_symbols = ['ANTE', 'AAPL', 'TSLA', 'UP', 'NAK']
    
    for symbol in test_symbols:
        result = await debug_service.debug_single_symbol(symbol)
        if result:
            print(f"✅ {symbol} passed initial filters")
        else:
            print(f"❌ {symbol} failed initial filters")
        print("-" * 40)
    
    print("\n🔍 RUNNING FULL PIPELINE ON UNIVERSE...")
    
    # Run full discovery
    try:
        universe = debug_service.read_universe()
        print(f"📊 Starting with {len(universe)} symbols in universe")
        
        # Batch process symbols
        batch_size = 20
        processed = 0
        found_candidates = []
        
        for i in range(0, min(100, len(universe)), batch_size):  # Limit to first 100 for debug
            batch = universe[i:i+batch_size]
            print(f"🔄 Processing batch {i//batch_size + 1}: {batch}")
            
            for symbol in batch:
                try:
                    result = await debug_service.debug_single_symbol(symbol)
                    if result and result.get('volume_spike', 0) > 2.0:
                        found_candidates.append(result)
                        print(f"⭐ CANDIDATE FOUND: {symbol} (volume spike: {result.get('volume_spike', 0):.2f}x)")
                    processed += 1
                except Exception as e:
                    print(f"❌ Error processing {symbol}: {e}")
            
            if processed >= 100:  # Limit for debug
                break
        
        print(f"\n📊 DISCOVERY SUMMARY:")
        print(f"   Total processed: {processed}")
        print(f"   Candidates found: {len(found_candidates)}")
        print(f"   Candidates: {[c['symbol'] for c in found_candidates]}")
        
        return found_candidates
        
    except Exception as e:
        print(f"❌ Discovery pipeline failed: {e}")
        return []

if __name__ == "__main__":
    # Check for required env vars
    if not os.getenv("POLYGON_API_KEY"):
        print("❌ POLYGON_API_KEY environment variable required")
        sys.exit(1)
    
    print("🔍 AMC-TRADER Discovery Debug Pipeline")
    print(f"⏰ Started at: {datetime.now()}")
    
    # Run the debug discovery
    candidates = asyncio.run(run_debug_discovery())
    
    print(f"\n✅ Debug discovery complete!")
    print(f"📊 Final results: {len(candidates)} candidates found")