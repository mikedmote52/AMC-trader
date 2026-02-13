#!/usr/bin/env python3
"""
Send Telegram alert with scan results
Called by cron jobs after scanner runs
"""

import json
import subprocess
import os

def send_alert():
    # Read diamond scanner results
    diamonds_file = '/Users/mikeclawd/.openclaw/workspace/data/diamonds.json'
    
    if not os.path.exists(diamonds_file):
        return "No scan results found"
    
    with open(diamonds_file, 'r') as f:
        diamonds = json.load(f)
    
    # Filter for early-stage only (not extended)
    early_stage = [d for d in diamonds if d['momentum_score'] >= 12]  # Early or starting
    
    if not early_stage:
        msg = "📊 Scan complete - No early-stage setups found\n\nMarket conditions may not be ideal for new entries right now."
    else:
        msg = f"🔬 SCANNER ALERT\n\n"
        msg += f"Found {len(early_stage)} early-stage candidates:\n\n"
        
        for d in early_stage[:5]:  # Top 5
            msg += f"*{d['symbol']}* - ${d['price']:.2f}\n"
            msg += f"Score: {d['score']}/200\n"
            msg += f"• {d['squeeze_info']}\n"
            msg += f"• {d['momentum']}\n"
            
            if d['catalyst_score'] > 0:
                msg += f"• {d['catalyst']}\n"
            
            msg += "\n"
    
    # Send via OpenClaw message tool (this script will be called from main session)
    print(msg)
    
    # Return message for cron to send
    return msg

if __name__ == '__main__':
    send_alert()
