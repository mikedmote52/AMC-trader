#!/usr/bin/env python3
"""
Daily Portfolio Review - Run at market close (1:00 PM PT)
- Updates portfolio_tracking.csv with current prices
- Checks stop-losses and profit targets
- Identifies actions needed
- Logs performance vs thesis
"""

import json
import requests
import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))
from telegram_alert import send_alert

WORKSPACE = Path('/Users/mikeclawd/.openclaw/workspace')
SECRETS = Path('/Users/mikeclawd/.openclaw/secrets/alpaca.json')

# Load credentials
with open(SECRETS) as f:
    creds = json.load(f)

headers = {
    'APCA-API-KEY-ID': creds['apiKey'],
    'APCA-API-SECRET-KEY': creds['apiSecret']
}

BASE_URL = 'https://paper-api.alpaca.markets/v2'

def get_positions():
    """Get current positions from Alpaca"""
    resp = requests.get(f'{BASE_URL}/positions', headers=headers)
    return resp.json()

def get_account():
    """Get account info"""
    resp = requests.get(f'{BASE_URL}/account', headers=headers)
    return resp.json()

def load_tracking():
    """Load existing tracking data"""
    tracking_file = WORKSPACE / 'data/portfolio_tracking.csv'
    tracking = {}
    
    if tracking_file.exists():
        with open(tracking_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                tracking[row['Symbol']] = row
    
    return tracking

def update_tracking(positions, tracking):
    """Update tracking CSV with current data"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    updated = []
    actions_needed = []
    
    for pos in positions:
        sym = pos['symbol']
        qty = float(pos['qty'])
        entry = float(pos['avg_entry_price'])
        current = float(pos['current_price'])
        cost = qty * entry
        value = qty * current
        pnl = value - cost
        pnl_pct = (pnl / cost) * 100
        
        # Get existing thesis or mark as unknown
        existing = tracking.get(sym, {})
        thesis = existing.get('Thesis', 'UNKNOWN - needs entry')
        entry_date = existing.get('Entry Date', 'Unknown')
        stop_loss = existing.get('Stop Loss', '')
        target = existing.get('Target', '')
        
        # Calculate stop loss if not set (-15% rule)
        if not stop_loss:
            stop_loss = f'${entry * 0.85:.2f}'
        
        # Calculate targets if not set (+30%, +50%)
        if not target:
            target = f'${entry * 1.30:.2f} / ${entry * 1.50:.2f}'
        
        # Check for actions needed
        if pnl_pct <= -15:
            actions_needed.append(f'🔴 {sym}: STOP LOSS HIT ({pnl_pct:.1f}%) - EXIT ASAP')
        elif pnl_pct <= -12:
            actions_needed.append(f'⚠️  {sym}: Approaching stop ({pnl_pct:.1f}%) - Monitor closely')
        elif pnl_pct >= 50:
            actions_needed.append(f'🎯 {sym}: +50% TARGET HIT - Scale out 50%, trail rest')
        elif pnl_pct >= 30:
            actions_needed.append(f'💰 {sym}: +30% TARGET HIT - Scale out 30%, set trailing stop')
        
        # Flag missing thesis
        if thesis == 'UNKNOWN - needs entry':
            actions_needed.append(f'📝 {sym}: NO THESIS RECORDED - Document why you entered')
        
        updated.append({
            'Date': today,
            'Symbol': sym,
            'Qty': qty,
            'Entry Price': f'${entry:.2f}',
            'Current Price': f'${current:.2f}',
            'Cost Basis': f'${cost:.2f}',
            'Market Value': f'${value:.2f}',
            'Unrealized P&L': f'${pnl:+.2f}',
            'Unrealized P&L %': f'{pnl_pct:+.1f}%',
            'Entry Date': entry_date,
            'Days Held': '',
            'Thesis': thesis,
            'Stop Loss': stop_loss,
            'Target': target,
            'Notes': ''
        })
    
    return updated, actions_needed

def save_tracking(data):
    """Save updated tracking data"""
    tracking_file = WORKSPACE / 'data/portfolio_tracking.csv'
    
    with open(tracking_file, 'w', newline='') as f:
        if data:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

def log_daily_snapshot(positions, account):
    """Append to daily log CSV"""
    log_file = WORKSPACE / 'data/portfolio_daily_log.csv'
    today = datetime.now().strftime('%Y-%m-%d')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    total_value = float(account['portfolio_value'])
    cash = float(account['cash'])
    positions_value = total_value - cash
    
    # Calculate total P&L
    total_pnl = sum(float(p['unrealized_pl']) for p in positions)
    
    entry = {
        'Date': today,
        'Timestamp': timestamp,
        'Portfolio Value': total_value,
        'Cash': cash,
        'Positions Value': positions_value,
        'Total Unrealized P&L': total_pnl,
        'Num Positions': len(positions)
    }
    
    # Check if file exists
    file_exists = log_file.exists()
    
    with open(log_file, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=entry.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(entry)

def generate_report(positions, account, actions):
    """Generate daily report text"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    report = f"📊 DAILY PORTFOLIO REVIEW - {today}\n"
    report += "=" * 60 + "\n\n"
    
    # Account summary
    total_value = float(account['portfolio_value'])
    cash = float(account['cash'])
    positions_value = total_value - cash
    
    report += f"💰 Portfolio Value: ${total_value:,.2f}\n"
    report += f"💵 Cash: ${cash:,.2f}\n"
    report += f"📈 Positions Value: ${positions_value:,.2f}\n"
    report += f"🎯 Positions: {len(positions)}\n\n"
    
    # Actions needed
    if actions:
        report += "🚨 ACTIONS NEEDED:\n"
        report += "-" * 60 + "\n"
        for action in actions:
            report += f"{action}\n"
        report += "\n"
    
    # Top winners/losers
    sorted_pos = sorted(positions, key=lambda p: float(p['unrealized_plpc']), reverse=True)
    
    report += "🏆 TOP 3 WINNERS:\n"
    report += "-" * 60 + "\n"
    for pos in sorted_pos[:3]:
        sym = pos['symbol']
        pnl_pct = float(pos['unrealized_plpc']) * 100
        pnl_usd = float(pos['unrealized_pl'])
        report += f"{sym}: {pnl_pct:+.1f}% (${pnl_usd:+.2f})\n"
    
    report += "\n🔻 TOP 3 LOSERS:\n"
    report += "-" * 60 + "\n"
    for pos in sorted_pos[-3:]:
        sym = pos['symbol']
        pnl_pct = float(pos['unrealized_plpc']) * 100
        pnl_usd = float(pos['unrealized_pl'])
        report += f"{sym}: {pnl_pct:+.1f}% (${pnl_usd:+.2f})\n"
    
    return report

def update_memory_file(positions, account, actions):
    """
    Automatically update memory file with daily learnings
    """
    today = datetime.now().strftime('%Y-%m-%d')
    memory_dir = WORKSPACE / 'memory'
    memory_dir.mkdir(exist_ok=True)
    memory_file = memory_dir / f'{today}.md'

    # Sort positions by P&L
    sorted_pos = sorted(positions, key=lambda p: float(p['unrealized_plpc']), reverse=True)

    # Build memory entry
    timestamp = datetime.now().strftime('%I:%M %p')
    entry = f"\n## {timestamp} - DAILY PORTFOLIO REVIEW\n\n"

    # Account status
    total_value = float(account['portfolio_value'])
    cash = float(account['cash'])
    entry += f"**Portfolio:** ${total_value:,.2f} | **Cash:** ${cash:,.2f} | **Positions:** {len(positions)}\n\n"

    # Top winners - extract lessons
    if sorted_pos:
        winners = [p for p in sorted_pos if float(p['unrealized_plpc']) > 0.15]  # >15% gains
        if winners:
            entry += "**Top Performers (>15% gains):**\n\n"
            for pos in winners[:3]:
                sym = pos['symbol']
                pnl_pct = float(pos['unrealized_plpc']) * 100
                pnl_usd = float(pos['unrealized_pl'])
                entry += f"- **{sym}**: {pnl_pct:+.1f}% (${pnl_usd:+.2f})\n"
            entry += "\n💡 *Lesson: Analyze what these winners have in common*\n\n"

        # Positions at risk
        at_risk = [p for p in sorted_pos if float(p['unrealized_plpc']) < -0.12]  # <-12%
        if at_risk:
            entry += "**Positions at Risk (approaching -15% stop):**\n\n"
            for pos in at_risk:
                sym = pos['symbol']
                pnl_pct = float(pos['unrealized_plpc']) * 100
                entry += f"- **{sym}**: {pnl_pct:+.1f}% - *Monitor closely*\n"
            entry += "\n"

    # Actions needed
    if actions:
        entry += "**Actions Needed Tomorrow:**\n\n"
        for action in actions[:5]:  # Top 5 actions
            entry += f"- {action}\n"
        entry += "\n"

    # Append to memory file
    if memory_file.exists():
        with open(memory_file, 'a') as f:
            f.write(entry)
    else:
        # Create new file with header
        with open(memory_file, 'w') as f:
            f.write(f"# Daily Log - {today}\n\n")
            f.write(entry)

    return memory_file


def main():
    print("Running daily portfolio review...")

    # Get current data
    positions = get_positions()
    account = get_account()

    # Load existing tracking
    tracking = load_tracking()

    # Update tracking
    updated, actions = update_tracking(positions, tracking)

    # Save updated tracking
    save_tracking(updated)
    print(f"✅ Updated portfolio_tracking.csv ({len(updated)} positions)")

    # Log daily snapshot
    log_daily_snapshot(positions, account)
    print("✅ Logged daily snapshot")

    # Generate report
    report = generate_report(positions, account, actions)
    print("\n" + report)

    # Save report to file
    report_file = WORKSPACE / f"data/daily_review_{datetime.now().strftime('%Y-%m-%d')}.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"✅ Saved report to {report_file.name}")

    # Update memory file automatically
    memory_file = update_memory_file(positions, account, actions)
    print(f"✅ Updated memory file: {memory_file.name}")

    # Send critical actions to Telegram
    try:
        if actions:
            message = "📊 *DAILY REVIEW - ACTIONS NEEDED*\n\n"

            # Group actions by priority
            critical = [a for a in actions if '🔴' in a or 'STOP LOSS' in a]
            profits = [a for a in actions if '🎯' in a or '💰' in a]
            warnings = [a for a in actions if '⚠️' in a]

            if critical:
                message += "*CRITICAL:*\n"
                for action in critical[:3]:
                    message += f"{action}\n"
                message += "\n"

            if profits:
                message += "*PROFIT TARGETS:*\n"
                for action in profits[:3]:
                    message += f"{action}\n"
                message += "\n"

            if warnings:
                message += "*WARNINGS:*\n"
                for action in warnings[:2]:
                    message += f"{action}\n"
                message += "\n"

            # Add summary
            total_value = float(account['portfolio_value'])
            message += f"Portfolio: ${total_value:,.2f} | {len(positions)} positions"

            send_alert(message)
            print("✅ Sent daily review to Telegram")
        else:
            # No actions, just send summary
            total_value = float(account['portfolio_value'])
            message = f"📊 *DAILY REVIEW*\n\n"
            message += f"✅ No actions needed\n"
            message += f"Portfolio: ${total_value:,.2f} | {len(positions)} positions"
            send_alert(message)
            print("✅ Sent daily review to Telegram")
    except Exception as e:
        print(f"⚠️  Failed to send Telegram alert: {e}")

    return report, actions

if __name__ == '__main__':
    report, actions = main()
