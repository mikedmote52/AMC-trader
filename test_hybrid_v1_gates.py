#!/usr/bin/env python3
"""
Test suite for hybrid_v1 gate enhancements
Validates observability and new flexibility features
"""

from types import SimpleNamespace
import json
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'src'))

def mk(**kwargs):
    """Helper fixture to create test candidates"""
    base = {
        'symbol': 'TEST',
        'relvol_30': 3.0,
        'volume_spike': 3.0,
        'atr_pct': 0.05,
        'vwap_reclaim': True,
        'price': 10,
        'vwap': 9.9,
        'float_shares': 40_000_000,
        'float': 40_000_000,
        'short_interest': 0.25,
        'borrow_fee': 0.3,
        'utilization': 0.9,
        'has_news_catalyst': True,
        'social_rank': 0.8,
        'call_put_ratio': 2.2
    }
    base.update(kwargs)
    return base

def load_config():
    """Load calibration config"""
    config_path = os.path.join(os.path.dirname(__file__), 'calibration', 'active.json')
    with open(config_path, 'r') as f:
        return json.load(f)

def test_regular_hard_pass():
    """Test normal pass through gates"""
    from jobs.discover import _hybrid_v1_gate_check
    
    config = load_config()
    strategy_config = config['scoring']['hybrid_v1']
    
    candidate = mk()
    passed, reason, meta = _hybrid_v1_gate_check(candidate, {'hybrid_v1': strategy_config})
    
    assert passed, f"Should pass but got: {reason}"
    assert not meta.get('soft_pass'), "Should be hard pass, not soft"
    print("✓ Regular hard pass test passed")

def test_vwap_proximity():
    """Test VWAP proximity tolerance"""
    from jobs.discover import _hybrid_v1_gate_check
    
    config = load_config()
    strategy_config = config['scoring']['hybrid_v1']
    
    # Enable VWAP proximity
    strategy_config['thresholds']['vwap_proximity_pct'] = 0.5
    
    # Price within 0.4% of VWAP (should pass with proximity)
    candidate = mk(vwap_reclaim=False, price=99.6, vwap=100.0)
    passed, reason, meta = _hybrid_v1_gate_check(candidate, {'hybrid_v1': strategy_config})
    
    assert passed, f"Should pass with VWAP proximity but got: {reason}"
    assert meta.get('vwap_proximity_used'), "Should use VWAP proximity"
    print("✓ VWAP proximity test passed")

def test_mid_float_alt():
    """Test mid-float alternative path"""
    from jobs.discover import _hybrid_v1_gate_check
    
    config = load_config()
    strategy_config = config['scoring']['hybrid_v1']
    
    # Enable mid-float path
    strategy_config['thresholds']['mid_float_path']['enabled'] = True
    
    # Mid-float with catalyst
    candidate = mk(
        float_shares=100_000_000,
        float=100_000_000,
        short_interest=0.15,
        borrow_fee=0.12,
        utilization=0.8,
        has_news_catalyst=True
    )
    
    passed, reason, meta = _hybrid_v1_gate_check(candidate, {'hybrid_v1': strategy_config})
    
    assert passed, f"Should pass mid-float path but got: {reason}"
    assert meta.get('mid_alt'), "Should use mid-float alternative"
    print("✓ Mid-float alternative test passed")

def test_soft_pass():
    """Test soft-pass for near misses"""
    from jobs.discover import _hybrid_v1_gate_check
    
    config = load_config()
    strategy_config = config['scoring']['hybrid_v1']
    
    # Enable soft passes
    strategy_config['thresholds']['max_soft_pass'] = 5
    strategy_config['thresholds']['soft_gate_tolerance'] = 0.10
    
    # Near miss on relvol (2.3 vs 2.5) and ATR (0.039 vs 0.04)
    candidate = mk(
        relvol_30=2.3,
        volume_spike=2.3,
        atr_pct=0.039,
        vwap_reclaim=True,
        has_news_catalyst=True
    )
    
    passed, reason, meta = _hybrid_v1_gate_check(candidate, {'hybrid_v1': strategy_config})
    
    assert passed, f"Should soft pass but got: {reason}"
    assert meta.get('soft_pass'), "Should be soft pass"
    assert reason == 'soft_pass', f"Reason should be 'soft_pass' but got: {reason}"
    print("✓ Soft pass test passed")

def test_session_overrides():
    """Test session-aware threshold overrides"""
    from jobs.discover import _resolve_thresholds
    
    config = load_config()
    base_thresholds = config['scoring']['hybrid_v1']['thresholds']
    
    # Test with premarket enabled
    base_thresholds['session_overrides']['premarket']['enabled'] = True
    resolved = _resolve_thresholds(base_thresholds, 'premarket')
    
    assert resolved['min_relvol_30'] == 2.0, "Should use premarket relvol"
    assert resolved['min_atr_pct'] == 0.03, "Should use premarket ATR"
    assert resolved['require_vwap_reclaim'] == False, "Should disable VWAP in premarket"
    
    # Test with premarket disabled (default)
    base_thresholds['session_overrides']['premarket']['enabled'] = False
    resolved = _resolve_thresholds(base_thresholds, 'premarket')
    
    assert resolved['min_relvol_30'] == 2.5, "Should use default relvol"
    assert resolved['min_atr_pct'] == 0.04, "Should use default ATR"
    print("✓ Session override test passed")

def run_all_tests():
    """Run all test cases"""
    print("\n=== Running Hybrid V1 Gate Enhancement Tests ===\n")
    
    tests = [
        test_regular_hard_pass,
        test_vwap_proximity,
        test_mid_float_alt,
        test_soft_pass,
        test_session_overrides
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            return False
    
    print("\n=== All tests passed! ===\n")
    return True

if __name__ == "__main__":
    # Check if running locally
    if os.path.exists('calibration/active.json'):
        run_all_tests()
    else:
        print("Tests require local environment with calibration/active.json")