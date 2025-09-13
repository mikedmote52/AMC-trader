#!/usr/bin/env python3
"""
Message Bus Integration Demo for Enhanced Backtesting Agent

This script demonstrates how the Enhanced Backtesting Agent communicates with
the Orchestration Agent via RabbitMQ message bus.
"""

import time
import json
import threading
from datetime import datetime
from backtesting_agent import EnhancedBacktestingAgent, Command, CommandType

try:
    import pika
    PIKA_AVAILABLE = True
except ImportError:
    PIKA_AVAILABLE = False
    print("⚠️  pika not installed - will demonstrate file-based fallback")

class MockOrchestrationMessageReceiver:
    """Mock message receiver to demonstrate orchestration agent receiving messages"""
    
    def __init__(self, queue_name="orchestration_queue"):
        self.queue_name = queue_name
        self.received_messages = []
        self.listening = False
        
    def start_listening(self):
        """Start listening for messages (with fallback to file-based monitoring)"""
        if PIKA_AVAILABLE:
            self._listen_rabbitmq()
        else:
            self._listen_files()
            
    def _listen_rabbitmq(self):
        """Listen for RabbitMQ messages"""
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
            channel = connection.channel()
            channel.queue_declare(queue=self.queue_name, durable=True)
            
            def callback(ch, method, properties, body):
                message = json.loads(body)
                self.received_messages.append(message)
                print(f"📨 ORCHESTRATION AGENT RECEIVED: {message.get('message_type', 'unknown')}")
                print(f"   Status: {message.get('status')}")
                if message.get('data'):
                    print(f"   Data: {json.dumps(message['data'], indent=4)}")
                print()
                ch.basic_ack(delivery_tag=method.delivery_tag)
                
            channel.basic_consume(queue=self.queue_name, on_message_callback=callback)
            print(f"📡 Orchestration Agent listening on RabbitMQ queue: {self.queue_name}")
            
            # Listen for a limited time in demo
            self.listening = True
            start_time = time.time()
            while self.listening and (time.time() - start_time) < 30:  # 30 second timeout
                connection.process_data_events(time_limit=1)
                
            connection.close()
            
        except Exception as e:
            print(f"❌ RabbitMQ connection failed: {e}")
            print("📁 Falling back to file-based monitoring...")
            self._listen_files()
            
    def _listen_files(self):
        """Monitor file-based messages as fallback"""
        print("📁 Orchestration Agent monitoring file-based messages...")
        import glob
        import os
        
        # Monitor for new message files
        base_path = "../data/orchestrator_message_*.json"
        seen_files = set()
        
        start_time = time.time()
        while time.time() - start_time < 30:  # 30 second timeout
            message_files = glob.glob(base_path)
            new_files = set(message_files) - seen_files
            
            for file_path in new_files:
                try:
                    with open(file_path, 'r') as f:
                        message = json.load(f)
                    self.received_messages.append(message)
                    print(f"📨 ORCHESTRATION AGENT RECEIVED (FILE): {message.get('message_type', 'unknown')}")
                    print(f"   Status: {message.get('status')}")
                    if message.get('data'):
                        print(f"   Data: {json.dumps(message['data'], indent=4)}")
                    print()
                    seen_files.add(file_path)
                except Exception as e:
                    print(f"Error reading message file {file_path}: {e}")
                    
            time.sleep(1)
            
        print("📡 File monitoring completed")
        
    def stop_listening(self):
        """Stop listening for messages"""
        self.listening = False
        
    def get_received_messages(self):
        """Get all received messages"""
        return self.received_messages

def demonstrate_message_integration():
    """Demonstrate complete message bus integration"""
    print("🎭 ENHANCED BACKTESTING AGENT - MESSAGE BUS INTEGRATION DEMO")
    print("="*70)
    
    # Initialize components
    backtesting_agent = EnhancedBacktestingAgent()
    orchestration_receiver = MockOrchestrationMessageReceiver()
    
    # Start orchestration message receiver in background
    receiver_thread = threading.Thread(target=orchestration_receiver.start_listening, daemon=True)
    receiver_thread.start()
    
    print("🚀 Starting Enhanced Backtesting Agent with message bus integration...")
    backtesting_agent.start_listening()
    
    time.sleep(2)  # Allow startup
    
    # Send test validation command
    print("📤 Sending VALIDATE_ALGORITHMS command...")
    test_command = Command(
        type=CommandType.VALIDATE_ALGORITHMS,
        payload={
            'strategies': ['hybrid_v1'],
            'holding_periods': [5, 10],
            'max_candidates': 15,
            'requested_by': 'OrchestrationAgent',
            'priority': 'HIGH'
        },
        timestamp=datetime.now(),
        request_id=f"messagebus_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    backtesting_agent.send_command(test_command)
    
    # Wait for processing to complete
    print("⏳ Waiting for validation to complete...")
    time.sleep(15)  # Allow time for full processing
    
    # Stop services
    backtesting_agent.stop_listening()
    orchestration_receiver.stop_listening()
    
    # Display results
    print("\n" + "="*70)
    print("📊 MESSAGE BUS COMMUNICATION SUMMARY")
    print("="*70)
    
    received_messages = orchestration_receiver.get_received_messages()
    print(f"📨 Total messages received by Orchestration Agent: {len(received_messages)}")
    
    # Categorize messages
    message_types = {}
    for msg in received_messages:
        msg_type = msg.get('message_type', 'unknown')
        if msg_type not in message_types:
            message_types[msg_type] = []
        message_types[msg_type].append(msg)
        
    print("\n📋 Message Types Received:")
    for msg_type, messages in message_types.items():
        print(f"   {msg_type}: {len(messages)} messages")
        
    # Show key message details
    print("\n📝 Key Message Details:")
    for msg in received_messages:
        msg_type = msg.get('message_type')
        status = msg.get('status')
        timestamp = msg.get('timestamp', '')[:19]  # Truncate timestamp
        
        if msg_type == 'validation_started':
            strategies = msg.get('data', {}).get('strategies', [])
            print(f"   🚀 Started: {', '.join(strategies)} at {timestamp}")
            
        elif msg_type == 'validation_progress':
            progress = msg.get('data', {}).get('progress_percent', 0)
            step = msg.get('data', {}).get('current_step', '')
            print(f"   ⏳ Progress: {progress:.1f}% - {step}")
            
        elif msg_type == 'validation_completed':
            data = msg.get('data', {})
            win_rate = data.get('win_rate', 0)
            avg_return = data.get('avg_return', 0)
            recommendations = data.get('recommendations_count', 0)
            print(f"   ✅ Completed: {win_rate}% win rate, {avg_return:.2f}% avg return, {recommendations} recommendations")
            
        elif msg_type == 'algorithm_weakness_alert':
            data = msg.get('data', {})
            urgency = data.get('urgency', 'unknown')
            weakness_count = len(data.get('weaknesses', []))
            print(f"   ⚠️  Weakness Alert: {weakness_count} issues detected (urgency: {urgency})")
            
    print("\n✅ Message Bus Integration Demo Completed!")
    print("\nKey Features Demonstrated:")
    print("✓ RabbitMQ message bus communication")
    print("✓ File-based fallback when RabbitMQ unavailable")
    print("✓ Real-time progress updates")
    print("✓ Validation completion notifications")
    print("✓ Algorithm weakness alerts")
    print("✓ Structured message formats")
    print("✓ Error handling and graceful degradation")

def show_installation_instructions():
    """Show pika installation instructions"""
    print("\n" + "="*70)
    print("📦 PIKA INSTALLATION INSTRUCTIONS")
    print("="*70)
    print("To enable full RabbitMQ integration, install pika:")
    print("   pip install pika")
    print("\nTo install RabbitMQ server:")
    print("   # macOS with Homebrew:")
    print("   brew install rabbitmq")
    print("   brew services start rabbitmq")
    print("\n   # Ubuntu/Debian:")
    print("   sudo apt-get install rabbitmq-server")
    print("   sudo systemctl start rabbitmq-server")
    print("\n   # Docker:")
    print("   docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management")

if __name__ == "__main__":
    if not PIKA_AVAILABLE:
        show_installation_instructions()
        print("\nProceeding with file-based fallback demonstration...\n")
        
    demonstrate_message_integration()