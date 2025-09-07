#!/usr/bin/env python3
"""
AMC-TRADER Regression Watchdog

Monitors for critical regressions:
1. raw>0 && served==0 (discovery pipeline broken)
2. Missing headers (route contract violations) 
3. X-System-State=DEGRADED during RTH (freshness failures)

Sends Slack alerts when issues detected.
"""
import requests
import json
import os
import time
from datetime import datetime
from typing import Dict, Optional


class RegressionMonitor:
    def __init__(self, api_base: str, slack_webhook: Optional[str] = None):
        self.api = api_base
        self.slack_webhook = slack_webhook or os.getenv("SLACK_WEBHOOK_URL")
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'AMC-Watchdog/1.0'})
    
    def check_contenders_regression(self) -> Dict:
        """Check for raw>0 && served==0 regression"""
        try:
            # Get raw count
            raw_resp = self.session.get(f"{self.api}/discovery/contenders/raw?strategy=legacy_v0", 
                                      headers={"X-Admin-Token": os.getenv("ADMIN_TOKEN", "")},
                                      timeout=10)
            
            # Get served count and headers
            served_resp = self.session.get(f"{self.api}/discovery/contenders?strategy=legacy_v0", 
                                         timeout=10)
            
            if raw_resp.status_code != 200 or served_resp.status_code != 200:
                return {
                    "regression_detected": True,
                    "issue": "API_ERROR",
                    "details": f"Raw: {raw_resp.status_code}, Served: {served_resp.status_code}"
                }
            
            raw_data = raw_resp.json()
            served_data = served_resp.json()
            
            raw_count = len(raw_data) if isinstance(raw_data, list) else raw_data.get("count", 0)
            served_count = len(served_data) if isinstance(served_data, list) else 0
            
            # CRITICAL: Check for regression
            regression = raw_count > 0 and served_count == 0
            
            # Check required headers
            headers = served_resp.headers
            required_headers = ['X-System-State', 'X-Reason-Stats', 'Cache-Control']
            missing_headers = [h for h in required_headers if h not in headers]
            headers_missing = len(missing_headers) > 0
            
            # Check system state
            system_state = headers.get('X-System-State', 'UNKNOWN')
            
            return {
                "regression_detected": regression or headers_missing,
                "raw_count": raw_count,
                "served_count": served_count,
                "missing_headers": missing_headers,
                "system_state": system_state,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "regression_detected": True,
                "issue": "MONITOR_ERROR", 
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def check_market_hours(self) -> bool:
        """Check if we're in regular trading hours (approximate)"""
        try:
            health_resp = self.session.get(f"{self.api}/discovery/health", timeout=5)
            if health_resp.status_code == 200:
                data = health_resp.json()
                market_session = data.get('market_session', 'closed')
                return market_session == 'regular'  # RTH only
        except Exception:
            pass
        return False
    
    def send_slack_alert(self, alert_data: Dict):
        """Send Slack alert for regression"""
        if not self.slack_webhook:
            print(f"⚠️  ALERT (no Slack): {json.dumps(alert_data, indent=2)}")
            return
            
        try:
            # Format alert message
            if alert_data.get("issue") == "REGRESSION":
                message = (
                    f"🚨 *AMC-TRADER REGRESSION DETECTED* 🚨\n\n"
                    f"• **Raw count**: {alert_data['raw_count']}\n"
                    f"• **Served count**: {alert_data['served_count']}\n"
                    f"• **Strategy**: {alert_data.get('strategy', 'legacy_v0')}\n"
                    f"• **Missing headers**: {alert_data.get('missing_headers', [])}\n"
                    f"• **System state**: {alert_data.get('system_state', 'UNKNOWN')}\n"
                    f"• **Time**: {alert_data['timestamp']}\n\n"
                    f"The discovery pipeline is finding candidates but /contenders is returning empty!\n"
                    f"Check: Redis keys, route filtering, header setting."
                )
            elif alert_data.get("issue") == "DEGRADED_RTH":
                message = (
                    f"⚠️ *AMC-TRADER DEGRADED DURING RTH* ⚠️\n\n"
                    f"• **System state**: DEGRADED\n"
                    f"• **Market session**: Regular Trading Hours\n" 
                    f"• **Time**: {alert_data['timestamp']}\n\n"
                    f"Freshness thresholds exceeded during market hours!"
                )
            else:
                message = f"🚨 *AMC-TRADER ALERT*: {json.dumps(alert_data, indent=2)}"
            
            payload = {
                "text": message,
                "username": "AMC-Watchdog",
                "icon_emoji": ":warning:"
            }
            
            response = requests.post(self.slack_webhook, json=payload, timeout=10)
            if response.status_code == 200:
                print(f"✅ Slack alert sent successfully")
            else:
                print(f"❌ Slack alert failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Slack alert error: {e}")
    
    def run_check(self) -> bool:
        """Run full regression check, return True if healthy"""
        print(f"🔍 Running regression check at {datetime.now().strftime('%H:%M:%S')}")
        
        # Check for contenders regression
        regression_data = self.check_contenders_regression()
        
        if regression_data["regression_detected"]:
            # Determine alert type
            raw_count = regression_data.get("raw_count", 0)
            served_count = regression_data.get("served_count", 0)
            missing_headers = regression_data.get("missing_headers", [])
            system_state = regression_data.get("system_state", "UNKNOWN")
            
            if raw_count > 0 and served_count == 0:
                alert_data = {
                    "issue": "REGRESSION",
                    "strategy": "legacy_v0",
                    **regression_data
                }
                print(f"🚨 REGRESSION DETECTED: Raw={raw_count}, Served={served_count}")
                self.send_slack_alert(alert_data)
                return False
            
            if missing_headers:
                alert_data = {
                    "issue": "HEADERS_MISSING", 
                    "missing_headers": missing_headers,
                    **regression_data
                }
                print(f"🚨 MISSING HEADERS: {missing_headers}")
                self.send_slack_alert(alert_data)
                return False
        
        # Check for DEGRADED during RTH
        if regression_data.get("system_state") == "DEGRADED" and self.check_market_hours():
            alert_data = {
                "issue": "DEGRADED_RTH",
                **regression_data
            }
            print(f"⚠️  DEGRADED DURING RTH")
            self.send_slack_alert(alert_data)
            return False
        
        print(f"✅ All checks passed")
        return True


def main():
    """Main monitoring loop"""
    api_base = os.getenv("API", "https://amc-trader.onrender.com")
    
    monitor = RegressionMonitor(api_base)
    
    # Single check mode (for cron)
    if os.getenv("WATCHDOG_MODE") == "once":
        healthy = monitor.run_check()
        exit(0 if healthy else 1)
    
    # Continuous monitoring mode
    print("🚀 AMC-TRADER Regression Watchdog starting...")
    print(f"📡 Monitoring: {api_base}")
    print(f"📢 Slack alerts: {'Enabled' if monitor.slack_webhook else 'Disabled'}")
    
    interval = int(os.getenv("WATCHDOG_INTERVAL", 300))  # 5 minutes default
    
    try:
        while True:
            monitor.run_check()
            print(f"💤 Sleeping {interval}s...")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n👋 Watchdog stopped")


if __name__ == "__main__":
    main()