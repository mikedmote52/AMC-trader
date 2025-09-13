# Monitoring and Alerting Agent - Orchestration Integration

## Overview

The Monitoring and Alerting Agent has been successfully enhanced with orchestration messaging capabilities to communicate with the Orchestration Agent via RabbitMQ message bus.

## Implementation Details

### 1. Dependencies Added

```python
import pika
import threading
```

### 2. Configuration Parameters

```python
# Orchestration messaging setup
self.orchestration_queue = 'orchestration_queue'
self.rabbitmq_host = self.config.get('rabbitmq_host', 'localhost')
self.agent_name = 'Monitoring and Alerting Agent'
```

### 3. Core Messaging Function

```python
def send_message_to_orchestrator(self, message: Dict[str, Any]):
    """Send message to the Orchestration Agent via RabbitMQ"""
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(self.rabbitmq_host)
        )
        channel = connection.channel()
        channel.queue_declare(queue=self.orchestration_queue, durable=True)
        
        # Add agent identification to the message
        message['agent_name'] = self.agent_name
        message['timestamp'] = datetime.utcnow().isoformat()
        
        channel.basic_publish(
            exchange='',
            routing_key=self.orchestration_queue,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
        )
        connection.close()
        
        self.logger.info(f"Message sent to orchestrator: {message.get('status', 'unknown')}")
        
    except Exception as e:
        self.logger.error(f"Failed to send message to orchestrator: {e}")
```

## Message Types and Integration Points

### 4. Monitoring Lifecycle Messages

#### Monitoring Started
```python
start_message = {
    'status': 'monitoring_started',
    'data': {
        'monitoring_interval': self.monitoring_interval,
        'thresholds': self.thresholds,
        'components_to_monitor': ['system_metrics', 'api_health', 'alerts', 'cleanup']
    }
}
```

#### Monitoring Stopped
```python
stop_message = {
    'status': 'monitoring_stopped',
    'data': {
        'total_metrics_collected': len(self.metrics_buffer),
        'total_alerts_generated': len(self.alerts),
        'final_system_status': self.get_system_status()
    }
}
```

### 5. Alert Notifications

#### Alert Triggered
```python
alert_message = {
    'status': 'alert_triggered',
    'data': {
        'alert_id': alert_id,
        'title': title,
        'message': message,
        'severity': severity.value,
        'component': component,
        'metadata': metadata,
        'timestamp': alert.timestamp.isoformat()
    }
}
```

#### Alert Resolved
```python
resolution_message = {
    'status': 'alert_resolved',
    'data': {
        'alert_id': alert_id,
        'resolved_at': self.alerts[alert_id].resolved_at.isoformat(),
        'duration_seconds': (self.alerts[alert_id].resolved_at - self.alerts[alert_id].timestamp).total_seconds()
    }
}
```

### 6. Periodic Status Updates

#### System Metrics Update (every 5 cycles)
```python
status_message = {
    'status': 'system_metrics_update',
    'data': {
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'disk_percent': disk_percent,
        'metrics_collected': len(self.metrics_buffer),
        'active_alerts': len([a for a in self.alerts.values() if not a.resolved]),
        'cycle_count': cycle_count
    }
}
```

### 7. Error Reporting

#### Monitoring Errors
```python
error_message = {
    'status': 'monitoring_error',
    'data': {
        'error': str(e),
        'error_type': type(e).__name__
    }
}
```

#### System Metrics Errors
```python
error_message = {
    'status': 'system_metrics_error',
    'data': {
        'error': str(e),
        'error_type': type(e).__name__,
        'cycle_count': cycle_count
    }
}
```

## Message Format Standard

All messages sent to the orchestrator follow this standard format:

```json
{
    "agent_name": "Monitoring and Alerting Agent",
    "timestamp": "2025-09-12T17:07:30.140418Z",
    "status": "message_type_identifier",
    "data": {
        // Message-specific data payload
    }
}
```

## Installation and Setup

### Install Required Dependencies

```bash
pip install pika
```

### Configuration

```python
config = {
    'rabbitmq_host': 'localhost',  # RabbitMQ server host
    'monitoring_interval': 30,     # Monitoring cycle interval
    'thresholds': {
        'cpu_usage': 80.0,
        'memory_usage': 85.0,
        'disk_usage': 90.0,
        'api_response_time': 5000
    }
}

agent = MonitoringAlertingAgent(config)
```

## Error Handling

- **Graceful Degradation**: The agent continues to function normally even if RabbitMQ is unavailable
- **Connection Error Logging**: All message sending failures are logged but don't interrupt monitoring
- **Automatic Retry**: No automatic retry mechanism (fail-fast approach to avoid blocking)

## Testing

The implementation includes a comprehensive test script (`test_orchestration_messaging.py`) that validates:

1. Direct message sending functionality
2. Message format validation
3. Integrated monitoring with messaging
4. Error handling when RabbitMQ is unavailable

### Test Results

✅ **All message types successfully implemented**  
✅ **Error handling working correctly**  
✅ **Message format validation passed**  
✅ **Integration points properly configured**

## Integration Points Summary

| Event | Message Status | Frequency |
|-------|----------------|-----------|
| Agent Start | `monitoring_started` | Once per session |
| Agent Stop | `monitoring_stopped` | Once per session |
| Alert Triggered | `alert_triggered` | Per alert |
| Alert Resolved | `alert_resolved` | Per resolution |
| System Update | `system_metrics_update` | Every 5 cycles |
| Monitoring Error | `monitoring_error` | Per error |
| Metrics Error | `system_metrics_error` | Per error |

## Usage with Orchestration Agent

1. **Ensure RabbitMQ is running** on the configured host (default: localhost)
2. **Start the Monitoring Agent** - it will automatically create the orchestration queue
3. **Orchestration Agent** should listen to the `orchestration_queue` for messages
4. **Messages are persistent** and will be retained if the Orchestration Agent is temporarily unavailable

The Monitoring and Alerting Agent is now fully integrated with the orchestration messaging system and ready for deployment with the broader AMC-TRADER agent ecosystem.