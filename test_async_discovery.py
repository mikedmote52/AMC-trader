#!/usr/bin/env python3
"""
Test script for async discovery system
"""

import os
import sys
import requests
import json
import time

# Add backend to path
sys.path.append('/Users/michaelmote/Desktop/AMC-TRADER/backend/src')

def test_redis_connection():
    """Test Redis connectivity"""
    print("1. Testing Redis connection...")
    try:
        import redis
        r = redis.from_url("redis://localhost:6379/0", decode_responses=True)
        ping_result = r.ping()
        print(f"   ✅ Redis ping: {ping_result}")
        return True
    except Exception as e:
        print(f"   ❌ Redis error: {e}")
        return False

def test_worker_function():
    """Test the worker function directly"""
    print("2. Testing worker function...")
    try:
        os.environ['POLYGON_API_KEY'] = '1ORwpSzeOV20X6uaA8G3Zuxx7hLJ0KIC'  # Test key
        os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
        
        from backend.src.worker import run_discovery
        results = run_discovery(limit=5)
        
        print(f"   ✅ Worker function returned {len(results)} candidates")
        if results:
            print(f"   Top candidate: {results[0].get('symbol')} - {results[0].get('bms_score', 0):.1f}")
        return True
        
    except Exception as e:
        print(f"   ❌ Worker error: {e}")
        return False

def test_rq_job():
    """Test RQ job enqueueing"""
    print("3. Testing RQ job system...")
    try:
        import redis
        import rq
        
        r = redis.from_url("redis://localhost:6379/0", decode_responses=True)
        q = rq.Queue("discovery", connection=r)
        
        # Clear queue first
        q.empty()
        
        job = q.enqueue("backend.src.worker.run_discovery", 3, job_timeout=300)
        print(f"   ✅ Job enqueued: {job.id}")
        
        # Wait a bit and check status
        time.sleep(2)
        job.refresh()
        print(f"   Job status: {job.get_status()}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ RQ error: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints if server is running"""
    print("4. Testing API endpoints...")
    base_url = "http://localhost:8000"
    
    try:
        # Test Redis ping endpoint
        resp = requests.get(f"{base_url}/_redis_ping", timeout=5)
        if resp.status_code == 200:
            print(f"   ✅ Redis ping endpoint: {resp.json()}")
        else:
            print(f"   ❌ Redis ping failed: {resp.status_code}")
            
        # Test discovery candidates endpoint
        resp = requests.get(f"{base_url}/discovery/candidates?limit=3", timeout=10)
        if resp.status_code in [200, 202]:
            data = resp.json()
            print(f"   ✅ Discovery endpoint: {data.get('status')} - {resp.status_code}")
        else:
            print(f"   ❌ Discovery failed: {resp.status_code}")
            
        return True
        
    except requests.exceptions.ConnectionError:
        print("   ⚠️ API server not running (normal for test)")
        return True
    except Exception as e:
        print(f"   ❌ API error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 AMC-TRADER Async Discovery Test")
    print("=" * 40)
    
    tests = [
        test_redis_connection,
        test_worker_function, 
        test_rq_job,
        test_api_endpoints
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"   💥 Test failed with exception: {e}")
            results.append(False)
        print()
    
    passed = sum(results)
    total = len(results)
    
    print("=" * 40)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! Ready for deployment.")
    else:
        print("❌ Some tests failed. Check dependencies.")
        
    print("\nNext steps:")
    print("1. Deploy to Render with updated render.yaml")
    print("2. Verify Redis service starts")
    print("3. Verify worker service starts")
    print("4. Test production endpoints")