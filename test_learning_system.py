#!/usr/bin/env python3
"""
AMC-TRADER Learning System Validation Test
Tests the enhanced learning intelligence system functionality
"""

import asyncio
import requests
import json
import time
from datetime import datetime

API_BASE = "https://amc-trader.onrender.com"

def test_basic_endpoints():
    """Test basic learning system endpoints"""
    print("🧪 Testing Basic Learning System Endpoints")
    print("-" * 50)

    # Test basic learning insights
    print("1. Testing basic learning insights...")
    response = requests.get(f"{API_BASE}/learning/insights")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Learning insights: {data['success']}")
        print(f"   - Decision stats: {len(data['data']['decision_stats'])} entries")
        print(f"   - Best patterns: {len(data['data']['best_patterns'])} entries")
    else:
        print(f"❌ Learning insights failed: {response.status_code}")

    # Test optimization recommendations
    print("\n2. Testing optimization recommendations...")
    response = requests.get(f"{API_BASE}/learning/optimize-recommendations")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Optimization recommendations: {data['success']}")
        optim = data['data']['optimizations']
        print(f"   - Market times: {len(optim['best_market_times'])} entries")
        print(f"   - Successful patterns: {len(optim['successful_patterns'])} entries")
    else:
        print(f"❌ Optimization recommendations failed: {response.status_code}")

def test_discovery_integration():
    """Test discovery system integration with learning"""
    print("\n🔗 Testing Discovery System Integration")
    print("-" * 50)

    print("1. Triggering discovery run...")
    start_time = time.time()
    response = requests.post(f"{API_BASE}/discovery/emergency/enhanced-discovery?limit=5")

    if response.status_code == 200:
        data = response.json()
        execution_time = time.time() - start_time
        print(f"✅ Discovery run successful:")
        print(f"   - Status: {data['status']}")
        print(f"   - Candidates found: {data['count']}")
        print(f"   - Trade ready: {data.get('trade_ready_count', 0)}")
        print(f"   - Execution time: {execution_time:.2f}s")
        print(f"   - Pipeline flow: {data.get('trace', {}).get('pipeline_flow', 'N/A')}")

        # Check if candidates have required structure for learning
        if data.get('candidates'):
            candidate = data['candidates'][0]
            required_fields = ['symbol', 'score', 'action_tag', 'subscores']
            missing_fields = [field for field in required_fields if field not in candidate]

            if not missing_fields:
                print("✅ Candidate structure compatible with learning system")
                print(f"   - Sample candidate: {candidate['symbol']} (score: {candidate['score']:.3f})")
                if 'subscores' in candidate:
                    subscores = candidate['subscores']
                    print(f"   - Subscores: {len(subscores)} components")
            else:
                print(f"⚠️  Missing fields for learning: {missing_fields}")
    else:
        print(f"❌ Discovery run failed: {response.status_code}")

def test_system_health():
    """Test overall system health"""
    print("\n💗 Testing System Health")
    print("-" * 50)

    # Test health endpoint
    print("1. Testing health endpoint...")
    response = requests.get(f"{API_BASE}/health")
    if response.status_code == 200:
        health_data = response.json()
        print(f"✅ System health: {health_data.get('status', 'unknown')}")
        if 'database' in health_data:
            print(f"   - Database: {health_data['database']}")
        if 'redis' in health_data:
            print(f"   - Redis: {health_data['redis']}")
    else:
        print(f"❌ Health check failed: {response.status_code}")

    # Test discovery contenders endpoint
    print("\n2. Testing discovery contenders...")
    response = requests.get(f"{API_BASE}/discovery/contenders?limit=3")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Discovery contenders: {len(data.get('candidates', []))} candidates")
        if data.get('candidates'):
            for i, candidate in enumerate(data['candidates'][:2]):
                print(f"   - {i+1}. {candidate.get('symbol', 'N/A')} (score: {candidate.get('score', 0):.3f})")
    else:
        print(f"❌ Discovery contenders failed: {response.status_code}")

def test_data_persistence():
    """Test if learning data is being persisted"""
    print("\n💾 Testing Data Persistence")
    print("-" * 50)

    # Run multiple discovery calls to generate data
    print("1. Running multiple discoveries to generate learning data...")
    for i in range(3):
        print(f"   Discovery run {i+1}/3...")
        response = requests.post(f"{API_BASE}/discovery/emergency/enhanced-discovery?limit=3")
        if response.status_code == 200:
            print(f"   ✅ Run {i+1} successful")
        else:
            print(f"   ❌ Run {i+1} failed")
        time.sleep(2)  # Brief pause between runs

    # Check if learning insights have accumulated data
    print("\n2. Checking for accumulated learning data...")
    response = requests.get(f"{API_BASE}/learning/insights")
    if response.status_code == 200:
        data = response.json()
        stats_count = len(data['data']['decision_stats'])
        patterns_count = len(data['data']['best_patterns'])

        if stats_count > 0 or patterns_count > 0:
            print(f"✅ Learning data accumulated:")
            print(f"   - Decision stats: {stats_count} entries")
            print(f"   - Pattern data: {patterns_count} entries")
        else:
            print("⚠️  No learning data accumulated yet (this may be normal for new deployments)")
    else:
        print(f"❌ Failed to check learning data: {response.status_code}")

def generate_learning_report():
    """Generate a comprehensive learning system report"""
    print("\n📊 Learning System Validation Report")
    print("=" * 60)

    report = {
        "timestamp": datetime.now().isoformat(),
        "system_status": "unknown",
        "capabilities": {},
        "integration_status": {},
        "recommendations": []
    }

    # Basic functionality test
    try:
        response = requests.get(f"{API_BASE}/learning/insights")
        if response.status_code == 200:
            report["capabilities"]["basic_insights"] = "operational"
        else:
            report["capabilities"]["basic_insights"] = "failed"
    except:
        report["capabilities"]["basic_insights"] = "unreachable"

    # Discovery integration test
    try:
        response = requests.post(f"{API_BASE}/discovery/emergency/enhanced-discovery?limit=1")
        if response.status_code == 200:
            report["integration_status"]["discovery_system"] = "connected"
        else:
            report["integration_status"]["discovery_system"] = "failed"
    except:
        report["integration_status"]["discovery_system"] = "unreachable"

    # Overall status
    operational_count = sum(1 for v in {**report["capabilities"], **report["integration_status"]}.values() if v == "operational" or v == "connected")
    total_count = len(report["capabilities"]) + len(report["integration_status"])

    if operational_count == total_count:
        report["system_status"] = "fully_operational"
    elif operational_count > total_count / 2:
        report["system_status"] = "partially_operational"
    else:
        report["system_status"] = "degraded"

    # Recommendations
    if report["capabilities"]["basic_insights"] != "operational":
        report["recommendations"].append("Initialize learning database tables")

    if report["integration_status"]["discovery_system"] != "connected":
        report["recommendations"].append("Check discovery system deployment")

    if not report["recommendations"]:
        report["recommendations"].append("System operational - continue monitoring")

    print(f"System Status: {report['system_status'].upper()}")
    print(f"Timestamp: {report['timestamp']}")
    print()
    print("Capabilities:")
    for capability, status in report["capabilities"].items():
        icon = "✅" if status == "operational" else "❌"
        print(f"  {icon} {capability}: {status}")

    print()
    print("Integration Status:")
    for integration, status in report["integration_status"].items():
        icon = "✅" if status == "connected" else "❌"
        print(f"  {icon} {integration}: {status}")

    print()
    print("Recommendations:")
    for rec in report["recommendations"]:
        print(f"  • {rec}")

    return report

if __name__ == "__main__":
    print("🧠 AMC-TRADER Learning System Validation")
    print("=" * 60)
    print(f"Testing against: {API_BASE}")
    print(f"Test started: {datetime.now().isoformat()}")
    print()

    # Run all tests
    test_basic_endpoints()
    test_discovery_integration()
    test_system_health()
    test_data_persistence()

    # Generate final report
    print()
    report = generate_learning_report()

    print()
    print("🎉 Validation Complete!")

    if report["system_status"] == "fully_operational":
        print("✅ All systems operational - Learning intelligence ready for production!")
    elif report["system_status"] == "partially_operational":
        print("⚠️  System partially operational - Some features may need attention")
    else:
        print("❌ System degraded - Manual intervention required")