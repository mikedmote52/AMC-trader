#!/usr/bin/env python3
"""
Portfolio Stop-Loss Check
Checks all positions for stop-loss triggers and sends alerts
"""

import json
import requests
from datetime import datetime

def check_stop_losses():
    import os
    # Load credentials - try multiple paths for cron compatibility
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
        print(f"❌ ERROR: Alpaca credentials not found")
        return 0
    
    base_url = creds['baseUrl'].rstrip('/v2').rstrip('/')
    headers = {
        'APCA-API-KEY-ID': creds['apiKey'],
        'APCA-API-SECRET-KEY': creds['apiSecret']
    }
    
    # Get positions
    positions = requests.get(f'{base_url}/v2/positions', headers=headers).json()
    
    print(f"🛡️ STOP-LOSS CHECK - {datetime.now().strftime('%I:%M %p PT')}")
    print(f"Checking {len(positions)} positions...")
    print()
    
    stops_triggered = []
    near_stops = []
    
    for pos in positions:
        symbol = pos['symbol']
        pl_pct = float(pos['unrealized_plpc']) * 100
        
        if pl_pct <= -15:
            stops_triggered.append({
                'symbol': symbol,
                'loss': pl_pct,
                'shares': int(float(pos['qty']))
            })
        elif pl_pct <= -12:
            near_stops.append({
                'symbol': symbol,
                'loss': pl_pct
            })
    
    if stops_triggered:
        print("🔴 STOP-LOSSES TRIGGERED:")
        for stop in stops_triggered:
            print(f"  {stop['symbol']}: {stop['loss']:.1f}% - SELL {stop['shares']} shares")
    else:
        print("✅ No stop-losses triggered")
    
    if near_stops:
        print()
        print("⚠️  NEAR STOP-LOSS (Monitor):")
        for near in near_stops:
            print(f"  {near['symbol']}: {near['loss']:.1f}%")
    
    print()
    print(f"Next check: Automatic")
    
    return len(stops_triggered)

if __name__ == '__main__':
    import sys
    check_stop_losses()
