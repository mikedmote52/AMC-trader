#!/usr/bin/env python3
"""
Guardrail Monitor - Prevents silent regressions
Monitors zero candidates and cycle time over budget
"""

import requests
import json
import time
import os
from datetime import datetime
from typing import Dict

class GuardrailMonitor:
    """Monitor system health and trigger alerts on issues"""
    
    def __init__(self, base_url: str = "https://amc-trader.onrender.com"):
        self.base_url = base_url
        self.alert_email = os.getenv('ALERT_EMAIL')
        self.slack_webhook = os.getenv('SLACK_WEBHOOK')
        
        # Thresholds
        self.max_zero_candidates_minutes = 10  # Alert if 0 candidates for >10 min
        self.max_cycle_time_ms = 20000  # 20 second cycle time budget
        self.max_slow_cycles = 3  # Alert after 3 consecutive slow cycles
        
        # State tracking
        self.zero_candidates_start = None
        self.slow_cycles_count = 0
        
    def check_health(self) -> Dict:
        """Get current system health"""
        try:
            response = requests.get(f"{self.base_url}/discovery/health", timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                return {'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'error': str(e)}
    
    def check_candidates(self) -> Dict:
        """Get current candidates count"""
        try:
            response = requests.get(f"{self.base_url}/discovery/candidates?limit=1", timeout=30)
            if response.status_code == 200:
                data = response.json()
                return {
                    'count': data.get('count', 0),
                    'cached': data.get('cached', False),
                    'updated_at': data.get('updated_at'),
                    'duration_ms': data.get('duration_ms', 0)
                }
            else:
                return {'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'error': str(e)}
    
    def send_alert(self, message: str, level: str = "warning"):
        """Send alert via available channels"""
        alert_data = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message,
            'service': 'AMC-TRADER Discovery'
        }
        
        print(f"🚨 ALERT [{level.upper()}]: {message}")
        
        # Send to Slack if configured
        if self.slack_webhook:
            try:
                slack_payload = {
                    'text': f"🚨 AMC-TRADER Alert [{level.upper()}]",
                    'attachments': [{
                        'color': 'danger' if level == 'critical' else 'warning',
                        'fields': [
                            {'title': 'Message', 'value': message, 'short': False},
                            {'title': 'Time', 'value': alert_data['timestamp'], 'short': True},
                            {'title': 'Service', 'value': 'AMC-TRADER Discovery', 'short': True}
                        ]
                    }]
                }
                requests.post(self.slack_webhook, json=slack_payload, timeout=10)
                print("✅ Alert sent to Slack")
            except Exception as e:
                print(f"❌ Failed to send Slack alert: {e}")
        
        # Log to file for debugging
        try:
            with open('/tmp/amc_trader_alerts.log', 'a') as f:
                f.write(json.dumps(alert_data) + '\n')
        except Exception as e:
            print(f"❌ Failed to log alert: {e}")
    
    def check_zero_candidates_alert(self, candidates_data: Dict):
        """Check for zero candidates during market hours"""
        count = candidates_data.get('count', 0)
        current_time = datetime.now()
        
        # Check if it's during trading hours (9:30 AM - 4:00 PM ET)
        # Simple check - in production, use proper timezone handling
        hour = current_time.hour
        is_market_hours = 9 <= hour <= 16  # Rough approximation
        
        if count == 0 and is_market_hours:
            if self.zero_candidates_start is None:
                self.zero_candidates_start = current_time
                print(f"⚠️ Zero candidates detected at {current_time}")
            else:
                # Check how long we've had zero candidates
                zero_duration_minutes = (current_time - self.zero_candidates_start).total_seconds() / 60
                
                if zero_duration_minutes > self.max_zero_candidates_minutes:
                    self.send_alert(
                        f"Zero candidates for {zero_duration_minutes:.1f} minutes during market hours. "
                        f"Possible calibration or data issue. Last update: {candidates_data.get('updated_at', 'unknown')}",
                        level="critical"
                    )
                    # Reset to avoid spam
                    self.zero_candidates_start = current_time
        else:
            # Reset if we have candidates again
            if self.zero_candidates_start is not None:
                zero_duration_minutes = (current_time - self.zero_candidates_start).total_seconds() / 60
                print(f"✅ Zero candidates resolved after {zero_duration_minutes:.1f} minutes")
                self.zero_candidates_start = None
    
    def check_cycle_time_alert(self, candidates_data: Dict):
        """Check for cycle time over budget"""
        duration_ms = candidates_data.get('duration_ms', 0)
        
        if duration_ms > self.max_cycle_time_ms:
            self.slow_cycles_count += 1
            print(f"⚠️ Slow cycle: {duration_ms}ms (count: {self.slow_cycles_count})")
            
            if self.slow_cycles_count >= self.max_slow_cycles:
                self.send_alert(
                    f"Cycle time over budget: {duration_ms}ms > {self.max_cycle_time_ms}ms for "
                    f"{self.slow_cycles_count} consecutive cycles. System may be overloaded.",
                    level="warning"
                )
                self.slow_cycles_count = 0  # Reset to avoid spam
        else:
            # Reset count if we have a fast cycle
            if self.slow_cycles_count > 0:
                print(f"✅ Cycle time back to normal: {duration_ms}ms")
                self.slow_cycles_count = 0
    
    def run_check(self):
        """Run all monitoring checks"""
        print(f"🔍 Running guardrail checks at {datetime.now()}")
        
        # Check system health
        health = self.check_health()
        if 'error' in health:
            self.send_alert(f"Health check failed: {health['error']}", level="critical")
            return
        
        print(f"✅ Health check passed: {health.get('status', 'unknown')}")
        
        # Check candidates
        candidates = self.check_candidates()
        if 'error' in candidates:
            self.send_alert(f"Candidates check failed: {candidates['error']}", level="critical")
            return
        
        print(f"📊 Candidates: {candidates.get('count', 0)} found, "
              f"cached: {candidates.get('cached', False)}, "
              f"duration: {candidates.get('duration_ms', 0)}ms")
        
        # Run specific alerts
        self.check_zero_candidates_alert(candidates)
        self.check_cycle_time_alert(candidates)
        
        print("✅ Guardrail checks complete\n")

def main():
    """Run monitoring loop"""
    monitor = GuardrailMonitor()
    
    print("🚀 Starting AMC-TRADER Guardrail Monitor")
    print(f"   Zero candidates threshold: {monitor.max_zero_candidates_minutes} minutes")
    print(f"   Cycle time budget: {monitor.max_cycle_time_ms}ms")
    print(f"   Monitoring: {monitor.base_url}")
    print()
    
    # Check if we're running in continuous mode
    continuous = os.getenv('CONTINUOUS_MONITORING', 'false').lower() == 'true'
    interval_seconds = int(os.getenv('CHECK_INTERVAL_SECONDS', '300'))  # 5 minutes default
    
    if continuous:
        print(f"🔄 Continuous monitoring every {interval_seconds} seconds...")
        while True:
            try:
                monitor.run_check()
                time.sleep(interval_seconds)
            except KeyboardInterrupt:
                print("🛑 Monitoring stopped by user")
                break
            except Exception as e:
                print(f"❌ Monitoring error: {e}")
                time.sleep(60)  # Wait a minute before retrying
    else:
        # Single check
        monitor.run_check()

if __name__ == "__main__":
    main()