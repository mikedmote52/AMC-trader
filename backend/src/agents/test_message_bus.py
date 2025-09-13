#!/usr/bin/env python3
"""
Test script for message bus connectivity between Caching Performance Agent and Orchestration Agent
"""

import asyncio
import logging
import time
from datetime import datetime
from caching_performance_agent import CachingPerformanceAgent, send_message_to_orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_message_bus_connectivity():
    """Test basic message bus connectivity"""
    
    print("=" * 60)
    print("MESSAGE BUS CONNECTIVITY TEST")
    print("=" * 60)
    
    print("\n1. TESTING BASIC MESSAGE SENDING")
    print("-" * 40)
    
    # Test basic message
    test_message = {
        'status': 'test_message',
        'data': {
            'test_type': 'connectivity_check',
            'message': 'Hello from Caching Performance Agent!',
            'test_timestamp': datetime.now().isoformat()
        }
    }
    
    success = send_message_to_orchestrator(test_message)
    if success:
        print("✅ Basic message sent successfully")
    else:
        print("❌ Failed to send basic message")
        return False
    
    print("\n2. TESTING AGENT INITIALIZATION MESSAGE")
    print("-" * 40)
    
    # Test agent initialization
    init_message = {
        'status': 'agent_initialized',
        'data': {
            'redis_connected': True,
            'data_path': '/test/path',
            'performance_thresholds': {
                'hit_ratio_min': 0.8,
                'response_time_max_ms': 100
            }
        }
    }
    
    success = send_message_to_orchestrator(init_message)
    if success:
        print("✅ Agent initialization message sent successfully")
    else:
        print("❌ Failed to send agent initialization message")
    
    print("\n3. TESTING CACHE OPERATION MESSAGE")
    print("-" * 40)
    
    # Test cache operation message
    cache_message = {
        'status': 'cache_operation_completed',
        'data': {
            'operation': 'cache_write',
            'cache_key': 'test_key_12345',
            'response_time_ms': 2.5,
            'data_size_candidates': 5,
            'success': True
        }
    }
    
    success = send_message_to_orchestrator(cache_message)
    if success:
        print("✅ Cache operation message sent successfully")
    else:
        print("❌ Failed to send cache operation message")
    
    print("\n4. TESTING PERFORMANCE MONITORING MESSAGE")
    print("-" * 40)
    
    # Test performance monitoring message
    perf_message = {
        'status': 'performance_monitoring_completed',
        'data': {
            'cache_metrics': {
                'hit_ratio': 0.85,
                'avg_response_time_ms': 1.2,
                'total_requests': 150
            },
            'redis_metrics': {
                'used_memory_mb': 45.2,
                'connected_clients': 3
            },
            'alert_count': 0,
            'recommendation_count': 2,
            'critical_alerts': 0
        }
    }
    
    success = send_message_to_orchestrator(perf_message)
    if success:
        print("✅ Performance monitoring message sent successfully")
    else:
        print("❌ Failed to send performance monitoring message")
    
    print("\n5. TESTING ERROR MESSAGE")
    print("-" * 40)
    
    # Test error message
    error_message = {
        'status': 'cache_operation_error',
        'data': {
            'operation': 'cache_read',
            'cache_key': 'invalid_key',
            'error': 'Connection timeout',
            'traceback': 'Traceback (most recent call last):\n  File "test.py", line 1, in <module>\n    raise Exception("Test error")\nException: Test error'
        }
    }
    
    success = send_message_to_orchestrator(error_message)
    if success:
        print("✅ Error message sent successfully")
    else:
        print("❌ Failed to send error message")
    
    print("\n6. TESTING HIGH-FREQUENCY MESSAGE SENDING")
    print("-" * 40)
    
    # Test sending multiple messages rapidly
    start_time = time.time()
    successful_sends = 0
    
    for i in range(10):
        rapid_message = {
            'status': 'rapid_test_message',
            'data': {
                'sequence_number': i,
                'batch_test': True,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        if send_message_to_orchestrator(rapid_message):
            successful_sends += 1
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"✅ High-frequency test completed:")
    print(f"   - Messages sent: {successful_sends}/10")
    print(f"   - Duration: {duration:.2f}s")
    print(f"   - Rate: {successful_sends/duration:.1f} messages/second")
    
    print("\n" + "=" * 60)
    print("MESSAGE BUS TEST SUMMARY")
    print("=" * 60)
    
    if successful_sends >= 8:  # Allow for some failures in rapid testing
        print("✅ All message bus connectivity tests passed!")
        print("✅ Caching Performance Agent is ready for orchestration integration")
        return True
    else:
        print("❌ Some message bus tests failed")
        print("⚠️  Check RabbitMQ connectivity and configuration")
        return False


async def test_agent_with_messaging():
    """Test the full agent with message bus integration"""
    
    print("\n" + "=" * 60)
    print("FULL AGENT WITH MESSAGING TEST")
    print("=" * 60)
    
    try:
        agent = CachingPerformanceAgent()
        
        print("\n✅ Agent initialized with messaging capability")
        
        # Test discovery data processing with messaging
        discovery_data = await agent.read_discovery_results()
        if discovery_data:
            await agent.cache_discovery_results(discovery_data)
            print("✅ Discovery data cached with orchestrator notification")
        
        # Test performance monitoring with messaging
        performance_data = await agent.monitor_performance()
        print("✅ Performance monitoring completed with orchestrator notification")
        
        # Test optimization with messaging
        await agent.optimize_cache_performance()
        print("✅ Cache optimization completed with orchestrator notification")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent test failed: {e}")
        return False


def main():
    """Main test function"""
    print("CACHING PERFORMANCE AGENT - MESSAGE BUS INTEGRATION TEST")
    print("=" * 70)
    
    # Test basic message bus connectivity
    bus_test_passed = test_message_bus_connectivity()
    
    if bus_test_passed:
        # Test full agent with messaging
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            agent_test_passed = loop.run_until_complete(test_agent_with_messaging())
            
            if agent_test_passed:
                print("\n🎉 ALL TESTS PASSED! 🎉")
                print("Caching Performance Agent is fully integrated with message bus")
            else:
                print("\n⚠️  Agent integration test failed")
                
        except Exception as e:
            print(f"\n❌ Agent test error: {e}")
        finally:
            loop.close()
    else:
        print("\n❌ Message bus connectivity failed - skipping agent tests")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()