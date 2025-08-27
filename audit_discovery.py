#!/usr/bin/env python3
"""
Discovery Output Audit Script
Checks Redis for top 6 contenders and validates no ETFs/funds leaked through
"""

import json
import redis
import sys

def audit_discovery():
    try:
        # Connect to Redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        # Get contenders from Redis
        contenders_data = r.get('amc:discovery:contenders.latest')
        if not contenders_data:
            print("❌ No contenders found in Redis")
            return False
        
        contenders = json.loads(contenders_data)
        print(f"✅ Found {len(contenders)} contenders in Redis")
        
        # Check trace data for ETF elimination stage
        trace_data = r.get('amc:discovery:explain.latest')
        if trace_data:
            trace = json.loads(trace_data)
            rejections = trace.get('rejections', {})
            if 'etf_elimination' in rejections:
                print(f"📊 ETF elimination stage rejected: {sum(rejections['etf_elimination'].values())} candidates")
        
        print()
        
        # Show top 6 symbols with class and score
        print("Top 6 Discovery Contenders:")
        print("=" * 50)
        print(f"{'Rank':<4} {'Symbol':<8} {'Class':<10} {'Score':<8} {'Status'}")
        print("-" * 50)
        
        etf_leaks = []
        for i, candidate in enumerate(contenders[:6], 1):
            symbol = candidate.get('symbol', '?')
            cls = candidate.get('class', 'unknown')
            score = candidate.get('score', 0)
            
            # Check for ETF/fund leakage
            is_leak = (
                cls.upper() in {'ETF', 'FUND', 'INDEX', 'BOND', 'ETN', 'ADR', 'TRUST'} or
                symbol.upper() in {'DFAS', 'BSV', 'JETS', 'SCHO', 'KSA', 'IYH', 'VXX', 'VNQ'}
            )
            
            if is_leak:
                etf_leaks.append(f"{symbol} ({cls})")
                status = "🚨 LEAK!"
            else:
                status = "✅ Clean"
            
            print(f"{i:<4} {symbol:<8} {cls:<10} {score:<8.1f} {status}")
        
        print()
        
        if etf_leaks:
            print(f"❌ ETF/Fund leakage detected: {', '.join(etf_leaks)}")
            print("🔧 Redeploy discovery with updated filters")
            return False
        else:
            print("✅ No ETF/fund leakage detected - all candidates are equities")
            return True
            
    except Exception as e:
        print(f"❌ Audit failed: {e}")
        return False

if __name__ == "__main__":
    success = audit_discovery()
    sys.exit(0 if success else 1)