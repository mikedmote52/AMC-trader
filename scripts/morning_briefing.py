#!/usr/bin/env python3
"""
Morning Briefing - Run at 6:00 AM PT
- Portfolio overnight status
- Stop-losses triggered?
- Top 3 priorities for the day
- Premarket movers
"""

import json
import requests
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))
from telegram_alert import send_alert

WORKSPACE = Path('/Users/mikeclawd/.openclaw/workspace')
SECRETS = Path('/Users/mikeclawd/.openclaw/secrets/alpaca.json')

with open(SECRETS) as f:
    creds = json.load(f)

headers = {
    'APCA-API-KEY-ID': creds['apiKey'],
    'APCA-API-SECRET-KEY': creds['apiSecret']
}

BASE_URL = 'https://paper-api.alpaca.markets/v2'

def get_positions():
    """Get current positions"""
    resp = requests.get(f'{BASE_URL}/positions', headers=headers)
    return resp.json()

def get_account():
    """Get account info"""
    resp = requests.get(f'{BASE_URL}/account', headers=headers)
    return resp.json()

def check_overnight_fills():
    """Check if any stop-losses filled overnight"""
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    resp = requests.get(f'{BASE_URL}/orders', headers=headers, params={
        'status': 'filled',
        'after': yesterday + 'T16:00:00-05:00'  # After market close ET
    })
    
    overnight_fills = []
    for order in resp.json():
        filled_at = datetime.fromisoformat(order['filled_at'].replace('Z', '+00:00'))
        if filled_at.hour >= 16 or filled_at.hour < 9:  # After hours
            overnight_fills.append(order)
    
    return overnight_fills

def generate_briefing(positions, account, overnight_fills):
    """Generate morning briefing"""
    today = datetime.now().strftime('%A, %B %d, %Y')
    
    briefing = f"🌅 MORNING BRIEFING - {today}\n"
    briefing += "=" * 60 + "\n\n"
    
    # Account status
    portfolio_value = float(account['portfolio_value'])
    cash = float(account['cash'])
    buying_power = float(account['buying_power'])
    
    briefing += f"💰 Portfolio: ${portfolio_value:,.2f}\n"
    briefing += f"💵 Cash: ${cash:,.2f}\n"
    briefing += f"🎯 Positions: {len(positions)}\n"
    briefing += f"📊 Daily Budget: $300\n\n"
    
    # Overnight fills
    if overnight_fills:
        briefing += "🔔 OVERNIGHT ACTIVITY:\n"
        briefing += "-" * 60 + "\n"
        for order in overnight_fills:
            sym = order['symbol']
            side = order['side'].upper()
            qty = order['filled_qty']
            price = order['filled_avg_price']
            briefing += f"  {side} {qty} {sym} @ ${price}\n"
        briefing += "\n"
    
    # Positions near stop-loss
    at_risk = []
    profit_taking = []
    
    for pos in positions:
        sym = pos['symbol']
        pnl_pct = float(pos['unrealized_plpc']) * 100
        pnl_usd = float(pos['unrealized_pl'])
        
        if pnl_pct <= -12:
            at_risk.append((sym, pnl_pct, pnl_usd))
        elif pnl_pct >= 30:
            profit_taking.append((sym, pnl_pct, pnl_usd))
    
    if at_risk:
        briefing += "⚠️  POSITIONS AT RISK (near stop-loss):\n"
        briefing += "-" * 60 + "\n"
        for sym, pct, usd in at_risk:
            briefing += f"  {sym}: {pct:.1f}% (${usd:+.2f})\n"
        briefing += "\n"
    
    if profit_taking:
        briefing += "💰 PROFIT TAKING OPPORTUNITIES:\n"
        briefing += "-" * 60 + "\n"
        for sym, pct, usd in profit_taking:
            briefing += f"  {sym}: {pct:.1f}% (${usd:+.2f}) - SCALE OUT\n"
        briefing += "\n"
    
    # Top 3 priorities
    briefing += "🎯 TODAY'S PRIORITIES:\n"
    briefing += "-" * 60 + "\n"
    briefing += "1. Run premarket scanner (6:30 AM)\n"
    briefing += "2. Review positions for profit-taking\n"
    briefing += "3. Find 2-3 new setups within $300 budget\n\n"
    
    return briefing

def main():
    positions = get_positions()
    account = get_account()
    overnight_fills = check_overnight_fills()

    briefing = generate_briefing(positions, account, overnight_fills)
    print(briefing)

    # Save to file
    today = datetime.now().strftime('%Y-%m-%d')
    briefing_file = WORKSPACE / f'data/morning_briefing_{today}.txt'
    with open(briefing_file, 'w') as f:
        f.write(briefing)

    # Send to Telegram
    try:
        send_alert(f"🌅 *MORNING BRIEFING*\n\n{briefing}")
        print("✅ Sent to Telegram")
    except Exception as e:
        print(f"⚠️  Failed to send Telegram alert: {e}")

    return briefing

if __name__ == '__main__':
    main()
