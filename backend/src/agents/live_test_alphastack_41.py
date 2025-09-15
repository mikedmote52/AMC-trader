#!/usr/bin/env python3
"""
AlphaStack 4.1 Live System Test
Comprehensive test showing full discovery pipeline from universe to final candidates
"""

import asyncio
import logging
from alphastack_v4 import create_discovery_system

# Set up detailed logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def test_live_system():
    print('🚀 ALPHASTACK 4.1 LIVE SYSTEM TEST')
    print('=' * 60)
    
    # Create the enhanced discovery system
    discovery = create_discovery_system()
    
    # Check system health first
    print('📊 SYSTEM HEALTH CHECK:')
    health = await discovery.system_health_check()
    print(f'System Ready: {health["system_ready"]}')
    print(f'Provider Summary: {health["summary"]}')
    print()
    
    if not health['system_ready']:
        print('❌ System not ready - cannot proceed with live test')
        return
    
    print('🔍 RUNNING FULL DISCOVERY PIPELINE...')
    print('=' * 60)
    
    # Run full discovery with detailed output
    results = await discovery.discover_candidates(limit=25)
    
    # Show pipeline statistics
    stats = results['pipeline_stats']
    print(f'📈 PIPELINE RESULTS:')
    print(f'Universe Size: {stats["universe_size"]:,} stocks')
    print(f'After Enrichment: {stats["enriched"]:,} stocks')
    print(f'After Filtering: {stats["filtered"]:,} stocks')
    print(f'Final Scored: {stats["scored"]:,} stocks')
    print(f'Top Candidates: {results["count"]} stocks')
    print()
    
    print(f'⏱️  Execution Time: {results["execution_time_sec"]:.2f} seconds')
    print(f'🔖 Schema Version: {results.get("schema_version", "N/A")}')
    print(f'🧠 Algorithm: {results.get("algorithm_version", "N/A")}')
    print()
    
    # Calculate filtration rates
    universe_size = stats["universe_size"]
    enriched_size = stats["enriched"]
    filtered_size = stats["filtered"]
    scored_size = stats["scored"]
    final_size = results["count"]
    
    print('📊 FILTRATION BREAKDOWN:')
    print('-' * 50)
    if universe_size > 0:
        enrich_rate = (universe_size - enriched_size) / universe_size * 100
        filter_rate = (enriched_size - filtered_size) / enriched_size * 100 if enriched_size > 0 else 0
        score_rate = (filtered_size - scored_size) / filtered_size * 100 if filtered_size > 0 else 0
        final_rate = (scored_size - final_size) / scored_size * 100 if scored_size > 0 else 0
        
        print(f'1. Universe → Enriched: {universe_size:,} → {enriched_size:,} ({enrich_rate:.1f}% filtered)')
        print(f'2. Enriched → Basic Filters: {enriched_size:,} → {filtered_size:,} ({filter_rate:.1f}% filtered)')
        print(f'3. Filtered → Scored: {filtered_size:,} → {scored_size:,} ({score_rate:.1f}% filtered)')
        print(f'4. Scored → Top Candidates: {scored_size:,} → {final_size:,} ({final_rate:.1f}% filtered)')
    print()
    
    # Show top candidates with enhanced scoring
    if results['candidates']:
        print('🏆 TOP CANDIDATES FOUND:')
        print('-' * 85)
        print(f"{'#':<3} {'Symbol':<8} {'Score':<6} {'Action':<12} {'Conf':<5} {'RelVol':<7} {'Price':<8} {'Components'}")
        print('-' * 85)
        
        for i, candidate in enumerate(results['candidates'][:15], 1):
            components = f"V:{candidate['volume_momentum_score']:.0f} S:{candidate['squeeze_score']:.0f} C:{candidate['catalyst_score']:.0f}"
            print(f'{i:<3} {candidate["symbol"]:<8} {candidate["total_score"]:<6.1f} {candidate["action_tag"]:<12} {candidate["confidence"]:<5.2f} {candidate.get("rel_vol", 0):<7.1f} ${candidate.get("price", 0):<7.2f} {components}')
        
        print('-' * 85)
        print(f'V=Volume/Momentum(30%), S=Squeeze(25%), C=Catalyst(20%)')
        print(f'Enhanced 4.1 Features: Time-normalized RelVol, Float rotation, Catalyst decay')
        print()
        
        # Analyze action tags
        action_counts = {}
        for candidate in results['candidates']:
            action = candidate['action_tag']
            action_counts[action] = action_counts.get(action, 0) + 1
        
        print('🎯 ACTION TAG DISTRIBUTION:')
        for action, count in action_counts.items():
            print(f'   {action}: {count} candidates')
        print()
        
        # Show scoring distribution
        scores = [c['total_score'] for c in results['candidates']]
        if scores:
            print('📊 SCORING ANALYSIS:')
            print(f'   Highest Score: {max(scores):.1f}')
            print(f'   Lowest Score: {min(scores):.1f}')
            print(f'   Average Score: {sum(scores)/len(scores):.1f}')
            print(f'   Score Range: {max(scores) - min(scores):.1f}')
        print()
        
        # Show risk analysis
        risk_counts = {}
        for candidate in results['candidates']:
            for risk in candidate.get('risk_flags', []):
                risk_counts[risk] = risk_counts.get(risk, 0) + 1
        
        if risk_counts:
            print('⚠️  RISK ANALYSIS:')
            for risk, count in risk_counts.items():
                print(f'   {risk}: {count} candidates')
        else:
            print('✅ No significant risk flags detected')
    else:
        print('❌ No candidates found - check market conditions or filtering criteria')
    
    # Clean up
    await discovery.close()
    print()
    print('✅ LIVE TEST COMPLETE - AlphaStack 4.1 Enhanced System Operational')

if __name__ == "__main__":
    # Run the comprehensive test
    asyncio.run(test_live_system())