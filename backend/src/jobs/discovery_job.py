"""
Discovery Background Job - Runs full universe scan and caches results
Ensures non-blocking API responses by processing in background
"""
import os
import time
import json
import logging
import asyncio
import redis.asyncio as redis
from typing import Dict, List, Any
from datetime import datetime

from backend.src.constants import (
    CACHE_KEY_CONTENDERS, CACHE_KEY_STATUS, CACHE_TTL_SECONDS,
    TRADE_READY_THRESHOLD, MONITOR_THRESHOLD, DEFAULT_LIMIT, MAX_LIMIT
)
from backend.src.services.universe_loader import load_universe
from backend.src.services.bms_engine_real import RealBMSEngine

logger = logging.getLogger(__name__)

class DiscoveryJob:
    """Background job for discovery processing"""
    
    def __init__(self, job_id: str = None):
        self.job_id = job_id or f"discovery_{int(time.time())}"
        self.redis_client = None
        self.start_time = time.time()
        self.stats = {
            'universe_size': 0,
            'filtered_size': 0,
            'processed': 0,
            'trade_ready': 0,
            'monitor': 0,
            'rejected': 0
        }
    
    async def update_status(self, status: str, progress: int = 0, message: str = ""):
        """Update job status in Redis"""
        if not self.redis_client:
            return
            
        status_data = {
            'job_id': self.job_id,
            'status': status,
            'progress': progress,
            'message': message,
            'stats': self.stats,
            'elapsed_seconds': int(time.time() - self.start_time),
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            await self.redis_client.setex(
                CACHE_KEY_STATUS, 
                CACHE_TTL_SECONDS, 
                json.dumps(status_data)
            )
            logger.info(f"Status update: {status} - {message}")
        except Exception as e:
            logger.warning(f"Failed to update status: {e}")
    
    async def run_discovery(self, limit: int = DEFAULT_LIMIT) -> Dict[str, Any]:
        """Main discovery pipeline"""
        lock_key = os.getenv("DISCOVERY_LOCK_KEY", "discovery_job_lock")
        lock_token = f"{os.getpid()}:{int(time.time())}"
        
        try:
            # Connect to Redis
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            self.redis_client = redis.from_url(redis_url)
            
            # Acquire lock with TTL and token ownership
            lock_acquired = await self.redis_client.set(lock_key, lock_token, nx=True, ex=240)  # 4 minute TTL
            if not lock_acquired:
                existing_lock = await self.redis_client.get(lock_key)
                logger.warning(f"Another discovery job is running (lock held by: {existing_lock}) - exiting")
                return {
                    'status': 'skipped',
                    'reason': 'Another discovery job is already running',
                    'lock_holder': existing_lock
                }
            
            await self.update_status('starting', 0, 'Initializing discovery scan...')
            
            # Step 1: Load and filter universe
            logger.info("🌍 Loading stock universe...")
            filtered_stocks, universe_stats = await load_universe()
            
            self.stats.update({
                'universe_size': universe_stats.get('total_fetched', 0),
                'filtered_size': len(filtered_stocks)
            })
            
            await self.update_status(
                'filtering', 
                10, 
                f'Universe loaded: {len(filtered_stocks)} stocks to analyze'
            )
            
            if not filtered_stocks:
                raise ValueError("No stocks passed universe filtering")
            
            # Step 2: Initialize BMS engine
            logger.info("🔥 Initializing BMS scoring engine...")
            polygon_key = os.getenv('POLYGON_API_KEY')
            if not polygon_key:
                raise ValueError("POLYGON_API_KEY not configured")
            
            bms_engine = RealBMSEngine(polygon_key)
            await self.update_status('scoring', 20, 'Starting BMS analysis...')
            
            # Step 3: Process stocks with BMS scoring
            logger.info(f"📊 Scoring {len(filtered_stocks)} stocks...")
            
            # Extract symbols for processing
            symbols = [stock[0] for stock in filtered_stocks]
            
            # Use existing BMS engine parallel processing
            candidates = await bms_engine.discover_real_candidates(limit=MAX_LIMIT)
            
            await self.update_status('processing', 80, f'Scored {len(symbols)} stocks')
            
            # Step 4: Categorize results
            trade_ready = []
            monitor_list = []
            
            for candidate in candidates:
                score = candidate.get('bms_score', 0)
                action = candidate.get('action', 'REJECT')
                
                if action == 'TRADE_READY' or score >= TRADE_READY_THRESHOLD:
                    trade_ready.append(candidate)
                elif action == 'MONITOR' or score >= MONITOR_THRESHOLD:
                    monitor_list.append(candidate)
            
            # Update final stats
            self.stats.update({
                'processed': len(candidates),
                'trade_ready': len(trade_ready),
                'monitor': len(monitor_list),
                'rejected': len(candidates) - len(trade_ready) - len(monitor_list)
            })
            
            # Step 5: Build final payload
            all_candidates = trade_ready + monitor_list
            all_candidates.sort(key=lambda x: x.get('bms_score', 0), reverse=True)
            
            # Limit results but keep good quantity for caching
            cached_candidates = all_candidates[:max(limit, 300)]
            
            payload = {
                'timestamp': int(time.time()),
                'iso_timestamp': datetime.now().isoformat(),
                'universe_size': self.stats['universe_size'],
                'filtered_size': self.stats['filtered_size'],
                'processed': self.stats['processed'],
                'count': len(cached_candidates),
                'trade_ready_count': len(trade_ready),
                'monitor_count': len(monitor_list),
                'candidates': cached_candidates,
                'stats': self.stats,
                'job_id': self.job_id,
                'engine': 'BMS Real Engine v1.1 - Background Job',
                'elapsed_seconds': int(time.time() - self.start_time)
            }
            
            # Step 6: Cache results
            logger.info(f"💾 Caching {len(cached_candidates)} candidates...")
            await self.redis_client.setex(
                CACHE_KEY_CONTENDERS,
                CACHE_TTL_SECONDS,
                json.dumps(payload)
            )
            
            await self.update_status(
                'completed', 
                100, 
                f'Discovery complete: {len(cached_candidates)} candidates cached'
            )
            
            logger.info(f"✅ Discovery job completed in {payload['elapsed_seconds']}s")
            logger.info(f"   Universe: {payload['universe_size']} → {payload['filtered_size']} → {payload['count']}")
            logger.info(f"   Trade Ready: {payload['trade_ready_count']}")
            logger.info(f"   Monitor: {payload['monitor_count']}")
            
            return {
                'status': 'success',
                'universe_size': payload['universe_size'],
                'filtered_size': payload['filtered_size'],
                'count': payload['count'],
                'trade_ready_count': payload['trade_ready_count'],
                'elapsed_seconds': payload['elapsed_seconds']
            }
            
        except Exception as e:
            logger.error(f"Discovery job failed: {e}")
            await self.update_status('failed', 0, f'Error: {str(e)}')
            raise
            
        finally:
            # Release lock if we own it
            if self.redis_client:
                try:
                    current_lock = await self.redis_client.get(lock_key)
                    if current_lock == lock_token:
                        await self.redis_client.delete(lock_key)
                        logger.info(f"Released discovery lock: {lock_token}")
                except Exception as e:
                    logger.warning(f"Error releasing lock: {e}")
                
                await self.redis_client.close()


def run_discovery_sync(limit: int = DEFAULT_LIMIT) -> Dict[str, Any]:
    """Synchronous wrapper for RQ job execution"""
    job = DiscoveryJob()
    return asyncio.run(job.run_discovery(limit))


# RQ job function - must be at module level for RQ to import
def run_discovery_job(limit: int = DEFAULT_LIMIT) -> Dict[str, Any]:
    """RQ job entry point"""
    logger.info(f"🚀 Starting discovery job with limit={limit}")
    try:
        result = run_discovery_sync(limit)
        logger.info(f"✅ Discovery job succeeded: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Discovery job failed: {e}")
        raise