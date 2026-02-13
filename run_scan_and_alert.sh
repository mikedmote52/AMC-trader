#!/bin/bash
# Run diamond scanner and send Telegram alert
# Called by cron jobs

cd /Users/mikeclawd/.openclaw/workspace

# Run scanner
echo "Running diamond scanner..."
python3 diamond_scanner.py > /tmp/scan_output.log 2>&1

# Check if it succeeded
if [ $? -eq 0 ]; then
    echo "Scanner completed successfully"
    
    # Read results and send alert via OpenClaw
    python3 << 'PYTHON_EOF'
import json
import sys
import os

# Add OpenClaw workspace to path for message sending
sys.path.insert(0, '/Users/mikeclawd/.openclaw/workspace')

diamonds_file = 'data/diamonds.json'

if not os.path.exists(diamonds_file):
    print("SCAN_ALERT:📊 Scan complete - No results file generated")
    sys.exit(0)

with open(diamonds_file, 'r') as f:
    diamonds = json.load(f)

# Filter for trade-worthy stocks
high_conviction = [d for d in diamonds if d['score'] >= 120]
early_stage = [d for d in diamonds if d['momentum_score'] >= 12 and d['score'] >= 70]

if high_conviction:
    msg = f"🚨 HIGH CONVICTION ALERT\n\n"
    msg += f"Found {len(high_conviction)} trade-ready stocks:\n\n"
    
    for d in high_conviction[:3]:
        msg += f"*{d['symbol']}* - ${d['price']:.2f} ({d['score']}/200)\n"
        msg += f"• {d['squeeze_info']}\n"
        msg += f"• {d['momentum']}\n"
        if d['catalyst_score'] > 0:
            msg += f"• {d['catalyst']}\n"
        msg += "\n"
        
elif early_stage:
    msg = f"👀 WATCH LIST\n\n"
    msg += f"Found {len(early_stage)} early-stage candidates:\n\n"
    
    for d in early_stage[:5]:
        msg += f"*{d['symbol']}* - ${d['price']:.2f} ({d['score']}/200)\n"
        msg += f"• {d['squeeze_info']}\n"
        msg += f"• {d['momentum']}\n"
        msg += "\n"
else:
    msg = "📊 Scan complete - No strong setups found right now"

print(f"SCAN_ALERT:{msg}")
PYTHON_EOF

else
    echo "SCAN_ALERT:❌ Scanner failed - check logs"
fi
