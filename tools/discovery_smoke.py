# tools/discovery_smoke.py
import os, json, time
import requests
from redis import Redis

API = os.getenv("API_BASE", "https://amc-trader.onrender.com")
REDIS_URL = os.getenv("REDIS_URL")

def main():
    print("🧪 Discovery Smoke Test")
    print(f"API: {API}")
    print("=" * 50)
    
    # 1) Trigger cached route so it enqueues a job if no cache
    print("\n1. Triggering /discovery/contenders...")
    try:
        r = requests.get(f"{API}/discovery/contenders?limit=10", timeout=30)
        print(f"   Status: {r.status_code}")
        print(f"   Response size: {len(r.text)} bytes")
        
        if r.status_code == 202:
            data = r.json()
            print(f"   Job queued: {data.get('job_id')}")
            print(f"   Message: {data.get('message')}")
        elif r.status_code == 200:
            data = r.json()
            print(f"   Status: {data.get('status')}")
            print(f"   Count: {data.get('count')}")
            print(f"   Cached: {data.get('cached')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 2) Check cache key exists and is non-empty
    print("\n2. Checking Redis cache...")
    if REDIS_URL:
        try:
            rc = Redis.from_url(REDIS_URL, decode_responses=True)
            
            # Check cache key
            cache_key = "amc:discovery:candidates:v2"
            raw = rc.get(cache_key)
            print(f"   Cache key: {cache_key}")
            print(f"   Exists: {bool(raw)}")
            print(f"   Size: {len(raw) if raw else 0} bytes")
            
            if raw:
                payload = json.loads(raw)
                cands = payload.get("candidates", [])
                print(f"   Candidates: {len(cands)}")
                print(f"   Universe size: {payload.get('universe_size')}")
                print(f"   Timestamp: {payload.get('iso_timestamp')}")
                
                if cands:
                    print(f"   Sample symbols: {[c.get('symbol') for c in cands[:3]]}")
            
            # Check worker heartbeat
            heartbeat_key = "amc:discovery:worker:heartbeat"
            heartbeat = rc.get(heartbeat_key)
            print(f"\n   Worker heartbeat: {heartbeat if heartbeat else 'Not found'}")
            
            # Check lock status
            lock_key = "discovery_job_lock"
            lock = rc.get(lock_key)
            print(f"   Discovery lock: {lock if lock else 'Not locked'}")
            
        except Exception as e:
            print(f"   ❌ Redis error: {e}")
    else:
        print("   ⚠️  REDIS_URL not set - skipping cache check")

    # 3) Fetch again to see ready response
    print("\n3. Second call to /discovery/contenders...")
    time.sleep(2)  # Small delay
    try:
        r2 = requests.get(f"{API}/discovery/contenders?limit=10", timeout=30)
        print(f"   Status: {r2.status_code}")
        
        if r2.status_code == 200:
            data = r2.json()
            print(f"   Response keys: {list(data.keys())}")
            print(f"   Count: {data.get('count')}")
            print(f"   Trade ready: {data.get('trade_ready_count')}")
            print(f"   Monitor: {data.get('monitor_count')}")
            
            candidates = data.get('candidates', [])
            if candidates:
                print(f"   ✅ Found {len(candidates)} candidates")
                print(f"   Sample: {[c.get('symbol') for c in candidates[:3]]}")
            else:
                print(f"   ⚠️  No candidates in response")
        else:
            print(f"   Unexpected status: {r2.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 4) Check discovery health endpoint
    print("\n4. Checking /discovery/health...")
    try:
        r3 = requests.get(f"{API}/discovery/health", timeout=10)
        if r3.status_code == 200:
            data = r3.json()
            print(f"   Status: {data.get('status')}")
            print(f"   Engine: {data.get('engine')}")
            print(f"   Redis connected: {data.get('redis_connected')}")
            
            cache_info = data.get('cache', {})
            if cache_info.get('cached_results'):
                print(f"   Cache age: {cache_info.get('cache_age_seconds')}s")
                print(f"   Cache count: {cache_info.get('cache_count')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Smoke test complete")

if __name__ == "__main__":
    main()