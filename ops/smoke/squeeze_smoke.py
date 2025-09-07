#!/usr/bin/env python3
"""
Comprehensive Smoke Tests for AMC-TRADER Polygon Pro Mode
Tests discovery pipeline, WebSocket freshness, and fail-closed behavior
"""
import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Optional

API = "https://amc-trader.onrender.com"

class SmokeTestRunner:
    def __init__(self, api_base: str = API):
        self.api = api_base
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'AMC-TRADER-SmokeTest/1.0'})
        self.results = []
        self.passed = 0
        self.failed = 0
    
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def test(self, name: str, condition: bool, details: str = ""):
        result = "PASS" if condition else "FAIL"
        status = "✅" if condition else "❌"
        
        if condition:
            self.passed += 1
        else:
            self.failed += 1
        
        self.log(f"{status} {name}: {result}{f' - {details}' if details else ''}")
        self.results.append({"test": name, "result": result, "details": details})
        
        return condition
    
    def get_json(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request and return JSON response"""
        try:
            url = f"{self.api}{endpoint}"
            response = self.session.get(url, params=params or {}, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.log(f"API error {response.status_code}: {endpoint}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"Request error: {e}", "ERROR")
            return None
    
    def post_json(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API POST request and return JSON response"""
        try:
            url = f"{self.api}{endpoint}"
            response = self.session.post(url, params=params or {}, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.log(f"API POST error {response.status_code}: {endpoint}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"POST request error: {e}", "ERROR")
            return None
    
    def run_all_tests(self):
        """Run comprehensive smoke test suite"""
        self.log("🚀 Starting AMC-TRADER Polygon Pro Mode Smoke Tests")
        
        # Determine if we're in market hours for context
        market_hours = self._check_market_hours()
        self.log(f"📈 Market status: {'OPEN' if market_hours else 'CLOSED'}")
        
        # Test 1: Strategy Resolution
        self._test_strategy_effective()
        
        # Test 2: Health Endpoints
        self._test_health_endpoints()
        
        # Test 3: WebSocket Freshness (if market hours)
        if market_hours:
            self._test_websocket_freshness()
        else:
            self.log("⏰ Skipping WebSocket freshness tests (market closed)")
        
        # Test 4: Discovery Pipeline
        self._test_discovery_pipeline()
        
        # Test 5: Redis Key Alignment
        self._test_redis_alignment()
        
        # Test 6: Contenders Endpoint Parity
        self._test_contenders_parity()
        
        # Test 7: Headers and State
        self._test_headers_and_state()
        
        # Test 8: Fail-Closed Behavior (if degraded)
        self._test_fail_closed_behavior()
        
        self._print_summary()
        
        return self.failed == 0
    
    def _check_market_hours(self) -> bool:
        """Check if market is currently open"""
        data = self.get_json("/discovery/health")
        if data:
            market_session = data.get('market_session', 'closed')
            return market_session in ['regular', 'premarket', 'afterhours']
        return False
    
    def _test_strategy_effective(self):
        """Test strategy resolution works correctly"""
        self.log("🎯 Testing strategy resolution...")
        
        data = self.get_json("/discovery/strategy/effective", {"strategy": "legacy_v0"})
        if data:
            self.test(
                "strategy_resolution",
                data.get('effective_strategy') == 'legacy_v0',
                f"Got {data.get('effective_strategy')} expected legacy_v0"
            )
        else:
            self.test("strategy_resolution", False, "API request failed")
    
    def _test_health_endpoints(self):
        """Test health endpoints return required information"""
        self.log("🏥 Testing health endpoints...")
        
        # Discovery health
        data = self.get_json("/discovery/health")
        if data:
            required_fields = ['universe', 'market_data', 'system_state', 'redis_info', 'market_session']
            missing_fields = [f for f in required_fields if f not in data]
            
            self.test(
                "health_endpoint_fields",
                len(missing_fields) == 0,
                f"Missing: {missing_fields}" if missing_fields else "All required fields present"
            )
            
            # Check provider stats
            providers = data.get('providers', {})
            self.test(
                "health_provider_stats",
                'polygon_ws' in providers and 'polygon_options' in providers,
                "Provider stats included"
            )
        else:
            self.test("health_endpoint_fields", False, "Health endpoint failed")
    
    def _test_websocket_freshness(self):
        """Test WebSocket data freshness during market hours"""
        self.log("📡 Testing WebSocket freshness...")
        
        data = self.get_json("/discovery/freshness/sample", {"symbols": "SPY,QQQ,AAPL"})
        if data:
            stats = data.get('freshness_stats', {})
            fresh_feeds = stats.get('fresh_feeds', 0)
            total_feeds = stats.get('total_feeds', 1)
            stale_pct = stats.get('stale_percentage', 100)
            
            self.test(
                "websocket_freshness",
                stale_pct <= 40,
                f"{stale_pct:.1f}% stale (threshold: 40%)"
            )
            
            self.test(
                "websocket_data_available",
                fresh_feeds > 0,
                f"{fresh_feeds}/{total_feeds} feeds fresh"
            )
        else:
            self.test("websocket_freshness", False, "Freshness check failed")
    
    def _test_discovery_pipeline(self):
        """Test discovery pipeline execution"""
        self.log("🔍 Testing discovery pipeline...")
        
        # Trigger discovery
        data = self.post_json("/discovery/trigger", {"strategy": "legacy_v0", "limit": 200})
        if data:
            candidates_found = data.get('candidates_found', 0)
            success = data.get('success', False)
            
            self.test(
                "discovery_execution",
                success,
                f"Found {candidates_found} candidates"
            )
            
            # During market hours, expect some candidates
            market_hours = self._check_market_hours()
            if market_hours:
                self.test(
                    "discovery_candidates_found",
                    candidates_found > 0,
                    f"Expected >0 candidates during market hours, got {candidates_found}"
                )
        else:
            self.test("discovery_execution", False, "Discovery trigger failed")
    
    def _test_redis_alignment(self):
        """Test Redis key alignment between writers and readers"""
        self.log("🔑 Testing Redis key alignment...")
        
        # Get raw data
        raw_data = self.get_json("/discovery/contenders/raw", {"strategy": "legacy_v0"})
        if raw_data is not None:
            raw_count = raw_data.get('count', len(raw_data.get('raw_candidates', [])))
            
            # Get debug data
            debug_data = self.get_json("/discovery/contenders/debug", {"strategy": "legacy_v0"})
            if debug_data:
                diagnostics = debug_data.get('data_diagnostics', {})
                redis_count = diagnostics.get('items_found', 0)
                
                self.test(
                    "redis_key_alignment",
                    raw_count == redis_count,
                    f"Raw: {raw_count}, Debug: {redis_count}"
                )
            else:
                self.test("redis_key_alignment", False, "Debug endpoint failed")
        else:
            self.test("redis_key_alignment", False, "Raw endpoint failed")
    
    def _test_contenders_parity(self):
        """Test parity between raw and served contenders"""
        self.log("📊 Testing contenders parity...")
        
        # Get raw data
        raw_data = self.get_json("/discovery/contenders/raw", {"strategy": "legacy_v0"})
        served_data = self.get_json("/discovery/contenders", {"strategy": "legacy_v0"})
        
        if raw_data is not None and served_data is not None:
            raw_count = raw_data.get('count', len(raw_data.get('raw_candidates', [])))
            served_count = len(served_data) if isinstance(served_data, list) else 0
            
            self.test(
                "contenders_parity",
                raw_count == served_count,
                f"Raw: {raw_count}, Served: {served_count}"
            )
        else:
            self.test("contenders_parity", False, "Contenders endpoints failed")
    
    def _test_headers_and_state(self):
        """Test required headers and system state"""
        self.log("🏷️  Testing headers and system state...")
        
        try:
            url = f"{self.api}/discovery/contenders"
            response = self.session.get(url, params={"strategy": "legacy_v0"}, timeout=10)
            
            headers = response.headers
            required_headers = ['X-System-State', 'X-Reason-Stats', 'Cache-Control']
            missing_headers = [h for h in required_headers if h not in headers]
            
            self.test(
                "required_headers_present",
                len(missing_headers) == 0,
                f"Missing: {missing_headers}" if missing_headers else "All headers present"
            )
            
            # Check Cache-Control
            cache_control = headers.get('Cache-Control', '')
            self.test(
                "cache_control_header",
                'no-store' in cache_control,
                f"Cache-Control: {cache_control}"
            )
            
        except Exception as e:
            self.test("required_headers_present", False, f"Header check failed: {e}")
    
    def _test_fail_closed_behavior(self):
        """Test fail-closed behavior during degraded state"""
        self.log("🚫 Testing fail-closed behavior...")
        
        # Check current system state
        health_data = self.get_json("/discovery/health")
        if health_data:
            system_state = health_data.get('system_state', 'UNKNOWN')
            
            if system_state == 'DEGRADED':
                # In degraded state, contenders should return empty
                contenders = self.get_json("/discovery/contenders", {"strategy": "legacy_v0"})
                is_empty = isinstance(contenders, list) and len(contenders) == 0
                
                self.test(
                    "fail_closed_behavior",
                    is_empty,
                    f"System DEGRADED, contenders returned {'empty' if is_empty else 'data'}"
                )
            else:
                self.test(
                    "fail_closed_behavior",
                    True,
                    f"System {system_state} - fail-closed not applicable"
                )
    
    def _print_summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        success_rate = (self.passed / total * 100) if total > 0 else 0
        
        self.log("=" * 50)
        self.log(f"📋 SMOKE TEST SUMMARY")
        self.log(f"Total tests: {total}")
        self.log(f"✅ Passed: {self.passed}")
        self.log(f"❌ Failed: {self.failed}")
        self.log(f"Success rate: {success_rate:.1f}%")
        self.log("=" * 50)
        
        if self.failed > 0:
            self.log("❌ SMOKE TESTS FAILED", "ERROR")
            self.log("Failed tests:", "ERROR")
            for result in self.results:
                if result['result'] == 'FAIL':
                    self.log(f"  - {result['test']}: {result['details']}", "ERROR")
        else:
            self.log("✅ ALL SMOKE TESTS PASSED", "SUCCESS")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AMC-TRADER Smoke Tests')
    parser.add_argument('--api', default=API, help='API base URL')
    args = parser.parse_args()
    
    runner = SmokeTestRunner(args.api)
    success = runner.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()