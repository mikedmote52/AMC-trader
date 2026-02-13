# Google Sheets Integration - Setup Guide

## Quick Setup (5 minutes)

### Step 1: Install Required Libraries
```bash
pip3 install gspread oauth2client
```

### Step 2: Create Google Cloud Project
1. Go to https://console.cloud.google.com
2. Click "Select a project" → "New Project"
3. Name it "OpenClaw" → Create

### Step 3: Enable Google Sheets API
1. In your project, go to "APIs & Services" → "Library"
2. Search for "Google Sheets API"
3. Click "Enable"

### Step 4: Create Service Account
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "Service Account"
3. Name: `openclaw-bot`
4. Click "Create and Continue"
5. Skip optional steps → Done

### Step 5: Generate JSON Key
1. Click on the service account you just created
2. Go to "Keys" tab
3. "Add Key" → "Create New Key"
4. Choose "JSON"
5. Download the file

### Step 6: Save Credentials
```bash
mv ~/Downloads/your-project-*.json ~/.openclaw/secrets/google_sheets.json
```

### Step 7: Create Your Spreadsheet
```bash
python3 ~/.openclaw/workspace/scripts/google_sheets_sync.py --create
```

This will:
- Create a new Google Sheet named "OpenClaw Portfolio"
- Give you the Sheet ID
- Print the sheet URL

### Step 8: Share the Sheet
1. Open the sheet URL from step 7
2. Click "Share"
3. Add the service account email (found in the JSON file: `client_email`)
4. Give it "Editor" permissions

### Step 9: Test the Sync
```bash
python3 ~/.openclaw/workspace/scripts/google_sheets_sync.py
```

You should see your portfolio data synced to Google Sheets!

---

## Automated Syncing

To sync automatically every hour during market hours, add to your crontab:

```bash
# Sync to Google Sheets every hour 6 AM - 2 PM PT (market hours)
0 6-14 * * 1-5 /usr/bin/python3 ~/.openclaw/workspace/scripts/google_sheets_sync.py >> ~/.openclaw/logs/google_sheets_sync.log 2>&1
```

Or use launchd (macOS):

Create `/Users/mikeclawd/Library/LaunchAgents/com.openclaw.sheets_sync.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.openclaw.sheets_sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/mikeclawd/.openclaw/workspace/scripts/google_sheets_sync.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>
        <dict>
            <key>Hour</key>
            <integer>6</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
        <dict>
            <key>Hour</key>
            <integer>13</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
    </array>
    <key>StandardOutPath</key>
    <string>/Users/mikeclawd/.openclaw/logs/sheets_sync.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/mikeclawd/.openclaw/logs/sheets_sync_error.log</string>
</dict>
</plist>
```

Then load it:
```bash
launchctl load ~/Library/LaunchAgents/com.openclaw.sheets_sync.plist
```

---

## What Gets Synced

The Google Sheet will show:
- **Account Summary**
  - Total portfolio value
  - Cash available
  - Number of positions

- **Positions Table**
  - Symbol
  - Quantity, Entry Price, Current Price
  - Cost Basis, Market Value
  - P&L in $ and %
  - Stop Loss and Target prices

Updates automatically every sync (hourly during market hours if automated).

---

## Troubleshooting

### "gspread not installed"
```bash
pip3 install gspread oauth2client
```

### "google_sheets.json not found"
- Make sure you downloaded the JSON key from Google Cloud
- Save it to `~/.openclaw/secrets/google_sheets.json`

### "Permission denied"
- Make sure you shared the Google Sheet with the service account email
- The email is in the JSON file under `client_email`

### "Spreadsheet not found"
- Run with `--create` to create a new sheet
- Or specify an existing sheet with `--sheet-id YOUR_SHEET_ID`

---

## Mobile Access

Once synced to Google Sheets:
1. Open Google Sheets app on your phone
2. Find "OpenClaw Portfolio"
3. Bookmark it for quick access

Now you can monitor your portfolio from anywhere!
