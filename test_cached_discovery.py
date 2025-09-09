#!/usr/bin/env python3
"""
Test the cached discovery system locally
"""
import sys
import os
import asyncio
import time

# Add backend to path
sys.path.insert(0, os.path.join(os.getcwd(), 'backend', 'src'))

async def test_universe_loader():
    """Test the universe loader"""
    print("🧪 Testing Universe Loader...")
    
    try:
        from backend.src.services.universe_loader import load_universe
        
        print("Loading universe...")
        start_time = time.time()
        filtered_stocks, stats = await load_universe()
        elapsed = time.time() - start_time
        
        print(f"✅ Universe loaded in {elapsed:.1f}s")
        print(f"   Total stocks: {stats.get('total_fetched', 0)}")
        print(f"   After filters: {len(filtered_stocks)}")
        print(f"   Sample stocks: {[s[0] for s in filtered_stocks[:10]]}")
        
        # Ensure coverage tripwire works
        if len(filtered_stocks) < 100:
            print("⚠️  WARNING: Very few stocks - check filters")
        else:
            print(f"✅ Good coverage: {len(filtered_stocks)} stocks")
            
        return True
        
    except Exception as e:
        print(f"❌ Universe loader test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_constants():
    """Test constants and configuration"""
    print("\n🧪 Testing Constants...")
    
    try:
        from backend.src.constants import (
            UNIVERSE_MIN_EXPECTED, PRICE_MAX, MIN_DOLLAR_VOL_M,
            is_fund_symbol, validate_environment
        )
        
        print(f"✅ Configuration loaded:")
        print(f"   Universe minimum: {UNIVERSE_MIN_EXPECTED}")
        print(f"   Price max: ${PRICE_MAX}")
        print(f"   Min volume: ${MIN_DOLLAR_VOL_M}M")
        
        # Test fund detection
        test_symbols = ["AAPL", "SPY", "QQQ", "TSLA", "SQQQ"]
        for symbol in test_symbols:
            is_fund = is_fund_symbol(symbol)
            print(f"   {symbol}: {'FUND' if is_fund else 'STOCK'}")
        
        # Test environment validation
        try:
            validate_environment()
            print("✅ Environment validation passed")
        except Exception as e:
            print(f"⚠️  Environment issue: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ Constants test failed: {e}")
        return False

def test_job_import():
    """Test job imports"""
    print("\n🧪 Testing Job Import...")
    
    try:
        from backend.src.jobs.discovery_job import run_discovery_job
        print("✅ Discovery job imported successfully")
        print(f"   Function: {run_discovery_job}")
        return True
        
    except Exception as e:
        print(f"❌ Job import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    print("🚀 Testing Cached Discovery System")
    print("=" * 50)
    
    tests = [
        test_constants(),
        test_universe_loader(),
    ]
    
    results = await asyncio.gather(*tests, return_exceptions=True)
    
    # Test job import (synchronous)
    job_result = test_job_import()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    
    passed = sum(1 for r in results + [job_result] if r is True)
    total = len(results) + 1
    
    print(f"   Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All tests passed - system ready for deployment!")
        return True
    else:
        print("❌ Some tests failed - check errors above")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)