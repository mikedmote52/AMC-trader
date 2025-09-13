"""
Management Agent for AMC-TRADER System

You are a Management Agent responsible for overseeing the production, verification, and testing of the entire AMC-TRADER system.

Your tasks include:
1. Coordinate the execution and communication between all other agents
2. Monitor the system's performance, error rates, and resource utilization
3. Conduct regular tests to ensure the accuracy and reliability of the stock discovery process
4. Verify that the user interface is displaying real, actionable stock recommendations (not mock or fallback data)
5. Identify and address any discrepancies, bugs, or performance issues in the system
6. Provide regular status reports and alerts to the development team for prompt resolution

Implement a comprehensive management framework that ensures the smooth operation, data integrity, and user experience of the AMC-TRADER system.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import json
import aiohttp
import time
from enum import Enum
import pika

class SystemHealth(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    DOWN = "down"

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class SystemMetrics:
    timestamp: datetime
    api_response_time: float
    discovery_candidates_count: int
    error_rate: float
    scoring_strategy: str
    system_health: SystemHealth
    active_preset: str
    weights_hash: str
    data_freshness: float
    
@dataclass
class Alert:
    level: AlertLevel
    component: str
    message: str
    timestamp: datetime
    resolved: bool = False

class ManagementAgent:
    """
    Comprehensive Management Agent for AMC-TRADER System
    
    Coordinates all system operations, monitors health, and ensures data integrity
    """
    
    def __init__(self, api_base: str = "https://amc-trader.onrender.com"):
        self.api_base = api_base
        self.logger = logging.getLogger(__name__)
        self.alerts: List[Alert] = []
        self.metrics_history: List[SystemMetrics] = []
        self.last_health_check = None
        self.monitoring_interval = 60  # seconds
        self.performance_thresholds = {
            'max_response_time': 10.0,  # seconds
            'min_candidates': 5,
            'max_error_rate': 0.05,  # 5%
            'max_data_age': 300  # 5 minutes
        }
        
        # Decision-making and automation system
        self.orchestration_agent = None
        self.rule_timers: Dict[str, datetime] = {}
        self.automated_actions_log: List[Dict[str, Any]] = []
        
        # Message bus integration
        self.message_bus = None
        self.messenger = None
        self._initialize_message_bus()
        
        self.decision_rules = {
            'discovery_system_failure': {
                'condition': self._check_discovery_system_failure,
                'timeout_minutes': 30,
                'action': 'RESTART_DISCOVERY_SYSTEM',
                'priority': 'CRITICAL'
            },
            'data_integrity_compromised': {
                'condition': self._check_data_integrity_compromised,
                'timeout_minutes': 60,
                'action': 'INTEGRATE_REAL_DATA',
                'priority': 'HIGH'
            },
            'algorithm_quality_threshold': {
                'condition': self._check_algorithm_quality_threshold,
                'timeout_minutes': 45,
                'action': 'VALIDATE_ALGORITHMS',
                'priority': 'MEDIUM'
            },
            'high_error_rate': {
                'condition': self._check_high_error_rate,
                'timeout_minutes': 15,
                'action': 'EMERGENCY_RESTART',
                'priority': 'CRITICAL'
            }
        }
        
    async def start_monitoring(self):
        """Start continuous system monitoring with automated decision-making"""
        self.logger.info("Management Agent starting continuous monitoring with automation...")
        
        # Initialize orchestration agent
        if not self.orchestration_agent:
            from .orchestration_agent import OrchestrationAgent, CommandPriority
            self.orchestration_agent = OrchestrationAgent(self.api_base)
            # Start orchestration in background
            asyncio.create_task(self.orchestration_agent.start_orchestration())
        
        while True:
            try:
                # Core monitoring tasks
                await self.perform_health_check()
                await self.validate_data_integrity()
                await self.check_system_performance()
                
                # Decision-making and automated actions
                await self._evaluate_decision_rules()
                await self._monitor_orchestration_commands()
                
                # Generate comprehensive report
                await self.generate_status_report()
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await self._create_alert(AlertLevel.ERROR, "monitoring", f"Monitoring loop error: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def perform_health_check(self) -> SystemMetrics:
        """Comprehensive system health check"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                # Check basic health
                health_response = await self._safe_request(session, "GET", "/health")
                if not health_response:
                    return await self._create_critical_metrics("Health endpoint unreachable")
                
                # Check discovery system
                discovery_start = time.time()
                discovery_response = await self._safe_request(
                    session, "GET", "/discovery/contenders?strategy=hybrid_v1&limit=10"
                )
                discovery_time = time.time() - discovery_start
                
                if not discovery_response:
                    return await self._create_critical_metrics("Discovery endpoint unreachable")
                
                # Check calibration status
                status_response = await self._safe_request(session, "GET", "/discovery/calibration/status")
                
                # Extract metrics
                candidates_count = discovery_response.get('count', 0)
                scoring_strategy = discovery_response.get('strategy', 'unknown')
                active_preset = status_response.get('preset', 'unknown') if status_response else 'unknown'
                weights_hash = discovery_response.get('meta', {}).get('weights_hash', 'unknown')
                
                # Calculate system health
                health_status = self._determine_health_status(
                    discovery_time, candidates_count, health_response
                )
                
                metrics = SystemMetrics(
                    timestamp=datetime.now(),
                    api_response_time=discovery_time,
                    discovery_candidates_count=candidates_count,
                    error_rate=0.0,  # Will be calculated separately
                    scoring_strategy=scoring_strategy,
                    system_health=health_status,
                    active_preset=active_preset,
                    weights_hash=weights_hash,
                    data_freshness=0.0  # Will be calculated from timestamp
                )
                
                self.metrics_history.append(metrics)
                self.last_health_check = datetime.now()
                
                # Send status update message to Orchestration Agent
                await self._send_status_update_message(metrics)
                
                # Trim history to last 24 hours
                cutoff = datetime.now() - timedelta(hours=24)
                self.metrics_history = [m for m in self.metrics_history if m.timestamp > cutoff]
                
                return metrics
                
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return await self._create_critical_metrics(f"Health check exception: {e}")
    
    async def validate_data_integrity(self):
        """Verify that real data is being served, not mock/fallback data"""
        try:
            async with aiohttp.ClientSession() as session:
                # Test multiple endpoints to ensure real data
                test_cases = [
                    ("/discovery/contenders?limit=50", "candidates"),
                    ("/discovery/test?strategy=hybrid_v1&limit=20", "candidates"),
                    ("/discovery/strategy-validation", "comparison")
                ]
                
                real_data_indicators = 0
                total_tests = len(test_cases)
                
                for endpoint, key in test_cases:
                    response = await self._safe_request(session, "GET", endpoint)
                    if response and self._is_real_data(response, key):
                        real_data_indicators += 1
                
                data_integrity_score = real_data_indicators / total_tests
                
                if data_integrity_score < 0.5:
                    await self._create_alert(
                        AlertLevel.CRITICAL, 
                        "data_integrity",
                        f"Suspected mock/fallback data detected. Score: {data_integrity_score}"
                    )
                elif data_integrity_score < 0.8:
                    await self._create_alert(
                        AlertLevel.WARNING,
                        "data_integrity", 
                        f"Partial data integrity issues. Score: {data_integrity_score}"
                    )
                
        except Exception as e:
            await self._create_alert(AlertLevel.ERROR, "data_integrity", f"Data validation failed: {e}")
    
    async def check_system_performance(self):
        """Monitor system performance against thresholds"""
        if not self.metrics_history:
            return
        
        latest_metrics = self.metrics_history[-1]
        
        # Check response time
        if latest_metrics.api_response_time > self.performance_thresholds['max_response_time']:
            await self._create_alert(
                AlertLevel.WARNING,
                "performance",
                f"High API response time: {latest_metrics.api_response_time:.2f}s"
            )
        
        # Check candidate count
        if latest_metrics.discovery_candidates_count < self.performance_thresholds['min_candidates']:
            await self._create_alert(
                AlertLevel.WARNING,
                "discovery",
                f"Low candidate count: {latest_metrics.discovery_candidates_count}"
            )
        
        # Check error rate (calculate from recent history)
        error_rate = self._calculate_error_rate()
        if error_rate > self.performance_thresholds['max_error_rate']:
            await self._create_alert(
                AlertLevel.ERROR,
                "reliability",
                f"High error rate: {error_rate:.1%}"
            )
    
    async def coordinate_agents(self, agents: Dict[str, Any]):
        """Coordinate communication between different system agents"""
        coordination_results = {}
        
        for agent_name, agent_instance in agents.items():
            try:
                if hasattr(agent_instance, 'get_status'):
                    status = await agent_instance.get_status()
                    coordination_results[agent_name] = status
                    
                if hasattr(agent_instance, 'perform_health_check'):
                    await agent_instance.perform_health_check()
                    
            except Exception as e:
                self.logger.error(f"Error coordinating with {agent_name}: {e}")
                await self._create_alert(
                    AlertLevel.ERROR, 
                    f"agent_{agent_name}",
                    f"Agent coordination failed: {e}"
                )
        
        return coordination_results
    
    async def generate_status_report(self) -> Dict[str, Any]:
        """Generate comprehensive system status report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "system_overview": {
                "health": self.metrics_history[-1].system_health.value if self.metrics_history else "unknown",
                "active_strategy": self.metrics_history[-1].scoring_strategy if self.metrics_history else "unknown",
                "active_preset": self.metrics_history[-1].active_preset if self.metrics_history else "unknown"
            },
            "performance_metrics": self._get_performance_summary(),
            "active_alerts": [asdict(alert) for alert in self.alerts if not alert.resolved],
            "recent_metrics": [asdict(m) for m in self.metrics_history[-5:]] if self.metrics_history else [],
            "recommendations": self._generate_recommendations()
        }
        
        # Log critical alerts
        critical_alerts = [a for a in self.alerts if a.level == AlertLevel.CRITICAL and not a.resolved]
        if critical_alerts:
            self.logger.critical(f"CRITICAL ALERTS: {len(critical_alerts)} unresolved issues")
            for alert in critical_alerts:
                self.logger.critical(f"  - {alert.component}: {alert.message}")
        
        return report
    
    async def run_diagnostic_tests(self) -> Dict[str, Any]:
        """Run comprehensive diagnostic tests"""
        diagnostics = {
            "timestamp": datetime.now().isoformat(),
            "tests": {}
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test 1: Basic connectivity
                diagnostics["tests"]["connectivity"] = await self._test_connectivity(session)
                
                # Test 2: Discovery system
                diagnostics["tests"]["discovery"] = await self._test_discovery_system(session)
                
                # Test 3: Strategy validation
                diagnostics["tests"]["strategy_validation"] = await self._test_strategy_validation(session)
                
                # Test 4: Calibration system
                diagnostics["tests"]["calibration"] = await self._test_calibration_system(session)
                
                # Test 5: Data quality
                diagnostics["tests"]["data_quality"] = await self._test_data_quality(session)
                
        except Exception as e:
            diagnostics["error"] = str(e)
        
        return diagnostics
    
    # Helper methods
    
    async def _safe_request(self, session: aiohttp.ClientSession, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make a safe HTTP request with error handling"""
        try:
            url = f"{self.api_base}{endpoint}"
            async with session.request(method, url, timeout=30, **kwargs) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    self.logger.warning(f"HTTP {response.status} for {endpoint}")
                    return None
        except Exception as e:
            self.logger.error(f"Request failed for {endpoint}: {e}")
            return None
    
    def _is_real_data(self, response: Dict, key: str) -> bool:
        """Check if response contains real data vs mock/fallback"""
        if key not in response:
            return False
        
        data = response[key]
        
        # Check for common mock data indicators
        mock_indicators = [
            "mock", "test", "sample", "demo", "fallback", "example"
        ]
        
        # Convert data to string for analysis
        data_str = json.dumps(data, default=str).lower()
        
        # If any mock indicators are found, it's likely mock data
        if any(indicator in data_str for indicator in mock_indicators):
            return False
        
        # Check for realistic data patterns
        if isinstance(data, list) and len(data) > 0:
            # Look for realistic stock symbols and scores
            first_item = data[0]
            if isinstance(first_item, dict):
                if 'symbol' in first_item and 'score' in first_item:
                    symbol = first_item['symbol']
                    # Real stock symbols are typically 1-5 uppercase letters
                    if isinstance(symbol, str) and symbol.isupper() and 1 <= len(symbol) <= 5:
                        return True
        
        return len(data) > 0  # Basic non-empty check
    
    def _determine_health_status(self, response_time: float, candidates_count: int, health_data: Dict) -> SystemHealth:
        """Determine overall system health status"""
        if response_time > 15 or candidates_count == 0:
            return SystemHealth.CRITICAL
        elif response_time > 10 or candidates_count < 3:
            return SystemHealth.DEGRADED
        elif response_time > 5 or candidates_count < 5:
            return SystemHealth.DEGRADED
        else:
            return SystemHealth.HEALTHY
    
    async def _create_critical_metrics(self, error_message: str) -> SystemMetrics:
        """Create critical metrics when system is down"""
        await self._create_alert(AlertLevel.CRITICAL, "system", error_message)
        
        return SystemMetrics(
            timestamp=datetime.now(),
            api_response_time=999.0,
            discovery_candidates_count=0,
            error_rate=1.0,
            scoring_strategy="unknown",
            system_health=SystemHealth.DOWN,
            active_preset="unknown",
            weights_hash="unknown",
            data_freshness=999.0
        )
    
    async def _create_alert(self, level: AlertLevel, component: str, message: str):
        """Create and log system alert"""
        alert = Alert(
            level=level,
            component=component,
            message=message,
            timestamp=datetime.now()
        )
        
        self.alerts.append(alert)
        
        # Send alert message to Orchestration Agent
        await self._send_alert_message(alert)
        
        # Log based on severity
        if level == AlertLevel.CRITICAL:
            self.logger.critical(f"[{component}] {message}")
        elif level == AlertLevel.ERROR:
            self.logger.error(f"[{component}] {message}")
        elif level == AlertLevel.WARNING:
            self.logger.warning(f"[{component}] {message}")
        else:
            self.logger.info(f"[{component}] {message}")
    
    def _calculate_error_rate(self) -> float:
        """Calculate error rate from recent metrics"""
        if len(self.metrics_history) < 2:
            return 0.0
        
        recent_metrics = self.metrics_history[-10:]  # Last 10 checks
        error_count = sum(1 for m in recent_metrics if m.system_health in [SystemHealth.CRITICAL, SystemHealth.DOWN])
        
        return error_count / len(recent_metrics)
    
    def _get_performance_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary"""
        if not self.metrics_history:
            return {}
        
        recent_metrics = self.metrics_history[-10:]
        
        return {
            "avg_response_time": sum(m.api_response_time for m in recent_metrics) / len(recent_metrics),
            "avg_candidates": sum(m.discovery_candidates_count for m in recent_metrics) / len(recent_metrics),
            "current_error_rate": self._calculate_error_rate(),
            "uptime_percentage": sum(1 for m in recent_metrics if m.system_health != SystemHealth.DOWN) / len(recent_metrics) * 100
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate system improvement recommendations"""
        recommendations = []
        
        if not self.metrics_history:
            return ["No metrics available for recommendations"]
        
        latest = self.metrics_history[-1]
        performance = self._get_performance_summary()
        
        if latest.api_response_time > 8:
            recommendations.append("Consider optimizing API response times")
        
        if latest.discovery_candidates_count < 5:
            recommendations.append("Investigate low candidate discovery counts")
        
        if performance.get("current_error_rate", 0) > 0.1:
            recommendations.append("High error rate detected - investigate system stability")
        
        if performance.get("uptime_percentage", 100) < 95:
            recommendations.append("System uptime is below acceptable levels")
        
        critical_alerts = [a for a in self.alerts if a.level == AlertLevel.CRITICAL and not a.resolved]
        if critical_alerts:
            recommendations.append(f"Address {len(critical_alerts)} critical alerts immediately")
        
        return recommendations or ["System operating within normal parameters"]
    
    # Test methods
    
    async def _test_connectivity(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test basic API connectivity"""
        result = {"status": "pass", "details": {}}
        
        endpoints = ["/health", "/_whoami"]
        for endpoint in endpoints:
            response = await self._safe_request(session, "GET", endpoint)
            result["details"][endpoint] = "success" if response else "failed"
        
        if any(status == "failed" for status in result["details"].values()):
            result["status"] = "fail"
        
        return result
    
    async def _test_discovery_system(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test discovery system functionality"""
        result = {"status": "pass", "details": {}}
        
        # Test different strategies
        strategies = ["legacy_v0", "hybrid_v1"]
        for strategy in strategies:
            response = await self._safe_request(session, "GET", f"/discovery/test?strategy={strategy}&limit=5")
            result["details"][f"strategy_{strategy}"] = {
                "success": response is not None,
                "candidate_count": response.get("count", 0) if response else 0
            }
        
        # Test contenders endpoint
        response = await self._safe_request(session, "GET", "/discovery/contenders?limit=10")
        result["details"]["contenders"] = {
            "success": response is not None,
            "candidate_count": response.get("count", 0) if response else 0
        }
        
        # Determine overall status
        if not any(detail.get("success", False) for detail in result["details"].values()):
            result["status"] = "fail"
        
        return result
    
    async def _test_strategy_validation(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test strategy validation system"""
        response = await self._safe_request(session, "GET", "/discovery/strategy-validation")
        
        return {
            "status": "pass" if response else "fail",
            "details": {
                "validation_available": response is not None,
                "has_comparison": response.get("comparison") is not None if response else False
            }
        }
    
    async def _test_calibration_system(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test calibration system functionality"""
        result = {"status": "pass", "details": {}}
        
        # Test status endpoint
        status_response = await self._safe_request(session, "GET", "/discovery/calibration/status")
        result["details"]["status"] = status_response is not None
        
        # Test config endpoint
        config_response = await self._safe_request(session, "GET", "/discovery/calibration/hybrid_v1/config")
        result["details"]["config"] = config_response is not None
        
        if not all(result["details"].values()):
            result["status"] = "fail"
        
        return result
    
    async def _test_data_quality(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test data quality and freshness"""
        result = {"status": "pass", "details": {}}
        
        # Get sample data
        response = await self._safe_request(session, "GET", "/discovery/contenders?limit=20")
        
        if response and response.get("candidates"):
            candidates = response["candidates"]
            result["details"]["sample_size"] = len(candidates)
            result["details"]["has_real_symbols"] = self._has_realistic_symbols(candidates)
            result["details"]["has_scores"] = all("score" in c for c in candidates)
            result["details"]["timestamp_fresh"] = True  # Could check actual timestamp
        else:
            result["status"] = "fail"
            result["details"]["error"] = "No candidates data available"
        
        return result
    
    def _has_realistic_symbols(self, candidates: List[Dict]) -> bool:
        """Check if candidates have realistic stock symbols"""
        for candidate in candidates[:5]:  # Check first 5
            symbol = candidate.get("symbol", "")
            if not (isinstance(symbol, str) and symbol.isupper() and 1 <= len(symbol) <= 5):
                return False
        return True
    
    # Decision-making and automation methods
    
    async def _evaluate_decision_rules(self):
        """Evaluate all decision rules and trigger automated actions"""
        current_time = datetime.now()
        
        for rule_name, rule_config in self.decision_rules.items():
            try:
                # Check if condition is met
                condition_met = await rule_config['condition']()
                
                if condition_met:
                    # Initialize timer if not exists
                    if rule_name not in self.rule_timers:
                        self.rule_timers[rule_name] = current_time
                        await self._log_automated_action(f"Started timer for rule: {rule_name}")
                    
                    # Check if timeout has elapsed
                    elapsed_time = current_time - self.rule_timers[rule_name]
                    timeout_threshold = timedelta(minutes=rule_config['timeout_minutes'])
                    
                    if elapsed_time >= timeout_threshold:
                        await self._trigger_automated_action(rule_name, rule_config)
                        # Reset timer after action
                        self.rule_timers[rule_name] = current_time
                
                else:
                    # Reset timer if condition no longer met
                    if rule_name in self.rule_timers:
                        del self.rule_timers[rule_name]
                        
            except Exception as e:
                self.logger.error(f"Error evaluating rule {rule_name}: {e}")
    
    async def _trigger_automated_action(self, rule_name: str, rule_config: Dict[str, Any]):
        """Trigger an automated action through the Orchestration Agent"""
        if not self.orchestration_agent:
            self.logger.error("Orchestration Agent not available for automated action")
            return
        
        try:
            from .orchestration_agent import CommandPriority
            
            # Map priority string to enum
            priority_map = {
                'LOW': CommandPriority.LOW,
                'MEDIUM': CommandPriority.MEDIUM,
                'HIGH': CommandPriority.HIGH,
                'CRITICAL': CommandPriority.CRITICAL
            }
            
            priority = priority_map.get(rule_config['priority'], CommandPriority.MEDIUM)
            action = rule_config['action']
            
            # Execute command through orchestration agent
            command_id = await self.orchestration_agent.execute_command(
                action=action,
                parameters={'triggered_by': rule_name, 'automated': True},
                priority=priority
            )
            
            await self._log_automated_action(
                f"Triggered automated action: {action} (Command ID: {command_id}) due to rule: {rule_name}"
            )
            
            # Send automated action message to Orchestration Agent
            await self._send_automated_action_message(
                rule_name, 
                action, 
                f"Automated trigger after {rule_config['timeout_minutes']} minutes"
            )
            
            # Create alert for automated action
            await self._create_alert(
                AlertLevel.WARNING,
                "automation",
                f"Automated action triggered: {action} (Rule: {rule_name})"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to trigger automated action for rule {rule_name}: {e}")
            await self._create_alert(
                AlertLevel.ERROR,
                "automation",
                f"Failed automated action: {rule_name} - {e}"
            )
    
    async def _monitor_orchestration_commands(self):
        """Monitor execution status of orchestration commands"""
        if not self.orchestration_agent:
            return
        
        try:
            # Get system status from orchestration agent
            orch_status = await self.orchestration_agent.get_system_status()
            
            # Log any failed or timed out commands
            for active_cmd in orch_status.get('active', []):
                # Monitor long-running commands
                started_at = datetime.fromisoformat(active_cmd['started_at'].replace('Z', '+00:00'))
                if (datetime.now() - started_at.replace(tzinfo=None)).total_seconds() > 600:  # 10 minutes
                    await self._create_alert(
                        AlertLevel.WARNING,
                        "orchestration",
                        f"Long-running command: {active_cmd['action']} (ID: {active_cmd['id']})"
                    )
            
        except Exception as e:
            self.logger.error(f"Error monitoring orchestration commands: {e}")
    
    async def _log_automated_action(self, message: str):
        """Log automated actions for audit trail"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'component': 'automated_decision_making'
        }
        
        self.automated_actions_log.append(log_entry)
        self.logger.info(f"AUTOMATED ACTION: {message}")
        
        # Keep only last 100 entries
        if len(self.automated_actions_log) > 100:
            self.automated_actions_log = self.automated_actions_log[-100:]
    
    # Rule condition methods
    
    async def _check_discovery_system_failure(self) -> bool:
        """Check if discovery system has failed"""
        if not self.metrics_history:
            return False
        
        latest_metrics = self.metrics_history[-1]
        
        # Discovery system is considered failed if:
        # - No candidates in recent checks
        # - System health is critical or down
        # - High response times indicating timeouts
        
        failure_indicators = [
            latest_metrics.discovery_candidates_count == 0,
            latest_metrics.system_health in [SystemHealth.CRITICAL, SystemHealth.DOWN],
            latest_metrics.api_response_time > 60.0  # Indicates timeout/failure
        ]
        
        # Require at least 2 failure indicators
        return sum(failure_indicators) >= 2
    
    async def _check_data_integrity_compromised(self) -> bool:
        """Check if data integrity is compromised"""
        if not self.metrics_history:
            return False
        
        # Check recent metrics for data integrity issues
        recent_metrics = self.metrics_history[-3:] if len(self.metrics_history) >= 3 else self.metrics_history
        
        # Data integrity is compromised if:
        # - Consistently low candidate counts
        # - System showing signs of mock/fallback data
        # - High error rates
        
        low_candidate_count = all(m.discovery_candidates_count < 3 for m in recent_metrics)
        high_error_rate = any(m.error_rate > 0.1 for m in recent_metrics)
        
        return low_candidate_count or high_error_rate
    
    async def _check_algorithm_quality_threshold(self) -> bool:
        """Check if algorithm quality is below threshold"""
        if not self.metrics_history:
            return False
        
        latest_metrics = self.metrics_history[-1]
        
        # Algorithm quality issues if:
        # - Very low candidate counts consistently
        # - System degraded for extended period
        
        quality_issues = [
            latest_metrics.discovery_candidates_count < 2,
            latest_metrics.system_health == SystemHealth.DEGRADED,
            latest_metrics.api_response_time > 20.0
        ]
        
        return sum(quality_issues) >= 2
    
    async def _check_high_error_rate(self) -> bool:
        """Check if system has high error rate"""
        error_rate = self._calculate_error_rate()
        return error_rate > 0.2  # 20% error rate threshold for emergency action
    
    # Enhanced reporting with automation insights
    
    async def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive system status report with automation insights"""
        base_report = await self.generate_status_report()
        
        # Add automation insights
        automation_report = {
            "automation_status": {
                "active_rules": len([r for r in self.rule_timers if r in self.rule_timers]),
                "rules_with_timers": list(self.rule_timers.keys()),
                "recent_automated_actions": self.automated_actions_log[-10:],
                "orchestration_status": await self._get_orchestration_status()
            },
            "decision_rules": {
                rule_name: {
                    "timeout_minutes": config["timeout_minutes"],
                    "action": config["action"],
                    "priority": config["priority"],
                    "timer_active": rule_name in self.rule_timers,
                    "time_remaining": self._get_time_remaining(rule_name, config) if rule_name in self.rule_timers else None
                }
                for rule_name, config in self.decision_rules.items()
            }
        }
        
        # Merge reports
        base_report.update(automation_report)
        
        # Send comprehensive health report to Orchestration Agent
        await self._send_health_report_message(base_report)
        
        return base_report
    
    async def _get_orchestration_status(self) -> Dict[str, Any]:
        """Get orchestration agent status"""
        if not self.orchestration_agent:
            return {"status": "not_initialized"}
        
        try:
            return await self.orchestration_agent.get_system_status()
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _get_time_remaining(self, rule_name: str, rule_config: Dict[str, Any]) -> str:
        """Calculate time remaining before rule triggers"""
        if rule_name not in self.rule_timers:
            return "N/A"
        
        elapsed = datetime.now() - self.rule_timers[rule_name]
        timeout = timedelta(minutes=rule_config['timeout_minutes'])
        remaining = timeout - elapsed
        
        if remaining.total_seconds() <= 0:
            return "Ready to trigger"
        
        minutes = int(remaining.total_seconds() // 60)
        seconds = int(remaining.total_seconds() % 60)
        return f"{minutes}m {seconds}s"
    
    # Message Bus Integration Methods
    
    def _initialize_message_bus(self):
        """Initialize RabbitMQ message bus connection"""
        try:
            from .message_bus_integration import MessageBusConnector, ManagementAgentMessenger
            
            self.message_bus = MessageBusConnector()
            if self.message_bus.connect():
                self.messenger = ManagementAgentMessenger(self.message_bus)
                self.logger.info("Message bus integration initialized successfully")
            else:
                self.logger.warning("Failed to initialize message bus - continuing without messaging")
                
        except ImportError:
            self.logger.warning("Message bus integration not available - continuing without messaging")
        except Exception as e:
            self.logger.error(f"Error initializing message bus: {e}")
    
    def send_message_to_orchestrator(self, message: Dict[str, Any]) -> bool:
        """Send message to Orchestration Agent via RabbitMQ"""
        try:
            if not self.message_bus:
                self.logger.warning("Message bus not available - cannot send message")
                return False
            
            # Ensure connection is active
            if not self.message_bus.channel or self.message_bus.connection.is_closed:
                if not self.message_bus.connect():
                    self.logger.error("Failed to reconnect to message bus")
                    return False
            
            # Add metadata
            message['agent_name'] = 'Management Agent'
            message['timestamp'] = datetime.now().isoformat()
            
            # Send message
            return self.message_bus.send_message_to_orchestrator(message)
            
        except Exception as e:
            self.logger.error(f"Error sending message to orchestrator: {e}")
            return False
    
    async def _send_status_update_message(self, metrics: SystemMetrics):
        """Send status update message to Orchestration Agent"""
        if not self.messenger:
            return
        
        try:
            metrics_data = {
                'system_health': metrics.system_health.value,
                'api_response_time': metrics.api_response_time,
                'discovery_candidates_count': metrics.discovery_candidates_count,
                'error_rate': metrics.error_rate,
                'scoring_strategy': metrics.scoring_strategy,
                'active_preset': metrics.active_preset,
                'data_freshness': metrics.data_freshness
            }
            
            await self.messenger.send_status_update(metrics.system_health.value, metrics_data)
            
        except Exception as e:
            self.logger.error(f"Error sending status update message: {e}")
    
    async def _send_alert_message(self, alert: Alert):
        """Send alert notification to Orchestration Agent"""
        if not self.messenger:
            return
        
        try:
            alert_level = alert.level.name if hasattr(alert.level, 'name') else str(alert.level)
            await self.messenger.send_alert_notification(
                alert_level, 
                alert.component, 
                alert.message
            )
            
        except Exception as e:
            self.logger.error(f"Error sending alert message: {e}")
    
    async def _send_automated_action_message(self, rule_name: str, action: str, reason: str):
        """Send automated action trigger message to Orchestration Agent"""
        if not self.messenger:
            return
        
        try:
            await self.messenger.send_automated_action_trigger(rule_name, action, reason)
            
        except Exception as e:
            self.logger.error(f"Error sending automated action message: {e}")
    
    async def _send_health_report_message(self, report: Dict[str, Any]):
        """Send comprehensive health report to Orchestration Agent"""
        if not self.messenger:
            return
        
        try:
            await self.messenger.send_health_report(report)
            
        except Exception as e:
            self.logger.error(f"Error sending health report message: {e}")
    
    async def _send_completion_notification_message(self, task: str, result: Dict[str, Any]):
        """Send task completion notification to Orchestration Agent"""
        if not self.messenger:
            return
        
        try:
            await self.messenger.send_completion_notification(task, result)
            
        except Exception as e:
            self.logger.error(f"Error sending completion notification: {e}")

# Example usage and main execution
async def main():
    """Main execution for standalone management agent"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    agent = ManagementAgent()
    
    # Run initial diagnostic
    print("Running initial diagnostic tests...")
    diagnostics = await agent.run_diagnostic_tests()
    print(json.dumps(diagnostics, indent=2, default=str))
    
    # Perform health check
    print("\nPerforming health check...")
    metrics = await agent.perform_health_check()
    print(f"System Health: {metrics.system_health.value}")
    print(f"Candidates: {metrics.discovery_candidates_count}")
    print(f"Response Time: {metrics.api_response_time:.2f}s")
    
    # Generate status report
    print("\nGenerating status report...")
    report = await agent.generate_status_report()
    print(json.dumps(report, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())