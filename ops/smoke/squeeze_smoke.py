#!/usr/bin/env python3
"""
Squeeze Monitor Smoke Test
End-to-end validation of the squeeze discovery system
"""

import requests
import json
import sys
from datetime import datetime, timezone
import os

# Configuration
API_BASE = os.getenv("API_BASE_URL", "https://amc-trader.onrender.com")
STRATEGY = "legacy_v0"

def log(level, message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def is_market_hours():
    """Check if it's currently market hours (Mon-Fri, 13:30-20:00 UTC)"""
    now = datetime.now(timezone.utc)
    if now.weekday() >= 5:  # Weekend
        return False
    hour = now.hour + now.minute / 60.0
    return 13.5 <= hour < 20.0

def test_health_endpoint():
    """Test /discovery/health endpoint"""
    log("INFO", "Testing health endpoint...")
    
    try:
        response = requests.get(f"{API_BASE}/discovery/health", timeout=10)
        if response.status_code != 200:
            log("FAIL", f"Health endpoint returned {response.status_code}")
            return False
            
        data = response.json()
        log("PASS", f"Health: {data}")
        
        required_keys = ["universe", "market_data", "system_state"]
        for key in required_keys:
            if key not in data:
                log("FAIL", f"Health response missing key: {key}")
                return False
        
        return True
        
    except Exception as e:
        log("FAIL", f"Health endpoint error: {e}")
        return False

def test_contenders_endpoint():
    """Test /discovery/contenders endpoint with headers"""
    log("INFO", "Testing contenders endpoint...")
    
    try:
        response = requests.get(f"{API_BASE}/discovery/contenders?strategy={STRATEGY}", timeout=30)
        
        if response.status_code != 200:
            log("FAIL", f"Contenders endpoint returned {response.status_code}")
            return False
            
        # Check headers
        system_state = response.headers.get("X-System-State")
        reason_stats = response.headers.get("X-Reason-Stats")
        
        log("INFO", f"System-State: {system_state}")
        log("INFO", f"Reason-Stats: {reason_stats}")
        
        data = response.json()
        candidate_count = len(data) if isinstance(data, list) else 0
        
        log("INFO", f"Candidates found: {candidate_count}")
        
        # Validation logic based on market hours
        if is_market_hours():
            # During market hours, DEGRADED system should fail the build
            if system_state == "DEGRADED":
                log("FAIL", "System DEGRADED during market hours")
                return False
                
            # If HEALTHY during market hours but 0 candidates, check for stale data issues
            if system_state == "HEALTHY" and candidate_count == 0:
                if reason_stats:
                    stats = json.loads(reason_stats)
                    if stats.get("stale", 0) > 0:
                        log("FAIL", "HEALTHY system with 0 candidates due to stale data during market hours")
                        return False
        else:
            # Outside market hours, DEGRADED is acceptable
            if system_state == "DEGRADED":
                log("WARN", "System DEGRADED outside market hours (acceptable)")
        
        return True
        
    except Exception as e:
        log("FAIL", f"Contenders endpoint error: {e}")
        return False

def test_debug_endpoint():
    """Test /discovery/contenders/debug endpoint"""
    log("INFO", "Testing debug endpoint...")
    
    try:
        response = requests.get(f"{API_BASE}/discovery/contenders/debug?strategy={STRATEGY}", timeout=10)
        
        if response.status_code != 200:
            log("WARN", f"Debug endpoint returned {response.status_code} (may not be deployed yet)")
            return True  # Don't fail on debug endpoint
            
        data = response.json()
        log("INFO", f"Debug summary: {data.get('summary', {})}")
        log("INFO", f"Top drop reasons: {data.get('drop_reasons', [])[:3]}")
        
        return True
        
    except Exception as e:
        log("WARN", f"Debug endpoint error (may not be deployed yet): {e}")
        return True  # Don't fail on debug endpoint

def run_smoke_tests():
    """Run all smoke tests"""
    log("INFO", f"Starting smoke tests against {API_BASE}")
    log("INFO", f"Market hours check: {'YES' if is_market_hours() else 'NO'}")
    
    tests = [
        test_health_endpoint,
        test_contenders_endpoint, 
        test_debug_endpoint
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            log("PASS" if result else "FAIL", f"{test.__name__}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            log("FAIL", f"{test.__name__}: ERROR - {e}")
            results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    log("INFO", f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        log("PASS", "All smoke tests PASSED")
        return 0
    else:
        log("FAIL", "Some smoke tests FAILED")
        return 1

if __name__ == "__main__":
    exit_code = run_smoke_tests()
    sys.exit(exit_code)