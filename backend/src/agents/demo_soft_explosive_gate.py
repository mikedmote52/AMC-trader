#!/usr/bin/env python3
"""
Demo the soft EGS explosive gate with simulated realistic data
Shows how the elastic fallback works with proper market data
"""

import asyncio
import logging
from datetime import datetime
from alphastack_v4 import create_discovery_system

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def demo_soft_explosive_gate():
    print('🔥 SOFT EGS EXPLOSIVE GATE DEMO')
    print('=' * 100)
    print('Demonstrating elastic fallback with simulated realistic market data')
    print()
    
    # Since weekend data has missing prices, let's create a mock explosive shortlist
    # to demonstrate the EGS scoring and elastic fallback logic
    
    print('SIMULATED EXPLOSIVE CANDIDATES (Realistic Market Conditions):')
    print('=' * 100)
    
    # Mock candidates representing different EGS tiers
    mock_candidates = [
        {
            "symbol": "QUBT",
            "price": 3.45,
            "egs": 72.5,
            "ser": 89.2,
            "relvol_tod": 4.8,
            "float_rotation": 0.45,
            "squeeze_friction": 78.3,
            "gamma_pressure": 85.2,
            "catalyst_freshness": 92.1,
            "vwap_adherence_30m": 82.4,
            "value_traded_usd": 8_500_000,
            "effective_spread_bps": 25.3,
            "tier": "Prime"
        },
        {
            "symbol": "IONQ",
            "price": 12.67,
            "egs": 68.1,
            "ser": 75.6,
            "relvol_tod": 3.2,
            "float_rotation": 0.28,
            "squeeze_friction": 65.1,
            "gamma_pressure": 71.8,
            "catalyst_freshness": 88.5,
            "vwap_adherence_30m": 76.2,
            "value_traded_usd": 12_200_000,
            "effective_spread_bps": 18.7,
            "tier": "Prime"
        },
        {
            "symbol": "SMCI",
            "price": 28.94,
            "egs": 55.7,
            "ser": 68.3,
            "relvol_tod": 2.8,
            "float_rotation": 0.15,
            "squeeze_friction": 45.2,
            "gamma_pressure": 58.9,
            "catalyst_freshness": 76.3,
            "vwap_adherence_30m": 71.5,
            "value_traded_usd": 22_800_000,
            "effective_spread_bps": 12.4,
            "tier": "Strong"
        },
        {
            "symbol": "BBAI",
            "price": 4.82,
            "egs": 52.3,
            "ser": 61.7,
            "relvol_tod": 2.1,
            "float_rotation": 0.32,
            "squeeze_friction": 52.8,
            "gamma_pressure": 48.6,
            "catalyst_freshness": 65.4,
            "vwap_adherence_30m": 68.2,
            "value_traded_usd": 5_400_000,
            "effective_spread_bps": 35.1,
            "tier": "Strong"
        },
        {
            "symbol": "RGTI",
            "price": 1.89,
            "egs": 47.8,
            "ser": 52.4,
            "relvol_tod": 1.8,
            "float_rotation": 0.52,
            "squeeze_friction": 38.5,
            "gamma_pressure": 35.2,
            "catalyst_freshness": 58.7,
            "vwap_adherence_30m": 62.1,
            "value_traded_usd": 3_200_000,
            "effective_spread_bps": 42.8,
            "tier": "Elastic"
        }
    ]
    
    print('EGS SCORING BREAKDOWN:')
    print('-' * 50)
    print('  • ToD-RelVol (sustain): 30 pts - Volume surge with persistence')
    print('  • Gamma/Options: 18 pts - Smart money positioning') 
    print('  • Float rotation: 12 pts - Structural pressure')
    print('  • Squeeze friction: 10 pts - Short squeeze potential')
    print('  • Catalyst/Sentiment: 15 pts - Reason for move')
    print('  • VWAP adherence: 10 pts - Institutional support')
    print('  • Liquidity tier: 3 pts - $3M+ traded bonus')
    print('  • ATR band: 2 pts - Volatility sweet spot')
    print('  📊 Total: 100 pts (soft scoring, no hard failures)')
    print()
    
    print('ELASTIC FALLBACK DEMONSTRATION:')
    print('-' * 50)
    print('  1. Prime tier (EGS ≥ 60): Look for highest conviction candidates')
    print('  2. Strong tier (EGS ≥ 50): Include solid opportunities if needed')
    print('  3. Elastic fallback: Lower threshold by 5 until 3+ candidates')
    print('  4. Floor protection: Never go below EGS 45 (quality control)')
    print()
    
    print('🎯 SIMULATED EXPLOSIVE CANDIDATES:')
    print('-' * 140)
    print(f"{'#':<3} {'Symbol':<8} {'Tier':<8} {'EGS':<5} {'SER':<5} {'RelVol':<7} {'Float%':<7} {'Squeeze':<8} {'Gamma':<7} {'VWAP%':<7} {'Value($M)':<10}")
    print('-' * 140)
    
    for i, exp in enumerate(mock_candidates, 1):
        value_m = exp['value_traded_usd'] / 1_000_000
        print(f'{i:<3} {exp["symbol"]:<8} {exp["tier"]:<8} {exp["egs"]:<5.1f} {exp["ser"]:<5.1f} '
              f'{exp["relvol_tod"]:<7.2f} {exp["float_rotation"]*100:<7.1f} '
              f'{exp["squeeze_friction"]:<8.1f} {exp["gamma_pressure"]:<7.1f} '
              f'{exp["vwap_adherence_30m"]:<7.1f} {value_m:<10.2f}')
    
    print('-' * 140)
    print()
    
    # Demonstrate tier logic
    print('TIER SELECTION LOGIC:')
    print('-' * 40)
    
    prime_candidates = [c for c in mock_candidates if c['egs'] >= 60]
    strong_candidates = [c for c in mock_candidates if 50 <= c['egs'] < 60]
    elastic_candidates = [c for c in mock_candidates if c['egs'] < 50]
    
    print(f'Prime (EGS ≥ 60): {len(prime_candidates)} candidates - {[c["symbol"] for c in prime_candidates]}')
    print(f'Strong (EGS 50-59): {len(strong_candidates)} candidates - {[c["symbol"] for c in strong_candidates]}')
    print(f'Elastic (EGS < 50): {len(elastic_candidates)} candidates - {[c["symbol"] for c in elastic_candidates]}')
    print()
    
    # Show final selection
    print('FINAL SELECTION (Target: 3-5 candidates):')
    print('-' * 45)
    
    if len(prime_candidates) >= 3:
        selected = prime_candidates[:5]
        print(f'✅ Prime tier sufficient: {len(selected)} candidates selected')
    else:
        selected = prime_candidates + strong_candidates
        if len(selected) >= 3:
            selected = selected[:5]
            print(f'✅ Prime + Strong sufficient: {len(selected)} candidates selected')
        else:
            selected = prime_candidates + strong_candidates + elastic_candidates
            selected = selected[:5]
            print(f'✅ Elastic fallback engaged: {len(selected)} candidates selected')
    
    print()
    for i, candidate in enumerate(selected, 1):
        print(f'{i}. {candidate["symbol"]} (EGS: {candidate["egs"]:.1f}, Tier: {candidate["tier"]})')
    
    print()
    print('=' * 100)
    print('✅ SOFT EGS SYSTEM ADVANTAGES')
    print('=' * 100)
    print('🎯 CONSISTENCY: Always provides 3-5 explosive candidates')
    print('📊 QUALITY: EGS scoring ranks by true explosive potential')
    print('🛡️ SAFETY: Hard guards prevent untradeable situations')
    print('⚡ ADAPTIVE: Elastic fallback works in all market conditions')
    print('🔬 TRANSPARENT: Clear tier system shows conviction level')
    print()
    print('vs. Old Hard Gate:')
    print('❌ Could return 0 candidates on quiet days')
    print('❌ Binary pass/fail obscured quality differences')
    print('❌ No fallback for edge cases')
    print()
    print('🚀 RESULT: More reliable explosive opportunity detection')

if __name__ == "__main__":
    asyncio.run(demo_soft_explosive_gate())