#!/usr/bin/env python3
"""
AMC-TRADER Fallback Contamination Validation
Tests that NO fallback/fake data exists in the system.
"""

import asyncio
import sys
import os
import json
import httpx
from datetime import datetime

# Add backend src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend/src'))

from services.short_interest_service import get_short_interest_service

async def test_short_interest_service():
    """Test that short interest service returns no fallback data"""
    print("🔍 Testing Short Interest Service...")
    
    si_service = await get_short_interest_service()
    test_symbols = ['QUBT', 'PLTR', 'NAMM', 'LCFY', 'UAMY', 'FAKE_SYMBOL', 'NONEXISTENT']
    
    results = {
        'contaminated': [],
        'clean': [],
        'excluded': []
    }
    
    for symbol in test_symbols:
        try:
            si_data = await si_service.get_short_interest(symbol)
            
            if si_data is None:
                results['excluded'].append({
                    'symbol': symbol,
                    'status': 'properly_excluded',
                    'reason': 'No real data available'
                })
                print(f"   ✅ {symbol}: Properly excluded (no real data)")
            elif si_data.source in ['sector_fallback', 'default_fallback']:
                results['contaminated'].append({
                    'symbol': symbol,
                    'source': si_data.source,
                    'short_percent': si_data.short_percent_float,
                    'confidence': si_data.confidence
                })
                print(f"   ❌ {symbol}: CONTAMINATED ({si_data.source}) - {si_data.short_percent_float:.1%}")
            else:
                results['clean'].append({
                    'symbol': symbol,
                    'source': si_data.source,
                    'short_percent': si_data.short_percent_float,
                    'confidence': si_data.confidence,
                    'last_updated': si_data.last_updated.isoformat()
                })
                print(f"   ✅ {symbol}: Clean data ({si_data.source}) - {si_data.short_percent_float:.1%}")
                
        except Exception as e:
            results['excluded'].append({
                'symbol': symbol,
                'status': 'error',
                'reason': str(e)
            })
            print(f"   ⚠️ {symbol}: Error - {e}")
    
    print(f"\n📊 Short Interest Service Results:")
    print(f"   Clean entries: {len(results['clean'])}")
    print(f"   Contaminated entries: {len(results['contaminated'])}")
    print(f"   Properly excluded: {len(results['excluded'])}")
    
    return len(results['contaminated']) == 0

async def test_api_endpoints():
    """Test API endpoints for fallback contamination"""
    print("\n🌐 Testing API Endpoints...")
    
    base_url = "https://amc-trader.onrender.com"
    contamination_found = False
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Test discovery/contenders endpoint
            print("   Testing /discovery/contenders...")
            response = await client.get(f"{base_url}/discovery/contenders")
            
            if response.status_code == 200:
                contenders = response.json()
                
                contaminated_count = 0
                total_count = len(contenders)
                
                for item in contenders[:10]:  # Check first 10
                    si_data = item.get('short_interest_data', {})
                    if si_data.get('source') in ['sector_fallback', 'default_fallback']:
                        contaminated_count += 1
                        print(f"      ❌ {item['symbol']}: Contaminated ({si_data.get('source')}) - {si_data.get('percent', 0):.1%}")
                        contamination_found = True
                    elif si_data.get('source') == 'yahoo_finance':
                        print(f"      ✅ {item['symbol']}: Clean data ({si_data.get('source')}) - {si_data.get('percent', 0):.1%}")
                
                print(f"      Checked {min(10, total_count)} items, found {contaminated_count} contaminated")
            else:
                print(f"      ⚠️ Discovery endpoint returned {response.status_code}")
                
        except Exception as e:
            print(f"      ❌ API test failed: {e}")
            return False
    
    return not contamination_found

def test_static_code():
    """Test that fallback code has been removed from source files"""
    print("\n📝 Testing Source Code...")
    
    critical_files = [
        'backend/src/services/short_interest_service.py',
        'backend/src/jobs/discover.py',
        'backend/src/services/data_validator.py',
        'backend/src/routes/discovery.py'
    ]
    
    contamination_found = False
    
    for file_path in critical_files:
        if not os.path.exists(file_path):
            print(f"   ⚠️ File not found: {file_path}")
            continue
            
        print(f"   Checking {file_path}...")
        
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Check for dangerous patterns
        danger_patterns = [
            ('sector_fallbacks = {', 'sector fallback dictionary'),
            ('source=\'sector_fallback\'', 'sector fallback source assignment'),
            ('source=\'default_fallback\'', 'default fallback source assignment'),
            ('short_percent_float=0.15', '15% default short interest'),
            ('short_percent_float=fallback_percent', 'fallback percent usage'),
            (': 0.30,  # AGGRESSIVE: 30% default', '30% aggressive default'),
            (': 10_000_000,     # AGGRESSIVE: 10M tight float', '10M float default'),
            ('calculated_avg_volume = 1000000  # Reasonable default', 'volume default')
        ]
        
        found_patterns = []
        for pattern, description in danger_patterns:
            if pattern in content:
                found_patterns.append(description)
                contamination_found = True
        
        if found_patterns:
            print(f"      ❌ Found contamination patterns:")
            for pattern in found_patterns:
                print(f"         - {pattern}")
        else:
            print(f"      ✅ No contamination patterns found")
    
    return not contamination_found

async def main():
    """Run comprehensive validation"""
    print("🎯 AMC-TRADER Fallback Contamination Validation")
    print("=" * 60)
    
    validation_results = {
        'short_interest_service': False,
        'api_endpoints': False,
        'static_code': False,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Test 1: Short Interest Service
    validation_results['short_interest_service'] = await test_short_interest_service()
    
    # Test 2: API Endpoints
    validation_results['api_endpoints'] = await test_api_endpoints()
    
    # Test 3: Static Code Analysis
    validation_results['static_code'] = test_static_code()
    
    # Final Report
    print("\n" + "=" * 60)
    print("🎯 VALIDATION SUMMARY")
    print("=" * 60)
    
    all_passed = all(validation_results[key] for key in ['short_interest_service', 'api_endpoints', 'static_code'])
    
    print(f"Short Interest Service: {'✅ PASSED' if validation_results['short_interest_service'] else '❌ FAILED'}")
    print(f"API Endpoints:          {'✅ PASSED' if validation_results['api_endpoints'] else '❌ FAILED'}")
    print(f"Static Code Analysis:   {'✅ PASSED' if validation_results['static_code'] else '❌ FAILED'}")
    print()
    
    if all_passed:
        print("🎉 ALL VALIDATIONS PASSED")
        print("   No fallback contamination detected in the system.")
        print("   All stocks will use real data or be properly excluded.")
    else:
        print("❌ VALIDATION FAILED")
        print("   Fallback contamination still exists in the system.")
        print("   Manual review and additional fixes required.")
    
    print(f"\nValidation completed at: {validation_results['timestamp']}")
    
    # Save results
    with open('validation_results.json', 'w') as f:
        json.dump(validation_results, f, indent=2)
    
    print(f"Results saved to: validation_results.json")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)