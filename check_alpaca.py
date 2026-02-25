#!/usr/bin/env python3
import alpaca_trade_api as tradeapi
import os
from datetime import datetime

# Check credentials
api_key = os.environ.get('ALPACA_API_KEY')
secret_key = os.environ.get('ALPACA_SECRET_KEY')
base_url = os.environ.get('ALPACA_BASE_URL', 'https://api.alpaca.markets')

print('Alpaca API Check:')
print(f'API Key present: {bool(api_key)}')
print(f'Secret Key present: {bool(secret_key)}')
print(f'Base URL: {base_url}')

if api_key and secret_key:
    try:
        api = tradeapi.REST(api_key, secret_key, base_url, api_version='v2')
        account = api.get_account()
        print(f'\nAccount connected successfully!')
        print(f'Account ID: {account.id}')
        print(f'Cash: ${float(account.cash):,.2f}')
        print(f'Portfolio Value: ${float(account.portfolio_value):,.2f}')
        print(f'Buying Power: ${float(account.buying_power):,.2f}')
        
        # Get positions
        positions = api.list_positions()
        print(f'\nCurrent Positions: {len(positions)}')
        for pos in positions:
            pl_pct = (float(pos.unrealized_pl) / float(pos.cost_basis)) * 100 if float(pos.cost_basis) > 0 else 0
            print(f'{pos.symbol}: {pos.qty} shares @ ${float(pos.avg_entry_price):.2f} | P/L: {pl_pct:+.2f}%')
    except Exception as e:
        print(f'\nError connecting to Alpaca: {e}')
else:
    print('\nMissing Alpaca API credentials in environment')
