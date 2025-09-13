"""
Performance Monitor and Optimizer

Comprehensive performance monitoring and optimization system for the API Integration Agent.
Tracks response times, identifies bottlenecks, and provides optimization recommendations.
"""

import asyncio
import json
import logging
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Deque
from enum import Enum

import psutil


class PerformanceMetric(Enum):
    """Performance metric types."""
    RESPONSE_TIME = "response_time"
    CACHE_HIT_RATIO = "cache_hit_ratio"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    REDIS_LATENCY = "redis_latency"


class OptimizationLevel(Enum):
    """Optimization priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PerformanceSample:
    """Individual performance measurement."""
    timestamp: float
    metric_type: PerformanceMetric
    value: float
    endpoint: Optional[str] = None
    strategy: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


@dataclass
class PerformanceAlert:
    """Performance alert definition."""
    alert_id: str
    metric_type: PerformanceMetric
    threshold_exceeded: float
    threshold_limit: float
    severity: OptimizationLevel
    endpoint: Optional[str] = None
    suggestion: Optional[str] = None
    timestamp: Optional[str] = None


@dataclass
class OptimizationRecommendation:
    """Performance optimization recommendation."""
    recommendation_id: str
    category: str
    priority: OptimizationLevel
    title: str
    description: str
    estimated_impact: str
    implementation_effort: str
    affected_endpoints: List[str]
    metrics_improved: List[PerformanceMetric]


class PerformanceMonitor:
    """
    Comprehensive performance monitoring and optimization system.
    
    Features:
    - Real-time performance tracking
    - Bottleneck identification
    - Automatic optimization recommendations
    - Performance alerting
    - Historical trend analysis
    - Resource usage monitoring
    """
    
    def __init__(self, max_samples: int = 10000):
        self.logger = logging.getLogger(__name__)
        
        # Sample storage (using deques for efficient rotation)
        self.max_samples = max_samples
        self.samples: Dict[PerformanceMetric, Deque[PerformanceSample]] = defaultdict(
            lambda: deque(maxlen=max_samples)
        )
        
        # Endpoint-specific metrics
        self.endpoint_metrics: Dict[str, Dict[PerformanceMetric, Deque[float]]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=1000))
        )
        
        # Performance thresholds
        self.thresholds = {
            PerformanceMetric.RESPONSE_TIME: {
                'warning': 2000,   # 2 seconds
                'critical': 5000   # 5 seconds
            },
            PerformanceMetric.CACHE_HIT_RATIO: {
                'warning': 0.8,    # 80%
                'critical': 0.6    # 60%
            },
            PerformanceMetric.ERROR_RATE: {
                'warning': 0.05,   # 5%
                'critical': 0.10   # 10%
            },
            PerformanceMetric.MEMORY_USAGE: {
                'warning': 80,     # 80%
                'critical': 90     # 90%
            },
            PerformanceMetric.CPU_USAGE: {
                'warning': 80,     # 80%
                'critical': 90     # 90%
            }
        }
        
        # Active alerts
        self.active_alerts: Dict[str, PerformanceAlert] = {}
        
        # Optimization tracking
        self.optimization_history = []
        self.last_optimization_check = time.time()
        
        # System monitoring
        self.system_monitor_interval = 60  # 60 seconds
        self.last_system_check = 0
    
    async def record_performance_sample(
        self,
        metric_type: PerformanceMetric,
        value: float,
        endpoint: Optional[str] = None,
        strategy: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """
        Record a performance measurement sample.
        
        Args:
            metric_type: Type of performance metric
            value: Measured value
            endpoint: API endpoint (if applicable)
            strategy: Strategy used (if applicable)
            additional_data: Additional context data
        """
        try:
            sample = PerformanceSample(
                timestamp=time.time(),
                metric_type=metric_type,
                value=value,
                endpoint=endpoint,
                strategy=strategy,
                additional_data=additional_data
            )
            
            # Store in global samples
            self.samples[metric_type].append(sample)
            
            # Store in endpoint-specific metrics
            if endpoint:
                self.endpoint_metrics[endpoint][metric_type].append(value)
            
            # Check for threshold violations
            await self._check_thresholds(sample)
            
        except Exception as e:
            self.logger.error(f"Failed to record performance sample: {str(e)}")
    
    async def record_api_call(
        self,
        endpoint: str,
        response_time_ms: float,
        success: bool,
        cache_hit: bool = False,
        strategy: Optional[str] = None
    ):
        """
        Record API call performance metrics.
        
        Args:
            endpoint: API endpoint called
            response_time_ms: Response time in milliseconds
            success: Whether the call was successful
            cache_hit: Whether result came from cache
            strategy: Strategy used (if applicable)
        """
        try:
            # Record response time
            await self.record_performance_sample(
                PerformanceMetric.RESPONSE_TIME,
                response_time_ms,
                endpoint=endpoint,
                strategy=strategy,
                additional_data={'cache_hit': cache_hit}
            )
            
            # Update endpoint-specific cache hit ratio
            if endpoint in self.endpoint_metrics:
                endpoint_cache_hits = sum(
                    1 for sample in self.samples[PerformanceMetric.RESPONSE_TIME]
                    if (sample.endpoint == endpoint and 
                        sample.additional_data and 
                        sample.additional_data.get('cache_hit', False))
                )
                endpoint_total_calls = sum(
                    1 for sample in self.samples[PerformanceMetric.RESPONSE_TIME]
                    if sample.endpoint == endpoint
                )
                
                if endpoint_total_calls > 0:
                    cache_ratio = endpoint_cache_hits / endpoint_total_calls
                    await self.record_performance_sample(
                        PerformanceMetric.CACHE_HIT_RATIO,
                        cache_ratio,
                        endpoint=endpoint,
                        strategy=strategy
                    )
            
        except Exception as e:
            self.logger.error(f"Failed to record API call metrics: {str(e)}")
    
    async def monitor_system_resources(self):
        """Monitor system resource usage."""
        try:
            current_time = time.time()
            
            # Throttle system monitoring
            if current_time - self.last_system_check < self.system_monitor_interval:
                return
            
            self.last_system_check = current_time
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            await self.record_performance_sample(
                PerformanceMetric.CPU_USAGE,
                cpu_percent
            )
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            await self.record_performance_sample(
                PerformanceMetric.MEMORY_USAGE,
                memory_percent,
                additional_data={
                    'available_bytes': memory.available,
                    'used_bytes': memory.used
                }
            )
            
        except Exception as e:
            self.logger.error(f"System resource monitoring failed: {str(e)}")
    
    async def analyze_performance_trends(
        self,
        time_window_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        Analyze performance trends over specified time window.
        
        Args:
            time_window_minutes: Time window for analysis
            
        Returns:
            Performance trend analysis results
        """
        try:
            current_time = time.time()
            cutoff_time = current_time - (time_window_minutes * 60)
            
            analysis_results = {}
            
            for metric_type, samples in self.samples.items():
                # Filter samples within time window
                recent_samples = [
                    sample for sample in samples 
                    if sample.timestamp >= cutoff_time
                ]
                
                if not recent_samples:
                    continue
                
                values = [sample.value for sample in recent_samples]
                
                # Calculate statistics
                analysis_results[metric_type.value] = {
                    'sample_count': len(values),
                    'min': min(values),
                    'max': max(values),
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'std_dev': statistics.stdev(values) if len(values) > 1 else 0,
                    'p95': self._calculate_percentile(values, 95),
                    'p99': self._calculate_percentile(values, 99),
                    'trend': self._calculate_trend(values),
                    'quality_assessment': self._assess_metric_quality(metric_type, values)
                }
            
            analysis_results['time_window_minutes'] = time_window_minutes
            analysis_results['analysis_timestamp'] = datetime.utcnow().isoformat()
            
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Performance trend analysis failed: {str(e)}")
            return {
                'error': str(e),
                'analysis_timestamp': datetime.utcnow().isoformat()
            }
    
    async def get_endpoint_performance_summary(
        self,
        endpoint: str,
        time_window_minutes: int = 30
    ) -> Dict[str, Any]:
        """
        Get performance summary for specific endpoint.
        
        Args:
            endpoint: API endpoint to analyze
            time_window_minutes: Time window for analysis
            
        Returns:
            Endpoint performance summary
        """
        try:
            current_time = time.time()
            cutoff_time = current_time - (time_window_minutes * 60)
            
            # Filter samples for this endpoint within time window
            endpoint_samples = {}
            for metric_type, samples in self.samples.items():
                endpoint_samples[metric_type] = [
                    sample for sample in samples
                    if (sample.endpoint == endpoint and 
                        sample.timestamp >= cutoff_time)
                ]
            
            summary = {
                'endpoint': endpoint,
                'time_window_minutes': time_window_minutes,
                'metrics': {}
            }
            
            # Analyze each metric for this endpoint
            for metric_type, samples in endpoint_samples.items():
                if not samples:
                    continue
                
                values = [sample.value for sample in samples]
                
                summary['metrics'][metric_type.value] = {
                    'sample_count': len(values),
                    'avg': statistics.mean(values),
                    'p95': self._calculate_percentile(values, 95),
                    'p99': self._calculate_percentile(values, 99),
                    'trend': self._calculate_trend(values)
                }
            
            # Add endpoint-specific insights
            summary['insights'] = await self._generate_endpoint_insights(endpoint, endpoint_samples)
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Endpoint performance summary failed: {str(e)}")
            return {
                'endpoint': endpoint,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def generate_optimization_recommendations(self) -> List[OptimizationRecommendation]:
        """
        Generate optimization recommendations based on performance analysis.
        
        Returns:
            List of optimization recommendations
        """
        try:
            recommendations = []
            
            # Analyze recent performance
            trend_analysis = await self.analyze_performance_trends(time_window_minutes=30)
            
            # Response time optimization
            response_time_data = trend_analysis.get('response_time', {})
            if response_time_data:
                avg_response_time = response_time_data.get('mean', 0)
                p95_response_time = response_time_data.get('p95', 0)
                
                if avg_response_time > 1000:  # > 1 second
                    recommendations.append(OptimizationRecommendation(
                        recommendation_id=f"opt_response_time_{int(time.time())}",
                        category="response_time",
                        priority=OptimizationLevel.HIGH if avg_response_time > 3000 else OptimizationLevel.MEDIUM,
                        title="Optimize API Response Times",
                        description=f"Average response time ({avg_response_time:.0f}ms) exceeds optimal thresholds",
                        estimated_impact="20-50% response time improvement",
                        implementation_effort="Medium",
                        affected_endpoints=self._get_slow_endpoints(),
                        metrics_improved=[PerformanceMetric.RESPONSE_TIME]
                    ))
            
            # Cache optimization
            cache_hit_data = trend_analysis.get('cache_hit_ratio', {})
            if cache_hit_data:
                avg_cache_ratio = cache_hit_data.get('mean', 0)
                
                if avg_cache_ratio < 0.7:  # < 70%
                    recommendations.append(OptimizationRecommendation(
                        recommendation_id=f"opt_cache_{int(time.time())}",
                        category="caching",
                        priority=OptimizationLevel.HIGH,
                        title="Improve Cache Hit Ratio",
                        description=f"Cache hit ratio ({avg_cache_ratio:.1%}) is below optimal levels",
                        estimated_impact="30-60% response time improvement",
                        implementation_effort="Low to Medium",
                        affected_endpoints=self._get_cache_inefficient_endpoints(),
                        metrics_improved=[PerformanceMetric.CACHE_HIT_RATIO, PerformanceMetric.RESPONSE_TIME]
                    ))
            
            # Memory optimization
            memory_data = trend_analysis.get('memory_usage', {})
            if memory_data:
                avg_memory = memory_data.get('mean', 0)
                
                if avg_memory > 75:  # > 75%
                    recommendations.append(OptimizationRecommendation(
                        recommendation_id=f"opt_memory_{int(time.time())}",
                        category="memory",
                        priority=OptimizationLevel.CRITICAL if avg_memory > 90 else OptimizationLevel.HIGH,
                        title="Optimize Memory Usage",
                        description=f"Memory usage ({avg_memory:.1f}%) approaching critical levels",
                        estimated_impact="Reduced memory pressure and improved stability",
                        implementation_effort="Medium to High",
                        affected_endpoints=["all"],
                        metrics_improved=[PerformanceMetric.MEMORY_USAGE, PerformanceMetric.RESPONSE_TIME]
                    ))
            
            # Error rate optimization
            error_rate_data = trend_analysis.get('error_rate', {})
            if error_rate_data:
                avg_error_rate = error_rate_data.get('mean', 0)
                
                if avg_error_rate > 0.02:  # > 2%
                    recommendations.append(OptimizationRecommendation(
                        recommendation_id=f"opt_errors_{int(time.time())}",
                        category="reliability",
                        priority=OptimizationLevel.HIGH,
                        title="Reduce Error Rate",
                        description=f"Error rate ({avg_error_rate:.1%}) indicates reliability issues",
                        estimated_impact="Improved system reliability and user experience",
                        implementation_effort="Medium",
                        affected_endpoints=self._get_error_prone_endpoints(),
                        metrics_improved=[PerformanceMetric.ERROR_RATE]
                    ))
            
            # Sort by priority
            priority_order = {
                OptimizationLevel.CRITICAL: 4,
                OptimizationLevel.HIGH: 3,
                OptimizationLevel.MEDIUM: 2,
                OptimizationLevel.LOW: 1
            }
            
            recommendations.sort(
                key=lambda r: priority_order.get(r.priority, 0),
                reverse=True
            )
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Optimization recommendation generation failed: {str(e)}")
            return []
    
    async def get_performance_dashboard(self) -> Dict[str, Any]:
        """
        Get comprehensive performance dashboard data.
        
        Returns:
            Performance dashboard data
        """
        try:
            # System resource monitoring
            await self.monitor_system_resources()
            
            # Get recent trend analysis
            trends = await self.analyze_performance_trends(time_window_minutes=60)
            
            # Get optimization recommendations
            recommendations = await self.generate_optimization_recommendations()
            
            # Get active alerts
            active_alerts = list(self.active_alerts.values())
            
            # Calculate overall health score
            health_score = await self._calculate_health_score()
            
            dashboard = {
                'health_score': health_score,
                'performance_trends': trends,
                'active_alerts': [asdict(alert) for alert in active_alerts],
                'optimization_recommendations': [asdict(rec) for rec in recommendations],
                'system_status': {
                    'total_samples': sum(len(samples) for samples in self.samples.values()),
                    'monitored_endpoints': len(self.endpoint_metrics),
                    'alert_count': len(active_alerts),
                    'recommendation_count': len(recommendations)
                },
                'dashboard_timestamp': datetime.utcnow().isoformat()
            }
            
            return dashboard
            
        except Exception as e:
            self.logger.error(f"Performance dashboard generation failed: {str(e)}")
            return {
                'error': str(e),
                'dashboard_timestamp': datetime.utcnow().isoformat()
            }
    
    # Private helper methods
    
    async def _check_thresholds(self, sample: PerformanceSample):
        """Check if sample violates performance thresholds."""
        try:
            thresholds = self.thresholds.get(sample.metric_type)
            if not thresholds:
                return
            
            alert_key = f"{sample.metric_type.value}_{sample.endpoint or 'global'}"
            
            # Check critical threshold
            if sample.value > thresholds.get('critical', float('inf')):
                alert = PerformanceAlert(
                    alert_id=f"alert_{int(time.time())}_{hash(alert_key) % 10000:04d}",
                    metric_type=sample.metric_type,
                    threshold_exceeded=sample.value,
                    threshold_limit=thresholds['critical'],
                    severity=OptimizationLevel.CRITICAL,
                    endpoint=sample.endpoint,
                    suggestion=self._get_threshold_suggestion(sample.metric_type, 'critical'),
                    timestamp=datetime.utcnow().isoformat()
                )
                
                self.active_alerts[alert_key] = alert
                self.logger.critical(
                    f"Critical performance threshold exceeded: {alert.metric_type.value} = {alert.threshold_exceeded}",
                    extra={'alert_id': alert.alert_id, 'endpoint': alert.endpoint}
                )
                
            # Check warning threshold
            elif sample.value > thresholds.get('warning', float('inf')):
                # Only create warning alert if no critical alert exists
                if alert_key not in self.active_alerts:
                    alert = PerformanceAlert(
                        alert_id=f"alert_{int(time.time())}_{hash(alert_key) % 10000:04d}",
                        metric_type=sample.metric_type,
                        threshold_exceeded=sample.value,
                        threshold_limit=thresholds['warning'],
                        severity=OptimizationLevel.MEDIUM,
                        endpoint=sample.endpoint,
                        suggestion=self._get_threshold_suggestion(sample.metric_type, 'warning'),
                        timestamp=datetime.utcnow().isoformat()
                    )
                    
                    self.active_alerts[alert_key] = alert
                    self.logger.warning(
                        f"Performance threshold warning: {alert.metric_type.value} = {alert.threshold_exceeded}",
                        extra={'alert_id': alert.alert_id, 'endpoint': alert.endpoint}
                    )
            else:
                # Clear alert if threshold is no longer exceeded
                if alert_key in self.active_alerts:
                    del self.active_alerts[alert_key]
                    
        except Exception as e:
            self.logger.error(f"Threshold checking failed: {str(e)}")
    
    def _calculate_percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile value from list of values."""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index == int(index):
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from values."""
        if len(values) < 2:
            return "insufficient_data"
        
        # Simple linear trend calculation
        n = len(values)
        x_values = list(range(n))
        
        # Calculate slope
        x_mean = sum(x_values) / n
        y_mean = sum(values) / n
        
        numerator = sum((x_values[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return "flat"
        
        slope = numerator / denominator
        
        if abs(slope) < 0.01:
            return "stable"
        elif slope > 0:
            return "increasing"
        else:
            return "decreasing"
    
    def _assess_metric_quality(self, metric_type: PerformanceMetric, values: List[float]) -> str:
        """Assess quality of metric values."""
        if not values:
            return "no_data"
        
        avg_value = statistics.mean(values)
        
        if metric_type == PerformanceMetric.RESPONSE_TIME:
            if avg_value < 500:
                return "excellent"
            elif avg_value < 1000:
                return "good"
            elif avg_value < 2000:
                return "fair"
            else:
                return "poor"
        
        elif metric_type == PerformanceMetric.CACHE_HIT_RATIO:
            if avg_value > 0.9:
                return "excellent"
            elif avg_value > 0.8:
                return "good"
            elif avg_value > 0.7:
                return "fair"
            else:
                return "poor"
        
        elif metric_type == PerformanceMetric.ERROR_RATE:
            if avg_value < 0.01:
                return "excellent"
            elif avg_value < 0.02:
                return "good"
            elif avg_value < 0.05:
                return "fair"
            else:
                return "poor"
        
        return "unknown"
    
    async def _generate_endpoint_insights(
        self,
        endpoint: str,
        samples: Dict[PerformanceMetric, List[PerformanceSample]]
    ) -> List[str]:
        """Generate insights for specific endpoint."""
        insights = []
        
        try:
            # Response time insights
            response_samples = samples.get(PerformanceMetric.RESPONSE_TIME, [])
            if response_samples:
                values = [s.value for s in response_samples]
                avg_time = statistics.mean(values)
                
                if avg_time > 2000:
                    insights.append(f"Slow response times detected (avg: {avg_time:.0f}ms)")
                
                # Cache hit analysis
                cache_hits = sum(1 for s in response_samples 
                               if s.additional_data and s.additional_data.get('cache_hit', False))
                cache_ratio = cache_hits / len(response_samples) if response_samples else 0
                
                if cache_ratio < 0.5:
                    insights.append(f"Low cache hit ratio: {cache_ratio:.1%}")
            
            # Strategy performance comparison
            strategy_performance = defaultdict(list)
            for sample in response_samples:
                if sample.strategy:
                    strategy_performance[sample.strategy].append(sample.value)
            
            if len(strategy_performance) > 1:
                best_strategy = min(strategy_performance.items(), 
                                  key=lambda x: statistics.mean(x[1]))
                insights.append(f"Best performing strategy: {best_strategy[0]}")
            
        except Exception as e:
            self.logger.error(f"Insight generation failed: {str(e)}")
        
        return insights
    
    async def _calculate_health_score(self) -> float:
        """Calculate overall system health score (0-100)."""
        try:
            scores = []
            
            # Response time score
            response_samples = list(self.samples[PerformanceMetric.RESPONSE_TIME])
            if response_samples:
                recent_responses = [s.value for s in response_samples[-100:]]  # Last 100 samples
                avg_response_time = statistics.mean(recent_responses)
                
                # Score inversely proportional to response time
                response_score = max(0, 100 - (avg_response_time / 50))  # 50ms = 1 point
                scores.append(min(100, response_score))
            
            # Cache hit ratio score
            cache_samples = list(self.samples[PerformanceMetric.CACHE_HIT_RATIO])
            if cache_samples:
                recent_cache = [s.value for s in cache_samples[-10:]]  # Last 10 samples
                avg_cache_ratio = statistics.mean(recent_cache)
                cache_score = avg_cache_ratio * 100
                scores.append(cache_score)
            
            # Error rate score (inverted)
            error_samples = list(self.samples[PerformanceMetric.ERROR_RATE])
            if error_samples:
                recent_errors = [s.value for s in error_samples[-10:]]
                avg_error_rate = statistics.mean(recent_errors)
                error_score = max(0, 100 - (avg_error_rate * 1000))  # 0.1% error = 10 points off
                scores.append(error_score)
            
            # System resource scores
            memory_samples = list(self.samples[PerformanceMetric.MEMORY_USAGE])
            if memory_samples:
                recent_memory = [s.value for s in memory_samples[-5:]]
                avg_memory = statistics.mean(recent_memory)
                memory_score = max(0, 100 - avg_memory)  # 1% memory = 1 point off
                scores.append(memory_score)
            
            # Calculate weighted average
            if scores:
                return round(statistics.mean(scores), 1)
            else:
                return 100.0  # No data = assume healthy
                
        except Exception as e:
            self.logger.error(f"Health score calculation failed: {str(e)}")
            return 50.0  # Default moderate health score on error
    
    def _get_slow_endpoints(self) -> List[str]:
        """Get list of endpoints with slow response times."""
        slow_endpoints = []
        
        for endpoint, metrics in self.endpoint_metrics.items():
            response_times = list(metrics.get(PerformanceMetric.RESPONSE_TIME, []))
            if response_times:
                avg_time = statistics.mean(response_times)
                if avg_time > 1500:  # > 1.5 seconds
                    slow_endpoints.append(endpoint)
        
        return slow_endpoints
    
    def _get_cache_inefficient_endpoints(self) -> List[str]:
        """Get list of endpoints with poor cache performance."""
        inefficient_endpoints = []
        
        for endpoint, metrics in self.endpoint_metrics.items():
            cache_ratios = list(metrics.get(PerformanceMetric.CACHE_HIT_RATIO, []))
            if cache_ratios:
                avg_ratio = statistics.mean(cache_ratios)
                if avg_ratio < 0.6:  # < 60%
                    inefficient_endpoints.append(endpoint)
        
        return inefficient_endpoints
    
    def _get_error_prone_endpoints(self) -> List[str]:
        """Get list of endpoints with high error rates."""
        error_prone_endpoints = []
        
        # This would need to be tracked separately by endpoint
        # For now, return empty list
        return error_prone_endpoints
    
    def _get_threshold_suggestion(self, metric_type: PerformanceMetric, severity: str) -> str:
        """Get suggestion for threshold violation."""
        suggestions = {
            PerformanceMetric.RESPONSE_TIME: {
                'warning': "Consider optimizing database queries, adding caching, or reviewing algorithm efficiency",
                'critical': "Immediate action required: check for blocking operations, database issues, or resource exhaustion"
            },
            PerformanceMetric.CACHE_HIT_RATIO: {
                'warning': "Review caching strategy, increase cache TTL, or optimize cache invalidation",
                'critical': "Cache system may be malfunctioning - check Redis connectivity and configuration"
            },
            PerformanceMetric.MEMORY_USAGE: {
                'warning': "Monitor memory usage trends and consider implementing memory optimization",
                'critical': "Risk of OOM - implement immediate memory cleanup or increase available memory"
            },
            PerformanceMetric.CPU_USAGE: {
                'warning': "High CPU usage detected - consider optimizing algorithms or scaling resources",
                'critical': "CPU exhaustion - immediate scaling or optimization required"
            }
        }
        
        return suggestions.get(metric_type, {}).get(severity, "Review system performance and consider optimization")


# Global monitor instance
_performance_monitor = None

def get_performance_monitor() -> PerformanceMonitor:
    """Get singleton performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor