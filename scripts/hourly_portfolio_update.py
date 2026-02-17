#!/usr/bin/env python3
"""
Hourly Portfolio Update - Sends Telegram alerts throughout trading day
"""

import json
import requests
from datetime import datetime

# Load credentials
with open('/Users/mikeclawd/.openclaw/secrets/alpaca.json', 'r') as f:
    creds = json.load(f)

base_url = creds['baseUrl'].rstrip('/v2').rstrip('/')
headers = {
    'APCA-API-KEY-ID': creds['apiKey'],
    'APCA-API-SECRET-KEY': creds['apiSecret']
}

# Get positions and account
positions = requests.get(f'{base_url}/v2/positions', headers=headers).json()
account = requests.get(f'{base_url}/v2/account', headers=headers).json()

portfolio_value = float(account['portfolio_value'])

# Find big movers
gainers = [p for p in positions if float(p['unrealized_plpc']) * 100 > 5]
losers = [p for p in positions if float(p['unrealized_plpc']) * 100 < -5]

# Build message
hour = datetime.now().hour
emoji = "📊"
if hour >= 14:
    emoji = "🌅"  # Afternoon
elif hour >= 11:
    emoji = "☀️"   # Midday
else:
    emoji = "🌄"   # Morning

message = f"""{emoji} PORTFOLIO UPDATE - {datetime.now().strftime('%I:%M %p PT')}

💰 Portfolio: ${portfolio_value:,.2f}
📈 Positions: {len(positions)}

"""

if gainers:
    message += "🔥 TOP MOVERS:\n"
    for p in sorted(gainers, key=lambda x: float(x['unrealized_plpc']), reverse=True)[:3]:
        pct = float(p['unrealized_plpc']) * 100
        message += f"  {p['symbol']}: {pct:+.1f}%\n"
    message += "\n"

if losers:
    message += "🔻 WATCH:\n"
    for p in sorted(losers, key=lambda x: float(x['unrealized_plpc']))[:3]:
        pct = float(p['unrealized_plpc']) * 100
        message += f"  {p['symbol']}: {pct:+.1f}%\n"

# Check for profit targets
profit_targets = [p for p in positions if float(p['unrealized_plpc']) * 100 > 30]
if profit_targets:
    message += "\n🎯 PROFIT TARGETS HIT:\n"
    for p in profit_targets:
        pct = float(p['unrealized_plpc']) * 100
        message += f"  {p['symbol']}: +{pct:.1f}% - Consider scaling out\n"

# Check for stop losses
stop_losses = [p for p in positions if float(p['unrealized_plpc']) * 100 < -14]
if stop_losses:
    message += "\n⚠️ STOP LOSS ALERT:\n"
    for p in stop_losses:
        pct = float(p['unrealized_plpc']) * 100
        message += f"  {p['symbol']}: {pct:.1f}% - Near -15% stop\n"

print(message)
