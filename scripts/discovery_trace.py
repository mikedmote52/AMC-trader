#!/usr/bin/env python3
"""
Local discovery trace harness - runs selector in dry mode and prints readable summary
"""

import asyncio
import json
import os
import sys
from textwrap import shorten

# Add backend/src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend', 'src'))

async def main():
    relaxed = os.getenv("RELAXED", "false").lower() in ("1","true","yes")
    limit = int(os.getenv("LIMIT", "15"))
    
    try:
        # tolerate either file name
        from jobs.discovery import select_candidates
    except Exception:
        try:
            from jobs.discover import select_candidates  # fallback if module is named discover
        except Exception as e:
            print(f"Error importing select_candidates: {e}")
            print("Make sure you're running from the repo root and backend is available")
            sys.exit(1)
    
    print("=== Running Discovery Trace ===")
    print(f"Relaxed: {relaxed}, Limit: {limit}")
    print()
    
    try:
        items, trace = await select_candidates(relaxed=relaxed, limit=limit, with_trace=True)
    except Exception as e:
        print(f"Error running select_candidates: {e}")
        sys.exit(1)
    
    print("\n=== DISCOVERY TRACE ===")
    print("Stages:", ", ".join(trace.get("stages", [])))
    
    ci, co = trace.get("counts_in", {}), trace.get("counts_out", {})
    print("\nStage Flow:")
    for s in trace.get("stages", []):
        in_count = ci.get(s, 0)
        out_count = co.get(s, 0)
        filtered = in_count - out_count
        print(f"  {s:20s}  in={in_count:5d}  out={out_count:5d}  filtered={filtered:5d}")
    
    rej = trace.get("rejections", {})
    if rej:
        print("\nTop rejection reasons per stage:")
        for s, counts in rej.items():
            tops = sorted(counts.items(), key=lambda x: -x[1])[:5]
            tops_s = ", ".join([f"{k}:{v}" for k,v in tops])
            print(f"  {s:20s}  {tops_s}")
    
    print(f"\nTop items ({len(items)} total):")
    for i, it in enumerate(items[:min(len(items), limit)]):
        sym = it.get("symbol", "")
        score = it.get("score", 0)
        reason = it.get("reason", "")
        print(f"  {i+1:2d}. {sym:8s}  score={score:.4f}  reason={shorten(reason, 40)}")
    
    if os.getenv("JSON", "false").lower() in ("1", "true", "yes"):
        print("\n=== JSON OUTPUT ===")
        print(json.dumps({"items": items, "trace": trace}, indent=2))

if __name__ == "__main__":
    asyncio.run(main())