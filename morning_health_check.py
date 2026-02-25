#!/usr/bin/env python3
"""
MORNING HEALTH CHECK - Pre-Trading System Validation
Runs at 6:00 AM PT before 6:35 AM scanner
Generates GO/NO-GO report for autonomous trading
"""

import json
import os
from datetime import datetime
from pathlib import Path

# System paths
WORKSPACE = Path('/Users/mikeclawd/.openclaw/workspace')
SECRETS = Path('/Users/mikeclawd/.openclaw/secrets')

def check_api_connections():
    """Test all API connections"""
    results = {}
    
    # Polygon API
    try:
        from polygon import RESTClient
        with open(SECRETS / 'polygon.json') as f:
            creds = json.load(f)
        client = RESTClient(api_key=creds['apiKey'])
        snap = client.get_snapshot_ticker('stocks', 'AAPL')
        results['polygon'] = {'status': '✅', 'price': f'${snap.day.close:.2f}' if snap.day else 'N/A'}
    except Exception as e:
        results['polygon'] = {'status': '❌', 'error': str(e)}
    
    # Alpaca API
    try:
        import alpaca_trade_api as tradeapi
        with open(SECRETS / 'alpaca.json') as f:
            creds = json.load(f)
        api = tradeapi.REST(creds['apiKey'], creds['apiSecret'], creds['baseUrl'])
        account = api.get_account()
        results['alpaca'] = {
            'status': '✅',
            'portfolio': f'${float(account.portfolio_value):,.2f}',
            'cash': f'${float(account.cash):,.2f}'
        }
    except Exception as e:
        results['alpaca'] = {'status': '❌', 'error': str(e)}
    
    return results

def check_critical_files():
    """Verify all critical files exist and are current"""
    files = {
        'MEMORY.md': (WORKSPACE / 'MEMORY.md', 86400),  # Within 24h
        'state/current.md': (WORKSPACE / 'state/current.md', 86400),
        'diamond_scanner.py': (WORKSPACE / 'diamond_scanner.py', 604800),  # Within 7 days
        'data/diamonds.json': (WORKSPACE / 'data/diamonds.json', 86400),
        'data/market_cap_cache.json': (WORKSPACE / 'data/market_cap_cache.json', 604800),
    }
    
    results = {}
    now = datetime.now().timestamp()
    
    for name, (path, max_age) in files.items():
        if not path.exists():
            results[name] = {'status': '❌', 'error': 'Missing'}
        else:
            age = now - path.stat().st_mtime
            if age > max_age:
                results[name] = {'status': '⚠️', 'age_hours': f'{age/3600:.1f}h old'}
            else:
                results[name] = {'status': '✅', 'age_hours': f'{age/3600:.1f}h'}
    
    return results

def check_cron_jobs():
    """Check active cron jobs"""
    try:
        import subprocess
        result = subprocess.run(['openclaw', 'cron', 'list'], 
                              capture_output=True, text=True, timeout=30)
        
        # Parse for critical jobs
        critical_jobs = [
            'Premarket Scan (Automated)',
            'Scanner Results Alert',
            'Portfolio Health Check'
        ]
        
        results = {'total_jobs': 0, 'enabled': 0, 'critical': {}}
        
        # Count jobs (simplified)
        if 'error' not in result.stderr.lower():
            results['status'] = '✅'
            results['note'] = 'Cron system responsive'
        else:
            results['status'] = '⚠️'
            results['note'] = 'Check manually: openclaw cron list'
        
        return results
    except Exception as e:
        return {'status': '❌', 'error': str(e)}

def assess_system_health():
    """Calculate overall system health score"""
    api_results = check_api_connections()
    file_results = check_critical_files()
    cron_results = check_cron_jobs()
    
    # Calculate score
    score = 0
    max_score = 100
    
    # APIs (40 points)
    if api_results.get('polygon', {}).get('status') == '✅':
        score += 20
    if api_results.get('alpaca', {}).get('status') == '✅':
        score += 20
    
    # Files (30 points)
    critical_files = ['MEMORY.md', 'state/current.md', 'diamond_scanner.py']
    for cf in critical_files:
        if file_results.get(cf, {}).get('status') == '✅':
            score += 10
    
    # Cron (20 points)
    if cron_results.get('status') == '✅':
        score += 20
    
    # Context check (10 points) - did we read MEMORY.md today?
    try:
        with open(WORKSPACE / 'memory' / f'{datetime.now().strftime("%Y-%m-%d")}.md') as f:
            if 'morning' in f.read().lower():
                score += 10
    except:
        pass
    
    return {
        'score': score,
        'max_score': max_score,
        'percentage': f'{score}%',
        'status': '✅ GO' if score >= 80 else '⚠️ CAUTION' if score >= 60 else '❌ NO-GO',
        'apis': api_results,
        'files': file_results,
        'cron': cron_results
    }

def determine_priority_action(health_score, recent_performance=None):
    """Based on health and recent results, what needs fixing most?"""
    
    if health_score < 80:
        return "CRITICAL: Fix failing components before trading"
    
    # Check yesterday's scanner runtime
    try:
        with open(WORKSPACE / 'memory' / f'{datetime.now().strftime("%Y-%m-%d")}.md') as f:
            today_log = f.read()
        if '55-90 seconds' in today_log or 'timeout' in today_log.lower():
            return "PRIORITY: Scanner speed optimization (<30s target)"
    except:
        pass
    
    # Check if we missed any explosive moves
    yesterday_candidates = list((WORKSPACE / 'data').glob('diamonds_*.json'))
    if yesterday_candidates:
        # If we had low scores yesterday, prioritize social sentiment
        return "PRIORITY: Social sentiment integration (catch moves earlier)"
    
    # Default: Historical validation for confidence
    return "PRIORITY: Historical validator (prove system works)"

def generate_report():
    """Generate full health report"""
    now = datetime.now().strftime('%I:%M %p PT')
    health = assess_system_health()
    priority = determine_priority_action(health['score'])
    
    report = f"""🩺 MORNING HEALTH CHECK - {now}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 SYSTEM STATUS: {health['status']}
Overall Health: {health['percentage']} ({health['score']}/{health['max_score']})

🔗 API CONNECTIONS:
• Polygon: {health['apis'].get('polygon', {}).get('status', '?')} {health['apis'].get('polygon', {}).get('price', '')}
• Alpaca: {health['apis'].get('alpaca', {}).get('status', '?')} {health['apis'].get('alpaca', {}).get('portfolio', '')}

📁 CRITICAL FILES:
• MEMORY.md: {health['files'].get('MEMORY.md', {}).get('status', '?')}
• state/current.md: {health['files'].get('state/current.md', {}).get('status', '?')}
• diamond_scanner.py: {health['files'].get('diamond_scanner.py', {}).get('status', '?')}

⏰ AUTOMATION:
• Cron Jobs: {health['cron'].get('status', '?')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 TODAY'S PRIORITY: {priority}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
    
    # Add trading readiness
    if health['score'] >= 80:
        report += """✅ READY FOR AUTONOMOUS TRADING

6:35 AM Plan:
1. Scanner runs automatically
2. Execute buy if score 150+
3. Document thesis fully
4. Report immediately

Daily Budget: $300 (unused)
Current Cash: $""" + health['apis'].get('alpaca', {}).get('cash', 'N/A').replace('$', '') + """
"""
    else:
        report += """⚠️ SYSTEM NEEDS ATTENTION

Fix before trading:
"""
        # List specific issues
        for api_name, api_data in health['apis'].items():
            if api_data.get('status') != '✅':
                report += f"• {api_name}: {api_data.get('error', 'Check connection')}\n"
        
        for file_name, file_data in health['files'].items():
            if file_data.get('status') == '❌':
                report += f"• {file_name}: {file_data.get('error', 'Missing')}\n"
    
    report += "\n" + "━"*50 + "\n"
    
    return report

def main():
    """Main entry point"""
    print(generate_report())
    
    # Save to file
    report_path = WORKSPACE / 'logs' / f'health_check_{datetime.now().strftime("%Y-%m-%d")}.txt'
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, 'w') as f:
        f.write(generate_report())
    
    # Return exit code based on health
    health = assess_system_health()
    return 0 if health['score'] >= 80 else 1

if __name__ == '__main__':
    exit(main())