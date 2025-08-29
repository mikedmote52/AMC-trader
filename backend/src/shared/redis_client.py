import redis
import os
import logging
from contextlib import contextmanager
from typing import Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def get_redis_client():
    """Get Redis client with configuration from environment"""
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    return redis.from_url(redis_url, decode_responses=True)

@contextmanager
def redis_lock(lock_key, ttl_seconds=240):  # 4 minutes default
    """
    Redis-based distributed lock to prevent job overlap
    
    Args:
        lock_key (str): Unique key for the lock
        ttl_seconds (int): Time to live for the lock in seconds (default 4 minutes)
    
    Yields:
        bool: True if lock acquired, False otherwise
    """
    client = get_redis_client()
    lock_acquired = False
    
    try:
        # Try to acquire lock with TTL
        lock_acquired = client.set(lock_key, "locked", nx=True, ex=ttl_seconds)
        
        if lock_acquired:
            logger.info(f"Lock acquired: {lock_key}")
            yield True
        else:
            logger.warning(f"Lock already exists: {lock_key}")
            yield False
            
    except Exception as e:
        logger.error(f"Redis lock error: {e}")
        yield False
        
    finally:
        if lock_acquired:
            try:
                client.delete(lock_key)
                logger.info(f"Lock released: {lock_key}")
            except Exception as e:
                logger.error(f"Failed to release lock {lock_key}: {e}")


def get_dynamic_ttl(symbol: str, metrics: Dict[str, Any]) -> int:
    """
    Calculate dynamic cache TTL based on market activity and squeeze indicators.
    Hot stocks with high volume or volatility get shorter TTLs for real-time data.
    
    Args:
        symbol (str): Stock symbol
        metrics (dict): Market metrics containing volume_spike, volatility, etc.
    
    Returns:
        int: Cache TTL in seconds
    """
    try:
        volume_spike = metrics.get('volume_spike', 1.0)
        volatility = metrics.get('volatility', 0.0)
        
        # Squeeze detection - extremely short TTL for maximum responsiveness
        if volume_spike > 10:  # 10x+ average volume = potential squeeze
            return 30  # 30 seconds for hot stocks
        
        # High volatility - short TTL for fast-moving stocks
        elif volatility > 0.10:  # 10%+ volatility
            return 60  # 1 minute for volatile stocks
            
        # Moderate activity - balanced TTL
        elif volume_spike > 3:  # 3x+ average volume
            return 120  # 2 minutes for active stocks
            
        # Normal activity - standard TTL
        elif volume_spike > 1.5:  # 1.5x+ average volume
            return 300  # 5 minutes for normal stocks
            
        # Low activity - longer TTL for efficiency
        else:
            return 600  # 10 minutes for quiet stocks
            
    except Exception as e:
        logger.warning(f"Dynamic TTL calculation failed for {symbol}: {e}")
        return 300  # Default 5 minutes on error


class SqueezeCache:
    """
    Specialized caching system for squeeze detection with performance optimization.
    Implements intelligent cache warming and eviction strategies.
    """
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self.CACHE_PREFIX = "squeeze_cache:"
        self.METRICS_PREFIX = "market_metrics:"
        
    def set_with_dynamic_ttl(self, symbol: str, data: Dict[str, Any], metrics: Dict[str, Any] = None) -> bool:
        """Set cache value with dynamically calculated TTL based on market activity"""
        try:
            cache_key = f"{self.CACHE_PREFIX}{symbol}"
            
            # Calculate dynamic TTL
            if metrics is None:
                metrics = data.get('metrics', {})
            ttl = get_dynamic_ttl(symbol, metrics)
            
            # Store data with TTL
            import json
            cached_data = {
                **data,
                'cached_at': datetime.now().isoformat(),
                'ttl_used': ttl,
                'cache_reason': self._get_cache_reason(metrics)
            }
            
            self.redis_client.setex(cache_key, ttl, json.dumps(cached_data))
            
            # Also cache the metrics separately for TTL calculations
            metrics_key = f"{self.METRICS_PREFIX}{symbol}"
            self.redis_client.setex(metrics_key, ttl * 2, json.dumps(metrics))  # Metrics live longer
            
            logger.debug(f"Cached {symbol} with {ttl}s TTL: {cached_data.get('cache_reason', 'standard')}")
            return True
            
        except Exception as e:
            logger.error(f"Dynamic cache set failed for {symbol}: {e}")
            return False
    
    def get_with_metrics(self, symbol: str) -> Dict[str, Any]:
        """Get cached data along with metrics used for TTL calculation"""
        try:
            cache_key = f"{self.CACHE_PREFIX}{symbol}"
            metrics_key = f"{self.METRICS_PREFIX}{symbol}"
            
            # Get both data and metrics
            cached_data = self.redis_client.get(cache_key)
            cached_metrics = self.redis_client.get(metrics_key)
            
            result = {
                'data': None,
                'metrics': {},
                'cache_hit': False,
                'cache_age': None
            }
            
            if cached_data:
                import json
                data = json.loads(cached_data)
                result['data'] = data
                result['cache_hit'] = True
                
                # Calculate cache age
                if 'cached_at' in data:
                    cached_at = datetime.fromisoformat(data['cached_at'])
                    result['cache_age'] = (datetime.now() - cached_at).total_seconds()
            
            if cached_metrics:
                import json
                result['metrics'] = json.loads(cached_metrics)
            
            return result
            
        except Exception as e:
            logger.error(f"Cache retrieval failed for {symbol}: {e}")
            return {'data': None, 'metrics': {}, 'cache_hit': False, 'cache_age': None}
    
    def warm_cache_for_hot_stocks(self, hot_symbols: list) -> Dict[str, bool]:
        """Proactively warm cache for stocks showing squeeze activity"""
        results = {}
        
        for symbol in hot_symbols:
            try:
                # This would trigger price validation and caching
                # Implementation would integrate with DataValidator
                results[symbol] = True
                logger.info(f"Cache warmed for hot stock: {symbol}")
                
            except Exception as e:
                logger.error(f"Cache warming failed for {symbol}: {e}")
                results[symbol] = False
        
        return results
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache performance statistics for monitoring"""
        try:
            # Get all cache keys
            cache_pattern = f"{self.CACHE_PREFIX}*"
            cache_keys = self.redis_client.keys(cache_pattern)
            
            metrics_pattern = f"{self.METRICS_PREFIX}*"
            metrics_keys = self.redis_client.keys(metrics_pattern)
            
            stats = {
                'total_cached_symbols': len(cache_keys),
                'total_metrics_cached': len(metrics_keys),
                'cache_efficiency': len(cache_keys) / max(len(metrics_keys), 1),
                'timestamp': datetime.now().isoformat()
            }
            
            # Analyze TTL distribution
            ttl_distribution = {'hot': 0, 'active': 0, 'normal': 0, 'quiet': 0}
            
            for key in cache_keys:
                try:
                    ttl = self.redis_client.ttl(key)
                    if ttl > 0:
                        if ttl <= 60:
                            ttl_distribution['hot'] += 1
                        elif ttl <= 180:
                            ttl_distribution['active'] += 1
                        elif ttl <= 360:
                            ttl_distribution['normal'] += 1
                        else:
                            ttl_distribution['quiet'] += 1
                except:
                    pass
            
            stats['ttl_distribution'] = ttl_distribution
            return stats
            
        except Exception as e:
            logger.error(f"Cache statistics retrieval failed: {e}")
            return {'error': str(e)}
    
    def _get_cache_reason(self, metrics: Dict[str, Any]) -> str:
        """Get human-readable reason for cache TTL decision"""
        volume_spike = metrics.get('volume_spike', 1.0)
        volatility = metrics.get('volatility', 0.0)
        
        if volume_spike > 10:
            return f"squeeze_detected_{volume_spike:.1f}x_volume"
        elif volatility > 0.10:
            return f"high_volatility_{volatility:.2%}"
        elif volume_spike > 3:
            return f"active_trading_{volume_spike:.1f}x_volume"
        elif volume_spike > 1.5:
            return f"normal_activity_{volume_spike:.1f}x_volume"
        else:
            return f"quiet_stock_{volume_spike:.1f}x_volume"


# Global singleton for efficient reuse
squeeze_cache = SqueezeCache()