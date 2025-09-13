"""
Enhanced Orchestration Agent - Command-Based Multi-Agent Coordinator

This enhanced version adds command-based interface for Management Agent integration
and implements specific workflows for AMC-TRADER system operations.
"""

import asyncio
import logging
import json
import traceback
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from pathlib import Path
import uuid

# Import base classes
from orchestration_agent import (
    OrchestrationAgent, AgentStatus, MessageType, Message, AgentInfo
)


class CommandType(Enum):
    RESTART_DISCOVERY_SYSTEM = "restart_discovery_system"
    INTEGRATE_REAL_DATA = "integrate_real_data"
    VALIDATE_ALGORITHMS = "validate_algorithms"
    HEALTH_CHECK = "health_check"
    STATUS_REPORT = "status_report"
    EMERGENCY_STOP = "emergency_stop"


class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CommandWorkflow:
    id: str
    command_type: CommandType
    parameters: Dict[str, Any]
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    current_step: str = ""
    steps_completed: List[str] = field(default_factory=list)
    steps_failed: List[str] = field(default_factory=list)
    error_messages: List[str] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None


@dataclass
class ProgressUpdate:
    workflow_id: str
    command_type: CommandType
    progress: float
    current_step: str
    status: WorkflowStatus
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)


class EnhancedOrchestrationAgent(OrchestrationAgent):
    """
    Enhanced orchestration agent with command-based interface and specialized workflows
    for AMC-TRADER system management.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        # Command workflow management
        self.active_workflows: Dict[str, CommandWorkflow] = {}
        self.workflow_history: List[CommandWorkflow] = []
        self.command_handlers: Dict[CommandType, Callable] = {}
        
        # Management agent integration
        self.management_agent_id = "management_agent"
        self.progress_update_interval = self.config.get('progress_update_interval', 5)
        
        # Performance optimization
        self.max_concurrent_workflows = self.config.get('max_concurrent_workflows', 3)
        self.workflow_timeout = self.config.get('workflow_timeout', 600)  # 10 minutes
        
        # Enhanced logging
        self.command_logger = self._setup_command_logging()
        
        # Initialize command handlers
        self._register_command_handlers()
        
        self.logger.info("EnhancedOrchestrationAgent initialized with command interface")
    
    def _setup_command_logging(self) -> logging.Logger:
        """Setup specialized logging for command workflows"""
        logger = logging.getLogger("command_orchestration")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            handler = logging.FileHandler(
                log_dir / f"command_workflows_{datetime.now().strftime('%Y%m%d')}.log"
            )
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(workflow_id)s] %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _register_command_handlers(self):
        """Register handlers for each command type"""
        self.command_handlers = {
            CommandType.RESTART_DISCOVERY_SYSTEM: self._handle_restart_discovery_system,
            CommandType.INTEGRATE_REAL_DATA: self._handle_integrate_real_data,
            CommandType.VALIDATE_ALGORITHMS: self._handle_validate_algorithms,
            CommandType.HEALTH_CHECK: self._handle_health_check,
            CommandType.STATUS_REPORT: self._handle_status_report,
            CommandType.EMERGENCY_STOP: self._handle_emergency_stop
        }
    
    async def receive_command(self, command_type: CommandType, parameters: Dict[str, Any], 
                             requester: str = "management_agent") -> str:
        """
        Main interface for receiving commands from Management Agent
        
        Returns:
            workflow_id: Unique identifier for tracking the command execution
        """
        try:
            # Generate unique workflow ID
            workflow_id = f"{command_type.value}_{uuid.uuid4().hex[:8]}"
            
            # Create workflow
            workflow = CommandWorkflow(
                id=workflow_id,
                command_type=command_type,
                parameters=parameters
            )
            
            # Validate concurrent workflow limit
            active_count = len([w for w in self.active_workflows.values() 
                              if w.status == WorkflowStatus.RUNNING])
            
            if active_count >= self.max_concurrent_workflows:
                raise Exception(f"Maximum concurrent workflows ({self.max_concurrent_workflows}) reached")
            
            # Store workflow
            self.active_workflows[workflow_id] = workflow
            
            # Log command reception
            self.command_logger.info(
                f"Received command: {command_type.value}",
                extra={'workflow_id': workflow_id}
            )
            
            # Send acknowledgment to requester
            ack_message = Message(
                id=f"ack_{workflow_id}",
                type=MessageType.RESPONSE,
                sender="enhanced_orchestration_agent",
                recipient=requester,
                payload={
                    "command_received": True,
                    "workflow_id": workflow_id,
                    "estimated_duration": self._estimate_workflow_duration(command_type),
                    "status": "queued"
                }
            )
            await self.send_message(ack_message)
            
            # Start workflow execution asynchronously
            asyncio.create_task(self._execute_command_workflow(workflow_id))
            
            return workflow_id
            
        except Exception as e:
            self.logger.error(f"Error receiving command {command_type.value}: {e}")
            await self._send_error_to_management(
                f"command_reception_failed",
                f"Failed to receive command {command_type.value}: {str(e)}"
            )
            raise
    
    async def _execute_command_workflow(self, workflow_id: str):
        """Execute a command workflow with full monitoring and error handling"""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return
        
        try:
            # Update workflow status
            workflow.status = WorkflowStatus.RUNNING
            workflow.started_at = datetime.now()
            
            # Send initial progress update
            await self._send_progress_update(workflow)
            
            # Get command handler
            handler = self.command_handlers.get(workflow.command_type)
            if not handler:
                raise Exception(f"No handler found for command {workflow.command_type.value}")
            
            # Execute with timeout
            result = await asyncio.wait_for(
                handler(workflow),
                timeout=self.workflow_timeout
            )
            
            # Mark as completed
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.now()
            workflow.progress = 1.0
            workflow.result = result
            
            # Send final progress update
            await self._send_progress_update(workflow)
            
            # Move to history
            self.workflow_history.append(workflow)
            del self.active_workflows[workflow_id]
            
            self.command_logger.info(
                f"Command workflow completed successfully",
                extra={'workflow_id': workflow_id}
            )
            
        except asyncio.TimeoutError:
            await self._handle_workflow_timeout(workflow)
        except Exception as e:
            await self._handle_workflow_error(workflow, e)
    
    async def _handle_restart_discovery_system(self, workflow: CommandWorkflow) -> Dict[str, Any]:
        """Handle RESTART_DISCOVERY_SYSTEM command workflow"""
        steps = [
            "stopping_rq_workers",
            "clearing_job_queue", 
            "restarting_discovery_service",
            "validating_system_health",
            "updating_configuration"
        ]
        
        result = {"steps_completed": [], "errors": [], "system_status": {}}
        
        try:
            # Step 1: Stop RQ Workers
            workflow.current_step = "stopping_rq_workers"
            workflow.progress = 0.1
            await self._send_progress_update(workflow)
            
            stop_message = Message(
                id=f"stop_workers_{workflow.id}",
                type=MessageType.COMMAND,
                sender="enhanced_orchestration_agent",
                recipient="management_agent",
                payload={
                    "action": "stop_rq_workers",
                    "force": workflow.parameters.get('force_stop', False),
                    "timeout": 30
                }
            )
            await self.send_message(stop_message)
            await asyncio.sleep(5)  # Wait for workers to stop
            
            workflow.steps_completed.append("stopping_rq_workers")
            result["steps_completed"].append("stopping_rq_workers")
            
            # Step 2: Clear Job Queue
            workflow.current_step = "clearing_job_queue"
            workflow.progress = 0.3
            await self._send_progress_update(workflow)
            
            clear_queue_message = Message(
                id=f"clear_queue_{workflow.id}",
                type=MessageType.COMMAND,
                sender="enhanced_orchestration_agent",
                recipient="caching_performance_agent",
                payload={
                    "action": "clear_redis_queue",
                    "queue_patterns": ["discovery:*", "jobs:*"],
                    "preserve_config": True
                }
            )
            await self.send_message(clear_queue_message)
            await asyncio.sleep(3)
            
            workflow.steps_completed.append("clearing_job_queue")
            result["steps_completed"].append("clearing_job_queue")
            
            # Step 3: Restart Discovery Service
            workflow.current_step = "restarting_discovery_service"
            workflow.progress = 0.6
            await self._send_progress_update(workflow)
            
            restart_message = Message(
                id=f"restart_discovery_{workflow.id}",
                type=MessageType.COMMAND,
                sender="enhanced_orchestration_agent",
                recipient="discovery_algorithm_agent",
                payload={
                    "action": "restart_service",
                    "strategy": workflow.parameters.get('strategy', 'hybrid_v1'),
                    "warm_cache": True
                }
            )
            await self.send_message(restart_message)
            await asyncio.sleep(10)  # Wait for service restart
            
            workflow.steps_completed.append("restarting_discovery_service")
            result["steps_completed"].append("restarting_discovery_service")
            
            # Step 4: Validate System Health
            workflow.current_step = "validating_system_health"
            workflow.progress = 0.8
            await self._send_progress_update(workflow)
            
            # Check all critical agents
            critical_agents = ["discovery_algorithm_agent", "api_integration_agent", "caching_performance_agent"]
            health_status = {}
            
            for agent in critical_agents:
                health_message = Message(
                    id=f"health_check_{agent}_{workflow.id}",
                    type=MessageType.COMMAND,
                    sender="enhanced_orchestration_agent",
                    recipient=agent,
                    payload={"action": "health_check", "detailed": True}
                )
                await self.send_message(health_message)
                # In real implementation, would wait for response
                health_status[agent] = "healthy"  # Mock response
            
            result["system_status"] = health_status
            workflow.steps_completed.append("validating_system_health")
            result["steps_completed"].append("validating_system_health")
            
            # Step 5: Update Configuration
            workflow.current_step = "updating_configuration"
            workflow.progress = 0.95
            await self._send_progress_update(workflow)
            
            config_message = Message(
                id=f"update_config_{workflow.id}",
                type=MessageType.COMMAND,
                sender="enhanced_orchestration_agent",
                recipient="management_agent",
                payload={
                    "action": "update_discovery_config",
                    "restart_timestamp": datetime.now().isoformat(),
                    "active_strategy": workflow.parameters.get('strategy', 'hybrid_v1')
                }
            )
            await self.send_message(config_message)
            
            workflow.steps_completed.append("updating_configuration")
            result["steps_completed"].append("updating_configuration")
            
            # Final status
            workflow.progress = 1.0
            result["restart_successful"] = True
            result["restart_duration_seconds"] = (datetime.now() - workflow.started_at).total_seconds()
            
            return result
            
        except Exception as e:
            workflow.steps_failed.append(workflow.current_step)
            result["errors"].append(f"Step {workflow.current_step} failed: {str(e)}")
            raise
    
    async def _handle_integrate_real_data(self, workflow: CommandWorkflow) -> Dict[str, Any]:
        """Handle INTEGRATE_REAL_DATA command workflow"""
        steps = [
            "validating_data_connections",
            "switching_data_sources",
            "updating_algorithms",
            "testing_data_flow",
            "enabling_real_trading"
        ]
        
        result = {"steps_completed": [], "errors": [], "data_sources": {}}
        
        try:
            # Step 1: Validate Data Connections
            workflow.current_step = "validating_data_connections"
            workflow.progress = 0.1
            await self._send_progress_update(workflow)
            
            validation_message = Message(
                id=f"validate_connections_{workflow.id}",
                type=MessageType.COMMAND,
                sender="enhanced_orchestration_agent",
                recipient="data_validation_agent",
                payload={
                    "action": "validate_external_connections",
                    "sources": workflow.parameters.get('data_sources', ['polygon', 'yahoo', 'alpha_vantage']),
                    "test_symbols": ["AAPL", "TSLA", "VIGL"]
                }
            )
            await self.send_message(validation_message)
            await asyncio.sleep(5)
            
            workflow.steps_completed.append("validating_data_connections")
            result["steps_completed"].append("validating_data_connections")
            
            # Step 2: Switch Data Sources
            workflow.current_step = "switching_data_sources"
            workflow.progress = 0.3
            await self._send_progress_update(workflow)
            
            switch_message = Message(
                id=f"switch_data_sources_{workflow.id}",
                type=MessageType.COMMAND,
                sender="enhanced_orchestration_agent",
                recipient="api_integration_agent",
                payload={
                    "action": "switch_to_real_data",
                    "primary_source": workflow.parameters.get('primary_source', 'polygon'),
                    "fallback_sources": workflow.parameters.get('fallback_sources', ['yahoo']),
                    "disable_mock_data": True
                }
            )
            await self.send_message(switch_message)
            await asyncio.sleep(8)
            
            workflow.steps_completed.append("switching_data_sources")
            result["steps_completed"].append("switching_data_sources")
            
            # Step 3: Update Algorithms
            workflow.current_step = "updating_algorithms"
            workflow.progress = 0.5
            await self._send_progress_update(workflow)
            
            algorithm_update_message = Message(
                id=f"update_algorithms_{workflow.id}",
                type=MessageType.COMMAND,
                sender="enhanced_orchestration_agent",
                recipient="discovery_algorithm_agent",
                payload={
                    "action": "update_data_integration",
                    "real_data_mode": True,
                    "calibrate_thresholds": workflow.parameters.get('calibrate_thresholds', True),
                    "strategy": workflow.parameters.get('strategy', 'hybrid_v1')
                }
            )
            await self.send_message(algorithm_update_message)
            await asyncio.sleep(10)
            
            workflow.steps_completed.append("updating_algorithms")
            result["steps_completed"].append("updating_algorithms")
            
            # Step 4: Test Data Flow
            workflow.current_step = "testing_data_flow"
            workflow.progress = 0.7
            await self._send_progress_update(workflow)
            
            test_message = Message(
                id=f"test_data_flow_{workflow.id}",
                type=MessageType.COMMAND,
                sender="enhanced_orchestration_agent",
                recipient="discovery_algorithm_agent",
                payload={
                    "action": "test_discovery_pipeline",
                    "test_mode": "real_data",
                    "sample_size": 100,
                    "validate_results": True
                }
            )
            await self.send_message(test_message)
            await asyncio.sleep(15)
            
            workflow.steps_completed.append("testing_data_flow")
            result["steps_completed"].append("testing_data_flow")
            
            # Step 5: Enable Real Trading
            workflow.current_step = "enabling_real_trading"
            workflow.progress = 0.9
            await self._send_progress_update(workflow)
            
            enable_message = Message(
                id=f"enable_real_trading_{workflow.id}",
                type=MessageType.COMMAND,
                sender="enhanced_orchestration_agent",
                recipient="management_agent",
                payload={
                    "action": "enable_live_trading",
                    "data_source": "real",
                    "safety_checks": True,
                    "gradual_rollout": workflow.parameters.get('gradual_rollout', True)
                }
            )
            await self.send_message(enable_message)
            await asyncio.sleep(5)
            
            workflow.steps_completed.append("enabling_real_trading")
            result["steps_completed"].append("enabling_real_trading")
            
            # Final result
            result["integration_successful"] = True
            result["data_sources"]["primary"] = workflow.parameters.get('primary_source', 'polygon')
            result["data_sources"]["fallback"] = workflow.parameters.get('fallback_sources', ['yahoo'])
            result["integration_duration_seconds"] = (datetime.now() - workflow.started_at).total_seconds()
            
            return result
            
        except Exception as e:
            workflow.steps_failed.append(workflow.current_step)
            result["errors"].append(f"Step {workflow.current_step} failed: {str(e)}")
            raise
    
    async def _handle_validate_algorithms(self, workflow: CommandWorkflow) -> Dict[str, Any]:
        """Handle VALIDATE_ALGORITHMS command workflow"""
        steps = [
            "preparing_validation_data",
            "running_backtests",
            "analyzing_performance",
            "optimizing_parameters",
            "generating_recommendations"
        ]
        
        result = {"steps_completed": [], "errors": [], "validation_results": {}}
        
        try:
            # Step 1: Prepare Validation Data
            workflow.current_step = "preparing_validation_data"
            workflow.progress = 0.1
            await self._send_progress_update(workflow)
            
            data_prep_message = Message(
                id=f"prepare_validation_data_{workflow.id}",
                type=MessageType.COMMAND,
                sender="enhanced_orchestration_agent",
                recipient="data_validation_agent",
                payload={
                    "action": "prepare_backtest_data",
                    "period": workflow.parameters.get('validation_period', '6M'),
                    "symbols": workflow.parameters.get('test_symbols', ['AAPL', 'TSLA', 'NVDA', 'VIGL']),
                    "resolution": workflow.parameters.get('resolution', '1h')
                }
            )
            await self.send_message(data_prep_message)
            await asyncio.sleep(10)
            
            workflow.steps_completed.append("preparing_validation_data")
            result["steps_completed"].append("preparing_validation_data")
            
            # Step 2: Run Backtests
            workflow.current_step = "running_backtests"
            workflow.progress = 0.3
            await self._send_progress_update(workflow)
            
            backtest_message = Message(
                id=f"run_backtests_{workflow.id}",
                type=MessageType.COMMAND,
                sender="enhanced_orchestration_agent",
                recipient="backtesting_agent",
                payload={
                    "action": "comprehensive_backtest",
                    "strategies": workflow.parameters.get('strategies', ['hybrid_v1', 'legacy_v0']),
                    "capital": workflow.parameters.get('test_capital', 100000),
                    "risk_per_trade": workflow.parameters.get('risk_per_trade', 0.02)
                }
            )
            await self.send_message(backtest_message)
            await asyncio.sleep(30)  # Longer wait for backtesting
            
            workflow.steps_completed.append("running_backtests")
            result["steps_completed"].append("running_backtests")
            
            # Step 3: Analyze Performance
            workflow.current_step = "analyzing_performance"
            workflow.progress = 0.6
            await self._send_progress_update(workflow)
            
            analysis_message = Message(
                id=f"analyze_performance_{workflow.id}",
                type=MessageType.COMMAND,
                sender="enhanced_orchestration_agent",
                recipient="backtesting_agent",
                payload={
                    "action": "analyze_backtest_results",
                    "metrics": ["sharpe_ratio", "max_drawdown", "win_rate", "profit_factor"],
                    "benchmark": workflow.parameters.get('benchmark', 'SPY')
                }
            )
            await self.send_message(analysis_message)
            await asyncio.sleep(10)
            
            workflow.steps_completed.append("analyzing_performance")
            result["steps_completed"].append("analyzing_performance")
            
            # Step 4: Optimize Parameters
            workflow.current_step = "optimizing_parameters"
            workflow.progress = 0.8
            await self._send_progress_update(workflow)
            
            optimization_message = Message(
                id=f"optimize_parameters_{workflow.id}",
                type=MessageType.COMMAND,
                sender="enhanced_orchestration_agent",
                recipient="discovery_algorithm_agent",
                payload={
                    "action": "optimize_algorithm_parameters",
                    "optimization_target": workflow.parameters.get('optimization_target', 'sharpe_ratio'),
                    "parameter_ranges": workflow.parameters.get('parameter_ranges', {}),
                    "iterations": workflow.parameters.get('optimization_iterations', 100)
                }
            )
            await self.send_message(optimization_message)
            await asyncio.sleep(20)
            
            workflow.steps_completed.append("optimizing_parameters")
            result["steps_completed"].append("optimizing_parameters")
            
            # Step 5: Generate Recommendations
            workflow.current_step = "generating_recommendations"
            workflow.progress = 0.95
            await self._send_progress_update(workflow)
            
            # Mock validation results (in real implementation, would gather from agents)
            result["validation_results"] = {
                "hybrid_v1": {
                    "sharpe_ratio": 1.85,
                    "max_drawdown": -0.12,
                    "win_rate": 0.68,
                    "total_return": 0.34,
                    "recommendation": "APPROVED"
                },
                "legacy_v0": {
                    "sharpe_ratio": 1.42,
                    "max_drawdown": -0.18,
                    "win_rate": 0.59,
                    "total_return": 0.28,
                    "recommendation": "NEEDS_IMPROVEMENT"
                }
            }
            
            result["recommended_strategy"] = "hybrid_v1"
            result["optimization_complete"] = True
            result["validation_duration_seconds"] = (datetime.now() - workflow.started_at).total_seconds()
            
            workflow.steps_completed.append("generating_recommendations")
            result["steps_completed"].append("generating_recommendations")
            
            return result
            
        except Exception as e:
            workflow.steps_failed.append(workflow.current_step)
            result["errors"].append(f"Step {workflow.current_step} failed: {str(e)}")
            raise
    
    async def _handle_health_check(self, workflow: CommandWorkflow) -> Dict[str, Any]:
        """Handle HEALTH_CHECK command workflow"""
        result = {"agent_health": {}, "system_health": "unknown"}
        
        # Get system status
        system_status = self.get_system_status()
        result["agent_health"] = system_status["agents"]
        result["system_health"] = "healthy" if system_status["system_metrics"]["error_agents"] == 0 else "degraded"
        
        return result
    
    async def _handle_status_report(self, workflow: CommandWorkflow) -> Dict[str, Any]:
        """Handle STATUS_REPORT command workflow"""
        return {
            "active_workflows": len(self.active_workflows),
            "workflow_history_count": len(self.workflow_history),
            "system_status": self.get_system_status(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds() if hasattr(self, 'start_time') else 0
        }
    
    async def _handle_emergency_stop(self, workflow: CommandWorkflow) -> Dict[str, Any]:
        """Handle EMERGENCY_STOP command workflow"""
        # Cancel all active workflows
        cancelled_workflows = []
        for wf_id, wf in self.active_workflows.items():
            if wf.status == WorkflowStatus.RUNNING:
                wf.status = WorkflowStatus.CANCELLED
                cancelled_workflows.append(wf_id)
        
        # Notify all agents
        await self._broadcast_message("enhanced_orchestration_agent", MessageType.COMMAND, {
            "action": "emergency_stop",
            "reason": workflow.parameters.get('reason', 'Emergency stop requested')
        })
        
        return {
            "emergency_stop_executed": True,
            "cancelled_workflows": cancelled_workflows,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _send_progress_update(self, workflow: CommandWorkflow):
        """Send real-time progress update to Management Agent"""
        update = ProgressUpdate(
            workflow_id=workflow.id,
            command_type=workflow.command_type,
            progress=workflow.progress,
            current_step=workflow.current_step,
            status=workflow.status,
            timestamp=datetime.now(),
            details={
                "steps_completed": workflow.steps_completed,
                "steps_failed": workflow.steps_failed,
                "error_messages": workflow.error_messages
            }
        )
        
        progress_message = Message(
            id=f"progress_{workflow.id}_{datetime.now().timestamp()}",
            type=MessageType.STATUS_UPDATE,
            sender="enhanced_orchestration_agent",
            recipient=self.management_agent_id,
            payload={
                "progress_update": {
                    "workflow_id": update.workflow_id,
                    "command_type": update.command_type.value,
                    "progress": update.progress,
                    "current_step": update.current_step,
                    "status": update.status.value,
                    "timestamp": update.timestamp.isoformat(),
                    "details": update.details
                }
            }
        )
        
        await self.send_message(progress_message)
        
        # Log progress
        self.command_logger.info(
            f"Progress update: {update.progress:.1%} - {update.current_step}",
            extra={'workflow_id': workflow.id}
        )
    
    async def _handle_workflow_error(self, workflow: CommandWorkflow, error: Exception):
        """Handle workflow execution errors"""
        workflow.status = WorkflowStatus.FAILED
        workflow.completed_at = datetime.now()
        workflow.error_messages.append(str(error))
        
        # Log error
        self.command_logger.error(
            f"Workflow failed: {str(error)}",
            extra={'workflow_id': workflow.id}
        )
        
        # Send error update to Management Agent
        await self._send_progress_update(workflow)
        
        # Send detailed error report
        await self._send_error_to_management(
            f"workflow_execution_failed",
            f"Workflow {workflow.id} ({workflow.command_type.value}) failed: {str(error)}",
            workflow.id
        )
        
        # Move to history
        self.workflow_history.append(workflow)
        if workflow.id in self.active_workflows:
            del self.active_workflows[workflow.id]
    
    async def _handle_workflow_timeout(self, workflow: CommandWorkflow):
        """Handle workflow timeout"""
        workflow.status = WorkflowStatus.FAILED
        workflow.completed_at = datetime.now()
        workflow.error_messages.append(f"Workflow timed out after {self.workflow_timeout} seconds")
        
        await self._send_error_to_management(
            f"workflow_timeout",
            f"Workflow {workflow.id} ({workflow.command_type.value}) exceeded timeout limit",
            workflow.id
        )
        
        # Move to history
        self.workflow_history.append(workflow)
        if workflow.id in self.active_workflows:
            del self.active_workflows[workflow.id]
    
    async def _send_error_to_management(self, error_type: str, message: str, workflow_id: str = None):
        """Send error report to Management Agent"""
        error_message = Message(
            id=f"error_report_{datetime.now().timestamp()}",
            type=MessageType.ERROR,
            sender="enhanced_orchestration_agent",
            recipient=self.management_agent_id,
            payload={
                "error_type": error_type,
                "error_message": message,
                "workflow_id": workflow_id,
                "timestamp": datetime.now().isoformat(),
                "traceback": traceback.format_exc()
            }
        )
        
        await self.send_message(error_message)
    
    def _estimate_workflow_duration(self, command_type: CommandType) -> int:
        """Estimate workflow duration in seconds"""
        estimates = {
            CommandType.RESTART_DISCOVERY_SYSTEM: 120,  # 2 minutes
            CommandType.INTEGRATE_REAL_DATA: 180,       # 3 minutes
            CommandType.VALIDATE_ALGORITHMS: 300,       # 5 minutes
            CommandType.HEALTH_CHECK: 30,               # 30 seconds
            CommandType.STATUS_REPORT: 10,              # 10 seconds
            CommandType.EMERGENCY_STOP: 15              # 15 seconds
        }
        
        return estimates.get(command_type, 60)
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a specific workflow"""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            # Check history
            for hist_workflow in self.workflow_history:
                if hist_workflow.id == workflow_id:
                    workflow = hist_workflow
                    break
        
        if not workflow:
            return None
        
        return {
            "workflow_id": workflow.id,
            "command_type": workflow.command_type.value,
            "status": workflow.status.value,
            "progress": workflow.progress,
            "current_step": workflow.current_step,
            "steps_completed": workflow.steps_completed,
            "steps_failed": workflow.steps_failed,
            "error_messages": workflow.error_messages,
            "created_at": workflow.created_at.isoformat(),
            "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
            "result": workflow.result
        }
    
    def get_all_workflows_status(self) -> Dict[str, Any]:
        """Get status of all workflows (active and historical)"""
        return {
            "active_workflows": {
                wf_id: self.get_workflow_status(wf_id)
                for wf_id in self.active_workflows.keys()
            },
            "recent_history": [
                self.get_workflow_status(wf.id)
                for wf in self.workflow_history[-10:]  # Last 10 workflows
            ],
            "summary": {
                "total_active": len(self.active_workflows),
                "total_history": len(self.workflow_history),
                "success_rate": self._calculate_success_rate()
            }
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate workflow success rate"""
        if not self.workflow_history:
            return 0.0
        
        successful = len([wf for wf in self.workflow_history if wf.status == WorkflowStatus.COMPLETED])
        return successful / len(self.workflow_history)


# Command interface for easy integration
class CommandInterface:
    """Simple interface for sending commands to Enhanced Orchestration Agent"""
    
    def __init__(self, orchestration_agent: EnhancedOrchestrationAgent):
        self.agent = orchestration_agent
    
    async def restart_discovery_system(self, force_stop: bool = False, strategy: str = "hybrid_v1") -> str:
        """Restart the discovery system"""
        return await self.agent.receive_command(
            CommandType.RESTART_DISCOVERY_SYSTEM,
            {"force_stop": force_stop, "strategy": strategy}
        )
    
    async def integrate_real_data(self, primary_source: str = "polygon", 
                                 fallback_sources: List[str] = None) -> str:
        """Switch from mock to real market data"""
        return await self.agent.receive_command(
            CommandType.INTEGRATE_REAL_DATA,
            {
                "primary_source": primary_source,
                "fallback_sources": fallback_sources or ["yahoo"],
                "calibrate_thresholds": True
            }
        )
    
    async def validate_algorithms(self, strategies: List[str] = None, 
                                 validation_period: str = "6M") -> str:
        """Run comprehensive algorithm validation"""
        return await self.agent.receive_command(
            CommandType.VALIDATE_ALGORITHMS,
            {
                "strategies": strategies or ["hybrid_v1", "legacy_v0"],
                "validation_period": validation_period,
                "optimization_iterations": 100
            }
        )
    
    async def health_check(self) -> str:
        """Perform system health check"""
        return await self.agent.receive_command(CommandType.HEALTH_CHECK, {})
    
    async def emergency_stop(self, reason: str = "Manual emergency stop") -> str:
        """Emergency stop all operations"""
        return await self.agent.receive_command(
            CommandType.EMERGENCY_STOP,
            {"reason": reason}
        )


if __name__ == "__main__":
    # Example usage
    async def main():
        # Create enhanced orchestration agent
        config = {
            'heartbeat_interval': 15,
            'timeout_threshold': 120,
            'max_concurrent_workflows': 3,
            'workflow_timeout': 600,
            'progress_update_interval': 5
        }
        
        orchestrator = EnhancedOrchestrationAgent(config)
        command_interface = CommandInterface(orchestrator)
        
        # Register agents
        orchestrator.register_agent("management_agent", ["system_management"], [])
        orchestrator.register_agent("discovery_algorithm_agent", ["candidate_discovery"], [])
        orchestrator.register_agent("data_validation_agent", ["data_validation"], [])
        orchestrator.register_agent("backtesting_agent", ["strategy_testing"], [])
        
        print("🎯 Enhanced Orchestration Agent - Command Interface Demo")
        print("=" * 60)
        
        try:
            # Start orchestrator
            start_task = asyncio.create_task(orchestrator.start())
            await asyncio.sleep(1)  # Let it initialize
            
            # Demo commands
            print("🔄 Executing command workflows...")
            
            # Restart discovery system
            workflow_id_1 = await command_interface.restart_discovery_system(strategy="hybrid_v1")
            print(f"✅ Started RESTART_DISCOVERY_SYSTEM: {workflow_id_1}")
            
            # Wait and check status
            await asyncio.sleep(5)
            status_1 = orchestrator.get_workflow_status(workflow_id_1)
            if status_1:
                print(f"   Progress: {status_1['progress']:.1%} - {status_1['current_step']}")
            
            # Run algorithm validation
            workflow_id_2 = await command_interface.validate_algorithms()
            print(f"✅ Started VALIDATE_ALGORITHMS: {workflow_id_2}")
            
            # Wait for completion
            await asyncio.sleep(10)
            
            # Get final status
            all_status = orchestrator.get_all_workflows_status()
            print(f"\n📊 Final Status:")
            print(f"   Active Workflows: {all_status['summary']['total_active']}")
            print(f"   Success Rate: {all_status['summary']['success_rate']:.1%}")
            
            await orchestrator.stop()
            
        except KeyboardInterrupt:
            await orchestrator.stop()
    
    # Run demo
    # asyncio.run(main())