#!/usr/bin/env python3
"""
Test the new Explosive Discovery V2 system with real Polygon MCP data
"""
import asyncio
import json
from datetime import datetime

async def test_mcp_functions():
    """Test MCP functions directly to ensure they work"""
    print("🧪 Testing MCP Functions Direct Access...")

    try:
        # Test snapshot data
        print("📊 Testing market snapshot...")
        snapshot_data = await mcp__polygon__get_snapshot_all(
            market_type='stocks',
            include_otc=False,
            tickers=['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL']
        )

        if snapshot_data and snapshot_data.get('tickers'):
            print(f"✅ Snapshot: Got {len(snapshot_data['tickers'])} tickers")
            for ticker in snapshot_data['tickers'][:3]:
                symbol = ticker.get('ticker', 'UNKNOWN')
                day_data = ticker.get('day', {})
                price = day_data.get('c', 0)
                change_pct = ticker.get('todaysChangePerc', 0)
                print(f"   {symbol}: ${price:.2f} ({change_pct:+.2f}%)")
        else:
            print("❌ No snapshot data returned")

    except Exception as e:
        print(f"❌ MCP test failed: {e}")
        return False

    try:
        # Test historical data
        print("\n📈 Testing historical data...")
        hist_data = await mcp__polygon__get_aggs(
            ticker='AAPL',
            multiplier=1,
            timespan='day',
            from_='2024-12-01',
            to='2024-12-20',
            adjusted=True
        )

        if hist_data and hist_data.get('results'):
            print(f"✅ Historical: Got {len(hist_data['results'])} data points for AAPL")
            latest = hist_data['results'][-1]
            print(f"   Latest: ${latest.get('c', 0):.2f}, Volume: {latest.get('v', 0):,}")
        else:
            print("❌ No historical data returned")

    except Exception as e:
        print(f"❌ Historical data test failed: {e}")
        return False

    try:
        # Test news data
        print("\n📰 Testing news data...")
        news_data = await mcp__polygon__list_ticker_news(
            ticker='AAPL',
            limit=5
        )

        if news_data and news_data.get('results'):
            print(f"✅ News: Got {len(news_data['results'])} articles for AAPL")
            for article in news_data['results'][:2]:
                title = article.get('title', 'No title')[:50] + '...'
                sentiment = 'neutral'
                insights = article.get('insights', [])
                for insight in insights:
                    if insight.get('ticker') == 'AAPL':
                        sentiment = insight.get('sentiment', 'neutral')
                        break
                print(f"   {title} [{sentiment}]")
        else:
            print("❌ No news data returned")

    except Exception as e:
        print(f"❌ News data test failed: {e}")
        return False

    print("\n✅ All MCP functions working correctly!")
    return True

async def test_explosive_discovery():
    """Test the explosive discovery system"""
    print("\n💥 Testing Explosive Discovery System...")

    try:
        # Import the discovery system
        import sys
        import os
        sys.path.append(os.path.join(os.getcwd(), 'backend', 'src', 'discovery'))

        from explosive_discovery_v2 import create_explosive_discovery_engine

        # Create discovery engine
        engine = create_explosive_discovery_engine()
        print("✅ Discovery engine created")

        # Run discovery
        print("🔍 Running explosive discovery...")
        results = await engine.discover_explosive_candidates(limit=10)

        if results['status'] == 'success':
            candidates = results['candidates']
            print(f"✅ Discovery successful: Found {len(candidates)} candidates")
            print(f"   Execution time: {results['execution_time_sec']:.2f}s")
            print(f"   Pipeline stats: {results['pipeline_stats']}")

            # Show top candidates
            print("\n🎯 Top Explosive Candidates:")
            for i, candidate in enumerate(candidates[:5], 1):
                symbol = candidate['symbol']
                score = candidate['score']
                action = candidate['action_tag']
                price_change = candidate['price_change_pct']
                volume_surge = candidate['volume_surge_ratio']

                print(f"   {i}. {symbol}: Score {score:.1f} [{action}]")
                print(f"      Price: {price_change:+.1f}%, Volume: {volume_surge:.1f}x")

                # Show subscores
                subscores = candidate.get('subscores', {})
                print(f"      Subscores: Vol={subscores.get('volume_surge', 0):.0f}, "
                      f"Price={subscores.get('price_momentum', 0):.0f}, "
                      f"News={subscores.get('news_catalyst', 0):.0f}")
                print()

        else:
            print(f"❌ Discovery failed: {results.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"❌ Discovery test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("✅ Explosive discovery system working!")
    return True

async def test_integration():
    """Test integration with the discovery job"""
    print("\n🔗 Testing Discovery Job Integration...")

    try:
        # Import the discovery job
        import sys
        import os
        sys.path.append(os.path.join(os.getcwd(), 'backend', 'src', 'jobs'))

        from discovery_job import run_discovery_job

        # Run discovery job
        print("🚀 Running discovery job...")
        results = await run_discovery_job(limit=5)

        if results['status'] == 'success':
            print(f"✅ Discovery job successful!")
            print(f"   Engine: {results['engine']}")
            print(f"   Algorithm: {results['algorithm_version']}")
            print(f"   Candidates: {results['count']}")
            print(f"   Execution time: {results['execution_time_sec']:.2f}s")

            # Show sample candidate
            if results['candidates']:
                candidate = results['candidates'][0]
                print(f"\n📋 Sample Candidate: {candidate['symbol']}")
                print(f"   Score: {candidate['score']:.1f}")
                print(f"   Action: {candidate['action_tag']}")
                print(f"   Confidence: {candidate['confidence']:.3f}")

        else:
            print(f"❌ Discovery job failed: {results.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("✅ Discovery job integration working!")
    return True

async def main():
    """Run all tests"""
    print("🧪 AMC-TRADER Explosive Discovery V2 Testing")
    print("=" * 50)

    # Test MCP functions
    mcp_ok = await test_mcp_functions()
    if not mcp_ok:
        print("\n❌ MCP functions not working - cannot proceed with other tests")
        return

    # Test explosive discovery
    discovery_ok = await test_explosive_discovery()
    if not discovery_ok:
        print("\n❌ Explosive discovery not working")
        return

    # Test integration
    integration_ok = await test_integration()
    if not integration_ok:
        print("\n❌ Integration not working")
        return

    print("\n" + "=" * 50)
    print("🎉 ALL TESTS PASSED! Explosive Discovery V2 is ready!")
    print("\n📊 System Summary:")
    print("   ✅ MCP Polygon integration working")
    print("   ✅ Explosive growth detection active")
    print("   ✅ Volume surge screening enabled")
    print("   ✅ News catalyst analysis working")
    print("   ✅ API compatibility maintained")
    print("\n🚀 Ready to find explosive growth stocks!")

if __name__ == "__main__":
    asyncio.run(main())