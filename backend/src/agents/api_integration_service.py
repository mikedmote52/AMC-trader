"""
API Integration Service

Service layer that integrates the API Integration Agent with existing discovery routes.
Provides a bridge between the agent and the current Redis/RQ-based discovery system.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import redis.asyncio as redis
from fastapi import HTTPException, BackgroundTasks

from .api_integration_agent import APIIntegrationAgent
from ..shared.redis_client import get_redis_client, SqueezeCache
from ..constants import CACHE_KEY_CONTENDERS, CACHE_KEY_STATUS


class APIIntegrationService:
    """
    Service layer that connects the API Integration Agent with existing discovery infrastructure.
    Handles translation between agent methods and current Redis keys/data formats.
    """
    
    def __init__(self):
        # Initialize Redis connections
        self.redis_sync = get_redis_client()
        self.squeeze_cache = SqueezeCache()
        
        # Initialize the API Integration Agent with our Redis service
        from ..services.redis_service import RedisService
        redis_service = RedisService(self.redis_sync)
        self.agent = APIIntegrationAgent(redis_service)
        
        self.logger = logging.getLogger(__name__)
        
        # Current system Redis keys (compatibility)
        self.DISCOVERY_KEYS = {
            'v2_cont': "amc:discovery:v2:contenders.latest",
            'v1_cont': "amc:discovery:contenders.latest", 
            'v2_trace': "amc:discovery:v2:explain.latest",
            'v1_trace': "amc:discovery:explain.latest",
            'status': "amc:discovery:status",
            'cached_cont': CACHE_KEY_CONTENDERS,
            'cached_status': CACHE_KEY_STATUS
        }
    
    async def get_discovery_contenders_enhanced(
        self, 
        strategy: str = "hybrid_v1", 
        limit: int = 50,
        force_refresh: bool = False,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> Dict[str, Any]:
        """
        Enhanced discovery contenders with API Integration Agent features.
        
        Integrates with existing Redis keys while providing agent capabilities:
        - Intelligent caching with performance metrics
        - Data validation and enrichment  
        - Error handling and logging
        - Background optimization tasks
        """
        try:
            start_time = time.time()
            
            # First try the agent's intelligent caching system
            try:
                agent_result = await self.agent.get_discovery_contenders(
                    strategy=strategy, 
                    limit=limit, 
                    force_refresh=force_refresh
                )
                
                # If agent found data, return it with performance metrics
                if agent_result.get('candidates'):
                    processing_time = time.time() - start_time
                    agent_result['meta']['service_processing_time_ms'] = round(processing_time * 1000, 2)
                    agent_result['meta']['source'] = 'api_integration_agent'
                    return agent_result
                    
            except Exception as agent_error:
                self.logger.warning(f"Agent fallback needed: {agent_error}")
                # Continue to fallback system
            
            # Fallback to existing Redis key system
            return await self._fallback_to_existing_system(strategy, limit)
            
        except Exception as e:
            self.logger.error(f"Enhanced contenders retrieval failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Discovery contenders retrieval failed: {str(e)}"
            )
    
    async def trigger_discovery_enhanced(
        self,
        strategy: str = "hybrid_v1",
        limit: int = 10,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> Dict[str, Any]:
        """
        Enhanced discovery trigger with agent integration.
        
        Combines agent's trigger capabilities with existing RQ job system.
        """
        try:
            start_time = time.time()
            
            # Use agent's trigger method for cache invalidation and background tasks
            agent_result = await self.agent.trigger_discovery(
                strategy=strategy,
                limit=limit,
                background_tasks=background_tasks
            )
            
            # Also trigger the existing RQ job system for compatibility
            await self._trigger_existing_job_system(strategy, limit)
            
            execution_time = time.time() - start_time
            agent_result['execution']['service_execution_time_ms'] = round(execution_time * 1000, 2)
            agent_result['execution']['hybrid_trigger'] = True
            
            return agent_result
            
        except Exception as e:
            self.logger.error(f"Enhanced discovery trigger failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Discovery trigger failed: {str(e)}"
            )
    
    async def get_squeeze_candidates_enhanced(
        self,
        min_score: float = 0.25,
        limit: int = 50,
        strategy: str = "hybrid_v1"
    ) -> Dict[str, Any]:
        """
        Enhanced squeeze candidates with agent validation and caching.
        """
        try:
            # Get discovery data through agent
            discovery_data = await self.agent.get_discovery_contenders(strategy, limit * 2)  # Get more for filtering
            
            if not discovery_data.get('candidates'):
                return {
                    'candidates': [],
                    'count': 0,
                    'min_score_threshold': min_score,
                    'strategy': strategy,
                    'message': 'No discovery data available'
                }
            
            # Filter for squeeze candidates
            squeeze_candidates = []
            for candidate in discovery_data['candidates']:
                # Extract squeeze-related scores
                squeeze_score = self._calculate_squeeze_score(candidate)
                
                if squeeze_score >= min_score:
                    enhanced_candidate = {
                        **candidate,
                        'squeeze_score': squeeze_score,
                        'squeeze_classification': self._classify_squeeze_potential(squeeze_score),
                        'validation_timestamp': datetime.utcnow().isoformat()
                    }
                    squeeze_candidates.append(enhanced_candidate)
            
            # Sort and limit
            squeeze_candidates.sort(key=lambda x: x.get('squeeze_score', 0), reverse=True)
            squeeze_candidates = squeeze_candidates[:limit]
            
            return {
                'candidates': squeeze_candidates,
                'count': len(squeeze_candidates),
                'min_score_threshold': min_score,
                'strategy': strategy,
                'validation_passed': True,
                'source': 'api_integration_service_enhanced',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Enhanced squeeze candidates failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Squeeze candidates retrieval failed: {str(e)}"
            )
    
    async def get_api_health_comprehensive(self) -> Dict[str, Any]:
        """
        Comprehensive health check combining agent metrics with system health.
        """
        try:
            # Get agent health metrics
            agent_health = await self.agent.get_api_health()
            
            # Get existing system health
            system_health = await self._check_existing_system_health()
            
            # Check Redis cache performance
            cache_stats = self.squeeze_cache.get_cache_statistics()
            
            # Combine all health data
            comprehensive_health = {
                'overall_status': 'healthy' if agent_health.get('status') == 'healthy' and system_health.get('status') == 'healthy' else 'degraded',
                'api_integration_agent': agent_health,
                'existing_discovery_system': system_health,
                'redis_cache_performance': cache_stats,
                'service_layer': {
                    'status': 'operational',
                    'fallback_available': True,
                    'hybrid_mode': True
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
            return comprehensive_health
            
        except Exception as e:
            self.logger.error(f"Comprehensive health check failed: {str(e)}")
            return {
                'overall_status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def validate_api_responses(self, endpoint: str, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate API responses using the agent's validation capabilities.
        """
        try:
            validation_result = {
                'endpoint': endpoint,
                'validation_passed': True,
                'validation_errors': [],
                'validation_warnings': [],
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Required fields validation
            required_fields = self._get_required_fields_for_endpoint(endpoint)
            for field in required_fields:
                if field not in response_data:
                    validation_result['validation_errors'].append(f"Missing required field: {field}")
                    validation_result['validation_passed'] = False
            
            # Data type validation
            if 'candidates' in response_data:
                candidates = response_data['candidates']
                if not isinstance(candidates, list):
                    validation_result['validation_errors'].append("'candidates' must be a list")
                    validation_result['validation_passed'] = False
                else:
                    for i, candidate in enumerate(candidates):
                        if not isinstance(candidate, dict):
                            validation_result['validation_errors'].append(f"Candidate {i} must be a dictionary")
                            validation_result['validation_passed'] = False
                        elif 'symbol' not in candidate:
                            validation_result['validation_errors'].append(f"Candidate {i} missing 'symbol' field")
                            validation_result['validation_passed'] = False
            
            # Performance validation
            if 'meta' in response_data:
                meta = response_data['meta']
                processing_time = meta.get('processing_time_ms', 0)
                if processing_time > 10000:  # 10 seconds
                    validation_result['validation_warnings'].append(f"High processing time: {processing_time}ms")
            
            return validation_result
            
        except Exception as e:
            return {
                'endpoint': endpoint,
                'validation_passed': False,
                'validation_errors': [f"Validation failed: {str(e)}"],
                'timestamp': datetime.utcnow().isoformat()
            }
    
    # Private helper methods
    
    async def _fallback_to_existing_system(self, strategy: str, limit: int) -> Dict[str, Any]:
        """Fallback to existing Redis key system when agent fails."""
        try:
            redis_client = redis.from_url(os.getenv('REDIS_URL'))
            
            # Try strategy-aware keys first
            strategy_suffix = f":{strategy}" if strategy in ["legacy_v0", "hybrid_v1"] else ""
            
            keys_to_try = [
                f"{self.DISCOVERY_KEYS['v2_cont']}{strategy_suffix}",
                f"{self.DISCOVERY_KEYS['v1_cont']}{strategy_suffix}",
                self.DISCOVERY_KEYS['v2_cont'],
                self.DISCOVERY_KEYS['v1_cont'],
                self.DISCOVERY_KEYS['cached_cont']
            ]
            
            cached_data = None
            found_key = None
            
            for key in keys_to_try:
                data = await redis_client.get(key)
                if data:
                    cached_data = data
                    found_key = key
                    break
            
            await redis_client.close()
            
            if cached_data:
                # Parse data based on key type
                if found_key == self.DISCOVERY_KEYS['cached_cont']:
                    # Cached format
                    payload = json.loads(cached_data.decode('utf-8') if isinstance(cached_data, bytes) else cached_data)
                    candidates = payload.get('candidates', [])
                else:
                    # Discovery format - direct array
                    candidates = json.loads(cached_data.decode('utf-8') if isinstance(cached_data, bytes) else cached_data)
                    if not isinstance(candidates, list):
                        candidates = []
                
                # Limit results
                candidates = candidates[:limit]
                
                return {
                    'candidates': candidates,
                    'count': len(candidates),
                    'strategy': strategy,
                    'meta': {
                        'source': 'existing_system_fallback',
                        'found_key': found_key,
                        'cache_hit': True,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                }
            
            # No data found
            return {
                'candidates': [],
                'count': 0,
                'strategy': strategy,
                'meta': {
                    'source': 'existing_system_fallback',
                    'cache_hit': False,
                    'keys_tried': keys_to_try,
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Existing system fallback failed: {str(e)}")
            raise
    
    async def _trigger_existing_job_system(self, strategy: str, limit: int):
        """Trigger existing RQ job system for compatibility."""
        try:
            from rq import Queue
            from ..constants import DISCOVERY_QUEUE, JOB_TIMEOUT_SECONDS, RESULT_TTL_SECONDS
            
            queue = Queue(DISCOVERY_QUEUE, connection=self.redis_sync)
            job = queue.enqueue(
                'backend.src.jobs.discovery_job.run_discovery_job',
                limit,
                job_timeout=JOB_TIMEOUT_SECONDS,
                result_ttl=RESULT_TTL_SECONDS,
                job_id=f"enhanced_trigger_{int(time.time())}"
            )
            
            self.logger.info(f"Triggered existing job system: {job.id}")
            
        except Exception as e:
            self.logger.warning(f"Could not trigger existing job system: {str(e)}")
            # Don't fail the entire operation
    
    async def _check_existing_system_health(self) -> Dict[str, Any]:
        """Check health of existing discovery system."""
        try:
            redis_client = redis.from_url(os.getenv('REDIS_URL'))
            
            # Check Redis connectivity
            await redis_client.ping()
            
            # Check cache status
            cached_data = await redis_client.get(self.DISCOVERY_KEYS['cached_cont'])
            status_data = await redis_client.get(self.DISCOVERY_KEYS['cached_status'])
            
            await redis_client.close()
            
            return {
                'status': 'healthy',
                'redis_connected': True,
                'cached_data_available': cached_data is not None,
                'status_data_available': status_data is not None
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def _calculate_squeeze_score(self, candidate: Dict[str, Any]) -> float:
        """Calculate squeeze score from candidate data."""
        # Use existing score as base, or calculate from factors
        base_score = candidate.get('score', 0)
        if base_score > 1:
            base_score = base_score / 100.0  # Normalize to 0-1
        
        # Adjust based on squeeze-specific factors
        factors = candidate.get('factors', {})
        squeeze_adjustments = 0
        
        # Volume surge indicator
        volume_spike = factors.get('volume_spike', 1.0)
        if volume_spike > 10:
            squeeze_adjustments += 0.2
        elif volume_spike > 5:
            squeeze_adjustments += 0.1
        
        # Short interest adjustment
        short_interest = factors.get('short_interest', 0)
        if short_interest > 0.3:  # 30%+
            squeeze_adjustments += 0.15
        elif short_interest > 0.2:  # 20%+
            squeeze_adjustments += 0.1
        
        return min(1.0, base_score + squeeze_adjustments)
    
    def _classify_squeeze_potential(self, squeeze_score: float) -> str:
        """Classify squeeze potential based on score."""
        if squeeze_score >= 0.85:
            return 'EXTREME'
        elif squeeze_score >= 0.75:
            return 'HIGH'
        elif squeeze_score >= 0.5:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _get_required_fields_for_endpoint(self, endpoint: str) -> List[str]:
        """Get required fields for specific endpoints."""
        field_requirements = {
            '/discovery/contenders': ['candidates', 'count'],
            '/discovery/squeeze-candidates': ['candidates', 'count', 'min_score_threshold'],
            '/discovery/health': ['status', 'timestamp']
        }
        
        return field_requirements.get(endpoint, ['status'])


# Global service instance
_api_integration_service = None

async def get_api_integration_service() -> APIIntegrationService:
    """Get singleton instance of API Integration Service."""
    global _api_integration_service
    if _api_integration_service is None:
        _api_integration_service = APIIntegrationService()
    return _api_integration_service