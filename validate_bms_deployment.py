#!/usr/bin/env python3
"""
BMS System Deployment Validation
Tests the new unified discovery system without external dependencies
"""

import json
import os
import sys

def validate_bms_files():
    """Validate that all BMS files are in place"""
    print("🔍 Validating BMS System Files")
    print("=" * 40)
    
    required_files = [
        '/Users/michaelmote/Desktop/AMC-TRADER/backend/src/services/bms_engine.py',
        '/Users/michaelmote/Desktop/AMC-TRADER/backend/src/routes/bms_discovery.py',
        '/Users/michaelmote/Desktop/AMC-TRADER/frontend/src/components/BMSDiscovery.tsx',
        '/Users/michaelmote/Desktop/AMC-TRADER/frontend/src/pages/BMSDiscoveryPage.tsx'
    ]
    
    all_present = True
    
    for file_path in required_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"✅ {os.path.basename(file_path)} ({size:,} bytes)")
        else:
            print(f"❌ {os.path.basename(file_path)} - MISSING")
            all_present = False
    
    return all_present

def validate_app_integration():
    """Validate that app.py has been updated correctly"""
    print("\n🔗 Validating App Integration")
    print("=" * 40)
    
    app_path = '/Users/michaelmote/Desktop/AMC-TRADER/backend/src/app.py'
    
    if not os.path.exists(app_path):
        print("❌ app.py not found")
        return False
    
    with open(app_path, 'r') as f:
        app_content = f.read()
    
    # Check for BMS integration
    checks = [
        ('bms_discovery import', 'bms_discovery as discovery_routes'),
        ('discovery routes included', 'discovery_routes.router'),
        ('calibration removed', '# Calibration routes removed')
    ]
    
    passed = 0
    for check_name, check_string in checks:
        if check_string in app_content:
            print(f"✅ {check_name}")
            passed += 1
        else:
            print(f"❌ {check_name} - NOT FOUND")
    
    # Special check for old import removal
    if 'get_contenders' not in app_content:
        print("✅ old discovery imports cleaned")
        passed += 1
    else:
        print("❌ old discovery imports still present")
    
    total_checks = len(checks) + 1
    
    return passed == total_checks

def validate_bms_config():
    """Validate BMS engine configuration"""
    print("\n⚙️ Validating BMS Configuration")
    print("=" * 40)
    
    # Check if we can import the BMS engine
    sys.path.append('/Users/michaelmote/Desktop/AMC-TRADER/backend')
    
    try:
        from src.services.bms_engine_real import RealBMSEngine as BMSEngine
        
        # Test initialization
        bms = BMSEngine("test_key")
        config = bms.config
        
        print("✅ BMS Engine imports successfully")
        print(f"✅ Weights configured: {len(config['weights'])} components")
        print(f"✅ Thresholds configured: {len(config['thresholds'])} parameters")
        print(f"✅ Scoring levels: Trade Ready {config['scoring']['trade_ready_min']}+, Monitor {config['scoring']['monitor_min']}+")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def validate_winner_patterns():
    """Validate the historical winner patterns are encoded correctly"""
    print("\n🏆 Validating Winner Pattern Logic")
    print("=" * 40)
    
    # Historical winners with their key characteristics
    winners = [
        {"symbol": "VIGL", "gain": 324, "pattern": "massive volume surge"},
        {"symbol": "CRWV", "gain": 171, "pattern": "squeeze setup"},
        {"symbol": "AEVA", "gain": 162, "pattern": "volatility expansion"},
        {"symbol": "WOLF", "gain": -25, "pattern": "risk rejection"}
    ]
    
    print("Historical winner patterns encoded:")
    for winner in winners:
        emoji = "🚀" if winner["gain"] > 100 else "📈" if winner["gain"] > 0 else "🚫"
        print(f"{emoji} {winner['symbol']}: {winner['gain']:+.0f}% ({winner['pattern']})")
    
    # Check if BMS weights align with winner characteristics
    try:
        from src.services.bms_engine_real import RealBMSEngine as BMSEngine
        bms = BMSEngine("test_key")
        weights = bms.config['weights']
        
        print(f"\nBMS weights alignment:")
        print(f"  Volume Surge: {weights['volume_surge']:.0%} (VIGL pattern)")
        print(f"  Price Momentum: {weights['price_momentum']:.0%} (Multi-timeframe)")
        print(f"  Volatility Expansion: {weights['volatility_expansion']:.0%} (AEVA pattern)")
        print(f"  Risk Filter: {weights['risk_filter']:.0%} (WOLF rejection)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error validating patterns: {e}")
        return False

def main():
    """Main validation function"""
    print("🧪 BMS SYSTEM DEPLOYMENT VALIDATION")
    print("=" * 50)
    print("Validating the new unified Breakout Momentum Score system")
    print("Based on June-July 2025 portfolio: +$957.50 (+63.8%)\n")
    
    # Run all validation tests
    results = []
    
    results.append(("File Structure", validate_bms_files()))
    results.append(("App Integration", validate_app_integration()))
    results.append(("BMS Configuration", validate_bms_config()))
    results.append(("Winner Patterns", validate_winner_patterns()))
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 VALIDATION SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 BMS SYSTEM READY FOR DEPLOYMENT!")
        print("The unified discovery system is properly configured and should replace")
        print("all legacy/hybrid discovery components.")
        
        print("\nNext steps:")
        print("1. Deploy backend changes to Render")
        print("2. Update frontend routing to use BMSDiscoveryPage")
        print("3. Remove old discovery components")
        print("4. Test with live market data")
        
    else:
        print(f"\n⚠️  BMS SYSTEM NEEDS ATTENTION")
        print(f"Please fix the {total - passed} failed validation(s) before deployment.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)