#!/usr/bin/env python3
"""
Test Dynamic Universe System
"""

import os
import sys
import asyncio
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend/src'))

# Set environment for dynamic universe
os.environ["AMC_DYNAMIC_UNIVERSE"] = "true"

from jobs.discover import DiscoveryService

async def test_dynamic_universe():
    """Test the new dynamic universe loading"""
    
    print("🧪 TESTING DYNAMIC UNIVERSE SYSTEM")
    print("=" * 60)
    
    try:
        # Create discovery service
        discovery = DiscoveryService()
        
        # Test universe loading
        print("🌍 Loading universe...")
        universe = discovery.read_universe()
        
        print(f"✅ Universe loaded: {len(universe)} symbols")
        print(f"📊 First 20 symbols: {universe[:20]}")
        
        # Check for specific symbols
        test_symbols = ['ANTE', 'AMC', 'GME', 'SNDL', 'UP', 'NAK', 'AAPL']
        print(f"\n🎯 Checking for specific symbols:")
        for symbol in test_symbols:
            status = "✅" if symbol in universe else "❌"
            print(f"   {status} {symbol}")
        
        # Show some stats
        print(f"\n📊 UNIVERSE STATS:")
        print(f"   Total symbols: {len(universe):,}")
        print(f"   A-C symbols: {len([s for s in universe if s[0] in 'ABC'])}")
        print(f"   Unique starting letters: {len(set(s[0] for s in universe))}")
        
        return universe
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return []

if __name__ == "__main__":
    universe = asyncio.run(test_dynamic_universe())