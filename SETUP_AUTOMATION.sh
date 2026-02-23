#!/bin/bash
# SETUP_AUTOMATION.sh - Set up cron jobs for trading system
# Created by OpenClaw + Claude Code collaboration

echo "🤖 Setting up Atlas Investments AI automation..."
echo ""

# Check if openclaw is available
if ! command -v openclaw &> /dev/null; then
    echo "⚠️  openclaw command not found. Please ensure OpenClaw is installed."
    exit 1
fi

echo "📅 Setting up cron jobs..."

# 6:35 AM PT - Morning scanner (M-F)
openclaw cron add --name "Morning Scanner" \
    --schedule "35 6 * * 1-5" \
    --command "cd ~/.openclaw/workspace && python3 diamond_scanner.py"

# 9:30 AM ET / 6:30 AM PT - Market Open check (M-F)  
openclaw cron add --name "Market Open Check" \
    --schedule "30 6 * * 1-5" \
    --command "cd ~/.openclaw/workspace && python3 market_open_check.py"

# 12:00 PM PT - Midday check (M-F)
openclaw cron add --name "Midday Check" \
    --schedule "0 12 * * 1-5" \
    --command "cd ~/.openclaw/workspace && python3 check_profit_targets.py"

# 2:00 PM PT - Power Hour check (M-F)
openclaw cron add --name "Power Hour Check" \
    --schedule "0 14 * * 1-5" \
    --command "cd ~/.openclaw/workspace && python3 check_profit_targets.py"

# Hourly stop-loss checks during market hours (9:30 AM - 4:00 PM ET / 6:30 AM - 1:00 PM PT)
openclaw cron add --name "Hourly Stop Check" \
    --schedule "30 6-13 * * 1-5" \
    --command "cd ~/.openclaw/workspace && python3 portfolio_stoploss_check.py"

echo ""
echo "✅ Automation setup complete!"
echo ""
echo "Schedule:"
echo "  6:30 AM PT - Market Open Check"
echo "  6:35 AM PT - Morning Scanner"
echo "  12:00 PM PT - Midday Check"
echo "  2:00 PM PT - Power Hour Check"
echo "  6:30 AM-1:00 PM PT - Hourly Stop-Loss Checks"
echo ""
echo "🎯 Ready for Monday trading!"
