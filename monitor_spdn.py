#!/usr/bin/env python3
"""
Monitor SPDN for breakout above $9.50
Alert if it breaks out on volume
"""

import json
import requests
import time

with open('/Users/mikeclawd/.openclaw/secrets/polygon.json', 'r') as f:
    creds = json.load(f)

from polygon import RESTClient
client = RESTClient(api_key=creds['apiKey'])

BREAKOUT_PRICE = 9.50
SYMBOL = 'SPDN'

print(f"Monitoring {SYMBOL} for breakout above ${BREAKOUT_PRICE}")
print("Will check every 2 minutes until 1:00 PM PT close")
print()

while True:
    try:
        # Get latest price
        quote = client.get_last_quote(SYMBOL)
        price = quote.ask_price
        
        print(f"{SYMBOL}: ${price:.2f}", end="")
        
        if price >= BREAKOUT_PRICE:
            print(f" 🚨 BREAKOUT!")
            print(f"\n{SYMBOL} broke above ${BREAKOUT_PRICE}!")
            print(f"Current: ${price:.2f}")
            
            # Get volume
            bars = list(client.list_aggs(SYMBOL, 1, "minute", limit=5))
            recent_vol = sum(bar.volume for bar in bars) if bars else 0
            
            print(f"Recent volume: {recent_vol:,}")
            print("\nALERT: Send this to Mike")
            break
        else:
            print(f" (watching)")
        
        time.sleep(120)  # Check every 2 minutes
        
    except KeyboardInterrupt:
        print("\nMonitoring stopped")
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(120)
