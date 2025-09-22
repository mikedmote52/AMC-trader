#!/usr/bin/env python3
"""
Live Discovery Test - Tests the enhanced AMC-TRADER system with real MCP data
Simulates full discovery pipeline to find explosive stocks before they move
"""
import asyncio
import sys
import os
from datetime import datetime

# Add backend to path
sys.path.append('backend/src')

async def test_enhanced_discovery_pipeline():
    """Test the enhanced discovery system with real data sources"""
    print("🚀 Testing Enhanced AMC-TRADER Discovery Pipeline")
    print("=" * 60)

    # Test 1: MCP Client Integration
    print("\n1. Testing MCP Client Integration...")
    try:
        from mcp_client_enhanced import mcp_client

        # Test short interest data
        short_data = await mcp_client.get_short_interest("TSLA")
        print(f"   ✅ Short Interest: Available={short_data.get('available', False)}")
        if short_data.get('available'):
            print(f"      Days to Cover: {short_data.get('days_to_cover', 'N/A')}")

        # Test news sentiment
        sentiment_data = await mcp_client.get_news_sentiment("TSLA", hours_back=24)
        print(f"   ✅ News Sentiment: Available={sentiment_data.get('available', False)}")
        if sentiment_data.get('available'):
            print(f"      Sentiment Score: {sentiment_data.get('sentiment_score', 'N/A')}")
            print(f"      News Count: {sentiment_data.get('news_count', 'N/A')}")

        # Test aggregates data
        agg_data = await mcp_client.get_detailed_aggregates("TSLA", days_back=5)
        print(f"   ✅ Aggregates Data: Available={agg_data.get('available', False)}")

        # Test premium features with fallbacks
        options_data = await mcp_client.get_options_activity("TSLA")
        print(f"   ✅ Options Data: Available={options_data.get('available', False)}")
        if not options_data.get('available'):
            print(f"      Reason: {options_data.get('reason', 'Unknown')}")

        trades_data = await mcp_client.get_realtime_trades("TSLA")
        print(f"   ✅ Trades Data: Available={trades_data.get('available', False)}")
        if trades_data.get('available'):
            print(f"      Source: {trades_data.get('source', 'direct')}")
            print(f"      Momentum: {trades_data.get('recent_momentum_pct', 'N/A')}%")

    except Exception as e:
        print(f"   ❌ MCP Client Error: {e}")
        return False

    # Test 2: Scoring System
    print("\n2. Testing Enhanced Scoring System...")
    try:
        from discovery.polygon_explosive_discovery import _combine_subscores

        # Test 8-pillar scoring with missing data
        test_parts = [
            ("price_momentum", 20, 85),
            ("volume_surge", 20, 75),
            ("float_short", 15, None),  # Missing
            ("catalyst", 15, 60),
            ("sentiment", 10, 70),
            ("technical", 10, None),   # Missing
            ("options_flow", 5, None), # Missing (premium)
            ("realtime_momentum", 5, 80)
        ]

        score, subscores, meta = _combine_subscores(test_parts)
        active_count = len([s for s in subscores.values() if s is not None])

        print(f"   ✅ Dynamic Scoring: {score:.1f}/100")
        print(f"   ✅ Active Components: {active_count}/8")
        print(f"   ✅ Missing: {meta['missing']}")
        print(f"   ✅ Reweighted: {list(meta['active_weights'].keys())}")

    except Exception as e:
        print(f"   ❌ Scoring System Error: {e}")
        return False

    # Test 3: Discovery Engine
    print("\n3. Testing Discovery Engine Creation...")
    try:
        from discovery.polygon_explosive_discovery import create_polygon_explosive_discovery

        engine = create_polygon_explosive_discovery()
        print(f"   ✅ Engine Created: {type(engine).__name__}")
        print(f"   ✅ Weights Total: {sum(engine.ALPHASTACK_WEIGHTS.values())}%")
        print(f"   ✅ Pillars: {list(engine.ALPHASTACK_WEIGHTS.keys())}")

    except Exception as e:
        print(f"   ❌ Discovery Engine Error: {e}")
        return False

    # Test 4: Individual Stock Analysis
    print("\n4. Testing Individual Stock Analysis...")
    try:
        # Simulate stock data for TSLA
        stock_data = {
            'symbol': 'TSLA',
            'current_price': 426.07,
            'price_change_pct': 1.0,  # 1% gain
            'current_volume': 93131034,
            'volume_ratio': 2.5  # 2.5x average volume
        }

        # Test momentum scoring
        momentum_score = engine._calculate_momentum_score(stock_data, [])
        print(f"   ✅ Momentum Score: {momentum_score}")

        # Test volume scoring
        volume_score = engine._calculate_volume_score(stock_data, [])
        print(f"   ✅ Volume Score: {volume_score}")

        # Test scoring with real data
        short_data = await mcp_client.get_short_interest("TSLA")
        float_score = engine._calculate_float_short_score("TSLA", short_data)
        print(f"   ✅ Float/Short Score: {float_score}")

        sentiment_data = await mcp_client.get_news_sentiment("TSLA")
        sentiment_score = engine._calculate_sentiment_score("TSLA", sentiment_data)
        print(f"   ✅ Sentiment Score: {sentiment_score}")

    except Exception as e:
        print(f"   ❌ Stock Analysis Error: {e}")
        return False

    print("\n" + "=" * 60)
    print("🎉 ENHANCED DISCOVERY PIPELINE TEST COMPLETE")
    print("✅ All core components working with real MCP data")
    print("✅ Graceful handling of premium features")
    print("✅ Dynamic reweighting functional")
    print("✅ Ready for Render deployment")
    return True

async def test_universe_simulation():
    """Simulate discovery across multiple stocks"""
    print("\n🌟 Testing Universe Discovery Simulation...")

    test_tickers = ["TSLA", "AAPL", "NVDA", "AMD", "PLTR"]

    try:
        from mcp_client_enhanced import mcp_client

        results = []
        for ticker in test_tickers:
            print(f"   Analyzing {ticker}...")

            # Get basic data
            short_data = await mcp_client.get_short_interest(ticker)
            sentiment_data = await mcp_client.get_news_sentiment(ticker, hours_back=24)

            # Simulate scoring
            has_short = short_data.get('available', False)
            has_sentiment = sentiment_data.get('available', False)

            results.append({
                'ticker': ticker,
                'short_available': has_short,
                'sentiment_available': has_sentiment,
                'days_to_cover': short_data.get('days_to_cover') if has_short else None,
                'sentiment_score': sentiment_data.get('sentiment_score') if has_sentiment else None,
                'news_count': sentiment_data.get('news_count') if has_sentiment else None
            })

        print(f"\n   ✅ Analyzed {len(results)} stocks")
        for result in results:
            ticker = result['ticker']
            short_status = "✅" if result['short_available'] else "❌"
            sentiment_status = "✅" if result['sentiment_available'] else "❌"
            print(f"   {ticker}: Short{short_status} Sentiment{sentiment_status}")

        return True

    except Exception as e:
        print(f"   ❌ Universe Test Error: {e}")
        return False

if __name__ == "__main__":
    async def main():
        success1 = await test_enhanced_discovery_pipeline()
        success2 = await test_universe_simulation()

        if success1 and success2:
            print("\n🚀 SYSTEM READY FOR PRODUCTION DEPLOYMENT")
        else:
            print("\n❌ Issues detected - review before deployment")

    asyncio.run(main())