#!/usr/bin/env python3
"""
Full Pipeline Live Test
Shows step-by-step how the BMS system scans ALL stocks and filters them
"""

import asyncio
import sys
import os
import time
from collections import defaultdict

# Add backend to path
sys.path.append('/Users/michaelmote/Desktop/AMC-TRADER/backend')

from src.services.bms_engine_real import RealBMSEngine

async def full_pipeline_test():
    """Test the complete discovery pipeline on ALL stocks"""
    
    print("🔍 FULL STOCK UNIVERSE PIPELINE TEST")
    print("=" * 70)
    print("Testing complete discovery pipeline - ALL 5000+ stocks")
    print("Step-by-step filtering with real-time counts")
    print()
    
    # Initialize real BMS engine
    polygon_key = "1ORwpSzeOV20X6uaA8G3Zuxx7hLJ0KIC"
    engine = RealBMSEngine(polygon_key)
    
    # Enhanced statistics tracking
    stats = {
        'step1_universe_fetched': 0,
        'step2_api_successful': 0,
        'step3_price_passed': 0,
        'step4_volume_passed': 0,
        'step5_options_passed': 0,
        'step6_scored': 0,
        'step7_trade_ready': 0,
        'step8_monitor': 0,
        'api_errors': 0,
        'rejection_reasons': defaultdict(int),
        'symbol_distribution': defaultdict(int),
        'price_distribution': defaultdict(int),
        'final_candidates': []
    }
    
    print("🌍 STEP 1: FETCHING COMPLETE STOCK UNIVERSE")
    print("-" * 50)
    start_time = time.time()
    
    all_symbols = await engine.fetch_all_active_stocks()
    stats['step1_universe_fetched'] = len(all_symbols)
    
    print(f"✅ Retrieved {len(all_symbols)} active stocks from Polygon")
    print(f"   Sample symbols: {', '.join(all_symbols[:10])}...")
    print(f"   Last symbols: {', '.join(all_symbols[-10:])}")
    
    # Check alphabetical distribution
    for symbol in all_symbols:
        first_letter = symbol[0] if symbol else 'OTHER'
        stats['symbol_distribution'][first_letter] += 1
    
    print(f"   Distribution by first letter:")
    for letter in sorted(stats['symbol_distribution'].keys())[:10]:
        print(f"     {letter}: {stats['symbol_distribution'][letter]} stocks")
    
    if not all_symbols:
        print("❌ No symbols retrieved - aborting test")
        return
    
    print(f"\n⚡ STEP 2: PROCESSING ALL {len(all_symbols)} STOCKS")
    print("-" * 50)
    print("Real-time filtering pipeline:")
    
    batch_size = engine.config['limits']['batch_size']
    processed = 0
    
    # Process ALL symbols (not just 200)
    for i in range(0, len(all_symbols), batch_size):
        batch = all_symbols[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(all_symbols) + batch_size - 1) // batch_size
        
        print(f"\n  📦 Batch {batch_num}/{total_batches} ({len(batch)} symbols):")
        print(f"      Processing: {', '.join(batch[:5])}{'...' if len(batch) > 5 else ''}")
        
        batch_start = time.time()
        
        for symbol in batch:
            try:
                processed += 1
                
                # STEP 2a: Get market data
                market_data = await engine.get_real_market_data(symbol)
                if not market_data:
                    stats['api_errors'] += 1
                    continue
                
                stats['step2_api_successful'] += 1
                
                # STEP 3: Price bounds filter
                price = market_data['price']
                u = engine.config['universe']
                
                if price < u['min_price'] or price > u['max_price']:
                    if price < u['min_price']:
                        stats['rejection_reasons'][f'price_too_low_{price:.2f}'] += 1
                    else:
                        stats['rejection_reasons'][f'price_too_high_{price:.2f}'] += 1
                    continue
                
                stats['step3_price_passed'] += 1
                
                # Track price distribution
                if price < 1.0:
                    stats['price_distribution']['$0.5-1.0'] += 1
                elif price < 5.0:
                    stats['price_distribution']['$1.0-5.0'] += 1
                elif price < 20.0:
                    stats['price_distribution']['$5.0-20.0'] += 1
                elif price < 50.0:
                    stats['price_distribution']['$20.0-50.0'] += 1
                else:
                    stats['price_distribution']['$50.0-100.0'] += 1
                
                # STEP 4: Volume filter
                dollar_volume_m = market_data['dollar_volume'] / 1_000_000
                if dollar_volume_m < u['min_dollar_volume_m']:
                    stats['rejection_reasons'][f'volume_too_low_{dollar_volume_m:.1f}M'] += 1
                    continue
                
                stats['step4_volume_passed'] += 1
                
                # STEP 5: Options liquidity filter
                has_options = market_data.get('has_liquid_options', False)
                if u['require_liquid_options'] and not has_options:
                    stats['rejection_reasons']['no_liquid_options'] += 1
                    continue
                
                stats['step5_options_passed'] += 1
                
                # STEP 6: Calculate BMS score
                candidate = engine._calculate_real_bms_score(market_data)
                if not candidate:
                    stats['rejection_reasons']['scoring_failed'] += 1
                    continue
                
                stats['step6_scored'] += 1
                
                # STEP 7 & 8: Action classification
                if candidate['action'] == 'TRADE_READY':
                    stats['step7_trade_ready'] += 1
                    stats['final_candidates'].append(candidate)
                elif candidate['action'] == 'MONITOR':
                    stats['step8_monitor'] += 1
                    stats['final_candidates'].append(candidate)
                else:
                    stats['rejection_reasons']['score_too_low'] += 1
                
                # Progress updates
                if processed % 500 == 0:
                    elapsed = time.time() - start_time
                    rate = processed / elapsed
                    candidates_found = len(stats['final_candidates'])
                    
                    print(f"      Progress: {processed:,}/{len(all_symbols):,} ({rate:.1f}/sec)")
                    print(f"      Pipeline: API:{stats['step2_api_successful']:,} → Price:{stats['step3_price_passed']:,} → Volume:{stats['step4_volume_passed']:,} → Options:{stats['step5_options_passed']:,} → Scored:{stats['step6_scored']:,}")
                    print(f"      Found: {candidates_found} candidates ({stats['step7_trade_ready']} trade-ready, {stats['step8_monitor']} monitor)")
            
            except Exception as e:
                stats['api_errors'] += 1
                continue
        
        batch_time = time.time() - batch_start
        print(f"      Batch completed in {batch_time:.1f}s")
        
        # Small delay to respect rate limits
        await asyncio.sleep(0.2)
    
    # Sort final candidates by BMS score
    stats['final_candidates'].sort(key=lambda x: x['bms_score'], reverse=True)
    final_candidates = stats['final_candidates'][:50]  # Top 50
    
    # Final results
    elapsed = time.time() - start_time
    
    print(f"\n" + "=" * 70)
    print("📊 COMPLETE PIPELINE RESULTS")
    print("=" * 70)
    
    print(f"⏱️  Total Processing Time: {elapsed/60:.1f} minutes ({elapsed:.1f} seconds)")
    print(f"⚡ Processing Rate: {processed/elapsed:.1f} stocks/second")
    
    print(f"\n🔢 STEP-BY-STEP FILTERING:")
    print(f"   Step 1 - Universe Fetched:     {stats['step1_universe_fetched']:,} stocks")
    print(f"   Step 2 - API Data Retrieved:   {stats['step2_api_successful']:,} stocks ({stats['step2_api_successful']/stats['step1_universe_fetched']*100:.1f}%)")
    print(f"   Step 3 - Price Bounds Passed:  {stats['step3_price_passed']:,} stocks ({stats['step3_price_passed']/stats['step2_api_successful']*100:.1f}% of API success)")
    print(f"   Step 4 - Volume Filter Passed: {stats['step4_volume_passed']:,} stocks ({stats['step4_volume_passed']/stats['step3_price_passed']*100:.1f}% of price passed)")
    print(f"   Step 5 - Options Filter Passed:{stats['step5_options_passed']:,} stocks ({stats['step5_options_passed']/stats['step4_volume_passed']*100:.1f}% of volume passed)")
    print(f"   Step 6 - Successfully Scored:  {stats['step6_scored']:,} stocks ({stats['step6_scored']/stats['step5_options_passed']*100:.1f}% of options passed)")
    print(f"   Step 7 - Trade Ready (75+):    {stats['step7_trade_ready']:,} stocks")
    print(f"   Step 8 - Monitor (60-74):      {stats['step8_monitor']:,} stocks")
    print(f"   📈 Total Final Candidates:     {len(stats['final_candidates']):,} stocks")
    
    print(f"\n🚫 TOP REJECTION REASONS:")
    top_rejections = sorted(stats['rejection_reasons'].items(), key=lambda x: x[1], reverse=True)[:10]
    for reason, count in top_rejections:
        percentage = count / stats['step1_universe_fetched'] * 100
        print(f"   {reason}: {count:,} stocks ({percentage:.1f}%)")
    
    print(f"\n💰 PRICE DISTRIBUTION OF CANDIDATES:")
    for price_range, count in sorted(stats['price_distribution'].items()):
        print(f"   {price_range}: {count:,} stocks")
    
    print(f"\n🏆 TOP 20 CANDIDATES FOUND:")
    print("   Rank | Symbol | Price   | Score | Action      | Volume    | Letter")
    print("   -----|--------|---------|-------|-------------|-----------|-------")
    
    for i, candidate in enumerate(final_candidates[:20], 1):
        symbol = candidate['symbol']
        price = candidate['price']
        score = candidate['bms_score']
        action = candidate['action']
        volume_m = candidate.get('dollar_volume', 0) / 1_000_000
        first_letter = symbol[0]
        
        action_icon = "🚀" if action == 'TRADE_READY' else "👁️"
        print(f"   {i:2d}   | {symbol:<6} | ${price:7.2f} | {score:5.1f} | {action_icon} {action:<9} | ${volume_m:6.0f}M | {first_letter}")
    
    # Verify alphabet distribution in results
    candidate_letters = defaultdict(int)
    for candidate in final_candidates:
        candidate_letters[candidate['symbol'][0]] += 1
    
    print(f"\n🔤 CANDIDATE ALPHABET DISTRIBUTION:")
    for letter in sorted(candidate_letters.keys()):
        print(f"   {letter}: {candidate_letters[letter]} candidates")
    
    print(f"\n✅ VERIFICATION:")
    if len(set(candidate_letters.keys())) > 5:
        print("   ✅ Candidates span multiple letters - full universe scanned")
    else:
        print("   ⚠️  Candidates mostly from early letters - may indicate incomplete scan")
    
    if stats['step1_universe_fetched'] > 4000:
        print("   ✅ Large universe fetched - comprehensive scan")
    else:
        print(f"   ⚠️  Only {stats['step1_universe_fetched']} symbols - may be incomplete")
    
    if processed >= stats['step1_universe_fetched'] * 0.9:
        print("   ✅ Processed >90% of universe - comprehensive coverage")
    else:
        print(f"   ⚠️  Only processed {processed}/{stats['step1_universe_fetched']} ({processed/stats['step1_universe_fetched']*100:.1f}%)")
    
    return final_candidates

if __name__ == "__main__":
    try:
        print("Starting comprehensive pipeline test...")
        print("This will scan ALL active stocks and show filtering at each step")
        print("Expected duration: 15-30 minutes for full scan\n")
        
        results = asyncio.run(full_pipeline_test())
        print(f"\n🎯 Test completed successfully!")
        print(f"Found {len(results)} final candidates from complete universe scan")
        
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()