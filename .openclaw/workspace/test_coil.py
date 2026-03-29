#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/mikeclawd/.openclaw/workspace/scripts')
from coil_detector import detect_coil_setup, get_coil_entry_trigger
from polygon import RESTClient
import json

with open('/Users/mikeclawd/.openclaw/secrets/polygon.json') as f:
    creds = json.load(f)
client = RESTClient(api_key=creds['apiKey'])

from datetime import datetime, timedelta

end = datetime.now().strftime('%Y-%m-%d')
start = (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')

print('Testing COIL DETECTOR on recent stocks...')
print('=' * 60)

for symbol in ['TPET', 'USEG', 'ENSC']:
    try:
        bars = list(client.list_aggs(symbol, 1, 'day', start, end, limit=15))
        print(f'\n{symbol}: {len(bars)} days of data')
        
        coil_score, desc = detect_coil_setup(symbol, bars)
        if coil_score > 0:
            print(f'COIL DETECTED: Score {coil_score}')
            print(f'   {desc}')
            entry, stop = get_coil_entry_trigger(symbol, bars)
            if entry:
                print(f'   Entry on break: ${entry:.2f}')
                print(f'   Stop below: ${stop:.2f}')
        else:
            print(f'No coil pattern')
    except Exception as e:
        print(f'   Error: {e}')

print()
print('=' * 60)
