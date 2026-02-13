#!/usr/bin/env python3
"""
Real-time position monitoring with stop-loss alerts
Checks portfolio against trading rules from MEMORY.md
"""

import json
import requests
from datetime import datetime

# Load Alpaca credentials
ALPACA_CREDS_PATH = '/Users/mikeclawd/.openclaw/secrets/alpaca.json'
with open(ALPACA_CREDS_PATH, 'r') as f:
    creds = json.load(f)

headers = {
    'APCA-API-KEY-ID': creds['apiKey'],
    'APCA-API-SECRET-KEY': creds['apiSecret']
}

base_url = creds['baseUrl'].rstrip('/v2').rstrip('/')

# Get positions
positions_url = f"{base_url}/v2/positions"
positions = requests.get(positions_url, headers=headers).json()

# Get account
account_url = f"{base_url}/v2/account"
account = requests.get(account_url, headers=headers).json()

print("=" * 80)
print(f"POSITION MONITOR - {datetime.now().strftime('%I:%M %p PT')}")
print("=" * 80)

# Sort by P&L%
positions_sorted = sorted(positions, key=lambda x: float(x['unrealized_plpc']), reverse=True)

alerts = []
profit_targets = []
stop_losses = []

for pos in positions_sorted:
    symbol = pos['symbol']
    qty = float(pos['qty'])
    entry = float(pos['avg_entry_price'])
    current = float(pos['current_price'])
    pl_pct = float(pos['unrealized_plpc']) * 100
    value = float(pos['market_value'])
    
    # Check for alerts
    if pl_pct <= -15:
        stop_losses.append(f"🚨 {symbol}: {pl_pct:.1f}% STOP LOSS HIT!")
    elif pl_pct <= -10:
        alerts.append(f"⚠️  {symbol}: {pl_pct:.1f}% approaching stop (-15%)")
    
    if pl_pct >= 30:
        profit_targets.append(f"💰 {symbol}: {pl_pct:.1f}% - TAKE PROFITS (target +30%)")
    elif pl_pct >= 50:
        profit_targets.append(f"🚀 {symbol}: {pl_pct:.1f}% - SCALE OUT (target +50%)")

# Print alerts
if stop_losses:
    print("\n🚨 STOP LOSS ALERTS:")
    for alert in stop_losses:
        print(f"   {alert}")

if alerts:
    print("\n⚠️  WARNING ZONE (-10% to -15%):")
    for alert in alerts:
        print(f"   {alert}")

if profit_targets:
    print("\n💰 PROFIT TARGETS HIT:")
    for target in profit_targets:
        print(f"   {target}")

# Summary stats
total_value = float(account['portfolio_value'])
cash = float(account['cash'])
equity = float(account['equity'])

winners = [p for p in positions if float(p['unrealized_plpc']) > 0]
losers = [p for p in positions if float(p['unrealized_plpc']) < 0]

print(f"\n📊 PORTFOLIO SUMMARY:")
print(f"   Total Equity:     ${equity:,.2f}")
print(f"   Portfolio Value:  ${total_value:,.2f}")
print(f"   Cash:             ${cash:,.2f}")
print(f"   Positions:        {len(positions)} ({len(winners)} up, {len(losers)} down)")

# Check for rule violations
print(f"\n📋 RULE CHECKS:")
if len(positions) > 12:
    print(f"   ⚠️  Too many positions: {len(positions)} (target: 10-12)")
else:
    print(f"   ✅ Position count OK: {len(positions)}")

oversized = [p for p in positions if float(p['market_value']) > 300]
if oversized:
    print(f"   ⚠️  Oversized positions: {', '.join([p['symbol'] for p in oversized])}")
else:
    print(f"   ✅ Position sizing OK")

print("=" * 80)
