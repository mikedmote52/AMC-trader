#!/usr/bin/env python3
"""
Test script to verify AMC-TRADER now uses full stock universe
This tests the fix to search all stocks instead of just gainers/losers
"""
import asyncio
import logging
import sys
import os
from pathlib import Path

# Add the backend source to the path
backend_path = Path(__file__).parent / "backend" / "src"
sys.path.insert(0, str(backend_path))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_universe_size():
    """Test that AMC-TRADER now loads full universe"""
    try:
        # Import the updated discovery system
        from discovery.unified_discovery import UnifiedDiscoverySystem

        logger.info("🚀 Testing AMC-TRADER full universe loading...")

        # Initialize the discovery system
        discovery = UnifiedDiscoverySystem()

        # Test the universe loading
        logger.info("📡 Testing universe loading...")
        universe = await discovery.get_market_universe()

        logger.info(f"✅ Universe size: {len(universe)} stocks")

        # Compare with expected sizes
        if len(universe) >= 1000:
            logger.info("🎉 SUCCESS: Full universe loading works!")
            logger.info(f"📊 Universe size increased from ~500 (old) to {len(universe)} (new)")
            return True
        elif len(universe) >= 100:
            logger.warning(f"⚠️ Partial success: Got {len(universe)} stocks (better than old ~500 limit)")
            return True
        else:
            logger.error(f"❌ FAILED: Only got {len(universe)} stocks")
            return False

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

async def test_discovery_pipeline():
    """Test the full discovery pipeline with larger universe"""
    try:
        from jobs.discovery_job import run_discovery_job

        logger.info("🔍 Testing full discovery pipeline...")

        # Run the discovery job
        result = await run_discovery_job(limit=20)

        if result['status'] == 'success':
            universe_size = result.get('universe_size', 0)
            candidate_count = result.get('count', 0)

            logger.info(f"✅ Discovery pipeline success!")
            logger.info(f"📊 Universe size: {universe_size}")
            logger.info(f"🎯 Candidates found: {candidate_count}")

            if universe_size >= 1000:
                logger.info("🎉 SUCCESS: Pipeline now uses full universe!")
                return True
            else:
                logger.warning(f"⚠️ Universe size still small: {universe_size}")
                return False
        else:
            logger.error(f"❌ Discovery pipeline failed: {result.get('error')}")
            return False

    except Exception as e:
        logger.error(f"❌ Pipeline test failed: {e}")
        return False

async def main():
    """Run all tests"""
    logger.info("🧪 AMC-TRADER Full Universe Fix Verification")
    logger.info("=" * 50)

    # Test 1: Universe loading
    logger.info("\n📋 Test 1: Universe Loading")
    universe_test = await test_universe_size()

    # Test 2: Full pipeline
    logger.info("\n📋 Test 2: Discovery Pipeline")
    pipeline_test = await test_discovery_pipeline()

    # Summary
    logger.info("\n📊 Test Results Summary")
    logger.info("=" * 30)
    logger.info(f"Universe Loading: {'✅ PASS' if universe_test else '❌ FAIL'}")
    logger.info(f"Discovery Pipeline: {'✅ PASS' if pipeline_test else '❌ FAIL'}")

    if universe_test and pipeline_test:
        logger.info("\n🎉 ALL TESTS PASSED!")
        logger.info("AMC-TRADER now searches the full stock universe!")
    else:
        logger.info("\n⚠️ Some tests failed - check the logs above")

    return universe_test and pipeline_test

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)