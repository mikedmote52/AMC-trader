"""
You are a Caching and Performance Agent responsible for optimizing the caching mechanism and monitoring the system's performance.

Your tasks include:
1. Read discovery results from `backend/src/data/discovery_results.json`
2. Implement efficient caching strategies using Redis to store and retrieve discovery data
3. Monitor cache hit/miss ratios, response times, and memory usage
4. Identify performance bottlenecks and optimize the caching layer for high throughput and low latency

Ensure seamless integration with the existing Redis caching infrastructure in `backend/src/services/redis_service.py`
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import redis
from redis.exceptions import RedisError
import pika
import traceback

logger = logging.getLogger(__name__)


@dataclass
class CacheMetrics:
    """Metrics for cache performance monitoring"""
    hits: int = 0
    misses: int = 0
    total_requests: int = 0
    avg_response_time_ms: float = 0.0
    cache_size_mb: float = 0.0
    hit_ratio: float = 0.0
    last_updated: datetime = None


@dataclass
class PerformanceAlert:
    """Performance alert data structure"""
    alert_type: str
    message: str
    severity: str  # INFO, WARNING, CRITICAL
    timestamp: datetime
    metric_value: float = None
    threshold: float = None


def send_message_to_orchestrator(message: Dict[str, Any]) -> bool:
    """
    Send message to the Orchestration Agent via RabbitMQ message bus
    
    Args:
        message: Dictionary containing the message data
        
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host='localhost',
                heartbeat=600,
                blocked_connection_timeout=300
            )
        )
        channel = connection.channel()
        channel.queue_declare(queue='orchestration_queue', durable=True)
        
        # Add agent identification to message
        message['agent_name'] = 'Caching Performance Agent'
        message['timestamp'] = datetime.now().isoformat()
        
        # Publish message with persistence
        channel.basic_publish(
            exchange='',
            routing_key='orchestration_queue',
            body=json.dumps(message, default=str),
            properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
        )
        
        connection.close()
        logger.info(f"Message sent to orchestrator: {message.get('status', 'unknown')}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send message to orchestrator: {e}")
        return False


class CachingPerformanceAgent:
    """
    Caching and Performance Agent for optimizing Redis caching and monitoring system performance
    """
    
    def __init__(self, redis_client=None, data_path: str = None):
        self.redis_client = redis_client or self._init_redis_client()
        self.data_path = data_path or "/Users/michaelmote/Desktop/AMC-TRADER/backend/src/data/discovery_results.json"
        self.metrics = CacheMetrics()
        self.performance_thresholds = {
            'hit_ratio_min': 0.8,  # 80% minimum hit ratio
            'response_time_max_ms': 100,  # 100ms maximum response time
            'cache_size_max_mb': 512,  # 512MB maximum cache size
            'memory_usage_max_pct': 85  # 85% maximum memory usage
        }
        self.cache_ttl = {
            'discovery_results': 300,  # 5 minutes
            'market_data': 60,  # 1 minute
            'analytics': 900,  # 15 minutes
            'user_sessions': 3600  # 1 hour
        }
        
        # Send initialization message
        init_message = {
            'status': 'agent_initialized',
            'data': {
                'redis_connected': self.redis_client is not None,
                'data_path': self.data_path,
                'performance_thresholds': self.performance_thresholds
            }
        }
        send_message_to_orchestrator(init_message)
        
    def _init_redis_client(self):
        """Initialize Redis client with connection pooling"""
        try:
            pool = redis.ConnectionPool(
                host='localhost',
                port=6379,
                db=0,
                max_connections=20,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            return redis.Redis(connection_pool=pool, decode_responses=True)
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            return None
    
    def _generate_cache_key(self, prefix: str, **params) -> str:
        """Generate consistent cache key from parameters"""
        param_str = json.dumps(params, sort_keys=True)
        hash_suffix = hashlib.md5(param_str.encode()).hexdigest()[:8]
        return f"{prefix}:{hash_suffix}"
    
    async def cache_discovery_results(self, results: Dict[str, Any], cache_key: str = None) -> bool:
        """Cache discovery results with optimized serialization"""
        if not self.redis_client:
            return False
            
        try:
            start_time = time.time()
            
            if not cache_key:
                cache_key = self._generate_cache_key("discovery", 
                                                   timestamp=results.get('timestamp', time.time()))
            
            # Optimize data before caching
            optimized_data = self._optimize_discovery_data(results)
            
            # Use JSON serialization for complex data
            serialized_data = json.dumps(optimized_data, default=str)
            
            # Set with TTL
            success = self.redis_client.setex(
                cache_key, 
                self.cache_ttl['discovery_results'], 
                serialized_data
            )
            
            # Update metrics
            response_time = (time.time() - start_time) * 1000
            self._update_cache_metrics('set', response_time)
            
            if success:
                logger.info(f"Cached discovery results: {cache_key}")
                
                # Send success message to orchestrator
                cache_message = {
                    'status': 'cache_operation_completed',
                    'data': {
                        'operation': 'cache_write',
                        'cache_key': cache_key,
                        'response_time_ms': response_time,
                        'data_size_candidates': len(results.get('candidates', [])),
                        'success': True
                    }
                }
                send_message_to_orchestrator(cache_message)
                return True
            else:
                logger.warning(f"Failed to cache discovery results: {cache_key}")
                
                # Send failure message
                failure_message = {
                    'status': 'cache_operation_failed',
                    'data': {
                        'operation': 'cache_write',
                        'cache_key': cache_key,
                        'error': 'Redis setex operation failed'
                    }
                }
                send_message_to_orchestrator(failure_message)
                return False
                
        except Exception as e:
            logger.error(f"Error caching discovery results: {e}")
            
            # Send error message
            error_message = {
                'status': 'cache_operation_error',
                'data': {
                    'operation': 'cache_write',
                    'cache_key': cache_key,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }
            }
            send_message_to_orchestrator(error_message)
            return False
    
    async def get_cached_discovery_results(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached discovery results with performance tracking"""
        if not self.redis_client:
            return None
            
        try:
            start_time = time.time()
            
            # Attempt to retrieve from cache
            cached_data = self.redis_client.get(cache_key)
            response_time = (time.time() - start_time) * 1000
            
            if cached_data:
                # Cache hit
                self._update_cache_metrics('hit', response_time)
                data = json.loads(cached_data)
                logger.debug(f"Cache hit for discovery results: {cache_key}")
                return data
            else:
                # Cache miss
                self._update_cache_metrics('miss', response_time)
                logger.debug(f"Cache miss for discovery results: {cache_key}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving cached discovery results: {e}")
            self._update_cache_metrics('miss', 0)
            return None
    
    def _optimize_discovery_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize discovery data for caching efficiency"""
        optimized = data.copy()
        
        # Remove redundant fields
        if 'raw_data' in optimized:
            del optimized['raw_data']
        
        # Compress candidate data
        if 'candidates' in optimized:
            candidates = optimized['candidates']
            for candidate in candidates:
                # Keep only essential fields
                essential_fields = [
                    'symbol', 'score', 'action_tag', 'price', 'volume',
                    'market_cap', 'float_shares', 'short_interest'
                ]
                optimized_candidate = {k: v for k, v in candidate.items() if k in essential_fields}
                candidate.clear()
                candidate.update(optimized_candidate)
        
        return optimized
    
    async def read_discovery_results(self) -> Optional[Dict[str, Any]]:
        """Read discovery results from file system"""
        try:
            data_file = Path(self.data_path)
            if not data_file.exists():
                logger.warning(f"Discovery results file not found: {self.data_path}")
                return None
                
            with open(data_file, 'r') as f:
                data = json.load(f)
            
            logger.info(f"Read discovery results from {self.data_path}")
            return data
            
        except Exception as e:
            logger.error(f"Error reading discovery results: {e}")
            return None
    
    async def cache_with_strategy(self, key: str, data: Any, strategy: str = 'default') -> bool:
        """Cache data with different strategies based on data type and access patterns"""
        if not self.redis_client:
            return False
            
        try:
            # Determine TTL and serialization strategy
            ttl = self.cache_ttl.get(strategy, self.cache_ttl['discovery_results'])
            
            if strategy == 'market_data':
                # High-frequency data with shorter TTL
                ttl = 60
                # Use hash for structured market data
                if isinstance(data, dict):
                    return self.redis_client.hmset(key, data) and self.redis_client.expire(key, ttl)
            
            elif strategy == 'analytics':
                # Computational results with longer TTL
                ttl = 900
                # Compress if large dataset
                serialized = json.dumps(data, default=str)
                if len(serialized) > 10000:  # 10KB threshold
                    import gzip
                    serialized = gzip.compress(serialized.encode())
                    key += ":compressed"
                
                return self.redis_client.setex(key, ttl, serialized)
            
            else:
                # Default strategy
                serialized = json.dumps(data, default=str)
                return self.redis_client.setex(key, ttl, serialized)
                
        except Exception as e:
            logger.error(f"Error in cache strategy {strategy}: {e}")
            return False
    
    def _update_cache_metrics(self, operation: str, response_time_ms: float):
        """Update cache performance metrics"""
        self.metrics.total_requests += 1
        
        if operation == 'hit':
            self.metrics.hits += 1
        elif operation == 'miss':
            self.metrics.misses += 1
        
        # Update running average response time
        if self.metrics.total_requests > 0:
            total_time = self.metrics.avg_response_time_ms * (self.metrics.total_requests - 1)
            self.metrics.avg_response_time_ms = (total_time + response_time_ms) / self.metrics.total_requests
        
        # Update hit ratio
        if self.metrics.total_requests > 0:
            self.metrics.hit_ratio = self.metrics.hits / self.metrics.total_requests
        
        self.metrics.last_updated = datetime.now()
    
    async def monitor_performance(self) -> Dict[str, Any]:
        """Monitor cache and system performance"""
        performance_data = {
            'cache_metrics': asdict(self.metrics),
            'redis_info': {},
            'alerts': [],
            'recommendations': []
        }
        
        if not self.redis_client:
            return performance_data
        
        try:
            # Get Redis info
            redis_info = self.redis_client.info()
            performance_data['redis_info'] = {
                'used_memory_mb': redis_info.get('used_memory', 0) / (1024 * 1024),
                'connected_clients': redis_info.get('connected_clients', 0),
                'total_commands_processed': redis_info.get('total_commands_processed', 0),
                'keyspace_hits': redis_info.get('keyspace_hits', 0),
                'keyspace_misses': redis_info.get('keyspace_misses', 0)
            }
            
            # Update cache size metric
            self.metrics.cache_size_mb = performance_data['redis_info']['used_memory_mb']
            
            # Generate alerts
            alerts = self._check_performance_thresholds(performance_data)
            performance_data['alerts'] = alerts
            
            # Generate recommendations
            recommendations = self._generate_recommendations(performance_data)
            performance_data['recommendations'] = recommendations
            
            # Send performance monitoring update
            monitoring_message = {
                'status': 'performance_monitoring_completed',
                'data': {
                    'cache_metrics': performance_data['cache_metrics'],
                    'redis_metrics': performance_data['redis_info'],
                    'alert_count': len(alerts),
                    'recommendation_count': len(recommendations),
                    'critical_alerts': len([a for a in alerts if getattr(a, 'severity', '') == 'CRITICAL'])
                }
            }
            send_message_to_orchestrator(monitoring_message)
            
        except Exception as e:
            logger.error(f"Error monitoring performance: {e}")
            
            # Send error message
            error_message = {
                'status': 'performance_monitoring_error',
                'data': {
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }
            }
            send_message_to_orchestrator(error_message)
            
        return performance_data
    
    def _check_performance_thresholds(self, performance_data: Dict) -> List[PerformanceAlert]:
        """Check performance metrics against thresholds and generate alerts"""
        alerts = []
        
        # Check hit ratio
        if self.metrics.hit_ratio < self.performance_thresholds['hit_ratio_min']:
            alerts.append(PerformanceAlert(
                alert_type='cache_hit_ratio',
                message=f"Low cache hit ratio: {self.metrics.hit_ratio:.2%}",
                severity='WARNING',
                timestamp=datetime.now(),
                metric_value=self.metrics.hit_ratio,
                threshold=self.performance_thresholds['hit_ratio_min']
            ))
        
        # Check response time
        if self.metrics.avg_response_time_ms > self.performance_thresholds['response_time_max_ms']:
            alerts.append(PerformanceAlert(
                alert_type='response_time',
                message=f"High average response time: {self.metrics.avg_response_time_ms:.2f}ms",
                severity='WARNING',
                timestamp=datetime.now(),
                metric_value=self.metrics.avg_response_time_ms,
                threshold=self.performance_thresholds['response_time_max_ms']
            ))
        
        # Check cache size
        if self.metrics.cache_size_mb > self.performance_thresholds['cache_size_max_mb']:
            alerts.append(PerformanceAlert(
                alert_type='cache_size',
                message=f"Cache size approaching limit: {self.metrics.cache_size_mb:.2f}MB",
                severity='CRITICAL',
                timestamp=datetime.now(),
                metric_value=self.metrics.cache_size_mb,
                threshold=self.performance_thresholds['cache_size_max_mb']
            ))
        
        return alerts
    
    def _generate_recommendations(self, performance_data: Dict) -> List[str]:
        """Generate optimization recommendations based on performance data"""
        recommendations = []
        
        if self.metrics.hit_ratio < 0.7:
            recommendations.append("Consider increasing cache TTL for frequently accessed data")
            recommendations.append("Review cache key generation strategy for better hit rates")
        
        if self.metrics.avg_response_time_ms > 50:
            recommendations.append("Consider using Redis pipelining for batch operations")
            recommendations.append("Review data serialization strategy for performance")
        
        if self.metrics.cache_size_mb > 400:
            recommendations.append("Implement cache eviction strategy for old data")
            recommendations.append("Consider data compression for large objects")
        
        redis_info = performance_data.get('redis_info', {})
        if redis_info.get('connected_clients', 0) > 50:
            recommendations.append("Monitor connection pool usage and consider optimization")
        
        return recommendations
    
    async def optimize_cache_performance(self):
        """Run optimization routines for cache performance"""
        if not self.redis_client:
            return
            
        try:
            # Clean expired keys
            await self._cleanup_expired_keys()
            
            # Optimize memory usage
            await self._optimize_memory_usage()
            
            # Update cache strategies based on access patterns
            await self._update_cache_strategies()
            
            logger.info("Cache performance optimization completed")
            
            # Send optimization completion message
            optimization_message = {
                'status': 'cache_optimization_completed',
                'data': {
                    'optimization_tasks': ['cleanup_expired_keys', 'optimize_memory_usage', 'update_cache_strategies'],
                    'cache_metrics': asdict(self.metrics)
                }
            }
            send_message_to_orchestrator(optimization_message)
            
        except Exception as e:
            logger.error(f"Error optimizing cache performance: {e}")
            
            # Send error message
            error_message = {
                'status': 'cache_optimization_error',
                'data': {
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }
            }
            send_message_to_orchestrator(error_message)
    
    async def _cleanup_expired_keys(self):
        """Clean up expired or stale cache keys"""
        try:
            # Get all keys with our prefixes
            patterns = ['discovery:*', 'market_data:*', 'analytics:*']
            
            for pattern in patterns:
                keys = self.redis_client.keys(pattern)
                expired_keys = []
                
                for key in keys:
                    ttl = self.redis_client.ttl(key)
                    if ttl == -2:  # Key doesn't exist
                        expired_keys.append(key)
                    elif ttl == -1:  # Key exists but has no TTL
                        # Check if it's old data that should expire
                        self.redis_client.expire(key, self.cache_ttl['discovery_results'])
                
                if expired_keys:
                    self.redis_client.delete(*expired_keys)
                    logger.info(f"Cleaned up {len(expired_keys)} expired keys for pattern {pattern}")
                    
        except Exception as e:
            logger.error(f"Error cleaning up expired keys: {e}")
    
    async def _optimize_memory_usage(self):
        """Optimize Redis memory usage"""
        try:
            # Force garbage collection if memory usage is high
            redis_info = self.redis_client.info()
            used_memory_mb = redis_info.get('used_memory', 0) / (1024 * 1024)
            
            if used_memory_mb > self.performance_thresholds['cache_size_max_mb'] * 0.8:
                # Remove oldest discovery results
                keys = self.redis_client.keys('discovery:*')
                if len(keys) > 100:  # Keep only recent 100 results
                    keys_to_remove = keys[100:]
                    self.redis_client.delete(*keys_to_remove)
                    logger.info(f"Removed {len(keys_to_remove)} old discovery result keys")
                    
        except Exception as e:
            logger.error(f"Error optimizing memory usage: {e}")
    
    async def _update_cache_strategies(self):
        """Update cache strategies based on access patterns"""
        try:
            # Analyze access patterns and adjust TTLs
            redis_info = self.redis_client.info()
            hit_rate = redis_info.get('keyspace_hits', 1) / max(
                redis_info.get('keyspace_hits', 1) + redis_info.get('keyspace_misses', 0), 1
            )
            
            if hit_rate < 0.8:
                # Increase TTLs for better hit rates
                self.cache_ttl['discovery_results'] = min(600, self.cache_ttl['discovery_results'] * 1.2)
                logger.info(f"Increased discovery results TTL to {self.cache_ttl['discovery_results']}s")
                
        except Exception as e:
            logger.error(f"Error updating cache strategies: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        return {
            'metrics': asdict(self.metrics),
            'thresholds': self.performance_thresholds,
            'ttl_settings': self.cache_ttl,
            'redis_connection': self.redis_client is not None
        }


async def main():
    """Main function for running the Caching Performance Agent"""
    agent = CachingPerformanceAgent()
    
    # Example usage
    logger.info("Starting Caching Performance Agent")
    
    # Send startup message
    startup_message = {
        'status': 'agent_startup',
        'data': {
            'agent_version': '1.0',
            'capabilities': ['caching', 'performance_monitoring', 'optimization', 'redis_integration']
        }
    }
    send_message_to_orchestrator(startup_message)
    
    # Read and cache discovery results
    discovery_data = await agent.read_discovery_results()
    if discovery_data:
        await agent.cache_discovery_results(discovery_data)
        
        # Send discovery data processing message
        discovery_message = {
            'status': 'discovery_data_processed',
            'data': {
                'candidates_count': discovery_data.get('count', 0),
                'strategy': discovery_data.get('strategy', 'unknown'),
                'processing_successful': True
            }
        }
        send_message_to_orchestrator(discovery_message)
    
    # Monitor performance
    performance_data = await agent.monitor_performance()
    logger.info(f"Performance metrics: {performance_data['cache_metrics']}")
    
    # Run optimization
    await agent.optimize_cache_performance()
    
    # Send completion message
    completion_message = {
        'status': 'agent_execution_completed',
        'data': {
            'final_metrics': performance_data['cache_metrics'],
            'execution_successful': True
        }
    }
    send_message_to_orchestrator(completion_message)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())