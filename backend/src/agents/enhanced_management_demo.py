"""
Enhanced Management Agent Demo with Automated Decision-Making

This script demonstrates the advanced Management Agent with rule-based automation,
orchestration command execution, and comprehensive system oversight.
"""

import asyncio
import logging
import json
from datetime import datetime
from management_agent import ManagementAgent, SystemHealth, AlertLevel

async def demonstrate_enhanced_management():
    """Demonstrate the enhanced Management Agent capabilities"""
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🤖 Enhanced Management Agent with Automated Decision-Making")
    print("=" * 60)
    
    # Initialize Management Agent
    agent = ManagementAgent()
    
    print("\n📋 TASK 1: System Health Assessment")
    print("-" * 40)
    
    # Perform initial health check
    metrics = await agent.perform_health_check()
    print(f"System Health: {metrics.system_health.value}")
    print(f"Discovery Candidates: {metrics.discovery_candidates_count}")
    print(f"API Response Time: {metrics.api_response_time:.2f}s")
    print(f"Active Strategy: {metrics.scoring_strategy}")
    
    print("\n📋 TASK 2: Data Integrity Validation")
    print("-" * 40)
    
    await agent.validate_data_integrity()
    data_alerts = [a for a in agent.alerts if a.component == "data_integrity"]
    if data_alerts:
        latest_alert = data_alerts[-1]
        print(f"Data Integrity Alert: {latest_alert.message}")
    else:
        print("✅ Data integrity validation completed - no issues detected")
    
    print("\n📋 TASK 3: Decision Rule Evaluation")
    print("-" * 40)
    
    # Manually trigger rule evaluation to demonstrate functionality
    await agent._evaluate_decision_rules()
    
    print("Decision Rules Status:")
    for rule_name, rule_config in agent.decision_rules.items():
        timer_status = "⏱️  ACTIVE" if rule_name in agent.rule_timers else "⏸️  INACTIVE"
        print(f"  • {rule_name}: {timer_status}")
        print(f"    - Timeout: {rule_config['timeout_minutes']} minutes")
        print(f"    - Action: {rule_config['action']}")
        print(f"    - Priority: {rule_config['priority']}")
        
        if rule_name in agent.rule_timers:
            time_remaining = agent._get_time_remaining(rule_name, rule_config)
            print(f"    - Time Remaining: {time_remaining}")
    
    print("\n📋 TASK 4: Automated Action Logging")
    print("-" * 40)
    
    if agent.automated_actions_log:
        print("Recent Automated Actions:")
        for action in agent.automated_actions_log[-5:]:
            print(f"  • {action['timestamp']}: {action['message']}")
    else:
        print("No automated actions logged yet")
    
    print("\n📋 TASK 5: Comprehensive System Report")
    print("-" * 40)
    
    # Generate comprehensive report with automation insights
    report = await agent.generate_comprehensive_report()
    
    print("System Overview:")
    print(f"  • Health: {report['system_overview']['health']}")
    print(f"  • Active Strategy: {report['system_overview']['active_strategy']}")
    print(f"  • Active Preset: {report['system_overview']['active_preset']}")
    
    print(f"\nAutomation Status:")
    automation = report.get('automation_status', {})
    print(f"  • Active Rules: {automation.get('active_rules', 0)}")
    print(f"  • Rules with Timers: {automation.get('rules_with_timers', [])}")
    
    orchestration_status = automation.get('orchestration_status', {})
    if orchestration_status.get('is_running'):
        print(f"  • Orchestration: ✅ RUNNING")
        print(f"  • Queued Commands: {orchestration_status.get('queued_commands', 0)}")
        print(f"  • Active Commands: {orchestration_status.get('active_commands', 0)}")
    else:
        print(f"  • Orchestration: ❌ NOT RUNNING")
    
    print(f"\nActive Alerts:")
    active_alerts = report.get('active_alerts', [])
    if active_alerts:
        for alert in active_alerts[-3:]:  # Show last 3 alerts
            level_str = str(alert['level'])
            level = level_str.split('.')[-1] if '.' in level_str else level_str
            print(f"  • [{level}] {alert['component']}: {alert['message']}")
    else:
        print("  • No active alerts")
    
    print(f"\nRecommendations:")
    for rec in report.get('recommendations', [])[:3]:
        print(f"  • {rec}")
    
    print("\n📋 TASK 6: Trigger Test Automated Actions")
    print("-" * 40)
    
    # Initialize orchestration agent for demo
    if not agent.orchestration_agent:
        from orchestration_agent import OrchestrationAgent
        agent.orchestration_agent = OrchestrationAgent()
    
    # Simulate automated action triggering
    print("Triggering test automated actions...")
    
    # Test HEALTH_CHECK command
    from orchestration_agent import CommandPriority
    cmd_id = await agent.orchestration_agent.execute_command(
        "HEALTH_CHECK", 
        {"test_mode": True}, 
        CommandPriority.HIGH
    )
    print(f"✅ Health check command queued: {cmd_id}")
    
    # Process the command
    await agent.orchestration_agent._process_command_queue()
    await asyncio.sleep(2)
    
    # Check command status
    status = await agent.orchestration_agent.get_command_status(cmd_id)
    if status:
        print(f"Command Status: {status['status']}")
        if status.get('result'):
            print(f"Result: Command executed successfully")
    
    print("\n📋 TASK 7: System Performance Monitoring")
    print("-" * 40)
    
    performance = report.get('performance_metrics', {})
    if performance:
        print("Performance Metrics:")
        print(f"  • Average Response Time: {performance.get('avg_response_time', 0):.2f}s")
        print(f"  • Average Candidates: {performance.get('avg_candidates', 0):.1f}")
        print(f"  • Error Rate: {performance.get('current_error_rate', 0):.1%}")
        print(f"  • Uptime: {performance.get('uptime_percentage', 0):.1f}%")
    else:
        print("Performance metrics not yet available")
    
    print("\n🎯 AUTOMATED DECISION-MAKING DEMONSTRATION COMPLETE")
    print("=" * 60)
    
    print("\n🔄 Rule-Based Scenarios Configured:")
    print("  1. Discovery System Failure → Restart Discovery (30min timeout)")
    print("  2. Data Integrity Compromised → Integrate Real Data (60min timeout)")  
    print("  3. Algorithm Quality Issues → Validate Algorithms (45min timeout)")
    print("  4. High Error Rate → Emergency Restart (15min timeout)")
    
    print("\n🎛️  Management Agent Features:")
    print("  ✅ Continuous health monitoring")
    print("  ✅ Automated decision-making with rule-based triggers")
    print("  ✅ Orchestration command execution")
    print("  ✅ Real-time anomaly detection")
    print("  ✅ Comprehensive system reporting")
    print("  ✅ Workflow execution monitoring")
    print("  ✅ Audit trail for automated actions")
    
    return agent

async def run_continuous_monitoring_demo():
    """Demonstrate continuous monitoring with decision-making"""
    
    print("\n🔄 Starting Continuous Monitoring Demo (30 seconds)")
    print("-" * 50)
    
    agent = ManagementAgent()
    
    # Initialize orchestration
    if not agent.orchestration_agent:
        from orchestration_agent import OrchestrationAgent
        agent.orchestration_agent = OrchestrationAgent()
        # Start orchestration in background
        asyncio.create_task(agent.orchestration_agent.start_orchestration())
    
    # Run monitoring for 30 seconds
    start_time = asyncio.get_event_loop().time()
    
    while asyncio.get_event_loop().time() - start_time < 30:
        try:
            # Perform core monitoring tasks
            await agent.perform_health_check()
            await agent.validate_data_integrity()
            await agent._evaluate_decision_rules()
            
            # Show real-time status
            print(f"⏱️  {datetime.now().strftime('%H:%M:%S')} - Monitoring cycle complete")
            
            if agent.rule_timers:
                print(f"   Active rule timers: {list(agent.rule_timers.keys())}")
            
            recent_alerts = [a for a in agent.alerts[-3:] if (datetime.now() - a.timestamp).total_seconds() < 60]
            if recent_alerts:
                print(f"   Recent alerts: {len(recent_alerts)}")
            
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"   ⚠️  Error in monitoring cycle: {e}")
            await asyncio.sleep(5)
    
    print(f"\n📊 Monitoring Summary:")
    print(f"   Health Checks: {len(agent.metrics_history)}")
    print(f"   Total Alerts: {len(agent.alerts)}")
    print(f"   Automated Actions: {len(agent.automated_actions_log)}")
    
    return agent

if __name__ == "__main__":
    print("🚀 AMC-TRADER Enhanced Management Agent Demo")
    print("=" * 60)
    
    # Run the demonstration
    agent = asyncio.run(demonstrate_enhanced_management())
    
    # Optionally run continuous monitoring demo
    response = input("\n🤔 Run continuous monitoring demo? (y/n): ")
    if response.lower() == 'y':
        asyncio.run(run_continuous_monitoring_demo())
    
    print("\n✅ Enhanced Management Agent demonstration complete!")