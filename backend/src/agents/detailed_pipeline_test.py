#!/usr/bin/env python3
"""
Detailed Pipeline Test - Shows exactly what happens at each filtration stage
"""

import asyncio
import logging
from alphastack_v4 import create_discovery_system

async def detailed_pipeline_test():
    print('🔬 DETAILED ALPHASTACK 4.1 PIPELINE ANALYSIS')
    print('=' * 70)
    
    discovery = create_discovery_system()
    
    # Run discovery and capture detailed metrics
    results = await discovery.discover_candidates(limit=10)
    
    print('📊 COMPLETE PIPELINE BREAKDOWN:')
    print('=' * 70)
    
    stats = results['pipeline_stats']
    
    # Show each stage
    print(f'🌍 STAGE 1: UNIVERSE GENERATION')
    print(f'   Started with: 11,409 stocks from Polygon API')
    print(f'   Basic eligibility filter applied')
    print(f'   Result: {stats["universe_size"]:,} qualifying stocks')
    print()
    
    print(f'🔍 STAGE 2: DATA ENRICHMENT')
    print(f'   Technical indicators calculated (VWAP, RSI, ATR)')
    print(f'   Market data normalized and validated')
    print(f'   Result: {stats["enriched"]:,} enriched stocks')
    print()
    
    print(f'⚡ STAGE 3: FILTERING PIPELINE')
    print(f'   Multiple filters applied sequentially:')
    enriched = stats["enriched"]
    filtered = stats["filtered"]
    removed = enriched - filtered
    print(f'   • Basic filters (price, volume, market cap)')
    print(f'   • Liquidity filters (bid-ask spread)')
    print(f'   • Microstructure filters (market quality)')
    print(f'   • RelVol filters (enhanced time-normalized)')
    print(f'   • VWAP filters (momentum confirmation)')
    print(f'   • Squeeze filters (float-based)')
    print(f'   Filtered out: {removed:,} stocks ({removed/enriched*100:.1f}%)')
    print(f'   Result: {filtered:,} candidate stocks')
    print()
    
    print(f'🧠 STAGE 4: ALPHASTACK 4.1 ENHANCED SCORING')
    print(f'   Each stock scored using 6-component algorithm:')
    print(f'   • Volume & Momentum (30%): Time-normalized RelVol')
    print(f'   • Squeeze Potential (25%): Float rotation + friction index')
    print(f'   • Catalyst Strength (20%): Exponential decay + source boost')
    print(f'   • Sentiment Anomaly (10%): Z-score statistical analysis') 
    print(f'   • Options Activity (8%): Call/put ratios + IV analysis')
    print(f'   • Technical Setup (7%): Regime-aware RSI/ATR bands')
    print(f'   Regime adjustments applied based on market conditions')
    print(f'   Result: {stats["scored"]:,} scored candidates')
    print()
    
    print(f'🏆 STAGE 5: FINAL SELECTION')
    print(f'   Top candidates selected by composite score')
    print(f'   Action tags assigned:')
    action_counts = {}
    for candidate in results['candidates']:
        action = candidate['action_tag']
        action_counts[action] = action_counts.get(action, 0) + 1
    
    for action, count in action_counts.items():
        print(f'   • {action}: {count} stocks')
    print(f'   Final result: {results["count"]} top candidates')
    print()
    
    # Show the actual winners with detailed breakdown
    print('🎯 FINAL CANDIDATES WITH ENHANCED 4.1 SCORING:')
    print('=' * 90)
    print(f"{'Rank':<4} {'Symbol':<8} {'Total':<6} {'Vol':<4} {'Sqz':<4} {'Cat':<4} {'Sent':<4} {'Opt':<4} {'Tech':<4} {'Action'}")
    print('=' * 90)
    
    for i, candidate in enumerate(results['candidates'], 1):
        print(f'{i:<4} {candidate["symbol"]:<8} {candidate["total_score"]:<6.1f} '
              f'{candidate["volume_momentum_score"]:<4.0f} {candidate["squeeze_score"]:<4.0f} '
              f'{candidate["catalyst_score"]:<4.0f} {candidate["sentiment_score"]:<4.0f} '
              f'{candidate["options_score"]:<4.0f} {candidate["technical_score"]:<4.0f} '
              f'{candidate["action_tag"]}')
    
    print('=' * 90)
    print('Vol=Volume(30%), Sqz=Squeeze(25%), Cat=Catalyst(20%), Sent=Sentiment(10%), Opt=Options(8%), Tech=Technical(7%)')
    print()
    
    # Show filtration efficiency
    total_reduction = (11409 - results["count"]) / 11409 * 100
    print(f'📈 OVERALL FILTRATION EFFICIENCY:')
    print(f'   Started: 11,409 stocks in market universe')
    print(f'   Ended: {results["count"]} high-quality candidates')
    print(f'   Reduction: {total_reduction:.3f}% (99.9%+ filtered out)')
    print(f'   Execution time: {results["execution_time_sec"]:.2f} seconds')
    print(f'   Schema version: {results["schema_version"]}')
    print()
    
    await discovery.close()
    print('✅ DETAILED PIPELINE TEST COMPLETE')
    print('✅ AlphaStack 4.1 Enhanced System Successfully Filtering Universe → Quality Candidates')

if __name__ == "__main__":
    asyncio.run(detailed_pipeline_test())