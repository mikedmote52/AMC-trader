#!/usr/bin/env python3
"""
Scanner Performance Tracker - The Foundation of Learning

Tracks every scanner pick and its outcome to enable true learning.

Functions:
1. log_scanner_picks() - Records all scanner results
2. link_trade_to_scan() - Connects executed trades to scanner picks
3. update_trade_outcome() - Records final results when position closes
4. analyze_performance() - Calculates win rates, correlations, insights
5. get_factor_performance() - Shows which factors predict success

Usage:
- Called automatically after each scanner run
- Called when trades are executed (via execute_trade.py)
- Called during daily portfolio review (closed positions)
"""

import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
import requests

WORKSPACE = Path('/Users/mikeclawd/.openclaw/workspace')
SECRETS = Path('/Users/mikeclawd/.openclaw/secrets/alpaca.json')

# Load Alpaca credentials
with open(SECRETS) as f:
    creds = json.load(f)

ALPACA_HEADERS = {
    'APCA-API-KEY-ID': creds['apiKey'],
    'APCA-API-SECRET-KEY': creds['apiSecret']
}
BASE_URL = 'https://paper-api.alpaca.markets/v2'

# CSV structure
SCANNER_PERFORMANCE_FILE = WORKSPACE / 'data/scanner_performance.csv'
SCANNER_PERFORMANCE_HEADERS = [
    'scan_date', 'scan_time', 'symbol', 'price_at_scan', 'scanner_score',
    'float_score', 'momentum_score', 'volume_score', 'catalyst_score', 'multiday_score',
    'vigl_bonus', 'vigl_match', 'rvol',  # NEW: VIGL pattern tracking for learning
    'float_shares', 'change_pct', 'volume', 'catalyst_text',
    'entered', 'entry_date', 'entry_price', 'entry_thesis',
    'exit_date', 'exit_price', 'hold_days', 'return_pct', 'return_dollars',
    'outcome', 'notes'
]


def log_scanner_picks(scan_results):
    """
    Log all picks from a scanner run

    Args:
        scan_results: List of dicts from diamond_scanner.py output
    """
    scan_date = datetime.now().strftime('%Y-%m-%d')
    scan_time = datetime.now().strftime('%H:%M:%S')

    # Create file with headers if it doesn't exist
    if not SCANNER_PERFORMANCE_FILE.exists():
        SCANNER_PERFORMANCE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SCANNER_PERFORMANCE_FILE, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=SCANNER_PERFORMANCE_HEADERS)
            writer.writeheader()

    # Append scanner picks
    with open(SCANNER_PERFORMANCE_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=SCANNER_PERFORMANCE_HEADERS)

        for result in scan_results:
            row = {
                'scan_date': scan_date,
                'scan_time': scan_time,
                'symbol': result.get('symbol', ''),
                'price_at_scan': result.get('price', 0),
                'scanner_score': result.get('score', 0),
                'float_score': result.get('details', {}).get('float_score', 0),
                'momentum_score': result.get('details', {}).get('momentum_score', 0),
                'volume_score': result.get('details', {}).get('volume_score', 0),
                'catalyst_score': result.get('details', {}).get('catalyst_score', 0),
                'multiday_score': result.get('details', {}).get('multiday_score', 0),
                'vigl_bonus': result.get('vigl_bonus', 0),
                'vigl_match': result.get('vigl_match', 'none'),
                'rvol': result.get('rvol', 0),
                'float_shares': result.get('details', {}).get('float_shares', 0),
                'change_pct': result.get('details', {}).get('change_pct', 0),
                'volume': result.get('volume', 0),
                'catalyst_text': result.get('details', {}).get('catalyst', ''),
                'entered': 'No',
                'entry_date': '',
                'entry_price': '',
                'entry_thesis': '',
                'exit_date': '',
                'exit_date': '',
                'exit_price': '',
                'hold_days': '',
                'return_pct': '',
                'return_dollars': '',
                'outcome': '',
                'notes': ''
            }
            writer.writerow(row)

    print(f"✅ Logged {len(scan_results)} scanner picks to {SCANNER_PERFORMANCE_FILE}")


def link_trade_to_scan(symbol, entry_price, thesis):
    """
    Link an executed trade to its scanner pick

    Args:
        symbol: Stock symbol
        entry_price: Price at which trade was entered
        thesis: Entry thesis/reason
    """
    if not SCANNER_PERFORMANCE_FILE.exists():
        print(f"⚠️  Scanner performance file doesn't exist yet")
        return

    entry_date = datetime.now().strftime('%Y-%m-%d')

    # Read all rows
    rows = []
    with open(SCANNER_PERFORMANCE_FILE, 'r', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Find most recent scanner pick for this symbol (within last 7 days)
    cutoff_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    updated = False

    for row in reversed(rows):  # Search backwards (most recent first)
        if row['symbol'] == symbol and row['scan_date'] >= cutoff_date and row['entered'] == 'No':
            row['entered'] = 'Yes'
            row['entry_date'] = entry_date
            row['entry_price'] = entry_price
            row['entry_thesis'] = thesis
            updated = True
            print(f"✅ Linked {symbol} trade to scanner pick from {row['scan_date']} (score: {row['scanner_score']})")
            break

    if not updated:
        print(f"⚠️  No recent scanner pick found for {symbol} (may be manual entry)")

    # Write back
    with open(SCANNER_PERFORMANCE_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=SCANNER_PERFORMANCE_HEADERS)
        writer.writeheader()
        writer.writerows(rows)


def update_trade_outcome(symbol, exit_price, exit_date=None, notes=''):
    """
    Record outcome when a position is closed

    Args:
        symbol: Stock symbol
        exit_price: Exit price
        exit_date: Date exited (defaults to today)
        notes: Any notes about the trade
    """
    if not SCANNER_PERFORMANCE_FILE.exists():
        return

    if exit_date is None:
        exit_date = datetime.now().strftime('%Y-%m-%d')

    # Read all rows
    rows = []
    with open(SCANNER_PERFORMANCE_FILE, 'r', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Find the open trade for this symbol
    for row in reversed(rows):
        if row['symbol'] == symbol and row['entered'] == 'Yes' and row['exit_date'] == '':
            entry_price = float(row['entry_price'])
            entry_date_obj = datetime.strptime(row['entry_date'], '%Y-%m-%d')
            exit_date_obj = datetime.strptime(exit_date, '%Y-%m-%d')
            hold_days = (exit_date_obj - entry_date_obj).days

            return_pct = ((exit_price - entry_price) / entry_price) * 100
            # Note: return_dollars would need quantity, which we don't have here
            # Could fetch from portfolio tracking CSV

            row['exit_date'] = exit_date
            row['exit_price'] = exit_price
            row['hold_days'] = hold_days
            row['return_pct'] = f"{return_pct:.2f}"
            row['outcome'] = 'WIN' if return_pct > 0 else 'LOSS'
            row['notes'] = notes

            print(f"✅ Recorded {symbol} outcome: {row['outcome']} ({return_pct:+.1f}% in {hold_days} days)")
            break

    # Write back
    with open(SCANNER_PERFORMANCE_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=SCANNER_PERFORMANCE_HEADERS)
        writer.writeheader()
        writer.writerows(rows)


def analyze_performance(days=30):
    """
    Analyze scanner performance over last N days

    Returns:
        Dict with analysis results
    """
    if not SCANNER_PERFORMANCE_FILE.exists():
        return {'error': 'No performance data yet'}

    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    # Read completed trades
    completed_trades = []
    with open(SCANNER_PERFORMANCE_FILE, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['entered'] == 'Yes' and row['exit_date'] and row['scan_date'] >= cutoff_date:
                completed_trades.append(row)

    if not completed_trades:
        return {'error': f'No completed trades in last {days} days'}

    # Calculate statistics
    wins = [t for t in completed_trades if t['outcome'] == 'WIN']
    losses = [t for t in completed_trades if t['outcome'] == 'LOSS']

    total_trades = len(completed_trades)
    win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0

    avg_win = sum(float(t['return_pct']) for t in wins) / len(wins) if wins else 0
    avg_loss = sum(float(t['return_pct']) for t in losses) / len(losses) if losses else 0
    avg_return = sum(float(t['return_pct']) for t in completed_trades) / total_trades if total_trades > 0 else 0

    # Score range analysis
    score_ranges = {
        '150+': [t for t in completed_trades if float(t['scanner_score']) >= 150],
        '130-150': [t for t in completed_trades if 130 <= float(t['scanner_score']) < 150],
        '120-130': [t for t in completed_trades if 120 <= float(t['scanner_score']) < 130],
        '100-120': [t for t in completed_trades if 100 <= float(t['scanner_score']) < 120],
        '<100': [t for t in completed_trades if float(t['scanner_score']) < 100],
    }

    score_performance = {}
    for range_name, trades in score_ranges.items():
        if trades:
            range_wins = [t for t in trades if t['outcome'] == 'WIN']
            score_performance[range_name] = {
                'trades': len(trades),
                'win_rate': len(range_wins) / len(trades) * 100,
                'avg_return': sum(float(t['return_pct']) for t in trades) / len(trades)
            }

    analysis = {
        'period_days': days,
        'total_trades': total_trades,
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': win_rate,
        'avg_return': avg_return,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'score_performance': score_performance,
        'best_trade': max(completed_trades, key=lambda t: float(t['return_pct'])),
        'worst_trade': min(completed_trades, key=lambda t: float(t['return_pct']))
    }

    return analysis


def get_factor_performance(days=30):
    """
    Analyze which factors correlate with success

    Returns:
        Dict showing performance by factor
    """
    if not SCANNER_PERFORMANCE_FILE.exists():
        return {'error': 'No performance data yet'}

    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    completed_trades = []
    with open(SCANNER_PERFORMANCE_FILE, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['entered'] == 'Yes' and row['exit_date'] and row['scan_date'] >= cutoff_date:
                completed_trades.append(row)

    if not completed_trades:
        return {'error': f'No completed trades in last {days} days'}

    # Analyze each factor
    factors = {}

    # Float analysis (ultra-low vs low vs medium)
    ultra_low_float = [t for t in completed_trades if float(t.get('float_shares', 0)) <= 10_000_000]
    low_float = [t for t in completed_trades if 10_000_000 < float(t.get('float_shares', 0)) <= 30_000_000]

    if ultra_low_float:
        wins = [t for t in ultra_low_float if t['outcome'] == 'WIN']
        factors['ultra_low_float'] = {
            'trades': len(ultra_low_float),
            'win_rate': len(wins) / len(ultra_low_float) * 100,
            'avg_return': sum(float(t['return_pct']) for t in ultra_low_float) / len(ultra_low_float)
        }

    if low_float:
        wins = [t for t in low_float if t['outcome'] == 'WIN']
        factors['low_float'] = {
            'trades': len(low_float),
            'win_rate': len(wins) / len(low_float) * 100,
            'avg_return': sum(float(t['return_pct']) for t in low_float) / len(low_float)
        }

    # Momentum analysis (early entry vs chasing)
    early_entry = [t for t in completed_trades if abs(float(t.get('change_pct', 0))) <= 5]
    chasing = [t for t in completed_trades if float(t.get('change_pct', 0)) > 10]

    if early_entry:
        wins = [t for t in early_entry if t['outcome'] == 'WIN']
        factors['early_entry'] = {
            'trades': len(early_entry),
            'win_rate': len(wins) / len(early_entry) * 100,
            'avg_return': sum(float(t['return_pct']) for t in early_entry) / len(early_entry)
        }

    if chasing:
        wins = [t for t in chasing if t['outcome'] == 'WIN']
        factors['chasing'] = {
            'trades': len(chasing),
            'win_rate': len(wins) / len(chasing) * 100,
            'avg_return': sum(float(t['return_pct']) for t in chasing) / len(chasing)
        }

    # Catalyst analysis
    with_catalyst = [t for t in completed_trades if t.get('catalyst_text') and t['catalyst_text'] != '']
    without_catalyst = [t for t in completed_trades if not t.get('catalyst_text') or t['catalyst_text'] == '']

    if with_catalyst:
        wins = [t for t in with_catalyst if t['outcome'] == 'WIN']
        factors['with_catalyst'] = {
            'trades': len(with_catalyst),
            'win_rate': len(wins) / len(with_catalyst) * 100,
            'avg_return': sum(float(t['return_pct']) for t in with_catalyst) / len(with_catalyst)
        }

    if without_catalyst:
        wins = [t for t in without_catalyst if t['outcome'] == 'WIN']
        factors['without_catalyst'] = {
            'trades': len(without_catalyst),
            'win_rate': len(wins) / len(without_catalyst) * 100,
            'avg_return': sum(float(t['return_pct']) for t in without_catalyst) / len(without_catalyst)
        }

    return factors


def print_performance_report(days=30):
    """
    Print a formatted performance report
    """
    print(f"\n{'='*60}")
    print(f"SCANNER PERFORMANCE REPORT - Last {days} Days")
    print(f"{'='*60}\n")

    analysis = analyze_performance(days)

    if 'error' in analysis:
        print(f"⚠️  {analysis['error']}")
        return

    print(f"📊 Overall Performance:")
    print(f"   Total Trades: {analysis['total_trades']}")
    print(f"   Wins: {analysis['wins']} | Losses: {analysis['losses']}")
    print(f"   Win Rate: {analysis['win_rate']:.1f}%")
    print(f"   Avg Return: {analysis['avg_return']:+.1f}%")
    print(f"   Avg Win: {analysis['avg_win']:+.1f}% | Avg Loss: {analysis['avg_loss']:+.1f}%")

    print(f"\n🎯 Performance by Scanner Score:")
    for range_name, perf in analysis['score_performance'].items():
        print(f"   {range_name}: {perf['trades']} trades, {perf['win_rate']:.0f}% win rate, {perf['avg_return']:+.1f}% avg")

    print(f"\n🏆 Best Trade:")
    best = analysis['best_trade']
    print(f"   {best['symbol']}: {float(best['return_pct']):+.1f}% (score: {best['scanner_score']}, held {best['hold_days']} days)")

    print(f"\n📉 Worst Trade:")
    worst = analysis['worst_trade']
    print(f"   {worst['symbol']}: {float(worst['return_pct']):+.1f}% (score: {worst['scanner_score']}, held {worst['hold_days']} days)")

    print(f"\n🔬 Factor Analysis:")
    factors = get_factor_performance(days)

    if 'error' not in factors:
        for factor_name, perf in factors.items():
            print(f"   {factor_name}: {perf['trades']} trades, {perf['win_rate']:.0f}% win rate, {perf['avg_return']:+.1f}% avg")

    print(f"\n{'='*60}\n")


if __name__ == '__main__':
    # When run directly, show performance report
    print_performance_report(30)
