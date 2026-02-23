#!/usr/bin/env python3
"""Check Alpaca positions for profit-taking opportunities"""

import json
import os
import requests

# Load Alpaca credentials
ALPACA_CREDS_PATH = os.path.expanduser('~/.openclaw/secrets/alpaca.json')
with open(ALPACA_CREDS_PATH, 'r') as f:
    alpaca_creds = json.load(f)

ALPACA_API_KEY = alpaca_creds['apiKey']
ALPACA_API_SECRET = alpaca_creds['apiSecret']
ALPACA_BASE_URL = alpaca_creds['baseUrl'].rstrip('/v2').rstrip('/')

headers = {
    'APCA-API-KEY-ID': ALPACA_API_KEY,
    'APCA-API-SECRET-KEY': ALPACA_API_SECRET
}

# Get positions
url = f'{ALPACA_BASE_URL}/v2/positions'
resp = requests.get(url, headers=headers)
positions = resp.json()

print('=== ALPACA POSITIONS (10:00 AM PT) ===')
print(f'Total positions: {len(positions)}')
print()

PROFIT_THRESHOLD = 30.0
profit_targets = []

for pos in positions:
    symbol = pos['symbol']
    qty = float(pos['qty'])
    unrealized_plpc = float(pos['unrealized_plpc']) * 100
    unrealized_pl = float(pos['unrealized_pl'])
    market_value = float(pos['market_value'])
    avg_entry = float(pos['avg_entry_price'])
    current_price = float(pos['current_price'])
    
    status = ""
    if unrealized_plpc >= PROFIT_THRESHOLD:
        status = "🎯 PROFIT TARGET HIT!"
        half_qty = qty / 2
        half_value = half_qty * current_price
        profit_targets.append({
            'symbol': symbol,
            'qty': qty,
            'half_qty': half_qty,
            'pl_pct': unrealized_plpc,
            'avg_entry': avg_entry,
            'current_price': current_price,
            'market_value': market_value,
            'half_value': half_value
        })
    elif unrealized_plpc < -15:
        status = "🚨 STOP-LOSS WARNING"
    
    print(f'{symbol}: Qty={qty:.2f}, Entry=${avg_entry:.2f}, Current=${current_price:.2f}, '
          f'P/L%={unrealized_plpc:+.2f}%, P/L=${unrealized_pl:+.2f}, Value=${market_value:.2f} {status}')

print()
print('=== PROFIT-TAKING ANALYSIS ===')
if profit_targets:
    print(f'🎯 Positions over +{PROFIT_THRESHOLD}%: {len(profit_targets)}')
    for target in profit_targets:
        print(f"\n{target['symbol']}:")
        print(f"  Current P/L: +{target['pl_pct']:.2f}%")
        print(f"  Shares owned: {target['qty']:.2f}")
        print(f"  50% profit-taking: Sell {target['half_qty']:.2f} shares")
        print(f"  Estimated proceeds: ${target['half_value']:.2f}")
else:
    print(f'✅ No positions over +{PROFIT_THRESHOLD}% gain')
    print('   No profit-taking required at this time')

# Save results for potential trading
import sys
sys.exit(0 if not profit_targets else 1)
