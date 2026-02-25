#!/usr/bin/env python3
"""
Morning Trades Execution - 9:30 AM
Execute stop-losses (-15%) and profit-taking (+30%)
"""

import requests
import json
import os
from datetime import datetime
import pytz

# Alpaca credentials
ALPACA_CREDS_PATH = os.path.expanduser('~/.openclaw/secrets/alpaca.json')
if not os.path.exists(ALPACA_CREDS_PATH):
    ALPACA_CREDS_PATH = '/Users/mikeclawd/.openclaw/secrets/alpaca.json'

try:
    with open(ALPACA_CREDS_PATH, 'r') as f:
        creds = json.load(f)
except FileNotFoundError:
    print(f"❌ ERROR: Alpaca credentials not found at {ALPACA_CREDS_PATH}")
    exit(1)

ALPACA_HEADERS = {
    'APCA-API-KEY-ID': creds['apiKey'],
    'APCA-API-SECRET-KEY': creds['apiSecret']
}

BASE_URL = creds['baseUrl'].rstrip('/v2').rstrip('/')

def get_account():
    url = f"{BASE_URL}/v2/account"
    resp = requests.get(url, headers=ALPACA_HEADERS)
    return resp.json() if resp.status_code == 200 else None

def get_positions():
    url = f"{BASE_URL}/v2/positions"
    resp = requests.get(url, headers=ALPACA_HEADERS)
    return resp.json() if resp.status_code == 200 else []

def submit_order(symbol, qty, side, order_type='market'):
    """Submit an order to Alpaca"""
    url = f"{BASE_URL}/v2/orders"
    payload = {
        'symbol': symbol,
        'qty': qty,
        'side': side,
        'type': order_type,
        'time_in_force': 'day'
    }
    resp = requests.post(url, headers=ALPACA_HEADERS, json=payload)
    return resp.json() if resp.status_code == 200 else {'error': resp.text}

def main():
    pt = pytz.timezone('America/Los_Angeles')
    now = datetime.now(pt)
    
    print("=" * 70)
    print(f"🌅 MORNING TRADES EXECUTION - {now.strftime('%A, %B %d at %I:%M %p PT')}")
    print("=" * 70)
    
    # Get account and positions
    account = get_account()
    positions = get_positions()
    
    if not account:
        print("❌ Failed to connect to Alpaca API")
        return
    
    portfolio_value = float(account.get('portfolio_value', 0))
    cash = float(account.get('cash', 0))
    buying_power = float(account.get('buying_power', 0))
    
    print(f"\n💰 PORTFOLIO STATUS")
    print("-" * 70)
    print(f"Portfolio Value:  ${portfolio_value:,.2f}")
    print(f"Cash Available:   ${cash:,.2f}")
    print(f"Buying Power:     ${buying_power:,.2f}")
    print(f"Active Positions: {len(positions)}")
    
    # Trading rules
    STOP_LOSS_THRESHOLD = -15.0
    PROFIT_TARGET_THRESHOLD = 30.0
    
    executed_trades = []
    positions_data = []
    
    # Analyze all positions
    for pos in positions:
        symbol = pos.get('symbol', 'N/A')
        qty = float(pos.get('qty', 0))
        avg_entry = float(pos.get('avg_entry_price', 0))
        current = float(pos.get('current_price', 0))
        market_value = float(pos.get('market_value', 0))
        unrealized_pl = float(pos.get('unrealized_pl', 0))
        unrealized_plpc = float(pos.get('unrealized_plpc', 0)) * 100
        
        positions_data.append({
            'symbol': symbol,
            'qty': qty,
            'avg_entry': avg_entry,
            'current': current,
            'market_value': market_value,
            'unrealized_pl': unrealized_pl,
            'unrealized_plpc': unrealized_plpc
        })
    
    # STOP-LOSS CHECK (-15%)
    print(f"\n🛡️  STOP-LOSS CHECK (Threshold: {STOP_LOSS_THRESHOLD}%)")
    print("-" * 70)
    
    stop_violations = [p for p in positions_data if p['unrealized_plpc'] <= STOP_LOSS_THRESHOLD]
    
    if stop_violations:
        print(f"🚨 STOP-LOSS VIOLATIONS: {len(stop_violations)} position(s)")
        for v in stop_violations:
            print(f"\n  • {v['symbol']}: {v['unrealized_plpc']:.2f}% | ${v['market_value']:.2f}")
            
            # Execute stop-loss sell
            qty_to_sell = int(v['qty'])
            result = submit_order(v['symbol'], qty_to_sell, 'sell')
            
            if 'error' not in result:
                print(f"    ✅ SELL ORDER SUBMITTED: {qty_to_sell} shares of {v['symbol']}")
                executed_trades.append({
                    'timestamp': now.strftime('%Y-%m-%d %H:%M:%S PT'),
                    'type': 'stop_loss',
                    'symbol': v['symbol'],
                    'qty': qty_to_sell,
                    'price': v['current'],
                    'pnl_pct': v['unrealized_plpc'],
                    'pnl_dollar': v['unrealized_pl'],
                    'status': 'executed'
                })
            else:
                print(f"    ❌ ORDER FAILED: {result.get('error', 'Unknown error')}")
                executed_trades.append({
                    'timestamp': now.strftime('%Y-%m-%d %H:%M:%S PT'),
                    'type': 'stop_loss',
                    'symbol': v['symbol'],
                    'qty': qty_to_sell,
                    'price': v['current'],
                    'pnl_pct': v['unrealized_plpc'],
                    'pnl_dollar': v['unrealized_pl'],
                    'status': 'failed',
                    'error': result.get('error', 'Unknown')
                })
    else:
        print("✅ No stop-loss violations")
    
    # PROFIT TARGET CHECK (+30%)
    print(f"\n🎯 PROFIT TARGET CHECK (Threshold: +{PROFIT_TARGET_THRESHOLD}%)")
    print("-" * 70)
    
    profit_targets = [p for p in positions_data if p['unrealized_plpc'] >= PROFIT_TARGET_THRESHOLD]
    
    if profit_targets:
        print(f"🎯 PROFIT TARGETS HIT: {len(profit_targets)} position(s)")
        for t in profit_targets:
            print(f"\n  • {t['symbol']}: {t['unrealized_plpc']:.2f}% | ${t['market_value']:.2f}")
            
            # Sell 50% of position for profit-taking
            qty_to_sell = max(1, int(t['qty'] * 0.5))
            result = submit_order(t['symbol'], qty_to_sell, 'sell')
            
            if 'error' not in result:
                print(f"    ✅ PROFIT-TAKE SUBMITTED: {qty_to_sell} shares of {t['symbol']} (50%)")
                executed_trades.append({
                    'timestamp': now.strftime('%Y-%m-%d %H:%M:%S PT'),
                    'type': 'profit_take',
                    'symbol': t['symbol'],
                    'qty': qty_to_sell,
                    'price': t['current'],
                    'pnl_pct': t['unrealized_plpc'],
                    'pnl_dollar': t['unrealized_pl'] * (qty_to_sell / t['qty']),
                    'status': 'executed'
                })
            else:
                print(f"    ❌ ORDER FAILED: {result.get('error', 'Unknown error')}")
                executed_trades.append({
                    'timestamp': now.strftime('%Y-%m-%d %H:%M:%S PT'),
                    'type': 'profit_take',
                    'symbol': t['symbol'],
                    'qty': qty_to_sell,
                    'price': t['current'],
                    'pnl_pct': t['unrealized_plpc'],
                    'pnl_dollar': t['unrealized_pl'] * (qty_to_sell / t['qty']),
                    'status': 'failed',
                    'error': result.get('error', 'Unknown')
                })
    else:
        print("✅ No profit targets hit")
    
    # SUMMARY
    print("\n" + "=" * 70)
    print("📊 EXECUTION SUMMARY")
    print("=" * 70)
    
    if executed_trades:
        print(f"\nTotal Orders Submitted: {len(executed_trades)}")
        for trade in executed_trades:
            status_icon = "✅" if trade['status'] == 'executed' else "❌"
            print(f"  {status_icon} {trade['type'].upper()}: {trade['symbol']} - {trade['qty']} shares @ ${trade['price']:.2f}")
    else:
        print("\nNo trades executed today.")
    
    # Position Status Table
    print("\n" + "-" * 70)
    print("📈 POSITION STATUS")
    print("-" * 70)
    print(f"{'Symbol':<10} {'Qty':<8} {'P/L %':<10} {'P/L $':<12} {'Value':<12} {'Status':<15}")
    print("-" * 70)
    
    # Sort by P/L % descending
    sorted_positions = sorted(positions_data, key=lambda x: x['unrealized_plpc'], reverse=True)
    
    for p in sorted_positions:
        if p['unrealized_plpc'] >= 20:
            status = "🎯 Near Target"
        elif p['unrealized_plpc'] >= 30:
            status = "🎯 TARGET HIT"
        elif p['unrealized_plpc'] <= -15:
            status = "🛑 STOP HIT"
        elif p['unrealized_plpc'] <= -10:
            status = "⚠️  Near Stop"
        elif p['unrealized_plpc'] > 0:
            status = "📈 Green"
        else:
            status = "📉 Red"
        
        print(f"{p['symbol']:<10} {p['qty']:<8.0f} {p['unrealized_plpc']:>+7.2f}%  ${p['unrealized_pl']:>+9.2f}  ${p['market_value']:>9.2f}  {status}")
    
    print("\n" + "=" * 70)
    print("✅ MORNING TRADES COMPLETE")
    print("=" * 70)
    
    # Return results for logging
    return {
        'timestamp': now.strftime('%Y-%m-%d %H:%M:%S PT'),
        'portfolio_value': portfolio_value,
        'cash': cash,
        'buying_power': buying_power,
        'position_count': len(positions),
        'stop_violations': len(stop_violations),
        'profit_targets': len(profit_targets),
        'executed_trades': executed_trades,
        'positions': sorted_positions
    }

if __name__ == '__main__':
    result = main()
    
    # Save results to JSON for processing
    output_path = '/Users/mikeclawd/.openclaw/workspace/morning_trades_result.json'
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\nResults saved to: {output_path}")
