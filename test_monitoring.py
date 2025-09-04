#!/usr/bin/env python3
"""
AMC-TRADER Monitoring System Interactive Tester
Explore and test all new monitoring features
"""

import json
import httpx
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

# API Configuration
API_BASE = "https://amc-trader.onrender.com"

class Colors:
    """Terminal colors for pretty output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_section(title: str):
    """Print a section header"""
    print(f"\n{Colors.YELLOW}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.YELLOW}{Colors.BOLD}{title}{Colors.ENDC}")
    print(f"{Colors.YELLOW}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_test(name: str, endpoint: str):
    """Print test information"""
    print(f"{Colors.CYAN}Testing: {name}{Colors.ENDC}")
    print(f"Endpoint: {endpoint}")

def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {message}{Colors.ENDC}")

def print_error(message: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {message}{Colors.ENDC}")

def print_data(data: Any, indent: int = 2):
    """Pretty print JSON data"""
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=indent, default=str))
    else:
        print(data)

async def test_endpoint(name: str, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
    """Test a single endpoint"""
    print_test(name, f"{method} {API_BASE}{endpoint}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                response = await client.get(f"{API_BASE}{endpoint}")
            else:
                response = await client.post(f"{API_BASE}{endpoint}", json=data or {})
            
            if response.status_code == 200:
                print_success(f"Success (HTTP {response.status_code})")
                result = response.json()
                return result
            else:
                print_error(f"Failed (HTTP {response.status_code})")
                try:
                    print_data(response.json())
                except:
                    print(response.text)
                return None
    except Exception as e:
        print_error(f"Request failed: {e}")
        return None

async def test_monitoring_system():
    """Run comprehensive monitoring system tests"""
    
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("🚀 AMC-TRADER MONITORING SYSTEM TEST SUITE")
    print(f"{Colors.ENDC}")
    
    # ========== SYSTEM HEALTH ==========
    print_section("📊 SYSTEM HEALTH & STATUS")
    
    status = await test_endpoint(
        "Monitoring System Status",
        "GET",
        "/monitoring/status"
    )
    if status and status.get('success'):
        components = status.get('status', {}).get('components', {})
        for comp_name, comp_status in components.items():
            status_emoji = "✅" if comp_status.get('status') in ['healthy', 'ready', 'ACTIVE'] else "⚠️"
            print(f"  {status_emoji} {comp_name}: {comp_status.get('status', 'unknown')}")
    print()
    
    dashboard = await test_endpoint(
        "Comprehensive Dashboard",
        "GET",
        "/monitoring/dashboard"
    )
    if dashboard and dashboard.get('success'):
        dash_data = dashboard.get('dashboard', {})
        print(f"\n{Colors.BOLD}Dashboard Summary:{Colors.ENDC}")
        
        # Discovery Health
        discovery = dash_data.get('discovery_health', {})
        print(f"  📈 Discovery Pipeline:")
        print(f"     Health Score: {discovery.get('score', 0):.2f}")
        print(f"     Universe Size: {discovery.get('universe_size', 0):,} stocks")
        print(f"     Latest Candidates: {discovery.get('latest_candidates', 0)}")
        
        # Recommendations
        recs = dash_data.get('recommendations', {})
        print(f"  📊 Learning System:")
        print(f"     Missed Opportunities (30d): {recs.get('missed_opportunities_30d', 0)}")
        print(f"     Avg 30d Performance: {recs.get('avg_30d_performance', 0):.1f}%")
        print(f"     Success Rate: {recs.get('success_rate_pct', 0):.1f}%")
        
        # Buy-the-Dip
        dips = dash_data.get('buy_the_dip', {})
        print(f"  💎 Buy-the-Dip:")
        print(f"     Active Opportunities: {dips.get('active_opportunities', 0)}")
    
    # ========== DISCOVERY MONITORING ==========
    print_section("🔍 DISCOVERY PIPELINE MONITORING")
    print("Track how 10,325+ stocks get filtered to final candidates\n")
    
    flow_stats = await test_endpoint(
        "Discovery Flow Statistics (Last 24h)",
        "GET",
        "/monitoring/discovery/flow-stats?hours_back=24&limit=3"
    )
    if flow_stats and flow_stats.get('success'):
        summary = flow_stats.get('summary', {})
        print(f"\n{Colors.BOLD}Flow Summary (24h):{Colors.ENDC}")
        print(f"  Total Runs: {summary.get('total_discovery_runs', 0)}")
        print(f"  Avg Universe: {summary.get('avg_universe_size', 0):,} stocks")
        print(f"  Avg Candidates: {summary.get('avg_final_candidates', 0):.1f}")
        print(f"  Avg Health: {summary.get('avg_health_score', 0):.3f}")
        
        # Show recent flows
        flows = flow_stats.get('flow_data', [])[:2]
        if flows:
            print(f"\n{Colors.BOLD}Recent Discovery Flows:{Colors.ENDC}")
            for flow in flows:
                timestamp = flow.get('timestamp', '')
                if timestamp:
                    time_str = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
                else:
                    time_str = 'Unknown'
                print(f"  • {time_str}: {flow.get('universe_size', 0):,} → {flow.get('final_candidates', 0)} candidates")
                if flow.get('alerts'):
                    for alert in flow['alerts'][:1]:
                        print(f"    ⚠️ {alert}")
    
    # ========== LEARNING SYSTEM ==========
    print_section("📈 LEARNING SYSTEM & MISSED OPPORTUNITIES")
    print("Track recommendations you didn't buy that performed well\n")
    
    missed = await test_endpoint(
        "Missed Opportunities (30 days, >15% gain)",
        "GET",
        "/monitoring/recommendations/missed-opportunities?days_back=30&min_performance=15"
    )
    if missed and missed.get('success'):
        opportunities = missed.get('missed_opportunities', [])
        print(f"\n{Colors.BOLD}Top Missed Opportunities:{Colors.ENDC}")
        if opportunities:
            for opp in opportunities[:5]:
                symbol = opp.get('symbol', 'N/A')
                perf = opp.get('performance_30d', 0)
                price = opp.get('discovery_price', 0)
                reason = opp.get('discovery_reason', '')
                print(f"  💔 {symbol}: +{perf:.1f}% (was ${price:.2f})")
                print(f"     Reason: {reason[:50]}...")
        else:
            print("  No missed opportunities found (good job!)")
    
    insights = await test_endpoint(
        "Learning System Insights",
        "GET",
        "/monitoring/recommendations/performance-insights"
    )
    if insights and insights.get('success'):
        data = insights.get('insights', {})
        print(f"\n{Colors.BOLD}Learning Insights:{Colors.ENDC}")
        print(f"  Total Tracked: {data.get('total_tracked', 0)}")
        print(f"  Explosive Rate: {data.get('explosive_rate', 0)*100:.1f}%")
        print(f"  Success Rate: {data.get('success_rate', 0)*100:.1f}%")
        print(f"  Missed Count: {data.get('missed_opportunities', 0)}")
    
    # ========== BUY-THE-DIP ==========
    print_section("💎 BUY-THE-DIP OPPORTUNITIES")
    print("Find underperforming holdings with strong thesis\n")
    
    dips = await test_endpoint(
        "Current Dip Opportunities",
        "GET",
        "/monitoring/dip-analysis/opportunities?min_drop_pct=10&days_back=7"
    )
    if dips and dips.get('success'):
        opportunities = dips.get('opportunities', [])
        print(f"\n{Colors.BOLD}Buy-the-Dip Opportunities:{Colors.ENDC}")
        if opportunities:
            for opp in opportunities[:5]:
                symbol = opp.get('symbol', 'N/A')
                drop = opp.get('price_drop_pct', 0)
                thesis = opp.get('thesis_strength', 'N/A')
                rec = opp.get('dip_buy_recommendation', 'N/A')
                price = opp.get('current_price', 0)
                risk = opp.get('risk_score', 0)
                
                emoji = "🔥" if rec == "STRONG_BUY" else "💰" if rec == "BUY" else "⏳"
                print(f"  {emoji} {symbol}: -{drop:.1f}% at ${price:.2f}")
                print(f"     Thesis: {thesis}, Recommendation: {rec}, Risk: {risk:.2f}")
                
                reasons = opp.get('reasoning', [])
                if reasons and isinstance(reasons, list):
                    print(f"     Reasoning: {reasons[0] if reasons else 'N/A'}")
        else:
            print("  No dip opportunities currently")
    
    # ========== ALERTS ==========
    print_section("🚨 SYSTEM ALERTS")
    
    alerts = await test_endpoint(
        "All System Alerts",
        "GET",
        "/monitoring/alerts/system?limit=5"
    )
    if alerts and alerts.get('success'):
        alert_list = alerts.get('alerts', [])
        if alert_list:
            print(f"\n{Colors.BOLD}Recent Alerts:{Colors.ENDC}")
            for alert in alert_list[:3]:
                alert_type = alert.get('type', 'UNKNOWN')
                message = alert.get('message', 'No message')
                emoji = "🔴" if 'CRITICAL' in str(alert) else "🟡" if 'WARNING' in str(alert) else "🔵"
                print(f"  {emoji} [{alert_type}] {message}")
        else:
            print("  ✅ No active alerts")
    
    # ========== SUMMARY ==========
    print_section("📋 TEST COMPLETE!")
    
    print(f"{Colors.BOLD}Quick Actions You Can Take:{Colors.ENDC}")
    print("1. Check missed opportunities for stocks to research")
    print("2. Review buy-the-dip opportunities for position adds")
    print("3. Monitor discovery health score (should be >0.7)")
    print("4. Watch for critical alerts requiring attention")
    print()
    print(f"{Colors.BOLD}Continuous Monitoring:{Colors.ENDC}")
    print(f"Dashboard: {API_BASE}/monitoring/dashboard")
    print(f"Alerts: {API_BASE}/monitoring/alerts/system")
    print()

async def interactive_mode():
    """Run in interactive mode"""
    print(f"\n{Colors.BOLD}Interactive Mode - Choose what to test:{Colors.ENDC}")
    print("1. Run full test suite")
    print("2. Check discovery pipeline health only")
    print("3. Check missed opportunities only")
    print("4. Check buy-the-dip opportunities only")
    print("5. Check system alerts only")
    print("6. Initialize monitoring system")
    print("7. Trigger dip analysis")
    print("0. Exit")
    
    choice = input("\nEnter choice (0-7): ").strip()
    
    if choice == "1":
        await test_monitoring_system()
    elif choice == "2":
        print_section("DISCOVERY PIPELINE HEALTH")
        await test_endpoint("Discovery Health", "GET", "/monitoring/discovery/health")
        result = await test_endpoint("Flow Stats", "GET", "/monitoring/discovery/flow-stats?hours_back=24&limit=5")
        if result and result.get('success'):
            print_data(result.get('summary', {}))
    elif choice == "3":
        print_section("MISSED OPPORTUNITIES")
        result = await test_endpoint(
            "Missed Opportunities",
            "GET",
            "/monitoring/recommendations/missed-opportunities?days_back=30&min_performance=15"
        )
        if result and result.get('success'):
            for opp in result.get('missed_opportunities', [])[:10]:
                print(f"  {opp.get('symbol')}: +{opp.get('performance_30d', 0):.1f}%")
    elif choice == "4":
        print_section("BUY-THE-DIP OPPORTUNITIES")
        result = await test_endpoint(
            "Dip Opportunities",
            "GET",
            "/monitoring/dip-analysis/opportunities?min_drop_pct=10&days_back=7"
        )
        if result and result.get('success'):
            for opp in result.get('opportunities', [])[:10]:
                print(f"  {opp.get('symbol')}: -{opp.get('price_drop_pct', 0):.1f}% ({opp.get('dip_buy_recommendation')})")
    elif choice == "5":
        print_section("SYSTEM ALERTS")
        result = await test_endpoint("System Alerts", "GET", "/monitoring/alerts/system?limit=20")
        if result and result.get('success'):
            for alert in result.get('alerts', []):
                print(f"  [{alert.get('type')}] {alert.get('message')}")
    elif choice == "6":
        print_section("INITIALIZE MONITORING")
        result = await test_endpoint("Initialize", "POST", "/monitoring/initialize")
        if result and result.get('success'):
            print_success("Monitoring system initialized!")
            print_data(result.get('components', []))
    elif choice == "7":
        print_section("TRIGGER DIP ANALYSIS")
        result = await test_endpoint("Trigger Analysis", "POST", "/monitoring/dip-analysis/run")
        if result and result.get('success'):
            print_success("Dip analysis triggered in background!")
    elif choice == "0":
        print("Goodbye! 👋")
        return
    
    # Ask if user wants to continue
    if choice != "0":
        again = input("\nRun another test? (y/n): ").strip().lower()
        if again == 'y':
            await interactive_mode()

if __name__ == "__main__":
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("🚀 AMC-TRADER MONITORING SYSTEM TESTER")
    print(f"{Colors.ENDC}")
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "full":
        asyncio.run(test_monitoring_system())
    else:
        asyncio.run(interactive_mode())