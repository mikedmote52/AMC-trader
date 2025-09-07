#!/usr/bin/env python3
"""
Test script for the new BMS (Breakout Momentum Score) system
Validates the system against June-July 2025 winners
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.append('/Users/michaelmote/Desktop/AMC-TRADER/backend')

from src.services.bms_engine_real import RealBMSEngine as BMSEngine

async def test_bms_system():
    """Test the BMS system with historical winners"""
    
    print("🧪 Testing BMS Discovery System")
    print("=" * 50)
    
    # Initialize BMS engine with Polygon API key
    polygon_key = "1ORwpSzeOV20X6uaA8G3Zuxx7hLJ0KIC"
    bms = BMSEngine(polygon_key)
    
    # Test 1: System Health
    print("\n1️⃣ System Health Check")
    health = bms.get_health_status()
    print(f"✅ Engine: {health['engine']}")
    print(f"✅ Config loaded: {len(health['config']['weights'])} weights")
    
    # Test 2: Historical Winners Analysis
    print("\n2️⃣ Historical Winners Analysis")
    historical_winners = [
        'VIGL',  # +324%
        'CRWV',  # +171% 
        'AEVA',  # +162%
        'CRDO',  # +108%
        'SEZL',  # +66%
        'SMCI',  # +35%
        'TSLA',  # +21%
        'WOLF'   # -25% (the loser)
    ]
    
    print(f"Testing {len(historical_winners)} historical symbols...")
    
    results = []
    for symbol in historical_winners:
        try:
            print(f"\n📊 Analyzing {symbol}...")
            
            # Fetch current market data
            market_data = await bms.fetch_market_data(symbol)
            if market_data:
                # Calculate BMS score
                analysis = bms.calculate_bms_score(market_data)
                if analysis:
                    results.append({
                        'symbol': symbol,
                        'bms_score': analysis['bms_score'],
                        'action': analysis['action'],
                        'confidence': analysis['confidence'],
                        'volume_surge': market_data['rel_volume_30d'],
                        'momentum_1d': market_data['momentum_1d'],
                        'atr_pct': market_data['atr_pct']
                    })
                    
                    print(f"  Score: {analysis['bms_score']:.1f} | Action: {analysis['action']}")
                    print(f"  Volume: {market_data['rel_volume_30d']:.1f}x | Momentum: {market_data['momentum_1d']:.1f}%")
                else:
                    print(f"  ❌ Failed to calculate BMS score")
            else:
                print(f"  ❌ No market data available")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    # Test 3: Full Discovery Scan
    print("\n3️⃣ Discovery Scan Test")
    print("Running discovery scan for top candidates...")
    
    try:
        candidates = await bms.discover_candidates(limit=10)
        
        if candidates:
            print(f"✅ Found {len(candidates)} candidates")
            
            trade_ready = [c for c in candidates if c['action'] == 'TRADE_READY']
            monitor = [c for c in candidates if c['action'] == 'MONITOR']
            
            print(f"  🚀 Trade Ready: {len(trade_ready)}")
            print(f"  👁️ Monitor: {len(monitor)}")
            
            if candidates:
                print(f"  🏆 Top candidate: {candidates[0]['symbol']} (BMS: {candidates[0]['bms_score']:.1f})")
        else:
            print("⚠️ No candidates found")
            
    except Exception as e:
        print(f"❌ Discovery scan failed: {e}")
    
    # Summary Report
    print("\n" + "=" * 50)
    print("📋 SUMMARY REPORT")
    print("=" * 50)
    
    if results:
        print(f"Analyzed {len(results)} historical symbols:")
        
        # Sort by BMS score
        results.sort(key=lambda x: x['bms_score'], reverse=True)
        
        print("\nRankings (by current BMS score):")
        for i, result in enumerate(results, 1):
            action_emoji = "🚀" if result['action'] == 'TRADE_READY' else "👁️" if result['action'] == 'MONITOR' else "❌"
            print(f"{i:2d}. {action_emoji} {result['symbol']:<6} | {result['bms_score']:5.1f} | {result['action']}")
        
        # System validation
        trade_ready_count = len([r for r in results if r['action'] == 'TRADE_READY'])
        monitor_count = len([r for r in results if r['action'] == 'MONITOR'])
        
        print(f"\nSystem Performance:")
        print(f"  Would catch for trading: {trade_ready_count}/{len(results)} ({trade_ready_count/len(results)*100:.1f}%)")
        print(f"  Would monitor: {monitor_count}/{len(results)} ({monitor_count/len(results)*100:.1f}%)")
        
        # Check if WOLF (the loser) would be rejected
        wolf_result = next((r for r in results if r['symbol'] == 'WOLF'), None)
        if wolf_result:
            if wolf_result['action'] == 'REJECT' or wolf_result['bms_score'] < 60:
                print(f"  ✅ Successfully would reject WOLF (loser): {wolf_result['bms_score']:.1f}")
            else:
                print(f"  ⚠️ System would not reject WOLF: {wolf_result['bms_score']:.1f}")
    
    print(f"\n🎯 BMS System Status: {'✅ OPERATIONAL' if results else '❌ NEEDS ATTENTION'}")
    return results

if __name__ == "__main__":
    # Run the test
    try:
        results = asyncio.run(test_bms_system())
        print(f"\n✅ Test completed. Analyzed {len(results) if results else 0} symbols.")
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()