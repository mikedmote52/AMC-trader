#!/usr/bin/env python3
"""
Debug discovery system to see why no stocks are found
"""

import asyncio
import os
import sys
import httpx
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_market_snapshot():
    """Test getting market snapshot"""
    api_key = os.getenv('POLYGON_API_KEY')

    if not api_key:
        logger.error("No POLYGON_API_KEY found")
        return

    logger.info("Testing market snapshot...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get all US stocks snapshot
        snapshot_url = "https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers"

        try:
            response = await client.get(
                snapshot_url,
                params={
                    'apiKey': api_key,
                    'limit': 1000
                }
            )

            if response.status_code == 200:
                data = response.json()
                tickers = data.get('tickers', [])
                logger.info(f"✅ Got {len(tickers)} tickers from market snapshot")

                # Filter for stocks with good volume and price movement
                filtered = []
                for ticker_data in tickers[:100]:  # Check first 100
                    try:
                        ticker = ticker_data.get('ticker', '')
                        day = ticker_data.get('day', {})

                        if not day:
                            continue

                        price = day.get('c', 0)
                        volume = day.get('v', 0)
                        change_pct = ticker_data.get('todaysChangePerc', 0)

                        # Basic filters
                        if price < 0.50 or price > 50:
                            continue
                        if volume < 500000:
                            continue
                        if abs(change_pct) < 3:
                            continue

                        filtered.append({
                            'ticker': ticker,
                            'price': price,
                            'volume': volume,
                            'change_pct': change_pct
                        })

                        logger.info(f"  ✓ {ticker}: ${price:.2f}, Vol: {volume:,}, Change: {change_pct:.1f}%")

                    except Exception as e:
                        logger.debug(f"Error processing ticker: {e}")

                logger.info(f"\n📊 Summary: {len(filtered)} stocks passed initial filters")
                return filtered

            else:
                logger.error(f"API Error: {response.status_code}")
                logger.error(response.text)

        except Exception as e:
            logger.error(f"Request failed: {e}")

    return []

async def test_discovery_engine():
    """Test the discovery engine directly"""
    from routes.discovery_optimized import ExplosiveDiscoveryEngine

    logger.info("\nTesting discovery engine...")
    engine = ExplosiveDiscoveryEngine()

    # Test getting universe
    universe = await engine.get_market_universe()
    logger.info(f"Discovery engine found {len(universe)} candidates in universe")

    if universe:
        # Show first few
        for candidate in universe[:5]:
            ticker = candidate.get('ticker', '')
            price = candidate.get('day', {}).get('c', 0)
            volume = candidate.get('day', {}).get('v', 0)
            change = candidate.get('todaysChangePerc', 0)
            logger.info(f"  {ticker}: ${price:.2f}, Vol: {volume:,}, Change: {change:.1f}%")

    # Test full discovery
    logger.info("\nRunning full discovery...")
    result = await engine.run_discovery(limit=10)

    if result.get('success'):
        candidates = result.get('candidates', [])
        logger.info(f"✅ Discovery found {len(candidates)} final candidates")
        for c in candidates:
            logger.info(f"  {c.get('ticker')}: Score {c.get('total_score', 0)*100:.1f}%")
    else:
        logger.error(f"❌ Discovery failed: {result.get('error', 'Unknown error')}")

async def main():
    """Run all tests"""
    logger.info("🚀 Starting discovery debug tests...")
    logger.info(f"Time: {datetime.now()}")

    # Test market snapshot first
    stocks = await test_market_snapshot()

    if stocks:
        logger.info(f"\n✅ Market snapshot working - found {len(stocks)} active stocks")
    else:
        logger.warning("\n⚠️ No stocks found in market snapshot")

    # Test discovery engine
    await test_discovery_engine()

if __name__ == "__main__":
    asyncio.run(main())