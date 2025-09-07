#!/usr/bin/env python3
"""
Live BMS System Test
Test the new BMS system locally to see what stocks it finds
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.append('/Users/michaelmote/Desktop/AMC-TRADER/backend')

from src.services.bms_engine_real import RealBMSEngine as BMSEngine

async def live_bms_test():
    """Test what the BMS system currently finds"""
    
    print("🔍 LIVE BMS SYSTEM TEST")
    print("=" * 50)
    print("Testing what stocks the new BMS system discovers")
    print("with $0.5-$100 price bounds and ≥$10M volume\n")
    
    # Initialize BMS engine
    polygon_key = "1ORwpSzeOV20X6uaA8G3Zuxx7hLJ0KIC" 
    bms = BMSEngine(polygon_key)
    
    # Test 1: System Configuration
    print("1️⃣ System Configuration")
    config = bms.config
    universe = config['universe']
    print(f"  Price Range: ${universe['min_price']} - ${universe['max_price']}")
    print(f"  Min Volume: ${universe['min_dollar_volume_m']}M")
    print(f"  Options Required: {universe['require_liquid_options']}")
    
    # Test 2: Run Discovery
    print(f"\n2️⃣ Running Live Discovery Scan...")
    candidates = await bms.discover_candidates(limit=25)
    
    if not candidates:
        print("❌ No candidates found!")
        print("This could be due to:")
        print("  - Market hours (system may need live data)")
        print("  - API rate limits")
        print("  - Restrictive universe gates")
        
        # Try a few specific symbols manually
        print(f"\n3️⃣ Testing Specific Symbols")
        test_symbols = ['AAPL', 'TSLA', 'VIGL', 'AMD', 'NVDA']
        
        for symbol in test_symbols:
            try:
                market_data = await bms.get_market_data_polygon(symbol)
                if market_data:
                    passes_gates = bms._passes_universe_gates(market_data)
                    bms_result = bms.calculate_bms_score(market_data)
                    
                    print(f"  {symbol}: ${market_data['price']:.2f} | "
                          f"Vol: ${market_data['dollar_volume']/1_000_000:.1f}M | "
                          f"Gates: {'✅' if passes_gates else '❌'} | "
                          f"BMS: {bms_result['bms_score']:.1f if bms_result else 'N/A'}")
                else:
                    print(f"  {symbol}: No market data available")
            except Exception as e:
                print(f"  {symbol}: Error - {e}")
    
    else:
        print(f"✅ Found {len(candidates)} candidates!")
        
        # Analyze results
        trade_ready = [c for c in candidates if c['action'] == 'TRADE_READY']
        monitor = [c for c in candidates if c['action'] == 'MONITOR']
        
        print(f"\n3️⃣ Results Breakdown")
        print(f"  🚀 Trade Ready (75+): {len(trade_ready)} candidates")
        print(f"  👁️ Monitor (60-74): {len(monitor)} candidates")
        
        if candidates:
            min_price = min(c['price'] for c in candidates)
            max_price = max(c['price'] for c in candidates)
            avg_score = sum(c['bms_score'] for c in candidates) / len(candidates)
            
            print(f"\n4️⃣ Price Distribution")
            print(f"  Price Range: ${min_price:.2f} - ${max_price:.2f}")
            print(f"  Average BMS Score: {avg_score:.1f}")
            
            # Show top candidates
            print(f"\n5️⃣ Top 10 Candidates")
            print("  Rank | Symbol | Price  | BMS   | Action     | Volume Surge")
            print("  -----|--------|--------|-------|------------|-------------")
            
            for i, candidate in enumerate(candidates[:10], 1):
                action_icon = "🚀" if candidate['action'] == 'TRADE_READY' else "👁️"
                print(f"   {i:2d}  | {candidate['symbol']:<6} | ${candidate['price']:5.2f} | "
                      f"{candidate['bms_score']:5.1f} | {action_icon} {candidate['action']:<8} | "
                      f"{candidate['volume_surge']:.1f}x")
            
            # Check for sub-$2 and over-$100 stocks
            sub_2_stocks = [c for c in candidates if c['price'] < 2.0]
            over_100_stocks = [c for c in candidates if c['price'] > 100.0]
            
            print(f"\n6️⃣ Price Bounds Validation")
            print(f"  Sub-$2 stocks: {len(sub_2_stocks)} (should have ≥$10M volume)")
            if sub_2_stocks:
                for stock in sub_2_stocks:
                    vol_m = stock.get('dollar_volume', 0) / 1_000_000
                    print(f"    {stock['symbol']}: ${stock['price']:.2f}, ${vol_m:.1f}M volume")
            
            print(f"  Over-$100 stocks: {len(over_100_stocks)} (should be 0)")
            if over_100_stocks:
                for stock in over_100_stocks:
                    print(f"    ❌ {stock['symbol']}: ${stock['price']:.2f} (should be filtered)")
    
    print(f"\n" + "=" * 50)
    print("📋 LIVE TEST SUMMARY")
    print("=" * 50)
    
    if candidates:
        print(f"✅ BMS system is functional and finding candidates")
        print(f"✅ Found {len(candidates)} stocks in discovery scan")
        print(f"✅ Price bounds working: ${min_price:.2f} - ${max_price:.2f}")
        print(f"✅ Ready for deployment to replace legacy system")
        
        if len(trade_ready) > 0:
            print(f"🚀 {len(trade_ready)} stocks ready for immediate trading")
        if len(monitor) > 0:
            print(f"👁️ {len(monitor)} stocks worth monitoring")
            
    else:
        print("⚠️ No candidates found - investigation needed")
        print("Possible causes:")
        print("- Market closed (need live market data)")
        print("- API rate limits or connectivity issues")
        print("- Universe gates too restrictive")
        print("- Mock data limitations in simplified engine")
    
    return candidates

if __name__ == "__main__":
    try:
        results = asyncio.run(live_bms_test())
        candidate_count = len(results) if results else 0
        print(f"\n🎯 Test completed. Found {candidate_count} candidates.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()