#!/usr/bin/env python3
"""
Check Alpaca positions for profit targets and execute profit-taking
"""

import json
import os
import sys
import time
import requests

# Load Alpaca credentials
ALPACA_CREDS_PATH = os.path.expanduser('~/.openclaw/secrets/alpaca.json')
with open(ALPACA_CREDS_PATH, 'r') as f:
    alpaca_creds = json.load(f)

ALPACA_API_KEY = alpaca_creds['apiKey']
ALPACA_API_SECRET = alpaca_creds['apiSecret']
ALPACA_BASE_URL = alpaca_creds['baseUrl']

ALPACA_HEADERS = {
    'APCA-API-KEY-ID': ALPACA_API_KEY,
    'APCA-API-SECRET-KEY': ALPACA_API_SECRET
}

def get_alpaca_positions():
    """Get detailed positions with gain info from Alpaca"""
    base_url = ALPACA_BASE_URL.rstrip('/v2').rstrip('/')
    url = f"{base_url}/v2/positions"
    response = requests.get(url, headers=ALPACA_HEADERS)
    if response.status_code == 200:
        return response.json()
    print(f"Error fetching positions: {response.status_code} - {response.text}")
    return []

def submit_order(symbol, qty, side, order_type='market', time_in_force='day'):
    """Submit an order to Alpaca"""
    base_url = ALPACA_BASE_URL.rstrip('/v2').rstrip('/')
    url = f"{base_url}/v2/orders"
    payload = {
        'symbol': symbol,
        'qty': str(qty),
        'side': side,
        'type': order_type,
        'time_in_force': time_in_force
    }
    response = requests.post(url, json=payload, headers=ALPACA_HEADERS)
    if response.status_code in [200, 201]:
        return response.json()
    print(f"Error submitting order: {response.status_code} - {response.text}")
    return None

def main():
    print("🔍 Checking Alpaca positions for profit targets (>30% gain)\n")
    
    positions = get_alpaca_positions()
    
    if not positions:
        print("❌ No positions found or API error")
        return []
    
    profit_targets = []
    executed_trades = []
    
    for pos in positions:
        symbol = pos['symbol']
        qty = float(pos['qty'])
        avg_entry = float(pos['avg_entry_price'])
        current_price = float(pos['current_price'])
        unrealized_pl = float(pos['unrealized_pl'])
        unrealized_plpc = float(pos['unrealized_plpc'])  # This is a decimal (e.g., 0.30 = 30%)
        gain_pct = unrealized_plpc * 100
        
        print(f"📊 {symbol}: {int(qty)} shares | Entry: ${avg_entry:.2f} | Current: ${current_price:.2f} | Gain: {gain_pct:+.1f}%")
        
        if gain_pct >= 30:
            # Calculate 50% profit-taking shares (round down)
            sell_qty = int(qty * 0.5)
            if sell_qty < 1:
                sell_qty = 1  # Sell at least 1 share
            
            profit_amount = sell_qty * (current_price - avg_entry)
            
            print(f"   🎯 PROFIT TARGET HIT! +{gain_pct:.1f}%")
            print(f"   💰 SELL: {sell_qty} shares for ~${profit_amount:.2f} profit")
            
            profit_targets.append({
                'symbol': symbol,
                'qty': qty,
                'sell_qty': sell_qty,
                'avg_entry': avg_entry,
                'current_price': current_price,
                'gain_pct': gain_pct,
                'profit_amount': profit_amount
            })
            
            # Execute the sell
            print(f"   📤 Submitting sell order for {sell_qty} shares...")
            order = submit_order(symbol, sell_qty, 'sell')
            if order:
                print(f"   ✅ Order submitted: {order.get('id', 'unknown')}")
                executed_trades.append({
                    'symbol': symbol,
                    'sell_qty': sell_qty,
                    'price': current_price,
                    'profit': profit_amount,
                    'gain_pct': gain_pct,
                    'order_id': order.get('id')
                })
            else:
                print(f"   ❌ Failed to submit order")
                executed_trades.append({
                    'symbol': symbol,
                    'sell_qty': sell_qty,
                    'price': current_price,
                    'profit': profit_amount,
                    'gain_pct': gain_pct,
                    'order_id': None,
                    'failed': True
                })
            print()
    
    if not profit_targets:
        print("\n✅ No positions hit the +30% profit target.")
    
    return executed_trades

if __name__ == '__main__':
    trades = main()
    # Output JSON for downstream processing
    print("\n=== TRADES_JSON ===")
    print(json.dumps(trades))
