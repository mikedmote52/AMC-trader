import json
import sys
from datetime import datetime

# Load Alpaca API
try:
    from alpaca.trading.client import TradingClient
    print('✅ Alpaca TradingClient imported')
except Exception as e:
    print(f'❌ Error importing Alpaca: {e}')
    sys.exit(1)

# Load credentials
try:
    with open('/Users/mikeclawd/.openclaw/secrets/alpaca.json', 'r') as f:
        creds = json.load(f)
    print('✅ Credentials loaded')
    client = TradingClient(creds['apiKey'], creds['apiSecret'], paper=True)
    print('✅ TradingClient initialized')
except Exception as e:
    print(f'❌ Error with credentials/client: {e}')
    sys.exit(1)

# Get account info
try:
    account = client.get_account()
    print(f'Portfolio Value: ${float(account.portfolio_value):,.2f}')
    print(f'Cash: ${float(account.cash):,.2f}')
except Exception as e:
    print(f'❌ Error getting account: {e}')

# Get positions
try:
    positions = client.get_all_positions()
    print(f'\nTotal Positions: {len(positions)}')
    
    all_positions = []
    for pos in positions:
        symbol = pos.symbol
        qty = float(pos.qty)
        avg_entry = float(pos.avg_entry_price)
        current = float(pos.current_price)
        unrealized_pl = float(pos.unrealized_pl)
        unrealized_plpc = float(pos.unrealized_plpc) * 100
        
        status = '📈' if unrealized_plpc > 0 else '📉' if unrealized_plpc < 0 else '📊'
        if unrealized_plpc >= 20:
            status = '🎯 SCALE-OUT'
        if unrealized_plpc <= -15:
            status = '🚨 STOP-LOSS'
        
        all_positions.append({
            'symbol': symbol,
            'qty': qty,
            'avg_entry': avg_entry,
            'current': current,
            'pl': unrealized_pl,
            'plpc': unrealized_plpc,
            'status': status
        })
    
    # Sort by P/L %
    all_positions.sort(key=lambda x: x['plpc'], reverse=True)</think><|tool_calls_section_begin|><|tool_call_begin|>functions.exec:17<|tool_call_argument_begin|>{