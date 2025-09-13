"""
Redis Service

Provides a service layer for Redis operations compatible with the API Integration Agent.
Adapts the existing Redis client to work with the agent's interface requirements.
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import redis
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

class RedisService:
    """
    Redis service that adapts existing Redis clients for API Integration Agent.
    
    Provides both synchronous and asynchronous operations with error handling,
    connection management, and performance monitoring.
    """
    
    def __init__(self, redis_client: redis.Redis = None, redis_url: str = None):
        """
        Initialize Redis service.
        
        Args:
            redis_client: Existing synchronous Redis client
            redis_url: Redis connection URL (if client not provided)
        """
        import os
        
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        
        # Synchronous client
        if redis_client:
            self.redis_sync = redis_client
        else:
            self.redis_sync = redis.from_url(self.redis_url, decode_responses=False)
        
        # Async client (created on demand)
        self._redis_async = None
        
        # Performance tracking
        self.operations_count = 0
        self.operations_success = 0
        self.operations_error = 0
        
        self.logger = logger
    
    async def get_async_client(self) -> aioredis.Redis:
        """Get or create async Redis client."""
        if self._redis_async is None:
            self._redis_async = aioredis.from_url(
                self.redis_url, 
                decode_responses=False,
                retry_on_timeout=True,
                retry_on_error=[ConnectionError, TimeoutError],
                health_check_interval=30
            )
        return self._redis_async
    
    async def close_async_client(self):
        """Close async Redis client."""
        if self._redis_async:
            await self._redis_async.close()
            self._redis_async = None
    
    # Async operations (for API Integration Agent)
    
    async def get(self, key: str) -> Optional[str]:
        """
        Async get operation.
        
        Args:
            key: Redis key
            
        Returns:
            Value as string or None if not found
        """
        try:
            self.operations_count += 1
            client = await self.get_async_client()
            
            value = await client.get(key)
            if value:
                # Decode bytes to string if needed
                result = value.decode('utf-8') if isinstance(value, bytes) else value
                self.operations_success += 1
                return result
            
            self.operations_success += 1
            return None
            
        except Exception as e:
            self.operations_error += 1
            self.logger.error(f"Redis GET error for key {key}: {str(e)}")
            raise
    
    async def set(self, key: str, value: str, ex: int = None) -> bool:
        """
        Async set operation.
        
        Args:
            key: Redis key
            value: Value to store
            ex: Expiration in seconds
            
        Returns:
            True if successful
        """
        try:
            self.operations_count += 1
            client = await self.get_async_client()
            
            if ex:
                result = await client.setex(key, ex, value)
            else:
                result = await client.set(key, value)
            
            self.operations_success += 1
            return bool(result)
            
        except Exception as e:
            self.operations_error += 1
            self.logger.error(f"Redis SET error for key {key}: {str(e)}")
            raise
    
    async def setex(self, key: str, ex: int, value: str) -> bool:
        """
        Async set with expiration.
        
        Args:
            key: Redis key
            ex: Expiration in seconds
            value: Value to store
            
        Returns:
            True if successful
        """
        return await self.set(key, value, ex)
    
    async def delete(self, *keys: str) -> int:
        """
        Async delete operation.
        
        Args:
            keys: Redis keys to delete
            
        Returns:
            Number of keys deleted
        """
        try:
            self.operations_count += 1
            client = await self.get_async_client()
            
            result = await client.delete(*keys)
            self.operations_success += 1
            return int(result)
            
        except Exception as e:
            self.operations_error += 1
            self.logger.error(f"Redis DELETE error for keys {keys}: {str(e)}")
            raise
    
    async def keys(self, pattern: str) -> List[str]:
        """
        Async keys operation.
        
        Args:
            pattern: Key pattern (e.g., "prefix:*")
            
        Returns:
            List of matching keys
        """
        try:
            self.operations_count += 1
            client = await self.get_async_client()
            
            keys_bytes = await client.keys(pattern)
            keys = [k.decode('utf-8') if isinstance(k, bytes) else k for k in keys_bytes]
            
            self.operations_success += 1
            return keys
            
        except Exception as e:
            self.operations_error += 1
            self.logger.error(f"Redis KEYS error for pattern {pattern}: {str(e)}")
            raise
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists.
        
        Args:
            key: Redis key
            
        Returns:
            True if key exists
        """
        try:
            self.operations_count += 1
            client = await self.get_async_client()
            
            result = await client.exists(key)
            self.operations_success += 1
            return bool(result)
            
        except Exception as e:
            self.operations_error += 1
            self.logger.error(f"Redis EXISTS error for key {key}: {str(e)}")
            raise
    
    async def ttl(self, key: str) -> int:
        """
        Get time-to-live for key.
        
        Args:
            key: Redis key
            
        Returns:
            TTL in seconds (-1 if no expiry, -2 if key doesn't exist)
        """
        try:
            self.operations_count += 1
            client = await self.get_async_client()
            
            result = await client.ttl(key)
            self.operations_success += 1
            return int(result)
            
        except Exception as e:
            self.operations_error += 1
            self.logger.error(f"Redis TTL error for key {key}: {str(e)}")
            raise
    
    # JSON operations (convenience methods)
    
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get and parse JSON data.
        
        Args:
            key: Redis key
            
        Returns:
            Parsed JSON data or None
        """
        try:
            value = await self.get(key)
            if value:
                return json.loads(value)
            return None
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error for key {key}: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Error getting JSON for key {key}: {str(e)}")
            raise
    
    async def set_json(self, key: str, data: Dict[str, Any], ex: int = None) -> bool:
        """
        Set JSON data.
        
        Args:
            key: Redis key
            data: Data to serialize as JSON
            ex: Expiration in seconds
            
        Returns:
            True if successful
        """
        try:
            json_str = json.dumps(data, default=str)  # Handle datetime objects
            return await self.set(key, json_str, ex)
            
        except Exception as e:
            self.logger.error(f"Error setting JSON for key {key}: {str(e)}")
            raise
    
    # Health and monitoring operations
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Redis connection.
        
        Returns:
            Health check results
        """
        try:
            client = await self.get_async_client()
            
            # Test basic connectivity
            start_time = datetime.utcnow()
            pong = await client.ping()
            ping_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            if not pong:
                return {
                    'status': 'unhealthy',
                    'error': 'Ping failed',
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            # Get Redis info
            info = await client.info()
            
            return {
                'status': 'healthy',
                'ping_time_ms': round(ping_time, 2),
                'redis_version': info.get('redis_version', 'unknown'),
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', 'unknown'),
                'operations_stats': {
                    'total': self.operations_count,
                    'success': self.operations_success,
                    'error': self.operations_error,
                    'error_rate': (self.operations_error / max(self.operations_count, 1)) * 100
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Redis health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.
        
        Returns:
            Cache statistics
        """
        try:
            client = await self.get_async_client()
            info = await client.info()
            
            # Calculate hit ratio if available
            hits = info.get('keyspace_hits', 0)
            misses = info.get('keyspace_misses', 0)
            total_commands = hits + misses
            hit_ratio = (hits / max(total_commands, 1)) * 100
            
            return {
                'keyspace_hits': hits,
                'keyspace_misses': misses,
                'hit_ratio_pct': round(hit_ratio, 2),
                'total_operations': self.operations_count,
                'successful_operations': self.operations_success,
                'failed_operations': self.operations_error,
                'success_rate_pct': round((self.operations_success / max(self.operations_count, 1)) * 100, 2),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {str(e)}")
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    # Synchronous operations (for compatibility)
    
    def get_sync(self, key: str) -> Optional[str]:
        """Synchronous get operation."""
        try:
            value = self.redis_sync.get(key)
            if value:
                return value.decode('utf-8') if isinstance(value, bytes) else value
            return None
        except Exception as e:
            self.logger.error(f"Sync Redis GET error for key {key}: {str(e)}")
            raise
    
    def set_sync(self, key: str, value: str, ex: int = None) -> bool:
        """Synchronous set operation."""
        try:
            if ex:
                return bool(self.redis_sync.setex(key, ex, value))
            else:
                return bool(self.redis_sync.set(key, value))
        except Exception as e:
            self.logger.error(f"Sync Redis SET error for key {key}: {str(e)}")
            raise
    
    def get_json_sync(self, key: str) -> Optional[Dict[str, Any]]:
        """Synchronous get JSON operation."""
        try:
            value = self.get_sync(key)
            if value:
                return json.loads(value)
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Sync JSON decode error for key {key}: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Sync error getting JSON for key {key}: {str(e)}")
            raise
    
    def set_json_sync(self, key: str, data: Dict[str, Any], ex: int = None) -> bool:
        """Synchronous set JSON operation."""
        try:
            json_str = json.dumps(data, default=str)
            return self.set_sync(key, json_str, ex)
        except Exception as e:
            self.logger.error(f"Sync error setting JSON for key {key}: {str(e)}")
            raise
    
    # Cleanup
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_async_client()
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            if self._redis_async:
                # Can't await in __del__, so just try to close
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close_async_client())
        except:
            pass  # Best effort cleanup


# Global service instances
_redis_service = None

def get_redis_service(redis_client: redis.Redis = None) -> RedisService:
    """Get singleton Redis service instance."""
    global _redis_service
    if _redis_service is None:
        _redis_service = RedisService(redis_client)
    return _redis_service