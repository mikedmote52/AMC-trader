"""
Message Bus Integration for AMC-TRADER Agent Communication

This module provides RabbitMQ-based messaging capabilities for inter-agent communication,
specifically enabling the Management Agent to send commands and status updates to the Orchestration Agent.
"""

import pika
import json
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

class MessageType(Enum):
    STATUS_UPDATE = "status_update"
    COMMAND_REQUEST = "command_request"
    ALERT_NOTIFICATION = "alert_notification"
    HEALTH_REPORT = "health_report"
    COMPLETION_NOTIFICATION = "completion_notification"
    ERROR_ALERT = "error_alert"

@dataclass
class AgentMessage:
    message_type: MessageType
    agent_name: str
    timestamp: str
    data: Dict[str, Any]
    priority: str = "medium"
    correlation_id: Optional[str] = None

class MessageBusConnector:
    """
    RabbitMQ connector for inter-agent communication
    """
    
    def __init__(self, host: str = 'localhost', port: int = 5672):
        self.host = host
        self.port = port
        self.logger = logging.getLogger(__name__)
        self.connection = None
        self.channel = None
        
    def connect(self) -> bool:
        """Establish connection to RabbitMQ"""
        try:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=self.host, port=self.port)
            )
            self.channel = self.connection.channel()
            
            # Declare queues
            self.channel.queue_declare(queue='orchestration_queue', durable=True)
            self.channel.queue_declare(queue='management_responses', durable=True)
            
            self.logger.info("Successfully connected to RabbitMQ message bus")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    def disconnect(self):
        """Close RabbitMQ connection"""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                self.logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            self.logger.error(f"Error disconnecting from RabbitMQ: {e}")
    
    def send_message_to_orchestrator(self, message: Dict[str, Any]) -> bool:
        """Send message to Orchestration Agent"""
        try:
            if not self.channel:
                if not self.connect():
                    return False
            
            # Add metadata
            message['agent_name'] = 'Management Agent'
            message['timestamp'] = datetime.now().isoformat()
            
            # Publish message
            self.channel.basic_publish(
                exchange='',
                routing_key='orchestration_queue',
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    priority=self._get_priority_value(message.get('priority', 'medium'))
                )
            )
            
            self.logger.info(f"Message sent to Orchestration Agent: {message.get('message_type', 'unknown')}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send message to Orchestration Agent: {e}")
            return False
    
    def _get_priority_value(self, priority: str) -> int:
        """Convert priority string to numeric value"""
        priority_map = {
            'low': 1,
            'medium': 5,
            'high': 8,
            'critical': 10
        }
        return priority_map.get(priority.lower(), 5)

class ManagementAgentMessenger:
    """
    Message bus interface specifically for the Management Agent
    """
    
    def __init__(self, message_bus: MessageBusConnector):
        self.message_bus = message_bus
        self.logger = logging.getLogger(__name__)
    
    async def send_status_update(self, system_health: str, metrics: Dict[str, Any]):
        """Send system status update to Orchestration Agent"""
        message = {
            'message_type': MessageType.STATUS_UPDATE.value,
            'priority': 'medium',
            'data': {
                'system_health': system_health,
                'metrics': metrics,
                'update_type': 'periodic_health_check'
            }
        }
        
        return self.message_bus.send_message_to_orchestrator(message)
    
    async def send_command_request(self, command: str, parameters: Dict[str, Any], priority: str = 'medium'):
        """Send command execution request to Orchestration Agent"""
        message = {
            'message_type': MessageType.COMMAND_REQUEST.value,
            'priority': priority,
            'data': {
                'command': command,
                'parameters': parameters,
                'requested_by': 'automated_decision_engine',
                'correlation_id': f"cmd_{int(datetime.now().timestamp())}"
            }
        }
        
        self.logger.info(f"Requesting command execution: {command} (Priority: {priority})")
        return self.message_bus.send_message_to_orchestrator(message)
    
    async def send_alert_notification(self, alert_level: str, component: str, message_text: str):
        """Send alert notification to Orchestration Agent"""
        message = {
            'message_type': MessageType.ALERT_NOTIFICATION.value,
            'priority': 'high' if alert_level in ['ERROR', 'CRITICAL'] else 'medium',
            'data': {
                'alert_level': alert_level,
                'component': component,
                'message': message_text,
                'alert_timestamp': datetime.now().isoformat()
            }
        }
        
        return self.message_bus.send_message_to_orchestrator(message)
    
    async def send_health_report(self, comprehensive_report: Dict[str, Any]):
        """Send comprehensive health report to Orchestration Agent"""
        message = {
            'message_type': MessageType.HEALTH_REPORT.value,
            'priority': 'medium',
            'data': {
                'report': comprehensive_report,
                'report_type': 'comprehensive_system_analysis'
            }
        }
        
        return self.message_bus.send_message_to_orchestrator(message)
    
    async def send_completion_notification(self, task: str, result: Dict[str, Any]):
        """Send task completion notification to Orchestration Agent"""
        message = {
            'message_type': MessageType.COMPLETION_NOTIFICATION.value,
            'priority': 'medium',
            'data': {
                'completed_task': task,
                'result': result,
                'completion_time': datetime.now().isoformat()
            }
        }
        
        return self.message_bus.send_message_to_orchestrator(message)
    
    async def send_error_alert(self, error_type: str, error_message: str, context: Dict[str, Any]):
        """Send error alert to Orchestration Agent"""
        message = {
            'message_type': MessageType.ERROR_ALERT.value,
            'priority': 'high',
            'data': {
                'error_type': error_type,
                'error_message': error_message,
                'context': context,
                'error_timestamp': datetime.now().isoformat()
            }
        }
        
        return self.message_bus.send_message_to_orchestrator(message)
    
    async def send_automated_action_trigger(self, rule_name: str, action: str, reason: str):
        """Send notification about automated action being triggered"""
        message = {
            'message_type': MessageType.COMMAND_REQUEST.value,
            'priority': 'high',
            'data': {
                'command': action,
                'parameters': {
                    'triggered_by_rule': rule_name,
                    'trigger_reason': reason,
                    'automated': True
                },
                'requested_by': 'automated_decision_engine',
                'correlation_id': f"auto_{rule_name}_{int(datetime.now().timestamp())}"
            }
        }
        
        self.logger.info(f"Sending automated action trigger: {action} (Rule: {rule_name})")
        return self.message_bus.send_message_to_orchestrator(message)

# Integration functions for existing Management Agent
def create_message_bus_integration() -> ManagementAgentMessenger:
    """Create and initialize message bus integration"""
    try:
        message_bus = MessageBusConnector()
        if message_bus.connect():
            return ManagementAgentMessenger(message_bus)
        else:
            logging.error("Failed to establish message bus connection")
            return None
    except Exception as e:
        logging.error(f"Error creating message bus integration: {e}")
        return None

def test_message_bus_connection():
    """Test RabbitMQ connection and basic messaging"""
    print("🔌 Testing Message Bus Connection...")
    
    try:
        # Test connection
        message_bus = MessageBusConnector()
        if not message_bus.connect():
            print("❌ Failed to connect to RabbitMQ")
            return False
        
        print("✅ Connected to RabbitMQ successfully")
        
        # Test message sending
        messenger = ManagementAgentMessenger(message_bus)
        
        # Send test message
        test_message = {
            'message_type': 'status_update',
            'priority': 'low',
            'data': {
                'test': True,
                'message': 'Connection test successful'
            }
        }
        
        if message_bus.send_message_to_orchestrator(test_message):
            print("✅ Test message sent successfully")
        else:
            print("❌ Failed to send test message")
        
        message_bus.disconnect()
        print("✅ Message bus integration test completed")
        return True
        
    except Exception as e:
        print(f"❌ Message bus test failed: {e}")
        return False

if __name__ == "__main__":
    # Test the message bus integration
    logging.basicConfig(level=logging.INFO)
    test_message_bus_connection()