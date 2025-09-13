# Enhanced Backtesting Agent - Message Bus Integration

## Overview

The Enhanced Backtesting Agent now includes full RabbitMQ message bus integration for seamless communication with the Orchestration Agent. The system provides real-time status updates, progress notifications, completion alerts, and algorithm weakness warnings.

## Architecture

```
┌─────────────────────┐    RabbitMQ     ┌─────────────────────┐
│  Orchestration      │◄─── Queue ────►│   Backtesting       │
│     Agent           │                 │      Agent          │
└─────────────────────┘                 └─────────────────────┘
          │                                       │
          │ Commands                              │ Messages
          ▼                                       ▼
┌─────────────────────┐                 ┌─────────────────────┐
│ VALIDATE_ALGORITHMS │                 │  Status Updates     │
│   STATUS_CHECK      │                 │  Progress Reports   │
│    SHUTDOWN         │                 │  Completion Alerts  │
└─────────────────────┘                 │  Weakness Warnings  │
                                        └─────────────────────┘
```

## Message Types

### 1. validation_started
Sent when algorithm validation begins.
```json
{
  "message_type": "validation_started",
  "status": "validation_initiated",
  "request_id": "req_12345",
  "data": {
    "strategies": ["hybrid_v1"],
    "parameters": {...},
    "estimated_completion_minutes": 4
  },
  "agent_name": "Backtesting Agent",
  "timestamp": "2025-09-12T17:08:02.860139"
}
```

### 2. validation_progress
Real-time progress updates during validation.
```json
{
  "message_type": "validation_progress",
  "status": "validation_in_progress",
  "request_id": "req_12345",
  "data": {
    "progress_percent": 45.0,
    "current_step": "Backtesting hybrid_v1 with 5-day holding period",
    "timestamp": "2025-09-12T17:08:02.860113"
  }
}
```

### 3. validation_completed
Comprehensive completion notification with summary metrics.
```json
{
  "message_type": "validation_completed",
  "status": "validation_completed",
  "request_id": "req_12345",
  "data": {
    "report_id": "validation_req_12345_20250912_170800",
    "total_backtests": 4,
    "win_rate": 75.0,
    "avg_return": 8.45,
    "sharpe_ratio": 1.23,
    "recommendations_count": 6,
    "algorithm_weaknesses_count": 2,
    "statistical_significance": false,
    "risk_rating": "Medium",
    "symbols_tested": ["PLTR", "SOFI"],
    "report_file_path": "/path/to/validation_report.json"
  }
}
```

### 4. algorithm_weakness_alert
Critical alerts for algorithm performance issues.
```json
{
  "message_type": "algorithm_weakness_alert",
  "status": "weakness_detected",
  "data": {
    "weaknesses": [
      "Low correlation between strategy scores and actual returns",
      "Weak performing subscores need improvement: catalyst, options"
    ],
    "urgency": "high",
    "recommendation": "Algorithm recalibration recommended",
    "affected_components": ["catalyst", "options"]
  }
}
```

### 5. validation_failed
Error notifications with detailed failure information.
```json
{
  "message_type": "validation_failed",
  "status": "validation_failed",
  "request_id": "req_12345",
  "data": {
    "error_message": "API connection timeout",
    "timestamp": "2025-09-12T17:08:03.213409"
  }
}
```

## Installation & Setup

### 1. Install RabbitMQ Dependencies
```bash
# Install pika for Python RabbitMQ integration
pip install pika

# Install RabbitMQ server (choose one):

# macOS with Homebrew:
brew install rabbitmq
brew services start rabbitmq

# Ubuntu/Debian:
sudo apt-get install rabbitmq-server
sudo systemctl start rabbitmq-server

# Docker:
docker run -d --name rabbitmq \
  -p 5672:5672 -p 15672:15672 \
  rabbitmq:3-management
```

### 2. Agent Configuration
```python
from backtesting_agent import EnhancedBacktestingAgent

# Initialize with RabbitMQ settings
agent = EnhancedBacktestingAgent(
    data_dir="../data",
    api_base_url="https://amc-trader.onrender.com",
    rabbitmq_host="localhost",
    orchestration_queue="orchestration_queue"
)
```

## Usage Examples

### Basic Orchestration Workflow

```python
from backtesting_agent import EnhancedBacktestingAgent, Command, CommandType
from datetime import datetime

# 1. Initialize agent
agent = EnhancedBacktestingAgent()

# 2. Start listening for commands
agent.start_listening()

# 3. Send validation command
validation_command = Command(
    type=CommandType.VALIDATE_ALGORITHMS,
    payload={
        'strategies': ['hybrid_v1'],
        'holding_periods': [5, 10],
        'max_candidates': 30,
        'requested_by': 'OrchestrationAgent',
        'priority': 'HIGH'
    },
    timestamp=datetime.now(),
    request_id="validation_001"
)

agent.send_command(validation_command)

# 4. Monitor progress via message bus
# Messages automatically sent to orchestration_queue

# 5. Cleanup
agent.stop_listening()
```

### Message Monitoring (Orchestration Agent Side)

```python
import pika
import json

def setup_message_listener():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='orchestration_queue', durable=True)
    
    def callback(ch, method, properties, body):
        message = json.loads(body)
        handle_backtesting_message(message)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    
    channel.basic_consume(queue='orchestration_queue', on_message_callback=callback)
    channel.start_consuming()

def handle_backtesting_message(message):
    msg_type = message.get('message_type')
    
    if msg_type == 'validation_started':
        print(f"Validation started for {message['data']['strategies']}")
        
    elif msg_type == 'validation_progress':
        progress = message['data']['progress_percent']
        step = message['data']['current_step']
        print(f"Progress: {progress}% - {step}")
        
    elif msg_type == 'validation_completed':
        data = message['data']
        print(f"Validation completed: {data['win_rate']}% win rate")
        
    elif msg_type == 'algorithm_weakness_alert':
        urgency = message['data']['urgency']
        count = len(message['data']['weaknesses'])
        print(f"⚠️ Algorithm weakness detected: {count} issues ({urgency} urgency)")
        
    elif msg_type == 'validation_failed':
        error = message['data']['error_message']
        print(f"❌ Validation failed: {error}")
```

## Fallback Mechanism

When RabbitMQ is unavailable, the system automatically falls back to file-based messaging:

- Messages saved to `../data/orchestrator_message_*.json` files
- Orchestration Agent can monitor directory for new files
- Same message structure maintained
- Automatic detection and graceful degradation

```python
# File-based monitoring example
import glob
import json
import time

def monitor_file_messages():
    seen_files = set()
    
    while True:
        message_files = glob.glob("../data/orchestrator_message_*.json")
        new_files = set(message_files) - seen_files
        
        for file_path in new_files:
            with open(file_path, 'r') as f:
                message = json.load(f)
            handle_backtesting_message(message)
            seen_files.add(file_path)
            
        time.sleep(1)
```

## Error Handling

The message bus integration includes comprehensive error handling:

1. **Connection Failures**: Automatic fallback to file-based messaging
2. **Queue Unavailable**: Graceful degradation with logging
3. **Serialization Errors**: Error messages sent to orchestration
4. **Timeout Handling**: Progress updates with timeout detection

## Key Features

✅ **Real-time Communication**: Live progress updates during validation  
✅ **Comprehensive Notifications**: Start, progress, completion, and failure alerts  
✅ **Algorithm Health Monitoring**: Automatic weakness detection and alerts  
✅ **Robust Fallback**: File-based messaging when RabbitMQ unavailable  
✅ **Structured Messages**: Consistent JSON format for all communications  
✅ **Error Resilience**: Graceful handling of connection and serialization issues  
✅ **Production Ready**: Durable queues, persistent messages, acknowledgments  

## Message Flow Example

```
1. Orchestration Agent → VALIDATE_ALGORITHMS command
2. Backtesting Agent   → validation_started message
3. Backtesting Agent   → validation_progress (20% - Retrieving parameters)
4. Backtesting Agent   → validation_progress (45% - Backtesting strategy)
5. Backtesting Agent   → validation_progress (90% - Generating report)
6. Backtesting Agent   → validation_completed message
7. Backtesting Agent   → algorithm_weakness_alert (if issues found)
```

This comprehensive message bus integration ensures the Orchestration Agent has complete visibility into the backtesting process and can respond to events in real-time.