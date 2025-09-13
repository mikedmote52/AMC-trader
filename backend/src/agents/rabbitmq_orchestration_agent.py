"""
RabbitMQ-Based Orchestration Agent

This implementation extends the Enhanced Orchestration Agent with RabbitMQ message bus integration
for real message-based communication between agents in the AMC-TRADER system.
"""

import pika
import json
import logging
import asyncio
import threading
import traceback
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import time

# Import base orchestration classes
from enhanced_orchestration_agent import (
    EnhancedOrchestrationAgent, CommandType, WorkflowStatus, CommandWorkflow, 
    MessageType, Message
)


class MessagePriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class RabbitMQMessage:
    id: str
    message_type: str
    sender: str
    recipient: str
    payload: Dict[str, Any]
    timestamp: str
    correlation_id: Optional[str] = None
    priority: int = 2
    reply_to: Optional[str] = None
    routing_key: str = ""


class RabbitMQOrchestrationAgent(EnhancedOrchestrationAgent):
    """
    Orchestration Agent with RabbitMQ message bus integration for real-time
    inter-agent communication in the AMC-TRADER system.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        # RabbitMQ configuration
        self.rabbitmq_config = config.get('rabbitmq', {})
        self.host = self.rabbitmq_config.get('host', 'localhost')
        self.port = self.rabbitmq_config.get('port', 5672)
        self.username = self.rabbitmq_config.get('username', 'guest')
        self.password = self.rabbitmq_config.get('password', 'guest')
        self.virtual_host = self.rabbitmq_config.get('virtual_host', '/')
        
        # Connection and channel
        self.connection = None
        self.channel = None
        self.consumer_thread = None
        self.is_consuming = False
        
        # Queue configuration
        self.orchestration_queue = 'orchestration_queue'
        self.exchange_name = 'amc_trader_exchange'
        self.routing_keys = {
            'orchestration': 'orchestration.*',
            'commands': 'commands.*',
            'responses': 'responses.*',
            'status': 'status.*',
            'alerts': 'alerts.*'
        }
        
        # Message handlers for different types
        self.message_type_handlers = {
            'command': self._handle_command_message,
            'response': self._handle_response_message,
            'status_update': self._handle_status_update_message,
            'heartbeat': self._handle_heartbeat_message,
            'error': self._handle_error_message,
            'data': self._handle_data_message
        }
        
        # Message acknowledgment tracking
        self.pending_acks = {}
        self.message_timeout = self.config.get('message_timeout', 30)
        
        # Setup specialized logging
        self.rabbitmq_logger = self._setup_rabbitmq_logging()
        
        self.logger.info("RabbitMQOrchestrationAgent initialized")
    
    def _setup_rabbitmq_logging(self) -> logging.Logger:
        """Setup specialized logging for RabbitMQ operations"""
        logger = logging.getLogger("rabbitmq_orchestration")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            from pathlib import Path
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            handler = logging.FileHandler(
                log_dir / f"rabbitmq_orchestration_{datetime.now().strftime('%Y%m%d')}.log"
            )
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    async def start(self):
        """Start the orchestration agent with RabbitMQ integration"""
        try:
            # Initialize RabbitMQ connection
            await self._setup_rabbitmq_connection()
            
            # Start base orchestration agent
            await super().start()
            
            self.logger.info("RabbitMQOrchestrationAgent started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start RabbitMQOrchestrationAgent: {e}")
            raise
    
    async def stop(self):
        """Stop the orchestration agent and close RabbitMQ connection"""
        try:
            # Stop consuming messages
            self._stop_consuming()
            
            # Close RabbitMQ connection
            self._close_rabbitmq_connection()
            
            # Stop base orchestration agent
            await super().stop()
            
            self.logger.info("RabbitMQOrchestrationAgent stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping RabbitMQOrchestrationAgent: {e}")
    
    async def _setup_rabbitmq_connection(self):
        """Setup RabbitMQ connection, exchange, and queues"""
        try:
            self.rabbitmq_logger.info("Setting up RabbitMQ connection...")
            
            # Create connection parameters
            credentials = pika.PlainCredentials(self.username, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                virtual_host=self.virtual_host,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            
            # Establish connection
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare exchange
            self.channel.exchange_declare(
                exchange=self.exchange_name,
                exchange_type='topic',
                durable=True
            )
            
            # Declare orchestration queue
            self.channel.queue_declare(
                queue=self.orchestration_queue,
                durable=True,
                arguments={
                    'x-message-ttl': 300000,  # 5 minutes TTL
                    'x-max-length': 10000,    # Max 10k messages
                    'x-overflow': 'drop-head'
                }
            )
            
            # Bind queue to routing keys
            for routing_key in self.routing_keys.values():
                self.channel.queue_bind(
                    exchange=self.exchange_name,
                    queue=self.orchestration_queue,
                    routing_key=routing_key
                )
            
            # Setup QoS for fair dispatch
            self.channel.basic_qos(prefetch_count=10)
            
            # Start consuming messages
            self._start_consuming()
            
            self.rabbitmq_logger.info(f"RabbitMQ connection established successfully")
            self.rabbitmq_logger.info(f"Listening on queue: {self.orchestration_queue}")
            
        except Exception as e:
            self.rabbitmq_logger.error(f"Failed to setup RabbitMQ connection: {e}")
            raise
    
    def _start_consuming(self):
        """Start consuming messages from RabbitMQ in a separate thread"""
        def consume_messages():
            try:
                self.rabbitmq_logger.info("Starting message consumption...")
                
                self.channel.basic_consume(
                    queue=self.orchestration_queue,
                    on_message_callback=self._message_callback,
                    auto_ack=False
                )
                
                self.is_consuming = True
                self.rabbitmq_logger.info("Orchestration Agent is listening for messages...")
                
                # Start consuming (this blocks)
                self.channel.start_consuming()
                
            except Exception as e:
                self.rabbitmq_logger.error(f"Error in message consumption: {e}")
                self.is_consuming = False
        
        # Start consumer in separate thread
        self.consumer_thread = threading.Thread(target=consume_messages, daemon=True)
        self.consumer_thread.start()
    
    def _stop_consuming(self):
        """Stop consuming messages from RabbitMQ"""
        if self.is_consuming and self.channel:
            try:
                self.channel.stop_consuming()
                self.is_consuming = False
                
                if self.consumer_thread and self.consumer_thread.is_alive():
                    self.consumer_thread.join(timeout=5)
                
                self.rabbitmq_logger.info("Stopped consuming messages")
                
            except Exception as e:
                self.rabbitmq_logger.error(f"Error stopping message consumption: {e}")
    
    def _close_rabbitmq_connection(self):
        """Close RabbitMQ connection"""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                self.rabbitmq_logger.info("RabbitMQ connection closed")
                
        except Exception as e:
            self.rabbitmq_logger.error(f"Error closing RabbitMQ connection: {e}")
    
    def _message_callback(self, ch, method, properties, body):
        """Main callback function to handle incoming messages from other agents"""
        try:
            # Decode message
            message_data = json.loads(body.decode('utf-8'))
            
            # Create RabbitMQ message object
            rabbitmq_message = RabbitMQMessage(**message_data)
            
            self.rabbitmq_logger.info(
                f"Received message from {rabbitmq_message.sender}: "
                f"{rabbitmq_message.message_type} (ID: {rabbitmq_message.id})"
            )
            
            # Get handler for message type
            handler = self.message_type_handlers.get(rabbitmq_message.message_type)
            
            if handler:
                # Process message asynchronously
                asyncio.run_coroutine_threadsafe(
                    handler(rabbitmq_message), 
                    self._get_event_loop()
                )
                
                # Acknowledge message
                ch.basic_ack(delivery_tag=method.delivery_tag)
                
                self.rabbitmq_logger.debug(f"Message {rabbitmq_message.id} processed and acknowledged")
                
            else:
                self.rabbitmq_logger.warning(
                    f"No handler found for message type: {rabbitmq_message.message_type}"
                )
                # Reject message
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
        except json.JSONDecodeError as e:
            self.rabbitmq_logger.error(f"Failed to decode message JSON: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
        except Exception as e:
            self.rabbitmq_logger.error(f"Error processing message: {e}")
            self.rabbitmq_logger.error(f"Traceback: {traceback.format_exc()}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def _get_event_loop(self):
        """Get or create event loop for async operations"""
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            # Create new event loop if none exists
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop
    
    async def _handle_command_message(self, message: RabbitMQMessage):
        """Handle command messages from Management Agent"""
        try:
            payload = message.payload
            command_type_str = payload.get('command_type')
            parameters = payload.get('parameters', {})
            
            # Convert string to CommandType enum
            try:
                command_type = CommandType(command_type_str)
            except ValueError:
                raise Exception(f"Unknown command type: {command_type_str}")
            
            # Execute command workflow
            workflow_id = await self.receive_command(
                command_type, 
                parameters, 
                requester=message.sender
            )
            
            # Send acknowledgment back to sender
            await self._send_rabbitmq_message(
                message_type='response',
                recipient=message.sender,
                payload={
                    'command_received': True,
                    'workflow_id': workflow_id,
                    'original_message_id': message.id
                },
                correlation_id=message.id,
                priority=MessagePriority.HIGH.value
            )
            
            self.rabbitmq_logger.info(f"Command {command_type_str} received and executed: {workflow_id}")
            
        except Exception as e:
            # Send error response
            await self._send_rabbitmq_message(
                message_type='error',
                recipient=message.sender,
                payload={
                    'error': str(e),
                    'original_message_id': message.id,
                    'error_type': 'command_execution_failed'
                },
                correlation_id=message.id,
                priority=MessagePriority.HIGH.value
            )
            
            self.rabbitmq_logger.error(f"Error handling command message: {e}")
    
    async def _handle_response_message(self, message: RabbitMQMessage):
        """Handle response messages from other agents"""
        try:
            # Log the response
            self.rabbitmq_logger.info(f"Received response from {message.sender}: {message.payload}")
            
            # Update agent status based on response
            if message.sender in self.agents:
                self.agents[message.sender].last_heartbeat = datetime.now()
                self.agents[message.sender].status = AgentStatus.RUNNING
                
                # Update metrics if provided
                if 'metrics' in message.payload:
                    self.agents[message.sender].metrics.update(message.payload['metrics'])
            
            # Handle workflow responses
            if 'workflow_id' in message.payload:
                workflow_id = message.payload['workflow_id']
                if workflow_id in self.active_workflows:
                    workflow = self.active_workflows[workflow_id]
                    
                    # Update workflow based on response
                    if message.payload.get('status') == 'completed':
                        workflow.progress = message.payload.get('progress', workflow.progress)
                        
                        # Send progress update
                        await self._send_progress_update(workflow)
            
        except Exception as e:
            self.rabbitmq_logger.error(f"Error handling response message: {e}")
    
    async def _handle_status_update_message(self, message: RabbitMQMessage):
        """Handle status update messages from agents"""
        try:
            payload = message.payload
            agent_name = message.sender
            
            # Update agent status
            if agent_name in self.agents:
                agent = self.agents[agent_name]
                
                # Update based on status type
                if 'health_status' in payload:
                    health = payload['health_status']
                    if health == 'healthy':
                        agent.status = AgentStatus.RUNNING
                    elif health == 'degraded':
                        agent.status = AgentStatus.ERROR
                    else:
                        agent.status = AgentStatus.IDLE
                
                # Update metrics
                if 'metrics' in payload:
                    agent.metrics.update(payload['metrics'])
                
                # Update last heartbeat
                agent.last_heartbeat = datetime.now()
            
            self.rabbitmq_logger.debug(f"Status update from {agent_name}: {payload}")
            
        except Exception as e:
            self.rabbitmq_logger.error(f"Error handling status update: {e}")
    
    async def _handle_heartbeat_message(self, message: RabbitMQMessage):
        """Handle heartbeat messages from agents"""
        try:
            agent_name = message.sender
            
            if agent_name in self.agents:
                self.agents[agent_name].last_heartbeat = datetime.now()
                self.agents[agent_name].status = AgentStatus.RUNNING
                
                # Update metrics if provided
                if 'metrics' in message.payload:
                    self.agents[agent_name].metrics.update(message.payload['metrics'])
            
            self.rabbitmq_logger.debug(f"Heartbeat received from {agent_name}")
            
        except Exception as e:
            self.rabbitmq_logger.error(f"Error handling heartbeat: {e}")
    
    async def _handle_error_message(self, message: RabbitMQMessage):
        """Handle error messages from agents"""
        try:
            agent_name = message.sender
            error_info = message.payload
            
            # Update agent error status
            if agent_name in self.agents:
                agent = self.agents[agent_name]
                agent.status = AgentStatus.ERROR
                agent.error_count += 1
                agent.last_error = error_info.get('error_message', 'Unknown error')
            
            # Log error
            self.rabbitmq_logger.error(
                f"Error reported by {agent_name}: {error_info.get('error_message', 'Unknown error')}"
            )
            
            # Handle workflow errors
            if 'workflow_id' in error_info:
                workflow_id = error_info['workflow_id']
                if workflow_id in self.active_workflows:
                    workflow = self.active_workflows[workflow_id]
                    workflow.error_messages.append(f"{agent_name}: {error_info.get('error_message', 'Unknown error')}")
                    
                    # Check if workflow should be failed
                    if error_info.get('critical', False):
                        workflow.status = WorkflowStatus.FAILED
                        await self._send_progress_update(workflow)
            
        except Exception as e:
            self.rabbitmq_logger.error(f"Error handling error message: {e}")
    
    async def _handle_data_message(self, message: RabbitMQMessage):
        """Handle data messages from agents (discovery results, market data, etc.)"""
        try:
            agent_name = message.sender
            data_type = message.payload.get('data_type', 'unknown')
            
            self.rabbitmq_logger.info(f"Received {data_type} data from {agent_name}")
            
            # Route data based on type
            if data_type == 'discovery_results':
                await self._handle_discovery_results(message.payload)
            elif data_type == 'market_data':
                await self._handle_market_data(message.payload)
            elif data_type == 'backtest_results':
                await self._handle_backtest_results(message.payload)
            else:
                self.rabbitmq_logger.debug(f"Unhandled data type: {data_type}")
            
        except Exception as e:
            self.rabbitmq_logger.error(f"Error handling data message: {e}")
    
    async def _handle_discovery_results(self, data: Dict[str, Any]):
        """Handle discovery results from discovery algorithm agent"""
        candidates = data.get('candidates', [])
        strategy = data.get('strategy', 'unknown')
        
        self.rabbitmq_logger.info(f"Discovery results: {len(candidates)} candidates using {strategy}")
        
        # Broadcast discovery results to interested agents
        await self._broadcast_rabbitmq_message(
            message_type='data',
            payload={
                'data_type': 'discovery_results',
                'candidates': candidates,
                'strategy': strategy,
                'timestamp': datetime.now().isoformat()
            },
            recipients=['management_agent', 'monitoring_alerting_agent']
        )
    
    async def _handle_market_data(self, data: Dict[str, Any]):
        """Handle market data from API integration agent"""
        symbols = data.get('symbols', [])
        data_source = data.get('source', 'unknown')
        
        self.rabbitmq_logger.info(f"Market data received: {len(symbols)} symbols from {data_source}")
        
        # Route to discovery agent if needed
        if data.get('for_discovery', False):
            await self._send_rabbitmq_message(
                message_type='data',
                recipient='discovery_algorithm_agent',
                payload=data
            )
    
    async def _handle_backtest_results(self, data: Dict[str, Any]):
        """Handle backtest results from backtesting agent"""
        results = data.get('results', {})
        strategy = data.get('strategy', 'unknown')
        
        self.rabbitmq_logger.info(f"Backtest results for {strategy}: {results}")
        
        # Forward to management agent
        await self._send_rabbitmq_message(
            message_type='data',
            recipient='management_agent',
            payload={
                'data_type': 'backtest_complete',
                'strategy': strategy,
                'results': results,
                'timestamp': datetime.now().isoformat()
            }
        )
    
    async def _send_rabbitmq_message(self, message_type: str, recipient: str, 
                                   payload: Dict[str, Any], correlation_id: str = None,
                                   priority: int = MessagePriority.NORMAL.value,
                                   routing_key: str = None):
        """Send message via RabbitMQ to specific agent"""
        try:
            # Create message
            message = RabbitMQMessage(
                id=str(uuid.uuid4()),
                message_type=message_type,
                sender="rabbitmq_orchestration_agent",
                recipient=recipient,
                payload=payload,
                timestamp=datetime.now().isoformat(),
                correlation_id=correlation_id,
                priority=priority,
                routing_key=routing_key or f"{message_type}.{recipient}"
            )
            
            # Convert to JSON
            message_json = json.dumps(asdict(message), default=str)
            
            # Publish message
            self.channel.basic_publish(
                exchange=self.exchange_name,
                routing_key=message.routing_key,
                body=message_json,
                properties=pika.BasicProperties(
                    priority=priority,
                    correlation_id=correlation_id,
                    reply_to=self.orchestration_queue,
                    timestamp=int(time.time())
                )
            )
            
            self.rabbitmq_logger.debug(f"Sent {message_type} message to {recipient}: {message.id}")
            
        except Exception as e:
            self.rabbitmq_logger.error(f"Failed to send message to {recipient}: {e}")
            raise
    
    async def _broadcast_rabbitmq_message(self, message_type: str, payload: Dict[str, Any],
                                        recipients: List[str] = None, 
                                        priority: int = MessagePriority.NORMAL.value):
        """Broadcast message to multiple agents via RabbitMQ"""
        if recipients is None:
            recipients = list(self.agents.keys())
        
        for recipient in recipients:
            if recipient != "rabbitmq_orchestration_agent":  # Don't send to ourselves
                await self._send_rabbitmq_message(
                    message_type=message_type,
                    recipient=recipient,
                    payload=payload,
                    priority=priority
                )
    
    async def _send_progress_update(self, workflow: CommandWorkflow):
        """Override to send progress updates via RabbitMQ"""
        # Send via RabbitMQ to Management Agent
        await self._send_rabbitmq_message(
            message_type='status_update',
            recipient=self.management_agent_id,
            payload={
                'progress_update': {
                    'workflow_id': workflow.id,
                    'command_type': workflow.command_type.value,
                    'progress': workflow.progress,
                    'current_step': workflow.current_step,
                    'status': workflow.status.value,
                    'timestamp': datetime.now().isoformat(),
                    'details': {
                        'steps_completed': workflow.steps_completed,
                        'steps_failed': workflow.steps_failed,
                        'error_messages': workflow.error_messages
                    }
                }
            },
            priority=MessagePriority.HIGH.value
        )
        
        # Also call parent method for internal tracking
        await super()._send_progress_update(workflow)
    
    async def send_command_to_agent(self, agent_name: str, command: str, 
                                  parameters: Dict[str, Any] = None) -> str:
        """Send command to specific agent via RabbitMQ"""
        command_id = str(uuid.uuid4())
        
        await self._send_rabbitmq_message(
            message_type='command',
            recipient=agent_name,
            payload={
                'command_id': command_id,
                'command': command,
                'parameters': parameters or {},
                'timestamp': datetime.now().isoformat()
            },
            correlation_id=command_id,
            priority=MessagePriority.HIGH.value
        )
        
        self.rabbitmq_logger.info(f"Sent command '{command}' to {agent_name}: {command_id}")
        return command_id
    
    def get_rabbitmq_status(self) -> Dict[str, Any]:
        """Get RabbitMQ connection and queue status"""
        try:
            return {
                'connection_open': self.connection and not self.connection.is_closed,
                'channel_open': self.channel and self.channel.is_open,
                'is_consuming': self.is_consuming,
                'orchestration_queue': self.orchestration_queue,
                'exchange_name': self.exchange_name,
                'routing_keys': self.routing_keys,
                'pending_acks': len(self.pending_acks),
                'consumer_thread_alive': self.consumer_thread and self.consumer_thread.is_alive()
            }
        except Exception as e:
            return {
                'error': str(e),
                'connection_open': False,
                'is_consuming': False
            }


# Message Bus Interface for easy agent integration
class AgentMessageBus:
    """Simple interface for agents to communicate via RabbitMQ"""
    
    def __init__(self, agent_name: str, rabbitmq_config: Dict[str, Any] = None):
        self.agent_name = agent_name
        self.config = rabbitmq_config or {}
        self.connection = None
        self.channel = None
        self.exchange_name = 'amc_trader_exchange'
    
    async def connect(self):
        """Connect to RabbitMQ"""
        try:
            credentials = pika.PlainCredentials(
                self.config.get('username', 'guest'),
                self.config.get('password', 'guest')
            )
            
            parameters = pika.ConnectionParameters(
                host=self.config.get('host', 'localhost'),
                port=self.config.get('port', 5672),
                virtual_host=self.config.get('virtual_host', '/'),
                credentials=credentials
            )
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare exchange
            self.channel.exchange_declare(
                exchange=self.exchange_name,
                exchange_type='topic',
                durable=True
            )
            
        except Exception as e:
            raise Exception(f"Failed to connect to RabbitMQ: {e}")
    
    async def send_message(self, recipient: str, message_type: str, payload: Dict[str, Any]):
        """Send message to another agent"""
        if not self.connection or self.connection.is_closed:
            await self.connect()
        
        message = RabbitMQMessage(
            id=str(uuid.uuid4()),
            message_type=message_type,
            sender=self.agent_name,
            recipient=recipient,
            payload=payload,
            timestamp=datetime.now().isoformat(),
            routing_key=f"{message_type}.{recipient}"
        )
        
        message_json = json.dumps(asdict(message), default=str)
        
        self.channel.basic_publish(
            exchange=self.exchange_name,
            routing_key=message.routing_key,
            body=message_json
        )
    
    async def disconnect(self):
        """Disconnect from RabbitMQ"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()


if __name__ == "__main__":
    # Example usage and testing
    async def main():
        # Configuration
        config = {
            'heartbeat_interval': 15,
            'timeout_threshold': 300,
            'max_concurrent_workflows': 5,
            'workflow_timeout': 900,
            'rabbitmq': {
                'host': 'localhost',
                'port': 5672,
                'username': 'guest',
                'password': 'guest',
                'virtual_host': '/'
            }
        }
        
        print("🎯 Starting RabbitMQ Orchestration Agent")
        print("=" * 50)
        
        try:
            # Create and start agent
            orchestrator = RabbitMQOrchestrationAgent(config)
            
            # Register agents
            orchestrator.register_agent("management_agent", ["system_management"], [])
            orchestrator.register_agent("discovery_algorithm_agent", ["candidate_discovery"], [])
            orchestrator.register_agent("data_validation_agent", ["data_validation"], [])
            
            # Start orchestrator
            await orchestrator.start()
            
            print("✅ RabbitMQ Orchestration Agent started successfully")
            print(f"📊 RabbitMQ Status: {orchestrator.get_rabbitmq_status()}")
            
            # Keep running for demo
            await asyncio.sleep(30)
            
            # Stop orchestrator
            await orchestrator.stop()
            print("✅ RabbitMQ Orchestration Agent stopped successfully")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Run the example
    # asyncio.run(main())