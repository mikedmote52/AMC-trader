#!/usr/bin/env python3
"""
Daily Portfolio Review Script
Run at market close to update tracking and identify actions needed
"""

import json
import requests
import csv
from datetime import datetime
import os

with open('/Users/mikeclawd/.openclaw/secrets/alpaca.json', 'r') as f:
    creds = json.load(f)

base_url = creds['baseUrl'].rstrip('/v2').rstrip('/')
headers = {
    'APCA-API-KEY-ID': creds['apiKey'],
    'APCA-API-SECRET-KEY': creds['apiSecret']
}

print("=" * 80)
print(f"DAILY PORTFOLIO REVIEW - {datetime.now().strftime('%Y-%m-%d %I:%M %p PT')}")
print("=" * 80)
print()

# Get positions
url = f"{base_url}/v2/positions"
r = requests.get(url, headers=headers)
positions = r.json()

# Append to daily tracking log
log_file = 'data/portfolio_daily_log.csv'
file_exists = os.path.exists(log_file)

with open(log_file, 'a', newline='') as f:
    writer = csv.writer(f)
    
    if not file_exists:
        writer.writerow(['Date', 'Symbol', 'Qty', 'Entry', 'Current', 'P&L', 'P&L %', 'Action Taken'])
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    for pos in positions:
        symbol = pos['symbol']
        qty = pos['qty']
        entry = float(pos['avg_entry_price'])
        current = float(pos['current_price'])
        pl = float(pos['unrealized_pl'])
        pl_pct = float(pos['unrealized_plpc']) * 100
        
        writer.writerow([today, symbol, qty, f"${entry:.2f}", f"${current:.2f}", 
                        f"${pl:+.2f}", f"{pl_pct:+.1f}%", ""])

# Analyze and recommend actions
print("📊 POSITION REVIEW:")
print("-" * 80)

actions_needed = []

for pos in sorted(positions, key=lambda x: float(x['unrealized_plpc']), reverse=True):
    symbol = pos['symbol']
    qty = int(float(pos['qty']))
    entry = float(pos['avg_entry_price'])
    current = float(pos['current_price'])
    pl_pct = float(pos['unrealized_plpc']) * 100
    pl = float(pos['unrealized_pl'])
    
    stop_loss = entry * 0.85  # -15%
    target_30 = entry * 1.30
    target_50 = entry * 1.50
    
    # Determine action
    action = None
    
    if pl_pct < -12:
        action = f"🚨 NEAR STOP: Down {pl_pct:.1f}% - Consider stopping out"
        actions_needed.append((symbol, action, 1))  # Priority 1 = urgent
    elif pl_pct > 50:
        action = f"💰 BIG WINNER: Up {pl_pct:.1f}% - Take profits / trail stop"
        actions_needed.append((symbol, action, 2))
    elif pl_pct > 30:
        action = f"✅ PROFIT TARGET: Up {pl_pct:.1f}% - Scale out 50%"
        actions_needed.append((symbol, action, 2))
    
    if action:
        print(f"{symbol:6s} | {qty:>3} shares | {pl_pct:>+6.1f}% | {action}")

# Scanner test positions
print("\n" + "=" * 80)
print("📊 SCANNER TEST POSITIONS:")
print("-" * 80)

scanner_picks = ['CFLT', 'KRE']
for symbol in scanner_picks:
    pos = next((p for p in positions if p['symbol'] == symbol), None)
    if pos:
        entry = float(pos['avg_entry_price'])
        current = float(pos['current_price'])
        pl_pct = float(pos['unrealized_plpc']) * 100
        days_held = 1  # Calculate properly later
        
        print(f"{symbol}: Entry ${entry:.2f} → Now ${current:.2f} | {pl_pct:+.1f}% | Day {days_held}")

# Summary
print("\n" + "=" * 80)
print("ACTION ITEMS:")
print("=" * 80)

if actions_needed:
    actions_needed.sort(key=lambda x: x[2])  # Sort by priority
    for symbol, action, priority in actions_needed:
        print(f"  {action}")
else:
    print("  ✅ No urgent actions needed - portfolio looking healthy")

print("\n" + "=" * 80)
print(f"Daily log updated: {log_file}")
print("=" * 80)
