#!/usr/bin/env python3
"""
Mock message bus for testing Caching Performance Agent messaging without RabbitMQ
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass
import threading
import queue

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Message data structure for the mock bus"""
    agent_name: str
    status: str
    data: Dict[str, Any]
    timestamp: str
    message_id: str = None


class MockMessageBus:
    """Mock message bus that simulates RabbitMQ functionality"""
    
    def __init__(self):
        self.messages = queue.Queue()
        self.message_history = []
        self.connected = True
        self.message_counter = 0
        self.lock = threading.Lock()
    
    def send_message(self, message: Dict[str, Any]) -> bool:
        """Send a message to the mock bus"""
        try:
            with self.lock:
                self.message_counter += 1
                
                msg = Message(
                    agent_name=message.get('agent_name', 'Unknown'),
                    status=message.get('status', 'unknown'),
                    data=message.get('data', {}),
                    timestamp=message.get('timestamp', datetime.now().isoformat()),
                    message_id=f"msg_{self.message_counter:06d}"
                )
                
                self.messages.put(msg)
                self.message_history.append(msg)
                
                logger.info(f"Mock message bus received: {msg.status} from {msg.agent_name}")
                return True
                
        except Exception as e:
            logger.error(f"Mock message bus error: {e}")
            return False
    
    def get_messages(self) -> List[Message]:
        """Get all received messages"""
        messages = []
        while not self.messages.empty():
            try:
                messages.append(self.messages.get_nowait())
            except queue.Empty:
                break
        return messages
    
    def get_message_history(self) -> List[Message]:
        """Get complete message history"""
        return self.message_history.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get message bus statistics"""
        return {
            'total_messages': len(self.message_history),
            'pending_messages': self.messages.qsize(),
            'connected': self.connected,
            'message_types': self._get_message_type_counts()
        }
    
    def _get_message_type_counts(self) -> Dict[str, int]:
        """Count messages by status type"""
        counts = {}
        for msg in self.message_history:
            counts[msg.status] = counts.get(msg.status, 0) + 1
        return counts
    
    def clear(self):
        """Clear all messages"""
        with self.lock:
            while not self.messages.empty():
                try:
                    self.messages.get_nowait()
                except queue.Empty:
                    break
            self.message_history.clear()
            self.message_counter = 0


# Global mock message bus instance
mock_bus = MockMessageBus()


def send_message_to_orchestrator_mock(message: Dict[str, Any]) -> bool:
    """Mock version of send_message_to_orchestrator for testing"""
    try:
        # Add agent identification to message (same as real implementation)
        message['agent_name'] = 'Caching Performance Agent'
        message['timestamp'] = datetime.now().isoformat()
        
        # Send to mock bus instead of RabbitMQ
        return mock_bus.send_message(message)
        
    except Exception as e:
        logger.error(f"Failed to send mock message: {e}")
        return False


def test_mock_message_bus():
    """Test the mock message bus functionality"""
    
    print("=" * 60)
    print("MOCK MESSAGE BUS TEST")
    print("=" * 60)
    
    # Clear any existing messages
    mock_bus.clear()
    
    print("\n1. TESTING BASIC MESSAGE SENDING")
    print("-" * 40)
    
    # Test basic messages
    test_messages = [
        {
            'status': 'agent_initialized',
            'data': {'redis_connected': True, 'data_path': '/test/path'}
        },
        {
            'status': 'cache_operation_completed',
            'data': {'operation': 'cache_write', 'cache_key': 'test_key', 'success': True}
        },
        {
            'status': 'performance_monitoring_completed',
            'data': {'hit_ratio': 0.85, 'alert_count': 0}
        }
    ]
    
    successful_sends = 0
    for i, msg in enumerate(test_messages):
        if send_message_to_orchestrator_mock(msg):
            successful_sends += 1
            print(f"✅ Message {i+1} sent successfully: {msg['status']}")
        else:
            print(f"❌ Message {i+1} failed: {msg['status']}")
    
    print(f"\nMessages sent: {successful_sends}/{len(test_messages)}")
    
    print("\n2. CHECKING MESSAGE RECEPTION")
    print("-" * 40)
    
    # Check received messages
    received_messages = mock_bus.get_messages()
    print(f"✅ Received {len(received_messages)} messages")
    
    for msg in received_messages:
        print(f"   - {msg.status} from {msg.agent_name} (ID: {msg.message_id})")
    
    print("\n3. MESSAGE BUS STATISTICS")
    print("-" * 40)
    
    stats = mock_bus.get_stats()
    print(f"✅ Total messages processed: {stats['total_messages']}")
    print(f"✅ Pending messages: {stats['pending_messages']}")
    print(f"✅ Connection status: {'Connected' if stats['connected'] else 'Disconnected'}")
    
    print("\nMessage type distribution:")
    for msg_type, count in stats['message_types'].items():
        print(f"   - {msg_type}: {count}")
    
    print("\n4. MESSAGE HISTORY ANALYSIS")
    print("-" * 40)
    
    history = mock_bus.get_message_history()
    if history:
        print(f"✅ Message history contains {len(history)} messages")
        
        # Show detailed info for first and last message
        if len(history) >= 1:
            first_msg = history[0]
            print(f"   First message: {first_msg.status} at {first_msg.timestamp}")
        
        if len(history) >= 2:
            last_msg = history[-1]
            print(f"   Last message: {last_msg.status} at {last_msg.timestamp}")
    
    print("\n" + "=" * 60)
    print("MOCK MESSAGE BUS TEST COMPLETED")
    print("=" * 60)
    
    success_rate = successful_sends / len(test_messages)
    if success_rate >= 1.0:
        print("✅ All mock message bus tests passed!")
        return True
    else:
        print(f"⚠️  Mock message bus test success rate: {success_rate:.1%}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_mock_message_bus()