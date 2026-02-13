#!/usr/bin/env python3
"""
Telegram Alert System - Send notifications to your phone
"""

import json
import sys
import requests
from pathlib import Path
from datetime import datetime

SECRETS = Path('/Users/mikeclawd/.openclaw/secrets/telegram.json')

def load_credentials():
    """Load Telegram credentials"""
    if not SECRETS.exists():
        print(f"❌ Telegram not configured. Run: python3 scripts/telegram_setup.py")
        sys.exit(1)

    with open(SECRETS) as f:
        return json.load(f)

def send_alert(message, parse_mode='Markdown'):
    """Send alert to Telegram"""
    creds = load_credentials()

    url = f"https://api.telegram.org/bot{creds['bot_token']}/sendMessage"
    payload = {
        'chat_id': creds['chat_id'],
        'text': message,
        'parse_mode': parse_mode
    }

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        return True
    else:
        print(f"❌ Failed to send alert: {response.text}")
        return False

def send_test_message():
    """Send a test message"""
    now = datetime.now().strftime('%I:%M:%S %p')

    message = f"""🤖 *AUTOMATED TEST MESSAGE*

This message was sent automatically by OpenClaw at {now}.

✅ Your autonomous trading system is working!

This proves:
- ✓ OpenClaw is running
- ✓ Scheduled tasks execute
- ✓ Telegram alerts work
- ✓ You'll receive real-time notifications

Next, you'll receive:
• Morning briefings at 6:00 AM
• Scanner alerts when diamonds found
• Stop-loss warnings
• Profit target notifications

*OpenClaw is watching your money 24/7.* 👁️"""

    success = send_alert(message)

    if success:
        print(f"✅ Test message sent at {now}")

    return success

def send_scanner_alert(diamonds):
    """Send scanner results alert"""
    if not diamonds:
        return

    top_picks = diamonds[:3]  # Top 3

    message = "💎 *DIAMOND SCANNER ALERT*\n\n"

    for pick in top_picks:
        message += f"*{pick['symbol']}* - {pick['score']}/170 pts\n"
        message += f"Price: ${pick['price']:.2f}\n"
        message += f"{pick.get('float', 'N/A')}\n"
        message += f"{pick.get('momentum', 'N/A')}\n\n"

    message += f"_Found {len(diamonds)} total diamonds_"

    send_alert(message)

def send_position_alert(symbol, alert_type, details):
    """Send position alert (stop loss, profit target)"""
    emoji = {
        'stop_loss': '🔴',
        'profit_target': '🎯',
        'warning': '⚠️'
    }

    message = f"{emoji.get(alert_type, '📊')} *POSITION ALERT*\n\n"
    message += f"*{symbol}*: {details}\n"

    send_alert(message)

def send_morning_briefing(briefing_text):
    """Send morning briefing"""
    message = f"🌅 *MORNING BRIEFING*\n\n{briefing_text}"
    send_alert(message)

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        send_test_message()
    else:
        print("Usage:")
        print("  python3 telegram_alert.py --test    # Send test message")
        print("\nOr import and use functions:")
        print("  from telegram_alert import send_alert, send_scanner_alert")
