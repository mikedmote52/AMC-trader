#!/usr/bin/env python3
"""
Squeeze Monitor Watchdog
Monitors the discovery system and alerts on consecutive failures
"""

import os
import sys
import requests
import json
import time
from datetime import datetime, timezone
import asyncio
from typing import Optional

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.redis_client import get_redis_client

class SqueezeMonitorWatchdog:
    """Runtime watchdog that monitors squeeze candidate discovery"""
    
    def __init__(self):
        self.api_base = os.getenv("API_BASE_URL", "https://amc-trader.onrender.com")
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        self.redis = get_redis_client()
        self.alert_key = "squeeze_monitor:alerted"
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3
        self.poll_interval = 120  # 2 minutes
        
    def log(self, level: str, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] WATCHDOG-{level}: {message}")
    
    def check_system_health(self) -> tuple[bool, dict]:
        """Check system health via discovery endpoints"""
        try:
            # Check contenders endpoint
            response = requests.get(
                f"{self.api_base}/discovery/contenders?strategy=legacy_v0",
                timeout=30
            )
            
            if response.status_code != 200:
                return False, {"error": f"Contenders endpoint returned {response.status_code}"}
            
            system_state = response.headers.get("X-System-State", "UNKNOWN")
            reason_stats_header = response.headers.get("X-Reason-Stats", "{}")
            
            try:
                reason_stats = json.loads(reason_stats_header)
            except:
                reason_stats = {}
            
            candidates = response.json()
            candidate_count = len(candidates) if isinstance(candidates, list) else 0
            
            # Get debug information
            debug_info = {}
            try:
                debug_response = requests.get(
                    f"{self.api_base}/discovery/contenders/debug?strategy=legacy_v0",
                    timeout=10
                )
                if debug_response.status_code == 200:
                    debug_info = debug_response.json()
            except Exception as e:
                self.log("WARN", f"Debug endpoint unavailable: {e}")
            
            # Determine if this is a failure condition
            is_failure = (
                system_state == "DEGRADED" or
                (system_state == "HEALTHY" and 
                 candidate_count == 0 and 
                 debug_info.get("summary", {}).get("after_freshness", 0) >= 100)
            )
            
            return not is_failure, {
                "system_state": system_state,
                "candidate_count": candidate_count,
                "reason_stats": reason_stats,
                "debug_summary": debug_info.get("summary", {}),
                "drop_reasons": debug_info.get("drop_reasons", [])[:5],
                "config_snapshot": debug_info.get("config_snapshot", {})
            }
            
        except Exception as e:
            return False, {"error": f"Health check failed: {str(e)}"}
    
    def send_slack_alert(self, status_data: dict):
        """Send Slack alert about system issues"""
        if not self.slack_webhook:
            self.log("WARN", "SLACK_WEBHOOK_URL not configured - skipping alert")
            return
            
        try:
            summary = status_data.get("debug_summary", {})
            reason_stats = status_data.get("reason_stats", {})
            drop_reasons = status_data.get("drop_reasons", [])
            config = status_data.get("config_snapshot", {})
            
            # Format drop reasons
            reasons_text = "\n".join([f"• {r.get('reason', 'unknown')}: {r.get('count', 0)}" 
                                    for r in drop_reasons[:3]])
            
            message = f"""🚨 Squeeze Monitor Alert
State: {status_data.get('system_state', 'UNKNOWN')}
Candidates: {status_data.get('candidate_count', 0)}
Symbols in: {summary.get('symbols_in', 0)}
After freshness: {summary.get('after_freshness', 0)}
Watchlist: {summary.get('watchlist', 0)}
Trade ready: {summary.get('trade_ready', 0)}

Top drop reasons:
{reasons_text}

Thresholds: {config.get('gates', {})}
Reason stats: {reason_stats}"""

            payload = {
                "text": message,
                "username": "AMC-TRADER Watchdog",
                "icon_emoji": ":rotating_light:"
            }
            
            response = requests.post(
                self.slack_webhook,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                self.log("INFO", "Slack alert sent successfully")
            else:
                self.log("WARN", f"Slack alert failed: {response.status_code}")
                
        except Exception as e:
            self.log("ERROR", f"Failed to send Slack alert: {e}")
    
    def should_alert(self) -> bool:
        """Check if we should send an alert (throttling)"""
        try:
            # Check if we've already alerted recently
            alerted = self.redis.get(self.alert_key)
            return alerted is None
        except:
            return True  # Default to allowing alerts if Redis fails
    
    def mark_alerted(self):
        """Mark that we've sent an alert to avoid spam"""
        try:
            # Set alert flag with 10-minute TTL
            self.redis.setex(self.alert_key, 600, "true")
        except Exception as e:
            self.log("WARN", f"Failed to set alert throttle: {e}")
    
    async def run_watchdog(self):
        """Main watchdog loop"""
        self.log("INFO", f"Starting watchdog monitoring (poll interval: {self.poll_interval}s)")
        
        while True:
            try:
                is_healthy, status_data = self.check_system_health()
                
                if is_healthy:
                    self.consecutive_failures = 0
                    self.log("INFO", f"System healthy - {status_data.get('candidate_count', 0)} candidates")
                else:
                    self.consecutive_failures += 1
                    self.log("WARN", 
                           f"System issue detected ({self.consecutive_failures}/{self.max_consecutive_failures}): "
                           f"{status_data}")
                    
                    # Alert after consecutive failures
                    if (self.consecutive_failures >= self.max_consecutive_failures and 
                        self.should_alert()):
                        
                        self.log("ALERT", "Sending Slack alert for consecutive failures")
                        self.send_slack_alert(status_data)
                        self.mark_alerted()
                
                await asyncio.sleep(self.poll_interval)
                
            except KeyboardInterrupt:
                self.log("INFO", "Watchdog stopped by user")
                break
            except Exception as e:
                self.log("ERROR", f"Watchdog error: {e}")
                await asyncio.sleep(self.poll_interval)

async def main():
    """Entry point for watchdog"""
    watchdog = SqueezeMonitorWatchdog()
    await watchdog.run_watchdog()

if __name__ == "__main__":
    asyncio.run(main())