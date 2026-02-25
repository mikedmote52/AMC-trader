#!/usr/bin/env python3
import alpaca_trade_api as tradeapi
import json
import os
from datetime import datetime

# Load credentials from secrets file
with open('/Users/mikeclawd/.openclaw/secrets/alpaca.json', 'r') as f:
    creds = json.load(f)

api_key = creds['apiKey']
secret_key = creds['apiSecret']
base_url = creds['baseUrl']

print('Morning Trades Execution - February 24, 2026')
print('=' * 60)
print(f'Time: {datetime.now().strftime("%H:%M:%S")} PT')

# Connect to Alpaca
api = tradeapi.REST(api_key, secret_key, base_url, api_version='v2')

# Get account info
account = api.get_account()
cash = float(account.cash)
portfolio_value = float(account.portfolio_value)
buying_power = float(account.buying_power)

print(f'\nAccount Status:')
print(f'  Cash: ${cash:,.2f}')
print(f'  Portfolio Value: ${portfolio_value:,.2f}')
print(f'  Buying Power: ${buying_power:,.2f}')

# Get current positions
positions = api.list_positions()
print(f'\nPortfolio Positions: {len(positions)} stocks')
print('-' * 60)

# Trading rules
STOP_LOSS_PCT = -15.0
PROFIT_TARGET_PCT = 30.0

positions_data = []
trades_executed = []
stop_loss_triggered = []
profit_target_triggered = []

for pos in positions:
    symbol = pos.symbol
    qty = float(pos.qty)
    avg_entry = float(pos.avg_entry_price)
    current_price = float(pos.current_price)
    market_value = float(pos.market_value)
    unrealized_pl = float(pos.unrealized_pl)
    cost_basis = float(pos.cost_basis)
    
    pl_pct = (unrealized_pl / cost_basis) * 100 if cost_basis > 0 else 0
    
    status = "HOLD"
    if pl_pct <= STOP_LOSS_PCT:
        status = "STOP-LOSS"
        stop_loss_triggered.append({
            'symbol': symbol,
            'qty': qty,
            'pl_pct': pl_pct,
            'current_price': current_price
        })
    elif pl_pct >= PROFIT_TARGET_PCT:
        status = "PROFIT-TAKE"
        profit_target_triggered.append({
            'symbol': symbol,
            'qty': qty,
            'pl_pct': pl_pct,
            'current_price': current_price
        })
    
    positions_data.append({
        'symbol': symbol,
        'qty': qty,
        'avg_entry': avg_entry,
        'current_price': current_price,
        'market_value': market_value,
        'pl_pct': pl_pct,
        'status': status
    })
    
    status_icon = "🔴" if status == "STOP-LOSS" else ("🟢" if status == "PROFIT-TAKE" else "⚪")
    print(f'{status_icon} {symbol:5} | Qty: {qty:3} | P/L: {pl_pct:+7.2f}% | Value: ${market_value:,.2f}')

print('-' * 60)

# Execute trades
print('\nExecuting Trades:')
print('=' * 60)

# Execute stop-loss trades
for trade in stop_loss_triggered:
    try:
        print(f'\n🔴 STOP-LOSS: Selling {trade["qty"]} shares of {trade["symbol"]} @ ${trade["current_price"]:.2f} ({trade["pl_pct"]:.2f}%)')
        order = api.submit_order(
            symbol=trade['symbol'],
            qty=trade['qty'],
            side='sell',
            type='market',
            time_in_force='day'
        )
        print(f'   Order submitted: {order.id}')
        trades_executed.append({
            'symbol': trade['symbol'],
            'action': 'SELL',
            'qty': trade['qty'],
            'reason': 'STOP-LOSS',
            'pl_pct': trade['pl_pct'],
            'order_id': order.id
        })
    except Exception as e:
        print(f'   ERROR: {e}')
        trades_executed.append({
            'symbol': trade['symbol'],
            'action': 'SELL',
            'qty': trade['qty'],
            'reason': 'STOP-LOSS',
            'pl_pct': trade['pl_pct'],
            'error': str(e)
        })

# Execute profit-taking trades
for trade in profit_target_triggered:
    try:
        print(f'\n🟢 PROFIT-TAKE: Selling {trade["qty"]} shares of {trade["symbol"]} @ ${trade["current_price"]:.2f} ({trade["pl_pct"]:.2f}%)')
        order = api.submit_order(
            symbol=trade['symbol'],
            qty=trade['qty'],
            side='sell',
            type='market',
            time_in_force='day'
        )
        print(f'   Order submitted: {order.id}')
        trades_executed.append({
            'symbol': trade['symbol'],
            'action': 'SELL',
            'qty': trade['qty'],
            'reason': 'PROFIT-TARGET',
            'pl_pct': trade['pl_pct'],
            'order_id': order.id
        })
    except Exception as e:
        print(f'   ERROR: {e}')
        trades_executed.append({
            'symbol': trade['symbol'],
            'action': 'SELL',
            'qty': trade['qty'],
            'reason': 'PROFIT-TARGET',
            'pl_pct': trade['pl_pct'],
            'error': str(e)
        })

if not trades_executed:
    print('\n✅ No trades required. All positions within acceptable parameters.')

print('\n' + '=' * 60)
print('Execution Summary:')
print(f'  Trades Executed: {len(trades_executed)}')
print(f'  Stop-Loss Triggers: {len(stop_loss_triggered)}')
print(f'  Profit Targets Hit: {len(profit_target_triggered)}')

# Prepare results for logging
results = {
    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'date': 'February 24, 2026',
    'account_value': portfolio_value,
    'cash': cash,
    'buying_power': buying_power,
    'positions_count': len(positions),
    'positions': positions_data,
    'trades_executed': trades_executed,
    'stop_loss_count': len(stop_loss_triggered),
    'profit_target_count': len(profit_target_triggered)
}

# Save results for trade_decisions.md
with open('/Users/mikeclawd/.openclaw/workspace/trade_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print('\nResults saved to trade_results.json')
