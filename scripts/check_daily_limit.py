#!/usr/bin/env python3
"""
Check daily spending limit before placing trades
Usage: python check_daily_limit.py <proposed_trade_amount>
"""

import json
import requests
import sys
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

# Get today's filled orders
today = datetime.now().date()
after = today.isoformat()
orders_url = f"{base_url}/v2/orders?status=filled&after={after}T00:00:00Z"
response = requests.get(orders_url, headers=headers)
filled_orders = response.json()

# Calculate today's buys
buys_total = 0
for order in filled_orders:
    if order['side'] == 'buy':
        qty = float(order.get('filled_qty', 0))
        price = float(order.get('filled_avg_price', 0))
        buys_total += qty * price

DAILY_LIMIT = 300.00
remaining = DAILY_LIMIT - buys_total

print("=" * 60)
print("DAILY SPENDING LIMIT CHECK")
print("=" * 60)
print(f"Daily Limit:        ${DAILY_LIMIT:>10.2f}")
print(f"Spent Today:        ${buys_total:>10.2f}")
print(f"Remaining Budget:   ${remaining:>10.2f}")
print("-" * 60)

if len(sys.argv) > 1:
    proposed = float(sys.argv[1])
    print(f"Proposed Trade:     ${proposed:>10.2f}")
    print("-" * 60)
    
    if proposed <= remaining:
        new_remaining = remaining - proposed
        print(f"✅ TRADE APPROVED")
        print(f"   New Remaining:   ${new_remaining:>10.2f}")
    else:
        overage = proposed - remaining
        print(f"❌ TRADE REJECTED")
        print(f"   Over Budget By:  ${overage:>10.2f}")
        print(f"\n   Reduce trade to  ${remaining:.2f} or less")
        sys.exit(1)
else:
    if remaining > 0:
        print(f"✅ ${remaining:.2f} available for trades today")
    else:
        print(f"❌ Daily limit reached")
        sys.exit(1)

print("=" * 60)
