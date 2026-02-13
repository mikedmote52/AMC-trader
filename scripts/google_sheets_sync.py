#!/usr/bin/env python3
"""
Google Sheets Sync - Real-time portfolio tracking

Syncs portfolio data to Google Sheets for:
- Visual dashboard
- Collaborative tracking
- Historical performance charts
- Easy mobile access

Setup Required:
1. Install gspread: pip3 install gspread oauth2client
2. Create Google Cloud project: https://console.cloud.google.com
3. Enable Google Sheets API
4. Create service account and download JSON credentials
5. Save credentials to ~/.openclaw/secrets/google_sheets.json
6. Share your Google Sheet with service account email

Usage:
    python3 google_sheets_sync.py                    # Sync now
    python3 google_sheets_sync.py --create           # Create new sheet
    python3 google_sheets_sync.py --sheet-id abc123  # Sync to specific sheet
"""

import json
import sys
from datetime import datetime
from pathlib import Path
import requests

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

WORKSPACE = Path('/Users/mikeclawd/.openclaw/workspace')
SECRETS = Path('/Users/mikeclawd/.openclaw/secrets')
ALPACA_CREDS = SECRETS / 'alpaca.json'
GOOGLE_CREDS = SECRETS / 'google_sheets.json'

# Load Alpaca credentials
with open(ALPACA_CREDS) as f:
    alpaca_creds = json.load(f)

ALPACA_HEADERS = {
    'APCA-API-KEY-ID': alpaca_creds['apiKey'],
    'APCA-API-SECRET-KEY': alpaca_creds['apiSecret']
}
BASE_URL = 'https://paper-api.alpaca.markets/v2'


def check_setup():
    """Check if Google Sheets integration is set up"""
    if not GSPREAD_AVAILABLE:
        print("❌ gspread library not installed")
        print("\nTo install:")
        print("   pip3 install gspread oauth2client")
        return False

    if not GOOGLE_CREDS.exists():
        print("❌ Google Sheets credentials not found")
        print(f"\nExpected location: {GOOGLE_CREDS}")
        print("\nSetup instructions:")
        print("1. Go to https://console.cloud.google.com")
        print("2. Create a project and enable Google Sheets API")
        print("3. Create a service account")
        print("4. Download JSON credentials")
        print(f"5. Save to {GOOGLE_CREDS}")
        print("\nSee full guide: https://docs.gspread.org/en/latest/oauth2.html")
        return False

    return True


def get_google_client():
    """Authenticate and return Google Sheets client"""
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS, scope)
    client = gspread.authorize(creds)

    return client


def get_portfolio_data():
    """Get current portfolio data from Alpaca"""
    # Get positions
    positions_resp = requests.get(f'{BASE_URL}/positions', headers=ALPACA_HEADERS)
    positions = positions_resp.json()

    # Get account
    account_resp = requests.get(f'{BASE_URL}/account', headers=ALPACA_HEADERS)
    account = account_resp.json()

    return positions, account


def format_portfolio_for_sheets(positions, account):
    """Format portfolio data for Google Sheets"""
    today = datetime.now().strftime('%Y-%m-%d %I:%M %p')

    # Account summary
    summary = [
        ['OpenClaw Portfolio Dashboard', ''],
        ['Last Updated:', today],
        ['', ''],
        ['Account Value:', f"${float(account['portfolio_value']):,.2f}"],
        ['Cash:', f"${float(account['cash']):,.2f}"],
        ['Positions Value:', f"${float(account['portfolio_value']) - float(account['cash']):,.2f}"],
        ['Number of Positions:', str(len(positions))],
        ['', ''],
    ]

    # Positions table header
    header = [
        'Symbol', 'Quantity', 'Entry Price', 'Current Price',
        'Cost Basis', 'Market Value', 'P&L $', 'P&L %',
        'Days Held', 'Stop Loss', 'Target'
    ]

    # Positions data
    rows = [header]

    for pos in sorted(positions, key=lambda p: float(p['unrealized_pl']), reverse=True):
        qty = float(pos['qty'])
        entry = float(pos['avg_entry_price'])
        current = float(pos['current_price'])
        cost = qty * entry
        value = qty * current
        pnl = float(pos['unrealized_pl'])
        pnl_pct = float(pos['unrealized_plpc']) * 100

        # Calculate stop loss and targets
        stop_loss = entry * 0.85  # -15%
        target_1 = entry * 1.30   # +30%

        row = [
            pos['symbol'],
            qty,
            f"${entry:.2f}",
            f"${current:.2f}",
            f"${cost:.2f}",
            f"${value:.2f}",
            f"${pnl:+.2f}",
            f"{pnl_pct:+.1f}%",
            '',  # Days held - would need entry date
            f"${stop_loss:.2f}",
            f"${target_1:.2f}"
        ]
        rows.append(row)

    return summary, rows


def create_new_sheet(client, sheet_name="OpenClaw Portfolio"):
    """Create a new Google Sheet"""
    print(f"Creating new sheet: {sheet_name}...")

    sheet = client.create(sheet_name)

    # Share with your email (optional)
    # sheet.share('your-email@gmail.com', perm_type='user', role='writer')

    print(f"✅ Created: {sheet.url}")
    print(f"   Sheet ID: {sheet.id}")
    print(f"\n💡 Save this Sheet ID to ~/.openclaw/secrets/google_sheets_id.txt for future syncs")

    return sheet


def sync_to_sheet(client, sheet_id=None):
    """Sync portfolio data to Google Sheets"""
    # Get or open sheet
    if sheet_id:
        sheet = client.open_by_key(sheet_id)
    else:
        # Try to open default sheet
        try:
            sheet = client.open("OpenClaw Portfolio")
        except gspread.exceptions.SpreadsheetNotFound:
            print("❌ Sheet 'OpenClaw Portfolio' not found")
            print("   Run with --create to create a new sheet")
            print("   Or specify sheet ID with --sheet-id")
            return

    # Get portfolio data
    print("📊 Fetching portfolio data...")
    positions, account = get_portfolio_data()

    summary, rows = format_portfolio_for_sheets(positions, account)

    # Update sheet
    print(f"📤 Syncing to Google Sheets...")

    worksheet = sheet.get_worksheet(0)  # First worksheet

    # Clear existing data
    worksheet.clear()

    # Write summary
    for i, row in enumerate(summary, 1):
        worksheet.update(f'A{i}:B{i}', [row])

    # Write positions table (starting after summary)
    start_row = len(summary) + 2
    end_row = start_row + len(rows) - 1

    worksheet.update(f'A{start_row}:K{end_row}', rows)

    # Format header row
    header_row = start_row
    worksheet.format(f'A{header_row}:K{header_row}', {
        'textFormat': {'bold': True},
        'backgroundColor': {'red': 0.2, 'green': 0.2, 'blue': 0.2},
        'horizontalAlignment': 'CENTER'
    })

    print(f"✅ Synced {len(positions)} positions to Google Sheets")
    print(f"   View at: {sheet.url}")


def main():
    if not check_setup():
        sys.exit(1)

    # Parse arguments
    create = '--create' in sys.argv
    sheet_id = None

    if '--sheet-id' in sys.argv:
        idx = sys.argv.index('--sheet-id')
        if idx + 1 < len(sys.argv):
            sheet_id = sys.argv[idx + 1]

    # Authenticate
    print("🔐 Authenticating with Google Sheets...")
    client = get_google_client()
    print("✅ Authenticated")

    if create:
        create_new_sheet(client)
    else:
        sync_to_sheet(client, sheet_id)


if __name__ == '__main__':
    main()
