#!/usr/bin/env python3
"""
AMC-TRADER Mathematical Analysis
Shows exact calculations and formulas for explosive stock detection
"""

import asyncio
import sys
import os
sys.path.append('src')
from routes.discovery_optimized import ExplosiveDiscoveryEngine
import math

async def show_mathematical_calculations():
    engine = ExplosiveDiscoveryEngine()

    print('🧮 AMC-TRADER MATHEMATICAL ANALYSIS')
    print('=' * 70)

    print('\n📐 FILTRATION STEP 1: PRICE BOUNDARIES')
    print('-' * 50)
    print('Formula: $0.50 ≤ price ≤ $50.00')
    print('Purpose: Eliminate penny stocks and high-priced low-volatility stocks')
    print('Logic:')
    print('  - Below $0.50: Too volatile, manipulation risk')
    print('  - Above $50.00: Lower percentage movement potential')
    print('  - Sweet spot: $0.50-$50 for explosive percentage gains')

    print('\n📈 FILTRATION STEP 2: VOLUME THRESHOLD')
    print('-' * 50)
    print('Formula: current_volume ≥ 500,000 shares')
    print('Purpose: Ensure sufficient liquidity and institutional interest')
    print('Calculation:')
    print('  volume = stock.day.v')
    print('  if volume >= 500_000: PASS')
    print('  else: REJECT')
    print('Logic: 500K+ volume indicates real market movement vs noise')

    print('\n📊 FILTRATION STEP 3: PRICE MOVEMENT')
    print('-' * 50)
    print('Formula: |today_change_percent| ≥ 1.5%')
    print('Purpose: Identify stocks in motion (up OR down)')
    print('Calculation:')
    print('  change_pct = abs(stock.todaysChangePerc)')
    print('  if change_pct >= 1.5: PASS')
    print('  else: REJECT')
    print('Logic: 1.5%+ movement shows momentum vs sideways action')

    print('\n⚡ FILTRATION STEP 4: INTRADAY RELATIVE VOLUME (IRV)')
    print('-' * 60)
    print('🔥 MOST CRITICAL CALCULATION FOR EXPLOSIVE DETECTION')
    print()
    print('Formula: IRV = current_volume / expected_volume_at_time')
    print()
    print('Step-by-step IRV calculation:')
    print('1. Get 30-day historical volume data from Polygon API')
    print('2. Calculate average daily volume: avg_vol = sum(30_days) / 30')
    print('3. Determine market session progress:')
    print('   - Market open: 9:30 AM EST')
    print('   - Market close: 4:00 PM EST')
    print('   - Total session: 390 minutes')
    print('   - Current progress = (now - 9:30) / 390')
    print('4. Expected volume at current time:')
    print('   expected_vol = avg_vol * session_progress')
    print('5. Calculate IRV ratio:')
    print('   IRV = actual_current_volume / expected_vol')
    print()
    print('Example calculation:')
    print('  Stock: MSS')
    print('  Current volume: 89,856,044')
    print('  30-day avg volume: 227,088')
    print('  Session progress: 85% (3:20 PM)')
    print('  Expected vol: 227,088 * 0.85 = 193,025')
    print('  IRV = 89,856,044 / 193,025 = 465.5x')
    print('  Result: EXPLOSIVE VOLUME (100x cap applied)')

    # Get real data to show calculations
    print('\n🧪 LIVE IRV CALCULATIONS:')
    print('-' * 40)

    result = await engine.run_discovery(limit=5)
    candidates = result.get('candidates', [])

    for i, candidate in enumerate(candidates[:3], 1):
        ticker = candidate.get('ticker', 'UNKNOWN')
        current_vol = candidate.get('day', {}).get('v', 0)
        irv = candidate.get('intraday_relative_volume', 0)

        print(f'\n{i}. {ticker}:')
        print(f'   Current volume: {current_vol:,}')
        print(f'   IRV calculated: {irv:.1f}x')
        print(f'   Interpretation: {"EXPLOSIVE" if irv >= 10 else "ELEVATED" if irv >= 3 else "NORMAL"}')

    print('\n🎯 FILTRATION STEP 5: ALPHASTACK SCORING')
    print('-' * 50)
    print('Complex multi-factor scoring algorithm:')
    print()
    print('Main Formula: score = weighted_sum(all_factors) / 100')
    print()
    print('Factor breakdown:')
    print('1. MOMENTUM SCORE (0-20 points):')
    print('   - IRV component: min(IRV / 5 * 10, 10)')
    print('   - Consecutive up days: min(up_days * 2, 5)')
    print('   - Price vs VWAP: +3 if above, -2 if below')
    print('   - RSI momentum: +2 if 60-70 range')
    print()
    print('2. FLOAT & SHORT METRICS (0-20 points):')
    print('   - Short interest: higher = more squeeze potential')
    print('   - Float size: smaller = more explosive potential')
    print('   - Utilization: higher = tighter supply')
    print('   - Days to cover: higher = more squeeze risk')
    print()
    print('3. CATALYST DETECTION (0-20 points):')
    print('   - News sentiment analysis')
    print('   - Social media buzz')
    print('   - Unusual activity patterns')
    print()
    print('4. OPTIONS ACTIVITY (0-20 points):')
    print('   - Call/put ratio analysis')
    print('   - Implied volatility percentile')
    print('   - Open interest changes')
    print()
    print('5. TECHNICAL INDICATORS (0-20 points):')
    print('   - EMA crossovers (9 vs 20)')
    print('   - RSI levels (oversold bounce potential)')
    print('   - ATR for volatility')
    print('   - Support/resistance levels')

    print('\n📊 LIVE ALPHASTACK SCORING EXAMPLE:')
    print('-' * 45)

    if candidates:
        example = candidates[0]
        ticker = example.get('ticker', 'UNKNOWN')
        score = example.get('total_score', 0) * 100
        breakdown = example.get('alphastack_breakdown', {})

        print(f'\nStock: {ticker}')
        print(f'Final Score: {score:.1f}%')
        print(f'Component breakdown:')
        for component, points in breakdown.items():
            print(f'  {component}: {points:.1f} points')

        print(f'\nDetailed calculation for {ticker}:')
        irv = example.get('intraday_relative_volume', 0)
        change = example.get('todaysChangePerc', 0)
        volume = example.get('day', {}).get('v', 0)

        print(f'  IRV: {irv:.1f}x → Momentum boost')
        print(f'  Price change: {change:+.1f}% → Direction confirmation')
        print(f'  Volume: {volume:,} → Liquidity adequate')
        print(f'  Result: {score:.1f}% composite score')

    print('\n🎯 FILTRATION STEP 6: TIER ASSIGNMENT')
    print('-' * 45)
    print('Threshold-based classification:')
    print()
    print('Mathematical thresholds:')
    print('  if score >= 50.0: tier = "trade_ready"')
    print('  elif score >= 30.0: tier = "watchlist"')
    print('  elif score >= 25.0: tier = "near_miss"')
    print('  else: FILTERED OUT')
    print()
    print('Logic behind thresholds:')
    print('  - 50%+: High confidence for immediate trading')
    print('  - 30%+: Worth monitoring for entry opportunity')
    print('  - 25%+: Potential setup developing')
    print('  - <25%: Insufficient explosive characteristics')

    print('\n🔬 MATHEMATICAL VALIDATION:')
    print('-' * 40)

    if candidates:
        scores = [c.get('total_score', 0) * 100 for c in candidates]
        print(f'Score distribution analysis:')
        print(f'  Highest: {max(scores):.1f}%')
        print(f'  Lowest: {min(scores):.1f}%')
        print(f'  Average: {sum(scores)/len(scores):.1f}%')
        print(f'  Standard deviation: {(sum((x - sum(scores)/len(scores))**2 for x in scores) / len(scores))**0.5:.1f}%')

        # Show distribution
        buckets = {'50%+': 0, '40-49%': 0, '30-39%': 0, '25-29%': 0}
        for score in scores:
            if score >= 50: buckets['50%+'] += 1
            elif score >= 40: buckets['40-49%'] += 1
            elif score >= 30: buckets['30-39%'] += 1
            elif score >= 25: buckets['25-29%'] += 1

        print(f'\n  Score distribution:')
        for bucket, count in buckets.items():
            pct = count / len(scores) * 100
            print(f'    {bucket}: {count} stocks ({pct:.1f}%)')

    print('\n💡 KEY MATHEMATICAL INSIGHTS:')
    print('-' * 40)
    print('1. IRV is the primary explosive indicator')
    print('   - Normal: 1.0x (average volume)')
    print('   - Elevated: 3-5x (increased interest)')
    print('   - Explosive: 10x+ (major catalyst)')
    print('   - Extreme: 50x+ (squeeze/breakout)')
    print()
    print('2. Composite scoring prevents false positives')
    print('   - Single metric can be manipulated')
    print('   - Multi-factor approach more reliable')
    print('   - Weighted by historical effectiveness')
    print()
    print('3. Dynamic thresholds adapt to market conditions')
    print('   - Bull market: Higher thresholds')
    print('   - Bear market: Lower thresholds')
    print('   - Current: 30% captures real opportunities')

if __name__ == "__main__":
    asyncio.run(show_mathematical_calculations())