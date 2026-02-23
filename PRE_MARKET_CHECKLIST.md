# PRE-MARKET CHECKLIST
**Daily Trading System Checklist**
**Market Hours:** 6:30 AM - 1:00 PM PT (Mon-Fri)

---

## ⏰ TIMING GUIDE

| Time | Activity | Duration | Priority |
|------|----------|----------|----------|
| 6:00 AM | Morning Briefing | 5 min | 🔴 Critical |
| 6:05 AM | Portfolio Review | 10 min | 🔴 Critical |
| 6:15 AM | Risk Assessment | 5 min | 🔴 Critical |
| 6:20 AM | Market Context | 5 min | 🟡 Important |
| 6:25 AM | Trade Planning | 5 min | 🟡 Important |
| 6:30 AM | Market Open | 15 min | 🔴 Critical |
| 6:45 AM | Scanner Run | 10 min | 🟢 Optional |

**Total Prep Time:** 30 minutes minimum (40 min recommended)

---

## 🌅 PHASE 1: SYSTEM HEALTH (6:00 AM - 5 min)

### Quick System Checks
```bash
# Test API connections
cd /Users/mikeclawd/.openclaw/workspace

# 1. Test Alpaca API
python3 -c "import json, requests; creds = json.load(open('/Users/mikeclawd/.openclaw/secrets/alpaca.json')); r = requests.get(creds['baseUrl'] + '/v2/account', headers={'APCA-API-KEY-ID': creds['apiKey'], 'APCA-API-SECRET-KEY': creds['apiSecret']}); print('✅ Alpaca API: OK' if r.status_code == 200 else '❌ Alpaca API: FAILED')"

# 2. Test Polygon API
python3 -c "from polygon import RESTClient; import json; creds = json.load(open('/Users/mikeclawd/.openclaw/secrets/polygon.json')); client = RESTClient(api_key=creds['apiKey']); print('✅ Polygon API: OK')"

# 3. Check cache freshness
ls -lh data/market_cap_cache.json data/snapshot_cache.pkl
```

**Checklist:**
- [ ] Alpaca API responds
- [ ] Polygon API responds
- [ ] market_cap_cache.json exists (<24h old)
- [ ] No Python import errors

**If API fails:** Check credentials in `~/.openclaw/secrets/`

---

## 📊 PHASE 2: MORNING BRIEFING (6:05 AM - 5 min)

```bash
cd /Users/mikeclawd/.openclaw/workspace
python3 morning_briefing.py
```

**Review Output:**
- [ ] Portfolio value current
- [ ] Cash available noted
- [ ] Overnight fills (if any)
- [ ] Position P&L summary
- [ ] Alerts identified

**Key Questions:**
- What's my total portfolio value?
- How much buying power do I have?
- Any overnight gaps in my positions?
- Any positions near stops (-12% to -15%)?
- Any positions near targets (+25% to +30%)?

**Save output to:** `data/morning_briefing_$(date +%Y-%m-%d).txt`

---

## 💼 PHASE 3: PORTFOLIO REVIEW (6:10 AM - 10 min)

### A. Review Current Positions
```bash
# Check all positions
python3 check_positions.py

# OR manually review
cat data/portfolio_tracking.csv
```

**For Each Position, Note:**
- [ ] Current P&L %
- [ ] Distance to stop (-15%)
- [ ] Distance to target (+30%)
- [ ] Days held
- [ ] Original thesis still valid?

### B. Check Yesterday's State
```bash
# Review yesterday's end state
cat state/current.md | head -50
```

**Verify:**
- [ ] Yesterday's closing prices match today's opens
- [ ] No missing positions
- [ ] No unexpected fills overnight

### C. Ghost Portfolio Check
```bash
python3 ghost_portfolio_tracker.py
```

**Review:**
- [ ] What gains did we miss by selling?
- [ ] Should we adjust profit targets?
- [ ] Any patterns in missed gains?

---

## 🛡️ PHASE 4: RISK ASSESSMENT (6:20 AM - 5 min)

### A. Stop-Loss Analysis
```bash
python3 portfolio_stoploss_check.py
```

**Critical Checks:**
- [ ] Any positions below -15%? (IMMEDIATE SELL)
- [ ] Any positions -12% to -15%? (WATCH CLOSELY)
- [ ] Which position is closest to stop?
- [ ] Total capital at risk?

**Action Items:**
| P&L Range | Action |
|-----------|--------|
| Below -15% | 🔴 SELL IMMEDIATELY |
| -12% to -15% | 🟡 Monitor every 15 min |
| -8% to -12% | 🟢 Watch hourly |

### B. Profit Target Analysis
```bash
python3 check_profit_targets.py
```

**Target Checks:**
- [ ] Any positions above +30%? (SCALE OUT 50%)
- [ ] Any positions +25% to +30%? (PREPARE TO SCALE)
- [ ] Which positions are runners?
- [ ] Total unrealized gains?

**Action Items:**
| P&L Range | Action |
|-----------|--------|
| Above +30% | 🎯 SELL 50% at open |
| +25% to +30% | ⚠️ Prepare scale-out order |
| +20% to +25% | 📈 Monitor for continuation |

### C. Portfolio Exposure
**Calculate:**
- [ ] Total portfolio value: $________
- [ ] Cash available: $________
- [ ] Largest position size: $________ (_____%)
- [ ] Total positions: ___
- [ ] Buying power: $________
- [ ] Daily budget available: $300

**Risk Limits:**
- ✅ No position >20% of portfolio
- ✅ No more than 20 positions
- ✅ Keep 50%+ in cash
- ✅ Max $300/day new entries

---

## 📰 PHASE 5: MARKET CONTEXT (6:25 AM - 5 min)

### A. Market Direction
**Check Pre-Market:**
- [ ] SPY pre-market: $_____  (____%)
- [ ] QQQ pre-market: $_____  (____%)
- [ ] IWM pre-market: $_____  (____%)
- [ ] VIX level: $_____

**Market Mood:**
- 🟢 SPY/QQQ green = Risk-on day
- 🔴 SPY/QQQ red = Risk-off day
- ⚠️ VIX >20 = High volatility

### B. Sector Rotation
```bash
python3 -c "import sys; sys.path.insert(0, '/Users/mikeclawd/.openclaw/workspace'); from sector_tracker import get_sector_performance; print(get_sector_performance())"
```

**Hot Sectors Today:**
1. ________________
2. ________________
3. ________________

**Cold Sectors Today:**
1. ________________
2. ________________

### C. Major Catalysts
**Check News:**
- [ ] Any Fed announcements?
- [ ] Any major earnings today?
- [ ] Any geopolitical events?
- [ ] Any sector-specific news?

**Earnings Today:** _________________

---

## 🎯 PHASE 6: TRADE PLANNING (6:30 AM - 5 min)

### A. Exit Planning
**Profit-Taking Plan:**
```
Position    Current P&L    Action at Open
________    __________    _________________
________    __________    _________________
________    __________    _________________
```

**Stop-Loss Plan:**
```
Position    Current P&L    Stop Price    Action
________    __________    $_______    ____________
________    __________    $_______    ____________
```

### B. Entry Planning
**Scanner Watchlist (run at 6:45 AM):**
```bash
cd /Users/mikeclawd/.openclaw/workspace
python3 diamond_scanner.py
```

**Top 3 Entry Candidates:**
1. **Symbol:** _____ | **Price:** $_____ | **Score:** ____/305
   - Entry: $_____ | Stop: $_____ | Target: $_____
   - Shares: ___ ($300 budget)
   - Thesis: _______________________________

2. **Symbol:** _____ | **Price:** $_____ | **Score:** ____/305
   - Entry: $_____ | Stop: $_____ | Target: $_____
   - Shares: ___ ($300 budget)
   - Thesis: _______________________________

3. **Symbol:** _____ | **Price:** $_____ | **Score:** ____/305
   - Entry: $_____ | Stop: $_____ | Target: $_____
   - Shares: ___ ($300 budget)
   - Thesis: _______________________________

### C. Position Sizing
**For Each Entry:**
```
Budget: $300
Price: $____
Max Shares: ____ ($300 / price)
Stop-Loss: -15%
Target: +30%
Risk: $____ (15% of position)
```

---

## 🔔 MARKET OPEN (6:30 AM - 15 min)

### First 2 Minutes (6:30-6:32 AM)
```bash
# Run market open check
python3 market_open_check.py
```

**Immediate Actions:**
- [ ] Check for gap ups/downs in positions
- [ ] Execute planned profit-taking orders
- [ ] Place stop-loss orders if not automated
- [ ] Monitor SPY/QQQ direction

**Order Execution:**
```
SELL Orders (Profit Taking):
[ ] ____ shares of _____ @ market (reason: +___% target hit)
[ ] ____ shares of _____ @ market (reason: +___% target hit)

SELL Orders (Stop Loss):
[ ] ____ shares of _____ @ market (reason: -15% stop hit)

BUY Orders (New Entries):
[ ] ____ shares of _____ @ $_____ (reason: scanner pick)
```

### First 15 Minutes (6:30-6:45 AM)
**High Volatility Period - WATCH CLOSELY**

**Monitor:**
- [ ] Market direction confirmed (up/down/sideways)?
- [ ] Any positions gapping against us?
- [ ] Any stop-losses triggered?
- [ ] Any profit targets hit?
- [ ] Volume spike on any positions?

**Pattern Recognition:**
- 🟢 Strong gap up + volume = Likely continuation
- 🔴 Gap up fading = Take profits
- 🟡 Choppy = Wait for clarity

### Scanner Run (6:45 AM)
```bash
python3 diamond_scanner.py
```

**Look For:**
- [ ] Explosive volume (5x, 10x, 50x+)
- [ ] Gap-ups >10%
- [ ] Low float (<5M shares)
- [ ] Squeeze plays (high short interest)
- [ ] Score >200/305

**Best Setup Today:**
- Symbol: _____
- Score: ____/305
- Price: $_____
- Thesis: _______________________________

---

## 📈 INTRADAY MONITORING

### Hourly Checks (10:00, 11:00, 12:00, 1:00)

**Stop-Loss Check:**
```bash
python3 portfolio_stoploss_check.py
```
- [ ] Any new positions near stop?
- [ ] Any positions recovering from near-stop?

**Profit Target Check:**
```bash
python3 check_profit_targets.py
```
- [ ] Any new profit targets hit?
- [ ] Any positions approaching target?

**State Update:**
```bash
# Update current state
# (Will automate this later)
echo "Updated: $(date)" >> state/current.md
```

### Power Hour (2:00-4:00 PM)
**Increased volatility - potential for big moves**

- [ ] Run profit target check (14:00)
- [ ] Run stop-loss check (14:30)
- [ ] Prepare for EOD decisions
- [ ] Update position notes

---

## 🌙 END OF DAY (4:00 PM)

### Market Close Review
```bash
# Final portfolio check
python3 check_positions.py

# Update daily log
# (Manual for now, will automate)

# Check what we missed
python3 ghost_portfolio_tracker.py
```

### Update Logs
- [ ] Update `portfolio_daily_log.csv`
- [ ] Update `memory/YYYY-MM-DD.md` with day's events
- [ ] Update `memory/trade_decisions.md` with decisions
- [ ] Update `state/current.md` with final status
- [ ] Update `scanner_performance.csv` with outcomes

### Performance Review
**Today's Stats:**
- Portfolio Value: $________ (Change: $________)
- Unrealized P&L: $________ (_____%)
- Trades Executed: ___
- Wins: ___ | Losses: ___
- Best Position: _____ (+_____%)
- Worst Position: _____ (-_____%)

**Lessons Learned:**
- What worked: _______________________________
- What didn't: _______________________________
- Adjustment needed: _______________________________

---

## 🏁 WEEKEND REVIEW (Friday EOD)

```bash
# Run weekly review
python3 scripts/weekly_review_template.py
```

**Weekly Stats:**
- [ ] Total trades closed: ___
- [ ] Win rate: ____%
- [ ] Average return: ____%
- [ ] Best trade: _____ (+_____%)
- [ ] Worst trade: _____ (-_____%)
- [ ] Scanner accuracy: ____%
- [ ] Comparison to SPY: ____%

**Next Week Planning:**
- [ ] Review scanner performance
- [ ] Adjust profit targets if needed
- [ ] Identify pattern improvements
- [ ] Set goals for next week

---

## 🚨 EMERGENCY PROCEDURES

### If System/API Down
1. **Manual Portfolio Check:**
   - Log into Alpaca web interface
   - Check all positions manually
   - Note P&L for each position
   - Execute stops/targets manually if needed

2. **Backup Data:**
   ```bash
   # Backup critical files
   cp data/portfolio_tracking.csv data/portfolio_tracking_backup_$(date +%Y%m%d).csv
   cp data/scanner_performance.csv data/scanner_performance_backup_$(date +%Y%m%d).csv
   ```

3. **Contact:**
   - Alpaca Support: support@alpaca.markets
   - Polygon Support: support@polygon.io

### If Position Requires Immediate Action
1. **Stop-Loss Hit:**
   - Sell immediately at market
   - Log decision in memory/trade_decisions.md
   - Update portfolio_tracking.csv
   - Add to ghost_portfolio.json for tracking

2. **Profit Target Hit:**
   - Sell 50% at market
   - Move stop to breakeven on remaining 50%
   - Log decision
   - Add to ghost_portfolio.json

---

## 📝 QUICK REFERENCE

### File Locations
```
Scanner:          ~/workspace/diamond_scanner.py
Portfolio Check:  ~/workspace/check_positions.py
Stop-Loss:        ~/workspace/portfolio_stoploss_check.py
Profit Target:    ~/workspace/check_profit_targets.py
Morning Briefing: ~/workspace/morning_briefing.py
Market Open:      ~/workspace/market_open_check.py
Ghost Portfolio:  ~/workspace/ghost_portfolio_tracker.py

Data:             ~/workspace/data/
State:            ~/workspace/state/current.md
Memory:           ~/workspace/memory/
Logs:             ~/workspace/logs/ (create if needed)
```

### Key Thresholds
- **Stop-Loss:** -15% (exit immediately)
- **Watch Zone:** -12% to -15% (monitor closely)
- **Profit Target:** +30% (scale out 50%)
- **Scale-Out Zone:** +25% to +30% (prepare)
- **Daily Budget:** $300 max per day
- **Position Size:** Max 20% of portfolio
- **Max Positions:** 20 stocks

### Scanner Scoring (V3.2)
- **Max Score:** 305 points
- **Excellent:** >200 points
- **Good:** 150-199 points
- **Okay:** 100-149 points
- **Pass:** <100 points

**Key Factors:**
- Float <5M shares: 60 points (jackpot)
- Short interest >7 DTC: 25-30 points
- Explosive volume (100x): 30 points
- Gap-up >10%: 20 points
- Market cap $500M-$1B: 15 points

---

## ✅ TODAY'S CHECKLIST SUMMARY

**Pre-Market (6:00 AM):**
- [ ] Run morning briefing
- [ ] Review portfolio P&L
- [ ] Check stops and targets
- [ ] Review market context
- [ ] Plan today's trades

**Market Open (6:30 AM):**
- [ ] Execute profit-taking
- [ ] Execute stop-losses
- [ ] Enter new positions
- [ ] Run scanner

**Intraday (Every Hour):**
- [ ] Check stops
- [ ] Check targets
- [ ] Update state

**End of Day (4:00 PM):**
- [ ] Final portfolio check
- [ ] Update logs
- [ ] Review performance
- [ ] Plan tomorrow

**Print this page and keep it next to your trading desk!**

---

**Last Updated:** 2026-02-22
**Version:** 1.0
**System:** Diamond Scanner V3.2
