#!/usr/bin/env python3
"""
Test script to validate VIGL squeeze implementation
"""

import sys
import os
import json

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.squeeze_detector import SqueezeDetector
from services.squeeze_validator import validate_squeeze_detector

def test_squeeze_implementation():
    print("🎯 TESTING VIGL SQUEEZE PATTERN IMPLEMENTATION")
    print("=" * 60)
    
    # Test 1: Basic squeeze detector functionality
    print("\n1. Testing SqueezeDetector instantiation...")
    detector = SqueezeDetector()
    print(f"   ✅ Detector created successfully")
    print(f"   📊 VIGL criteria: {detector.VIGL_CRITERIA}")
    print(f"   🎯 Confidence levels: {detector.CONFIDENCE_LEVELS}")
    
    # Test 2: Test against VIGL pattern (should detect)
    print("\n2. Testing against VIGL pattern (+324% winner)...")
    vigl_data = {
        'symbol': 'VIGL',
        'price': 3.50,
        'volume': 10_450_000,  # 20.9x spike
        'avg_volume_30d': 500_000,
        'short_interest': 0.35,  # 35%
        'float': 25_000_000,
        'borrow_rate': 1.50,  # 150%
        'market_cap': 87_500_000
    }
    
    vigl_result = detector.detect_vigl_pattern('VIGL', vigl_data)
    
    if vigl_result:
        print(f"   ✅ VIGL pattern DETECTED!")
        print(f"   🔥 Squeeze Score: {vigl_result.squeeze_score:.3f}")
        print(f"   📊 Pattern: {vigl_result.pattern_match}")
        print(f"   💯 Confidence: {vigl_result.confidence}")
        print(f"   📈 Volume Spike: {vigl_result.volume_spike:.1f}x")
        print(f"   💡 Thesis: {vigl_result.thesis}")
    else:
        print("   ❌ VIGL pattern NOT detected - needs tuning!")
    
    # Test 3: Test against weak pattern (should NOT detect)
    print("\n3. Testing against weak pattern (should reject)...")
    weak_data = {
        'symbol': 'WEAK',
        'price': 15.00,  # Too high
        'volume': 1_200_000,  # Only 1.2x volume
        'avg_volume_30d': 1_000_000,
        'short_interest': 0.05,  # Only 5% SI
        'float': 200_000_000,  # Too large float
        'borrow_rate': 0.10,  # Low borrow rate
        'market_cap': 3_000_000_000  # Too large
    }
    
    weak_result = detector.detect_vigl_pattern('WEAK', weak_data)
    
    if not weak_result:
        print("   ✅ Weak pattern correctly REJECTED!")
    else:
        print(f"   ⚠️  Weak pattern detected (score: {weak_result.squeeze_score:.3f}) - may be too permissive")
    
    # Test 4: Full validation against historical winners
    print("\n4. Running full historical validation...")
    try:
        validation_results = validate_squeeze_detector()
        
        summary = validation_results['validation_summary']
        print(f"   📊 Total Winners Tested: {summary['total_tested']}")
        print(f"   ✅ Passed: {summary['passed']}")
        print(f"   ❌ Failed: {summary['failed']}")
        print(f"   ⚠️  Review Needed: {summary['review_needed']}")
        print(f"   📈 Avg Historical Return: {summary['avg_historical_return']}%")
        print(f"   🎯 Avg Detected Score: {summary['avg_detected_score']}")
        
        print(f"\n   🔍 Recommendations:")
        for rec in validation_results['recommendations']:
            print(f"   {rec}")
            
        # Show individual results
        print(f"\n   📋 Individual Results:")
        for symbol, result in validation_results['individual_results'].items():
            status = result['validation_status']
            score = result.get('detected_squeeze_score', 0)
            pattern = result.get('detected_pattern', 'N/A')
            print(f"   {symbol}: {status} (score: {score:.3f}, pattern: {pattern})")
        
    except Exception as e:
        print(f"   ❌ Validation error: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 SQUEEZE IMPLEMENTATION TEST COMPLETE")
    print("   Ready for deployment if VIGL pattern detection succeeded!")

if __name__ == "__main__":
    test_squeeze_implementation()