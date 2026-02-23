#!/usr/bin/env python3
"""
Weekly Performance Review Automation
=====================================

Runs every Friday at 6:00 PM PT to analyze trading performance.

Outputs:
- memory/weekly_review_YYYY-MM-DD.md
- Telegram alert with key metrics
- Recommendations for next week

Usage:
    python3 scripts/weekly_review_template.py
"""

import pandas as pd
import json
from datetime import datetime, timedelta
from pathlib import Path

def load_performance_data():
    """Load scanner and portfolio performance data"""
    scanner_perf = pd.read_csv('data/scanner_performance.csv')
    portfolio_log = pd.read_csv('data/portfolio_daily_log.csv')
    return scanner_perf, portfolio_log

def calculate_weekly_metrics(days=7):
    """Calculate key performance metrics for last N days"""
    scanner_perf, portfolio_log = load_performance_data()
    
    # Filter to last N days
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    recent = scanner_perf[scanner_perf['scan_date'] >= cutoff_date]
    
    # Calculate metrics
    closed_trades = recent[recent['exit_date'].notna()]
    
    metrics = {
        'total_scans': len(recent),
        'trades_entered': len(recent[recent['entered'] == 'Yes']),
        'trades_closed': len(closed_trades),
        'wins': len(closed_trades[closed_trades['return_pct'] > 0]),
        'losses': len(closed_trades[closed_trades['return_pct'] <= 0]),
        'win_rate': 0.0,
        'avg_return': 0.0,
        'best_trade': None,
        'worst_trade': None
    }
    
    if metrics['trades_closed'] > 0:
        metrics['win_rate'] = metrics['wins'] / metrics['trades_closed']
        metrics['avg_return'] = closed_trades['return_pct'].mean()
        metrics['best_trade'] = closed_trades.loc[closed_trades['return_pct'].idxmax()]['symbol']
        metrics['worst_trade'] = closed_trades.loc[closed_trades['return_pct'].idxmin()]['symbol']
    
    return metrics

def generate_report(metrics):
    """Generate markdown report"""
    report = f"""# Weekly Performance Review
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Period:** Last 7 days

## Key Metrics

- **Scans Run:** {metrics['total_scans']}
- **Trades Entered:** {metrics['trades_entered']}
- **Trades Closed:** {metrics['trades_closed']}
- **Win Rate:** {metrics['win_rate']*100:.1f}%
- **Average Return:** {metrics['avg_return']:.2f}%

## Trade Performance

### Wins: {metrics['wins']}
### Losses: {metrics['losses']}

### Best Trade: {metrics['best_trade'] or 'N/A'}
### Worst Trade: {metrics['worst_trade'] or 'N/A'}

## TODO: Add More Analysis

- [ ] Scanner accuracy (% of high-scoring picks that won)
- [ ] Factor performance breakdown
- [ ] Comparison to previous week
- [ ] Market-adjusted returns (alpha)
- [ ] Recommendations for next week

## Notes

_This is a template. Enhance with more detailed analysis as data accumulates._
"""
    return report

def main():
    print("=" * 60)
    print("WEEKLY PERFORMANCE REVIEW")
    print("=" * 60)
    
    # Calculate metrics
    metrics = calculate_weekly_metrics(days=7)
    
    # Generate report
    report = generate_report(metrics)
    
    # Save to memory
    filename = f"memory/weekly_review_{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(filename, 'w') as f:
        f.write(report)
    
    print(f"\n✅ Report saved to: {filename}")
    print(f"\nKey Stats:")
    print(f"  Win Rate: {metrics['win_rate']*100:.1f}%")
    print(f"  Avg Return: {metrics['avg_return']:.2f}%")
    print(f"  Trades Closed: {metrics['trades_closed']}")
    
    # TODO: Send to Telegram
    # from telegram_alert import send_alert
    # send_alert(f"📊 Weekly Review: {metrics['win_rate']*100:.0f}% WR, {metrics['avg_return']:.1f}% avg return")

if __name__ == "__main__":
    main()
