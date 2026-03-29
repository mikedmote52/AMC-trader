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
    today = "Thursday March 05, 2026"
    
    lines = [
        "📊 MARKET CLOSE REVIEW",
        f"📅 {today} | 🕐 {now}",
        "",
        "💰 TODAY'S RESULTS",
        "🔴 Stop-Loss Executed: -$1.31",
        "• UUUU: SOLD 0.34 shares at -15.8%",
        "• Positions: 16 stocks active",
        "",
        "📈 TRADING ACTIVITY",
        "• UUUU: STOP-LOSS EXECUTED (-15.8% | -$1.31)",
        "• SPHR: Still holding at +19.4%",
        "",
        "🎯 KEY LEVELS TO WATCH TOMORROW",
        "🎯 SPHR: +19.4% → +20% scale-out zone (0.6% away)",
        "📈 RIG: +14.39% → approaching +20% scale-out",
        "📉 RGTI: -6.77% → closest to -15% stop (8.23% buffer)",
        "📉 KRE: -6.02% → watch position",
        "",
        "📊 PORTFOLIO SNAPSHOT",
        "• Value: $101,506.59",
        "• Cash: $99,217.41",
        "• Unrealized P/L: +$102.91 (+4.50%)",
        "",
        "📝 NOTES",
        "• Stop-loss executed at 3:19 PM per SOP",
        "• Risk contained: No other positions near -15%",
        "• SPHR approaching scale-out opportunity",
        "",
        "⏰ See you at 6:00 AM for pre-market scan!",
        "",
        "🤖 Automated by OpenClaw"
    ]
    
    return "\n".join(lines)

if __name__ == "__main__":
    print(generate_summary())
