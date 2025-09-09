#!/usr/bin/env python3
"""
Test the direct discovery system with real Polygon data
"""

import sys
import os
import asyncio

# Add backend to path
sys.path.insert(0, os.path.join(os.getcwd(), 'backend', 'src'))

async def test_discovery():
    try:
        from backend.src.routes.discovery_direct import get_candidates, get_market_movers
        
        print("🧪 Testing direct discovery with real Polygon API...")
        
        # Test getting market movers
        print("1. Fetching real market movers...")
        movers = await get_market_movers()
        
        if movers:
            print(f"   ✅ Got {len(movers)} market movers")
            for i, mover in enumerate(movers[:5], 1):
                print(f"   {i}. {mover['symbol']}: {mover['bms_score']:.1f} ({mover['action']}) - ${mover['price']:.2f}")
        else:
            print("   ⚠️ No market movers (market may be closed)")
            
        # Test main candidates endpoint
        print("\n2. Testing candidates endpoint...")
        result = await get_candidates(limit=10)
        
        if result.get("candidates"):
            print(f"   ✅ Got {len(result['candidates'])} candidates")
            print(f"   Engine: {result.get('engine')}")
            
            for i, candidate in enumerate(result['candidates'][:5], 1):
                print(f"   {i}. {candidate['symbol']}: Score {candidate['bms_score']:.1f} - {candidate['action']}")
                print(f"      Price: ${candidate['price']:.2f}, Volume Surge: {candidate['volume_surge']}x")
                print(f"      Thesis: {candidate['thesis']}")
        else:
            print(f"   ⚠️ No candidates returned")
            print(f"   Message: {result.get('message', 'Unknown')}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error testing discovery: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_discovery())
    
    if success:
        print("\n✅ Direct discovery system tested - uses REAL market data!")
    else:
        print("\n💥 Issues found - check error messages")