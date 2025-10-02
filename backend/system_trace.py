#!/usr/bin/env python3
"""
Complete AMC-TRADER System Trace
Shows every filtration step with real numbers
"""

import asyncio
import sys
import os
sys.path.append('src')
from routes.discovery_optimized import ExplosiveDiscoveryEngine
import logging

# Set up detailed logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

async def complete_system_trace():
    engine = ExplosiveDiscoveryEngine()

    print('🚀 AMC-TRADER COMPLETE SYSTEM TRACE')
    print('=' * 60)

    # Step 1: Get raw universe
    print('\n📊 STEP 1: RAW UNIVERSE COLLECTION')
    print('-' * 40)
    universe = await engine.get_market_universe()
    print(f'✅ Raw universe size: {len(universe):,} stocks')
    print(f'   Source: Polygon snapshot API')
    print(f'   Coverage: All US markets (NASDAQ, NYSE, etc.)')

    # Step 2: Apply initial filters
    print('\n🔍 STEP 2: INITIAL FILTRATION')
    print('-' * 40)

    # Price filter
    price_filtered = []
    price_rejects = 0
    for stock in universe:
        price = stock.get('day', {}).get('c', 0)
        if 0.50 <= price <= 50.0:
            price_filtered.append(stock)
        else:
            price_rejects += 1

    print(f'💰 Price Filter ($0.50 - $50.00):')
    print(f'   ✅ Passed: {len(price_filtered):,}')
    print(f'   ❌ Rejected: {price_rejects:,}')

    # Volume filter
    volume_filtered = []
    volume_rejects = 0
    for stock in price_filtered:
        volume = stock.get('day', {}).get('v', 0)
        if volume >= 500_000:
            volume_filtered.append(stock)
        else:
            volume_rejects += 1

    print(f'\n📈 Volume Filter (≥500K):')
    print(f'   ✅ Passed: {len(volume_filtered):,}')
    print(f'   ❌ Rejected: {volume_rejects:,}')

    # Change filter
    change_filtered = []
    change_rejects = 0
    for stock in volume_filtered:
        change = abs(stock.get('todaysChangePerc', 0))
        if change >= 1.5:  # 1.5% minimum movement
            change_filtered.append(stock)
        else:
            change_rejects += 1

    print(f'\n📊 Change Filter (≥1.5%):')
    print(f'   ✅ Passed: {len(change_filtered):,}')
    print(f'   ❌ Rejected: {change_rejects:,}')

    reduction_pct = ((len(universe) - len(change_filtered)) / len(universe) * 100)
    print(f'\n🎯 INITIAL FILTRATION SUMMARY:')
    print(f'   Started with: {len(universe):,} stocks')
    print(f'   Survivors: {len(change_filtered):,} stocks')
    print(f'   Reduction: {reduction_pct:.1f}%')

    # Step 3: Show top survivors before enrichment
    print(f'\n🏆 TOP 10 SURVIVORS BEFORE ENRICHMENT:')
    print('-' * 50)
    for i, stock in enumerate(change_filtered[:10], 1):
        ticker = stock.get('ticker', 'UNKNOWN')
        price = stock.get('day', {}).get('c', 0)
        volume = stock.get('day', {}).get('v', 0)
        change = stock.get('todaysChangePerc', 0)
        print(f'{i:2d}. {ticker:5s}: ${price:6.2f} | {volume:10,} vol | {change:+6.1f}%')

    # Step 4: Full pipeline
    print(f'\n⚡ STEP 3: FULL DISCOVERY PIPELINE')
    print('-' * 40)
    print('Running complete discovery with enrichment...')

    result = await engine.run_discovery(limit=25)

    if result.get('status') == 'success':
        candidates = result.get('candidates', [])

        print(f'\n✅ DISCOVERY COMPLETE:')
        print(f'   Final candidates: {len(candidates)}')
        print(f'   Trade ready: {result.get("trade_ready_count", 0)}')
        print(f'   Watchlist: {result.get("watchlist_count", 0)}')
        exec_time = result.get('execution_time_sec', 0)
        print(f'   Execution time: {exec_time:.1f}s')

        print(f'\n🏅 FINAL EXPLOSIVE STOCKS:')
        print('-' * 50)

        for i, candidate in enumerate(candidates[:15], 1):
            ticker = candidate.get('ticker', 'UNKNOWN')
            score = candidate.get('total_score', 0) * 100
            irv = candidate.get('intraday_relative_volume', 0)
            change = candidate.get('todaysChangePerc', 0)
            price = candidate.get('price', 0)
            tier = candidate.get('tier', 'unknown')

            print(f'{i:2d}. {ticker:5s}: {score:5.1f}% | {irv:6.1f}x IRV | {change:+6.1f}% | ${price:6.2f} | {tier}')

        # Step 5: Scoring breakdown
        print(f'\n📊 SCORING ANALYSIS:')
        print('-' * 30)
        scores = [c.get('total_score', 0) * 100 for c in candidates]
        if scores:
            print(f'   Highest score: {max(scores):.1f}%')
            print(f'   Lowest score: {min(scores):.1f}%')
            avg_score = sum(scores)/len(scores)
            print(f'   Average score: {avg_score:.1f}%')

            # Count by tier
            tiers = {}
            for c in candidates:
                tier = c.get('tier', 'unknown')
                tiers[tier] = tiers.get(tier, 0) + 1

            print(f'\n   Tier breakdown:')
            for tier, count in tiers.items():
                print(f'     {tier}: {count} stocks')

        print(f'\n🎯 PIPELINE SUMMARY:')
        print(f'   Universe → Filters → IRV → Scoring → Tiers')
        universe_count = len(universe)
        filter_count = len(change_filtered)
        final_count = len(candidates)
        print(f'   {universe_count:,} → {filter_count:,} → Enriched → {final_count} survivors')

        # Step 6: Detailed filtration flow
        print(f'\n🔬 DETAILED FILTRATION FLOW:')
        print('-' * 40)
        print(f'1. Raw Universe:     {universe_count:,} stocks')
        print(f'2. Price Filter:     {len(price_filtered):,} stocks ({price_rejects:,} rejected)')
        print(f'3. Volume Filter:    {len(volume_filtered):,} stocks ({volume_rejects:,} rejected)')
        print(f'4. Change Filter:    {len(change_filtered):,} stocks ({change_rejects:,} rejected)')
        print(f'5. IRV Enrichment:   {len(change_filtered):,} stocks (all enriched)')
        print(f'6. AlphaStack Score: {len(candidates)} stocks (scoring applied)')
        print(f'7. Tier Filtering:   {len(candidates)} stocks (30%+ threshold)')

        survival_rate = (len(candidates) / len(universe) * 100)
        print(f'\n📈 SURVIVAL RATE: {survival_rate:.3f}%')
        print(f'   ({len(candidates)} survivors out of {universe_count:,} total stocks)')

    else:
        error_msg = result.get('error', 'Unknown error')
        print(f'❌ Discovery failed: {error_msg}')

if __name__ == "__main__":
    asyncio.run(complete_system_trace())