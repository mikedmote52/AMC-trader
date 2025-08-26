#!/usr/bin/env python3
"""
Run Once Script for Local Testing
Executes discovery pipeline once and prints JSON summary
"""

import os
import sys
import json
from datetime import datetime

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from discover import DiscoveryPipeline
from shared.redis_client import redis_lock

def main():
    """Run discovery pipeline once and print JSON summary"""
    
    print("=== Discovery Pipeline - Run Once ===")
    print(f"Started at: {datetime.now().isoformat()}")
    print()
    
    lock_key = "discovery_job_lock_test"
    
    try:
        with redis_lock(lock_key, ttl_seconds=240) as acquired:
            if not acquired:
                result = {
                    "success": False,
                    "error": "Another discovery job is running",
                    "timestamp": datetime.now().isoformat()
                }
                print("ERROR: Lock could not be acquired")
                print(json.dumps(result, indent=2))
                sys.exit(1)
            
            # Create and run pipeline
            pipeline = DiscoveryPipeline()
            result = pipeline.run()
            
            # Add timestamp to result
            result["timestamp"] = datetime.now().isoformat()
            
            # Print detailed summary
            print("=== EXECUTION SUMMARY ===")
            print(f"Success: {result['success']}")
            
            if result['success']:
                print(f"Market Status: {'OPEN' if result['market_status']['is_open'] else 'CLOSED'}")
                print(f"Recommendations Written: {result.get('recommendations_count', 0)}")
                print(f"Symbols Processed: {result.get('symbols_processed', 0)}")
                print(f"Symbols with Sentiment: {result.get('symbols_with_sentiment', 0)}")
                print(f"Duration: {result.get('duration_seconds', 0):.2f} seconds")
                
                if result.get('reason'):
                    print(f"Reason: {result['reason']}")
            else:
                print(f"Error: {result.get('error', 'Unknown error')}")
            
            print()
            print("=== JSON OUTPUT ===")
            print(json.dumps(result, indent=2))
            
            # Exit with appropriate code
            if result['success']:
                if result.get('reason') == 'insufficient live sentiment':
                    print("\nClean exit: Insufficient live sentiment during off-hours")
                    sys.exit(0)
                else:
                    print(f"\nSuccess: {result['recommendations_count']} recommendations processed")
                    sys.exit(0)
            else:
                print(f"\nFailure: {result.get('error', 'Unknown error')}")
                sys.exit(1)
                
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        result = {
            "success": False,
            "error": "Interrupted by user",
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)
        
    except Exception as e:
        print(f"\nFatal error: {e}")
        result = {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()