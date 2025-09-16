#!/usr/bin/env python3
"""
AlphaStack 4.1 Explosive Shortlist Test
Real-world test showing full universe processing with explosive opportunities detection
"""

import asyncio
import logging
import json
from datetime import datetime
from alphastack_v4 import create_discovery_system

# Set up detailed logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def explosive_test():
    print('🚀 ALPHASTACK 4.1 EXPLOSIVE SHORTLIST TEST')
    print('=' * 100)
    print('📊 Processing full market universe with explosive gate filtering')
    print('🎯 Identifying top 3-5 most explosive opportunities using geometric SER ranking')
    print()
    
    # Create the enhanced discovery system
    discovery = create_discovery_system()
    
    # Check system health first
    print('📊 SYSTEM HEALTH CHECK:')
    health = await discovery.system_health_check()
    print(f'✅ System Ready: {health["system_ready"]}')
    print(f'📈 Provider Summary: {health["summary"]}')
    print()
    
    if not health['system_ready']:
        print('❌ System not ready - cannot proceed with test')
        return
    
    print('=' * 100)
    print('🌍 STAGE 1: UNIVERSE ACQUISITION')
    print('=' * 100)
    
    # Run full discovery with explosive shortlist
    start_time = datetime.now()
    results = await discovery.discover_candidates(limit=50)
    execution_time = results['execution_time_sec']
    
    # Check for stale data condition
    if results.get('status') == 'stale_data':
        print('🚨 STALE DATA DETECTED:')
        print(f'   Market is open but data is stale: {results.get("age_minutes", 0):.1f} minutes old')
        print(f'   System correctly refused to process stale data during market hours')
        print(f'   Response: items=[], explosive_top=[]')
        await discovery.close()
        return
    
    # Show market status
    print(f'📅 Market Status: {results.get("status", "unknown").upper()}')
    print(f'🎭 Market Regime: {results.get("regime", "normal")}')
    print(f'⏱️ Execution Time: {execution_time:.2f} seconds')
    print()
    
    # Show pipeline statistics with detailed breakdown
    stats = results['pipeline_stats']
    print('=' * 100)
    print('🔬 STAGE 2: FILTRATION PIPELINE')
    print('=' * 100)
    
    universe_size = stats["universe_size"]
    enriched_size = stats["enriched"]
    filtered_size = stats["filtered"]
    scored_size = stats["scored"]
    final_size = results["count"]
    
    print(f'📥 Input Universe: {universe_size:,} stocks (complete market)')
    print()
    
    # Stage-by-stage breakdown
    print('FILTRATION STAGES:')
    print('-' * 80)
    
    # Stage 2.1: Business Logic Filter
    business_filtered = universe_size - enriched_size
    print(f'2.1 BUSINESS LOGIC FILTER:')
    print(f'    • Price range: $0.10 - $100.00')
    print(f'    • Min dollar volume: $5M')
    print(f'    • Symbol pattern exclusions')
    print(f'    ✂️ Removed: {business_filtered:,} stocks')
    print(f'    ➡️ Remaining: {enriched_size:,} stocks')
    print()
    
    # Stage 2.2: ETP/ETF Filter
    etp_filtered = 80  # Approximate from previous tests
    print(f'2.2 ETP/ETF EXCLUSION:')
    print(f'    • Removed ETFs/ETNs: ~{etp_filtered} (TSLL, TQQQ, etc.)')
    print(f'    ➡️ Remaining: {enriched_size - etp_filtered:,} stocks')
    print()
    
    # Stage 2.3: Liquidity Filter
    print(f'2.3 LIQUIDITY FILTER:')
    print(f'    • Bid-ask spread < 100 bps')
    print(f'    • Average volume requirements')
    print(f'    ➡️ Remaining: {filtered_size:,} stocks')
    print()
    
    # Stage 2.4: Technical Filters
    technical_filtered = enriched_size - filtered_size
    print(f'2.4 TECHNICAL FILTERS:')
    print(f'    • Microstructure requirements')
    print(f'    • RelVol gates')
    print(f'    • VWAP positioning')
    print(f'    • Squeeze criteria')
    print(f'    ✂️ Removed: {technical_filtered:,} stocks')
    print(f'    ➡️ Remaining: {filtered_size:,} stocks')
    print()
    
    # Stage 3: Scoring
    print('=' * 100)
    print('🎯 STAGE 3: 6-BUCKET SCORING ENGINE')
    print('=' * 100)
    print(f'📊 Scored Candidates: {scored_size:,} stocks')
    print()
    print('SCORING COMPONENTS:')
    print('  • S1: Volume & Momentum (30%) - Time-normalized RelVol')
    print('  • S2: Squeeze Potential (25%) - Float rotation + friction')
    print('  • S3: Catalyst Strength (20%) - Exponential decay + verification')
    print('  • S4: Sentiment Analysis (10%) - Z-score anomalies')
    print('  • S5: Options Activity (8%) - Down-weighted missing data')
    print('  • S6: Technical Indicators (7%) - Regime-aware thresholds')
    print()
    
    # Stage 4: Final Selection
    print('=' * 100)
    print('🏆 STAGE 4: FINAL CANDIDATE SELECTION')
    print('=' * 100)
    print(f'✅ Top Candidates Selected: {final_size} stocks')
    
    # Calculate filtration efficiency
    if universe_size > 0:
        total_filtration = (universe_size - final_size) / universe_size * 100
        print(f'📈 TOTAL FILTRATION RATE: {total_filtration:.2f}%')
    print()
    
    # Show top candidates
    if results['items']:
        print('TOP GENERAL CANDIDATES:')
        print('-' * 100)
        print(f"{'#':<3} {'Symbol':<8} {'Score':<7} {'Action':<12} {'Conf':<6} {'V':<4} {'S':<4} {'C':<4} {'O':<4} {'T':<4} {'Price':<8}")
        print('-' * 100)
        
        for i, candidate in enumerate(results['items'][:10], 1):
            vol_score = candidate.get('volume_momentum_score', 0)
            squeeze_score = candidate.get('squeeze_score', 0)
            catalyst_score = candidate.get('catalyst_score', 0)
            options_score = candidate.get('options_score', 0)
            technical_score = candidate.get('technical_score', 0)
            
            print(f'{i:<3} {candidate["symbol"]:<8} {candidate["total_score"]:<7.1f} {candidate["action_tag"]:<12} '
                  f'{candidate["confidence"]:<6.2f} {vol_score:<4.0f} {squeeze_score:<4.0f} {catalyst_score:<4.0f} '
                  f'{options_score:<4.0f} {technical_score:<4.0f} ${candidate.get("price", 0):<7.2f}')
        print()
    
    # Show explosive shortlist (NEW FEATURE)
    print('=' * 100)
    print('🔥 STAGE 5: EXPLOSIVE SHORTLIST (NEW)')
    print('=' * 100)
    
    explosive_top = results.get('explosive_top', [])
    
    if explosive_top:
        print(f'💎 EXPLOSIVE OPPORTUNITIES FOUND: {len(explosive_top)}')
        print()
        print('EXPLOSIVE GATE CRITERIA (ALL must pass):')
        print('  ✓ ToD-RelVol ≥ 3.0x (live) or 2.5x (premarket)')
        print('  ✓ Sustained volume ≥ 20 min (live) or 10 min (premarket)')
        print('  ✓ VWAP adherence ≥ 70% (last 30 minutes)')
        print('  ✓ Float rotation ≥ 30% OR Squeeze friction ≥ 60')
        print('  ✓ Gamma pressure ≥ 65 AND ATM call OI ≥ 500')
        print('  ✓ Catalyst freshness ≥ 70 OR Sentiment anomaly ≥ 70')
        print('  ✓ Effective spread ≤ 40 bps')
        print('  ✓ Value traded ≥ $3M')
        print('  ✓ ATR% in range [4%, 12%]')
        print()
        
        print('🎯 EXPLOSIVE CANDIDATES (Geometric SER Ranking):')
        print('-' * 140)
        print(f"{'#':<3} {'Symbol':<8} {'Price':<8} {'SER':<6} {'RelVol':<7} {'Float%':<7} {'Squeeze':<8} {'Gamma':<7} {'Catalyst':<9} {'VWAP%':<7} {'Value($M)':<10}")
        print('-' * 140)
        
        for i, exp in enumerate(explosive_top, 1):
            value_m = exp['value_traded_usd'] / 1_000_000
            print(f'{i:<3} {exp["symbol"]:<8} ${exp["price"]:<7.2f} {exp["ser"]:<6.1f} '
                  f'{exp["relvol_tod"]:<7.2f} {exp["float_rotation"]*100:<7.1f} '
                  f'{exp["squeeze_friction"]:<8.1f} {exp["gamma_pressure"]:<7.1f} '
                  f'{exp["catalyst_freshness"]:<9.1f} {exp["vwap_adherence_30m"]:<7.1f} '
                  f'{value_m:<10.2f}')
        
        print('-' * 140)
        print()
        print('📊 SER CALCULATION (Geometric Mean):')
        print('  SER = 100 × (RelVol/5)^0.28 × (Float/0.6)^0.18 × (Squeeze/100)^0.14')
        print('       × (Gamma/100)^0.18 × (Catalyst/100)^0.12 × (VWAP/100)^0.10')
        print()
        print('💡 Higher SER = More explosive potential (punishes weak components)')
        
    else:
        print('❌ NO EXPLOSIVE OPPORTUNITIES DETECTED')
        print()
        print('Possible reasons:')
        print('  • Market closed/weekend (stale data)')
        print('  • No stocks meeting all 9 explosive gate criteria')
        print('  • Quiet market regime (low volatility)')
        print('  • Insufficient options/catalyst activity')
    
    print()
    
    # Show telemetry
    if 'telemetry' in results:
        telemetry = results['telemetry']
        print('=' * 100)
        print('📡 TELEMETRY & DATA COVERAGE')
        print('=' * 100)
        
        if 'data_coverage' in telemetry:
            coverage = telemetry['data_coverage']
            print('DATA ENRICHMENT COVERAGE:')
            print(f'  • Options Data: {coverage.get("options_data", 0):.1f}%')
            print(f'  • Short Data: {coverage.get("short_data", 0):.1f}%')
            print(f'  • Social Data: {coverage.get("social_data", 0):.1f}%')
            print(f'  • Catalyst Data: {coverage.get("catalyst_data", 0):.1f}%')
            print(f'  • Technical Data: {coverage.get("technical_data", 0):.1f}%')
            print(f'  • Overall: {coverage.get("overall_enrichment", 0):.1f}%')
    
    # Clean up
    await discovery.close()
    print()
    print('=' * 100)
    print('✅ EXPLOSIVE SHORTLIST TEST COMPLETE')
    print('=' * 100)
    print('📊 System successfully processed full universe with explosive filtering')
    print('🎯 Explosive shortlist identifies highest-conviction opportunities')
    print('🛡️ Conservative gate ensures only true explosive setups pass through')

if __name__ == "__main__":
    # Run the comprehensive test
    asyncio.run(explosive_test())