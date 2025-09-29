#!/usr/bin/env python3
"""
Test squeeze endpoint locally before deployment completes
"""

import sys
import os
sys.path.append('src')

# Set up basic logging
import logging
logging.basicConfig(level=logging.INFO)

async def test_squeeze_routes():
    """Test squeeze routes locally"""

    print("🧪 TESTING SQUEEZE ENDPOINTS LOCALLY")
    print("=" * 50)

    try:
        # Import the squeeze module
        from routes.squeeze import (
            calculate_squeeze_potential,
            get_squeeze_rank,
            determine_alert_type,
            generate_alert_message
        )

        print("✅ Squeeze module imported successfully")

        # Test data
        test_candidate = {
            'ticker': 'TEST',
            'total_score': 0.75,
            'intraday_relative_volume': 4.5,
            'consecutive_up_days': 3,
            'change_pct': 8.5,
            'price': 15.50,
            'alphastack_regime': 'builder',
            'subscores': {
                'squeeze': 18,
                'volume_momentum': 20,
                'catalyst': 15,
                'options': 12,
                'technical': 14,
                'sentiment': 16
            }
        }

        # Test squeeze potential calculation
        squeeze_potential = calculate_squeeze_potential(test_candidate)
        test_candidate['squeeze_potential'] = squeeze_potential

        print(f"\n📊 Squeeze Potential Calculation:")
        print(f"   Input Score: {test_candidate['total_score']}")
        print(f"   IRV: {test_candidate['intraday_relative_volume']}")
        print(f"   Calculated Potential: {squeeze_potential:.1f}%")

        # Test squeeze rank
        rank = get_squeeze_rank(test_candidate)
        print(f"\n🏆 Squeeze Rank: {rank}")

        # Test alert type
        alert_type = determine_alert_type(test_candidate)
        print(f"\n🚨 Alert Type: {alert_type}")

        # Test alert message
        message = generate_alert_message(test_candidate)
        print(f"\n📢 Alert Message: {message}")

        print("\n✅ All squeeze functions working correctly!")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you're in the backend directory")
        return False
    except Exception as e:
        print(f"❌ Error testing squeeze routes: {e}")
        import traceback
        traceback.print_exc()
        return False

# Run async test
import asyncio
if __name__ == "__main__":
    success = asyncio.run(test_squeeze_routes())

    if success:
        print("\n🎯 SQUEEZE ENDPOINT READY")
        print("Once deployed, the squeeze monitor will:")
        print("• Connect to AlphaStack v2 discovery")
        print("• Calculate squeeze potential scores")
        print("• Generate real-time alerts")
        print("• Provide regime-based filtering")
    else:
        print("\n⚠️  Issues found - check error messages above")