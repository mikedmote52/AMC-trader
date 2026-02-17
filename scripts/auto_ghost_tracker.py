#!/usr/bin/env python3
"""
Automatic Ghost Portfolio Tracker
Monitors closed positions in portfolio_daily_log.csv
Auto-adds to ghost tracking when we sell
"""

import csv
import json
import os
from datetime import datetime

GHOST_FILE = '../data/ghost_portfolio.json'
DAILY_LOG = '../data/portfolio_daily_log.csv'

def load_ghost_portfolio():
    if os.path.exists(GHOST_FILE):
        with open(GHOST_FILE, 'r') as f:
            return json.load(f)
    return []

def save_ghost_portfolio(ghosts):
    os.makedirs(os.path.dirname(GHOST_FILE), exist_ok=True)
    with open(GHOST_FILE, 'w') as f:
        json.dump(ghosts, f, indent=2)

def check_for_new_exits():
    """Check daily log for positions that closed (Action Taken column)"""
    if not os.path.exists(DAILY_LOG):
        return
    
    ghosts = load_ghost_portfolio()
    ghost_symbols = [g['symbol'] for g in ghosts]
    
    with open(DAILY_LOG, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = row['Symbol']
            action = row.get('Action Taken', '')
            
            # Check if this is a sell action and not already tracked
            if 'SOLD' in action.upper() and symbol not in ghost_symbols:
                # Parse the row
                try:
                    ghost = {
                        'symbol': symbol,
                        'sell_date': row['Date'],
                        'sell_price': float(row['Current']),
                        'original_entry': float(row['Entry']),
                        'shares_sold': int(float(row['Qty'])),  # Approximate
                        'profit_at_exit': float(row['P&L %']),
                        'exit_reason': action,
                        'added': datetime.now().isoformat()
                    }
                    
                    ghosts.append(ghost)
                    ghost_symbols.append(symbol)
                    print(f"✅ Auto-added {symbol} to ghost portfolio (exited @ +{ghost['profit_at_exit']:.1f}%)")
                except (ValueError, KeyError) as e:
                    print(f"⚠️  Couldn't parse {symbol}: {e}")
    
    save_ghost_portfolio(ghosts)

if __name__ == '__main__':
    check_for_new_exits()
