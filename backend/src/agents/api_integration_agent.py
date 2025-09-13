"""
API Integration Agent

Responsible for handling the integration between the backend discovery system and the frontend API.
Manages API requests/responses, data validation, and real-time data access optimization.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import redis
from fastapi import HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, validator
import time

from ..services.redis_service import RedisService
from ..services.squeeze_detector import SqueezeDetector
from .orchestration_messaging import get_orchestration_messenger, MessageType, MessagePriority


class APIIntegrationAgent:
    """
    Handles integration between backend discovery system and frontend API.
    Manages caching, validation, error handling, and performance optimization.
    """
    
    def __init__(self, redis_service: RedisService):
        self.redis = redis_service
        self.squeeze_detector = SqueezeDetector()
        self.logger = logging.getLogger(__name__)
        
        # Orchestration messaging
        self.messenger = get_orchestration_messenger()
        
        # Performance metrics
        self.request_count = 0
        self.error_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Cache TTL settings (seconds)
        self.cache_ttl = {
            'discovery_results': 300,  # 5 minutes
            'contenders': 180,  # 3 minutes
            'strategy_validation': 600,  # 10 minutes
            'audit_data': 900,  # 15 minutes
        }
    
    async def get_discovery_contenders(
        self, 
        strategy: str = "hybrid_v1", 
        limit: int = 50,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Get discovery contenders with caching and validation.
        
        Args:
            strategy: Scoring strategy to use
            limit: Maximum number of candidates to return
            force_refresh: Bypass cache and fetch fresh data
            
        Returns:
            Dictionary containing candidates, metadata, and telemetry
        """
        try:
            self.request_count += 1
            start_time = time.time()
            
            # Generate cache key
            cache_key = f"contenders:{strategy}:{limit}"
            
            # Try cache first unless forced refresh
            if not force_refresh:
                cached_data = await self._get_cached_data(cache_key)
                if cached_data:
                    self.cache_hits += 1
                    cached_data['meta']['cache_hit'] = True
                    return cached_data
            
            self.cache_misses += 1
            
            # Fetch fresh data from discovery system
            discovery_data = await self._fetch_discovery_data(strategy, limit)
            
            # Validate and enrich the data
            validated_data = await self._validate_and_enrich_data(
                discovery_data, strategy
            )
            
            # Add performance telemetry
            processing_time = time.time() - start_time
            validated_data['meta'].update({
                'processing_time_ms': round(processing_time * 1000, 2),
                'cache_hit': False,
                'timestamp': datetime.utcnow().isoformat(),
                'strategy': strategy
            })
            
            # Cache the results
            await self._cache_data(
                cache_key, 
                validated_data, 
                self.cache_ttl['contenders']
            )
            
            # Send completion notification to orchestrator
            self.messenger.send_completion_notification(
                task="discovery_contenders_fetch",
                result={
                    'candidates_count': len(validated_data.get('candidates', [])),
                    'strategy': strategy,
                    'cache_miss': True,
                    'processing_time_ms': round(processing_time * 1000, 2)
                },
                duration_ms=processing_time * 1000
            )
            
            return validated_data
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error in get_discovery_contenders: {str(e)}")
            
            # Send error alert to orchestrator
            self.messenger.send_error_alert(
                error_type="discovery_fetch_error",
                error_message=str(e),
                error_details={
                    'strategy': strategy,
                    'limit': limit,
                    'force_refresh': force_refresh
                },
                severity="high"
            )
            
            raise HTTPException(
                status_code=500, 
                detail=f"Discovery contenders fetch failed: {str(e)}"
            )
    
    async def trigger_discovery(
        self,
        strategy: str = "hybrid_v1",
        limit: int = 10,
        background_tasks: BackgroundTasks = None
    ) -> Dict[str, Any]:
        """
        Trigger discovery process and return results.
        
        Args:
            strategy: Scoring strategy to use
            limit: Maximum candidates to discover
            background_tasks: FastAPI background tasks for async processing
            
        Returns:
            Discovery results with execution metadata
        """
        try:
            start_time = time.time()
            
            # Invalidate related caches
            await self._invalidate_discovery_caches(strategy)
            
            # Run discovery process
            discovery_results = await self._run_discovery_process(strategy, limit)
            
            # Schedule background cache warming if provided
            if background_tasks:
                background_tasks.add_task(
                    self._warm_related_caches, strategy, discovery_results
                )
            
            # Add execution metadata
            execution_time = time.time() - start_time
            discovery_results['execution'] = {
                'strategy': strategy,
                'execution_time_ms': round(execution_time * 1000, 2),
                'triggered_at': datetime.utcnow().isoformat(),
                'cache_invalidated': True
            }
            
            # Send completion notification to orchestrator
            self.messenger.send_completion_notification(
                task="discovery_trigger",
                result={
                    'strategy': strategy,
                    'cache_invalidated': True,
                    'execution_time_ms': round(execution_time * 1000, 2)
                },
                duration_ms=execution_time * 1000
            )
            
            return discovery_results
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error in trigger_discovery: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Discovery trigger failed: {str(e)}"
            )
    
    async def get_strategy_validation(self, symbols: List[str] = None) -> Dict[str, Any]:
        """
        Compare strategies side-by-side for validation.
        
        Args:
            symbols: Optional list of symbols to validate (defaults to current contenders)
            
        Returns:
            Strategy comparison results
        """
        try:
            cache_key = f"strategy_validation:{hash(str(sorted(symbols or [])))}"
            
            # Check cache first
            cached_data = await self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            # Run comparison between strategies
            legacy_results = await self._fetch_discovery_data("legacy_v0", 100)
            hybrid_results = await self._fetch_discovery_data("hybrid_v1", 100)
            
            # Generate comparison analysis
            validation_data = await self._compare_strategies(
                legacy_results, hybrid_results, symbols
            )
            
            # Cache results
            await self._cache_data(
                cache_key, 
                validation_data, 
                self.cache_ttl['strategy_validation']
            )
            
            return validation_data
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error in get_strategy_validation: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Strategy validation failed: {str(e)}"
            )
    
    async def audit_symbol(
        self, 
        symbol: str, 
        strategy: str = "hybrid_v1"
    ) -> Dict[str, Any]:
        """
        Perform detailed audit of a specific symbol.
        
        Args:
            symbol: Stock symbol to audit
            strategy: Strategy to use for scoring
            
        Returns:
            Detailed audit data including subscores and rationale
        """
        try:
            cache_key = f"audit:{symbol}:{strategy}"
            
            # Check cache first
            cached_data = await self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            # Fetch detailed symbol data
            audit_data = await self._perform_symbol_audit(symbol, strategy)
            
            # Cache audit results
            await self._cache_data(
                cache_key, 
                audit_data, 
                self.cache_ttl['audit_data']
            )
            
            return audit_data
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error in audit_symbol {symbol}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Symbol audit failed for {symbol}: {str(e)}"
            )
    
    async def get_api_health(self) -> Dict[str, Any]:
        """
        Get API integration health metrics.
        
        Returns:
            Health status and performance metrics
        """
        try:
            redis_health = await self.redis.health_check()
            
            health_data = {
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'metrics': {
                    'total_requests': self.request_count,
                    'error_count': self.error_count,
                    'error_rate': (self.error_count / max(self.request_count, 1)) * 100,
                    'cache_hits': self.cache_hits,
                    'cache_misses': self.cache_misses,
                    'cache_hit_rate': (self.cache_hits / max(self.cache_hits + self.cache_misses, 1)) * 100
                },
                'redis_health': redis_health,
                'cache_ttl_config': self.cache_ttl
            }
            
            # Send health check to orchestrator
            self.messenger.send_health_check(health_data)
            
            return health_data
            
        except Exception as e:
            self.logger.error(f"Error getting API health: {str(e)}")
            
            error_health = {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Send error alert to orchestrator
            self.messenger.send_error_alert(
                error_type="health_check_error",
                error_message=str(e),
                severity="medium"
            )
            
            return error_health
    
    # Private helper methods
    
    async def _get_cached_data(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get data from Redis cache."""
        try:
            cached_json = await self.redis.get(cache_key)
            if cached_json:
                return json.loads(cached_json)
        except Exception as e:
            self.logger.warning(f"Cache read error for {cache_key}: {str(e)}")
        return None
    
    async def _cache_data(self, cache_key: str, data: Dict[str, Any], ttl: int):
        """Cache data in Redis with TTL."""
        try:
            await self.redis.setex(
                cache_key, 
                ttl, 
                json.dumps(data, default=str)
            )
            
            # Send cache update notification to orchestrator
            self.messenger.send_cache_update_notification(
                cache_operation="set",
                cache_key=cache_key,
                cache_data={
                    'ttl': ttl,
                    'data_size': len(json.dumps(data, default=str)),
                    'candidate_count': len(data.get('candidates', []))
                }
            )
            
        except Exception as e:
            self.logger.warning(f"Cache write error for {cache_key}: {str(e)}")
            
            # Send error alert for cache failures
            self.messenger.send_error_alert(
                error_type="cache_write_error",
                error_message=str(e),
                error_details={'cache_key': cache_key},
                severity="low"
            )
    
    async def _fetch_discovery_data(
        self, 
        strategy: str, 
        limit: int
    ) -> Dict[str, Any]:
        """Fetch fresh discovery data from the backend system."""
        # This would integrate with the actual discovery system
        # For now, using squeeze detector as placeholder
        
        candidates = await self.squeeze_detector.find_candidates(
            strategy=strategy,
            limit=limit
        )
        
        return {
            'candidates': candidates,
            'count': len(candidates),
            'strategy': strategy,
            'meta': {
                'generated_at': datetime.utcnow().isoformat()
            }
        }
    
    async def _validate_and_enrich_data(
        self, 
        data: Dict[str, Any], 
        strategy: str
    ) -> Dict[str, Any]:
        """Validate and enrich discovery data with additional metadata."""
        
        # Validate candidate structure
        for candidate in data.get('candidates', []):
            if not all(key in candidate for key in ['symbol', 'score']):
                raise ValueError(f"Invalid candidate structure: {candidate}")
            
            # Ensure score is within valid range
            if not (0 <= candidate['score'] <= 100):
                raise ValueError(f"Invalid score for {candidate['symbol']}: {candidate['score']}")
        
        # Add enrichment metadata
        data['meta'].update({
            'validation_passed': True,
            'enriched_at': datetime.utcnow().isoformat(),
            'strategy_config': await self._get_strategy_config(strategy)
        })
        
        return data
    
    async def _invalidate_discovery_caches(self, strategy: str):
        """Invalidate caches related to discovery for a strategy."""
        pattern = f"*{strategy}*"
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
    
    async def _run_discovery_process(
        self, 
        strategy: str, 
        limit: int
    ) -> Dict[str, Any]:
        """Run the actual discovery process."""
        # This would trigger the actual discovery pipeline
        return await self._fetch_discovery_data(strategy, limit)
    
    async def _warm_related_caches(
        self, 
        strategy: str, 
        discovery_results: Dict[str, Any]
    ):
        """Background task to warm related caches."""
        try:
            # Pre-cache common queries
            common_limits = [10, 25, 50, 100]
            for limit in common_limits:
                cache_key = f"contenders:{strategy}:{limit}"
                limited_results = {
                    **discovery_results,
                    'candidates': discovery_results['candidates'][:limit],
                    'count': min(len(discovery_results['candidates']), limit)
                }
                await self._cache_data(
                    cache_key, 
                    limited_results, 
                    self.cache_ttl['contenders']
                )
        except Exception as e:
            self.logger.warning(f"Cache warming failed: {str(e)}")
    
    async def _compare_strategies(
        self,
        legacy_results: Dict[str, Any],
        hybrid_results: Dict[str, Any],
        symbols: List[str] = None
    ) -> Dict[str, Any]:
        """Compare two strategy results."""
        
        legacy_candidates = {c['symbol']: c for c in legacy_results.get('candidates', [])}
        hybrid_candidates = {c['symbol']: c for c in hybrid_results.get('candidates', [])}
        
        all_symbols = set(legacy_candidates.keys()) | set(hybrid_candidates.keys())
        if symbols:
            all_symbols = all_symbols & set(symbols)
        
        comparison = {
            'legacy_v0': {
                'count': len(legacy_candidates),
                'avg_score': sum(c['score'] for c in legacy_candidates.values()) / max(len(legacy_candidates), 1)
            },
            'hybrid_v1': {
                'count': len(hybrid_candidates),
                'avg_score': sum(c['score'] for c in hybrid_candidates.values()) / max(len(hybrid_candidates), 1)
            },
            'overlap': len(set(legacy_candidates.keys()) & set(hybrid_candidates.keys())),
            'symbols_analyzed': len(all_symbols),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return comparison
    
    async def _perform_symbol_audit(
        self, 
        symbol: str, 
        strategy: str
    ) -> Dict[str, Any]:
        """Perform detailed audit of a symbol."""
        
        # This would integrate with the actual scoring system
        audit_result = await self.squeeze_detector.audit_symbol(symbol, strategy)
        
        return {
            'symbol': symbol,
            'strategy': strategy,
            'audit_timestamp': datetime.utcnow().isoformat(),
            **audit_result
        }
    
    async def _get_strategy_config(self, strategy: str) -> Dict[str, Any]:
        """Get configuration for a specific strategy."""
        # This would load from calibration files
        return {
            'strategy': strategy,
            'loaded_from': 'calibration/active.json'
        }


# Error handling models for API responses

class APIError(BaseModel):
    """Standard API error response model."""
    error: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Type of error")
    timestamp: str = Field(..., description="When the error occurred")
    request_id: Optional[str] = Field(None, description="Request tracking ID")


class ValidationError(APIError):
    """Validation-specific error response."""
    validation_errors: List[str] = Field(..., description="List of validation issues")


# Response models for API endpoints

class DiscoveryResponse(BaseModel):
    """Standard discovery API response."""
    candidates: List[Dict[str, Any]] = Field(..., description="Discovery candidates")
    count: int = Field(..., description="Number of candidates returned")
    strategy: str = Field(..., description="Strategy used")
    meta: Dict[str, Any] = Field(..., description="Metadata and telemetry")


class HealthResponse(BaseModel):
    """API health check response."""
    status: str = Field(..., description="Health status")
    timestamp: str = Field(..., description="Health check timestamp")
    metrics: Dict[str, Any] = Field(..., description="Performance metrics")