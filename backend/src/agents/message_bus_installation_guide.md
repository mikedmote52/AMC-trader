# 🔌 RabbitMQ Message Bus Integration Guide
*Management Agent ↔ Orchestration Agent Communication*

## 📋 Overview

The AMC-TRADER Management Agent now includes **comprehensive RabbitMQ message bus integration** enabling seamless communication with the Orchestration Agent. This allows for real-time status updates, automated command execution, and system-wide coordination.

---

## 🛠️ Installation Requirements

### **1. Install RabbitMQ Server**

#### **macOS (Homebrew)**
```bash
# Install RabbitMQ
brew install rabbitmq

# Start RabbitMQ server
brew services start rabbitmq

# Or start manually
/opt/homebrew/sbin/rabbitmq-server
```

#### **Ubuntu/Debian**
```bash
# Install RabbitMQ
sudo apt-get update
sudo apt-get install rabbitmq-server

# Start RabbitMQ service
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server
```

#### **Docker (Recommended for Development)**
```bash
# Run RabbitMQ with management UI
docker run -d --name rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  rabbitmq:3-management

# Access management UI at http://localhost:15672
# Default credentials: guest/guest
```

### **2. Install Python Dependencies**
```bash
# Install pika library for RabbitMQ integration
pip install pika

# Verify installation
python -c "import pika; print('✅ Pika installed successfully')"
```

---

## 🎯 Message Bus Integration Features

### **Message Types Supported**
1. **Status Updates** - Real-time system health metrics
2. **Command Requests** - Automated action execution requests  
3. **Alert Notifications** - System alerts and warnings
4. **Health Reports** - Comprehensive system analysis
5. **Completion Notifications** - Task completion status
6. **Error Alerts** - Critical error notifications
7. **Automated Action Triggers** - Rule-based automation triggers

### **Integration Points**
- **Management Agent** sends messages to `orchestration_queue`
- **Automatic reconnection** handling for reliable messaging
- **Message priority** and persistence for critical communications
- **Error handling** with graceful degradation if message bus unavailable

---

## 🔧 Configuration & Setup

### **1. Test Message Bus Connection**
```bash
# Navigate to agents directory
cd /Users/michaelmote/Desktop/AMC-TRADER/backend/src/agents

# Run message bus integration test
python message_bus_integration.py
```

**Expected Output:**
```
🔌 Testing Message Bus Connection...
✅ Connected to RabbitMQ successfully
✅ Test message sent successfully
✅ Message bus integration test completed
```

### **2. Run Message Bus Demo**
```bash
# Comprehensive demonstration of all message types
python message_bus_demo.py
```

### **3. Integration with Management Agent**
```python
# The Management Agent automatically initializes message bus integration
# Messages are sent at key execution points:

# 1. Health check completion → Status update message
# 2. Alert creation → Alert notification message  
# 3. Automated action trigger → Command request message
# 4. Report generation → Health report message
# 5. Task completion → Completion notification message
```

---

## 📤 Message Examples

### **Status Update Message**
```json
{
  "message_type": "status_update",
  "agent_name": "Management Agent",
  "timestamp": "2025-09-12T17:15:30.123456",
  "priority": "medium",
  "data": {
    "system_health": "degraded",
    "api_response_time": 5.2,
    "discovery_candidates": 8,
    "error_rate": 0.03,
    "scoring_strategy": "hybrid_v1"
  }
}
```

### **Command Request Message**
```json
{
  "message_type": "command_request",
  "agent_name": "Management Agent", 
  "timestamp": "2025-09-12T17:15:30.123456",
  "priority": "critical",
  "data": {
    "command": "RESTART_DISCOVERY_SYSTEM",
    "parameters": {
      "triggered_by_rule": "discovery_system_failure",
      "automated": true
    },
    "correlation_id": "auto_discovery_system_failure_1726178130"
  }
}
```

### **Alert Notification Message**
```json
{
  "message_type": "alert_notification",
  "agent_name": "Management Agent",
  "timestamp": "2025-09-12T17:15:30.123456", 
  "priority": "high",
  "data": {
    "alert_level": "CRITICAL",
    "component": "discovery_system",
    "message": "Discovery system failure detected - no candidates for 30+ minutes",
    "alert_timestamp": "2025-09-12T17:15:30.123456"
  }
}
```

---

## 🔍 Monitoring & Debugging

### **RabbitMQ Management UI**
- **URL**: http://localhost:15672
- **Default Credentials**: guest/guest
- **Monitor**: Queue status, message rates, connections

### **Queue Information**
- **Primary Queue**: `orchestration_queue` (persistent)
- **Response Queue**: `management_responses` (for future bidirectional communication)
- **Message TTL**: Configurable (default: persistent)

### **Debugging Commands**
```bash
# Check RabbitMQ status
sudo systemctl status rabbitmq-server

# View RabbitMQ logs
sudo journalctl -u rabbitmq-server -f

# List queues
sudo rabbitmqctl list_queues

# Purge queue (if needed for testing)
sudo rabbitmqctl purge_queue orchestration_queue
```

---

## 🚀 Production Deployment

### **Environment Variables**
```bash
# RabbitMQ Configuration
export RABBITMQ_HOST=localhost
export RABBITMQ_PORT=5672
export RABBITMQ_USER=guest
export RABBITMQ_PASS=guest

# Message Bus Settings
export MESSAGE_BUS_ENABLED=true
export MESSAGE_QUEUE_NAME=orchestration_queue
export MESSAGE_PERSISTENCE=true
```

### **High Availability Setup**
```bash
# For production, consider RabbitMQ cluster
docker run -d --name rabbitmq-node1 \
  -p 5672:5672 \
  -p 15672:15672 \
  -e RABBITMQ_ERLANG_COOKIE=secret_cookie \
  rabbitmq:3-management
```

### **Security Considerations**
- Use dedicated RabbitMQ user accounts (not guest)
- Enable SSL/TLS for production
- Configure firewall rules for port 5672
- Implement message signing for sensitive commands

---

## 📊 Performance Metrics

### **Message Throughput**
- **Target Rate**: 100+ messages/second
- **Latency**: <10ms for local RabbitMQ
- **Queue Depth**: Monitor to prevent backlog

### **Connection Monitoring**
- **Automatic Reconnection**: Implemented with exponential backoff
- **Connection Pooling**: Available for high-volume scenarios
- **Health Checks**: Integrated with Management Agent monitoring

---

## 🎯 Integration Verification

### **Step 1: Verify RabbitMQ**
```bash
# Check RabbitMQ is running
curl -u guest:guest http://localhost:15672/api/overview
```

### **Step 2: Test Message Bus**
```bash
python message_bus_integration.py
```

### **Step 3: Run Management Agent**
```bash
python management_agent.py
```

### **Step 4: Monitor Messages**
```bash
# View RabbitMQ management UI
open http://localhost:15672

# Check orchestration_queue for messages
```

---

## 🔄 Message Flow Architecture

```
┌─────────────────┐    📤 Messages    ┌──────────────┐    📥 Commands    ┌─────────────────┐
│ Management      │ ────────────────► │   RabbitMQ   │ ────────────────► │ Orchestration   │
│ Agent           │                   │   Message    │                   │ Agent           │
│                 │ ◄──────────────── │   Bus        │ ◄──────────────── │                 │
└─────────────────┘    📤 Status      └──────────────┘    📥 Results     └─────────────────┘

Message Types:
• Status Updates → Real-time health metrics
• Command Requests → Automated action triggers  
• Alert Notifications → System warnings/errors
• Health Reports → Comprehensive analysis
• Completion Notifications → Task status
• Error Alerts → Critical failures
```

---

## ✅ Verification Checklist

- [ ] **RabbitMQ installed and running**
- [ ] **Pika library installed**
- [ ] **Message bus integration test passes**
- [ ] **Management Agent initializes message bus successfully**
- [ ] **Messages appear in RabbitMQ management UI**
- [ ] **Orchestration queue receiving messages**
- [ ] **Error handling works when RabbitMQ unavailable**

---

## 🎉 Success Indicators

### **✅ Integration Working Correctly**
- Management Agent logs show "Message bus integration initialized successfully"
- Messages appear in RabbitMQ orchestration_queue
- No connection errors in logs
- System continues operating if RabbitMQ unavailable

### **📈 Performance Targets**
- Message delivery < 10ms latency
- Zero message loss for critical alerts
- Automatic reconnection within 30 seconds
- Queue depth remains manageable (<1000 messages)

---

**🤖 Enhanced Management Agent with RabbitMQ Message Bus Integration Complete ✅**

*The Management Agent now provides seamless communication with the Orchestration Agent through robust, scalable messaging infrastructure.*