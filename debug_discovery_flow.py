#!/usr/bin/env python3
"""
Debug Discovery Flow - Live trace through BMS filtering steps
"""

import sys
import os
import asyncio
import time
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.getcwd(), 'backend', 'src'))

async def debug_discovery_flow():
    try:
        from backend.src.services.bms_engine_real import RealBMSEngine
        
        print("🔍 LIVE DISCOVERY DEBUG - Tracing each filtering step")
        print(f"⏰ Started at: {datetime.now().isoformat()}")
        print("=" * 60)
        
        # Initialize BMS engine
        polygon_key = os.getenv('POLYGON_API_KEY')
        if not polygon_key:
            print("❌ POLYGON_API_KEY not found in environment")
            return False
            
        print(f"✅ Polygon API Key: {'*' * 10}{polygon_key[-4:]}")
        bms_engine = RealBMSEngine(polygon_key)
        
        print("\n📊 BMS Configuration:")
        config = bms_engine.config
        print(f"  Price range: ${config['universe']['min_price']} - ${config['universe']['max_price']}")
        print(f"  Min dollar volume: ${config['universe']['min_dollar_volume_m']}M")
        print(f"  Universe limit: {config['universe']['universe_k']} stocks")
        print(f"  Early stop scan: {config['performance']['early_stop_scan']} stocks")
        
        # Step 1: Fetch initial universe
        print("\n" + "="*60)
        print("STEP 1: INITIAL UNIVERSE FETCH")
        print("="*60)
        
        start_time = time.perf_counter()
        try:
            filtered_symbols = await bms_engine.fetch_filtered_stocks()
        except Exception as e:
            print(f"❌ Error in universe fetch: {e}")
            return False
            
        fetch_time = time.perf_counter() - start_time
        print(f"✅ Initial fetch completed in {fetch_time:.1f}s")
        print(f"📈 Total symbols after price/volume pre-filter: {len(filtered_symbols)}")
        
        if len(filtered_symbols) == 0:
            print("❌ CRITICAL: No symbols passed initial filtering!")
            print("   This indicates API issues or overly restrictive filters")
            return False
            
        # Show first 20 symbols as sample
        print(f"📋 Sample symbols (first 20): {filtered_symbols[:20]}")
        
        # Step 2: Intraday snapshot filter
        print("\n" + "="*60) 
        print("STEP 2: INTRADAY SNAPSHOT FILTER")
        print("="*60)
        
        start_time = time.perf_counter()
        try:
            intraday_symbols = await bms_engine.intraday_snapshot_filter(filtered_symbols)
        except Exception as e:
            print(f"❌ Error in intraday filter: {e}")
            intraday_symbols = filtered_symbols[:1000]  # Fallback
            
        intraday_time = time.perf_counter() - start_time
        print(f"✅ Intraday filter completed in {intraday_time:.1f}s")
        print(f"📉 Symbols after intraday filter: {len(intraday_symbols)} (eliminated {len(filtered_symbols) - len(intraday_symbols)})")
        
        if len(intraday_symbols) == 0:
            print("❌ CRITICAL: No symbols passed intraday filtering!")
            print("   This indicates market closed or snapshot data unavailable")
            return False
            
        # Apply universe limit
        universe_limit = config['universe']['universe_k']
        if len(intraday_symbols) > universe_limit:
            print(f"📊 Applying universe limit: {universe_limit} from {len(intraday_symbols)}")
            intraday_symbols = intraday_symbols[:universe_limit]
        
        print(f"📋 Final universe for scoring: {len(intraday_symbols)} symbols")
        print(f"📋 Sample symbols for scoring: {intraday_symbols[:10]}")
        
        # Step 3: Test scoring on first 50 symbols
        print("\n" + "="*60)
        print("STEP 3: SCORING ANALYSIS (First 50 symbols)")
        print("="*60)
        
        scoring_results = {
            'tested': 0,
            'api_errors': 0,
            'gate_failures': 0,
            'score_rejects': 0,
            'monitor_candidates': 0,
            'trade_ready': 0,
            'detailed_rejects': {}
        }
        
        test_symbols = intraday_symbols[:50]  # Test first 50 for detailed analysis
        
        for i, symbol in enumerate(test_symbols):
            try:
                scoring_results['tested'] += 1
                
                # Get market data
                market_data = await bms_engine.get_real_market_data(symbol)
                
                if not market_data:
                    scoring_results['api_errors'] += 1
                    print(f"  {i+1:2d}. {symbol:6s} - ❌ API Error")
                    continue
                
                # Test universe gates
                passes, reason = bms_engine._passes_universe_gates(market_data)
                
                if not passes:
                    scoring_results['gate_failures'] += 1
                    gate_type = reason.split(':')[0]
                    scoring_results['detailed_rejects'][gate_type] = scoring_results['detailed_rejects'].get(gate_type, 0) + 1
                    print(f"  {i+1:2d}. {symbol:6s} - ❌ Gate: {reason}")
                    continue
                
                # Calculate BMS score
                candidate = bms_engine._calculate_real_bms_score(market_data)
                
                if not candidate:
                    scoring_results['api_errors'] += 1
                    print(f"  {i+1:2d}. {symbol:6s} - ❌ Scoring Error")
                    continue
                
                # Check action
                if candidate['action'] == 'TRADE_READY':
                    scoring_results['trade_ready'] += 1
                    print(f"  {i+1:2d}. {symbol:6s} - ✅ TRADE_READY: {candidate['bms_score']:.1f} (${market_data['price']:.2f}, {market_data['rel_volume_30d']:.1f}x vol)")
                elif candidate['action'] == 'MONITOR':
                    scoring_results['monitor_candidates'] += 1
                    print(f"  {i+1:2d}. {symbol:6s} - 👁️  MONITOR: {candidate['bms_score']:.1f} (${market_data['price']:.2f}, {market_data['rel_volume_30d']:.1f}x vol)")
                else:
                    scoring_results['score_rejects'] += 1
                    print(f"  {i+1:2d}. {symbol:6s} - ❌ Score: {candidate['bms_score']:.1f} < threshold")
                    
            except Exception as e:
                scoring_results['api_errors'] += 1
                print(f"  {i+1:2d}. {symbol:6s} - ❌ Exception: {str(e)[:40]}")
        
        # Results summary
        print("\n" + "="*60)
        print("DISCOVERY FLOW SUMMARY")
        print("="*60)
        
        print(f"📊 Initial Universe: {bms_engine.last_universe_counts.get('total_grouped', 'Unknown')} stocks")
        print(f"📊 Pre-filtered: {len(filtered_symbols)} stocks")
        print(f"📊 Intraday Pass: {len(intraday_symbols)} stocks") 
        print(f"📊 Scoring Test: {scoring_results['tested']} stocks")
        print()
        print(f"✅ Trade Ready: {scoring_results['trade_ready']}")
        print(f"👁️  Monitor: {scoring_results['monitor_candidates']}")
        print(f"❌ Score Rejects: {scoring_results['score_rejects']}")
        print(f"❌ Gate Failures: {scoring_results['gate_failures']}")
        print(f"❌ API Errors: {scoring_results['api_errors']}")
        print()
        
        if scoring_results['detailed_rejects']:
            print("🔍 Gate Rejection Breakdown:")
            for gate_type, count in scoring_results['detailed_rejects'].items():
                print(f"  - {gate_type}: {count}")
        
        # Calculate success rates
        total_viable = scoring_results['trade_ready'] + scoring_results['monitor_candidates']
        test_count = scoring_results['tested']
        
        if test_count > 0:
            success_rate = (total_viable / test_count) * 100
            print(f"\n📈 Success Rate: {success_rate:.1f}% ({total_viable}/{test_count})")
            
            if success_rate > 0:
                # Project to full universe
                projected_candidates = int((success_rate / 100) * len(intraday_symbols))
                print(f"📊 Projected Full Universe: ~{projected_candidates} candidates from {len(intraday_symbols)} stocks")
            else:
                print("⚠️  No viable candidates found in sample - may indicate overly strict filtering")
        
        return True
        
    except Exception as e:
        print(f"💥 Fatal error in discovery debug: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_discovery_flow())
    
    if success:
        print(f"\n✅ Discovery debug completed at {datetime.now().isoformat()}")
    else:
        print(f"\n❌ Discovery debug failed at {datetime.now().isoformat()}")