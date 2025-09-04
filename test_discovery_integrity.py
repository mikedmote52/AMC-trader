#!/usr/bin/env python3
"""
AMC-TRADER Discovery System Integrity Test Suite
Tests the critical fixes for fake data serving prevention
"""

import asyncio
import json
import requests
from datetime import datetime
from typing import List, Dict, Any

class DiscoveryIntegrityTester:
    def __init__(self, base_url: str = "https://amc-trader.onrender.com"):
        self.base_url = base_url
        self.results = []
    
    def test_no_fake_data_serving(self) -> Dict[str, Any]:
        """Test 1: Verify no fake sector_fallback data is served"""
        print("🔍 Test 1: Checking for fake sector_fallback data...")
        
        try:
            response = requests.get(f"{self.base_url}/discovery/contenders", timeout=30)
            candidates = response.json() if response.status_code == 200 else []
            
            fake_data_count = 0
            total_count = len(candidates)
            fake_items = []
            
            for item in candidates:
                if isinstance(item, dict):
                    si_data = item.get('short_interest_data', {})
                    if si_data.get('source') == 'sector_fallback':
                        fake_data_count += 1
                        fake_items.append({
                            'symbol': item.get('symbol'),
                            'fake_percent': si_data.get('percent'),
                            'fake_confidence': si_data.get('confidence')
                        })
            
            test_result = {
                'test_name': 'No Fake Data Serving',
                'status': 'PASS' if fake_data_count == 0 else 'FAIL',
                'total_candidates': total_count,
                'fake_data_count': fake_data_count,
                'fake_percentage': (fake_data_count / total_count * 100) if total_count > 0 else 0,
                'fake_items_sample': fake_items[:5],  # First 5 fake items
                'critical': True,
                'message': f"Found {fake_data_count} items with fake sector_fallback data" if fake_data_count > 0 else "No fake data detected"
            }
            
            return test_result
            
        except Exception as e:
            return {
                'test_name': 'No Fake Data Serving',
                'status': 'ERROR',
                'error': str(e),
                'critical': True
            }
    
    def test_universe_integrity(self) -> Dict[str, Any]:
        """Test 2: Verify discovery universe size vs final candidates correlation"""
        print("🔍 Test 2: Checking universe to candidates correlation...")
        
        try:
            # Get discovery explanation/trace
            response = requests.get(f"{self.base_url}/discovery/explain", timeout=30)
            trace_data = response.json() if response.status_code == 200 else {}
            
            # Get current candidates
            response = requests.get(f"{self.base_url}/discovery/contenders", timeout=30)
            candidates = response.json() if response.status_code == 200 else []
            
            # Extract universe sizes
            counts_in = trace_data.get('trace', {}).get('counts_in', trace_data.get('counts_in', {}))
            initial_universe = counts_in.get('universe', 0)
            final_candidates = len(candidates)
            
            # Critical check: If universe is tiny but candidates exist, that's suspicious
            is_suspicious = (initial_universe < 100 and final_candidates > 0)
            
            test_result = {
                'test_name': 'Universe Integrity',
                'status': 'FAIL' if is_suspicious else 'PASS',
                'initial_universe': initial_universe,
                'final_candidates': final_candidates,
                'ratio': final_candidates / initial_universe if initial_universe > 0 else float('inf'),
                'suspicious': is_suspicious,
                'critical': True,
                'message': f"Suspicious: {initial_universe} universe -> {final_candidates} candidates" if is_suspicious else "Universe to candidates correlation is normal"
            }
            
            return test_result
            
        except Exception as e:
            return {
                'test_name': 'Universe Integrity',
                'status': 'ERROR', 
                'error': str(e),
                'critical': True
            }
    
    def test_data_freshness(self) -> Dict[str, Any]:
        """Test 3: Verify data is fresh (< 5 minutes old)"""
        print("🔍 Test 3: Checking data freshness...")
        
        try:
            response = requests.get(f"{self.base_url}/discovery/status", timeout=30)
            status_data = response.json() if response.status_code == 200 else {}
            
            last_run_str = status_data.get('last_run') or status_data.get('ts')
            
            if not last_run_str:
                return {
                    'test_name': 'Data Freshness',
                    'status': 'FAIL',
                    'message': 'No timestamp found in discovery status',
                    'critical': False
                }
            
            # Parse timestamp
            try:
                last_run_time = datetime.fromisoformat(last_run_str.replace('Z', '+00:00'))
                age_seconds = (datetime.now(last_run_time.tzinfo) - last_run_time).total_seconds()
                
                is_fresh = age_seconds < 300  # 5 minutes
                
                test_result = {
                    'test_name': 'Data Freshness',
                    'status': 'PASS' if is_fresh else 'FAIL',
                    'last_run': last_run_str,
                    'age_seconds': int(age_seconds),
                    'age_minutes': round(age_seconds / 60, 1),
                    'is_fresh': is_fresh,
                    'critical': False,
                    'message': f"Data is {age_seconds:.0f} seconds old" + (" (STALE)" if not is_fresh else " (FRESH)")
                }
                
                return test_result
                
            except Exception as parse_error:
                return {
                    'test_name': 'Data Freshness',
                    'status': 'ERROR',
                    'error': f"Failed to parse timestamp: {parse_error}",
                    'critical': False
                }
            
        except Exception as e:
            return {
                'test_name': 'Data Freshness',
                'status': 'ERROR',
                'error': str(e),
                'critical': False
            }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run complete integrity test suite"""
        print("🚀 Starting AMC-TRADER Discovery Integrity Test Suite...")
        print("=" * 60)
        
        test_results = []
        
        # Run all tests
        tests = [
            self.test_no_fake_data_serving,
            self.test_universe_integrity,
            self.test_data_freshness
        ]
        
        for test_func in tests:
            result = test_func()
            test_results.append(result)
            
            # Print test result
            status_icon = "✅" if result['status'] == 'PASS' else "❌" if result['status'] == 'FAIL' else "⚠️"
            critical_flag = " [CRITICAL]" if result.get('critical', False) else ""
            print(f"{status_icon} {result['test_name']}: {result['status']}{critical_flag}")
            if 'message' in result:
                print(f"   {result['message']}")
            print()
        
        # Summary
        passed = len([r for r in test_results if r['status'] == 'PASS'])
        failed = len([r for r in test_results if r['status'] == 'FAIL'])
        errors = len([r for r in test_results if r['status'] == 'ERROR'])
        critical_failures = len([r for r in test_results if r['status'] == 'FAIL' and r.get('critical', False)])
        
        overall_status = 'PASS' if failed == 0 and errors == 0 else 'CRITICAL' if critical_failures > 0 else 'WARNING'
        
        summary = {
            'overall_status': overall_status,
            'total_tests': len(test_results),
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'critical_failures': critical_failures,
            'test_results': test_results,
            'timestamp': datetime.now().isoformat(),
            'recommendations': self._generate_recommendations(test_results)
        }
        
        print("=" * 60)
        print(f"🏁 Test Suite Complete: {overall_status}")
        print(f"   Passed: {passed}, Failed: {failed}, Errors: {errors}")
        if critical_failures > 0:
            print(f"   🚨 CRITICAL FAILURES: {critical_failures} (immediate attention required)")
        print()
        
        return summary
    
    def _generate_recommendations(self, test_results: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        for result in test_results:
            if result['status'] == 'FAIL':
                if result['test_name'] == 'No Fake Data Serving':
                    recommendations.append("URGENT: Deploy discovery API fixes to reject contaminated data")
                    recommendations.append("Clear all Redis cache keys containing fake sector_fallback data")
                elif result['test_name'] == 'Universe Integrity':
                    recommendations.append("URGENT: Fix Polygon API data fetch to get full universe")
                    recommendations.append("Deploy discovery pipeline fixes to prevent fallback data serving")
                elif result['test_name'] == 'Data Freshness':
                    recommendations.append("Trigger fresh discovery run to update stale data")
        
        if not recommendations:
            recommendations.append("All tests passing - system integrity maintained")
        
        return recommendations

def main():
    """Run integrity tests and save results"""
    tester = DiscoveryIntegrityTester()
    results = tester.run_all_tests()
    
    # Save detailed results
    with open('/Users/michaelmote/Desktop/AMC-TRADER/discovery_integrity_test_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"📄 Detailed results saved to: discovery_integrity_test_results.json")
    
    # Return exit code based on critical failures
    exit_code = 1 if results['critical_failures'] > 0 else 0
    return exit_code

if __name__ == "__main__":
    exit(main())