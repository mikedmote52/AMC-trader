#!/usr/bin/env python3
"""
Test script for API Integration Agent orchestration messaging.

This script tests the message bus connection and sends sample messages
to verify the integration with the Orchestration Agent.
"""

import asyncio
import json
import time
from datetime import datetime

from orchestration_messaging import (
    get_orchestration_messenger, 
    MessageType, 
    MessagePriority,
    send_message_to_orchestrator
)


async def test_orchestration_messaging():
    """Test the orchestration messaging system."""
    print("🚀 Testing API Integration Agent Orchestration Messaging")
    print("=" * 60)
    
    try:
        # Get messenger instance
        messenger = get_orchestration_messenger()
        
        # Test 1: Basic status update
        print("\n📤 Test 1: Sending status update...")
        success = messenger.send_status_update(
            status="api_integration_agent_initialized",
            details={
                'components': ['redis_service', 'error_handler', 'performance_monitor'],
                'initialization_time': '245ms',
                'ready_for_requests': True
            }
        )
        print(f"   ✅ Status update sent: {success}")
        
        # Test 2: Completion notification
        print("\n📤 Test 2: Sending completion notification...")
        success = messenger.send_completion_notification(
            task="discovery_contenders_fetch",
            result={
                'candidates_found': 12,
                'strategy': 'hybrid_v1',
                'cache_hit': False,
                'processing_time_ms': 1250
            },
            duration_ms=1250
        )
        print(f"   ✅ Completion notification sent: {success}")
        
        # Test 3: Error alert
        print("\n📤 Test 3: Sending error alert...")
        success = messenger.send_error_alert(
            error_type="redis_connection_timeout",
            error_message="Redis connection timed out after 5 seconds",
            error_details={
                'redis_host': 'localhost',
                'redis_port': 6379,
                'operation': 'get_discovery_data',
                'retry_count': 3
            },
            severity="medium"
        )
        print(f"   ✅ Error alert sent: {success}")
        
        # Test 4: Performance metrics
        print("\n📤 Test 4: Sending performance metrics...")
        success = messenger.send_performance_metrics({
            'avg_response_time_ms': 850,
            'cache_hit_ratio': 0.78,
            'error_rate': 0.02,
            'requests_per_minute': 45,
            'active_connections': 8
        })
        print(f"   ✅ Performance metrics sent: {success}")
        
        # Test 5: Cache update notification
        print("\n📤 Test 5: Sending cache update notification...")
        success = messenger.send_cache_update_notification(
            cache_operation="set",
            cache_key="discovery:contenders:hybrid_v1",
            cache_data={
                'candidates_count': 15,
                'ttl_seconds': 300,
                'data_size_bytes': 4096
            }
        )
        print(f"   ✅ Cache update notification sent: {success}")
        
        # Test 6: Health check
        print("\n📤 Test 6: Sending health check...")
        success = messenger.send_health_check({
            'status': 'healthy',
            'uptime_seconds': 3600,
            'memory_usage_percent': 45,
            'cpu_usage_percent': 12,
            'redis_connected': True,
            'last_error': None
        })
        print(f"   ✅ Health check sent: {success}")
        
        # Test 7: Optimization recommendation
        print("\n📤 Test 7: Sending optimization recommendation...")
        success = messenger.send_optimization_recommendation([
            {
                'recommendation_id': 'opt_001',
                'category': 'caching',
                'priority': 'high',
                'title': 'Increase cache TTL for stable data',
                'description': 'Discovery results are being cached for only 5 minutes. Increase to 15 minutes for better performance.',
                'estimated_impact': '30% reduction in API response time'
            }
        ])
        print(f"   ✅ Optimization recommendation sent: {success}")
        
        # Test 8: Legacy compatibility function
        print("\n📤 Test 8: Testing legacy compatibility function...")
        legacy_message = {
            'status': 'validation_completed',
            'data': {
                'validated_items': 100,
                'invalid_items': 5,
                'validation_time_ms': 450
            },
            'priority': 'normal'
        }
        success = send_message_to_orchestrator(legacy_message)
        print(f"   ✅ Legacy message sent: {success}")
        
        # Test 9: High priority critical alert
        print("\n📤 Test 9: Sending critical alert...")
        success = messenger.send_error_alert(
            error_type="system_overload",
            error_message="API response times exceeding 10 seconds",
            error_details={
                'avg_response_time': 12500,
                'active_requests': 150,
                'memory_usage': 95,
                'immediate_action_required': True
            },
            severity="critical"
        )
        print(f"   ✅ Critical alert sent: {success}")
        
        # Get messaging statistics
        print("\n📊 Messaging Statistics:")
        stats = messenger.get_messaging_statistics()
        for key, value in stats.items():
            print(f"   • {key}: {value}")
        
        print("\n🎉 All tests completed successfully!")
        print("   The API Integration Agent can now communicate with the Orchestration Agent.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        print("   Please check RabbitMQ connection and configuration.")
        return False
    
    finally:
        # Clean up connection
        if 'messenger' in locals():
            messenger.close_connection()
            print("\n🔌 RabbitMQ connection closed.")


async def test_message_flow_simulation():
    """Simulate a typical message flow during API operations."""
    print("\n🔄 Simulating typical API operation message flow...")
    print("-" * 50)
    
    messenger = get_orchestration_messenger()
    
    try:
        # Simulate discovery request flow
        correlation_id = f"test_flow_{int(time.time())}"
        
        # 1. Request started
        messenger.send_status_update(
            status="discovery_request_received",
            details={'endpoint': '/discovery/contenders', 'strategy': 'hybrid_v1'},
            correlation_id=correlation_id
        )
        print("1. ✅ Request received notification sent")
        
        await asyncio.sleep(0.1)  # Simulate processing delay
        
        # 2. Cache miss detected
        messenger.send_status_update(
            status="cache_miss_detected",
            details={'cache_key': 'discovery:contenders:hybrid_v1'},
            correlation_id=correlation_id
        )
        print("2. ✅ Cache miss notification sent")
        
        await asyncio.sleep(0.2)  # Simulate discovery processing
        
        # 3. Discovery completed
        messenger.send_completion_notification(
            task="discovery_analysis",
            result={'candidates_found': 8, 'processing_time_ms': 850},
            duration_ms=850,
            correlation_id=correlation_id
        )
        print("3. ✅ Discovery completion sent")
        
        # 4. Cache updated
        messenger.send_cache_update_notification(
            cache_operation="set",
            cache_key="discovery:contenders:hybrid_v1",
            cache_data={'candidates_count': 8, 'ttl': 300},
            correlation_id=correlation_id
        )
        print("4. ✅ Cache update notification sent")
        
        # 5. Response delivered
        messenger.send_completion_notification(
            task="api_response_delivered",
            result={'total_time_ms': 920, 'cache_populated': True},
            duration_ms=920,
            correlation_id=correlation_id
        )
        print("5. ✅ Response delivery confirmation sent")
        
        print(f"\n🔗 All messages sent with correlation ID: {correlation_id}")
        
    except Exception as e:
        print(f"❌ Flow simulation error: {str(e)}")
    
    finally:
        messenger.close_connection()


def main():
    """Main test function."""
    print("API Integration Agent - Orchestration Messaging Test")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Check if pika is available
    try:
        import pika
        print("✅ pika library is available")
    except ImportError:
        print("❌ pika library not found. Install with: pip install pika")
        return
    
    # Run tests
    asyncio.run(test_orchestration_messaging())
    asyncio.run(test_message_flow_simulation())


if __name__ == "__main__":
    main()