#!/usr/bin/env python3
"""
Local discovery publish harness - runs full production pass and publishes to Redis
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone

# Add backend/src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend', 'src'))

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def get_redis():
    try:
        from lib.redis_client import get_redis_client
        return get_redis_client()
    except Exception as e:
        print(f"Error getting Redis client: {e}")
        print("Make sure REDIS_URL is set and Redis is running")
        sys.exit(1)

async def main():
    limit = int(os.getenv("LIMIT", "15"))
    relaxed = os.getenv("RELAXED", "false").lower() in ("1","true","yes")
    
    print("=== Running Discovery Publisher ===")
    print(f"Limit: {limit}, Relaxed: {relaxed}")
    print(f"Redis URL: {os.getenv('REDIS_URL', 'redis://localhost:6379/0')}")
    print()
    
    try:
        # tolerate either file name
        from jobs.discovery import select_candidates
    except Exception:
        try:
            from jobs.discover import select_candidates
        except Exception as e:
            print(f"Error importing select_candidates: {e}")
            sys.exit(1)
    
    print("Running discovery pipeline...")
    try:
        items, trace = await select_candidates(relaxed=relaxed, limit=limit, with_trace=True)
    except Exception as e:
        print(f"Error running discovery: {e}")
        sys.exit(1)
    
    print(f"Found {len(items)} candidates")
    
    # Publish to Redis
    print("Publishing to Redis...")
    try:
        r = get_redis()
        
        # Test Redis connection
        r.ping()
        
        # Publish contenders
        r.set("amc:discovery:contenders.latest", json.dumps(items), ex=600)
        
        # Publish explain payload
        explain_payload = {
            "ts": now_iso(), 
            "count": len(items), 
            "trace": trace
        }
        r.set("amc:discovery:explain.latest", json.dumps(explain_payload), ex=600)
        
        print(f"✅ Published {len(items)} items to Redis")
        
        # Verify by reading back
        stored_count = len(json.loads(r.get("amc:discovery:contenders.latest") or "[]"))
        explain_stored = json.loads(r.get("amc:discovery:explain.latest") or "{}")
        
        print(f"✅ Verified: {stored_count} contenders, explain ts: {explain_stored.get('ts', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Redis error: {e}")
        sys.exit(1)
    
    # Print summary
    print("\n=== Summary ===")
    trace_counts = trace.get("counts_out", {})
    for stage, count in trace_counts.items():
        print(f"  {stage:20s}: {count:5d}")
    
    print(f"\nTop 5 candidates:")
    for i, item in enumerate(items[:5]):
        sym = item.get("symbol", "")
        score = item.get("score", 0)
        print(f"  {i+1}. {sym:8s} score={score:.4f}")
    
    if os.getenv("JSON", "false").lower() in ("1", "true", "yes"):
        print("\n=== JSON OUTPUT ===")
        print(json.dumps({
            "count": len(items), 
            "trace_counts_out": trace.get("counts_out", {}),
            "items": items
        }, indent=2))

if __name__ == "__main__":
    asyncio.run(main())