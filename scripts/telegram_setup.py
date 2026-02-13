#!/usr/bin/env python3
"""
Telegram Setup Helper - Get your bot configured in 2 minutes
"""

import requests
import json
from pathlib import Path

SECRETS = Path('/Users/mikeclawd/.openclaw/secrets')

def get_bot_info(token):
    """Test bot token and get bot info"""
    response = requests.get(f'https://api.telegram.org/bot{token}/getMe')
    if response.status_code == 200:
        return response.json()
    else:
        return None

def get_chat_id(token):
    """Get your chat ID by checking recent messages"""
    response = requests.get(f'https://api.telegram.org/bot{token}/getUpdates')
    if response.status_code == 200:
        data = response.json()
        if data['result']:
            # Get most recent chat
            chat_id = data['result'][-1]['message']['chat']['id']
            return chat_id
    return None

def save_credentials(token, chat_id):
    """Save Telegram credentials"""
    SECRETS.mkdir(exist_ok=True)
    creds = {
        'bot_token': token,
        'chat_id': chat_id
    }

    with open(SECRETS / 'telegram.json', 'w') as f:
        json.dump(creds, f, indent=2)

    print(f"✅ Saved credentials to {SECRETS / 'telegram.json'}")

def send_test_message(token, chat_id):
    """Send a test message"""
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': '✅ *OpenClaw Connected!*\n\nYour trading bot is now live and will send you:\n- Scanner alerts\n- Morning briefings\n- Stop/target notifications\n\nYou will get another test message in 3 minutes to prove automation works.',
        'parse_mode': 'Markdown'
    }

    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("✅ Test message sent to Telegram!")
        return True
    else:
        print(f"❌ Failed to send message: {response.text}")
        return False

def main():
    print("=" * 60)
    print("TELEGRAM BOT SETUP")
    print("=" * 60)
    print()

    print("Step 1: Create a Telegram bot")
    print("  1. Open Telegram and search for @BotFather")
    print("  2. Send: /newbot")
    print("  3. Choose a name (e.g., 'OpenClaw Trading Bot')")
    print("  4. Choose a username (e.g., 'mikeclawd_trading_bot')")
    print("  5. Copy the bot token (looks like: 123456:ABC-DEF1234...)")
    print()

    token = input("Enter your bot token: ").strip()

    if not token:
        print("❌ No token provided")
        return

    # Test token
    print("\n🔍 Testing bot token...")
    bot_info = get_bot_info(token)

    if not bot_info:
        print("❌ Invalid token")
        return

    print(f"✅ Bot connected: @{bot_info['result']['username']}")
    print()

    print("Step 2: Get your chat ID")
    print(f"  1. Open Telegram and search for @{bot_info['result']['username']}")
    print("  2. Click 'START' or send any message to the bot")
    print("  3. Press Enter when done")
    input()

    print("\n🔍 Fetching your chat ID...")
    chat_id = get_chat_id(token)

    if not chat_id:
        print("❌ No messages found. Make sure you sent a message to the bot.")
        return

    print(f"✅ Found chat ID: {chat_id}")
    print()

    # Save credentials
    save_credentials(token, chat_id)

    # Send test message
    print("📤 Sending test message...")
    send_test_message(token, chat_id)

    print()
    print("=" * 60)
    print("SETUP COMPLETE!")
    print("=" * 60)
    print()
    print("Your bot is configured and ready.")
    print("Check your Telegram app for the test message!")
    print()
    print("A second test message will arrive in 3 minutes to prove")
    print("the automated system is working.")
    print()

if __name__ == '__main__':
    main()
