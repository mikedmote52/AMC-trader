#!/usr/bin/env python3
"""
Learning Cycle Runner Script
Daily execution of the learning optimization system

Usage:
    python run_learning_cycle.py [--dry-run] [--verbose]
    
Example cron job (daily at 6 PM EST after market close):
    0 18 * * 1-5 cd /path/to/AMC-TRADER/backend && python src/jobs/run_learning_cycle.py
"""

import argparse
import asyncio
import json
import sys
import os
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from jobs.learning_optimizer import run_learning_optimization
from services.learning_engine import get_learning_engine

async def initialize_learning_system():
    """Initialize the learning system if not already done"""
    print("Initializing learning system...")
    try:
        learning_engine = await get_learning_engine()
        success = await learning_engine.initialize_learning_database()
        
        if success:
            print("✅ Learning system initialized successfully")
            return True
        else:
            print("❌ Learning system initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ Learning system initialization error: {e}")
        return False

async def run_learning_cycle(dry_run=False, verbose=False):
    """Run the complete learning cycle"""
    
    print(f"🧠 Starting learning cycle - {datetime.now().isoformat()}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE LEARNING'}")
    
    try:
        # Initialize learning system
        init_success = await initialize_learning_system()
        if not init_success:
            return {"success": False, "error": "Learning system initialization failed"}
        
        # Run optimization cycle
        if not dry_run:
            results = await run_learning_optimization()
        else:
            # In dry run, simulate the learning cycle
            results = {
                "dry_run": True,
                "learning_cycle_date": datetime.now().isoformat(),
                "simulated_optimizations": [
                    "discovery_parameter_adjustment",
                    "thesis_accuracy_improvement", 
                    "market_regime_detection"
                ],
                "message": "Dry run completed - no actual learning performed"
            }
        
        # Display results
        if verbose or dry_run:
            print("\n📊 Learning Cycle Results:")
            print(json.dumps(results, indent=2))
        
        if results.get('error'):
            print(f"❌ Learning cycle completed with errors: {results['error']}")
            return results
        else:
            print("✅ Learning cycle completed successfully")
            
            # Log key metrics
            if results.get('new_patterns_learned', 0) > 0:
                print(f"📈 New patterns learned: {results['new_patterns_learned']}")
            
            if results.get('parameter_adjustments'):
                print(f"🔧 Parameter adjustments: {len(results['parameter_adjustments'])} changes")
            
            if results.get('optimizations_applied'):
                print(f"⚡ Optimizations applied: {', '.join(results['optimizations_applied'])}")
            
        return results
        
    except Exception as e:
        error_msg = f"Learning cycle failed: {str(e)}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}

def main():
    """Main entry point with command line argument handling"""
    
    parser = argparse.ArgumentParser(
        description="Run AMC-TRADER Learning Optimization Cycle",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_learning_cycle.py --dry-run          # Test without making changes
  python run_learning_cycle.py --verbose          # Show detailed output
  python run_learning_cycle.py                    # Run normal learning cycle
        """
    )
    
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Run in dry-run mode without making actual changes'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true', 
        help='Show verbose output including detailed results'
    )
    
    parser.add_argument(
        '--init-only',
        action='store_true',
        help='Only initialize the learning system database tables'
    )
    
    args = parser.parse_args()
    
    if args.init_only:
        # Only initialize and exit
        async def init_only():
            success = await initialize_learning_system()
            return success
            
        try:
            success = asyncio.run(init_only())
            sys.exit(0 if success else 1)
        except Exception as e:
            print(f"Initialization failed: {e}")
            sys.exit(1)
    
    # Run the full learning cycle
    try:
        results = asyncio.run(run_learning_cycle(
            dry_run=args.dry_run, 
            verbose=args.verbose
        ))
        
        # Exit with appropriate code
        if results.get('success', True):  # Default to success if not specified
            print("\n🎯 Learning cycle completed successfully!")
            sys.exit(0)
        else:
            print(f"\n💥 Learning cycle failed: {results.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Learning cycle interrupted by user")
        sys.exit(130)  # Standard exit code for Ctrl+C
        
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()