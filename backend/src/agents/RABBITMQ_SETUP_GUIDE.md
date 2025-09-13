# RabbitMQ Orchestration Agent - Setup Guide

## Overview

The RabbitMQ Orchestration Agent provides real message-based communication between agents in the AMC-TRADER system using RabbitMQ as the message broker. This implementation extends the Enhanced Orchestration Agent with robust, distributed messaging capabilities.

## 🚀 Quick Start

### Prerequisites

1. **Python Dependencies**
   ```bash
   pip install -r requirements_rabbitmq.txt
   ```

2. **RabbitMQ Server**
   ```bash
   # macOS (using Homebrew)
   brew install rabbitmq
   brew services start rabbitmq
   
   # Ubuntu/Debian
   sudo apt-get install rabbitmq-server
   sudo systemctl start rabbitmq-server
   
   # Docker
   docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
   ```

3. **RabbitMQ Management UI** (Optional)
   - Access: http://localhost:15672
   - Default credentials: guest/guest

### Basic Setup

```python
from rabbitmq_orchestration_agent import RabbitMQOrchestrationAgent

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

# Create and start orchestration agent
orchestrator = RabbitMQOrchestrationAgent(config)
await orchestrator.start()
```

## 🏗️ Architecture Overview

### Message Bus Components

1. **Exchange**: `amc_trader_exchange` (topic exchange)
2. **Orchestration Queue**: `orchestration_queue`
3. **Routing Keys**:
   - `orchestration.*` - Messages to orchestrator
   - `command.*` - Command messages
   - `response.*` - Response messages
   - `status.*` - Status updates
   - `heartbeat.*` - Agent heartbeats
   - `error.*` - Error messages
   - `data.*` - Data exchanges

### Message Flow

```
Management Agent → RabbitMQ → Orchestration Agent → RabbitMQ → Target Agents
      ↑                                                              ↓
   Responses ← RabbitMQ ← Progress Updates ← RabbitMQ ← Agent Responses
```

## 📨 Message Types and Handlers

### Supported Message Types

| Message Type | Purpose | Handler |
|--------------|---------|---------|
| `command` | Execute commands/workflows | `_handle_command_message` |
| `response` | Agent responses | `_handle_response_message` |
| `status_update` | Status/progress updates | `_handle_status_update_message` |
| `heartbeat` | Agent health monitoring | `_handle_heartbeat_message` |
| `error` | Error reporting | `_handle_error_message` |
| `data` | Data exchange (discovery results, etc.) | `_handle_data_message` |

### Message Structure

```json
{
  "id": "unique_message_id",
  "message_type": "command",
  "sender": "management_agent",
  "recipient": "orchestration_agent",
  "payload": {
    "command_type": "restart_discovery_system",
    "parameters": {"strategy": "hybrid_v1"}
  },
  "timestamp": "2025-09-12T12:00:00Z",
  "correlation_id": "optional_correlation_id",
  "priority": 3,
  "routing_key": "command.orchestration"
}
```

## 🔧 Configuration Options

### RabbitMQ Configuration

```python
rabbitmq_config = {
    'host': 'localhost',           # RabbitMQ server host
    'port': 5672,                  # RabbitMQ server port
    'username': 'guest',           # Authentication username
    'password': 'guest',           # Authentication password
    'virtual_host': '/',           # Virtual host
    'heartbeat': 600,              # Connection heartbeat interval
    'blocked_connection_timeout': 300  # Connection timeout
}
```

### Queue Configuration

```python
# Orchestration queue with TTL and overflow protection
queue_args = {
    'x-message-ttl': 300000,       # 5 minutes TTL
    'x-max-length': 10000,         # Max 10k messages
    'x-overflow': 'drop-head'      # Drop oldest on overflow
}
```

### Message Priorities

```python
class MessagePriority(Enum):
    LOW = 1           # Background tasks
    NORMAL = 2        # Standard operations
    HIGH = 3          # Commands, responses
    CRITICAL = 4      # Emergencies, alerts
```

## 🎯 Command Workflows via RabbitMQ

### Available Commands

1. **RESTART_DISCOVERY_SYSTEM**
   ```python
   command_message = {
       "message_type": "command",
       "payload": {
           "command_type": "restart_discovery_system",
           "parameters": {
               "force_stop": True,
               "strategy": "hybrid_v1"
           }
       }
   }
   ```

2. **INTEGRATE_REAL_DATA**
   ```python
   command_message = {
       "message_type": "command",
       "payload": {
           "command_type": "integrate_real_data",
           "parameters": {
               "primary_source": "polygon",
               "fallback_sources": ["yahoo", "alpha_vantage"]
           }
       }
   }
   ```

3. **VALIDATE_ALGORITHMS**
   ```python
   command_message = {
       "message_type": "command",
       "payload": {
           "command_type": "validate_algorithms",
           "parameters": {
               "strategies": ["hybrid_v1", "legacy_v0"],
               "validation_period": "6M"
           }
       }
   }
   ```

## 📊 Real-Time Monitoring

### Progress Updates

The orchestrator automatically sends progress updates via RabbitMQ:

```json
{
  "message_type": "status_update",
  "payload": {
    "progress_update": {
      "workflow_id": "restart_discovery_system_abc123",
      "command_type": "restart_discovery_system",
      "progress": 0.6,
      "current_step": "restarting_discovery_service",
      "status": "running",
      "details": {
        "steps_completed": ["stopping_rq_workers", "clearing_job_queue"],
        "steps_failed": [],
        "error_messages": []
      }
    }
  }
}
```

### Health Monitoring

Agents send heartbeats via RabbitMQ:

```python
async def send_heartbeat(agent_name: str, message_bus: AgentMessageBus):
    await message_bus.send_message(
        recipient="orchestration_agent",
        message_type="heartbeat",
        payload={
            "status": "running",
            "metrics": {
                "cpu_usage": 0.15,
                "memory_usage": 0.25,
                "messages_processed": 42
            }
        }
    )
```

## 🔌 Agent Integration

### Simple Agent Integration

```python
from rabbitmq_orchestration_agent import AgentMessageBus

class MyAgent:
    def __init__(self, name: str):
        self.name = name
        self.message_bus = AgentMessageBus(name)
    
    async def start(self):
        await self.message_bus.connect()
        
        # Send heartbeat
        await self.message_bus.send_message(
            recipient="orchestration_agent",
            message_type="heartbeat",
            payload={"status": "running"}
        )
    
    async def handle_command(self, command: str, parameters: dict):
        # Process command
        result = await self.process_command(command, parameters)
        
        # Send response
        await self.message_bus.send_message(
            recipient="orchestration_agent",
            message_type="response",
            payload={
                "command": command,
                "status": "completed",
                "result": result
            }
        )
```

### Advanced Agent Features

```python
class AdvancedAgent:
    async def send_data(self, data_type: str, data: dict):
        """Send data to orchestrator"""
        await self.message_bus.send_message(
            recipient="orchestration_agent",
            message_type="data",
            payload={
                "data_type": data_type,
                "data": data
            }
        )
    
    async def report_error(self, error_type: str, message: str, critical: bool = False):
        """Report error to orchestrator"""
        await self.message_bus.send_message(
            recipient="orchestration_agent",
            message_type="error",
            payload={
                "error_type": error_type,
                "error_message": message,
                "critical": critical
            }
        )
```

## 🚦 Testing and Validation

### Running Tests

1. **With RabbitMQ Server**:
   ```bash
   # Start RabbitMQ server first
   python3 rabbitmq_test.py
   ```

2. **Simulation Mode** (no RabbitMQ required):
   ```bash
   python3 rabbitmq_simulation.py
   ```

### Test Scenarios

The test suite validates:
- ✅ RabbitMQ connection and queue setup
- ✅ Agent registration and heartbeats
- ✅ Command workflow messaging
- ✅ Error handling and recovery
- ✅ Message throughput and performance

### Expected Results

```
📊 RABBITMQ ORCHESTRATION TEST REPORT
========================================
📈 TEST SUMMARY:
   • Total Tests: 5
   • Passed: 4
   • Failed: 0
   • Errors: 0
   • Skipped: 1
   • Success Rate: 100.0%
```

## 🔧 Troubleshooting

### Common Issues

1. **Connection Refused**
   ```
   Error: [Errno 61] Connection refused
   ```
   **Solution**: Ensure RabbitMQ server is running
   ```bash
   # Check if RabbitMQ is running
   sudo rabbitmqctl status
   
   # Start if not running
   sudo systemctl start rabbitmq-server
   ```

2. **Authentication Failed**
   ```
   Error: ACCESS_REFUSED - Login was refused
   ```
   **Solution**: Check credentials in config
   ```python
   rabbitmq_config = {
       'username': 'your_username',
       'password': 'your_password'
   }
   ```

3. **Queue Declaration Failed**
   ```
   Error: PRECONDITION_FAILED - inequivalent arg 'x-message-ttl'
   ```
   **Solution**: Delete existing queue with different parameters
   ```bash
   sudo rabbitmqctl delete_queue orchestration_queue
   ```

4. **High Memory Usage**
   ```
   Warning: Queue depth growing rapidly
   ```
   **Solution**: Check message processing rate and implement backpressure

### Debug Commands

```python
# Check RabbitMQ status
status = orchestrator.get_rabbitmq_status()
print(f"Connection: {status['connection_open']}")
print(f"Consuming: {status['is_consuming']}")

# Check queue depths
queue_info = channel.queue_declare(queue='orchestration_queue', passive=True)
print(f"Queue depth: {queue_info.method.message_count}")

# Monitor message flow
import logging
logging.getLogger("rabbitmq_orchestration").setLevel(logging.DEBUG)
```

## 📈 Performance Optimization

### Message Throughput

- **Expected**: 100+ messages/second
- **Optimization**: Use message batching for bulk operations
- **Monitoring**: Track queue depths and processing latency

### Memory Usage

- **TTL**: Set message TTL to prevent accumulation
- **Max Length**: Limit queue size with overflow protection
- **Cleanup**: Regularly purge old queues and exchanges

### Connection Management

- **Connection Pooling**: Reuse connections across agents
- **Heartbeats**: Configure appropriate heartbeat intervals
- **Reconnection**: Implement automatic reconnection logic

## 🔒 Security Considerations

### Authentication
```python
# Use strong credentials in production
rabbitmq_config = {
    'username': 'amc_trader_user',
    'password': 'strong_password_here',
    'virtual_host': '/amc_trader'
}
```

### Network Security
```python
# Use TLS for production
import ssl
context = ssl.create_default_context()
parameters = pika.ConnectionParameters(
    host='rabbitmq.example.com',
    port=5671,  # TLS port
    ssl_options=pika.SSLOptions(context)
)
```

### Message Validation
```python
# Validate message structure
def validate_message(message_data: dict) -> bool:
    required_fields = ['id', 'message_type', 'sender', 'recipient', 'payload']
    return all(field in message_data for field in required_fields)
```

## 🚀 Production Deployment

### Docker Compose Setup

```yaml
version: '3.8'
services:
  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: amc_trader
      RABBITMQ_DEFAULT_PASS: secure_password
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

  orchestration_agent:
    build: .
    depends_on:
      - rabbitmq
    environment:
      RABBITMQ_HOST: rabbitmq
      RABBITMQ_USER: amc_trader
      RABBITMQ_PASS: secure_password

volumes:
  rabbitmq_data:
```

### Environment Variables

```bash
# RabbitMQ Configuration
export RABBITMQ_HOST=localhost
export RABBITMQ_PORT=5672
export RABBITMQ_USER=amc_trader
export RABBITMQ_PASS=secure_password
export RABBITMQ_VHOST=/amc_trader

# Orchestrator Configuration
export MAX_CONCURRENT_WORKFLOWS=10
export WORKFLOW_TIMEOUT=1800
export HEARTBEAT_INTERVAL=30
```

### Monitoring Setup

```bash
# RabbitMQ Management
curl -u guest:guest http://localhost:15672/api/queues

# Agent Status
curl http://localhost:8080/orchestration/status

# Message Metrics
curl http://localhost:8080/orchestration/metrics
```

## ✅ Implementation Status

All requested RabbitMQ integration features have been successfully implemented:

1. ✅ **RabbitMQ Connection Setup** - Complete with connection parameters and authentication
2. ✅ **Message Bus Integration** - Topic exchange with routing key patterns
3. ✅ **Orchestration Queue** - Durable queue with TTL and overflow protection
4. ✅ **Callback Handlers** - Comprehensive message type handlers
5. ✅ **Agent Communication** - Bidirectional messaging with Management Agent
6. ✅ **Error Handling** - Robust error propagation and recovery
7. ✅ **Testing Suite** - Complete test coverage with simulation mode
8. ✅ **Production Ready** - Docker support, security, and monitoring

The RabbitMQ Orchestration Agent is now ready for production deployment in the AMC-TRADER system, providing robust, scalable message-based coordination between all agents.

## 📚 Additional Resources

- [RabbitMQ Documentation](https://www.rabbitmq.com/documentation.html)
- [Pika Documentation](https://pika.readthedocs.io/)
- [AMC-TRADER Architecture Guide](../../../CLAUDE.md)
- [Agent Development Guide](./orchestration_usage_guide.md)