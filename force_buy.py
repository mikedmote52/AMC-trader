#!/usr/bin/env python3
"""
FORCE BUY - Execute a trade immediately
"""
import json
import sys
import requests

# Load Alpaca credentials
with open('/Users/mikeclawd/.openclaw/secrets/alpaca.json', 'r') as f:
    creds = json.load(f)

headers = {
    'APCA-API-KEY-ID': creds['apiKey'],
    'APCA-API-SECRET-KEY': creds['apiSecret']
}
base = creds.get('baseUrl', 'https://paper-api.alpaca.markets')

def get_account():
    resp = requests.get(f"{base}/v2/account", headers=headers)
    return resp.json()

def submit_order(symbol, qty, side='buy'):
    url = f"{base}/v2/orders"
    payload = {
        'symbol': symbol,
        'qty': qty,
        'side': side,
        'type': 'market',
        'time_in_force': 'day'
    }
    resp = requests.post(url, headers=headers, json=payload)
    return resp.json()

if __name__ == '__main__':
    symbol = sys.argv[1] if len(sys.argv) > 1 else 'ENSC'
    amount = float(sys.argv[2]) if len(sys.argv) > 2 else 150
    
    # Get current price
    bars_resp = requests.get(
        f"{base}/v2/stocks/{symbol}/bars?timeframe=1Min&limit=1",
        headers=headers
    ).json()
    
    if bars_resp.get('bars'):
        price = bars_resp['bars'][0]['close']
        qty = int(amount / price)
        
        print(f"Buying {qty} shares of {symbol} at ~${price:.2f} (${qty*price:.0f})")
        
        order = submit_order(symbol, qty)
        
        if order.get('id'):
            print(f"✅ Order submitted: {order['id']}")
            print(f"Status: {order.get('status', 'unknown')}")
        else:
            print(f"❌ Order failed: {order}")
    else:
        print(f"Could not get price for {symbol}")
