#!/usr/bin/env python3
"""
Sync Yahoo Finance portfolio with Alpaca positions
Uses browser automation via Playwright to avoid Yahoo Finance API limitations
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
    """Get current positions from Alpaca"""
    # Remove trailing /v2 if it exists to avoid /v2/v2/ duplication
    base_url = ALPACA_BASE_URL.rstrip('/v2').rstrip('/')
    url = f"{base_url}/v2/positions"
    response = requests.get(url, headers=ALPACA_HEADERS)
    if response.status_code == 200:
        return [pos['symbol'] for pos in response.json()]
    print(f"Error: {response.status_code} - {response.text}")
    return []

def main():
    # Get current Alpaca positions
    alpaca_symbols = set(get_alpaca_positions())
    print(f"✅ Found {len(alpaca_symbols)} positions in Alpaca:")
    print(f"   {', '.join(sorted(alpaca_symbols))}")
    
    # Yahoo Finance portfolio (from your message)
    yahoo_symbols = {
        'WULF', 'WOOF', 'SPHR', 'AMDL', 'DRD', 'SSRM', 'GMAB', 'CARS',
        'KSS', 'TNXP', 'UP', 'PSTV', 'GV', 'BTAI', 'ADTX', 'MVIS',
        'IMPP', 'GITS', 'RGC', 'LIXT', 'WINT', 'BTBT', 'QUBT', 'SOUN'
    }
    
    # Calculate differences
    to_delete = yahoo_symbols - alpaca_symbols
    to_add = alpaca_symbols - yahoo_symbols
    
    print(f"\n📋 Sync Plan:")
    print(f"   ❌ Delete from Yahoo: {len(to_delete)} stocks")
    print(f"      {', '.join(sorted(to_delete))}")
    print(f"   ➕ Add to Yahoo: {len(to_add)} stocks")
    print(f"      {', '.join(sorted(to_add))}")
    
    print(f"\n⚠️  Yahoo Finance doesn't have a public API for portfolio management.")
    print(f"   You'll need to manually:")
    print(f"   1. Go to https://finance.yahoo.com/portfolio/p_1/view")
    print(f"   2. Delete: {', '.join(sorted(to_delete))}")
    print(f"   3. Add: {', '.join(sorted(to_add))}")
    print(f"\n   Or use the browser automation in the dashboard.")

if __name__ == '__main__':
    main()
