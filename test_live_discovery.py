#!/usr/bin/env python3
"""
Live Discovery Test for AMC-TRADER UI
"""
import asyncio
import sys
import os
import json
from datetime import datetime

# Add backend paths
sys.path.append('backend/src')
sys.path.append('backend/src/agents')

async def test_live_discovery():
    """Run live discovery test with real market data"""
    try:
        from alphastack_v4 import DiscoveryOrchestrator

        print("🔍 AMC-TRADER Live Discovery Test")
        print("=" * 50)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Initialize discovery engine
        orchestrator = DiscoveryOrchestrator()

        # Run discovery with hybrid_v1 strategy
        print("Running AlphaStack 4.1 Discovery (Hybrid V1)...")
        result = await orchestrator.discover_opportunities(limit=15)

        print(f"✅ Discovery Status: {result.get('status', 'unknown')}")
        print(f"📊 Engine: {result.get('engine', 'unknown')}")
        print(f"🎯 Candidates Found: {result.get('count', 0)}")
        print(f"⏱️  Execution Time: {result.get('execution_time_sec', 0):.2f}s")
        print()

        candidates = result.get('candidates', [])

        if candidates:
            print("🚀 TOP MARKET OPPORTUNITIES")
            print("=" * 50)

            trade_ready = [c for c in candidates if c.get('action_tag') == 'trade_ready']
            watchlist = [c for c in candidates if c.get('action_tag') == 'watchlist']

            if trade_ready:
                print("🟢 TRADE READY (Immediate Execution):")
                for i, candidate in enumerate(trade_ready[:5], 1):
                    symbol = candidate.get('symbol', 'N/A')
                    score = candidate.get('composite_score', 0)
                    price = candidate.get('price', 0)
                    volume = candidate.get('volume', 0)

                    print(f"  {i}. {symbol}")
                    print(f"     Score: {score:.1f}% | Price: ${price:.2f} | Volume: {volume:,}")

                    if 'subscores' in candidate:
                        subs = candidate['subscores']
                        vol_score = subs.get('volume_momentum', 0) * 100
                        squeeze_score = subs.get('squeeze', 0) * 100
                        catalyst_score = subs.get('catalyst', 0) * 100
                        print(f"     Volume: {vol_score:.0f}% | Squeeze: {squeeze_score:.0f}% | Catalyst: {catalyst_score:.0f}%")

                    if 'thesis' in candidate:
                        print(f"     💡 {candidate['thesis'][:80]}...")
                    print()

            if watchlist:
                print("🟡 WATCHLIST (Monitor for Entry):")
                for i, candidate in enumerate(watchlist[:3], 1):
                    symbol = candidate.get('symbol', 'N/A')
                    score = candidate.get('composite_score', 0)
                    price = candidate.get('price', 0)

                    print(f"  {i}. {symbol} - Score: {score:.1f}% | Price: ${price:.2f}")
                print()

            # Market Analysis Summary
            pipeline_stats = result.get('pipeline_stats', {})
            print("📈 MARKET ANALYSIS SUMMARY")
            print("=" * 30)
            print(f"Universe Scanned: {pipeline_stats.get('universe_size', 'N/A')}")
            print(f"Pass Rate: {pipeline_stats.get('pass_rate_pct', 'N/A')}%")
            print(f"Avg Score: {pipeline_stats.get('avg_score', 'N/A')}")
            print(f"Strategy: Hybrid V1 (Enhanced Multi-Factor)")

        else:
            print("⚠️  No opportunities detected in current market conditions")
            print("   - All candidates filtered out by quality gates")
            print("   - Consider checking during higher volatility periods")

        return result

    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("   Please ensure all dependencies are installed")
        return None
    except Exception as e:
        print(f"❌ Discovery Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(test_live_discovery())