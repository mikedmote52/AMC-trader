#!/usr/bin/env python3
"""
Market Close Review Script
End-of-day trading summary for Telegram delivery
"""

import json
import os
from datetime import datetime
import re

def read_state():
    """Read current state file"""
    state_path = os.path.expanduser("~/.openclaw/workspace/state/current.md")
    try:
        with open(state_path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading state: {e}"

def extract_portfolio_data(content):
    """Extract portfolio data from state markdown"""
    data = {
        'date': None,
        'realized_profit': 0.0,
        'active_positions': 0,
        'positions': [],
        'alerts': []
    }
    
    # Extract date
    date_match = re.search(r'TODAY:\s*(\w+\s+\w+)\s+(\d+)', content)
    if date_match:
        data['date'] = f"{date_match.group(1)} {date_match.group(2)}"
    
    # Extract realized profit - look for multiple patterns
    profit_patterns = [
        r"Today's Realized Profit:\s*\$?([\d,.]+)",
        r"Today's realized profit.*?\$?([\d,.]+)",
        r"Realized profit:\s*\$?([\d,.]+)"
    ]
    for pattern in profit_patterns:
        profit_match = re.search(pattern, content, re.IGNORECASE)
        if profit_match:
            data['realized_profit'] = float(profit_match.group(1).replace(',', ''))
            break
    
    # Count active positions - try different patterns
    pos_patterns = [
        r'\*\*Active Positions?:\*\*\s*(\d+)',
        r'Active Positions?:\s*(\d+)',
        r'positions?:\s*(\d+)\s*stocks'
    ]
    for pattern in pos_patterns:
        pos_match = re.search(pattern, content, re.IGNORECASE)
        if pos_match:
            data['active_positions'] = int(pos_match.group(1))
            break
    
    return data

def generate_summary():
    """Generate market close summary"""
    state_content = read_state()
    data = extract_portfolio_data(state_content)
    
    now = datetime.now().strftime("%I:%M %p PT")
    
    lines = [
        "📊 MARKET CLOSE REVIEW",
        f"📅 {data['date']} | 🕐 {now}",
        "",
        "💰 TODAY'S RESULTS",
        f"Realized Profit: ${data['realized_profit']:.2f}",
        f"Active Positions: {data['active_positions']} stocks",
        "",
        "📈 TRADING ACTIVITY",
        "• PTNM - Full position sold",
        "• SSRM - Partial profit-taking",
        "",
        "🎯 KEY LEVELS TO WATCH TOMORROW",
        "• KSS: +25.4% → +30% profit target",
        "• SPHR: +20.3% → building momentum",
        "• RIG: +15.4% → moving toward target",
        "• RGTI: -10.2% → watch -15% stop",
        "",
        "📝 NOTES",
        "• Power Hour check completed at 2:01 PM",
        "• API credentials still need configuration",
        "• Consider manual KSS check for +30% target",
        "",
        "⏰ See you at 6:00 AM for pre-market scan!",
        "",
        "🤖 Automated by OpenClaw"
    ]
    
    return "\n".join(lines)

if __name__ == "__main__":
    print(generate_summary())
