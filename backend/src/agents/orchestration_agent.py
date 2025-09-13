"""
Orchestration Agent - Multi-Agent System Coordinator

This agent is responsible for coordinating the communication and workflow between all other agents
in the AMC-TRADER system. It provides centralized orchestration, monitoring, and fault tolerance.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import threading
from concurrent.futures import ThreadPoolExecutor, Future
import traceback
from pathlib import Path


class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    TIMEOUT = "timeout"
    DISABLED = "disabled"


class MessageType(Enum):
    COMMAND = "command"
    RESPONSE = "response"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    STATUS_UPDATE = "status_update"
    DATA = "data"


@dataclass
class Message:
    id: str
    type: MessageType
    sender: str
    recipient: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    priority: int = 1  # Higher number = higher priority


@dataclass
class AgentInfo:
    name: str
    status: AgentStatus = AgentStatus.IDLE
    last_heartbeat: datetime = field(default_factory=datetime.now)
    dependencies: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    error_count: int = 0
    last_error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


class OrchestrationAgent:
    """
    Central orchestration agent that coordinates communication and workflow between all other agents.
    
    Key responsibilities:
    1. Agent registry and lifecycle management
    2. Message routing and communication protocols
    3. Workflow orchestration and dependency management
    4. Health monitoring and fault tolerance
    5. Resource optimization and load balancing
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Agent management
        self.agents: Dict[str, AgentInfo] = {}
        self.agent_handlers: Dict[str, Callable] = {}
        
        # Message handling
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.message_handlers: Dict[MessageType, List[Callable]] = {
            msg_type: [] for msg_type in MessageType
        }
        
        # Workflow management
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        
        # System state
        self.is_running = False
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.heartbeat_interval = self.config.get('heartbeat_interval', 30)
        self.timeout_threshold = self.config.get('timeout_threshold', 300)
        
        # Error handling
        self.max_retries = self.config.get('max_retries', 3)
        self.error_threshold = self.config.get('error_threshold', 5)
        
        self.logger.info("OrchestrationAgent initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup structured logging for the orchestration agent"""
        logger = logging.getLogger(f"orchestration_agent")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    async def start(self):
        """Start the orchestration agent and all background processes"""
        if self.is_running:
            self.logger.warning("OrchestrationAgent already running")
            return
        
        self.is_running = True
        self.logger.info("Starting OrchestrationAgent...")
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._message_processor()),
            asyncio.create_task(self._health_monitor()),
            asyncio.create_task(self._workflow_manager())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            self.logger.error(f"Error in OrchestrationAgent main loop: {e}")
            await self.stop()
    
    async def stop(self):
        """Gracefully stop the orchestration agent"""
        self.logger.info("Stopping OrchestrationAgent...")
        self.is_running = False
        
        # Notify all agents
        await self._broadcast_message("system", MessageType.COMMAND, {"action": "shutdown"})
        
        # Clean up resources
        self.executor.shutdown(wait=True)
        self.logger.info("OrchestrationAgent stopped")
    
    def register_agent(self, agent_name: str, capabilities: List[str], 
                      dependencies: List[str] = None, handler: Callable = None):
        """Register a new agent with the orchestration system"""
        agent_info = AgentInfo(
            name=agent_name,
            capabilities=capabilities,
            dependencies=dependencies or []
        )
        
        self.agents[agent_name] = agent_info
        
        if handler:
            self.agent_handlers[agent_name] = handler
        
        self.logger.info(f"Registered agent: {agent_name} with capabilities: {capabilities}")
    
    def unregister_agent(self, agent_name: str):
        """Unregister an agent from the orchestration system"""
        if agent_name in self.agents:
            del self.agents[agent_name]
        
        if agent_name in self.agent_handlers:
            del self.agent_handlers[agent_name]
        
        self.logger.info(f"Unregistered agent: {agent_name}")
    
    async def send_message(self, message: Message) -> bool:
        """Send a message through the orchestration system"""
        try:
            await self.message_queue.put(message)
            self.logger.debug(f"Message queued: {message.sender} -> {message.recipient}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to queue message: {e}")
            return False
    
    async def _message_processor(self):
        """Process messages from the message queue"""
        while self.is_running:
            try:
                # Get message with timeout
                message = await asyncio.wait_for(
                    self.message_queue.get(), timeout=1.0
                )
                
                await self._route_message(message)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")
    
    async def _route_message(self, message: Message):
        """Route message to appropriate handler"""
        try:
            # Update sender status if heartbeat
            if message.type == MessageType.HEARTBEAT:
                await self._handle_heartbeat(message)
                return
            
            # Route to specific agent
            if message.recipient in self.agent_handlers:
                handler = self.agent_handlers[message.recipient]
                await self._execute_handler(handler, message)
            
            # Execute message type handlers
            for handler in self.message_handlers.get(message.type, []):
                await self._execute_handler(handler, message)
                
        except Exception as e:
            self.logger.error(f"Error routing message {message.id}: {e}")
            await self._handle_message_error(message, str(e))
    
    async def _execute_handler(self, handler: Callable, message: Message):
        """Execute a message handler with error handling"""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(message)
            else:
                # Execute in thread pool for sync handlers
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(self.executor, handler, message)
                
        except Exception as e:
            self.logger.error(f"Handler error for message {message.id}: {e}")
            raise
    
    async def _handle_heartbeat(self, message: Message):
        """Handle agent heartbeat messages"""
        agent_name = message.sender
        if agent_name in self.agents:
            self.agents[agent_name].last_heartbeat = datetime.now()
            self.agents[agent_name].status = AgentStatus.RUNNING
            
            # Update metrics if provided
            if 'metrics' in message.payload:
                self.agents[agent_name].metrics.update(message.payload['metrics'])
    
    async def _health_monitor(self):
        """Monitor agent health and handle timeouts"""
        while self.is_running:
            try:
                now = datetime.now()
                timeout_threshold = timedelta(seconds=self.timeout_threshold)
                
                for agent_name, agent_info in self.agents.items():
                    # Check for timeout
                    if now - agent_info.last_heartbeat > timeout_threshold:
                        if agent_info.status != AgentStatus.TIMEOUT:
                            self.logger.warning(f"Agent {agent_name} timed out")
                            agent_info.status = AgentStatus.TIMEOUT
                            await self._handle_agent_timeout(agent_name)
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                self.logger.error(f"Error in health monitor: {e}")
                await asyncio.sleep(5)
    
    async def _workflow_manager(self):
        """Manage workflow execution and dependencies"""
        while self.is_running:
            try:
                # Process active workflows
                completed_workflows = []
                
                for workflow_id, workflow_state in self.active_workflows.items():
                    if await self._process_workflow(workflow_id, workflow_state):
                        completed_workflows.append(workflow_id)
                
                # Clean up completed workflows
                for workflow_id in completed_workflows:
                    del self.active_workflows[workflow_id]
                    self.logger.info(f"Workflow {workflow_id} completed")
                
                await asyncio.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Error in workflow manager: {e}")
                await asyncio.sleep(5)
    
    async def _process_workflow(self, workflow_id: str, workflow_state: Dict[str, Any]) -> bool:
        """Process a single workflow and return True if completed"""
        try:
            workflow_def = workflow_state['definition']
            current_step = workflow_state.get('current_step', 0)
            steps = workflow_def.get('steps', [])
            
            if current_step >= len(steps):
                return True  # Workflow completed
            
            step = steps[current_step]
            
            # Check dependencies
            if await self._check_step_dependencies(step):
                # Execute step
                success = await self._execute_workflow_step(workflow_id, step)
                
                if success:
                    workflow_state['current_step'] = current_step + 1
                    workflow_state['completed_steps'].append(step['name'])
                else:
                    # Handle step failure
                    await self._handle_workflow_step_error(workflow_id, step)
            
            return False  # Workflow not completed yet
            
        except Exception as e:
            self.logger.error(f"Error processing workflow {workflow_id}: {e}")
            return True  # Mark as completed to clean up
    
    async def _check_step_dependencies(self, step: Dict[str, Any]) -> bool:
        """Check if all dependencies for a workflow step are satisfied"""
        dependencies = step.get('dependencies', [])
        
        for dep in dependencies:
            if isinstance(dep, str):
                # Agent dependency
                if dep not in self.agents or self.agents[dep].status != AgentStatus.RUNNING:
                    return False
            elif isinstance(dep, dict):
                # Complex dependency condition
                if not await self._evaluate_dependency_condition(dep):
                    return False
        
        return True
    
    async def _execute_workflow_step(self, workflow_id: str, step: Dict[str, Any]) -> bool:
        """Execute a single workflow step"""
        try:
            agent_name = step.get('agent')
            action = step.get('action')
            parameters = step.get('parameters', {})
            
            if not agent_name or not action:
                self.logger.error(f"Invalid step configuration in workflow {workflow_id}")
                return False
            
            # Create and send command message
            message = Message(
                id=f"workflow_{workflow_id}_step_{step['name']}",
                type=MessageType.COMMAND,
                sender="orchestration_agent",
                recipient=agent_name,
                payload={
                    'action': action,
                    'parameters': parameters,
                    'workflow_id': workflow_id,
                    'step_name': step['name']
                }
            )
            
            await self.send_message(message)
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing workflow step: {e}")
            return False
    
    async def start_workflow(self, workflow_id: str, workflow_definition: Dict[str, Any]) -> bool:
        """Start a new workflow execution"""
        try:
            if workflow_id in self.active_workflows:
                self.logger.warning(f"Workflow {workflow_id} already active")
                return False
            
            workflow_state = {
                'definition': workflow_definition,
                'current_step': 0,
                'completed_steps': [],
                'started_at': datetime.now(),
                'status': 'running'
            }
            
            self.active_workflows[workflow_id] = workflow_state
            self.logger.info(f"Started workflow: {workflow_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting workflow {workflow_id}: {e}")
            return False
    
    def define_workflow(self, workflow_name: str, steps: List[Dict[str, Any]], 
                       metadata: Dict[str, Any] = None):
        """Define a reusable workflow template"""
        workflow_def = {
            'name': workflow_name,
            'steps': steps,
            'metadata': metadata or {}
        }
        
        self.workflows[workflow_name] = workflow_def
        self.logger.info(f"Defined workflow: {workflow_name} with {len(steps)} steps")
    
    async def _handle_agent_timeout(self, agent_name: str):
        """Handle agent timeout scenarios"""
        self.logger.warning(f"Handling timeout for agent: {agent_name}")
        
        # Attempt to restart agent if handler available
        if agent_name in self.agent_handlers:
            try:
                restart_message = Message(
                    id=f"restart_{agent_name}_{datetime.now().timestamp()}",
                    type=MessageType.COMMAND,
                    sender="orchestration_agent",
                    recipient=agent_name,
                    payload={'action': 'restart'}
                )
                await self.send_message(restart_message)
            except Exception as e:
                self.logger.error(f"Failed to send restart message to {agent_name}: {e}")
    
    async def _handle_message_error(self, message: Message, error: str):
        """Handle message processing errors"""
        # Log error
        self.logger.error(f"Message error - ID: {message.id}, Error: {error}")
        
        # Update agent error count
        if message.sender in self.agents:
            self.agents[message.sender].error_count += 1
            self.agents[message.sender].last_error = error
        
        # Send error response if needed
        if message.type != MessageType.ERROR:
            error_response = Message(
                id=f"error_{message.id}",
                type=MessageType.ERROR,
                sender="orchestration_agent",
                recipient=message.sender,
                payload={
                    'original_message_id': message.id,
                    'error': error,
                    'timestamp': datetime.now().isoformat()
                },
                correlation_id=message.correlation_id
            )
            await self.send_message(error_response)
    
    async def _handle_workflow_step_error(self, workflow_id: str, step: Dict[str, Any]):
        """Handle workflow step execution errors"""
        self.logger.error(f"Workflow step error - Workflow: {workflow_id}, Step: {step['name']}")
        
        # Mark workflow as failed
        if workflow_id in self.active_workflows:
            self.active_workflows[workflow_id]['status'] = 'failed'
            self.active_workflows[workflow_id]['failed_step'] = step['name']
            self.active_workflows[workflow_id]['failed_at'] = datetime.now()
    
    async def _evaluate_dependency_condition(self, condition: Dict[str, Any]) -> bool:
        """Evaluate complex dependency conditions"""
        condition_type = condition.get('type')
        
        if condition_type == 'agent_status':
            agent_name = condition.get('agent')
            required_status = condition.get('status')
            if agent_name in self.agents:
                return self.agents[agent_name].status.value == required_status
        
        elif condition_type == 'metric_threshold':
            agent_name = condition.get('agent')
            metric_name = condition.get('metric')
            threshold = condition.get('threshold')
            operator = condition.get('operator', 'gte')
            
            if agent_name in self.agents:
                metrics = self.agents[agent_name].metrics
                if metric_name in metrics:
                    value = metrics[metric_name]
                    if operator == 'gte':
                        return value >= threshold
                    elif operator == 'lte':
                        return value <= threshold
                    elif operator == 'eq':
                        return value == threshold
        
        return False
    
    async def _broadcast_message(self, sender: str, msg_type: MessageType, payload: Dict[str, Any]):
        """Broadcast a message to all registered agents"""
        for agent_name in self.agents.keys():
            message = Message(
                id=f"broadcast_{datetime.now().timestamp()}",
                type=msg_type,
                sender=sender,
                recipient=agent_name,
                payload=payload
            )
            await self.send_message(message)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            'orchestrator_status': 'running' if self.is_running else 'stopped',
            'timestamp': datetime.now().isoformat(),
            'agents': {
                name: {
                    'status': info.status.value,
                    'last_heartbeat': info.last_heartbeat.isoformat(),
                    'error_count': info.error_count,
                    'capabilities': info.capabilities,
                    'metrics': info.metrics
                }
                for name, info in self.agents.items()
            },
            'active_workflows': len(self.active_workflows),
            'message_queue_size': self.message_queue.qsize(),
            'system_metrics': {
                'total_agents': len(self.agents),
                'running_agents': len([a for a in self.agents.values() if a.status == AgentStatus.RUNNING]),
                'error_agents': len([a for a in self.agents.values() if a.status == AgentStatus.ERROR])
            }
        }
    
    def add_message_handler(self, message_type: MessageType, handler: Callable):
        """Add a custom message handler"""
        self.message_handlers[message_type].append(handler)
    
    def remove_message_handler(self, message_type: MessageType, handler: Callable):
        """Remove a custom message handler"""
        if handler in self.message_handlers[message_type]:
            self.message_handlers[message_type].remove(handler)


# Example workflow definitions for AMC-TRADER
def create_trading_workflow() -> Dict[str, Any]:
    """Example trading workflow for AMC-TRADER"""
    return {
        'name': 'full_trading_cycle',
        'steps': [
            {
                'name': 'market_analysis',
                'agent': 'market_analysis_agent',
                'action': 'analyze_market_conditions',
                'parameters': {'timeframe': '1h', 'depth': 'detailed'},
                'dependencies': []
            },
            {
                'name': 'signal_generation',
                'agent': 'signal_agent',
                'action': 'generate_signals',
                'parameters': {'strategy': 'hybrid_v1'},
                'dependencies': ['market_analysis_agent']
            },
            {
                'name': 'risk_assessment',
                'agent': 'risk_management_agent',
                'action': 'assess_risk',
                'parameters': {'max_exposure': 0.02},
                'dependencies': ['signal_agent']
            },
            {
                'name': 'trade_execution',
                'agent': 'execution_agent',
                'action': 'execute_trade',
                'parameters': {'mode': 'live'},
                'dependencies': ['risk_management_agent']
            },
            {
                'name': 'position_monitoring',
                'agent': 'monitoring_agent',
                'action': 'monitor_position',
                'parameters': {'interval': 60},
                'dependencies': ['execution_agent']
            }
        ]
    }


if __name__ == "__main__":
    # Example usage
    async def main():
        # Create orchestration agent
        orchestrator = OrchestrationAgent({
            'heartbeat_interval': 30,
            'timeout_threshold': 300,
            'max_retries': 3
        })
        
        # Register some example agents
        orchestrator.register_agent(
            'market_analysis_agent', 
            ['market_data', 'technical_analysis'],
            []
        )
        
        orchestrator.register_agent(
            'signal_agent',
            ['signal_generation', 'pattern_recognition'],
            ['market_analysis_agent']
        )
        
        orchestrator.register_agent(
            'risk_management_agent',
            ['risk_calculation', 'position_sizing'],
            ['signal_agent']
        )
        
        # Define trading workflow
        trading_workflow = create_trading_workflow()
        orchestrator.define_workflow('trading_cycle', trading_workflow['steps'])
        
        # Start orchestrator (in real usage, this would run continuously)
        try:
            await orchestrator.start()
        except KeyboardInterrupt:
            await orchestrator.stop()
    
    # Run the example
    # asyncio.run(main())