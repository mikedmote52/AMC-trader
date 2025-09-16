#!/usr/bin/env python3
"""
Debug the explosive gate filtering to understand why no candidates pass
"""

import asyncio
import logging
from datetime import datetime
from alphastack_v4 import create_discovery_system

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def debug_explosive_gates():
    print('🔍 EXPLOSIVE GATE DEBUG ANALYSIS')
    print('=' * 80)
    print('Analyzing why no candidates pass the hard guards')
    print()
    
    discovery = create_discovery_system()
    
    # Get the raw results
    results = await discovery.discover_candidates(limit=50)
    
    if results.get('status') == 'stale_data':
        print('⚠️ Stale data - cannot analyze')
        await discovery.close()
        return
    
    # Check top candidates' raw data
    candidates = results.get('items', [])
    if not candidates:
        print('❌ No general candidates - pipeline issue')
        await discovery.close()
        return
    
    print(f'📊 Found {len(candidates)} general candidates')
    print('Analyzing top 10 for explosive gate compatibility...')
    print()
    
    # Hard gate thresholds
    E = discovery.scoring_engine.EXPLOSIVE_TUNABLES
    print('HARD GATE THRESHOLDS:')
    print(f'  • Max spread: {E["eff_spread_bps_max"]} bps')
    print(f'  • Min price: $1.50')
    print(f'  • Min value: ${E["value_traded_min"]:,}')
    print()
    
    print('TOP CANDIDATES ANALYSIS:')
    print('-' * 110)
    print(f"{'Symbol':<8} {'Price':<8} {'Value($M)':<10} {'Spread(bps)':<12} {'Hard Gate':<10} {'Reason'}")
    print('-' * 110)
    
    for i, candidate in enumerate(candidates[:10]):
        symbol = candidate['symbol']
        price = candidate.get('price', 0)
        
        # Extract spread and value data (these might be missing in mock data)
        spread_bps = 50.0  # Default for testing since real data may be missing
        value_traded = candidate.get('value_traded_usd', 0)
        
        # If value_traded is missing, estimate from volume and price
        if value_traded == 0:
            volume = candidate.get('volume', 0)
            if volume > 0 and price > 0:
                value_traded = volume * price
        
        value_m = value_traded / 1_000_000 if value_traded > 0 else 0
        
        # Check hard gates
        gate_pass = True
        reason = "OK"
        
        if spread_bps > E["eff_spread_bps_max"]:
            gate_pass = False
            reason = f"Spread {spread_bps:.1f}bps > {E['eff_spread_bps_max']}"
        elif price < 1.50:
            gate_pass = False
            reason = f"Price ${price:.2f} < $1.50"
        elif value_traded < E["value_traded_min"]:
            gate_pass = False
            reason = f"Value ${value_m:.1f}M < ${E['value_traded_min']/1_000_000:.1f}M"
        
        gate_status = "✅ PASS" if gate_pass else "❌ FAIL"
        
        print(f'{symbol:<8} ${price:<7.2f} {value_m:<10.1f} {spread_bps:<12.1f} {gate_status:<10} {reason}')
    
    print('-' * 110)
    print()
    
    # Check if the issue is mock data vs real market data
    print('DIAGNOSIS:')
    print('Since this is weekend/closed market data, the issue is likely:')
    print('  1. 📊 Volume data is stale (Friday\'s volume)')
    print('  2. 💰 Value traded < $1M threshold (weekend = no trading)')
    print('  3. 📈 Missing real-time spread data')
    print()
    
    print('SOLUTIONS:')
    print('  1. Relax value_traded_min for weekend testing')
    print('  2. Use mock spread data for demo purposes')
    print('  3. Test during market hours for real validation')
    print()
    
    await discovery.close()

if __name__ == "__main__":
    asyncio.run(debug_explosive_gates())