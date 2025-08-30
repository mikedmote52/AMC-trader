import asyncio
import asyncpg
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
import statistics
import psutil
import os

@dataclass
class SystemHealthMetrics:
    """Comprehensive system health metrics"""
    timestamp: datetime
    
    # Discovery System Health
    discovery_system_status: str  # HEALTHY, WARNING, CRITICAL, DOWN
    daily_candidate_count: int
    avg_composite_score: float
    discovery_api_response_time: float  # milliseconds
    discovery_error_rate: float  # percentage
    
    # Thesis Generation Health
    thesis_system_status: str
    thesis_generation_success_rate: float
    avg_thesis_confidence: float
    thesis_api_response_time: float
    thesis_accuracy_rate: float
    
    # Market Data Health
    market_data_status: str
    polygon_api_health: bool
    data_freshness_minutes: float  # How old is the latest data
    data_completeness_pct: float
    api_rate_limit_usage: float
    
    # Database Health
    database_status: str
    db_connection_pool_usage: float
    query_performance_avg: float  # Average query time
    storage_usage_pct: float
    active_connections: int
    
    # Portfolio Management Health
    portfolio_sync_status: str
    positions_sync_lag_minutes: float
    unrealized_pl_accuracy: float
    broker_api_health: bool
    
    # Performance Analytics Health
    analytics_processing_status: str
    last_analytics_update: datetime
    metrics_calculation_time: float
    report_generation_success: bool
    
    # Overall System Health
    overall_health_score: float  # 0-100 composite health score
    system_status: str  # HEALTHY, DEGRADED, CRITICAL, DOWN
    active_alerts: List[str]
    performance_vs_baseline: float  # % vs June-July performance

@dataclass
class SystemAlert:
    """System alert for health monitoring"""
    alert_id: str
    severity: str  # INFO, WARNING, CRITICAL, EMERGENCY
    component: str  # discovery, thesis, market_data, database, portfolio, analytics
    message: str
    details: str
    created_at: datetime
    acknowledged: bool = False
    resolved: bool = False
    resolved_at: Optional[datetime] = None

class SystemHealthMonitor:
    """Comprehensive system health monitoring and alerting"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv('DATABASE_URL', 'postgresql://localhost/amc_trader')
        self.polygon_api_key = os.getenv('POLYGON_API_KEY')
        self.alpaca_api_key = os.getenv('ALPACA_API_KEY')
        
        # Health thresholds
        self.health_thresholds = {
            'discovery_min_candidates': 5,      # Minimum daily candidates
            'discovery_min_score': 4.0,        # Minimum average composite score
            'discovery_max_response_time': 5000, # Max API response time (ms)
            'discovery_max_error_rate': 10.0,   # Max error rate %
            
            'thesis_min_success_rate': 90.0,    # Min thesis generation success %
            'thesis_min_confidence': 0.6,       # Min average confidence
            'thesis_max_response_time': 3000,   # Max response time (ms)
            'thesis_min_accuracy': 65.0,        # Min accuracy %
            
            'data_max_age_minutes': 60,         # Max data age
            'data_min_completeness': 85.0,      # Min data completeness %
            'api_rate_limit_warning': 80.0,     # Warning at 80% rate limit
            
            'db_max_pool_usage': 80.0,          # Max connection pool usage %
            'db_max_query_time': 1000,          # Max average query time (ms)
            'db_max_storage_usage': 85.0,       # Max storage usage %
            
            'portfolio_max_sync_lag': 30,       # Max sync lag minutes
            'portfolio_min_accuracy': 95.0,     # Min P&L accuracy %
            
            'analytics_max_update_lag': 24,     # Max update lag hours
            'analytics_max_calc_time': 30000,   # Max calculation time (ms)
            
            'overall_health_warning': 70.0,     # Warning threshold
            'overall_health_critical': 50.0     # Critical threshold
        }
        
        # Baseline performance (June-July 2024)
        self.performance_baseline = {
            'daily_candidates': 8,
            'avg_composite_score': 6.5,
            'thesis_accuracy': 73.0,
            'avg_return': 63.8,
            'explosive_growth_rate': 46.7
        }
    
    async def get_db_pool(self):
        """Get database connection pool"""
        try:
            return await asyncpg.create_pool(self.database_url, min_size=1, max_size=10)
        except Exception as e:
            print(f"Database connection failed: {e}")
            return None
    
    async def collect_system_health_metrics(self) -> SystemHealthMetrics:
        """Collect comprehensive system health metrics"""
        timestamp = datetime.utcnow()
        
        # Collect metrics from each subsystem
        discovery_health = await self._check_discovery_system_health()
        thesis_health = await self._check_thesis_system_health()
        market_data_health = await self._check_market_data_health()
        database_health = await self._check_database_health()
        portfolio_health = await self._check_portfolio_health()
        analytics_health = await self._check_analytics_health()
        
        # Calculate overall health score
        overall_score = self._calculate_overall_health_score(
            discovery_health, thesis_health, market_data_health,
            database_health, portfolio_health, analytics_health
        )
        
        # Determine system status
        system_status = self._determine_system_status(overall_score)
        
        # Generate active alerts
        active_alerts = self._generate_alerts(
            discovery_health, thesis_health, market_data_health,
            database_health, portfolio_health, analytics_health
        )
        
        # Performance comparison
        performance_vs_baseline = await self._calculate_performance_vs_baseline()
        
        metrics = SystemHealthMetrics(
            timestamp=timestamp,
            
            # Discovery system
            discovery_system_status=discovery_health['status'],
            daily_candidate_count=discovery_health['candidate_count'],
            avg_composite_score=discovery_health['avg_score'],
            discovery_api_response_time=discovery_health['response_time'],
            discovery_error_rate=discovery_health['error_rate'],
            
            # Thesis system
            thesis_system_status=thesis_health['status'],
            thesis_generation_success_rate=thesis_health['success_rate'],
            avg_thesis_confidence=thesis_health['avg_confidence'],
            thesis_api_response_time=thesis_health['response_time'],
            thesis_accuracy_rate=thesis_health['accuracy_rate'],
            
            # Market data
            market_data_status=market_data_health['status'],
            polygon_api_health=market_data_health['polygon_healthy'],
            data_freshness_minutes=market_data_health['data_age'],
            data_completeness_pct=market_data_health['completeness'],
            api_rate_limit_usage=market_data_health['rate_limit_usage'],
            
            # Database
            database_status=database_health['status'],
            db_connection_pool_usage=database_health['pool_usage'],
            query_performance_avg=database_health['avg_query_time'],
            storage_usage_pct=database_health['storage_usage'],
            active_connections=database_health['active_connections'],
            
            # Portfolio
            portfolio_sync_status=portfolio_health['status'],
            positions_sync_lag_minutes=portfolio_health['sync_lag'],
            unrealized_pl_accuracy=portfolio_health['pl_accuracy'],
            broker_api_health=portfolio_health['broker_healthy'],
            
            # Analytics
            analytics_processing_status=analytics_health['status'],
            last_analytics_update=analytics_health['last_update'],
            metrics_calculation_time=analytics_health['calc_time'],
            report_generation_success=analytics_health['report_success'],
            
            # Overall
            overall_health_score=overall_score,
            system_status=system_status,
            active_alerts=active_alerts,
            performance_vs_baseline=performance_vs_baseline
        )
        
        # Store metrics
        await self._store_health_metrics(metrics)
        
        return metrics
    
    async def _check_discovery_system_health(self) -> Dict:
        """Check discovery system health"""
        pool = await self.get_db_pool()
        if not pool:
            return {'status': 'DOWN', 'candidate_count': 0, 'avg_score': 0, 'response_time': 0, 'error_rate': 100}
        
        try:
            async with pool.acquire() as conn:
                # Check today's candidates
                today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                tomorrow = today + timedelta(days=1)
                
                candidate_query = """
                SELECT COUNT(*) as count, AVG(composite_score) as avg_score
                FROM recommendations
                WHERE created_at >= $1 AND created_at < $2
                """
                
                result = await conn.fetchrow(candidate_query, today, tomorrow)
                candidate_count = result['count'] or 0
                avg_score = result['avg_score'] or 0.0
                
                # Check recent discovery performance
                week_query = """
                SELECT COUNT(*) as total, 
                       COUNT(CASE WHEN composite_score IS NULL THEN 1 END) as errors
                FROM recommendations
                WHERE created_at >= $1
                """
                
                week_result = await conn.fetchrow(week_query, today - timedelta(days=7))
                total_attempts = week_result['total'] or 1
                error_count = week_result['errors'] or 0
                error_rate = (error_count / total_attempts) * 100
                
                # Determine status
                status = 'HEALTHY'
                if candidate_count < self.health_thresholds['discovery_min_candidates']:
                    status = 'WARNING'
                if avg_score < self.health_thresholds['discovery_min_score']:
                    status = 'CRITICAL'
                if error_rate > self.health_thresholds['discovery_max_error_rate']:
                    status = 'CRITICAL'
                
                return {
                    'status': status,
                    'candidate_count': candidate_count,
                    'avg_score': avg_score,
                    'response_time': 2000.0,  # Placeholder - would measure actual API response
                    'error_rate': error_rate
                }
                
        except Exception as e:
            print(f"Error checking discovery health: {e}")
            return {'status': 'DOWN', 'candidate_count': 0, 'avg_score': 0, 'response_time': 0, 'error_rate': 100}
        finally:
            if pool:
                await pool.close()
    
    async def _check_thesis_system_health(self) -> Dict:
        """Check thesis generation system health"""
        pool = await self.get_db_pool()
        if not pool:
            return {'status': 'DOWN', 'success_rate': 0, 'avg_confidence': 0, 'response_time': 0, 'accuracy_rate': 0}
        
        try:
            async with pool.acquire() as conn:
                # Check recent thesis generation success
                week_ago = datetime.utcnow() - timedelta(days=7)
                
                thesis_query = """
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN confidence_score IS NOT NULL THEN 1 END) as successful,
                       AVG(confidence_score) as avg_confidence,
                       AVG(prediction_accuracy) as avg_accuracy
                FROM thesis_accuracy_tracking
                WHERE thesis_generated_at >= $1
                """
                
                result = await conn.fetchrow(thesis_query, week_ago)
                total = result['total'] or 0
                successful = result['successful'] or 0
                success_rate = (successful / total * 100) if total > 0 else 0
                avg_confidence = result['avg_confidence'] or 0.0
                accuracy_rate = result['avg_accuracy'] or 0.0
                
                # Determine status
                status = 'HEALTHY'
                if success_rate < self.health_thresholds['thesis_min_success_rate']:
                    status = 'WARNING'
                if avg_confidence < self.health_thresholds['thesis_min_confidence']:
                    status = 'WARNING'
                if accuracy_rate < self.health_thresholds['thesis_min_accuracy']:
                    status = 'CRITICAL'
                
                return {
                    'status': status,
                    'success_rate': success_rate,
                    'avg_confidence': avg_confidence,
                    'response_time': 1500.0,  # Placeholder
                    'accuracy_rate': accuracy_rate
                }
                
        except Exception as e:
            print(f"Error checking thesis health: {e}")
            return {'status': 'DOWN', 'success_rate': 0, 'avg_confidence': 0, 'response_time': 0, 'accuracy_rate': 0}
        finally:
            if pool:
                await pool.close()
    
    async def _check_market_data_health(self) -> Dict:
        """Check market data system health"""
        polygon_healthy = bool(self.polygon_api_key)
        
        # Check data freshness
        pool = await self.get_db_pool()
        data_age = 120.0  # Default to 2 hours if can't check
        completeness = 50.0  # Default to 50% if can't check
        
        if pool:
            try:
                async with pool.acquire() as conn:
                    # Check latest recommendation data age
                    latest_query = """
                    SELECT MAX(created_at) as latest
                    FROM recommendations
                    """
                    
                    latest = await conn.fetchval(latest_query)
                    if latest:
                        data_age = (datetime.utcnow() - latest).total_seconds() / 60
                    
                    # Check data completeness (positions with price data)
                    completeness_query = """
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN last_price > 0 THEN 1 END) as with_price
                    FROM positions
                    """
                    
                    comp_result = await conn.fetchrow(completeness_query)
                    total = comp_result['total'] or 0
                    with_price = comp_result['with_price'] or 0
                    completeness = (with_price / total * 100) if total > 0 else 100
                    
            except Exception as e:
                print(f"Error checking data health: {e}")
            finally:
                await pool.close()
        
        # Determine status
        status = 'HEALTHY'
        if data_age > self.health_thresholds['data_max_age_minutes']:
            status = 'WARNING'
        if completeness < self.health_thresholds['data_min_completeness']:
            status = 'WARNING'
        if not polygon_healthy:
            status = 'CRITICAL'
        
        return {
            'status': status,
            'polygon_healthy': polygon_healthy,
            'data_age': data_age,
            'completeness': completeness,
            'rate_limit_usage': 45.0  # Placeholder - would track actual usage
        }
    
    async def _check_database_health(self) -> Dict:
        """Check database health"""
        pool = await self.get_db_pool()
        if not pool:
            return {'status': 'DOWN', 'pool_usage': 100, 'avg_query_time': 10000, 'storage_usage': 100, 'active_connections': 0}
        
        try:
            async with pool.acquire() as conn:
                # Check active connections
                connections_query = "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
                active_connections = await conn.fetchval(connections_query) or 0
                
                # Check database size (simplified)
                size_query = "SELECT pg_size_pretty(pg_database_size(current_database()))"
                db_size = await conn.fetchval(size_query)
                
                # Pool usage (estimated)
                pool_usage = (active_connections / 20) * 100  # Assuming max 20 connections
                
                status = 'HEALTHY'
                if pool_usage > self.health_thresholds['db_max_pool_usage']:
                    status = 'WARNING'
                if active_connections > 15:
                    status = 'CRITICAL'
                
                return {
                    'status': status,
                    'pool_usage': min(100, pool_usage),
                    'avg_query_time': 500.0,  # Placeholder
                    'storage_usage': 45.0,    # Placeholder
                    'active_connections': active_connections
                }
                
        except Exception as e:
            print(f"Error checking database health: {e}")
            return {'status': 'CRITICAL', 'pool_usage': 100, 'avg_query_time': 10000, 'storage_usage': 100, 'active_connections': 0}
        finally:
            if pool:
                await pool.close()
    
    async def _check_portfolio_health(self) -> Dict:
        """Check portfolio management health"""
        broker_healthy = bool(self.alpaca_api_key)
        
        pool = await self.get_db_pool()
        sync_lag = 60.0  # Default to 1 hour
        pl_accuracy = 85.0  # Default accuracy
        
        if pool:
            try:
                async with pool.acquire() as conn:
                    # Check position update lag
                    latest_update_query = """
                    SELECT MAX(updated_at) as latest
                    FROM positions
                    """
                    
                    latest = await conn.fetchval(latest_update_query)
                    if latest:
                        sync_lag = (datetime.utcnow() - latest).total_seconds() / 60
                    
                    # Check P&L data quality
                    pl_query = """
                    SELECT COUNT(*) as total,
                           COUNT(CASE WHEN unrealized_pl_pct IS NOT NULL THEN 1 END) as with_pl
                    FROM positions
                    """
                    
                    pl_result = await conn.fetchrow(pl_query)
                    total = pl_result['total'] or 0
                    with_pl = pl_result['with_pl'] or 0
                    pl_accuracy = (with_pl / total * 100) if total > 0 else 100
                    
            except Exception as e:
                print(f"Error checking portfolio health: {e}")
            finally:
                await pool.close()
        
        # Determine status
        status = 'HEALTHY'
        if sync_lag > self.health_thresholds['portfolio_max_sync_lag']:
            status = 'WARNING'
        if pl_accuracy < self.health_thresholds['portfolio_min_accuracy']:
            status = 'WARNING'
        if not broker_healthy:
            status = 'CRITICAL'
        
        return {
            'status': status,
            'sync_lag': sync_lag,
            'pl_accuracy': pl_accuracy,
            'broker_healthy': broker_healthy
        }
    
    async def _check_analytics_health(self) -> Dict:
        """Check performance analytics health"""
        pool = await self.get_db_pool()
        last_update = datetime.utcnow() - timedelta(hours=48)  # Default to 48 hours ago
        
        if pool:
            try:
                async with pool.acquire() as conn:
                    # Check latest performance metrics calculation
                    latest_query = """
                    SELECT MAX(calculated_at) as latest
                    FROM performance_metrics
                    """
                    
                    latest = await conn.fetchval(latest_query)
                    if latest:
                        last_update = latest
                    
            except Exception as e:
                print(f"Error checking analytics health: {e}")
            finally:
                await pool.close()
        
        # Calculate lag
        update_lag_hours = (datetime.utcnow() - last_update).total_seconds() / 3600
        
        # Determine status
        status = 'HEALTHY'
        if update_lag_hours > self.health_thresholds['analytics_max_update_lag']:
            status = 'WARNING'
        if update_lag_hours > 48:
            status = 'CRITICAL'
        
        return {
            'status': status,
            'last_update': last_update,
            'calc_time': 15000.0,  # Placeholder
            'report_success': update_lag_hours < 24
        }
    
    def _calculate_overall_health_score(self, discovery_health: Dict, thesis_health: Dict,
                                      market_data_health: Dict, database_health: Dict,
                                      portfolio_health: Dict, analytics_health: Dict) -> float:
        """Calculate weighted overall health score"""
        
        # Component weights (sum to 1.0)
        weights = {
            'discovery': 0.25,    # Most critical for finding opportunities
            'thesis': 0.20,       # Critical for decision making
            'market_data': 0.15,  # Important for accuracy
            'database': 0.15,     # Foundation system
            'portfolio': 0.15,    # Important for tracking
            'analytics': 0.10     # Important for improvement
        }
        
        # Convert status to score
        status_scores = {
            'HEALTHY': 100,
            'WARNING': 70,
            'CRITICAL': 30,
            'DOWN': 0
        }
        
        component_scores = {
            'discovery': status_scores.get(discovery_health['status'], 0),
            'thesis': status_scores.get(thesis_health['status'], 0),
            'market_data': status_scores.get(market_data_health['status'], 0),
            'database': status_scores.get(database_health['status'], 0),
            'portfolio': status_scores.get(portfolio_health['status'], 0),
            'analytics': status_scores.get(analytics_health['status'], 0)
        }
        
        # Calculate weighted score
        overall_score = sum(score * weights[component] for component, score in component_scores.items())
        
        return round(overall_score, 1)
    
    def _determine_system_status(self, overall_score: float) -> str:
        """Determine overall system status"""
        if overall_score >= self.health_thresholds['overall_health_warning']:
            return 'HEALTHY'
        elif overall_score >= self.health_thresholds['overall_health_critical']:
            return 'DEGRADED'
        elif overall_score > 0:
            return 'CRITICAL'
        else:
            return 'DOWN'
    
    def _generate_alerts(self, discovery_health: Dict, thesis_health: Dict,
                        market_data_health: Dict, database_health: Dict,
                        portfolio_health: Dict, analytics_health: Dict) -> List[str]:
        """Generate active system alerts"""
        alerts = []
        
        # Discovery alerts
        if discovery_health['status'] in ['CRITICAL', 'DOWN']:
            alerts.append(f"Discovery system {discovery_health['status'].lower()}")
        if discovery_health['candidate_count'] < self.health_thresholds['discovery_min_candidates']:
            alerts.append(f"Low candidate count: {discovery_health['candidate_count']}")
        
        # Thesis alerts
        if thesis_health['status'] in ['CRITICAL', 'DOWN']:
            alerts.append(f"Thesis system {thesis_health['status'].lower()}")
        if thesis_health['accuracy_rate'] < self.health_thresholds['thesis_min_accuracy']:
            alerts.append(f"Low thesis accuracy: {thesis_health['accuracy_rate']:.1f}%")
        
        # Market data alerts
        if market_data_health['status'] in ['CRITICAL', 'DOWN']:
            alerts.append(f"Market data {market_data_health['status'].lower()}")
        if market_data_health['data_age'] > self.health_thresholds['data_max_age_minutes']:
            alerts.append(f"Stale data: {market_data_health['data_age']:.1f} min old")
        
        # Database alerts
        if database_health['status'] in ['CRITICAL', 'DOWN']:
            alerts.append(f"Database {database_health['status'].lower()}")
        
        # Portfolio alerts
        if portfolio_health['status'] in ['CRITICAL', 'DOWN']:
            alerts.append(f"Portfolio sync {portfolio_health['status'].lower()}")
        
        # Analytics alerts
        if analytics_health['status'] in ['CRITICAL', 'DOWN']:
            alerts.append(f"Analytics {analytics_health['status'].lower()}")
        
        return alerts
    
    async def _calculate_performance_vs_baseline(self) -> float:
        """Calculate current performance vs June-July baseline"""
        pool = await self.get_db_pool()
        if not pool:
            return -50.0  # Assume poor performance if can't check
        
        try:
            async with pool.acquire() as conn:
                # Get recent performance metrics
                recent_query = """
                SELECT metrics_json
                FROM performance_metrics
                ORDER BY calculated_at DESC
                LIMIT 1
                """
                
                recent_row = await conn.fetchrow(recent_query)
                if not recent_row:
                    return -50.0
                
                metrics = json.loads(recent_row['metrics_json'])
                
                # Compare key metrics to baseline
                current_avg_return = metrics.get('average_return', 0)
                baseline_avg_return = self.performance_baseline['avg_return']
                
                performance_gap = current_avg_return - baseline_avg_return
                return performance_gap
                
        except Exception as e:
            print(f"Error calculating performance vs baseline: {e}")
            return -50.0
        finally:
            if pool:
                await pool.close()
    
    async def _store_health_metrics(self, metrics: SystemHealthMetrics):
        """Store health metrics in database"""
        pool = await self.get_db_pool()
        if not pool:
            return
        
        try:
            async with pool.acquire() as conn:
                query = """
                INSERT INTO system_health_metrics
                (timestamp, metrics_json, overall_health_score, system_status, active_alerts_count)
                VALUES ($1, $2, $3, $4, $5)
                """
                
                metrics_json = json.dumps(asdict(metrics), default=str)
                
                await conn.execute(query,
                                 metrics.timestamp,
                                 metrics_json,
                                 metrics.overall_health_score,
                                 metrics.system_status,
                                 len(metrics.active_alerts))
                                 
        except Exception as e:
            print(f"Error storing health metrics: {e}")
        finally:
            if pool:
                await pool.close()
    
    async def generate_health_report(self) -> Dict:
        """Generate comprehensive system health report"""
        
        # Collect current health metrics
        health_metrics = await self.collect_system_health_metrics()
        
        # Get health trends
        trends = await self._get_health_trends()
        
        # Generate insights and recommendations
        insights = []
        recommendations = []
        critical_actions = []
        
        # Overall system analysis
        if health_metrics.overall_health_score < self.health_thresholds['overall_health_critical']:
            insights.append(f"CRITICAL: System health at {health_metrics.overall_health_score:.1f}%")
            critical_actions.append("IMMEDIATE: Emergency system review required")
        
        # Component-specific analysis
        if health_metrics.discovery_system_status in ['CRITICAL', 'DOWN']:
            insights.append("Discovery system failure - no new opportunities")
            critical_actions.append("URGENT: Restore discovery system - revenue impact")
        
        if health_metrics.thesis_accuracy_rate < 50:
            insights.append(f"Thesis accuracy critically low at {health_metrics.thesis_accuracy_rate:.1f}%")
            recommendations.append("Review and retrain thesis generation algorithm")
        
        if health_metrics.performance_vs_baseline < -40:
            insights.append(f"Performance {health_metrics.performance_vs_baseline:.1f}% below June-July baseline")
            critical_actions.append("URGENT: Performance restoration program needed")
        
        # Data quality issues
        if health_metrics.data_completeness_pct < 80:
            insights.append(f"Data quality issues - {health_metrics.data_completeness_pct:.1f}% completeness")
            recommendations.append("Implement data quality monitoring and cleanup")
        
        # System resource issues
        if health_metrics.db_connection_pool_usage > 90:
            insights.append("Database connection pool near capacity")
            recommendations.append("Scale database connections or optimize queries")
        
        return {
            'executive_summary': {
                'overall_health_score': health_metrics.overall_health_score,
                'system_status': health_metrics.system_status,
                'active_alerts': len(health_metrics.active_alerts),
                'performance_vs_baseline': health_metrics.performance_vs_baseline,
                'critical_components': self._identify_critical_components(health_metrics),
                'emergency_action_required': len(critical_actions) > 0
            },
            'current_metrics': asdict(health_metrics),
            'health_trends': trends,
            'component_status': {
                'discovery': health_metrics.discovery_system_status,
                'thesis': health_metrics.thesis_system_status,
                'market_data': health_metrics.market_data_status,
                'database': health_metrics.database_status,
                'portfolio': health_metrics.portfolio_sync_status,
                'analytics': health_metrics.analytics_processing_status
            },
            'system_insights': insights,
            'recommendations': recommendations,
            'critical_actions': critical_actions,
            'restoration_priorities': self._generate_restoration_priorities(health_metrics)
        }
    
    async def _get_health_trends(self, days_back: int = 7) -> Dict:
        """Get health trends over specified period"""
        pool = await self.get_db_pool()
        if not pool:
            return {'trend': 'no_data', 'history': []}
        
        try:
            async with pool.acquire() as conn:
                start_date = datetime.utcnow() - timedelta(days=days_back)
                
                query = """
                SELECT timestamp, overall_health_score, system_status
                FROM system_health_metrics
                WHERE timestamp >= $1
                ORDER BY timestamp DESC
                """
                
                rows = await conn.fetch(query, start_date)
                
                if len(rows) < 2:
                    return {'trend': 'insufficient_data', 'history': []}
                
                scores = [row['overall_health_score'] for row in rows]
                
                # Analyze trend
                recent_avg = statistics.mean(scores[:3]) if len(scores) >= 3 else scores[0]
                older_avg = statistics.mean(scores[-3:]) if len(scores) >= 3 else scores[-1]
                
                trend_direction = 'improving' if recent_avg > older_avg + 5 else \
                                 'declining' if recent_avg < older_avg - 5 else 'stable'
                
                return {
                    'trend': trend_direction,
                    'current_score': scores[0],
                    'avg_score': statistics.mean(scores),
                    'min_score': min(scores),
                    'max_score': max(scores),
                    'history': [{'timestamp': row['timestamp'], 'score': row['overall_health_score'], 
                               'status': row['system_status']} for row in rows]
                }
                
        except Exception as e:
            print(f"Error getting health trends: {e}")
            return {'trend': 'error', 'history': []}
        finally:
            if pool:
                await pool.close()
    
    def _identify_critical_components(self, metrics: SystemHealthMetrics) -> List[str]:
        """Identify components in critical state"""
        critical = []
        
        if metrics.discovery_system_status in ['CRITICAL', 'DOWN']:
            critical.append('discovery')
        if metrics.thesis_system_status in ['CRITICAL', 'DOWN']:
            critical.append('thesis')
        if metrics.market_data_status in ['CRITICAL', 'DOWN']:
            critical.append('market_data')
        if metrics.database_status in ['CRITICAL', 'DOWN']:
            critical.append('database')
        if metrics.portfolio_sync_status in ['CRITICAL', 'DOWN']:
            critical.append('portfolio')
        if metrics.analytics_processing_status in ['CRITICAL', 'DOWN']:
            critical.append('analytics')
        
        return critical
    
    def _generate_restoration_priorities(self, metrics: SystemHealthMetrics) -> List[Dict]:
        """Generate prioritized system restoration actions"""
        priorities = []
        
        # Priority 1: Discovery system (revenue critical)
        if metrics.discovery_system_status != 'HEALTHY':
            priorities.append({
                'priority': 1,
                'component': 'Discovery System',
                'current_status': metrics.discovery_system_status,
                'impact': 'CRITICAL - No new opportunities',
                'action': 'Restore candidate discovery and scoring',
                'urgency': 'IMMEDIATE'
            })
        
        # Priority 2: Performance vs baseline
        if metrics.performance_vs_baseline < -30:
            priorities.append({
                'priority': 2,
                'component': 'Overall Performance',
                'current_status': f'{metrics.performance_vs_baseline:.1f}% below baseline',
                'impact': 'HIGH - Missing profit opportunities',
                'action': 'Implement June-July parameter restoration',
                'urgency': 'URGENT'
            })
        
        # Priority 3: Thesis accuracy
        if metrics.thesis_accuracy_rate < 60:
            priorities.append({
                'priority': 3,
                'component': 'Thesis Generation',
                'current_status': f'{metrics.thesis_accuracy_rate:.1f}% accuracy',
                'impact': 'HIGH - Poor decision quality',
                'action': 'Retrain thesis algorithm',
                'urgency': 'HIGH'
            })
        
        # Priority 4: Data quality
        if metrics.data_completeness_pct < 85:
            priorities.append({
                'priority': 4,
                'component': 'Data Quality',
                'current_status': f'{metrics.data_completeness_pct:.1f}% complete',
                'impact': 'MEDIUM - Accuracy degradation',
                'action': 'Implement data validation pipeline',
                'urgency': 'MEDIUM'
            })
        
        return sorted(priorities, key=lambda x: x['priority'])

# Database table for system health metrics
CREATE_SYSTEM_HEALTH_TABLE = """
CREATE TABLE IF NOT EXISTS system_health_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    metrics_json JSONB NOT NULL,
    overall_health_score FLOAT NOT NULL,
    system_status VARCHAR(20) NOT NULL,
    active_alerts_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_system_health_timestamp ON system_health_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_system_health_status ON system_health_metrics(system_status);
CREATE INDEX IF NOT EXISTS idx_system_health_score ON system_health_metrics(overall_health_score);
"""