#!/usr/bin/env python3
"""
Test script for enhanced thesis generation
"""
import asyncio
import sys
import os

# Add the backend src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.thesis_generator import ThesisGenerator

async def test_thesis_generation():
    """Test the enhanced thesis generator with sample position data"""
    generator = ThesisGenerator()
    
    # Test data representing the positions that currently lack thesis
    test_positions = [
        {
            'symbol': 'UP',
            'unrealized_pl_pct': 108.98,
            'market_value': 2500.00,
            'last_price': 12.50,
            'avg_entry_price': 5.98
        },
        {
            'symbol': 'KSS', 
            'unrealized_pl_pct': 15.11,
            'market_value': 1800.00,
            'last_price': 18.75,
            'avg_entry_price': 16.28
        },
        {
            'symbol': 'AMDL',
            'unrealized_pl_pct': 1.37,
            'market_value': 1200.00,
            'last_price': 8.45,
            'avg_entry_price': 8.34
        },
        {
            'symbol': 'TEVA',
            'unrealized_pl_pct': -1.15,
            'market_value': 950.00,
            'last_price': 16.20,
            'avg_entry_price': 16.39
        },
        {
            'symbol': 'WULF',
            'unrealized_pl_pct': 10.30,
            'market_value': 3200.00,
            'last_price': 22.15,
            'avg_entry_price': 20.08
        }
    ]
    
    print("🧠 Testing Enhanced Thesis Generation")
    print("=" * 60)
    
    for pos in test_positions:
        try:
            print(f"\n📊 Analyzing {pos['symbol']}:")
            print(f"   Performance: {pos['unrealized_pl_pct']:+.1f}%")
            print(f"   Market Value: ${pos['market_value']:.0f}")
            print(f"   Price: ${pos['last_price']:.2f} (entry: ${pos['avg_entry_price']:.2f})")
            
            # Generate thesis
            thesis_data = await generator.generate_thesis_for_position(pos['symbol'], pos)
            
            print(f"   Sector: {thesis_data['sector']}")
            print(f"   Risk Level: {thesis_data['risk_level']}")
            print(f"   Confidence: {thesis_data['confidence']:.3f}")
            print(f"   Recommendation: {thesis_data['recommendation'].upper()}")
            print(f"   📝 Thesis: {thesis_data['thesis']}")
            print(f"   💭 Reasoning: {thesis_data['reasoning']}")
            
        except Exception as e:
            print(f"   ❌ Error generating thesis for {pos['symbol']}: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Thesis generation test completed!")

if __name__ == "__main__":
    asyncio.run(test_thesis_generation())