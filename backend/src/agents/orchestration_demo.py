#!/usr/bin/env python3
"""
Orchestration Agent Demo - Demonstrates VALIDATE_ALGORITHMS Command

This script shows how an Orchestration Agent would interact with the Enhanced Backtesting Agent
to perform comprehensive algorithm validation.
"""

import time
import json
from datetime import datetime
from backtesting_agent import EnhancedBacktestingAgent, Command, CommandType

class MockOrchestrationAgent:
    """Mock Orchestration Agent for demonstration"""
    
    def __init__(self):
        self.backtesting_agent = EnhancedBacktestingAgent()
        
    def trigger_algorithm_validation(self, strategies=['hybrid_v1'], holding_periods=[5, 10], max_candidates=30):
        """Trigger comprehensive algorithm validation"""
        print("🚀 ORCHESTRATION AGENT: Initiating Algorithm Validation")
        print(f"   Strategies to validate: {strategies}")
        print(f"   Holding periods: {holding_periods} days")
        print(f"   Max candidates: {max_candidates}")
        print()
        
        # Start the backtesting agent listener
        print("📡 Starting Backtesting Agent listener...")
        self.backtesting_agent.start_listening()
        time.sleep(1)  # Allow startup
        
        # Send VALIDATE_ALGORITHMS command
        validation_command = Command(
            type=CommandType.VALIDATE_ALGORITHMS,
            payload={
                'strategies': strategies,
                'holding_periods': holding_periods,
                'max_candidates': max_candidates,
                'requested_by': 'OrchestrationAgent',
                'priority': 'HIGH'
            },
            timestamp=datetime.now(),
            request_id=f"orchestration_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        print(f"📨 Sending VALIDATE_ALGORITHMS command (Request ID: {validation_command.request_id})")
        self.backtesting_agent.send_command(validation_command)
        
        # Monitor progress
        print("⏳ Waiting for validation to complete...")
        self._monitor_validation_progress(validation_command.request_id)
        
        # Retrieve and display results
        self._display_validation_results(validation_command.request_id)
        
        # Cleanup
        self.backtesting_agent.stop_listening()
        print("✅ Algorithm validation workflow completed")
        
    def _monitor_validation_progress(self, request_id):
        """Monitor validation progress with status checks"""
        max_wait_time = 30  # seconds
        check_interval = 2
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            # Send status check
            status_command = Command(
                type=CommandType.STATUS_CHECK,
                payload={'request_id': request_id},
                timestamp=datetime.now(),
                request_id=f"status_check_{datetime.now().strftime('%H%M%S')}"
            )
            
            self.backtesting_agent.send_command(status_command)
            time.sleep(check_interval)
            
            # Check if validation completed
            if self.backtesting_agent.status.value == "COMPLETED":
                print("✅ Validation completed successfully!")
                break
            elif self.backtesting_agent.status.value == "FAILED":
                print("❌ Validation failed!")
                break
            else:
                print(f"⏳ Status: {self.backtesting_agent.status.value}")
                
            elapsed_time += check_interval
            
    def _display_validation_results(self, request_id):
        """Display comprehensive validation results"""
        print("\n" + "="*80)
        print("📊 ALGORITHM VALIDATION RESULTS")
        print("="*80)
        
        try:
            # Read confirmation file
            confirmation_file = self.backtesting_agent.data_dir / f"confirmation_{request_id}.json"
            if confirmation_file.exists():
                with open(confirmation_file, 'r') as f:
                    confirmation = json.load(f)
                    
                print(f"🎯 Request ID: {confirmation['request_id']}")
                print(f"📅 Completed: {confirmation['timestamp']}")
                print(f"📈 Status: {confirmation['status']}")
                
                if confirmation['status'] == 'SUCCESS':
                    summary = confirmation['summary']
                    print(f"🔬 Total Backtests: {summary['total_backtests']}")
                    print(f"🏆 Win Rate: {summary['win_rate']}%")
                    print(f"💰 Average Return: {summary['avg_return']}%")
                    print(f"💡 Recommendations: {summary['recommendations_count']}")
                    
                    # Read detailed report
                    report_id = confirmation['report_id']
                    report_file = self.backtesting_agent.validation_reports_dir / f"{report_id}.json"
                    
                    if report_file.exists():
                        with open(report_file, 'r') as f:
                            report = json.load(f)
                            
                        print(f"\n📋 DETAILED ANALYSIS:")
                        print(f"   Algorithm Strategy: {report['algorithm_parameters']['strategy']}")
                        print(f"   Symbols Tested: {', '.join(report['backtest_summary']['symbols_tested'])}")
                        print(f"   Average Holding Period: {report['backtest_summary']['avg_holding_period']} days")
                        
                        print(f"\n🎯 ALGORITHM WEAKNESSES IDENTIFIED:")
                        for weakness in report['algorithm_analysis']['algorithm_weaknesses']:
                            print(f"   ⚠️  {weakness}")
                            
                        print(f"\n🔧 OPTIMIZATION RECOMMENDATIONS:")
                        for i, rec in enumerate(report['recommendations'], 1):
                            print(f"   {i}. {rec}")
                            
                        print(f"\n📊 RISK METRICS:")
                        risk = report['risk_metrics']
                        print(f"   📉 Value at Risk (95%): {risk['value_at_risk_95']}%")
                        print(f"   📉 Max Drawdown: {risk['max_drawdown']}%")
                        print(f"   📊 Volatility: {risk['volatility']}%")
                        print(f"   🚨 Risk Rating: {risk['risk_rating']}")
                        
                        print(f"\n🧪 STATISTICAL SIGNIFICANCE:")
                        stats = report['statistical_significance']
                        print(f"   📊 Sample Size: {stats['sample_size']}")
                        print(f"   📈 Mean Return: {stats['mean_return']}%")
                        print(f"   🎯 Confidence Level: {stats['confidence_level']}")
                        print(f"   ✅ Statistically Significant: {stats['statistically_significant']}")
                        
        except Exception as e:
            print(f"❌ Error reading validation results: {e}")
            
        print("="*80)

def main():
    """Demonstrate Orchestration Agent triggering algorithm validation"""
    print("🎭 AMC-TRADER ORCHESTRATION DEMO")
    print("Demonstrating Enhanced Backtesting Agent Integration")
    print("="*60)
    
    # Initialize mock orchestration agent
    orchestration = MockOrchestrationAgent()
    
    # Example 1: Standard validation
    print("\n🔬 SCENARIO 1: Standard Algorithm Validation")
    orchestration.trigger_algorithm_validation(
        strategies=['hybrid_v1'],
        holding_periods=[5, 10],
        max_candidates=20
    )
    
    print("\n" + "="*60)
    print("✅ Orchestration Demo Completed!")
    print("\nKey Features Demonstrated:")
    print("✓ Command-based orchestration interface")
    print("✓ Real-time status monitoring")
    print("✓ Comprehensive algorithm analysis")
    print("✓ Automated weakness detection")
    print("✓ Optimization recommendations")
    print("✓ Statistical significance testing")
    print("✓ Risk metric calculation")
    print("✓ Structured report generation")
    print("✓ Confirmation callbacks to orchestration")

if __name__ == "__main__":
    main()