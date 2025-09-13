# Discovery Algorithm Agent - Message Bus Integration

## Overview

The Discovery Algorithm Agent now includes **RabbitMQ message bus integration** for seamless communication with the Orchestration Agent. This enables real-time command processing and status reporting across the distributed agent system.

## Prerequisites

### Install RabbitMQ Server
```bash
# macOS
brew install rabbitmq
brew services start rabbitmq

# Ubuntu/Debian
sudo apt-get install rabbitmq-server
sudo systemctl start rabbitmq-server

# CentOS/RHEL
sudo yum install rabbitmq-server
sudo systemctl start rabbitmq-server
```

### Install Python Dependencies
```bash
pip install pika>=1.3.0
```

## Message Bus Architecture

### Queue Configuration
- **Orchestration Queue**: `orchestration_queue` - Messages TO orchestrator
- **Discovery Queue**: `discovery_queue` - Commands FROM orchestrator
- **Connection**: `localhost:5672` (default RabbitMQ port)

### Message Format
```json
{
  "agent_name": "Discovery Algorithm Agent",
  "timestamp": "2025-09-12T17:00:00Z",
  "status": "discovery_completed",
  "data": {
    "total_candidates": 2,
    "trade_ready_count": 0,
    "watchlist_count": 2
  }
}
```

## Usage Examples

### 1. Enable Message Bus Communication
```bash
# Standard deployment with message bus
python3 discovery_algorithm_agent.py DEPLOY --message-bus

# Test message sending
python3 discovery_algorithm_agent.py MESSAGE-TEST --message-bus

# Listen for orchestrator commands
python3 discovery_algorithm_agent.py LISTEN --message-bus
```

### 2. Deployment Script with Message Bus
```bash
# Manual deployment with orchestrator communication
./deploy_discovery.sh MANUAL --message-bus

# Start command listener daemon
./deploy_discovery.sh LISTEN --message-bus

# Test connectivity
./deploy_discovery.sh MESSAGE-TEST --message-bus
```

## Message Types Sent to Orchestrator

### 1. Agent Status Messages
```json
{
  "status": "agent_online",
  "data": {
    "agent_type": "Discovery Algorithm Agent",
    "capabilities": ["stock_discovery", "investment_filtering", "real_time_data"],
    "version": "1.0"
  }
}
```

### 2. Deployment Lifecycle
```json
// Deployment Start
{
  "status": "deployment_started",
  "data": {
    "deployment_time": "2025-09-12T17:00:00Z",
    "data_source": "file_based",
    "message_bus_enabled": true
  }
}

// Deployment Complete
{
  "status": "deployment_completed", 
  "data": {
    "completion_time": "2025-09-12T17:01:30Z",
    "candidates_found": 2,
    "success": true
  }
}
```

### 3. Discovery Process Updates
```json
// Discovery Started
{
  "status": "discovery_started",
  "data": {
    "strategy": "hybrid_v1",
    "limit": 50,
    "data_source": "file_based"
  }
}

// Discovery Completed
{
  "status": "discovery_completed",
  "data": {
    "total_candidates": 2,
    "trade_ready_count": 0,
    "watchlist_count": 2,
    "strategy_used": "hybrid_v1",
    "candidates": [
      {
        "symbol": "PLTR",
        "score": 72.6,
        "action_tag": "watchlist",
        "price": 42.15,
        "volume": 38000000
      }
    ]
  }
}
```

### 4. Investment Opportunities
```json
// Investment Opportunities Found
{
  "status": "investment_opportunities_found",
  "data": {
    "total_candidates": 2,
    "trade_ready_count": 0,
    "watchlist_count": 2,
    "top_recommendations": [
      {
        "symbol": "PLTR",
        "price": 42.15,
        "score": 72.6,
        "action_tag": "watchlist",
        "volume": 38000000,
        "market_cap": 89000000000
      }
    ]
  }
}

// No Opportunities
{
  "status": "no_investment_opportunities",
  "data": {
    "reason": "No stocks met investment criteria in current market conditions",
    "filters_applied": {
      "min_price": 1.0,
      "max_price": 1000.0,
      "min_volume": 500000,
      "min_market_cap": 50000000
    }
  }
}
```

### 5. Error Handling
```json
// Discovery Failed
{
  "status": "discovery_failed",
  "error": "API connection timeout",
  "data": {
    "strategy": "hybrid_v1",
    "limit": 50
  }
}

// Command Failed
{
  "status": "command_failed",
  "data": {
    "command": "INVALID_COMMAND",
    "error": "Command processing failed: INVALID_COMMAND"
  }
}
```

## Commands Received from Orchestrator

The agent listens for these commands on the `discovery_queue`:

### 1. INTEGRATE_REAL_DATA
Switches the agent to use live market data sources
```json
{
  "command": "INTEGRATE_REAL_DATA"
}
```

### 2. DISCOVER_STOCKS  
Triggers immediate stock discovery process
```json
{
  "command": "DISCOVER_STOCKS"
}
```

### 3. SET_STRATEGY
Changes the discovery strategy
```json
{
  "command": "SET_STRATEGY:hybrid_v1"
}
```

## Production Deployment

### 1. Service Configuration
```bash
# Create systemd service for command listener
sudo nano /etc/systemd/system/discovery-agent-listener.service
```

```ini
[Unit]
Description=Discovery Algorithm Agent Command Listener
After=rabbitmq-server.service

[Service]
Type=simple
User=trader
WorkingDirectory=/path/to/AMC-TRADER/backend/src/agents
ExecStart=/usr/bin/python3 discovery_algorithm_agent.py LISTEN --message-bus
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2. Scheduled Deployments with Message Bus
```bash
# Cron entry for market hours deployment with orchestrator communication
*/30 9-16 * * 1-5 /path/to/deploy_discovery.sh AUTO --message-bus

# Extended hours with reduced frequency
0 4-8,17-20 * * 1-5 /path/to/deploy_discovery.sh AUTO --message-bus
```

### 3. Health Monitoring
```bash
# Check RabbitMQ status
sudo rabbitmqctl status

# List queues
sudo rabbitmqctl list_queues

# Monitor message flow
sudo rabbitmqctl list_consumers
```

## Error Handling & Reliability

### 1. Connection Resilience
- Automatic connection retry with exponential backoff
- Graceful degradation to file-based commands if message bus unavailable
- Persistent message queues survive service restarts

### 2. Message Persistence
- Messages marked as persistent (`delivery_mode=2`)
- Queue durability ensures messages survive RabbitMQ restarts
- Manual acknowledgment prevents message loss

### 3. Fallback Mechanisms
```python
# Agent automatically falls back to file-based commands if:
# 1. pika library not installed
# 2. RabbitMQ server unavailable  
# 3. Connection timeout occurs
# 4. Message bus explicitly disabled
```

## Integration Testing

### 1. Basic Connectivity Test
```bash
./deploy_discovery.sh MESSAGE-TEST --message-bus
```

### 2. End-to-End Command Flow
```bash
# Terminal 1: Start listener
./deploy_discovery.sh LISTEN --message-bus

# Terminal 2: Send test command (from orchestrator simulation)
python3 -c "
import pika, json
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.queue_declare(queue='discovery_queue', durable=True)
message = {'command': 'DISCOVER_STOCKS'}
channel.basic_publish(exchange='', routing_key='discovery_queue', body=json.dumps(message))
connection.close()
print('Test command sent')
"
```

### 3. Monitor Message Flow
```bash
# Check orchestration queue for agent messages
sudo rabbitmqctl list_queue_bindings orchestration_queue

# Monitor real-time message flow
sudo rabbitmq-plugins enable rabbitmq_management
# Access web UI at http://localhost:15672 (guest/guest)
```

## Performance Considerations

- **Message Throughput**: ~1000 messages/second typical
- **Latency**: <50ms for local RabbitMQ instance
- **Memory Usage**: +10-20MB per agent for message bus overhead
- **Network**: Minimal bandwidth (~1KB per message average)

The message bus integration provides robust, scalable communication between the Discovery Algorithm Agent and Orchestration Agent while maintaining backward compatibility with file-based operation modes.