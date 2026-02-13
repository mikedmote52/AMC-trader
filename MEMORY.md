# MEMORY.md - Long-Term Context

## Mike's Trading Rules (CRITICAL - READ EVERY SESSION)

### **DAILY LIMITS - NEVER EXCEED:**
- **Maximum spend per day: $300** (buys only, not counting sells)
- **Account size: ~$101K** (mostly cash, building positions slowly)
- **Position size: $150-300** per stock (small account, testing strategies)

### **Trading Strategy:**
- **Style:** Multi-week swing trading on small-caps ($0.50-$100 range) - NOT day trading
- **Hold time:** 1-4 weeks for explosive moves (60% portfolio return over time)
- **Scanner criteria:** Setup detection (catalysts, narrative, low float) - find stocks BEFORE they move
- **Entry timing:** Buy consolidation/pullbacks, not breakouts
- **DON'T CHASE:** Never buy stocks already up 10%+ on the day
- **Take profits:** Scale out at +30%, +50%, let winners run with trailing stops

### **Portfolio Management:**
- **Review frequency:** 6x daily (premarket, open, midday, power hour, close, after hours)
- **Stop losses:** -15% from entry (hard rule)
- **Max positions:** 10-12 stocks (currently 18 - too many)
- **Profit targets:** +30% first scale, +50% second scale
- **ALWAYS ask before placing trades** - confirm dollar amounts against daily limit

### **CRITICAL LESSON (2026-02-10):**
**Scanner was built WRONG - focused on day trading instead of swing trading**

**What was wrong:**
1. ❌ Scanning for momentum (stocks moving TODAY)
2. ❌ Day-trading mindset (in/out same day)
3. ❌ Chasing breakouts instead of finding setups
4. ❌ Scanner V3 too strict (found ZERO stocks)

**What Mike actually wants:**
1. ✅ Multi-week swing trading (hold 1-4 weeks)
2. ✅ Find stocks BEFORE they move (early setup detection)
3. ✅ Buy consolidation, not breakouts
4. ✅ 60% portfolio return over time (not daily wins)

**Scanner needs complete rebuild:**
- Prioritize: Catalysts, narrative, low float, sector rotation
- De-prioritize: Same-day momentum, volume spikes
- Focus: Setup detection (BEFORE the move)
- Example: ACHR at $7 (building) > ICHR at $45 (already moved)

---

## Account Details
- **Broker:** Alpaca (paper trading)
- **Credentials:** `~/.openclaw/secrets/alpaca.json`
- **Base URL:** `https://paper-api.alpaca.markets`

---

## Current Portfolio (as of 2026-02-03 9:29 AM PT)
**Active Positions (19 stocks):**

**Top Winners (Monitor for profit taking):**
- PTNM: 13 shares remaining (took 50% profit @ $10.15)
- SPHR: 8 shares total (original 4 + added 4 @ $95.48)
- LGN: 6 shares total (original 3 + added 3 @ $49.49)
- WULF: 21 shares @ $8.99 avg
- UEC: 8 shares @ $11.33 avg

**Watch for Breakout:**
- UUUU: 10 shares @ $24.17 (chase trade - needs to hold gains)

**Small Positions (consider consolidating):**
- RGTI, KOPN, SERV, KNOW, COOK, MMCA, PAII.U, IPCX, ITOS, KSS, SSRM

**Today's Activity:**
- ✅ Sold 50% PTNM (+$105 profit locked)
- ❌ Overspent: $948 vs $300 limit (keeping as lesson)
- ⚠️ Chased UUUU up +14% (monitoring closely)

---

## Key Lessons
1. **$300/day limit is SACRED** - write it in every trade script
2. **Don't chase green candles** - wait for red days to enter
3. **Ask Mike before executing** - especially multi-trade plans
4. **Position sizing matters** - $150-300 per stock, not $800 trades
5. **Memory files exist for a reason** - READ THEM EVERY SESSION

---

## Scanner Status (Updated 2026-02-03 9:52 AM PT)

### **Phase 1: Full Market Scanner Built**

**What's ready:**
- ✅ `full_market_scanner.py` - Scans ALL 7,062 NASDAQ/NYSE stocks
- ✅ Universe filter: price $0.50-$100, volume >1M
- ✅ Momentum detection: +5-20% (not chasing)
- ✅ Uses Alpaca API for real-time data
- ✅ Scores 0-100 using Squeeze Strategy framework

**What's missing (Phase 2):**
- ❌ Float data (need Polygon.io or FinViz scraper)
- ❌ Short interest / borrow fees
- ❌ Options OI / IV data
- ❌ Intraday bars (5/15 min for VWAP/EMA)
- ❌ Social sentiment tracking

**Current limitation:**
- Scanner works but scores are basic (momentum only)
- Need float + short data to identify real squeeze candidates
- Takes ~60 minutes to scan full market (rate limits)

**Next steps:**
1. Integrate Polygon.io MCP for float/short data
2. Add caching to speed up repeated scans
3. Run on cron schedule (6x daily)

---

_Updated: 2026-02-03 09:52 PT_
