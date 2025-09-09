#!/usr/bin/env python3
"""
Test the simple discovery system locally
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.getcwd(), 'backend', 'src'))

async def test_discovery():
    try:
        from backend.src.routes.discovery_simple import get_candidates, get_trade_ready_candidates
        
        print("🧪 Testing simple discovery system...")
        
        # Test main candidates endpoint
        print("1. Testing candidates endpoint...")
        result = await get_candidates(limit=5)
        
        if result.get("candidates"):
            print(f"   ✅ Got {len(result['candidates'])} candidates")
            
            for i, candidate in enumerate(result['candidates'][:3], 1):
                print(f"   {i}. {candidate['symbol']}: {candidate['bms_score']:.1f} ({candidate['action']})")
                
        else:
            print("   ❌ No candidates returned")
            return False
            
        # Test trade-ready filter
        print("2. Testing trade-ready filter...")
        trade_ready = await get_trade_ready_candidates(limit=10)
        
        if trade_ready.get("candidates"):
            print(f"   ✅ Got {len(trade_ready['candidates'])} trade-ready candidates")
            for candidate in trade_ready['candidates']:
                print(f"   - {candidate['symbol']}: {candidate['bms_score']:.1f}")
        else:
            print("   ❌ No trade-ready candidates")
            
        print("\n✅ Simple discovery system working!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing discovery: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(test_discovery())
    
    if success:
        print("\n🚀 Ready to deploy - discovery system will return actual stocks!")
    else:
        print("\n💥 Issues found - needs debugging")