#!/usr/bin/env python3
"""
Test Enhanced Short Interest System
Quick validation that the new multi-source system works
"""
import asyncio
import sys
import os
sys.path.append('backend/src')

from services.enhanced_short_interest import get_enhanced_short_interest

async def test_short_interest_coverage():
    """Test enhanced short interest system with various stocks"""
    
    # Test with various stock types
    test_symbols = [
        "AAPL",  # Large cap - should have some data
        "TSLA",  # High short interest stock
        "GME",   # Meme stock with high short interest
        "NAMM",  # Previously contaminated stock
        "LCFY",  # Previously contaminated stock
        "UP",    # Previously had real Yahoo data
        "NVDA",  # Tech stock
        "AMC"    # Meme stock
    ]
    
    print("🔍 Testing Enhanced Short Interest System")
    print("=" * 50)
    
    results = {}
    for symbol in test_symbols:
        print(f"\n📊 Testing {symbol}...")
        
        try:
            data = await get_enhanced_short_interest(symbol)
            if data:
                results[symbol] = data
                print(f"✅ {symbol}: {data.percent:.1%} short interest")
                print(f"   Source: {data.source}")
                print(f"   Confidence: {data.confidence:.2f}")
                print(f"   Updated: {data.last_updated}")
            else:
                results[symbol] = None
                print(f"❌ {symbol}: No data found")
                
        except Exception as e:
            print(f"💥 {symbol}: Error - {e}")
            results[symbol] = None
    
    # Summary statistics
    print("\n" + "=" * 50)
    print("📈 COVERAGE SUMMARY")
    print("=" * 50)
    
    found_data = [s for s, r in results.items() if r is not None]
    coverage = len(found_data) / len(test_symbols) * 100
    
    print(f"Coverage: {len(found_data)}/{len(test_symbols)} stocks ({coverage:.1f}%)")
    
    if found_data:
        print(f"✅ Success: {', '.join(found_data)}")
        
        # Source breakdown
        sources = {}
        for symbol in found_data:
            source = results[symbol].source
            sources[source] = sources.get(source, 0) + 1
        
        print("\n📊 Source Breakdown:")
        for source, count in sources.items():
            print(f"   {source}: {count} stocks")
            
        # Confidence analysis
        confidences = [results[symbol].confidence for symbol in found_data]
        avg_confidence = sum(confidences) / len(confidences)
        print(f"\n🎯 Average Confidence: {avg_confidence:.2f}")
        
    no_data = [s for s, r in results.items() if r is None]
    if no_data:
        print(f"❌ No Data: {', '.join(no_data)}")
    
    print("\n" + "=" * 50)
    if coverage >= 50:
        print("🎉 SUCCESS: Enhanced system provides significant improvement!")
        print(f"   Previous coverage: ~15% (Yahoo only)")
        print(f"   New coverage: {coverage:.1f}% ({coverage/15:.1f}x improvement)")
    else:
        print("⚠️  NEEDS WORK: Coverage below target")
        print("   Consider additional data sources or estimation algorithms")
    
    return results

if __name__ == "__main__":
    results = asyncio.run(test_short_interest_coverage())