#!/usr/bin/env python3
"""
Execute Trade - Always require thesis before buying
- Checks daily limit before executing
- Logs thesis to portfolio_tracking.csv
- Logs trade to memory/YYYY-MM-DD.md
"""

import json
import requests
import sys
from datetime import datetime
from pathlib import Path
from scanner_performance_tracker import link_trade_to_scan
from pytz import timezone

WORKSPACE = Path('/Users/mikeclawd/.openclaw/workspace')
SECRETS = Path('/Users/mikeclawd/.openclaw/secrets/alpaca.json')

with open(SECRETS) as f:
    creds = json.load(f)

headers = {
    'APCA-API-KEY-ID': creds['apiKey'],
    'APCA-API-SECRET-KEY': creds['apiSecret']
}

BASE_URL = 'https://paper-api.alpaca.markets/v2'

def check_daily_limit():
    """Check how much has been spent today"""
    # Get today's orders
    today = datetime.now().strftime('%Y-%m-%d')
    
    resp = requests.get(f'{BASE_URL}/orders', headers=headers, params={
        'status': 'filled',
        'after': today + 'T00:00:00-08:00'
    })
    
    orders = resp.json()
    
    # Calculate total buys today
    total_spent = 0
    for order in orders:
        if order['side'] == 'buy':
            filled_qty = float(order['filled_qty'])
            filled_price = float(order['filled_avg_price'])
            total_spent += filled_qty * filled_price
    
    return total_spent

def execute_order(symbol, qty, side, order_type='market', limit_price=None, stop_price=None):
    """Execute order via Alpaca with IOC (immediate-or-cancel)"""
    order_data = {
        'symbol': symbol,
        'qty': qty,
        'side': side,
        'type': order_type,
        'time_in_force': 'ioc'  # IMMEDIATE OR CANCEL - no overnight holds
    }
    
    if limit_price:
        order_data['limit_price'] = limit_price
    if stop_price:
        order_data['stop_price'] = stop_price
    
    resp = requests.post(f'{BASE_URL}/orders', headers=headers, json=order_data)
    return resp.json()

def log_trade(symbol, qty, side, price, thesis=None):
    """Log trade to daily memory"""
    today = datetime.now().strftime('%Y-%m-%d')
    timestamp = datetime.now().strftime('%H:%M:%S PT')
    memory_file = WORKSPACE / f'memory/{today}.md'
    
    # Create memory file if it doesn't exist
    if not memory_file.exists():
        memory_file.parent.mkdir(exist_ok=True)
        memory_file.write_text(f"# Daily Log - {today}\n\n")
    
    # Append trade
    with open(memory_file, 'a') as f:
        f.write(f"\n## {timestamp} - {side.upper()} {symbol}\n")
        f.write(f"- Qty: {qty}\n")
        f.write(f"- Price: ${price:.2f}\n")
        if thesis:
            f.write(f"- Thesis: {thesis}\n")

def is_market_open_for_trading():
    """Check if US market is open for new trades (6:30 AM - 1:00 PM PT)"""
    PT = timezone('America/Los_Angeles')
    ET = timezone('America/New_York')
    
    now_pt = datetime.now(PT)
    now_et = now_pt.astimezone(ET)
    
    hour_pt = now_pt.hour + now_pt.minute / 60.0
    hour_et = now_et.hour + now_et.minute / 60.0
    
    # Trading window: 6:30 AM PT to 1:00 PM PT (9:30 AM - 4:00 PM ET)
    # But we stop taking new trades at 1 PM PT to avoid afternoon fade
    TRADING_START_PT = 6.5  # 6:30 AM PT
    TRADING_END_PT = 13.0    # 1:00 PM PT (hard stop)
    
    # Check weekend
    if now_et.weekday() >= 5:
        return False, "Weekend - markets closed"
    
    # Check market hours
    if hour_pt < TRADING_START_PT:
        return False, f"Too early ({now_pt.strftime('%I:%M %p')} PT) - trading starts 6:30 AM PT"
    
    if hour_pt > TRADING_END_PT:
        return False, f"Too late ({now_pt.strftime('%I:%M %p')} PT) - no new trades after 1:00 PM PT"
    
    # Check if market is actually open (9:30 AM - 4:00 PM ET)
    if hour_et < 9.5 or hour_et >= 16.0:
        return False, f"Markets closed ({now_et.strftime('%I:%M %p')} ET)"
    
    return True, f"Markets open ({now_pt.strftime('%I:%M %p')} PT / {now_et.strftime('%I:%M %p')} ET)"


def buy_with_thesis(symbol, dollar_amount, thesis):
    """Buy stock with required thesis"""
    
    # CRITICAL: Check market hours FIRST
    market_ok, market_msg = is_market_open_for_trading()
    if not market_ok:
        print(f"❌ MARKET HOURS VIOLATION: {market_msg}")
        print(f"   Trade rejected to prevent overnight gap risk.")
        return None
    else:
        print(f"✅ {market_msg}")
    
    # Check daily limit
    spent_today = check_daily_limit()
    remaining = 300 - spent_today
    
    if dollar_amount > remaining:
        print(f"❌ OVER DAILY LIMIT!")
        print(f"   Spent today: ${spent_today:.2f}")
        print(f"   Remaining: ${remaining:.2f}")
        print(f"   Requested: ${dollar_amount:.2f}")
        return None
    
    # Get current price
    resp = requests.get(f'{BASE_URL}/positions/{symbol}', headers=headers)
    if resp.status_code == 200:
        # Already have position
        current_price = float(resp.json()['current_price'])
    else:
        # Get latest trade
        resp = requests.get(f'https://data.alpaca.markets/v2/stocks/{symbol}/trades/latest', 
                          headers=headers)
        current_price = float(resp.json()['trade']['p'])
    
    # Calculate qty
    qty = int(dollar_amount / current_price)
    
    if qty == 0:
        print(f"❌ Dollar amount too small (${dollar_amount:.2f} / ${current_price:.2f} = 0 shares)")
        return None
    
    actual_cost = qty * current_price
    
    # Confirm with user
    print(f"\n📊 TRADE CONFIRMATION:")
    print(f"   Symbol: {symbol}")
    print(f"   Qty: {qty} shares")
    print(f"   Price: ${current_price:.2f}")
    print(f"   Cost: ${actual_cost:.2f}")
    print(f"   Thesis: {thesis}")
    print(f"\n   Spent today: ${spent_today:.2f}")
    print(f"   After trade: ${spent_today + actual_cost:.2f} / $300")
    print(f"   Remaining: ${remaining - actual_cost:.2f}")
    
    confirm = input("\nExecute? (yes/no): ")
    if confirm.lower() != 'yes':
        print("❌ Trade cancelled")
        return None
    
    # Execute
    order = execute_order(symbol, qty, 'buy')
    
    if 'id' in order:
        print(f"✅ Order placed: {order['id']}")
        log_trade(symbol, qty, 'buy', current_price, thesis)

        # Link to scanner pick for performance tracking
        try:
            link_trade_to_scan(symbol, current_price, thesis)
        except Exception as e:
            print(f"⚠️  Could not link to scanner: {e}")

        return order
    else:
        print(f"❌ Order failed: {order}")
        return None

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python3 execute_trade.py <symbol> <dollar_amount> <thesis>")
        print("Example: python3 execute_trade.py AAPL 150 'Breaking above resistance, volume spike'")
        sys.exit(1)
    
    symbol = sys.argv[1].upper()
    dollar_amount = float(sys.argv[2])
    thesis = ' '.join(sys.argv[3:])
    
    buy_with_thesis(symbol, dollar_amount, thesis)
