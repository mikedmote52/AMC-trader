#!/usr/bin/env python3
"""
Market Open Check - Portfolio Status & Scanner
"""

import requests
import json
from datetime import datetime, timedelta

# Alpaca credentials
ALPACA_CREDS_PATH = '/Users/mikeclawd/.openclaw/secrets/alpaca.json'
with open(ALPACA_CREDS_PATH, 'r') as f:
    creds = json.load(f)

ALPACA_HEADERS = {
    'APCA-API-KEY-ID': creds['apiKey'],
    'APCA-API-SECRET-KEY': creds['apiSecret']
}

BASE_URL = creds['baseUrl'].rstrip('/v2').rstrip('/')
DATA_URL = 'https://data.alpaca.markets/v2'

# Get account info
def get_account():
    url = f"{BASE_URL}/v2/account"
    resp = requests.get(url, headers=ALPACA_HEADERS)
    return resp.json() if resp.status_code == 200 else None

# Get positions
def get_positions():
    url = f"{BASE_URL}/v2/positions"
    resp = requests.get(url, headers=ALPACA_HEADERS)
    return resp.json() if resp.status_code == 200 else []

# Get orders from last 24 hours
def get_recent_orders():
    url = f"{BASE_URL}/v2/orders"
    # Get orders from last 24 hours
    after = (datetime.now() - timedelta(days=1)).isoformat() + 'Z'
    params = {'status': 'all', 'after': after, 'limit': 50}
    resp = requests.get(url, headers=ALPACA_HEADERS, params=params)
    return resp.json() if resp.status_code == 200 else []

# Get market movers for scanning
def get_market_movers():
    """Get active stocks from Alpaca most active"""
    url = f"{DATA_URL}/stocks/screener"
    params = {
        'active': 'true',
        'limit': 50
    }
    resp = requests.get(url, headers=ALPACA_HEADERS, params=params)
    if resp.status_code == 200:
        data = resp.json()
        return data.get('most_actives', [])
    return []

# Get latest quote for a symbol
def get_quote(symbol):
    url = f"{DATA_URL}/stocks/{symbol}/quotes/latest"
    resp = requests.get(url, headers=ALPACA_HEADERS)
    if resp.status_code == 200:
        data = resp.json()
        return data.get('quote', {})
    return {}

# Get daily bar for change %
def get_daily_bar(symbol):
    url = f"{DATA_URL}/stocks/{symbol}/bars/latest"
    resp = requests.get(url, headers=ALPACA_HEADERS)
    if resp.status_code == 200:
        data = resp.json()
        return data.get('bar', {})
    return {}

# Score a stock for setup quality
def score_stock(symbol, price):
    """
    Score 0-100 based on setup quality
    - Momentum: 0-40 points
    - Volume: 0-30 points  
    - Price action: 0-30 points
    """
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
        reasons.append(f"✓ +{change_pct:.1f}% momentum")
    elif 15 < change_pct <= 25:
        score += 20
        reasons.append(f"⚠ +{change_pct:.1f}% extended")
    elif change_pct > 0:
        score += 10
        reasons.append(f"+{change_pct:.1f}%")
    else:
        reasons.append(f"{change_pct:.1f}%")
    
    # Volume scoring (0-30 pts)
    if volume > 5_000_000:
        score += 30
        reasons.append("high volume")
    elif volume > 2_000_000:
        score += 20
        reasons.append("good volume")
    elif volume > 1_000_000:
        score += 10
        reasons.append("decent volume")
    
    # Price scoring (0-30 pts) - prefer $5-50 range
    if 5 <= price <= 50:
        score += 30
        reasons.append("sweet spot price")
    elif 50 < price <= 100:
        score += 20
        reasons.append("higher price")
    elif 1 <= price < 5:
        score += 15
        reasons.append("lower price")
    
    return score, " | ".join(reasons)

# Main execution
print("=" * 70)
print(f"📊 MARKET OPEN CHECK - {datetime.now().strftime('%A, %B %d at %I:%M %p PT')}")
print("=" * 70)

# 1. ACCOUNT STATUS
print("\n💰 PORTFOLIO STATUS")
print("-" * 70)

account = get_account()
if account:
    portfolio_value = float(account.get('portfolio_value', 0))
    cash = float(account.get('cash', 0))
    buying_power = float(account.get('buying_power', 0))
    
    print(f"Portfolio Value: ${portfolio_value:,.2f}")
    print(f"Cash Available:  ${cash:,.2f}")
    print(f"Buying Power:    ${buying_power:,.2f}")
else:
    print("❌ Could not fetch account data")

# 2. OVERNIGHT ORDERS
print("\n📋 OVERNIGHT ORDER FILLS")
print("-" * 70)

orders = get_recent_orders()
filled_orders = [o for o in orders if o.get('status') == 'filled']

if filled_orders:
    for order in filled_orders:
        symbol = order.get('symbol', 'N/A')
        side = order.get('side', 'unknown')
        qty = order.get('filled_qty', 0)
        price = float(order.get('filled_avg_price', 0))
        value = qty * price
        
        print(f"  ✓ {side.upper()} {qty} shares {symbol} @ ${price:.2f} = ${value:,.2f}")
else:
    print("  No overnight fills")

# 3. CURRENT POSITIONS
print("\n📈 ACTIVE POSITIONS")
print("-" * 70)

positions = get_positions()
if positions:
    total_pl = 0
    total_pl_pct = 0
    
    # Header
    print(f"{'Symbol':<8} {'Qty':<6} {'Avg Cost':<10} {'Current':<10} {'P&L $':<12} {'P&L %':<8} {'Status'}")
    print("-" * 70)
    
    for pos in positions:
        symbol = pos.get('symbol', 'N/A')
        qty = int(float(pos.get('qty', 0)))
        avg_entry = float(pos.get('avg_entry_price', 0))
        current = float(pos.get('current_price', 0))
        lastday = float(pos.get('lastday_price', avg_entry))
        
        pl = (current - avg_entry) * qty
        pl_pct = ((current - avg_entry) / avg_entry * 100) if avg_entry > 0 else 0
        
        total_pl += pl
        
        # Status indicator
        status = ""
        if pl_pct >= 30:
            status = "🎯 TAKE PROFIT"
        elif pl_pct >= 20:
            status = "📈 Strong"
        elif pl_pct <= -15:
            status = "🛑 STOP HIT"
        elif pl_pct <= -10:
            status = "⚠️ Watch"
        
        print(f"{symbol:<8} {qty:<6} ${avg_entry:<9.2f} ${current:<9.2f} ${pl:<11.2f} {pl_pct:>+6.1f}% {status}")
    
    print("-" * 70)
    print(f"{'TOTAL':<8} {'':<6} {'':<10} {'':<10} ${total_pl:<11.2f}")
    print(f"\nTotal Positions: {len(positions)} stocks")
else:
    print("  No active positions")

# 4. SCANNER - FIND OPPORTUNITIES
print("\n" + "=" * 70)
print("🔍 SCANNER: TOP OPPORTUNITIES (7+/10 Score)")
print("=" * 70)
print("Criteria: $0.50-$100 price, momentum +3-15%, volume >1M")
print("-" * 70)

# Get active stocks
movers = get_market_movers()
print(f"Scanning {len(movers)} active stocks...\n")

candidates = []
for mover in movers:
    symbol = mover.get('symbol')
    if not symbol:
        continue
    
    # Get current price
    quote = get_quote(symbol)
    if not quote:
        continue
    
    price = float(quote.get('ap', 0))  # Ask price
    if price == 0:
        price = float(quote.get('bp', 0))  # Bid price
    if price == 0:
        continue
    
    # Filter by price range
    if not (0.50 <= price <= 100):
        continue
    
    # Score the setup
    score, reason = score_stock(symbol, price)
    
    if score >= 70:  # 7+/10
        candidates.append({
            'symbol': symbol,
            'price': price,
            'score': score,
            'reason': reason
        })

# Sort by score descending
candidates.sort(key=lambda x: x['score'], reverse=True)

# Show top picks
if candidates:
    print(f"{'Symbol':<8} {'Price':<10} {'Score':<8} {'Thesis'}")
    print("-" * 70)
    
    for c in candidates[:5]:
        print(f"{c['symbol']:<8} ${c['price']:<9.2f} {c['score']:<8} {c['reason']}")
    
    print("\n" + "=" * 70)
    print("💡 BUY RECOMMENDATIONS ($300 daily budget)")
    print("=" * 70)
    
    daily_budget = 300
    for i, c in enumerate(candidates[:3], 1):
        price = c['price']
        max_shares = int(daily_budget / price)
        cost = max_shares * price
        
        if max_shares > 0:
            print(f"\n#{i}: {c['symbol']}")
            print(f"  Price: ${price:.2f}")
            print(f"  Score: {c['score']}/100")
            print(f"  Thesis: {c['reason']}")
            print(f"  ➜ BUY {max_shares} shares = ${cost:.2f}")
else:
    print("  No 7+/10 setups found in current scan")
    print("  Market may be slow or extended - wait for better entries")

print("\n" + "=" * 70)
print("✅ Market Open Check Complete")
print("=" * 70)
