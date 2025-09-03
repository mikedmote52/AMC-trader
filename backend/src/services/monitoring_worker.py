#!/usr/bin/env python3
"""
AMC-TRADER Monitoring Background Worker
Runs performance tracking, alert generation, and dip analysis jobs
"""

import asyncio
import logging
import json
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from contextlib import asynccontextmanager
from .discovery_monitor import get_discovery_monitor
from .recommendation_tracker import get_recommendation_tracker, update_recommendation_performance
from .buy_the_dip_detector import get_buy_the_dip_detector
from ..shared.redis_client import get_redis_client
from ..shared.database import get_db_pool

logger = logging.getLogger(__name__)

class MonitoringWorker:
    """
    Background worker for comprehensive AMC-TRADER monitoring
    Runs all monitoring jobs with proper error handling and recovery
    """
    
    def __init__(self):
        self.redis = get_redis_client()
        self.running = False
        self.tasks = []
        
    async def start(self):
        """Start all monitoring background tasks"""
        if self.running:
            logger.warning("Monitoring worker already running")
            return
            
        self.running = True
        logger.info("🚀 Starting AMC-TRADER monitoring worker...")
        
        # Start all background tasks
        self.tasks = [
            asyncio.create_task(self._performance_update_job()),
            asyncio.create_task(self._dip_analysis_job()),
            asyncio.create_task(self._alert_processor_job()),
            asyncio.create_task(self._health_monitor_job()),
            asyncio.create_task(self._cleanup_job())
        ]
        
        logger.info("✅ All monitoring jobs started successfully")
        
        # Wait for all tasks to complete (they run indefinitely)
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
    async def stop(self):
        """Stop all monitoring tasks gracefully"""
        logger.info("🛑 Stopping monitoring worker...")
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to finish cancellation
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        logger.info("✅ Monitoring worker stopped")
    
    async def _performance_update_job(self):
        """Update recommendation performance tracking every 5 minutes"""
        job_name = "performance_update"
        logger.info(f"📊 Starting {job_name} job")
        
        while self.running:
            try:
                start_time = datetime.now()
                
                # Process recommendation performance updates
                tracker = get_recommendation_tracker()
                
                # Get recommendations that need updates (from Redis queue)
                updated_count = 0
                while self.running:
                    rec_id = tracker.redis.rpop("amc:tracker:queue")
                    if not rec_id:
                        break
                    
                    rec_id = rec_id.decode() if isinstance(rec_id, bytes) else rec_id
                    symbol = rec_id.split('_')[0] if '_' in rec_id else rec_id
                    date_str = rec_id.split('_')[1] if '_' in rec_id else None
                    
                    success = await tracker.update_performance(symbol, date_str)
                    if success:
                        updated_count += 1
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                # Log job completion
                if updated_count > 0:
                    logger.info(f"📊 {job_name}: Updated {updated_count} recommendations in {processing_time:.2f}s")
                
                # Store job stats
                await self._record_job_stats(job_name, processing_time, updated_count, success=True)
                
                # Wait 5 minutes before next run
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"❌ {job_name} error: {e}")
                await self._record_job_stats(job_name, 0, 0, success=False, error=str(e))
                await asyncio.sleep(60)  # Retry after 1 minute on error
    
    async def _dip_analysis_job(self):
        """Run buy-the-dip analysis every 30 minutes during market hours"""
        job_name = "dip_analysis"
        logger.info(f"💎 Starting {job_name} job")
        
        while self.running:
            try:
                start_time = datetime.now()
                
                # Check if market hours (approximate - 9:30 AM to 4:00 PM ET)
                current_hour = start_time.hour
                is_market_hours = 9 <= current_hour <= 16
                
                if is_market_hours or start_time.minute % 60 == 0:  # Run every hour outside market hours
                    detector = get_buy_the_dip_detector()
                    opportunities = await detector.analyze_portfolio_dips()
                    
                    processing_time = (datetime.now() - start_time).total_seconds()
                    
                    logger.info(f"💎 {job_name}: Found {len(opportunities)} dip opportunities in {processing_time:.2f}s")
                    
                    # Generate alerts for high-priority opportunities
                    strong_buy_count = sum(1 for opp in opportunities if opp.get('recommendation') == 'STRONG_BUY')
                    if strong_buy_count > 0:
                        await self._generate_dip_alert(strong_buy_count, opportunities)
                    
                    await self._record_job_stats(job_name, processing_time, len(opportunities), success=True)
                
                # Wait 30 minutes during market hours, 60 minutes otherwise
                sleep_time = 1800 if is_market_hours else 3600
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"❌ {job_name} error: {e}")
                await self._record_job_stats(job_name, 0, 0, success=False, error=str(e))
                await asyncio.sleep(300)  # Retry after 5 minutes on error
    
    async def _alert_processor_job(self):
        """Process and distribute system alerts every minute"""
        job_name = "alert_processor"
        logger.info(f"🚨 Starting {job_name} job")
        
        while self.running:
            try:
                start_time = datetime.now()
                alerts_processed = 0
                
                # Check for critical system issues
                monitor = get_discovery_monitor()
                health_status = await monitor.get_current_health_status()
                
                # Generate alerts for critical health issues
                if health_status.get('status') == 'critical':
                    await self._generate_system_alert('CRITICAL', 
                        f"Discovery pipeline critical: {health_status.get('message', 'Unknown issue')}")
                    alerts_processed += 1
                
                # Check for missed opportunity alerts
                missed_alerts = self.redis.llen("amc:tracker:alerts:missed")
                if missed_alerts > 0:
                    alerts_processed += missed_alerts
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                if alerts_processed > 0:
                    logger.info(f"🚨 {job_name}: Processed {alerts_processed} alerts in {processing_time:.2f}s")
                
                await self._record_job_stats(job_name, processing_time, alerts_processed, success=True)
                
                # Wait 1 minute
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ {job_name} error: {e}")
                await self._record_job_stats(job_name, 0, 0, success=False, error=str(e))
                await asyncio.sleep(60)
    
    async def _health_monitor_job(self):
        """Monitor overall system health every 5 minutes"""
        job_name = "health_monitor"
        logger.info(f"❤️ Starting {job_name} job")
        
        while self.running:
            try:
                start_time = datetime.now()
                
                # Check all monitoring components
                health_data = {
                    'timestamp': start_time.isoformat(),
                    'components': {}
                }
                
                # Check discovery monitor health
                try:
                    monitor = get_discovery_monitor()
                    discovery_health = await monitor.get_current_health_status()
                    health_data['components']['discovery_monitor'] = {
                        'status': discovery_health.get('status', 'unknown'),
                        'health_score': discovery_health.get('health_score', 0.0),
                        'last_update': discovery_health.get('last_update')
                    }
                except Exception as e:
                    health_data['components']['discovery_monitor'] = {'status': 'error', 'error': str(e)}
                
                # Check recommendation tracker health
                try:
                    tracker = get_recommendation_tracker()
                    insights = await tracker.get_learning_insights()
                    health_data['components']['recommendation_tracker'] = {
                        'status': insights.get('learning_status', 'unknown'),
                        'total_tracked': insights.get('total_tracked', 0),
                        'success_rate': insights.get('success_rate', 0)
                    }
                except Exception as e:
                    health_data['components']['recommendation_tracker'] = {'status': 'error', 'error': str(e)}
                
                # Check buy-the-dip detector health
                try:
                    detector = get_buy_the_dip_detector()
                    health_data['components']['buy_the_dip_detector'] = {'status': 'healthy'}
                except Exception as e:
                    health_data['components']['buy_the_dip_detector'] = {'status': 'error', 'error': str(e)}
                
                # Store health data
                await self._store_system_health(health_data)
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                # Count healthy components
                healthy_count = sum(1 for comp in health_data['components'].values() 
                                  if comp.get('status') in ['healthy', 'ACTIVE'])
                
                logger.info(f"❤️ {job_name}: {healthy_count}/{len(health_data['components'])} components healthy in {processing_time:.2f}s")
                
                await self._record_job_stats(job_name, processing_time, healthy_count, success=True)
                
                # Wait 5 minutes
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"❌ {job_name} error: {e}")
                await self._record_job_stats(job_name, 0, 0, success=False, error=str(e))
                await asyncio.sleep(300)
    
    async def _cleanup_job(self):
        """Clean up old data and logs every 4 hours"""
        job_name = "cleanup"
        logger.info(f"🧹 Starting {job_name} job")
        
        while self.running:
            try:
                start_time = datetime.now()
                
                # Run database cleanup function
                pool = await get_db_pool()
                if pool:
                    async with pool.acquire() as conn:
                        await conn.execute("SELECT monitoring.cleanup_old_data()")
                    
                    logger.info("🧹 Database cleanup completed")
                
                # Clean up Redis keys
                cleanup_patterns = [
                    "amc:monitor:discovery:flow:*",
                    "amc:tracker:rec:*",
                    "amc:worker:stats:*"
                ]
                
                total_cleaned = 0
                for pattern in cleanup_patterns:
                    # Clean keys older than 7 days
                    keys = self.redis.keys(pattern)
                    for key in keys:
                        # Check if key is old (this is a simplified check)
                        ttl = self.redis.ttl(key)
                        if ttl == -1:  # No expiration set
                            self.redis.expire(key, 604800)  # Set 7-day expiration
                            total_cleaned += 1
                
                processing_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"🧹 {job_name}: Cleaned {total_cleaned} Redis keys in {processing_time:.2f}s")
                
                await self._record_job_stats(job_name, processing_time, total_cleaned, success=True)
                
                # Wait 4 hours
                await asyncio.sleep(14400)
                
            except Exception as e:
                logger.error(f"❌ {job_name} error: {e}")
                await self._record_job_stats(job_name, 0, 0, success=False, error=str(e))
                await asyncio.sleep(3600)  # Retry after 1 hour on error
    
    async def _generate_dip_alert(self, strong_buy_count: int, opportunities: List[Dict]):
        """Generate alert for buy-the-dip opportunities"""
        try:
            strong_buys = [opp for opp in opportunities if opp.get('recommendation') == 'STRONG_BUY']
            
            alert_data = {
                'type': 'DIP_OPPORTUNITY',
                'timestamp': datetime.now().isoformat(),
                'priority': 'HIGH',
                'strong_buy_count': strong_buy_count,
                'total_opportunities': len(opportunities),
                'symbols': [opp.get('symbol') for opp in strong_buys[:5]],  # Top 5
                'message': f"🔥 {strong_buy_count} STRONG BUY dip opportunities detected!",
                'action_required': True
            }
            
            # Store alert
            self.redis.lpush("amc:alerts:dip_opportunities", json.dumps(alert_data))
            self.redis.ltrim("amc:alerts:dip_opportunities", 0, 49)  # Keep last 50
            self.redis.expire("amc:alerts:dip_opportunities", 604800)  # 7 days
            
            # Publish real-time notification
            self.redis.publish("amc:alerts:dip_opportunity", json.dumps(alert_data))
            
            logger.info(f"🔥 Generated dip opportunity alert: {strong_buy_count} strong buys")
            
        except Exception as e:
            logger.error(f"Failed to generate dip alert: {e}")
    
    async def _generate_system_alert(self, level: str, message: str):
        """Generate system health alert"""
        try:
            alert_data = {
                'type': 'SYSTEM_HEALTH',
                'timestamp': datetime.now().isoformat(),
                'level': level,
                'message': message,
                'action_required': level in ['CRITICAL', 'ERROR']
            }
            
            # Store alert
            self.redis.lpush("amc:alerts:system", json.dumps(alert_data))
            self.redis.ltrim("amc:alerts:system", 0, 99)  # Keep last 100
            self.redis.expire("amc:alerts:system", 604800)  # 7 days
            
            # Publish real-time notification
            self.redis.publish("amc:alerts:system_health", json.dumps(alert_data))
            
            logger.info(f"🚨 Generated system alert [{level}]: {message}")
            
        except Exception as e:
            logger.error(f"Failed to generate system alert: {e}")
    
    async def _store_system_health(self, health_data: Dict):
        """Store system health data in database"""
        try:
            pool = await get_db_pool()
            if not pool:
                return
            
            async with pool.acquire() as conn:
                # Store overall health record
                health_score = sum(1 for comp in health_data['components'].values() 
                                 if comp.get('status') in ['healthy', 'ACTIVE']) / max(len(health_data['components']), 1)
                
                await conn.execute("""
                    INSERT INTO monitoring.system_health 
                    (check_timestamp, component, status, health_score, metrics)
                    VALUES ($1, $2, $3, $4, $5)
                """, 
                    datetime.fromisoformat(health_data['timestamp']),
                    'MONITORING_SYSTEM',
                    'HEALTHY' if health_score > 0.5 else 'WARNING' if health_score > 0.3 else 'CRITICAL',
                    health_score,
                    json.dumps(health_data['components'])
                )
        except Exception as e:
            logger.error(f"Failed to store system health: {e}")
    
    async def _record_job_stats(self, job_name: str, processing_time: float, items_processed: int, 
                              success: bool, error: str = None):
        """Record job execution statistics"""
        try:
            stats = {
                'job_name': job_name,
                'timestamp': datetime.now().isoformat(),
                'processing_time_seconds': processing_time,
                'items_processed': items_processed,
                'success': success,
                'error': error
            }
            
            # Store in Redis for monitoring
            key = f"amc:worker:stats:{job_name}"
            self.redis.lpush(key, json.dumps(stats))
            self.redis.ltrim(key, 0, 49)  # Keep last 50 runs
            self.redis.expire(key, 86400)  # 1 day expiration
            
        except Exception as e:
            logger.error(f"Failed to record job stats for {job_name}: {e}")

# Global worker instance
_monitoring_worker = None

def get_monitoring_worker() -> MonitoringWorker:
    """Get singleton monitoring worker instance"""
    global _monitoring_worker
    if _monitoring_worker is None:
        _monitoring_worker = MonitoringWorker()
    return _monitoring_worker

async def start_monitoring_worker():
    """Start the monitoring worker"""
    worker = get_monitoring_worker()
    await worker.start()

async def stop_monitoring_worker():
    """Stop the monitoring worker"""
    worker = get_monitoring_worker()
    await worker.stop()

# CLI entry point for running as standalone service
async def main():
    """Main entry point for running monitoring worker as standalone service"""
    
    # Setup signal handlers for graceful shutdown
    worker = get_monitoring_worker()
    
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down gracefully...")
        asyncio.create_task(worker.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("🚀 AMC-TRADER Monitoring Worker starting...")
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Worker error: {e}")
    finally:
        await worker.stop()
        logger.info("👋 AMC-TRADER Monitoring Worker stopped")

if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the worker
    asyncio.run(main())