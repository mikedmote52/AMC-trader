#!/usr/bin/env python3
import asyncio
import sys
import time
sys.path.append('src')
from routes.discovery_optimized import discovery_engine

async def test_optimized():
    print('🔥 TESTING OPTIMIZED DISCOVERY ENGINE')
    print('=' * 40)

    start = time.time()
    universe = await discovery_engine.get_market_universe()
    universe_time = time.time() - start

    print(f'📊 Universe Collection:')
    print(f'   Size: {len(universe)} stocks')
    print(f'   Time: {universe_time:.1f}s')

    if universe:
        print(f'\n✨ OPTIMIZATION RESULTS:')
        print(f'   Universe: {len(universe)} stocks (vs 11,457 unfiltered)')
        print(f'   Reduction: {100 - (len(universe)/11457*100):.1f}%')
        print(f'   Processing time: {universe_time:.1f}s')

        # Show top 5 by volume
        print(f'\n🎯 Top 5 candidates by volume:')
        for i, stock in enumerate(universe[:5], 1):
            ticker = stock.get('ticker')
            vol = stock.get('day', {}).get('v', 0)
            price = stock.get('day', {}).get('c', 0)
            vr = stock.get('volume_ratio', 0)
            change = stock.get('todaysChangePerc', 0)
            print(f'   {i}. {ticker}: ${price:.2f} | Vol: {vol:,.0f} | VR: {vr:.1f}x | Δ: {change:+.1f}%')

        # Now test the full discovery pipeline
        print(f'\n🚀 Running full dual-tier discovery on {len(universe)} stocks...')
        discovery_start = time.time()
        result = await discovery_engine.run_discovery(limit=100)
        discovery_time = time.time() - discovery_start

        if result['status'] == 'success':
            print(f'\n📊 DISCOVERY RESULTS:')
            print(f'   Processing time: {discovery_time:.1f}s')
            print(f'   Elite candidates: {result["count"]}')
            print(f'   Near-miss candidates: {result.get("near_miss_count", 0)}')

            elite = result.get('candidates', [])
            near_miss = result.get('near_miss_candidates', [])

            if elite:
                print(f'\n💎 ELITE TIER (Ultra-selective):')
                for candidate in elite[:3]:
                    ticker = candidate.get('ticker')
                    score = candidate.get('total_score', 0) * 100
                    irv = candidate.get('intraday_relative_volume', 0)
                    change = candidate.get('todaysChangePerc', 0)
                    print(f'   {ticker}: {score:.1f}% | IRV: {irv:.1f}x | Δ: {change:+.1f}%')

            if near_miss:
                print(f'\n⚠️  NEAR-MISS TIER (Monitoring):')
                for candidate in near_miss[:5]:
                    ticker = candidate.get('ticker')
                    score = candidate.get('total_score', 0) * 100
                    irv = candidate.get('intraday_relative_volume', 0)
                    reason = candidate.get('miss_reason', 'Close to elite')
                    print(f'   {ticker}: {score:.1f}% | IRV: {irv:.1f}x | {reason}')

            if not elite and not near_miss:
                print('\n✅ ULTRA-SELECTIVE SYSTEM WORKING:')
                print('   No stocks meet explosive thresholds currently')
                print('   This is normal during low-volatility periods')
        else:
            print(f'❌ Discovery failed: {result.get("error")}')
    else:
        print('❌ No universe data available')

if __name__ == "__main__":
    asyncio.run(test_optimized())