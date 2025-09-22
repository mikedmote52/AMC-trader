#!/usr/bin/env python3
"""
Debug script to find why the unified discovery system is failing
and causing the fallback to inefficient individual API calls
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Set environment
os.environ['POLYGON_API_KEY'] = '1ORwpSzeOV20X6uaA8G3Zuxx7hLJ0KIC'
os.environ['REDIS_URL'] = 'redis://localhost:6379'

# Add backend path
backend_path = Path(__file__).parent / "backend" / "src"
sys.path.insert(0, str(backend_path))

async def debug_unified_discovery():
    """Test the unified discovery system to see why it's failing"""
    print("🔍 Debugging Unified Discovery System Failure")
    print("=" * 50)

    try:
        # Import and test unified discovery
        from discovery.unified_discovery import UnifiedDiscoverySystem
        print("✅ Successfully imported UnifiedDiscoverySystem")

        # Create instance
        discovery = UnifiedDiscoverySystem()
        print("✅ Successfully created discovery instance")

        # Test environment validation
        try:
            discovery.validate_environment()
            print("✅ Environment validation passed")
        except Exception as e:
            print(f"❌ Environment validation failed: {e}")
            return False

        # Test market universe loading
        try:
            print("🔄 Testing market universe loading...")
            universe = await discovery.get_market_universe()
            print(f"✅ Universe loaded successfully: {len(universe)} stocks")

            if len(universe) > 1000:
                print(f"🎉 SUCCESS: Large universe size indicates bulk API is working!")
                return True
            else:
                print(f"⚠️  Small universe size ({len(universe)}) - may be using fallback method")
                return False

        except Exception as e:
            print(f"❌ Market universe loading failed: {e}")
            print(f"📝 Error type: {type(e).__name__}")
            print(f"📝 Error details: {str(e)}")
            return False

    except Exception as e:
        print(f"❌ Failed to import or create unified discovery: {e}")
        return False

async def test_discovery_job():
    """Test the actual discovery job that's failing"""
    print("\n📋 Testing Discovery Job")
    print("=" * 25)

    try:
        from jobs.discovery_job import run_discovery_job
        print("✅ Successfully imported run_discovery_job")

        result = await run_discovery_job(limit=10)
        print(f"✅ Discovery job completed")
        print(f"📊 Status: {result.get('status')}")
        print(f"📊 Engine: {result.get('engine', 'unknown')}")
        print(f"📊 Count: {result.get('count', 0)}")
        print(f"📊 Universe size: {result.get('universe_size', 0)}")

        if "Efficient" in result.get('engine', ''):
            print("🎉 SUCCESS: Using efficient unified discovery system!")
            return True
        else:
            print("❌ FAILURE: Using fallback system (individual API calls)")
            return False

    except Exception as e:
        print(f"❌ Discovery job test failed: {e}")
        return False

async def main():
    """Run all debug tests"""
    print("🐛 AMC-TRADER Discovery System Debug")
    print("=" * 40)

    # Test 1: Unified Discovery System
    unified_ok = await debug_unified_discovery()

    # Test 2: Discovery Job
    job_ok = await test_discovery_job()

    # Summary
    print("\n📊 Debug Summary")
    print("=" * 17)

    if unified_ok and job_ok:
        print("🎉 SUCCESS: System is working correctly!")
        print("✅ Using efficient bulk API calls")
    elif unified_ok and not job_ok:
        print("🔧 ISSUE: Unified system works but job is not using it")
        print("💡 Solution: Fix discovery job routing")
    elif not unified_ok:
        print("❌ CRITICAL: Unified discovery system is broken")
        print("💡 Solution: Fix unified discovery implementation")
    else:
        print("❓ MIXED RESULTS: Need further investigation")

if __name__ == "__main__":
    asyncio.run(main())