#!/usr/bin/env python3
"""Portfolio Update - 2 PM Check (March 6, 2026)"""
import json
import os
import sys
from datetime import datetime

# Load Alpaca API
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import QueryOrderStatus

# Load Alpaca credentials
with open('/Users/mikeclawd/.openclaw/secrets/alpaca.json', 'r') as f:
    creds = json.load(f)

client = TradingClient(creds['apiKey'], creds['apiSecret'], paper=True)

# Get account info
account = client.get_account()

# Get fresh positions
positions = client.get_all_positions()

# Calculate portfolio stats
all_positions = []
stop_losses = []
scale_out_candidates = []
profit_targets = []
total_market_value = 0
total_unrealized_pl = 0

for pos in positions:
    symbol = pos.symbol
    qty = float(pos.qty)
    avg_entry = float(pos.avg_entry_price)
    current = float(pos.current_price)
    unrealized_pl = float(pos.unrealized_pl)
    unrealized_plpc = float(pos.unrealized_plpc) * 100
    market_value = float(pos.market_value)
    
    total_market_value += market_value
    total_unrealized_pl += unrealized_pl
    
    position_data = {
        'symbol': symbol,
        'qty': qty,
        'avg_entry': avg_entry,
        'current': current,
        'pl': unrealized_pl,
        'plpc': round(unrealized_plpc, 2),
        'market_value': market_value
    }
    all_positions.append(position_data)
    
    # Check thresholds
    if unrealized_plpc <= -15:
        stop_losses.append({'symbol': symbol, 'plpc': unrealized_plpc})
    if unrealized_plpc >= 20:
        scale_out_candidates.append({'symbol': symbol, 'plpc': unrealized_plpc})
    if unrealized_plpc >= 30:
        profit_targets.append({'symbol': symbol, 'plpc': unrealized_plpc})

# Sort positions by P/L %
all_positions.sort(key=lambda x: x['plpc'], reverse=True)

# Count up/down
up_positions = sum(1 for p in all_positions if p['plpc'] > 0)
down_positions = sum(1 for p in all_positions if p['plpc'] <= 0)

# Find closest to stop and scale-out
closest_to_stop = min(all_positions, key=lambda x: x['plpc']) if all_positions else None
closest_to_scale = max(all_positions, key=lambda x: x['plpc']) if all_positions else None

# Output JSON result
result = {
    'timestamp': datetime.now().isoformat(),
    'check_type': '2PM Portfolio Check',
    'market_status': 'Open' if account.status == 'ACTIVE' else 'Unknown',
    'portfolio_value': round(float(account.portfolio_value), 2),
    'cash': round(float(account.cash), 2),
    'buying_power': round(float(account.buying_power), 2),
    'total_positions': len(positions),
    'up_positions': up_positions,
    'down_positions': down_positions,
    'unrealized_pl': round(total_unrealized_pl, 2),
    'positions': all_positions,
    'closest_to_stop': closest_to_stop,
    'closest_to_scale_out': closest_to_scale,
    'stop_losses_triggered': stop_losses,
    'scale_out_candidates': scale_out_candidates,
    'profit_targets_triggered': profit_targets
}

print(json.dumps(result, indent=2))
