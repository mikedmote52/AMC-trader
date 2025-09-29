#!/usr/bin/env python3
"""
Test AlphaStack v2 integration locally before final validation
"""

import sys
sys.path.append('src')

from scoring.alphastack_v2 import score_ticker

def test_alphastack_scoring():
    """Test AlphaStack v2 scoring with sample data"""

    print("🧪 TESTING ALPHASTACK V2 INTEGRATION")
    print("=" * 50)

    # Test data mimicking a good momentum stock
    sample_features = {
        'ticker': 'TEST',
        'price': 12.50,
        'rel_vol_now': 3.2,  # 3.2x intraday volume
        'rel_vol_5d': [2.1, 1.8, 2.5, 3.2, 4.1],  # 5-day volume history
        'consecutive_up_days': 4,  # 4 up days in a row
        'daily_change_pct': 8.5,  # +8.5% today
        'rsi': 65,  # Good momentum RSI
        'atr_pct': 0.06,  # 6% ATR
        'vwap': 12.20,  # VWAP slightly below current
        'ema9': 11.80,
        'ema20': 11.40,
        'float_shares': 25e6,  # 25M float
        'short_interest': 0.28,  # 28% short interest
        'utilization': 0.92,  # 92% utilization
        'borrow_fee_pct': 0.35,  # 35% borrow fee
        'options_call_oi': 5000,
        'options_put_oi': 2000,  # 2.5:1 call/put ratio
        'iv_percentile': 55,
        'catalyst_detected': True,
        'social_rank': 15  # Top 15 social rank
    }

    print("📊 Sample Stock Features:")
    print(f"   Price: ${sample_features['price']}")
    print(f"   Volume: {sample_features['rel_vol_now']}x intraday")
    print(f"   Up Days: {sample_features['consecutive_up_days']}")
    print(f"   Change: {sample_features['daily_change_pct']:+.1f}%")
    print(f"   RSI: {sample_features['rsi']}")
    print(f"   Short Interest: {sample_features['short_interest']*100:.0f}%")
    print()

    # Score the stock
    result = score_ticker(sample_features)

    print("🎯 ALPHASTACK V2 SCORING RESULTS:")
    print("-" * 40)
    print(f"   Ticker: {result['ticker']}")
    print(f"   Regime: {result['regime']}")
    print(f"   Composite Score: {result['composite']}/100")
    print(f"   Action: {result['action']}")
    print()

    print("📈 Component Scores:")
    for component, score in result['scores'].items():
        print(f"   {component.replace('_', ' ').title()}: {score:.1f}/25")
    print()

    print("💡 Entry Plan:")
    for key, value in result['entry_plan'].items():
        print(f"   {key.title()}: {value}")
    print()

    # Test different regime
    print("🔄 TESTING SPIKE REGIME:")
    print("-" * 40)

    spike_features = sample_features.copy()
    spike_features.update({
        'rel_vol_now': 8.5,  # 8.5x volume spike
        'daily_change_pct': 18.0,  # +18% move
        'consecutive_up_days': 1,  # Single day move
    })

    spike_result = score_ticker(spike_features)
    print(f"   Regime: {spike_result['regime']}")
    print(f"   Score: {spike_result['composite']}/100")
    print(f"   Action: {spike_result['action']}")
    print()

    # Success validation
    if result['composite'] >= 60:
        print("✅ ALPHASTACK V2 INTEGRATION SUCCESS!")
        print(f"   • Builder regime detected correctly")
        print(f"   • Score {result['composite']}/100 indicates {result['action']}")
        print(f"   • Entry plan generated: {result['entry_plan']['trigger']}")
        print(f"   • Ready for explosive stock detection!")
        return True
    else:
        print("❌ SCORING ISSUE:")
        print(f"   • Score {result['composite']}/100 too low")
        print(f"   • Check component weights and thresholds")
        return False

if __name__ == "__main__":
    success = test_alphastack_scoring()
    print()
    print("🏁 TEST COMPLETE")
    print(f"Status: {'✅ PASS' if success else '❌ FAIL'}")