#!/usr/bin/env python3
import json
import requests
import os
from datetime import datetime

# Load credentials
creds_path = os.path.expanduser('~/.openclaw/secrets/alpaca.json')
with open(creds_path, 'r') as f:
    creds = json.load(f)

base_url = creds['baseUrl'].rstrip('/v2').rstrip('/')
headers = {
    'APCA-API-KEY-ID': creds['apiKey'],
    'APCA-API-SECRET-KEY': creds['apiSecret']
}

# Get positions
positions = requests.get(f'{base_url}/v2/positions', headers=headers).json()
account = requests.get(f'{base_url}/v2/account', headers=headers).json()

print('=== PORTFOLIO STATUS ===')
print(f"Portfolio Value: ${float(account.get('portfolio_value', 0)):,.2f}")
print(f"Cash: ${float(account.get('cash', 0)):,.2f}")
print(f"Buying Power: ${float(account.get('buying_power', 0)):,.2f}")
print(f"Positions: {len(positions)}")
print()
print('=== HOLDINGS ===')

stops_triggered = []
near_stops = []
profit_targets = []

for pos in positions:
    symbol = pos['symbol']
    qty = int(float(pos['qty']))
    avg_entry = float(pos['avg_entry_price'])
    current = float(pos['current_price'])
    pl_pct = float(pos['unrealized_plpc']) * 100
    value = float(pos['market_value'])
    
    status = ""
    if pl_pct <= -15:
        status = "🔴 STOP LOSS"
        stops_triggered.append({'symbol': symbol, 'loss': pl_pct, 'qty': qty})
    elif pl_pct <= -12:
        status = "⚠️ NEAR STOP"
        near_stops.append({'symbol': symbol, 'loss': pl_pct})
    elif pl_pct >= 30:
        status = "🎯 PROFIT TARGET"
        profit_targets.append({'symbol': symbol, 'gain': pl_pct, 'qty': qty})
    elif pl_pct >= 23:
        status = "🟡 CLOSE TO TARGET"
    elif pl_pct >= 15:
        status = "📈 Building"
    
    print(f"{symbol:6} | Qty: {qty:4} | P/L: {pl_pct:+7.2f}% | ${value:8.2f} {status}")

print()

# Calculate unrealized P&L
total_pl = sum(float(p.get('unrealized_pl', 0)) for p in positions)
print(f"Unrealized P&L: ${total_pl:+,.2f}")

print()

if stops_triggered:
    print("🔴 STOP-LOSSES TRIGGERED - ACTION REQUIRED:")
    for stop in stops_triggered:
        print(f"  {stop['symbol']}: {stop['loss']:.1f}% - SELL {stop['qty']} shares")
else:
    print("✅ No stop-losses triggered")

if near_stops:
    print()
    print("⚠️  NEAR STOP-LOSS (Monitor):")
    for near in near_stops:
        print(f"  {near['symbol']}: {near['loss']:.1f}%")

if profit_targets:
    print()
    print("🎯 PROFIT TARGETS HIT:")
    for tgt in profit_targets:
        print(f"  {tgt['symbol']}: {tgt['gain']:.1f}% - SELL {tgt['qty']} shares")

# Save to file for state update
result = {
    'timestamp': datetime.now().strftime('%Y-%m-%d %I:%M %p PT'),
    'portfolio_value': float(account.get('portfolio_value', 0)),
    'cash': float(account.get('cash', 0)),
    'buying_power': float(account.get('buying_power', 0)),
    'position_count': len(positions),
    'unrealized_pl': total_pl,
    'positions': [
        {
            'symbol': p['symbol'],
            'qty': int(float(p['qty'])),
            'avg_entry': float(p['avg_entry_price']),
            'current': float(p['current_price']),
            'pl_pct': float(p['unrealized_plpc']) * 100,
            'value': float(p['market_value'])
        }
        for p in positions
    ],
    'stops_triggered': stops_triggered,
    'near_stops': near_stops,
    'profit_targets': profit_targets
}

with open('/Users/mikeclawd/.openclaw/workspace/data/midday_check.json', 'w') as f:
    json.dump(result, f, indent=2)

print()
print("Results saved to data/midday_check.json")
