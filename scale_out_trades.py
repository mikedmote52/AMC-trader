#!/usr/bin/env python3
"""Quick script to scale out 50% of PTNM, SSRM, UEC"""

import json
import requests
from datetime import datetime

# Load credentials
with open('/Users/mikeclawd/.openclaw/secrets/alpaca.json', 'r') as f:
    creds = json.load(f)

base_url = creds['baseUrl'].rstrip('/v2').rstrip('/')
headers = {
    'APCA-API-KEY-ID': creds['apiKey'],
    'APCA-API-SECRET-KEY': creds['apiSecret']
}

def get_position(symbol):
    """Get current position for symbol"""
    url = f"{base_url}/v2/positions/{symbol}"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json()
    return None

def sell_shares(symbol, qty, reason):
    """Sell shares at market price"""
    url = f"{base_url}/v2/orders"
    
    order = {
        'symbol': symbol,
        'qty': str(qty),
        'side': 'sell',
        'type': 'market',
        'time_in_force': 'day'
    }
    
    print(f"\n{'='*60}")
    print(f"SELLING {qty} shares of {symbol}")
    print(f"Reason: {reason}")
    print(f"{'='*60}")
    
    r = requests.post(url, json=order, headers=headers)
    
    if r.status_code in (200, 201):
        result = r.json()
        print(f"✅ Order submitted: {result['id']}")
        print(f"   Status: {result['status']}")
        return result
    else:
        print(f"❌ Error: {r.status_code}")
        print(f"   {r.text}")
        return None

# Scale out 50% of each position
symbols = ['PTNM', 'SSRM', 'UEC']
trades = []

print(f"\n🎯 SCALING OUT 50% - {datetime.now().strftime('%Y-%m-%d %I:%M %p PT')}")
print("="*60)

for symbol in symbols:
    pos = get_position(symbol)
    if pos:
        total_qty = int(float(pos['qty']))
        sell_qty = total_qty // 2
        entry = float(pos['avg_entry_price'])
        current = float(pos['current_price'])
        pl_pct = float(pos['unrealized_plpc']) * 100
        
        print(f"\n{symbol}:")
        print(f"  Total shares: {total_qty}")
        print(f"  Selling: {sell_qty} (50%)")
        print(f"  Entry: ${entry:.2f}")
        print(f"  Current: ${current:.2f}")
        print(f"  Gain: +{pl_pct:.1f}%")
        
        result = sell_shares(symbol, sell_qty, f"Scale out 50% at +{pl_pct:.1f}% profit target")
        if result:
            trades.append({
                'symbol': symbol,
                'qty': sell_qty,
                'order_id': result['id'],
                'gain_pct': pl_pct
            })
    else:
        print(f"\n❌ No position found for {symbol}")

# Log to memory
if trades:
    print(f"\n\n📝 LOGGING TO MEMORY...")
    
    memory_file = f"memory/{datetime.now().strftime('%Y-%m-%d')}.md"
    
    log_entry = f"\n\n## {datetime.now().strftime('%I:%M %p')} - SCALED OUT 50% (Profit Taking)\n\n"
    
    for trade in trades:
        log_entry += f"**✅ SOLD 50% {trade['symbol']}:**\n"
        log_entry += f"- Shares sold: {trade['qty']}\n"
        log_entry += f"- Profit: +{trade['gain_pct']:.1f}%\n"
        log_entry += f"- Order: {trade['order_id']}\n"
        log_entry += f"- Reason: Hit profit target, locking in gains\n\n"
    
    with open(memory_file, 'a') as f:
        f.write(log_entry)
    
    print(f"✅ Logged to {memory_file}")

print("\n" + "="*60)
print("✅ SCALE OUT COMPLETE")
print("="*60)
