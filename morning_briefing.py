#!/usr/bin/env python3
"""
Morning Briefing - Daily Trading Overview
Generates a formatted briefing for Telegram delivery
"""

import os
import json
import requests
from datetime import datetime, timedelta

# Alpaca credentials - robust path handling for cron
creds_paths = [
    os.path.expanduser('~/.openclaw/secrets/alpaca.json'),
    '/Users/mikeclawd/.openclaw/secrets/alpaca.json'
]

creds = None
for path in creds_paths:
    if os.path.exists(path):
        with open(path, 'r') as f:
            creds = json.load(f)
        break

if not creds:
    print("❌ ERROR: Alpaca credentials not found")
    print("   Checked: ~/.openclaw/secrets/alpaca.json")
    exit(1)

base_url = creds['baseUrl'].rstrip('/v2').rstrip('/')
data_url = 'https://data.alpaca.markets/v2'
headers = {
    'APCA-API-KEY-ID': creds['apiKey'],
    'APCA-API-SECRET-KEY': creds['apiSecret']
}

def get_account():
    """Get account info from Alpaca"""
    try:
        resp = requests.get(f"{base_url}/v2/account", headers=headers, timeout=10)
        return resp.json() if resp.status_code == 200 else None
    except Exception as e:
        return None

def get_positions():
    """Get all positions from Alpaca"""
    try:
        resp = requests.get(f"{base_url}/v2/positions", headers=headers, timeout=10)
        return resp.json() if resp.status_code == 200 else []
    except Exception as e:
        return []

def get_recent_orders():
    """Get orders from last 24 hours"""
    try:
        after = (datetime.now() - timedelta(days=1)).isoformat() + 'Z'
        params = {'status': 'all', 'after': after, 'limit': 50}
        resp = requests.get(f"{base_url}/v2/orders", headers=headers, params=params, timeout=10)
        return resp.json() if resp.status_code == 200 else []
    except Exception as e:
        return []

def get_quote(symbol):
    """Get latest quote for a symbol"""
    try:
        resp = requests.get(f"{data_url}/stocks/{symbol}/quotes/latest", headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('quote', {})
    except:
        pass
    return {}

def get_daily_bar(symbol):
    """Get daily bar for change %"""
    try:
        resp = requests.get(f"{data_url}/stocks/{symbol}/bars/latest", headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('bar', {})
    except:
        pass
    return {}

def score_stock(symbol, price):
    """Score stock setup quality 0-100"""
    bar = get_daily_bar(symbol)
    if not bar:
        return 0, "No data"
    
    open_p = bar.get('o', 0)
    close_p = bar.get('c', 0)
    volume = bar.get('v', 0)
    
    if open_p == 0:
        return 0, "Invalid data"
    
    change_pct = ((close_p - open_p) / open_p) * 100
    
    score = 0
    reasons = []
    
    # Momentum scoring (0-40 pts) - looking for 3-15% moves
    if 3 <= change_pct <= 15:
        score += 35
        reasons.append(f"+{change_pct:.1f}% momentum")
    elif 15 < change_pct <= 25:
        score += 20
        reasons.append(f"+{change_pct:.1f}% extended")
    elif change_pct > 0:
        score += 10
        reasons.append(f"+{change_pct:.1f}%")
    else:
        reasons.append(f"{change_pct:.1f}%")
    
    # Volume scoring (0-30 pts)
    if volume > 5_000_000:
        score += 30
        reasons.append("high vol")
    elif volume > 2_000_000:
        score += 20
        reasons.append("good vol")
    elif volume > 1_000_000:
        score += 10
        reasons.append("decent vol")
    
    # Price scoring (0-30 pts) - prefer $5-50 range
    if 5 <= price <= 50:
        score += 30
        reasons.append("sweet spot")
    elif 50 < price <= 100:
        score += 20
        reasons.append("higher price")
    elif 1 <= price < 5:
        score += 15
        reasons.append("lower price")
    
    return score, " | ".join(reasons)

def get_market_movers():
    """Get active stocks from Alpaca"""
    try:
        resp = requests.get(f"{data_url}/stocks/screener?active=true&limit=50", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('most_actives', [])
    except:
        pass
    return []

def main():
    now = datetime.now()
    
    # Header
    print(f"📊 MORNING BRIEFING - {now.strftime('%A, %B %d')}")
    print(f"⏰ {now.strftime('%I:%M %p PT')}")
    print("=" * 60)
    
    # Account Status
    account = get_account()
    if account:
        portfolio_value = float(account.get('portfolio_value', 0))
        cash = float(account.get('cash', 0))
        buying_power = float(account.get('buying_power', 0))
        
        print(f"\n💰 PORTFOLIO")
        print(f"   Value: ${portfolio_value:,.2f}")
        print(f"   Cash:  ${cash:,.2f}")
        print(f"   Power: ${buying_power:,.2f}")
    else:
        print("\n⚠️ Could not fetch account data")
    
    # Overnight Orders
    orders = get_recent_orders()
    filled = [o for o in orders if o.get('status') == 'filled']
    
    print(f"\n📋 OVERNIGHT ACTIVITY")
    if filled:
        for order in filled:
            symbol = order.get('symbol', 'N/A')
            side = order.get('side', 'unknown')
            qty = order.get('filled_qty', 0)
            price = float(order.get('filled_avg_price', 0))
            print(f"   ✓ {side.upper()} {qty} {symbol} @ ${price:.2f}")
    else:
        print("   No overnight fills")
    
    # Positions Summary
    positions = get_positions()
    
    print(f"\n📈 POSITIONS ({len(positions)} active)")
    
    if positions:
        # Track alerts
        profit_targets = []
        stop_losses = []
        near_targets = []
        near_stops = []
        
        total_unrealized = 0
        
        for pos in positions:
            symbol = pos.get('symbol', 'N/A')
            qty = int(float(pos.get('qty', 0)))
            avg_entry = float(pos.get('avg_entry_price', 0))
            current = float(pos.get('current_price', 0))
            
            pl_pct = ((current - avg_entry) / avg_entry * 100) if avg_entry > 0 else 0
            pl_dollar = (current - avg_entry) * qty
            total_unrealized += pl_dollar
            
            status_icon = "✅" if pl_pct > 0 else "📉"
            
            # Check for alerts
            if pl_pct >= 30:
                profit_targets.append(f"{symbol} (+{pl_pct:.1f}%)")
            elif pl_pct >= 25:
                near_targets.append(f"{symbol} (+{pl_pct:.1f}%)")
            elif pl_pct <= -15:
                stop_losses.append(f"{symbol} ({pl_pct:.1f}%)")
            elif pl_pct <= -12:
                near_stops.append(f"{symbol} ({pl_pct:.1f}%)")
            
            print(f"   {status_icon} {symbol}: {pl_pct:+.1f}% (${pl_dollar:+.2f})")
        
        print(f"\n   Total Unrealized P&L: ${total_unrealized:+.2f}")
        
        # Alerts Section
        alerts = []
        if profit_targets:
            alerts.append(f"🎯 PROFIT TARGET HIT: {', '.join(profit_targets)}")
        if stop_losses:
            alerts.append(f"🛑 STOP LOSS HIT: {', '.join(stop_losses)}")
        if near_targets:
            alerts.append(f"⚠️ NEAR TARGET: {', '.join(near_targets)}")
        if near_stops:
            alerts.append(f"⚠️ NEAR STOP: {', '.join(near_stops)}")
        
        if alerts:
            print(f"\n🚨 ALERTS")
            for alert in alerts:
                print(f"   {alert}")
    else:
        print("   No active positions")
    
    # Scanner - Top Opportunities
    print(f"\n🔍 SCANNER - Top Opportunities")
    
    movers = get_market_movers()
    candidates = []
    
    for mover in movers:
        symbol = mover.get('symbol')
        if not symbol:
            continue
        
        quote = get_quote(symbol)
        if not quote:
            continue
        
        price = float(quote.get('ap', 0)) or float(quote.get('bp', 0))
        if not price:
            continue
        
        if not (0.50 <= price <= 100):
            continue
        
        score, reason = score_stock(symbol, price)
        
        if score >= 70:
            candidates.append({
                'symbol': symbol,
                'price': price,
                'score': score,
                'reason': reason
            })
    
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    if candidates:
        print(f"   Found {len(candidates)} setups with score 7+/10")
        print()
        
        daily_budget = 300
        for i, c in enumerate(candidates[:3], 1):
            price = c['price']
            max_shares = int(daily_budget / price)
            cost = max_shares * price
            
            print(f"   #{i} {c['symbol']} - Score: {c['score']}/100")
            print(f"      Price: ${price:.2f} | {c['reason']}")
            if max_shares > 0:
                print(f"      ➜ {max_shares} shares = ${cost:.2f}")
            print()
    else:
        print("   No high-conviction setups found")
        print("   Market may be slow - wait for better entries")
    
    # Footer
    print("=" * 60)
    print("✅ Briefing complete - Market opens at 6:30 AM PT")
    print("=" * 60)

if __name__ == '__main__':
    main()
