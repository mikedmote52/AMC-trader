#!/usr/bin/env python3
"""
AMC-TRADER Monitoring System Startup Script
Initializes database, runs migrations, and starts background worker
"""

import sys
import os
import asyncio
import logging

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

async def initialize_monitoring_system():
    """Initialize the complete monitoring system"""
    print("🚀 AMC-TRADER Monitoring System Initialization")
    print("=" * 50)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # 1. Run database migrations
        print("\n📊 Step 1: Running database migrations...")
        from backend.src.shared.database import get_db_pool
        
        pool = await get_db_pool()
        if not pool:
            print("❌ Failed to connect to database")
            return False
        
        # Read and execute migration
        migration_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'migrations', '001_monitoring_schema.sql')
        if os.path.exists(migration_path):
            with open(migration_path, 'r') as f:
                migration_sql = f.read()
            
            async with pool.acquire() as conn:
                await conn.execute(migration_sql)
                print("✅ Database migration completed successfully")
        else:
            print("⚠️ Migration file not found, assuming schema already exists")
        
        # 2. Test monitoring services
        print("\n🔍 Step 2: Testing monitoring services...")
        
        # Test discovery monitor
        try:
            from backend.src.services.discovery_monitor import get_discovery_monitor
            monitor = get_discovery_monitor()
            health = await monitor.get_current_health_status()
            print(f"✅ Discovery monitor: {health.get('status', 'unknown')}")
        except Exception as e:
            print(f"❌ Discovery monitor error: {e}")
        
        # Test recommendation tracker
        try:
            from backend.src.services.recommendation_tracker import get_recommendation_tracker
            tracker = get_recommendation_tracker()
            insights = await tracker.get_learning_insights()
            print(f"✅ Recommendation tracker: {insights.get('learning_status', 'unknown')} ({insights.get('total_tracked', 0)} tracked)")
        except Exception as e:
            print(f"❌ Recommendation tracker error: {e}")
        
        # Test buy-the-dip detector
        try:
            from backend.src.services.buy_the_dip_detector import get_buy_the_dip_detector
            detector = get_buy_the_dip_detector()
            opportunities = await detector.get_recent_opportunities()
            print(f"✅ Buy-the-dip detector: Ready ({len(opportunities)} recent opportunities)")
        except Exception as e:
            print(f"❌ Buy-the-dip detector error: {e}")
        
        # 3. Start background worker (optional)
        print("\n⚙️ Step 3: Background worker setup...")
        print("Background worker can be started with: python -m backend.src.services.monitoring_worker")
        
        print("\n🎉 Monitoring system initialized successfully!")
        print("\nAvailable API endpoints:")
        print("  GET  /monitoring/dashboard - Comprehensive monitoring dashboard")
        print("  GET  /monitoring/discovery/health - Discovery pipeline health")
        print("  GET  /monitoring/recommendations/missed-opportunities - Learning insights")
        print("  GET  /monitoring/dip-analysis/opportunities - Buy-the-dip opportunities")
        print("  GET  /monitoring/alerts/system - All system alerts")
        print("  POST /monitoring/initialize - Re-initialize monitoring system")
        
        return True
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False

async def run_background_worker():
    """Start the background monitoring worker"""
    print("\n🔄 Starting background monitoring worker...")
    
    try:
        from backend.src.services.monitoring_worker import start_monitoring_worker
        await start_monitoring_worker()
    except KeyboardInterrupt:
        print("\n👋 Background worker stopped by user")
    except Exception as e:
        print(f"❌ Background worker error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "worker":
        print("Starting monitoring background worker...")
        asyncio.run(run_background_worker())
    else:
        # Run initialization
        success = asyncio.run(initialize_monitoring_system())
        
        if success:
            print("\n" + "=" * 50)
            print("🎯 Next steps:")
            print("1. Start the AMC-TRADER API server")
            print("2. Optional: Run background worker with: python scripts/start_monitoring.py worker")
            print("3. Test endpoints: curl https://amc-trader.onrender.com/monitoring/dashboard")
            print("4. Monitor alerts: curl https://amc-trader.onrender.com/monitoring/alerts/system")
            
            sys.exit(0)
        else:
            print("\n❌ Initialization failed!")
            sys.exit(1)