#!/bin/bash
# Prove OpenClaw is working - Send test message in 3 minutes

echo "=========================================="
echo "OPENCLAW PROOF-OF-WORK TEST"
echo "=========================================="
echo ""
echo "This will:"
echo "1. Configure Telegram (2 minutes)"
echo "2. Send immediate test message"
echo "3. Schedule another in 3 minutes (proves automation)"
echo ""

# Step 1: Run Telegram setup
echo "🔧 Step 1: Setting up Telegram..."
python3 /Users/mikeclawd/.openclaw/workspace/scripts/telegram_setup.py

# Check if setup succeeded
if [ ! -f ~/.openclaw/secrets/telegram.json ]; then
    echo "❌ Telegram setup failed"
    exit 1
fi

echo ""
echo "✅ Telegram configured!"
echo ""

# Step 2: Schedule test message in 3 minutes
echo "⏰ Scheduling test message in 3 minutes..."

# Calculate time for 3 minutes from now
FUTURE_TIME=$(date -v+3M "+%H:%M")

# Create temporary launchd plist
cat > /tmp/openclaw_test.plist <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.openclaw.test_message</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/mikeclawd/.openclaw/workspace/scripts/telegram_alert.py</string>
        <string>--test</string>
    </array>
    <key>RunAtLoad</key>
    <false/>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>$(date -v+3M "+%H")</integer>
        <key>Minute</key>
        <integer>$(date -v+3M "+%M")</integer>
    </dict>
</dict>
</plist>
EOF

# Load the job
launchctl unload /tmp/openclaw_test.plist 2>/dev/null
launchctl load /tmp/openclaw_test.plist

echo "✅ Test message scheduled for $FUTURE_TIME"
echo ""
echo "=========================================="
echo "READY!"
echo "=========================================="
echo ""
echo "Check your Telegram now for the first message."
echo "In 3 minutes (at $FUTURE_TIME), you'll get another"
echo "automated message proving the system works."
echo ""
echo "If you see both messages, OpenClaw is 100% operational!"
echo ""
