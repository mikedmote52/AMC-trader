#!/usr/bin/env python3
"""
Performance Projections Script
Run weekly (Fridays) and monthly to track performance trends
"""

import json
import requests
from datetime import datetime, timedelta

with open('/Users/mikeclawd/.openclaw/secrets/alpaca.json', 'r') as f:
    creds = json.load(f)

base_url = creds['baseUrl'].rstrip('/v2').rstrip('/')
headers = {
    'APCA-API-KEY-ID': creds['apiKey'],
    'APCA-API-SECRET-KEY': creds['apiSecret']
}

def generate_projection_report():
    """Generate weekly/monthly performance projection report"""
    
    # Get account
    account = requests.get(f'{base_url}/v2/account', headers=headers).json()
    account_value = float(account['portfolio_value'])
    
    # Load historical tracking
    import csv
    import os
    
    log_file = 'data/portfolio_daily_log.csv'
    if not os.path.exists(log_file):
        print("⚠️  No historical data yet")
        return
    
    # Get starting value from first entry
    with open(log_file, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
        if not rows:
            print("⚠️  No data in log")
            return
        
        # Get unique dates
        dates = sorted(set(row['Date'] for row in rows))
        start_date = datetime.strptime(dates[0], '%Y-%m-%d')
        current_date = datetime.now()
        
        days_active = (current_date - start_date).days + 1
    
    # Approximate starting value (could improve by tracking this)
    starting_value = 101000.0
    
    # Calculate returns
    current_return = account_value - starting_value
    current_return_pct = (current_return / starting_value) * 100
    daily_avg = current_return_pct / days_active if days_active > 0 else 0
    
    # Calculate weekly performance
    week_start = current_date - timedelta(days=7)
    week_rows = [r for r in rows if datetime.strptime(r['Date'], '%Y-%m-%d') >= week_start]
    
    # Calculate monthly performance
    month_start = current_date.replace(day=1)
    month_rows = [r for r in rows if datetime.strptime(r['Date'], '%Y-%m-%d') >= month_start]
    
    print('=' * 80)
    print(f'📊 PERFORMANCE PROJECTIONS - {current_date.strftime("%Y-%m-%d %I:%M %p PT")}')
    print('=' * 80)
    print()
    
    print('CURRENT PERFORMANCE:')
    print(f'  Starting Value: ${starting_value:,.2f}')
    print(f'  Current Value: ${account_value:,.2f}')
    print(f'  Total Gain: ${current_return:,.2f} (+{current_return_pct:.2f}%)')
    print(f'  Days Active: {days_active}')
    print(f'  Daily Avg: +{daily_avg:.3f}%')
    print()
    
    # Weekly stats
    if len(dates) >= 7:
        week_ago_date = dates[-7] if len(dates) >= 7 else dates[0]
        # This is simplified - you'd want actual portfolio values
        print(f'LAST 7 DAYS: {len(week_rows)} position updates logged')
        print()
    
    # Annual projections
    trading_days_year = 252
    
    scenarios = [
        {'name': 'Conservative (Current Pace)', 'daily_pct': daily_avg},
        {'name': 'Moderate (0.5% daily)', 'daily_pct': 0.5},
        {'name': 'Aggressive (1% daily)', 'daily_pct': 1.0},
    ]
    
    print('=' * 80)
    print('ANNUAL PROJECTIONS (252 trading days):')
    print('=' * 80)
    print()
    
    for scenario in scenarios:
        daily_pct = scenario['daily_pct']
        
        # Compound daily returns
        annual_multiplier = (1 + daily_pct/100) ** trading_days_year
        ending_value = starting_value * annual_multiplier
        annual_gain = ending_value - starting_value
        annual_return_pct = (annual_gain / starting_value) * 100
        
        print(f'{scenario["name"]}:')
        print(f'  Daily Avg: +{daily_pct:.3f}%')
        print(f'  Annual Return: +{annual_return_pct:,.1f}%')
        print(f'  Ending Value: ${ending_value:,.2f}')
        print(f'  Total Gain: ${annual_gain:,.2f}')
        print()
    
    # Monthly projection
    days_in_month = 21  # Typical trading days
    monthly_return = (1 + daily_avg/100) ** days_in_month
    monthly_gain = starting_value * (monthly_return - 1)
    
    print('=' * 80)
    print('MONTHLY PROJECTION (21 trading days):')
    print('=' * 80)
    print(f'  Expected Monthly Return: +{(monthly_return - 1) * 100:.2f}%')
    print(f'  Expected Monthly Gain: ${monthly_gain:,.2f}')
    print()
    
    print('=' * 80)
    print('⚠️  IMPORTANT NOTES:')
    print()
    print(f'  • Sample size: {days_active} days (need 30+ for statistical significance)')
    print('  • Past performance ≠ future results')
    print('  • Scanner is still learning and improving')
    print('  • Market conditions change')
    print('  • Risk management is critical')
    print()
    print('💡 BENCHMARK: Professional traders target 15-30% annually')
    print('=' * 80)
    
    # Save to tracking file
    report_file = 'data/performance_projections.jsonl'
    with open(report_file, 'a') as f:
        report = {
            'date': current_date.isoformat(),
            'account_value': account_value,
            'starting_value': starting_value,
            'total_return_pct': current_return_pct,
            'days_active': days_active,
            'daily_avg_pct': daily_avg,
            'annual_projection_pct': (annual_multiplier - 1) * 100,
            'monthly_projection_pct': (monthly_return - 1) * 100
        }
        f.write(json.dumps(report) + '\n')
    
    print(f'\n✅ Report saved to {report_file}')

if __name__ == '__main__':
    generate_projection_report()
