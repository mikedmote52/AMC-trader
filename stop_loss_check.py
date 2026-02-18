#!/usr/bin/env python3
import json
import os
from alpaca.trading.client import TradingClient
from datetime import datetime

# Load Alpaca credentials
with open('/Users/mikeclawd/.openclaw/secrets/alpaca.json', 'r') as f:
    creds = json.load(f)

# Initialize API (paper trading)
client = TradingClient(
    creds['apiKey'],
    creds['apiSecret'],
    paper=True
)

# Get all positions
positions = client.get_all_positions()

print('=' * 60)
print('STOP LOSS CHECK - Positions at -15% or worse')
print('Current time: Wednesday, February 18, 2025 - 10:06 AM PT')
print('=' * 60)

stop_loss_triggered = []
all_positions = []

for pos in positions:
    symbol = pos.symbol
    qty = float(pos.qty)
    avg_entry = float(pos.avg_entry_price)
    current = float(pos.current_price)
    unrealized_pl = float(pos.unrealized_pl)
    unrealized_plpc = float(pos.unrealized_plpc) * 100  # Convert to percentage
    
    all_positions.append({
        'symbol': symbol,
        'qty': qty,
        'avg_entry': avg_entry,
        'current': current,
        'plpc': unrealized_plpc,
        'pl': unrealized_pl
    })
    
    # Check if position hits -15% or worse
    if unrealized_plpc <= -15.0:
        stop_loss_triggered.append({
            'symbol': symbol,
            'qty': qty,
            'avg_entry': avg_entry,
            'current': current,
            'loss_pct': unrealized_plpc,
            'loss_amount': unrealized_pl
        })

# Display ALL positions summary
print('\n📊 ALL POSITIONS SUMMARY:')
print('-' * 60)
if all_positions:
    # Sort by P&L % (worst first)
    all_positions.sort(key=lambda x: x['plpc'])
    for p in all_positions:
        status = '🚨 URGENT' if p['plpc'] <= -15 else '⚠️  ' if p['plpc'] <= -8 else '✅' if p['plpc'] >= 0 else '🔍 '
        print(f"{status} {p['symbol']:6} | Qty: {p['qty']:>4} | P&L: {p['plpc']:>+7.2f}% | ${p['pl']:>+.2f}")
else:
    print('No positions found')

print('\n' + '=' * 60)
print('🚨 STOP LOSS ALERTS (Positions at -15% or worse):')
print('=' * 60)

if stop_loss_triggered:
    for alert in stop_loss_triggered:
        print(f"\n>>> URGENT ALERT <<<")
        print(f"Symbol: {alert['symbol']}")
        print(f"Current Loss: {alert['loss_pct']:.2f}%")
        print(f"Loss Amount: ${alert['loss_amount']:.2f}")
        print(f"Current Price: ${alert['current']:.2f}")
        print(f"Avg Entry: ${alert['avg_entry']:.2f}")
        print(f"RECOMMENDATION: SELL IMMEDIATELY - Stop loss triggered")
        print('---')
else:
    print('✅ NO STOP LOSSES TRIGGERED')
    print('No positions currently at -15% or worse loss.')

print('\n' + '=' * 60)
print(f'Total Positions Checked: {len(positions)}')
print(f'Stop Losses Triggered: {len(stop_loss_triggered)}')
print('=' * 60)

# Output JSON for message sending if needed
import json as json_module
result = {
    'stop_losses_triggered': stop_loss_triggered,
    'total_positions': len(positions),
    'timestamp': datetime.now().isoformat()
}

# Save to temp file for potential messaging
with open('/tmp/stop_loss_results.json', 'w') as f:
    json_module.dump(result, f, indent=2)
