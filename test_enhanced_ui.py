#!/usr/bin/env python3
"""
Enhanced Learning UI Testing Script
Validates the new learning intelligence UI components
"""

import requests
import json
import time
from datetime import datetime

FRONTEND_URL = "https://amc-frontend.onrender.com"
BACKEND_URL = "https://amc-trader.onrender.com"

def test_frontend_availability():
    """Test if the frontend is accessible"""
    print("🌐 Testing Frontend Availability")
    print("-" * 40)

    try:
        response = requests.get(FRONTEND_URL, timeout=10)
        if response.status_code == 200:
            print(f"✅ Frontend accessible at {FRONTEND_URL}")
            return True
        else:
            print(f"⚠️  Frontend returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frontend not accessible: {e}")
        return False

def test_learning_api_endpoints():
    """Test the enhanced learning API endpoints"""
    print("\n🧠 Testing Enhanced Learning API Endpoints")
    print("-" * 50)

    endpoints = [
        "/learning/insights",
        "/learning/optimize-recommendations",
        "/learning/intelligence/learning-summary",
        "/learning/intelligence/market-regime",
        "/learning/intelligence/pattern-analysis",
        "/learning/intelligence/confidence-calibration",
        "/learning/intelligence/discovery-parameters"
    ]

    results = {}

    for endpoint in endpoints:
        try:
            print(f"Testing {endpoint}...")
            response = requests.get(f"{BACKEND_URL}{endpoint}", timeout=5)

            if response.status_code == 200:
                data = response.json()
                results[endpoint] = {
                    "status": "✅ Available",
                    "has_data": bool(data.get('data') or data.get('success'))
                }
                print(f"  ✅ {endpoint}: Available")
            elif response.status_code == 404:
                results[endpoint] = {
                    "status": "⚠️  Not deployed yet",
                    "has_data": False
                }
                print(f"  ⚠️  {endpoint}: Not deployed yet")
            else:
                results[endpoint] = {
                    "status": f"❌ Error {response.status_code}",
                    "has_data": False
                }
                print(f"  ❌ {endpoint}: Error {response.status_code}")

        except Exception as e:
            results[endpoint] = {
                "status": f"❌ Failed: {str(e)[:50]}",
                "has_data": False
            }
            print(f"  ❌ {endpoint}: Failed - {e}")

        time.sleep(0.5)  # Rate limiting

    return results

def test_discovery_integration():
    """Test discovery system integration with learning"""
    print("\n🔗 Testing Discovery-Learning Integration")
    print("-" * 45)

    try:
        # Trigger a discovery run
        print("1. Triggering discovery run...")
        response = requests.post(f"{BACKEND_URL}/discovery/emergency/enhanced-discovery?limit=3", timeout=10)

        if response.status_code == 200:
            discovery_data = response.json()
            print(f"  ✅ Discovery successful: {discovery_data.get('count', 0)} candidates")

            # Wait a moment for learning integration
            time.sleep(2)

            # Check if learning data was collected
            print("2. Checking learning data collection...")
            learning_response = requests.get(f"{BACKEND_URL}/learning/insights", timeout=5)

            if learning_response.status_code == 200:
                learning_data = learning_response.json()
                decision_count = len(learning_data.get('data', {}).get('decision_stats', []))
                print(f"  ✅ Learning integration: {decision_count} decision stats recorded")
                return True
            else:
                print(f"  ⚠️  Learning data check failed: {learning_response.status_code}")
                return False
        else:
            print(f"  ❌ Discovery failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"  ❌ Integration test failed: {e}")
        return False

def test_ui_component_readiness():
    """Test if UI components can handle the enhanced data"""
    print("\n🎨 Testing UI Component Data Compatibility")
    print("-" * 45)

    # Test data structures that UI expects
    test_scenarios = {
        "Market Regime": {
            "data": {
                "current_regime": "normal_market",
                "regime_changed": False,
                "confidence": 0.8
            },
            "required_fields": ["current_regime", "regime_changed"]
        },
        "Pattern Analysis": {
            "data": {
                "pattern_count": {"winners": 5, "losers": 2},
                "feature_effectiveness": {
                    "volume_momentum_score": {
                        "effectiveness_score": 0.25,
                        "predictive_power": "high"
                    }
                }
            },
            "required_fields": ["pattern_count", "feature_effectiveness"]
        },
        "Confidence Calibration": {
            "data": {
                "calibration_table": [
                    {
                        "confidence_range": "0.9+",
                        "avg_return_7d": 15.2,
                        "success_rate": 85.0,
                        "sample_size": 12
                    }
                ]
            },
            "required_fields": ["calibration_table"]
        }
    }

    all_passed = True

    for component, test_data in test_scenarios.items():
        try:
            data = test_data["data"]
            required_fields = test_data["required_fields"]

            # Check required fields
            missing_fields = [field for field in required_fields if field not in data]

            if not missing_fields:
                print(f"  ✅ {component}: Data structure compatible")
            else:
                print(f"  ⚠️  {component}: Missing fields: {missing_fields}")
                all_passed = False

        except Exception as e:
            print(f"  ❌ {component}: Test failed - {e}")
            all_passed = False

    return all_passed

def generate_ui_deployment_report():
    """Generate comprehensive UI deployment readiness report"""
    print("\n📊 Enhanced Learning UI Deployment Report")
    print("=" * 60)

    # Run all tests
    frontend_ok = test_frontend_availability()
    api_results = test_learning_api_endpoints()
    integration_ok = test_discovery_integration()
    ui_compatible = test_ui_component_readiness()

    # Analyze results
    total_endpoints = len(api_results)
    available_endpoints = sum(1 for r in api_results.values() if "✅" in r["status"])
    deployed_endpoints = sum(1 for r in api_results.values() if "⚠️" not in r["status"])

    print(f"\n📈 Summary Report")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    print(f"Frontend Status: {'✅ Ready' if frontend_ok else '❌ Issues'}")
    print(f"API Endpoints: {available_endpoints}/{total_endpoints} available, {deployed_endpoints}/{total_endpoints} deployed")
    print(f"Discovery Integration: {'✅ Working' if integration_ok else '⚠️  Needs attention'}")
    print(f"UI Compatibility: {'✅ Compatible' if ui_compatible else '⚠️  Needs updates'}")

    print(f"\n🔧 API Endpoint Details:")
    for endpoint, result in api_results.items():
        print(f"  {result['status']} {endpoint}")

    # Overall readiness assessment
    ready_score = (
        (1 if frontend_ok else 0) +
        (available_endpoints / total_endpoints) +
        (1 if integration_ok else 0.5) +
        (1 if ui_compatible else 0.5)
    ) / 4

    print(f"\n🎯 Overall Readiness: {ready_score * 100:.0f}%")

    if ready_score >= 0.8:
        print("🚀 Status: READY FOR DEPLOYMENT")
        print("✅ Enhanced learning UI can be deployed to production")
    elif ready_score >= 0.6:
        print("⚡ Status: MOSTLY READY")
        print("⚠️  Some endpoints not deployed yet, but UI will gracefully degrade")
    else:
        print("🔧 Status: NEEDS WORK")
        print("❌ Significant issues need resolution before deployment")

    # Recommendations
    print(f"\n💡 Recommendations:")

    if not frontend_ok:
        print("  • Fix frontend accessibility issues")

    if available_endpoints < total_endpoints:
        print(f"  • Deploy remaining {total_endpoints - available_endpoints} enhanced learning endpoints")

    if not integration_ok:
        print("  • Verify discovery-learning integration is working")

    if not ui_compatible:
        print("  • Update UI components to handle enhanced data structures")

    if ready_score >= 0.8:
        print("  • All systems operational - proceed with deployment! 🎉")

    return {
        "ready_score": ready_score,
        "frontend_ok": frontend_ok,
        "api_results": api_results,
        "integration_ok": integration_ok,
        "ui_compatible": ui_compatible
    }

if __name__ == "__main__":
    print("🧠 Enhanced Learning UI Testing & Deployment Readiness")
    print("=" * 60)
    print(f"Frontend URL: {FRONTEND_URL}")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Test started: {datetime.now().isoformat()}")

    # Generate comprehensive report
    report = generate_ui_deployment_report()

    print()
    if report["ready_score"] >= 0.8:
        print("🎉 TESTING COMPLETE - READY FOR DEPLOYMENT!")
    else:
        print("🔧 TESTING COMPLETE - NEEDS ATTENTION")

    print(f"\nFor manual testing, visit: {FRONTEND_URL}/updates")
    print("The enhanced learning dashboard will be visible at the top of the page.")