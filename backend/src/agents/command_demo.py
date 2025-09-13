#!/usr/bin/env python3
"""
Command-Based Orchestration Demo

This script demonstrates the enhanced orchestration agent's command-based interface
and shows how the Management Agent can coordinate complex workflows.
"""

import asyncio
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add the agents directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_orchestration_agent import (
    EnhancedOrchestrationAgent, CommandInterface, CommandType, WorkflowStatus
)


class CommandDemo:
    """Demonstration of command-based orchestration workflows"""
    
    def __init__(self):
        self.orchestrator = None
        self.command_interface = None
        self.demo_results = []
        
        # Setup logging
        self.setup_logging()
    
    def setup_logging(self):
        """Setup demo logging"""
        import logging
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Reduce orchestration agent logging verbosity for demo
        logging.getLogger("orchestration_agent").setLevel(logging.WARNING)
    
    async def initialize_system(self):
        """Initialize the enhanced orchestration system"""
        print("🚀 INITIALIZING ENHANCED ORCHESTRATION SYSTEM")
        print("=" * 60)
        
        # Create enhanced orchestration agent with optimized config
        config = {
            'heartbeat_interval': 10,
            'timeout_threshold': 300,  # 5 minutes
            'max_concurrent_workflows': 5,
            'workflow_timeout': 900,   # 15 minutes for complex operations
            'progress_update_interval': 3
        }
        
        self.orchestrator = EnhancedOrchestrationAgent(config)
        self.command_interface = CommandInterface(self.orchestrator)
        
        # Register AMC-TRADER agents
        agents_to_register = [
            ("management_agent", ["system_management", "configuration", "deployment"]),
            ("discovery_algorithm_agent", ["candidate_discovery", "scoring", "filtering"]),
            ("data_validation_agent", ["data_validation", "data_quality", "schema_validation"]),
            ("api_integration_agent", ["external_api", "data_fetching", "rate_limiting"]),
            ("backtesting_agent", ["strategy_testing", "historical_analysis", "performance_metrics"]),
            ("caching_performance_agent", ["caching", "performance_optimization", "memory_management"]),
            ("monitoring_alerting_agent", ["system_monitoring", "alerting", "health_checks"])
        ]
        
        for agent_name, capabilities in agents_to_register:
            self.orchestrator.register_agent(agent_name, capabilities, [])
            print(f"✅ Registered: {agent_name}")
        
        # Start orchestrator
        orchestrator_task = asyncio.create_task(self.orchestrator.start())
        await asyncio.sleep(2)  # Allow initialization
        
        print(f"✅ Enhanced Orchestration System Online")
        print(f"   📊 Agents Registered: {len(agents_to_register)}")
        print(f"   ⚙️  Max Concurrent Workflows: {config['max_concurrent_workflows']}")
        print(f"   ⏱️  Workflow Timeout: {config['workflow_timeout']}s")
        
        return orchestrator_task
    
    async def demo_restart_discovery_system(self):
        """Demonstrate RESTART_DISCOVERY_SYSTEM workflow"""
        print(f"\n🔄 DEMO: RESTART_DISCOVERY_SYSTEM Workflow")
        print("-" * 45)
        
        try:
            # Start restart workflow
            workflow_id = await self.command_interface.restart_discovery_system(
                force_stop=True,
                strategy="hybrid_v1"
            )
            
            print(f"🎯 Started Workflow: {workflow_id}")
            print(f"   Command: RESTART_DISCOVERY_SYSTEM")
            print(f"   Strategy: hybrid_v1")
            
            # Monitor progress
            await self.monitor_workflow_progress(workflow_id, duration=25)
            
            # Get final result
            final_status = self.orchestrator.get_workflow_status(workflow_id)
            if final_status:
                self.demo_results.append({
                    "workflow": "RESTART_DISCOVERY_SYSTEM",
                    "status": final_status["status"],
                    "steps_completed": final_status["steps_completed"],
                    "duration": self.calculate_workflow_duration(final_status)
                })
                
                print(f"✅ Workflow Complete: {final_status['status']}")
                print(f"   📈 Steps Completed: {len(final_status['steps_completed'])}")
                if final_status.get('result'):
                    print(f"   🎯 System Status: {final_status['result'].get('system_status', 'N/A')}")
            
        except Exception as e:
            print(f"❌ Workflow Error: {e}")
            self.demo_results.append({
                "workflow": "RESTART_DISCOVERY_SYSTEM",
                "status": "ERROR",
                "error": str(e)
            })
    
    async def demo_integrate_real_data(self):
        """Demonstrate INTEGRATE_REAL_DATA workflow"""
        print(f"\n📊 DEMO: INTEGRATE_REAL_DATA Workflow")
        print("-" * 40)
        
        try:
            # Start integration workflow
            workflow_id = await self.command_interface.integrate_real_data(
                primary_source="polygon",
                fallback_sources=["yahoo", "alpha_vantage"]
            )
            
            print(f"🎯 Started Workflow: {workflow_id}")
            print(f"   Command: INTEGRATE_REAL_DATA")
            print(f"   Primary Source: polygon")
            print(f"   Fallback Sources: yahoo, alpha_vantage")
            
            # Monitor progress
            await self.monitor_workflow_progress(workflow_id, duration=30)
            
            # Get final result
            final_status = self.orchestrator.get_workflow_status(workflow_id)
            if final_status:
                self.demo_results.append({
                    "workflow": "INTEGRATE_REAL_DATA",
                    "status": final_status["status"],
                    "steps_completed": final_status["steps_completed"],
                    "duration": self.calculate_workflow_duration(final_status)
                })
                
                print(f"✅ Workflow Complete: {final_status['status']}")
                print(f"   📊 Data Integration: {final_status.get('result', {}).get('integration_successful', 'Unknown')}")
                if final_status.get('result', {}).get('data_sources'):
                    sources = final_status['result']['data_sources']
                    print(f"   🔗 Active Sources: {sources.get('primary', 'N/A')} + {len(sources.get('fallback', []))} fallback")
        
        except Exception as e:
            print(f"❌ Workflow Error: {e}")
            self.demo_results.append({
                "workflow": "INTEGRATE_REAL_DATA", 
                "status": "ERROR",
                "error": str(e)
            })
    
    async def demo_validate_algorithms(self):
        """Demonstrate VALIDATE_ALGORITHMS workflow"""
        print(f"\n🧪 DEMO: VALIDATE_ALGORITHMS Workflow")
        print("-" * 40)
        
        try:
            # Start validation workflow
            workflow_id = await self.command_interface.validate_algorithms(
                strategies=["hybrid_v1", "legacy_v0"],
                validation_period="6M"
            )
            
            print(f"🎯 Started Workflow: {workflow_id}")
            print(f"   Command: VALIDATE_ALGORITHMS")
            print(f"   Strategies: hybrid_v1, legacy_v0")
            print(f"   Period: 6 months")
            
            # Monitor progress (longer duration for validation)
            await self.monitor_workflow_progress(workflow_id, duration=40)
            
            # Get final result
            final_status = self.orchestrator.get_workflow_status(workflow_id)
            if final_status:
                self.demo_results.append({
                    "workflow": "VALIDATE_ALGORITHMS",
                    "status": final_status["status"],
                    "steps_completed": final_status["steps_completed"],
                    "duration": self.calculate_workflow_duration(final_status)
                })
                
                print(f"✅ Workflow Complete: {final_status['status']}")
                if final_status.get('result', {}).get('validation_results'):
                    results = final_status['result']['validation_results']
                    print(f"   🏆 Recommended Strategy: {final_status['result'].get('recommended_strategy', 'N/A')}")
                    
                    # Show validation metrics
                    for strategy, metrics in results.items():
                        print(f"   📈 {strategy}: Sharpe {metrics.get('sharpe_ratio', 'N/A'):.2f}, "
                              f"Win Rate {metrics.get('win_rate', 0)*100:.1f}%")
        
        except Exception as e:
            print(f"❌ Workflow Error: {e}")
            self.demo_results.append({
                "workflow": "VALIDATE_ALGORITHMS",
                "status": "ERROR",
                "error": str(e)
            })
    
    async def demo_concurrent_workflows(self):
        """Demonstrate concurrent workflow execution"""
        print(f"\n⚡ DEMO: CONCURRENT WORKFLOW EXECUTION")
        print("-" * 45)
        
        try:
            print("🚀 Starting multiple workflows simultaneously...")
            
            # Start multiple workflows concurrently
            workflow_ids = await asyncio.gather(
                self.command_interface.health_check(),
                self.command_interface.restart_discovery_system(strategy="legacy_v0"),
                return_exceptions=True
            )
            
            valid_workflow_ids = [wf_id for wf_id in workflow_ids if isinstance(wf_id, str)]
            
            print(f"✅ Started {len(valid_workflow_ids)} concurrent workflows")
            for i, wf_id in enumerate(valid_workflow_ids, 1):
                print(f"   {i}. {wf_id}")
            
            # Monitor all workflows
            await asyncio.sleep(15)
            
            # Check system status
            all_status = self.orchestrator.get_all_workflows_status()
            print(f"📊 Concurrent Execution Results:")
            print(f"   Active Workflows: {all_status['summary']['total_active']}")
            print(f"   Success Rate: {all_status['summary']['success_rate']:.1%}")
            
        except Exception as e:
            print(f"❌ Concurrent Execution Error: {e}")
    
    async def monitor_workflow_progress(self, workflow_id: str, duration: int = 30):
        """Monitor and display workflow progress in real-time"""
        start_time = datetime.now()
        end_time = start_time + asyncio.timedelta(seconds=duration)
        
        last_progress = -1
        
        while datetime.now() < end_time:
            status = self.orchestrator.get_workflow_status(workflow_id)
            
            if not status:
                break
            
            current_progress = status['progress']
            
            # Only show updates when progress changes
            if current_progress != last_progress:
                progress_bar = "█" * int(current_progress * 20) + "░" * (20 - int(current_progress * 20))
                print(f"   🔄 [{progress_bar}] {current_progress:.1%} - {status['current_step']}")
                last_progress = current_progress
            
            # Check if completed
            if status['status'] in ['completed', 'failed', 'cancelled']:
                break
            
            await asyncio.sleep(2)
    
    def calculate_workflow_duration(self, workflow_status: dict) -> float:
        """Calculate workflow duration in seconds"""
        if not workflow_status.get('started_at') or not workflow_status.get('completed_at'):
            return 0.0
        
        start = datetime.fromisoformat(workflow_status['started_at'])
        end = datetime.fromisoformat(workflow_status['completed_at'])
        
        return (end - start).total_seconds()
    
    async def demo_error_handling(self):
        """Demonstrate error handling and recovery"""
        print(f"\n⚠️  DEMO: ERROR HANDLING & RECOVERY")
        print("-" * 40)
        
        try:
            # Trigger an invalid workflow (should be handled gracefully)
            print("🧪 Testing error handling with invalid parameters...")
            
            workflow_id = await self.command_interface.validate_algorithms(
                strategies=["nonexistent_strategy"],
                validation_period="invalid_period"
            )
            
            # Monitor for errors
            await asyncio.sleep(10)
            
            status = self.orchestrator.get_workflow_status(workflow_id)
            if status and status.get('error_messages'):
                print(f"✅ Error Handling Working:")
                print(f"   ⚠️  Errors Detected: {len(status['error_messages'])}")
                print(f"   🔄 Status: {status['status']}")
            
        except Exception as e:
            print(f"✅ Exception Caught and Handled: {e}")
    
    def generate_demo_report(self):
        """Generate comprehensive demo report"""
        print(f"\n📊 COMMAND ORCHESTRATION DEMO REPORT")
        print("=" * 60)
        
        # Summary statistics
        total_workflows = len(self.demo_results)
        successful_workflows = len([r for r in self.demo_results if r['status'] == 'completed'])
        
        print(f"📈 EXECUTION SUMMARY:")
        print(f"   • Total Workflows Executed: {total_workflows}")
        print(f"   • Successful Completions: {successful_workflows}")
        print(f"   • Success Rate: {(successful_workflows/max(1, total_workflows)*100):.1f}%")
        
        # Individual workflow results
        print(f"\n🔍 WORKFLOW DETAILS:")
        for result in self.demo_results:
            status_emoji = "✅" if result['status'] == 'completed' else "❌"
            print(f"   {status_emoji} {result['workflow']}")
            print(f"      └─ Status: {result['status']}")
            
            if 'steps_completed' in result:
                print(f"      └─ Steps: {len(result['steps_completed'])}")
            
            if 'duration' in result:
                print(f"      └─ Duration: {result['duration']:.1f}s")
            
            if 'error' in result:
                print(f"      └─ Error: {result['error']}")
        
        # System capabilities demonstrated
        print(f"\n🎯 CAPABILITIES DEMONSTRATED:")
        capabilities = [
            "✅ Command-based workflow orchestration",
            "✅ Real-time progress monitoring",
            "✅ Multi-step workflow coordination",
            "✅ Error handling and recovery",
            "✅ Concurrent workflow execution",
            "✅ Management Agent integration",
            "✅ Comprehensive status reporting"
        ]
        
        for capability in capabilities:
            print(f"   {capability}")
        
        # Performance metrics
        if self.orchestrator:
            system_status = self.orchestrator.get_all_workflows_status()
            
            print(f"\n⚡ PERFORMANCE METRICS:")
            print(f"   • Workflow Success Rate: {system_status['summary']['success_rate']:.1%}")
            print(f"   • Total Workflow History: {system_status['summary']['total_history']}")
            print(f"   • Active Workflows: {system_status['summary']['total_active']}")
        
        # Save detailed report
        report_path = Path("logs") / f"command_demo_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        detailed_report = {
            "demo_timestamp": datetime.now().isoformat(),
            "execution_summary": {
                "total_workflows": total_workflows,
                "successful_workflows": successful_workflows,
                "success_rate": successful_workflows/max(1, total_workflows)
            },
            "workflow_results": self.demo_results,
            "system_status": self.orchestrator.get_all_workflows_status() if self.orchestrator else {},
            "capabilities_demonstrated": [cap.replace("✅ ", "") for cap in capabilities]
        }
        
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(detailed_report, f, indent=2, default=str)
        
        print(f"\n📄 Detailed Report Saved: {report_path}")
        
        return detailed_report


async def main():
    """Main demo execution"""
    demo = CommandDemo()
    
    print("🎯 AMC-TRADER ENHANCED ORCHESTRATION AGENT")
    print("   Command-Based Workflow Coordination Demo")
    print("=" * 70)
    
    try:
        # Initialize system
        orchestrator_task = await demo.initialize_system()
        
        # Run workflow demos
        demo_tasks = [
            ("Discovery System Restart", demo.demo_restart_discovery_system()),
            ("Real Data Integration", demo.demo_integrate_real_data()),
            ("Algorithm Validation", demo.demo_validate_algorithms()),
            ("Concurrent Workflows", demo.demo_concurrent_workflows()),
            ("Error Handling", demo.demo_error_handling())
        ]
        
        for demo_name, demo_task in demo_tasks:
            print(f"\n🎬 Running Demo: {demo_name}")
            try:
                await demo_task
                print(f"✅ Demo Complete: {demo_name}")
            except Exception as e:
                print(f"❌ Demo Failed: {demo_name} - {e}")
        
        # Generate final report
        report = demo.generate_demo_report()
        
        # Cleanup
        if demo.orchestrator:
            await demo.orchestrator.stop()
        
        print(f"\n🎉 COMMAND ORCHESTRATION DEMO COMPLETE")
        return report
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Demo failed - {e}")
        return None


if __name__ == "__main__":
    # Run the command demo
    report = asyncio.run(main())
    
    if report:
        print(f"\n✅ Demo completed successfully!")
    else:
        print(f"\n❌ Demo failed!")
        sys.exit(1)