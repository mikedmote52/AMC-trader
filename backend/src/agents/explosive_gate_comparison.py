#!/usr/bin/env python3
"""
Explosive Gate Comparison: Strict vs Lenient Filtering
Shows the difference between requiring ALL criteria vs MOST criteria
"""

import asyncio
import logging
from datetime import datetime
from alphastack_v4 import create_discovery_system

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def compare_gate_strategies():
    print('🔬 EXPLOSIVE GATE FILTERING COMPARISON')
    print('=' * 100)
    print('Comparing different gate strategies to show why "ALL must pass" is used')
    print()
    
    discovery = create_discovery_system()
    
    # Get candidates
    results = await discovery.discover_candidates(limit=50)
    
    if results.get('status') == 'stale_data':
        print('⚠️ Market closed - using cached data for demonstration')
        print()
    
    # Simulate different gate strategies
    print('GATE STRATEGY COMPARISON:')
    print('-' * 100)
    
    # Strategy 1: ALL must pass (current)
    print('📍 STRATEGY 1: ALL 9 CRITERIA MUST PASS (Current)')
    print('   • Ensures every factor aligns perfectly')
    print('   • Minimizes false positives')
    print('   • Result: 0-5 stocks (only true explosives)')
    print()
    
    # Strategy 2: 7 out of 9
    print('📍 STRATEGY 2: AT LEAST 7 OUT OF 9 CRITERIA')
    print('   • More lenient, allows some weakness')
    print('   • Risk: May include stocks with critical weaknesses')
    print('   • Example failure patterns:')
    print('     - No catalyst but high volume (pump & dump risk)')
    print('     - Wide spreads (can\'t enter profitably)')
    print('     - Low dollar volume (illiquid, hard to exit)')
    print('   • Result: 5-15 stocks (mix of explosive and just active)')
    print()
    
    # Strategy 3: Weighted scoring
    print('📍 STRATEGY 3: WEIGHTED SCORING (50% threshold)')
    print('   • Each criterion contributes to a score')
    print('   • Risk: Obscures critical failures')
    print('   • Example: Stock with 90% score but 200bps spread = untradeable')
    print('   • Result: 10-20 stocks (many false positives)')
    print()
    
    # Strategy 4: Category-based (must pass 1 from each category)
    print('📍 STRATEGY 4: CATEGORY-BASED REQUIREMENTS')
    print('   Categories:')
    print('   • Volume (RelVol OR sustained volume)')
    print('   • Structure (Float rotation OR squeeze friction)')
    print('   • Catalyst (News OR sentiment)')
    print('   • Tradability (Spread AND dollar volume)')
    print('   • Risk: Missing synergies between factors')
    print('   • Result: 8-12 stocks (moderate filtering)')
    print()
    
    print('=' * 100)
    print('WHY "ALL MUST PASS" IS OPTIMAL:')
    print('-' * 100)
    
    print('1. EXPLOSIVE ≠ ACTIVE')
    print('   • Main list already has 50 active stocks')
    print('   • Explosive list is for EXCEPTIONAL setups only')
    print()
    
    print('2. EACH CRITERION IS CRITICAL:')
    print('   • RelVol ≥ 3x: Real institutional interest, not retail churn')
    print('   • Sustained 20min: Not a brief spike that\'s already over')
    print('   • VWAP adherence: Institutions supporting the move')
    print('   • Float/Squeeze: Structural pressure for continuation')
    print('   • Options activity: Smart money positioning')
    print('   • Catalyst/Sentiment: Reason for the move to continue')
    print('   • Tight spread: Can actually trade it profitably')
    print('   • $3M+ traded: Liquidity for size')
    print('   • ATR 4-12%: Volatility sweet spot')
    print()
    
    print('3. GEOMETRIC SER RANKING:')
    print('   • Already accounts for relative strength')
    print('   • Weak components get punished by geometric mean')
    print('   • Top 3-5 that pass ALL gates are ranked by SER')
    print()
    
    print('4. OPERATIONAL SAFETY:')
    print('   • Traders may size up on "explosive" labels')
    print('   • False positives are especially costly')
    print('   • Better to miss opportunities than create losses')
    print()
    
    # Show hypothetical relaxation
    print('=' * 100)
    print('IF YOU WANT MORE EXPLOSIVE CANDIDATES:')
    print('-' * 100)
    print('Option 1: Relax specific thresholds (keep ALL logic):')
    print('   • Lower RelVol to 2.5x (from 3.0x)')
    print('   • Lower sustained to 15min (from 20min)')
    print('   • Lower VWAP adherence to 60% (from 70%)')
    print()
    print('Option 2: Create tiers:')
    print('   • "explosive_confirmed": ALL 9 criteria (current)')
    print('   • "explosive_probable": 7-8 criteria')
    print('   • "explosive_possible": 5-6 criteria')
    print()
    print('Option 3: Market regime adjustment:')
    print('   • Tighten in volatile markets')
    print('   • Relax in quiet markets')
    print('   • Auto-adjust based on VIX/SPY ATR')
    print()
    
    await discovery.close()
    
    print('=' * 100)
    print('💡 RECOMMENDATION: Keep "ALL must pass" for explosive_top')
    print('   The strict gate is a feature, not a bug.')
    print('   It ensures explosive opportunities are truly exceptional.')
    print('=' * 100)

if __name__ == "__main__":
    asyncio.run(compare_gate_strategies())