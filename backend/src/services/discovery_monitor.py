#!/usr/bin/env python3
"""
Discovery Pipeline Monitor - Zero Disruption Monitoring
Tracks discovery flow: 10K+ stocks → filtering stages → final candidates
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from ..shared.database import get_db_pool
from ..shared.redis_client import get_redis_client

logger = logging.getLogger(__name__)

@dataclass
class DiscoveryFlowStats:
    """Discovery pipeline flow statistics"""
    timestamp: str
    universe_size: int
    filtering_stages: Dict[str, int]
    final_candidates: int
    processing_time_ms: int
    health_score: float
    alerts: List[str]
    
class DiscoveryMonitor:
    """
    Non-invasive discovery pipeline monitoring
    Tracks flow without interfering with existing discovery logic
    """
    
    def __init__(self):
        self.redis = get_redis_client()
        self.monitoring_prefix = "amc:monitor:discovery:"
        
    async def track_discovery_run(self, trace_data: Dict, candidates: List) -> DiscoveryFlowStats:
        """
        Track a discovery run from trace data
        ZERO IMPACT - Only reads existing trace data
        """
        try:
            start_time = time.time()
            
            # Extract flow data from existing trace
            universe_size = trace_data.get("counts_in", {}).get("universe", 0)
            filtering_stages = trace_data.get("counts_out", {})
            final_candidates = len(candidates)
            
            # Calculate health metrics
            health_score = self._calculate_health_score(universe_size, filtering_stages, final_candidates)
            
            # Generate alerts if needed
            alerts = self._generate_alerts(universe_size, filtering_stages, final_candidates)
            
            # Create flow stats
            flow_stats = DiscoveryFlowStats(
                timestamp=datetime.now().isoformat(),
                universe_size=universe_size,
                filtering_stages=filtering_stages,
                final_candidates=final_candidates,
                processing_time_ms=int((time.time() - start_time) * 1000),
                health_score=health_score,
                alerts=alerts
            )
            
            # Store for tracking (non-blocking)
            await self._store_flow_stats(flow_stats)
            
            # Send alerts if critical issues detected
            if alerts:
                await self._send_alerts(alerts, flow_stats)
            
            logger.info(f"Discovery flow tracked: {universe_size} → {final_candidates} candidates, health: {health_score:.2f}")
            return flow_stats
            
        except Exception as e:
            logger.error(f"Discovery monitoring error (non-critical): {e}")
            # Return minimal stats on error - monitoring failure doesn't break discovery
            return DiscoveryFlowStats(
                timestamp=datetime.now().isoformat(),
                universe_size=0,
                filtering_stages={},
                final_candidates=len(candidates),
                processing_time_ms=0,
                health_score=0.0,
                alerts=[f"Monitoring error: {str(e)}"]
            )
    
    def _calculate_health_score(self, universe_size: int, filtering_stages: Dict, final_candidates: int) -> float:
        """Calculate discovery pipeline health score (0.0 - 1.0)"""
        
        score_components = []
        
        # Universe size check (target: 5000+ stocks)
        if universe_size >= 5000:
            score_components.append(1.0)
        elif universe_size >= 1000:
            score_components.append(0.8)
        elif universe_size >= 100:
            score_components.append(0.4)
        else:
            score_components.append(0.0)  # Critical: using fallback
        
        # Candidate count check (target: 10-50 candidates)
        if 10 <= final_candidates <= 50:
            score_components.append(1.0)
        elif 5 <= final_candidates <= 100:
            score_components.append(0.7)
        elif final_candidates > 0:
            score_components.append(0.3)
        else:
            score_components.append(0.0)  # Critical: no candidates
        
        # Filtering efficiency (should retain 0.1% - 1% of universe)
        if universe_size > 0:
            retention_rate = final_candidates / universe_size
            if 0.001 <= retention_rate <= 0.01:  # 0.1% - 1%
                score_components.append(1.0)
            elif 0.0001 <= retention_rate <= 0.05:  # 0.01% - 5%
                score_components.append(0.6)
            else:
                score_components.append(0.2)
        else:
            score_components.append(0.0)
        
        return sum(score_components) / len(score_components)
    
    def _generate_alerts(self, universe_size: int, filtering_stages: Dict, final_candidates: int) -> List[str]:
        """Generate alerts for critical discovery issues"""
        
        alerts = []
        
        # Critical: Universe too small (fallback detected)
        if universe_size < 1000:
            alerts.append(f"CRITICAL: Discovery using small universe ({universe_size} stocks) - fallback system active!")
        
        # Critical: No candidates found
        if final_candidates == 0:
            alerts.append("CRITICAL: Discovery found 0 candidates - system may be broken!")
        
        # Warning: Very few candidates
        elif final_candidates < 5:
            alerts.append(f"WARNING: Discovery found only {final_candidates} candidates - filters may be too restrictive")
        
        # Warning: Too many candidates (filters too loose)
        elif final_candidates > 100:
            alerts.append(f"WARNING: Discovery found {final_candidates} candidates - filters may be too loose")
        
        # Info: Normal operation confirmation
        if not alerts and 10 <= final_candidates <= 50:
            alerts.append(f"INFO: Discovery pipeline healthy - {universe_size:,} stocks → {final_candidates} candidates")
        
        return alerts
    
    async def _store_flow_stats(self, flow_stats: DiscoveryFlowStats):
        """Store flow statistics for tracking (non-blocking)"""
        try:
            # Store in Redis with 24-hour expiration
            key = f"{self.monitoring_prefix}flow:{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.redis.setex(key, 86400, json.dumps(asdict(flow_stats)))
            
            # Keep latest stats easily accessible
            self.redis.setex(f"{self.monitoring_prefix}latest", 3600, json.dumps(asdict(flow_stats)))
            
            # Store in database for historical tracking
            await self._store_in_database(flow_stats)
            
        except Exception as e:
            logger.error(f"Failed to store flow stats (non-critical): {e}")
    
    async def _store_in_database(self, flow_stats: DiscoveryFlowStats):
        """Store flow statistics in database"""
        try:
            pool = await get_db_pool()
            if not pool:
                return
                
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO monitoring.discovery_flow_stats 
                    (timestamp, universe_size, filtering_stages, final_candidates, 
                     processing_time_ms, health_score, alerts)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, 
                    datetime.fromisoformat(flow_stats.timestamp),
                    flow_stats.universe_size,
                    json.dumps(flow_stats.filtering_stages),
                    flow_stats.final_candidates,
                    flow_stats.processing_time_ms,
                    flow_stats.health_score,
                    json.dumps(flow_stats.alerts)
                )
        except Exception as e:
            logger.error(f"Failed to store flow stats in database (non-critical): {e}")
    
    async def _send_alerts(self, alerts: List[str], flow_stats: DiscoveryFlowStats):
        """Send alerts for critical issues (non-blocking)"""
        try:
            # Store alerts in Redis for dashboard access
            alert_key = f"{self.monitoring_prefix}alerts"
            alert_data = {
                'timestamp': flow_stats.timestamp,
                'health_score': flow_stats.health_score,
                'alerts': alerts,
                'flow_summary': f"{flow_stats.universe_size} → {flow_stats.final_candidates}"
            }
            
            self.redis.lpush(alert_key, json.dumps(alert_data))
            self.redis.ltrim(alert_key, 0, 99)  # Keep last 100 alerts
            self.redis.expire(alert_key, 604800)  # 7 days
            
            # Publish to Redis pub/sub for real-time notifications
            self.redis.publish("amc:alerts:discovery", json.dumps(alert_data))
            
        except Exception as e:
            logger.error(f"Failed to send alerts (non-critical): {e}")
    
    async def get_recent_flow_stats(self, hours: int = 24) -> List[DiscoveryFlowStats]:
        """Get recent discovery flow statistics"""
        try:
            pool = await get_db_pool()
            if not pool:
                return []
                
            async with pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM monitoring.discovery_flow_stats 
                    WHERE timestamp >= $1
                    ORDER BY timestamp DESC
                    LIMIT 100
                """, datetime.now() - timedelta(hours=hours))
                
                return [
                    DiscoveryFlowStats(
                        timestamp=row['timestamp'].isoformat(),
                        universe_size=row['universe_size'],
                        filtering_stages=json.loads(row['filtering_stages']),
                        final_candidates=row['final_candidates'],
                        processing_time_ms=row['processing_time_ms'],
                        health_score=row['health_score'],
                        alerts=json.loads(row['alerts'])
                    ) for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get recent flow stats: {e}")
            return []
    
    async def get_current_health_status(self) -> Dict:
        """Get current discovery pipeline health status"""
        try:
            latest_key = f"{self.monitoring_prefix}latest"
            latest_data = self.redis.get(latest_key)
            
            if latest_data:
                stats = json.loads(latest_data)
                return {
                    'status': 'healthy' if stats['health_score'] > 0.7 else 'warning' if stats['health_score'] > 0.3 else 'critical',
                    'health_score': stats['health_score'],
                    'last_update': stats['timestamp'],
                    'universe_size': stats['universe_size'],
                    'final_candidates': stats['final_candidates'],
                    'alerts': stats.get('alerts', [])
                }
            else:
                return {
                    'status': 'unknown',
                    'health_score': 0.0,
                    'last_update': None,
                    'message': 'No recent discovery data available'
                }
        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            return {'status': 'error', 'message': str(e)}

# Global monitor instance
_discovery_monitor = None

def get_discovery_monitor() -> DiscoveryMonitor:
    """Get singleton discovery monitor instance"""
    global _discovery_monitor
    if _discovery_monitor is None:
        _discovery_monitor = DiscoveryMonitor()
    return _discovery_monitor