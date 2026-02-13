# PROCEDURES - Standard Operating Procedures

**Purpose:** Stop making stupid mistakes. Follow these procedures EVERY TIME.

---

## 🔴 CRITICAL RULES

1. **BEFORE placing ANY trade:** Check daily spend limit ($300/day max)
2. **ALWAYS send Telegram alerts** when completing tasks
3. **READ files before writing** - don't overwrite working code
4. **Test scripts before claiming they work**
5. **Document what actually works** - not what should work
6. **WHEN CRON TRIGGERS:** Actually RUN the command, don't just acknowledge it
   - If system message says "Run diamond_scanner.py" → RUN IT immediately
   - If it says "Send alert" → SEND THE ALERT
   - Cron messages are COMMANDS, not notifications

---

## 📊 SCANNER WORKFLOW

### Every Scan (6x daily)

**Step 1: Run Scanner**
```bash
cd /Users/mikeclawd/.openclaw/workspace
python3 diamond_scanner.py
```

**Step 2: Read Results**
```bash
cat data/diamonds.json
```

**Step 3: Send Telegram Alert**
- If high conviction (≥120 pts): Send alert with top 3
- If strong (90-119 pts): Send watch list
- If nothing good: Send "No setups found"

**Step 4: Update Memory**
- Log scan time and results to `memory/YYYY-MM-DD.md`

### DO NOT:
- ❌ Run scanner without sending alert
- ❌ Send alert without reading actual results
- ❌ Claim scanner works without testing

---

## 💰 TRADING WORKFLOW

### Placing Orders

**Pre-Flight Checklist:**
1. ✅ Check daily spend so far
2. ✅ Verify we have capital available
3. ✅ Confirm symbol is valid
4. ✅ Calculate shares before placing order

**Execution:**
```python
import json
import requests

# Load credentials
with open('/Users/mikeclawd/.openclaw/secrets/alpaca.json', 'r') as f:
    creds = json.load(f)

# FIX THE URL (critical - this is where I keep messing up)
base_url = creds['baseUrl'].rstrip('/v2').rstrip('/')

headers = {
    'APCA-API-KEY-ID': creds['apiKey'],
    'APCA-API-SECRET-KEY': creds['apiSecret']
}

# Place order
order_data = {
    'symbol': 'SYMBOL',
    'qty': QTY,
    'side': 'buy',  # or 'sell'
    'type': 'market',
    'time_in_force': 'day'
}

url = f"{base_url}/v2/orders"
r = requests.post(url, headers=headers, json=order_data)

if r.status_code in [200, 201]:
    order = r.json()
    print(f"✅ Order ID: {order['id']}")
else:
    print(f"❌ Failed: {r.text}")
```

**Post-Trade:**
1. ✅ Send Telegram confirmation
2. ✅ Log trade to daily memory file
3. ✅ Update portfolio tracking

### DO NOT:
- ❌ Place trades without checking daily limit
- ❌ Use wrong API URL format
- ❌ Forget to send confirmation message

---

## 📱 TELEGRAM MESSAGING

### When to Send Messages

**ALWAYS send for:**
- Scanner results (6x daily)
- Trade confirmations (every trade)
- Alerts (stops hit, big moves, etc.)
- Errors that need attention

**Template:**
```python
from message import send_message

# Use the message tool, not exec/curl
message(
    action='send',
    channel='telegram',
    message='Your message here'
)
```

### DO NOT:
- ❌ Complete tasks without sending confirmation
- ❌ Use exec or curl for messaging (use message tool)
- ❌ Send "I'll send you an alert" without actually sending it

---

## 🔍 PORTFOLIO REVIEW

### 6x Daily (with scans)

**Step 1: Get Positions**
```python
url = f"{base_url}/v2/positions"
r = requests.get(url, headers=headers)
positions = r.json()
```

**Step 2: Check for Alerts**
- Any stock down >10% from entry? → Alert
- Any stock up >30%? → Alert (take profits)
- Stop losses hit? → Alert immediately

**Step 3: Update Memory**
- Log current portfolio state
- Note any significant moves
- Update stop-loss triggers

---

## 📝 DAILY CHECKLIST

### Morning (6:00 AM - Premarket)
- [ ] Run scanner
- [ ] Send alert with results
- [ ] Check for overnight news on positions
- [ ] Review open orders

### Market Open (9:30 AM)
- [ ] Run scanner
- [ ] Send alert
- [ ] Check positions for stop triggers

### Midday (12:00 PM)
- [ ] Run scanner
- [ ] Send alert
- [ ] Review portfolio performance

### Power Hour (2:00 PM)
- [ ] Run scanner
- [ ] Send alert
- [ ] Look for late-day momentum

### Market Close (1:00 PM PT / 4:00 PM ET)
- [ ] Run scanner
- [ ] Send alert
- [ ] **Run daily_portfolio_review.py** (MANDATORY)
- [ ] **Send Telegram with daily P&L summary** (MANDATORY)
- [ ] Review top winners/losers
- [ ] Check scanner test positions (CFLT, KRE, etc.)
- [ ] Update data/portfolio_daily_log.csv
- [ ] Log day's learnings to memory/YYYY-MM-DD.md

### Evening (8:00 PM)
- [ ] Run scanner (after-hours)
- [ ] Send summary
- [ ] Update MEMORY.md with key learnings

---

## 🐛 DEBUGGING CHECKLIST

**When something breaks:**

1. **Don't guess** - actually test it
2. **Read the error message** - don't ignore it
3. **Check the last working version** - what changed?
4. **Test in isolation** - don't fix 3 things at once
5. **Document the fix** - so I don't break it again

**Common Mistakes I Make:**

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| API returns 404 | Wrong URL format | Strip `/v2` from base_url first |
| No Telegram alerts | Forgot to send | Add message call to every task |
| Scanner finds extended stocks | Bad scoring | Penalize >8% moves heavily |
| Claims "working" but isn't | Didn't test | Actually run it before claiming success |
| Overwrites working code | Didn't read file first | Always read before write |

---

## 📚 FILE STRUCTURE

**Always maintain:**

```
workspace/
├── diamond_scanner.py         # Main scanner (current working version)
├── data/
│   ├── diamonds.json          # Latest scan results
│   ├── scanner_test_trades.json  # Performance tracking
│   └── snapshot_cache.pkl     # Market data cache
├── memory/
│   └── YYYY-MM-DD.md         # Daily logs
├── MEMORY.md                  # Long-term memory (main session only)
├── PROCEDURES.md             # This file - READ IT
└── scripts/                   # Utility scripts

```

**Before modifying files:**
1. Read the current version
2. Make backup if critical
3. Test changes
4. Document what you changed

---

## ✅ SUCCESS CRITERIA

**I'm functioning correctly when:**

1. ✅ Scanner runs 6x daily automatically
2. ✅ Telegram alerts sent every scan
3. ✅ Trades execute without API errors
4. ✅ Daily spend limit never exceeded
5. ✅ No "I forgot to..." messages
6. ✅ Memory files updated daily
7. ✅ No repeated mistakes

**If I'm failing these, STOP and fix the procedures.**

---

## 🚨 EMERGENCY PROCEDURES

**If I'm completely confused:**
1. STOP working
2. Read PROCEDURES.md (this file)
3. Read MEMORY.md
4. Read today's memory/YYYY-MM-DD.md
5. Ask Mike what's most important
6. Focus on ONE thing at a time

**If something broke that was working:**
1. Find the last working version
2. Compare what changed
3. Revert the breaking change
4. Test before claiming it's fixed

---

_Last updated: 2026-02-03 12:24 PM PT_
_Read this file EVERY session until procedures are muscle memory._
