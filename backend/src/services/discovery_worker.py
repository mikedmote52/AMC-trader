"""
Background Discovery Worker
Runs continuous discovery cycles and caches results for instant UI responses
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List

from .bms_engine_real import RealBMSEngine

try:
    import redis.asyncio as redis
except ImportError:
    import redis
    # Fallback for older redis-py versions
    redis.Redis = redis.Redis

logger = logging.getLogger(__name__)

class DiscoveryWorker:
    """Background worker for continuous discovery with caching"""
    
    def __init__(self, engine: RealBMSEngine, redis_url: str = None):
        self.engine = engine
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.cycle_seconds = int(os.getenv('BMS_CYCLE_SECONDS', '60'))
        self.running = False
        
        # Redis client
        try:
            self.redis = redis.from_url(self.redis_url)
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None
    
    async def run_discovery_cycle(self) -> Dict:
        """Run one complete discovery cycle"""
        try:
            cycle_start = time.perf_counter()
            logger.info("🔄 Starting discovery cycle...")
            
            # Run discovery with early stop enabled
            candidates = await self.engine.discover_real_candidates(limit=100, enable_early_stop=True)
            
            # Re-validate existing cached candidates
            candidates = await self._revalidate_candidates(candidates)
            
            # Calculate cycle metadata
            cycle_duration = time.perf_counter() - cycle_start
            cycle_meta = {
                'updated_at': datetime.utcnow().isoformat() + 'Z',
                'duration_ms': int(cycle_duration * 1000),
                'candidates_found': len(candidates),
                'trade_ready': len([c for c in candidates if c.get('action') == 'TRADE_READY']),
                'monitor': len([c for c in candidates if c.get('action') == 'MONITOR']),
                'universe_counts': self.engine.last_universe_counts.copy(),
                'stage_timings': {
                    'prefilter_ms': self.engine.stage_timings.prefilter_ms,
                    'intraday_ms': self.engine.stage_timings.intraday_ms,
                    'scoring_ms': self.engine.stage_timings.scoring_ms,
                    'total_ms': self.engine.stage_timings.total_ms
                }
            }
            
            # Cache results if Redis is available
            if self.redis and candidates:
                await self._cache_results(candidates, cycle_meta)
            
            logger.info(f"✅ Discovery cycle complete: {len(candidates)} candidates in {cycle_duration:.1f}s")
            return {'success': True, 'candidates': candidates, 'meta': cycle_meta}
            
        except Exception as e:
            logger.error(f"Discovery cycle failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _cache_results(self, candidates: List[Dict], meta: Dict):
        """Cache discovery results in Redis with TTL"""
        try:
            if not self.redis:
                return
            
            # Cache all candidates
            await self.redis.setex(
                'bms:candidates:all',
                120,  # 2 minute TTL
                json.dumps(candidates)
            )
            
            # Cache trade-ready candidates separately
            trade_ready = [c for c in candidates if c.get('action') == 'TRADE_READY']
            await self.redis.setex(
                'bms:candidates:trade_ready',
                120,
                json.dumps(trade_ready)
            )
            
            # Cache monitor candidates
            monitor = [c for c in candidates if c.get('action') == 'MONITOR']
            await self.redis.setex(
                'bms:candidates:monitor',
                120,
                json.dumps(monitor)
            )
            
            # Cache metadata
            await self.redis.setex(
                'bms:meta',
                120,
                json.dumps(meta)
            )
            
            logger.debug(f"Cached {len(candidates)} candidates in Redis")
            
        except Exception as e:
            logger.error(f"Failed to cache results: {e}")
    
    async def _revalidate_candidates(self, new_candidates: List[Dict]) -> List[Dict]:
        """Re-validate and promote/demote existing candidates"""
        try:
            # Get existing cached candidates
            existing = await self.get_cached_candidates(limit=200)
            if not existing.get('cached') or not existing.get('candidates'):
                return new_candidates
            
            existing_candidates = existing['candidates']
            revalidated = []
            
            logger.debug(f"Re-validating {len(existing_candidates)} cached candidates...")
            
            for candidate in existing_candidates:
                symbol = candidate.get('symbol')
                if not symbol:
                    continue
                
                try:
                    # Get fresh market data for re-validation
                    market_data = await self.engine.get_real_market_data(symbol)
                    if not market_data:
                        continue
                    
                    # Check universe gates (price bounds, volume)
                    passes, reason = self.engine._passes_universe_gates(market_data)
                    if not passes:
                        logger.debug(f"Dropping {symbol}: {reason}")
                        continue  # Remove from candidates
                    
                    # Re-calculate BMS score
                    fresh_candidate = self.engine._calculate_real_bms_score(market_data)
                    if not fresh_candidate:
                        continue
                    
                    # Apply promotion/demotion rules
                    old_action = candidate.get('action', 'MONITOR')
                    new_action = fresh_candidate['action']
                    
                    # Promotion: Monitor -> Trade-ready if momentum improves
                    if (old_action == 'MONITOR' and new_action == 'TRADE_READY' and
                        market_data.get('momentum_1d', 0) > 0 and
                        market_data.get('rel_volume_30d', 0) >= 3.0):
                        logger.info(f"🚀 Promoted {symbol}: MONITOR → TRADE_READY")
                    
                    # Demotion: Trade-ready -> Monitor if conditions degrade
                    elif (old_action == 'TRADE_READY' and 
                          (market_data.get('rel_volume_30d', 0) < 2.0 or
                           market_data.get('atr_pct', 0) < 2.0)):
                        logger.info(f"👁️ Demoted {symbol}: TRADE_READY → MONITOR")
                    
                    revalidated.append(fresh_candidate)
                    
                except Exception as e:
                    logger.debug(f"Error revalidating {symbol}: {e}")
                    continue
            
            # Combine new discoveries with revalidated existing
            combined = new_candidates + revalidated
            
            # Remove duplicates (prefer new candidates)
            seen = set()
            final_candidates = []
            for candidate in combined:
                symbol = candidate.get('symbol')
                if symbol and symbol not in seen:
                    final_candidates.append(candidate)
                    seen.add(symbol)
            
            # Sort by score
            final_candidates.sort(key=lambda x: x.get('bms_score', 0), reverse=True)
            
            logger.debug(f"Re-validation complete: {len(revalidated)} existing + {len(new_candidates)} new = {len(final_candidates)} total")
            
            return final_candidates[:100]  # Limit total
            
        except Exception as e:
            logger.error(f"Error in candidate revalidation: {e}")
            return new_candidates
    
    async def get_cached_candidates(self, action_filter: str = None, limit: int = 50) -> Dict:
        """Get candidates from cache with optional filtering"""
        try:
            if not self.redis:
                return {'candidates': [], 'cached': False}
            
            # Determine cache key based on filter
            if action_filter == 'TRADE_READY':
                cache_key = 'bms:candidates:trade_ready'
            elif action_filter == 'MONITOR':
                cache_key = 'bms:candidates:monitor'
            else:
                cache_key = 'bms:candidates:all'
            
            # Get cached candidates
            cached_data = await self.redis.get(cache_key)
            if not cached_data:
                return {'candidates': [], 'cached': False}
            
            candidates = json.loads(cached_data)
            
            # Apply additional filtering if needed
            if action_filter and cache_key == 'bms:candidates:all':
                candidates = [c for c in candidates if c.get('action') == action_filter]
            
            # Apply limit
            candidates = candidates[:limit]
            
            # Get metadata
            meta_data = await self.redis.get('bms:meta')
            meta = json.loads(meta_data) if meta_data else {}
            
            return {
                'candidates': candidates,
                'cached': True,
                'count': len(candidates),
                **meta
            }
            
        except Exception as e:
            logger.error(f"Failed to get cached candidates: {e}")
            return {'candidates': [], 'cached': False}
    
    async def scheduler_loop(self):
        """Main scheduler loop - runs discovery cycles continuously"""
        logger.info(f"🚀 Discovery scheduler starting (cycle: {self.cycle_seconds}s)...")
        self.running = True
        
        while self.running:
            try:
                # Run discovery cycle
                cycle_result = await self.run_discovery_cycle()
                
                if not cycle_result.get('success'):
                    logger.error(f"Discovery cycle failed: {cycle_result.get('error')}")
                
                # Wait for next cycle
                logger.debug(f"Sleeping {self.cycle_seconds}s until next cycle...")
                await asyncio.sleep(self.cycle_seconds)
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                # Wait before retrying on error
                await asyncio.sleep(min(self.cycle_seconds, 30))
    
    def stop(self):
        """Stop the scheduler loop"""
        logger.info("🛑 Stopping discovery scheduler...")
        self.running = False
    
    async def health_check(self) -> Dict:
        """Check worker health and cache status"""
        try:
            health = {
                'worker_running': self.running,
                'cycle_seconds': self.cycle_seconds,
                'redis_connected': self.redis is not None
            }
            
            if self.redis:
                # Check if we have cached data
                try:
                    meta_data = await self.redis.get('bms:meta')
                    if meta_data:
                        meta = json.loads(meta_data)
                        health['last_cache_update'] = meta.get('updated_at')
                        health['cached_candidates'] = meta.get('candidates_found', 0)
                        health['cache_age_seconds'] = (
                            datetime.utcnow() - datetime.fromisoformat(meta['updated_at'].replace('Z', '+00:00'))
                        ).total_seconds() if meta.get('updated_at') else None
                    else:
                        health['cache_status'] = 'empty'
                except Exception:
                    health['cache_status'] = 'error'
            
            return health
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {'error': str(e)}

# Global worker instance
_worker_instance = None

def get_worker() -> DiscoveryWorker:
    """Get the global worker instance"""
    global _worker_instance
    return _worker_instance

def initialize_worker(engine: RealBMSEngine, redis_url: str = None) -> DiscoveryWorker:
    """Initialize the global worker instance"""
    global _worker_instance
    _worker_instance = DiscoveryWorker(engine, redis_url)
    return _worker_instance

async def start_background_worker(engine: RealBMSEngine, redis_url: str = None):
    """Start the background discovery worker"""
    worker = initialize_worker(engine, redis_url)
    
    # Start the scheduler in the background
    asyncio.create_task(worker.scheduler_loop())
    
    logger.info("✅ Background discovery worker started")
    return worker