#!/usr/bin/env python3
"""
Ghost Portfolio Tracker
Continues tracking stocks AFTER we sell to see "what could have been"
Helps optimize exit strategy
"""

import json
import requests
from datetime import datetime
import os

# Load Alpaca credentials
with open('/Users/mikeclawd/.openclaw/secrets/alpaca.json', 'r') as f:
    creds = json.load(f)

base_url = creds['baseUrl'].rstrip('/v2').rstrip('/')
headers = {
    'APCA-API-KEY-ID': creds['apiKey'],
    'APCA-API-SECRET-KEY': creds['apiSecret']
}

GHOST_FILE = 'data/ghost_portfolio.json'

def load_ghost_portfolio():
    """Load ghost positions from file"""
    if os.path.exists(GHOST_FILE):
        with open(GHOST_FILE, 'r') as f:
            return json.load(f)
    return []

def save_ghost_portfolio(ghosts):
    """Save ghost positions to file"""
    os.makedirs('data', exist_ok=True)
    with open(GHOST_FILE, 'w') as f:
        json.dump(ghosts, f, indent=2)

def add_ghost_position(symbol, sell_date, sell_price, original_entry, shares_sold, profit_pct, reason):
    """Add a position to ghost tracking after selling"""
    ghosts = load_ghost_portfolio()
    
    ghost = {
        'symbol': symbol,
        'sell_date': sell_date,
        'sell_price': sell_price,
        'original_entry': original_entry,
        'shares_sold': shares_sold,
        'profit_at_exit': profit_pct,
        'exit_reason': reason,
        'added': datetime.now().isoformat()
    }
    
    ghosts.append(ghost)
    save_ghost_portfolio(ghosts)
    print(f"✅ Added {symbol} to ghost portfolio (exited @ +{profit_pct:.1f}%)")

def get_current_price(symbol):
    """Get current price from Alpaca"""
    try:
        url = f"{base_url}/v2/stocks/{symbol}/quotes/latest"
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return float(data['quote']['ap'])  # Ask price
    except:
        pass
    return None

def update_ghost_portfolio():
    """Update all ghost positions with current prices"""
    ghosts = load_ghost_portfolio()
    
    print('='*80)
    print(f'👻 GHOST PORTFOLIO - What We Left Behind')
    print(f'Updated: {datetime.now().strftime("%Y-%m-%d %I:%M %p PT")}')
    print('='*80)
    print()
    
    total_missed = 0
    total_would_be = 0
    
    for ghost in ghosts:
        symbol = ghost['symbol']
        current = get_current_price(symbol)
        
        if current is None:
            print(f"⚠️  {symbol} - Can't get current price")
            continue
        
        sell_price = ghost['sell_price']
        original_entry = ghost['original_entry']
        profit_at_exit = ghost['profit_at_exit']
        
        # Calculate what we WOULD have now
        current_from_entry = ((current - original_entry) / original_entry) * 100
        additional_gain = current_from_entry - profit_at_exit
        
        # Calculate dollar impact
        shares = ghost['shares_sold']
        missed_dollars = (current - sell_price) * shares
        
        status = '🚀' if additional_gain > 50 else '📈' if additional_gain > 20 else '✅' if additional_gain > 0 else '📉'
        
        print(f'{status} {symbol:6}')
        print(f'   Entry: ${original_entry:.2f} → Exit: ${sell_price:.2f} @ +{profit_at_exit:.1f}%')
        print(f'   Now: ${current:.2f} (+{current_from_entry:.1f}% from entry)')
        print(f'   Missed: +{additional_gain:.1f}% (${missed_dollars:+.2f} on {shares} shares)')
        print(f'   Exit reason: {ghost["exit_reason"]}')
        print(f'   Days since exit: {(datetime.now() - datetime.fromisoformat(ghost["sell_date"])).days}')
        print()
        
        total_missed += additional_gain
        total_would_be += missed_dollars
    
    if ghosts:
        print('='*80)
        print(f'SUMMARY:')
        print(f'  Positions tracked: {len(ghosts)}')
        print(f'  Avg additional gain missed: {total_missed/len(ghosts):.1f}%')
        print(f'  Total $ left on table: ${total_would_be:+.2f}')
        print('='*80)
        
        # Analysis
        print()
        print('💡 INSIGHTS:')
        
        big_misses = [g for g in ghosts if (get_current_price(g['symbol']) or 0) > g['sell_price'] * 1.2]
        if big_misses:
            print(f"   • {len(big_misses)} positions ran +20% AFTER we sold")
            print(f"   • Consider: Trailing stops instead of fixed exits")
        
        early_exits = [g for g in ghosts if 'scale' in g['exit_reason'].lower() and 
                      (get_current_price(g['symbol']) or 0) > g['sell_price'] * 1.5]
        if early_exits:
            print(f"   • {len(early_exits)} scaled positions ran +50% more")
            print(f"   • Consider: Scale at +30%, +60%, +100% (keep 25% runner)")

def compare_exit_strategies():
    """Compare different exit strategies on ghost portfolio"""
    ghosts = load_ghost_portfolio()
    
    strategies = {
        'Current (30%/50%)': [],
        'Trailing 15%': [],
        'Scale 30%/60%/100%': [],
        'Never Sell (HODL)': []
    }
    
    print()
    print('='*80)
    print('📊 EXIT STRATEGY COMPARISON')
    print('='*80)
    
    for ghost in ghosts:
        symbol = ghost['symbol']
        current = get_current_price(symbol)
        if not current:
            continue
        
        entry = ghost['original_entry']
        peak_gain = ((current - entry) / entry) * 100
        
        # Current strategy (actual)
        strategies['Current (30%/50%)'].append(ghost['profit_at_exit'])
        
        # Trailing 15% (would exit at peak - 15%)
        trailing_exit = peak_gain - 15
        strategies['Trailing 15%'].append(max(trailing_exit, ghost['profit_at_exit']))
        
        # Scale 30/60/100 (50% at +30%, 25% at +60%, 25% at +100%)
        if peak_gain >= 100:
            scale_exit = (0.5 * 30) + (0.25 * 60) + (0.25 * 100)
        elif peak_gain >= 60:
            scale_exit = (0.5 * 30) + (0.5 * 60)
        elif peak_gain >= 30:
            scale_exit = 30
        else:
            scale_exit = ghost['profit_at_exit']
        strategies['Scale 30%/60%/100%'].append(scale_exit)
        
        # HODL
        strategies['Never Sell (HODL)'].append(peak_gain)
    
    print()
    for strategy, results in strategies.items():
        if results:
            avg = sum(results) / len(results)
            print(f'{strategy:25} → Avg return: +{avg:.1f}%')
    
    print('='*80)

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'add':
        # Add a ghost position
        # Usage: python ghost_portfolio_tracker.py add PTNM 2026-02-13 10.31 2.20 2 368.6 "Scale out 50%"
        if len(sys.argv) != 9:
            print("Usage: python ghost_portfolio_tracker.py add SYMBOL SELL_DATE SELL_PRICE ENTRY SHARES PROFIT_PCT REASON")
        else:
            add_ghost_position(
                symbol=sys.argv[2],
                sell_date=sys.argv[3],
                sell_price=float(sys.argv[4]),
                original_entry=float(sys.argv[5]),
                shares_sold=int(sys.argv[6]),
                profit_pct=float(sys.argv[7]),
                reason=sys.argv[8]
            )
    else:
        # Update and show ghost portfolio
        update_ghost_portfolio()
        compare_exit_strategies()
