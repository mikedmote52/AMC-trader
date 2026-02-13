# OpenClaw Autonomous Operations Guide

## ✅ STATUS: FULLY AUTONOMOUS & RUNNING

OpenClaw is now configured to run automatically every day. You don't need to do anything - it will execute on schedule.

---

## 📅 Daily Schedule (Automatic)

All times Pacific Time (your local time). Runs Monday-Friday only.

| Time | Task | What It Does |
|------|------|--------------|
| **6:00 AM** | Morning Briefing | Portfolio status, positions at risk, profit opportunities, daily priorities |
| **6:30 AM** | Premarket Scanner | Scans 7,000+ stocks for setups before market opens |
| **6:31 AM** | Market Open Check | Monitors positions right as market opens (9:30 AM ET) |
| **9:00 AM** | Midday Check | Quick portfolio review at midday (12:00 PM ET) |
| **12:00 PM** | Power Hour Scanner | Scans for late-day momentum plays (3:00 PM ET) |
| **1:00 PM** | Market Close Review | Full daily review, P&L summary, position tracking (4:00 PM ET) |

---

## 🔍 How to Check If It's Running

### Quick Status Check:
```bash
launchctl list | grep openclaw
```

You should see 6 jobs listed like:
```
-	0	com.openclaw.morning_briefing
-	0	com.openclaw.premarket_scanner
-	0	com.openclaw.market_open
-	0	com.openclaw.midday_check
-	0	com.openclaw.power_hour
-	0	com.openclaw.market_close
```

If you see these, **OpenClaw is active and will run on schedule**.

---

## 📊 View Today's Activity

### Check Logs:
```bash
# Morning briefing
tail -20 ~/.openclaw/logs/morning_briefing.log

# Premarket scanner results
tail -20 ~/.openclaw/logs/premarket_scanner.log

# Market close review
tail -20 ~/.openclaw/logs/market_close.log

# View all logs
ls -lht ~/.openclaw/logs/
```

### View Scanner Results:
```bash
# Latest scan results (top stocks)
cat ~/.openclaw/workspace/data/diamonds.json | python3 -m json.tool | head -50
```

### View Portfolio Status:
```bash
cat ~/.openclaw/workspace/state/current.md
```

---

## 🔄 Manual Control (If Needed)

### Manually Run a Task Now:
```bash
# Run morning briefing now
launchctl start com.openclaw.morning_briefing

# Run scanner now
python3 ~/.openclaw/workspace/diamond_scanner.py
```

### Stop Automation:
```bash
# Stop all OpenClaw scheduled tasks
launchctl unload ~/Library/LaunchAgents/com.openclaw.*.plist
```

### Restart Automation:
```bash
# Restart all OpenClaw scheduled tasks
launchctl load ~/Library/LaunchAgents/com.openclaw.*.plist
```

---

## 📝 What's Automated vs Manual

### ✅ Fully Automatic (No Action Needed):
- Morning briefing at 6:00 AM
- Premarket & power hour scanners
- Position monitoring throughout the day
- Daily portfolio reviews
- Memory file updates
- Logging all activities

### ⚠️ Requires Your Approval:
- **Actual trade execution** - System will identify opportunities and alert you, but you must run:
  ```bash
  python3 ~/openclaw/workspace/scripts/execute_trade.py SYMBOL AMOUNT "thesis"
  ```
  This is intentional for safety - prevents the bot from burning through your account.

---

## 🚨 Troubleshooting

### Job Not Running?
1. Check if it's loaded:
   ```bash
   launchctl list | grep openclaw
   ```

2. Check error logs:
   ```bash
   cat ~/.openclaw/logs/morning_briefing_error.log
   ```

3. Reload the job:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.openclaw.morning_briefing.plist
   launchctl load ~/Library/LaunchAgents/com.openclaw.morning_briefing.plist
   ```

### No Output in Logs?
- Jobs only run at scheduled times or when manually started
- Check that you're looking at logs after the scheduled time has passed
- Manually trigger a job to test: `launchctl start com.openclaw.morning_briefing`

### Need to Change Schedule?
- Edit the plist files in `~/Library/LaunchAgents/com.openclaw.*.plist`
- Change the `<integer>` values under `StartCalendarInterval`
- Reload: `launchctl unload [file] && launchctl load [file]`

---

## 🎯 What Happens Automatically

### Every Morning (6:00 AM):
1. System wakes up
2. Checks your portfolio overnight status
3. Identifies positions near stop-loss
4. Flags profit-taking opportunities
5. Logs priorities for the day
6. Output saved to `~/.openclaw/logs/morning_briefing.log`

### Every Scanner Run (6:30 AM, 12:00 PM):
1. Scans 7,000+ stocks
2. Filters by volume, price action, catalysts
3. Scores 0-170 points
4. Saves top candidates to `data/diamonds.json`
5. Results ready for your review

### Every Close (1:00 PM PT):
1. Calculates daily P&L
2. Tracks all position changes
3. Updates portfolio log
4. Identifies actions needed tomorrow
5. Updates `state/current.md` with latest status

---

## 📈 Learning & Growth

The system learns from:
- **Every trade** - Logged with entry thesis to `data/portfolio_tracking.csv`
- **Scanner performance** - Tracks which scans predicted winners
- **Memory updates** - Daily logs in `memory/YYYY-MM-DD.md`
- **Strategy refinement** - Updates to `MEMORY.md` with lessons learned

Memory files automatically update with each run. The more it runs, the better it gets.

---

## ✅ Confirmation: You're All Set

**OpenClaw is now autonomous.** It will:
- Run 6 checkpoints daily automatically
- Monitor your portfolio continuously
- Alert you to opportunities
- Log all activities
- Learn from every trade

**You just need to:**
- Check the morning briefing (delivered automatically)
- Approve trades when opportunities arise
- Review end-of-day summary

**That's it. The bot is handling the rest.**

---

## 📞 Quick Reference Commands

```bash
# Status check
launchctl list | grep openclaw

# View today's activity
tail ~/.openclaw/logs/morning_briefing.log

# View latest scan results
cat ~/.openclaw/workspace/data/diamonds.json | python3 -m json.tool | head -30

# Manual scan now
python3 ~/.openclaw/workspace/diamond_scanner.py

# Execute a trade (requires your approval)
python3 ~/.openclaw/workspace/scripts/execute_trade.py SYMBOL AMOUNT "your thesis"

# View portfolio status
cat ~/.openclaw/workspace/state/current.md
```

---

**Last Updated:** February 7, 2026
**Status:** Active & Running Autonomously
