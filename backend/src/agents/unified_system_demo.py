#!/usr/bin/env python3
"""
Unified AlphaStack 4.0 Discovery System Demo
THE ONLY STOCK DISCOVERY SYSTEM - All others removed
"""
import asyncio
import logging
from alphastack_v4 import create_discovery_system

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demonstrate_unified_system():
    """Demonstrate the ONE unified explosive stock discovery system"""
    
    print("🚀 UNIFIED AlphaStack 4.0 Discovery System")
    print("=" * 60)
    print("THE ONLY STOCK DISCOVERY SYSTEM - All redundancy removed")
    print()
    
    # Initialize THE discovery system
    discovery = create_discovery_system()
    
    # Run discovery to show exact flow
    print("🔍 Running Unified Discovery Pipeline:")
    print("   Step 1: Universe (Polygon API) → 3,033 stocks ($0.10-$100)")
    print("   Step 2: Enrichment (Local Tech Indicators) → RSI, VWAP, ATR, RelVol") 
    print("   Step 3: Hard Gates (Explosive Filters) → RelVol≥1.5x, ATR≥3%, VWAP above")
    print("   Step 4: Confidence Scoring (Never Zero) → 6 components with proxies")
    print("   Step 5: Action Tags → trade_ready, watchlist, monitor")
    print()
    
    try:
        results = await discovery.discover_candidates(limit=10)
        
        print(f"✅ Discovery Complete in {results['execution_time_sec']:.2f}s")
        print(f"📊 Pipeline: {results['pipeline_stats']['universe_size']:,} → {results['pipeline_stats']['filtered']:,} → {len(results['candidates'])} top candidates")
        print()
        
        if results['candidates']:
            print("🎯 Top Explosive Candidates:")
            print("Rank | Symbol | Score | Action    | RelVol | Triggers")
            print("-" * 55)
            
            for i, candidate in enumerate(results['candidates'], 1):
                symbol = candidate['symbol']
                score = candidate['total_score'] 
                action = candidate.get('action_tag', 'monitor')
                
                snapshot = candidate['snapshot']
                rel_vol = snapshot.get('rel_vol_30d', 'N/A')
                
                # Count active triggers
                trigger_count = sum([
                    snapshot.get('trigger_3x30', False),
                    snapshot.get('trigger_vwap_reclaim', False), 
                    snapshot.get('trigger_range_break', False)
                ])
                
                print(f"{i:2d}   | {symbol:6s} | {score:5.1f} | {action:9s} | {rel_vol:6.1f}x | {trigger_count}/3")
            
            print(f"\n💡 System Architecture:")
            print(f"   • ONE unified discovery system (alphastack_v4.py)")
            print(f"   • Real Polygon API data (no mocks)")
            print(f"   • Local technical computation (no external deps)")
            print(f"   • Confidence-aware scoring (never zero)")
            print(f"   • Hard explosive gates (squeeze hunting)")
            print(f"   • Fail-closed architecture (production ready)")
            
        else:
            print("⚠️ No candidates found - gates may be too restrictive")
            
        await discovery.close()
        return 0
        
    except Exception as e:
        print(f"❌ Discovery failed: {e}")
        return 1

if __name__ == "__main__":
    import sys
    result = asyncio.run(demonstrate_unified_system())
    sys.exit(result)