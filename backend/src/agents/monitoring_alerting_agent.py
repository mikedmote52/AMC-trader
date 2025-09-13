"""
Monitoring and Alerting Agent for AMC-TRADER System

You are a Monitoring and Alerting Agent responsible for monitoring the overall system health, 
performance, and error states.

Your tasks include:
1. Collect logs, metrics, and error events from various components and agents
2. Aggregate and analyze the collected data to identify potential issues and anomalies
3. Set up proactive monitoring and alerting rules based on predefined thresholds and conditions
4. Trigger alerts and notifications to the relevant stakeholders for timely action

Integrate with external monitoring tools (e.g., Prometheus, Grafana) and logging frameworks 
(e.g., ELK stack) for enhanced visibility and insights.
"""

import asyncio
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import psutil
from collections import defaultdict, deque
import pika
import threading


class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Alert:
    id: str
    title: str
    message: str
    severity: AlertSeverity
    component: str
    timestamp: datetime
    metadata: Dict[str, Any]
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class Metric:
    name: str
    value: float
    type: MetricType
    labels: Dict[str, str]
    timestamp: datetime


@dataclass
class HealthCheck:
    component: str
    status: str
    latency_ms: float
    timestamp: datetime
    metadata: Dict[str, Any]


class MonitoringAlertingAgent:
    """
    Core monitoring and alerting agent for the AMC-TRADER system.
    Provides comprehensive monitoring capabilities with integration support
    for external tools like Prometheus, Grafana, and ELK stack.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Storage for metrics and alerts
        self.metrics_buffer = deque(maxlen=10000)
        self.alerts = {}
        self.health_checks = {}
        self.alert_rules = []
        self.notification_handlers = []
        
        # Performance tracking
        self.system_metrics = {
            'cpu_percent': 0.0,
            'memory_percent': 0.0,
            'disk_usage': 0.0,
            'network_io': {'bytes_sent': 0, 'bytes_recv': 0}
        }
        
        # Component status tracking
        self.component_status = defaultdict(lambda: {'status': 'unknown', 'last_check': None})
        
        # Alert thresholds (configurable)
        self.thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'api_response_time': 5000,  # ms
            'error_rate': 0.05,  # 5%
            'discovery_latency': 10000,  # ms
            'trade_execution_time': 3000,  # ms
        }
        
        # Update thresholds from config
        self.thresholds.update(self.config.get('thresholds', {}))
        
        # Orchestration messaging setup
        self.orchestration_queue = 'orchestration_queue'
        self.rabbitmq_host = self.config.get('rabbitmq_host', 'localhost')
        self.agent_name = 'Monitoring and Alerting Agent'
        
        self.running = False
        self.monitoring_interval = self.config.get('monitoring_interval', 30)  # seconds

    def _setup_logging(self) -> logging.Logger:
        """Setup structured logging for the monitoring agent"""
        logger = logging.getLogger('monitoring_agent')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger

    def send_message_to_orchestrator(self, message: Dict[str, Any]):
        """Send message to the Orchestration Agent via RabbitMQ"""
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(self.rabbitmq_host)
            )
            channel = connection.channel()
            channel.queue_declare(queue=self.orchestration_queue, durable=True)
            
            # Add agent identification to the message
            message['agent_name'] = self.agent_name
            message['timestamp'] = datetime.utcnow().isoformat()
            
            channel.basic_publish(
                exchange='',
                routing_key=self.orchestration_queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
            )
            connection.close()
            
            self.logger.info(f"Message sent to orchestrator: {message.get('status', 'unknown')}")
            
        except Exception as e:
            self.logger.error(f"Failed to send message to orchestrator: {e}")

    async def start_monitoring(self):
        """Start the continuous monitoring loop"""
        self.running = True
        self.logger.info("Monitoring and Alerting Agent started")
        
        # Notify orchestrator that monitoring has started
        start_message = {
            'status': 'monitoring_started',
            'data': {
                'monitoring_interval': self.monitoring_interval,
                'thresholds': self.thresholds,
                'components_to_monitor': ['system_metrics', 'api_health', 'alerts', 'cleanup']
            }
        }
        self.send_message_to_orchestrator(start_message)
        
        # Start monitoring tasks
        tasks = [
            asyncio.create_task(self._monitor_system_metrics()),
            asyncio.create_task(self._monitor_api_health()),
            asyncio.create_task(self._process_alerts()),
            asyncio.create_task(self._cleanup_old_data()),
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            self.logger.error(f"Monitoring error: {e}")
            # Notify orchestrator of error
            error_message = {
                'status': 'monitoring_error',
                'data': {
                    'error': str(e),
                    'error_type': type(e).__name__
                }
            }
            self.send_message_to_orchestrator(error_message)
        finally:
            self.running = False

    async def stop_monitoring(self):
        """Stop the monitoring agent gracefully"""
        self.running = False
        self.logger.info("Monitoring and Alerting Agent stopped")
        
        # Notify orchestrator that monitoring has stopped
        stop_message = {
            'status': 'monitoring_stopped',
            'data': {
                'total_metrics_collected': len(self.metrics_buffer),
                'total_alerts_generated': len(self.alerts),
                'final_system_status': self.get_system_status()
            }
        }
        self.send_message_to_orchestrator(stop_message)

    async def _monitor_system_metrics(self):
        """Monitor system-level metrics (CPU, memory, disk, network)"""
        cycle_count = 0
        status_report_interval = 5  # Send status every 5 cycles
        
        while self.running:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                await self.record_metric("system.cpu_percent", cpu_percent, MetricType.GAUGE)
                
                # Memory usage
                memory = psutil.virtual_memory()
                await self.record_metric("system.memory_percent", memory.percent, MetricType.GAUGE)
                
                # Disk usage
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                await self.record_metric("system.disk_percent", disk_percent, MetricType.GAUGE)
                
                # Network I/O
                net_io = psutil.net_io_counters()
                await self.record_metric("system.network_bytes_sent", net_io.bytes_sent, MetricType.COUNTER)
                await self.record_metric("system.network_bytes_recv", net_io.bytes_recv, MetricType.COUNTER)
                
                # Check thresholds and trigger alerts
                await self._check_system_thresholds(cpu_percent, memory.percent, disk_percent)
                
                # Send periodic status updates to orchestrator
                cycle_count += 1
                if cycle_count % status_report_interval == 0:
                    status_message = {
                        'status': 'system_metrics_update',
                        'data': {
                            'cpu_percent': cpu_percent,
                            'memory_percent': memory.percent,
                            'disk_percent': disk_percent,
                            'metrics_collected': len(self.metrics_buffer),
                            'active_alerts': len([a for a in self.alerts.values() if not a.resolved]),
                            'cycle_count': cycle_count
                        }
                    }
                    self.send_message_to_orchestrator(status_message)
                
            except Exception as e:
                self.logger.error(f"System metrics monitoring error: {e}")
                # Notify orchestrator of monitoring error
                error_message = {
                    'status': 'system_metrics_error',
                    'data': {
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'cycle_count': cycle_count
                    }
                }
                self.send_message_to_orchestrator(error_message)
            
            await asyncio.sleep(self.monitoring_interval)

    async def _monitor_api_health(self):
        """Monitor API endpoints health and performance"""
        api_base = self.config.get('api_base_url', 'https://amc-trader.onrender.com')
        health_endpoints = [
            f"{api_base}/health",
            f"{api_base}/discovery/diagnostics",
            f"{api_base}/discovery/calibration/status"
        ]
        
        while self.running:
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                    for endpoint in health_endpoints:
                        start_time = time.time()
                        try:
                            async with session.get(endpoint) as response:
                                latency_ms = (time.time() - start_time) * 1000
                                
                                # Record health check
                                component = endpoint.split('/')[-1]
                                health_check = HealthCheck(
                                    component=component,
                                    status="healthy" if response.status == 200 else "unhealthy",
                                    latency_ms=latency_ms,
                                    timestamp=datetime.utcnow(),
                                    metadata={
                                        'status_code': response.status,
                                        'endpoint': endpoint
                                    }
                                )
                                
                                self.health_checks[component] = health_check
                                await self.record_metric(f"api.{component}.latency_ms", latency_ms, MetricType.TIMER)
                                await self.record_metric(f"api.{component}.status", 1 if response.status == 200 else 0, MetricType.GAUGE)
                                
                                # Check API response time threshold
                                if latency_ms > self.thresholds['api_response_time']:
                                    await self._trigger_alert(
                                        f"api_slow_response_{component}",
                                        f"Slow API Response: {component}",
                                        f"API endpoint {endpoint} responded in {latency_ms:.2f}ms (threshold: {self.thresholds['api_response_time']}ms)",
                                        AlertSeverity.MEDIUM,
                                        component,
                                        {'latency_ms': latency_ms, 'threshold': self.thresholds['api_response_time']}
                                    )
                                
                        except Exception as e:
                            await self.record_metric(f"api.{component}.status", 0, MetricType.GAUGE)
                            await self._trigger_alert(
                                f"api_down_{component}",
                                f"API Endpoint Down: {component}",
                                f"Failed to reach {endpoint}: {str(e)}",
                                AlertSeverity.HIGH,
                                component,
                                {'endpoint': endpoint, 'error': str(e)}
                            )
            
            except Exception as e:
                self.logger.error(f"API health monitoring error: {e}")
            
            await asyncio.sleep(self.monitoring_interval * 2)  # Check API less frequently

    async def record_metric(self, name: str, value: float, metric_type: MetricType, labels: Optional[Dict[str, str]] = None):
        """Record a metric with timestamp"""
        metric = Metric(
            name=name,
            value=value,
            type=metric_type,
            labels=labels or {},
            timestamp=datetime.utcnow()
        )
        
        self.metrics_buffer.append(metric)
        
        # Log high-impact metrics
        if any(keyword in name for keyword in ['error', 'latency', 'cpu', 'memory']):
            self.logger.info(f"Metric recorded: {name}={value}")

    async def _trigger_alert(self, alert_id: str, title: str, message: str, 
                           severity: AlertSeverity, component: str, metadata: Dict[str, Any]):
        """Trigger an alert if conditions are met"""
        # Check if alert already exists and is unresolved
        if alert_id in self.alerts and not self.alerts[alert_id].resolved:
            return
        
        alert = Alert(
            id=alert_id,
            title=title,
            message=message,
            severity=severity,
            component=component,
            timestamp=datetime.utcnow(),
            metadata=metadata
        )
        
        self.alerts[alert_id] = alert
        
        # Log alert
        self.logger.warning(f"ALERT [{severity.value.upper()}] {title}: {message}")
        
        # Notify orchestrator of new alert
        alert_message = {
            'status': 'alert_triggered',
            'data': {
                'alert_id': alert_id,
                'title': title,
                'message': message,
                'severity': severity.value,
                'component': component,
                'metadata': metadata,
                'timestamp': alert.timestamp.isoformat()
            }
        }
        self.send_message_to_orchestrator(alert_message)
        
        # Send notifications
        await self._send_notifications(alert)

    async def _send_notifications(self, alert: Alert):
        """Send alert notifications through configured channels"""
        for handler in self.notification_handlers:
            try:
                await handler(alert)
            except Exception as e:
                self.logger.error(f"Notification handler error: {e}")

    async def resolve_alert(self, alert_id: str):
        """Resolve an alert"""
        if alert_id in self.alerts and not self.alerts[alert_id].resolved:
            self.alerts[alert_id].resolved = True
            self.alerts[alert_id].resolved_at = datetime.utcnow()
            self.logger.info(f"Alert resolved: {alert_id}")
            
            # Notify orchestrator of alert resolution
            resolution_message = {
                'status': 'alert_resolved',
                'data': {
                    'alert_id': alert_id,
                    'resolved_at': self.alerts[alert_id].resolved_at.isoformat(),
                    'duration_seconds': (self.alerts[alert_id].resolved_at - self.alerts[alert_id].timestamp).total_seconds()
                }
            }
            self.send_message_to_orchestrator(resolution_message)

    async def _check_system_thresholds(self, cpu_percent: float, memory_percent: float, disk_percent: float):
        """Check system metrics against thresholds and trigger alerts"""
        if cpu_percent > self.thresholds['cpu_usage']:
            await self._trigger_alert(
                "high_cpu_usage",
                "High CPU Usage",
                f"CPU usage is {cpu_percent:.1f}% (threshold: {self.thresholds['cpu_usage']}%)",
                AlertSeverity.MEDIUM if cpu_percent < 90 else AlertSeverity.HIGH,
                "system",
                {'cpu_percent': cpu_percent, 'threshold': self.thresholds['cpu_usage']}
            )
        else:
            await self.resolve_alert("high_cpu_usage")
        
        if memory_percent > self.thresholds['memory_usage']:
            await self._trigger_alert(
                "high_memory_usage",
                "High Memory Usage",
                f"Memory usage is {memory_percent:.1f}% (threshold: {self.thresholds['memory_usage']}%)",
                AlertSeverity.MEDIUM if memory_percent < 95 else AlertSeverity.CRITICAL,
                "system",
                {'memory_percent': memory_percent, 'threshold': self.thresholds['memory_usage']}
            )
        else:
            await self.resolve_alert("high_memory_usage")
        
        if disk_percent > self.thresholds['disk_usage']:
            await self._trigger_alert(
                "high_disk_usage",
                "High Disk Usage",
                f"Disk usage is {disk_percent:.1f}% (threshold: {self.thresholds['disk_usage']}%)",
                AlertSeverity.HIGH,
                "system",
                {'disk_percent': disk_percent, 'threshold': self.thresholds['disk_usage']}
            )
        else:
            await self.resolve_alert("high_disk_usage")

    async def _process_alerts(self):
        """Process and manage active alerts"""
        while self.running:
            try:
                # Auto-resolve stale alerts (older than 1 hour with no recent trigger)
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                for alert_id, alert in self.alerts.items():
                    if not alert.resolved and alert.timestamp < cutoff_time:
                        # Check if conditions still exist for system alerts
                        if alert.component == "system":
                            continue  # System alerts are checked continuously
                        
                        await self.resolve_alert(alert_id)
                
            except Exception as e:
                self.logger.error(f"Alert processing error: {e}")
            
            await asyncio.sleep(60)  # Process alerts every minute

    async def _cleanup_old_data(self):
        """Clean up old metrics and resolved alerts"""
        while self.running:
            try:
                # Clean up metrics older than 24 hours
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                
                # Clean up resolved alerts older than 7 days
                alert_cutoff_time = datetime.utcnow() - timedelta(days=7)
                alerts_to_remove = [
                    alert_id for alert_id, alert in self.alerts.items()
                    if alert.resolved and alert.resolved_at and alert.resolved_at < alert_cutoff_time
                ]
                
                for alert_id in alerts_to_remove:
                    del self.alerts[alert_id]
                
                if alerts_to_remove:
                    self.logger.info(f"Cleaned up {len(alerts_to_remove)} old resolved alerts")
                
            except Exception as e:
                self.logger.error(f"Data cleanup error: {e}")
            
            await asyncio.sleep(3600)  # Run cleanup hourly

    def add_notification_handler(self, handler: Callable):
        """Add a notification handler function"""
        self.notification_handlers.append(handler)

    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status summary"""
        active_alerts = [alert for alert in self.alerts.values() if not alert.resolved]
        
        return {
            'status': 'healthy' if not active_alerts else 'warning',
            'active_alerts_count': len(active_alerts),
            'total_alerts': len(self.alerts),
            'metrics_collected': len(self.metrics_buffer),
            'components_monitored': len(self.health_checks),
            'uptime_seconds': time.time() - (self.config.get('start_time', time.time())),
            'last_updated': datetime.utcnow().isoformat()
        }

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of recent metrics"""
        if not self.metrics_buffer:
            return {}
        
        recent_metrics = {}
        for metric in list(self.metrics_buffer)[-100:]:  # Last 100 metrics
            recent_metrics[metric.name] = {
                'value': metric.value,
                'timestamp': metric.timestamp.isoformat(),
                'type': metric.type.value
            }
        
        return recent_metrics

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active (unresolved) alerts"""
        return [
            asdict(alert) for alert in self.alerts.values() 
            if not alert.resolved
        ]


# Example usage and integration functions
async def setup_slack_notifications(webhook_url: str):
    """Example Slack notification handler"""
    async def slack_handler(alert: Alert):
        async with aiohttp.ClientSession() as session:
            payload = {
                'text': f"🚨 *{alert.title}*\n{alert.message}",
                'attachments': [{
                    'color': 'danger' if alert.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL] else 'warning',
                    'fields': [
                        {'title': 'Severity', 'value': alert.severity.value, 'short': True},
                        {'title': 'Component', 'value': alert.component, 'short': True},
                        {'title': 'Time', 'value': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'), 'short': True}
                    ]
                }]
            }
            await session.post(webhook_url, json=payload)
    
    return slack_handler


async def setup_prometheus_exporter(port: int = 8000):
    """Example Prometheus metrics exporter"""
    try:
        from prometheus_client import start_http_server, Gauge, Counter, Histogram
        
        # Create Prometheus metrics
        cpu_gauge = Gauge('system_cpu_percent', 'CPU usage percentage')
        memory_gauge = Gauge('system_memory_percent', 'Memory usage percentage')
        api_latency_histogram = Histogram('api_request_duration_seconds', 'API request duration')
        
        start_http_server(port)
        return {
            'cpu_gauge': cpu_gauge,
            'memory_gauge': memory_gauge,
            'api_latency_histogram': api_latency_histogram
        }
    except ImportError:
        logging.warning("prometheus_client not installed, skipping Prometheus integration")
        return {}


# Main execution example
if __name__ == "__main__":
    async def main():
        config = {
            'api_base_url': 'https://amc-trader.onrender.com',
            'monitoring_interval': 30,
            'thresholds': {
                'cpu_usage': 80.0,
                'memory_usage': 85.0,
                'api_response_time': 5000
            }
        }
        
        agent = MonitoringAlertingAgent(config)
        
        # Setup notifications (example)
        # slack_handler = await setup_slack_notifications('YOUR_SLACK_WEBHOOK_URL')
        # agent.add_notification_handler(slack_handler)
        
        # Setup Prometheus exporter (example)
        # prometheus_metrics = await setup_prometheus_exporter()
        
        try:
            await agent.start_monitoring()
        except KeyboardInterrupt:
            await agent.stop_monitoring()
    
    asyncio.run(main())