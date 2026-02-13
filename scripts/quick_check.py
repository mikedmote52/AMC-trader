#!/usr/bin/env python3
import json, requests, os
from datetime import datetime

# Load credentials
with open(os.path.expanduser('~/.openclaw/secrets/alpaca.json')) as f:
    creds = json.load(f)

headers = {
    'APCA-API-KEY-ID': creds['apiKey'],
    'APCA-API-SECRET-KEY': creds['apiSecret']
}

base_url = 'https://paper-api.alpaca.markets'

# Get account info
account = requests.get(f'{base_url}/v2/account', headers=headers).json()

# Get positions
positions = requests.get(f'{base_url}/v2/positions', headers=headers).json()

print(f'Account Value: ${float(account["equity"]):,.2f}')
print(f'Cash: ${float(account["cash"]):,.2f}')
print(f'P/L Today: ${float(account["equity"]) - float(account["last_equity"]):,.2f}')
print(f'\nPositions ({len(positions)}):')
print()

for p in sorted(positions, key=lambda x: float(x['unrealized_plpc']), reverse=True):
    symbol = p['symbol']
    qty = p['qty']
    avg = float(p['avg_entry_price'])
    current = float(p['current_price'])
    pnl_pct = float(p['unrealized_plpc']) * 100
    pnl_dollar = float(p['unrealized_pl'])
    
    emoji = '🟢' if pnl_pct > 0 else '🔴'
    print(f'{emoji} {symbol}: {qty} @ ${avg:.2f} → ${current:.2f} ({pnl_pct:+.1f}%) ${pnl_dollar:+.2f}')

# Market snapshot
print('\n=== Market Overview ===')
symbols = ['SPY', 'QQQ', 'IWM']
for sym in symbols:
    try:
        resp = requests.get(f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d')
        data = resp.json()
        quote = data['chart']['result'][0]['meta']
        price = quote['regularMarketPrice']
        prev = quote['previousClose']
        change = ((price - prev) / prev) * 100
        emoji = '🟢' if change > 0 else '🔴'
        print(f'{emoji} {sym}: ${price:.2f} ({change:+.2f}%)')
    except:
        print(f'❌ {sym}: Error fetching')
