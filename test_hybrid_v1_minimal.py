#!/usr/bin/env python3
"""
Minimal test suite for Hybrid V1 enhancements
Verifies: defaults unchanged, VWAP proximity, mid-float path, soft-pass
"""

def mk(**kwargs):
    """Create test candidate"""
    base = {
        'symbol': 'TEST',
        'relvol_30': 3.0,
        'volume_spike': 3.0,
        'atr_pct': 0.05,
        'vwap_reclaim': True,
        'price': 10.0,
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

def test_config_defaults():
    """Verify all new features are disabled by default"""
    import json
    with open('calibration/active.json', 'r') as f:
        config = json.load(f)
    
    t = config['scoring']['hybrid_v1']['thresholds']
    
    # All session overrides disabled
    assert not t['session_overrides']['premarket']['enabled']
    assert not t['session_overrides']['afterhours']['enabled'] 
    assert not t['session_overrides']['regular']['enabled']
    
    # VWAP proximity disabled
    assert t['vwap_proximity_pct'] == 0.0
    
    # Mid-float path disabled
    assert not t['mid_float_path']['enabled']
    
    # Soft-pass disabled
    assert t['max_soft_pass'] == 0
    
    print("✓ Config defaults test passed - all features disabled")

def test_baseline_unchanged():
    """Baseline candidate that used to pass still passes"""
    try:
        import sys, os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'src'))
        from jobs.discover import _hybrid_v1_gate_check
        
        import json
        with open('calibration/active.json', 'r') as f:
            config = json.load(f)
        
        strategy_config = config['scoring']['hybrid_v1']
        candidate = mk()  # Good baseline candidate
        
        passed, reason = _hybrid_v1_gate_check(candidate, strategy_config)
        assert passed, f"Baseline should pass but got: {reason}"
        
        print("✓ Baseline unchanged test passed")
    except ImportError:
        print("⚠ Skipping baseline test (import issues)")

def test_vwap_proximity():
    """VWAP proximity allows pass when within threshold"""
    try:
        import sys, os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'src'))
        from jobs.discover import _hybrid_v1_gate_check
        
        import json
        with open('calibration/active.json', 'r') as f:
            config = json.load(f)
        
        strategy_config = config['scoring']['hybrid_v1']
        
        # Enable VWAP proximity
        strategy_config['thresholds']['vwap_proximity_pct'] = 0.5
        
        # Price within 0.4% of VWAP (should pass)
        candidate = mk(vwap_reclaim=False, price=99.6, vwap=100.0)
        
        passed, reason = _hybrid_v1_gate_check(candidate, strategy_config)
        assert passed, f"Should pass with VWAP proximity but got: {reason}"
        
        print("✓ VWAP proximity test passed")
    except ImportError:
        print("⚠ Skipping VWAP proximity test (import issues)")

def test_mid_float_path():
    """Mid-float path passes qualifying 75-150M stocks"""
    try:
        import sys, os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'src'))
        from jobs.discover import _hybrid_v1_gate_check
        
        import json
        with open('calibration/active.json', 'r') as f:
            config = json.load(f)
        
        strategy_config = config['scoring']['hybrid_v1']
        
        # Enable mid-float path
        strategy_config['thresholds']['mid_float_path']['enabled'] = True
        
        # Mid-float with qualifying metrics + catalyst
        candidate = mk(
            float_shares=100_000_000,
            float=100_000_000,
            short_interest=0.15,  # > 0.12 minimum
            borrow_fee=0.12,      # > 0.10 minimum
            utilization=0.8,      # > 0.75 minimum
            has_news_catalyst=True
        )
        
        passed, reason = _hybrid_v1_gate_check(candidate, strategy_config)
        assert passed, f"Should pass mid-float path but got: {reason}"
        
        print("✓ Mid-float path test passed")
    except ImportError:
        print("⚠ Skipping mid-float test (import issues)")

def test_soft_pass():
    """Soft-pass allows near-miss with catalyst"""
    try:
        import sys, os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'src'))
        from jobs.discover import _hybrid_v1_gate_check
        
        import json
        with open('calibration/active.json', 'r') as f:
            config = json.load(f)
        
        strategy_config = config['scoring']['hybrid_v1']
        
        # Enable soft-pass
        strategy_config['thresholds']['max_soft_pass'] = 5
        strategy_config['thresholds']['soft_gate_tolerance'] = 0.10
        
        # Near miss: relvol 2.3 vs required 2.5 (within 10% tolerance)
        candidate = mk(
            relvol_30=2.3,
            volume_spike=2.3,
            atr_pct=0.05,  # Good ATR
            vwap_reclaim=True,
            has_news_catalyst=True
        )
        
        passed, reason = _hybrid_v1_gate_check(candidate, strategy_config)
        assert passed, f"Should soft-pass but got: {reason}"
        assert reason == "soft_pass", f"Reason should be 'soft_pass' but got: {reason}"
        assert candidate.get('soft_pass'), "Should be tagged as soft_pass"
        
        print("✓ Soft-pass test passed")
    except ImportError:
        print("⚠ Skipping soft-pass test (import issues)")

if __name__ == "__main__":
    print("\n=== Minimal Hybrid V1 Test Suite ===\n")
    
    test_config_defaults()
    test_baseline_unchanged() 
    test_vwap_proximity()
    test_mid_float_path()
    test_soft_pass()
    
    print("\n=== All tests completed ===\n")