#!/usr/bin/env python3
"""Portfolio check script - fetch Alpaca positions and analyze."""

import os
import json
import requests
from datetime import datetime

# Alpaca API credentials from environment
API_KEY = os.environ.get('ALPACA_API_KEY', '')
SECRET_KEY = os.environ.get('ALPACA_SECRET_KEY', '')
BASE_URL = 'https://paper-api.alpaca.markets'  # Paper trading

def get_alpaca_data():
    """Fetch positions and account data from Alpaca."""
    headers = {
        'APCA-API-KEY-ID': API_KEY,
        'APCA-API-SECRET-KEY': SECRET_KEY
    }
    
    try:
        # Get account info
        account_resp = requests.get(f'{BASE_URL}/v2/account', headers=headers, timeout=10)
        account = account_resp.json() if account_resp.status_code == 200 else None
        
        # Get positions
        positions_resp = requests.get(f'{BASE_URL}/v2/positions', headers=headers, timeout=10)
        positions = positions_resp.json() if positions_resp.status_code == 200 else []
        
        return {'account': account, 'positions': positions}
    except Exception as e:
        return {'error': str(e), 'account': None, 'positions': []}

def analyze_positions(positions):
    """Analyze positions for stop-loss and profit targets."""
    alerts = []
    position_summary = []
    
    for pos in positions:
        symbol = pos.get('symbol', 'N/A')
        qty = float(pos.get('qty', 0))
        market_value = float(pos.get('market_value', 0))
        cost_basis = float(pos.get('cost_basis', 0))
        unrealized_pl = float(pos.get('unrealized_pl', 0))
        current_price = float(pos.get('current_price', 0))
        avg_entry_price = float(pos.get('avg_entry_price', 0))
        
        # Calculate P&L percentage
        pl_pct = (unrealized_pl / cost_basis * 100) if cost_basis > 0 else 0
        
        position_summary.append({
            'symbol': symbol,
            'qty': qty,
            'market_value': market_value,
            'cost_basis': cost_basis,
            'unrealized_pl': unrealized_pl,
            'pl_pct': round(pl_pct, 2),
            'current_price': current_price,
            'avg_entry': avg_entry_price
        })
        
        # Check for stop-loss (-15%)
        if pl_pct <= -15:
            alerts.append(f"🔴 STOP-LOSS: {symbol} at {pl_pct:.1f}% loss (${unrealized_pl:.2f})")
        
        # Check for profit target (+30%)
        if pl_pct >= 30:
            alerts.append(f"🟢 PROFIT TARGET: {symbol} at +{pl_pct:.1f}% gain (+${unrealized_pl:.2f})")
    
    return position_summary, alerts

def main():
    print("📊 Portfolio Check - 10 AM", flush=True)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}\n", flush=True)
    
    # Fetch data
    data = get_alpaca_data()
    
    if data.get('error'):
        print(f"Error: {data['error']}", flush=True)
        return
    
    account = data.get('account')
    positions = data.get('positions', [])
    
    # Account Summary
    if account:
        print("💰 ACCOUNT", flush=True)
        print(f"  Equity: ${float(account.get('equity', 0)):,.2f}", flush=True)
        print(f"  Buying Power: ${float(account.get('buying_power', 0)):,.2f}", flush=True)
        print(f"  Cash: ${float(account.get('cash', 0)):,.2f}", flush=True)
        print(f"  Daytrading Count: {account.get('daytrade_count', 'N/A')}", flush=True)
        print()
    
    # Position Analysis
    position_summary, alerts = analyze_positions(positions)
    
    print(f"📈 POSITIONS ({len(positions)} total)", flush=True)
    total_pl = 0
    total_cost = 0
    
    for pos in position_summary:
        total_pl += pos['unrealized_pl']
        total_cost += pos['cost_basis']
        pl_emoji = "🟢" if pos['pl_pct'] > 0 else "🔴" if pos['pl_pct'] < 0 else "⚪"
        print(f"  {pl_emoji} {pos['symbol']}: {pos['qty']} shares @ ${pos['current_price']:.2f} | P&L: {pos['pl_pct']:+.2f}%", flush=True)
    
    print()
    
    # Portfolio P&L
    total_pl_pct = (total_pl / total_cost * 100) if total_cost > 0 else 0
    print(f"💵 TOTAL UNREALIZED P&L: ${total_pl:,.2f} ({total_pl_pct:+.2f}%)", flush=True)
    print()
    
    # Alerts
    if alerts:
        print("🚨 ALERTS:", flush=True)
        for alert in alerts:
            print(f"  {alert}", flush=True)
    else:
        print("✅ No stop-loss or profit target alerts", flush=True)
    
    print()
    print("🗑️ ~Dust Positions (under $1):", flush=True)
    dust = [p for p in position_summary if p['market_value'] < 1]
    if dust:
        for d in dust:
            print(f"  {d['symbol']}: ${d['market_value']:.4f}", flush=True)
    else:
        print("  None", flush=True)
    
    # Output for state file update
    output = {
        'timestamp': datetime.now().isoformat(),
        'account': {
            'equity': float(account.get('equity', 0)) if account else 0,
            'buying_power': float(account.get('buying_power', 0)) if account else 0,
            'cash': float(account.get('cash', 0)) if account else 0
        },
        'positions': position_summary,
        'alerts': alerts,
        'total_unrealized_pl': total_pl,
        'total_pl_pct': round(total_pl_pct, 2)
    }
    
    print("\n---JSON_START---", flush=True)
    print(json.dumps(output), flush=True)
    print("---JSON_END---", flush=True)

if __name__ == '__main__':
    main()
