"""
Orchestration Messaging System

Handles communication between the API Integration Agent and the Orchestration Agent
through RabbitMQ message bus for coordination and status reporting.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, asdict

import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError


class MessageType(Enum):
    """Message types for orchestration communication."""
    STATUS_UPDATE = "status_update"
    COMPLETION_NOTIFICATION = "completion_notification"
    ERROR_ALERT = "error_alert"
    PERFORMANCE_METRICS = "performance_metrics"
    CACHE_UPDATE = "cache_update"
    HEALTH_CHECK = "health_check"
    OPTIMIZATION_RECOMMENDATION = "optimization_recommendation"


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class OrchestrationMessage:
    """Standardized message format for orchestration communication."""
    agent_name: str
    message_type: MessageType
    priority: MessagePriority
    timestamp: str
    data: Dict[str, Any]
    correlation_id: Optional[str] = None
    expires_at: Optional[str] = None


class OrchestrationMessenger:
    """
    Handles message communication with the Orchestration Agent.
    
    Features:
    - Reliable message delivery with retry logic
    - Message prioritization and queuing
    - Connection management and health monitoring
    - Error handling and fallback mechanisms
    - Message correlation and tracking
    """
    
    def __init__(
        self,
        agent_name: str = "API Integration Agent",
        rabbitmq_host: str = "localhost",
        rabbitmq_port: int = 5672,
        queue_name: str = "orchestration_queue",
        max_retries: int = 3
    ):
        self.agent_name = agent_name
        self.rabbitmq_host = rabbitmq_host
        self.rabbitmq_port = rabbitmq_port
        self.queue_name = queue_name
        self.max_retries = max_retries
        
        self.logger = logging.getLogger(__name__)
        
        # Connection management
        self.connection = None
        self.channel = None
        self.is_connected = False
        
        # Message tracking
        self.messages_sent = 0
        self.messages_failed = 0
        self.last_connection_attempt = 0
        
        # Initialize connection
        self._initialize_connection()
    
    def _initialize_connection(self) -> bool:
        """
        Initialize RabbitMQ connection and channel.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.last_connection_attempt = time.time()
            
            # Create connection
            connection_params = pika.ConnectionParameters(
                host=self.rabbitmq_host,
                port=self.rabbitmq_port,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            
            self.connection = pika.BlockingConnection(connection_params)
            self.channel = self.connection.channel()
            
            # Declare queue with durability
            self.channel.queue_declare(
                queue=self.queue_name,
                durable=True,
                arguments={
                    'x-message-ttl': 3600000,  # 1 hour TTL
                    'x-max-priority': 4  # Priority queue support
                }
            )
            
            self.is_connected = True
            self.logger.info(f"Successfully connected to RabbitMQ at {self.rabbitmq_host}:{self.rabbitmq_port}")
            
            return True
            
        except AMQPConnectionError as e:
            self.logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            self.is_connected = False
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during connection: {str(e)}")
            self.is_connected = False
            return False
    
    def send_message_to_orchestrator(
        self,
        message_type: MessageType,
        data: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None,
        expires_in_seconds: Optional[int] = None
    ) -> bool:
        """
        Send message to the Orchestration Agent.
        
        Args:
            message_type: Type of message being sent
            data: Message payload data
            priority: Message priority level
            correlation_id: Optional correlation ID for tracking
            expires_in_seconds: Optional message expiration time
            
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            # Ensure connection is active
            if not self._ensure_connection():
                return False
            
            # Create standardized message
            expires_at = None
            if expires_in_seconds:
                expires_at = datetime.fromtimestamp(
                    time.time() + expires_in_seconds,
                    timezone.utc
                ).isoformat()
            
            message = OrchestrationMessage(
                agent_name=self.agent_name,
                message_type=message_type,
                priority=priority,
                timestamp=datetime.utcnow().isoformat(),
                data=data,
                correlation_id=correlation_id or f"api_integration_{int(time.time() * 1000)}",
                expires_at=expires_at
            )
            
            # Convert to JSON
            message_json = json.dumps(asdict(message), default=str)
            
            # Send with priority and persistence
            self.channel.basic_publish(
                exchange='',
                routing_key=self.queue_name,
                body=message_json,
                properties=pika.BasicProperties(
                    priority=priority.value,
                    delivery_mode=2,  # Persistent message
                    correlation_id=message.correlation_id,
                    timestamp=int(time.time()),
                    expiration=str(expires_in_seconds * 1000) if expires_in_seconds else None
                )
            )
            
            self.messages_sent += 1
            
            self.logger.info(
                f"Message sent to orchestrator: {message_type.value}",
                extra={
                    'message_type': message_type.value,
                    'priority': priority.value,
                    'correlation_id': message.correlation_id,
                    'data_size': len(message_json)
                }
            )
            
            return True
            
        except Exception as e:
            self.messages_failed += 1
            self.logger.error(f"Failed to send message to orchestrator: {str(e)}")
            return False
    
    def send_status_update(
        self,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Send status update to orchestrator."""
        data = {
            'status': status,
            'details': details or {},
            'agent_status': 'operational',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return self.send_message_to_orchestrator(
            MessageType.STATUS_UPDATE,
            data,
            MessagePriority.NORMAL,
            correlation_id
        )
    
    def send_completion_notification(
        self,
        task: str,
        result: Dict[str, Any],
        duration_ms: Optional[float] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Send task completion notification to orchestrator."""
        data = {
            'task': task,
            'result': result,
            'duration_ms': duration_ms,
            'completed_at': datetime.utcnow().isoformat()
        }
        
        return self.send_message_to_orchestrator(
            MessageType.COMPLETION_NOTIFICATION,
            data,
            MessagePriority.NORMAL,
            correlation_id
        )
    
    def send_error_alert(
        self,
        error_type: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
        severity: str = "medium",
        correlation_id: Optional[str] = None
    ) -> bool:
        """Send error alert to orchestrator."""
        priority = MessagePriority.HIGH if severity == "high" else MessagePriority.NORMAL
        if severity == "critical":
            priority = MessagePriority.CRITICAL
        
        data = {
            'error_type': error_type,
            'error_message': error_message,
            'error_details': error_details or {},
            'severity': severity,
            'agent_name': self.agent_name,
            'error_timestamp': datetime.utcnow().isoformat()
        }
        
        return self.send_message_to_orchestrator(
            MessageType.ERROR_ALERT,
            data,
            priority,
            correlation_id
        )
    
    def send_performance_metrics(
        self,
        metrics: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> bool:
        """Send performance metrics to orchestrator."""
        data = {
            'metrics': metrics,
            'agent_performance': {
                'messages_sent': self.messages_sent,
                'messages_failed': self.messages_failed,
                'connection_status': self.is_connected
            },
            'metrics_timestamp': datetime.utcnow().isoformat()
        }
        
        return self.send_message_to_orchestrator(
            MessageType.PERFORMANCE_METRICS,
            data,
            MessagePriority.LOW,
            correlation_id
        )
    
    def send_cache_update_notification(
        self,
        cache_operation: str,
        cache_key: str,
        cache_data: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Send cache update notification to orchestrator."""
        data = {
            'cache_operation': cache_operation,
            'cache_key': cache_key,
            'cache_data': cache_data or {},
            'cache_timestamp': datetime.utcnow().isoformat()
        }
        
        return self.send_message_to_orchestrator(
            MessageType.CACHE_UPDATE,
            data,
            MessagePriority.LOW,
            correlation_id
        )
    
    def send_health_check(
        self,
        health_status: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> bool:
        """Send health check status to orchestrator."""
        data = {
            'health_status': health_status,
            'messaging_health': {
                'connected': self.is_connected,
                'messages_sent': self.messages_sent,
                'messages_failed': self.messages_failed,
                'last_connection_attempt': self.last_connection_attempt
            },
            'health_check_timestamp': datetime.utcnow().isoformat()
        }
        
        return self.send_message_to_orchestrator(
            MessageType.HEALTH_CHECK,
            data,
            MessagePriority.LOW,
            correlation_id
        )
    
    def send_optimization_recommendation(
        self,
        recommendations: List[Dict[str, Any]],
        correlation_id: Optional[str] = None
    ) -> bool:
        """Send optimization recommendations to orchestrator."""
        data = {
            'recommendations': recommendations,
            'recommendation_count': len(recommendations),
            'generated_at': datetime.utcnow().isoformat()
        }
        
        return self.send_message_to_orchestrator(
            MessageType.OPTIMIZATION_RECOMMENDATION,
            data,
            MessagePriority.NORMAL,
            correlation_id
        )
    
    def _ensure_connection(self) -> bool:
        """
        Ensure RabbitMQ connection is active, reconnect if necessary.
        
        Returns:
            True if connection is active, False otherwise
        """
        if self.is_connected and self.connection and not self.connection.is_closed:
            return True
        
        # Attempt reconnection with retry logic
        for attempt in range(self.max_retries):
            self.logger.info(f"Attempting to reconnect to RabbitMQ (attempt {attempt + 1}/{self.max_retries})")
            
            if self._initialize_connection():
                return True
            
            # Wait before retry
            time.sleep(2 ** attempt)  # Exponential backoff
        
        self.logger.error(f"Failed to establish connection after {self.max_retries} attempts")
        return False
    
    def get_messaging_statistics(self) -> Dict[str, Any]:
        """Get messaging system statistics."""
        return {
            'agent_name': self.agent_name,
            'connection_status': self.is_connected,
            'messages_sent': self.messages_sent,
            'messages_failed': self.messages_failed,
            'success_rate': (
                self.messages_sent / max(self.messages_sent + self.messages_failed, 1)
            ) * 100,
            'last_connection_attempt': self.last_connection_attempt,
            'rabbitmq_host': self.rabbitmq_host,
            'queue_name': self.queue_name,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def close_connection(self):
        """Close RabbitMQ connection gracefully."""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                self.logger.info("RabbitMQ connection closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing RabbitMQ connection: {str(e)}")
        finally:
            self.is_connected = False
            self.connection = None
            self.channel = None
    
    def __del__(self):
        """Cleanup on object destruction."""
        self.close_connection()


# Global messenger instance
_orchestration_messenger = None

def get_orchestration_messenger() -> OrchestrationMessenger:
    """Get singleton orchestration messenger instance."""
    global _orchestration_messenger
    if _orchestration_messenger is None:
        _orchestration_messenger = OrchestrationMessenger()
    return _orchestration_messenger


# Convenience function for quick message sending
def send_message_to_orchestrator(message: Dict[str, Any]) -> bool:
    """
    Quick function to send message to orchestrator (maintains compatibility).
    
    Args:
        message: Message dictionary with 'status' and optional 'data' fields
        
    Returns:
        True if message sent successfully
    """
    try:
        messenger = get_orchestration_messenger()
        
        # Extract message components
        status = message.get('status', 'unknown')
        data = message.get('data', {})
        priority_str = message.get('priority', 'normal').lower()
        
        # Map priority
        priority_map = {
            'low': MessagePriority.LOW,
            'normal': MessagePriority.NORMAL,
            'high': MessagePriority.HIGH,
            'critical': MessagePriority.CRITICAL
        }
        priority = priority_map.get(priority_str, MessagePriority.NORMAL)
        
        # Determine message type based on status
        if 'error' in status.lower() or 'fail' in status.lower():
            message_type = MessageType.ERROR_ALERT
        elif 'complete' in status.lower() or 'finish' in status.lower():
            message_type = MessageType.COMPLETION_NOTIFICATION
        elif 'health' in status.lower():
            message_type = MessageType.HEALTH_CHECK
        else:
            message_type = MessageType.STATUS_UPDATE
        
        return messenger.send_message_to_orchestrator(
            message_type=message_type,
            data={'status': status, **data},
            priority=priority
        )
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to send message to orchestrator: {str(e)}")
        return False