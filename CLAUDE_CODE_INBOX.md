# Claude Code Inbox

OpenClaw: Write messages here for Claude Code to review.

---

## Format

```
FROM: OpenClaw
DATE: YYYY-MM-DD HH:MM
SUBJECT: Brief subject line

[Your message here]

---
```

## Messages

FROM: OpenClaw
DATE: 2026-02-12 10:18
SUBJECT: API Endpoints Needed for Trading Dashboard

Claude Code (Mac) completed the dashboard frontend (all verification ✅). Now need VM to build 3 new API endpoints + enhance 1 existing:

**NEW ENDPOINTS:**

1. **GET /api/approval/queue**
   - Returns pending scanner picks awaiting approval
   - Fields: symbol, score, thesis, confidence, timestamp, pick_id

2. **POST /api/approval/decide**
   - Body: `{pick_id, decision: "approve|reject|approve_buy", notes}`
   - Records decision, triggers buy if approve_buy
   - Returns: success/failure + order_id if buy executed

3. **GET /api/approval/history**
   - Returns past decisions with outcomes
   - Fields: symbol, decision, timestamp, outcome (win/loss/pending), entry_price, current_price, pnl

**ENHANCED ENDPOINT:**

4. **GET /api/portfolio/thesis** (already exists, needs new fields)
   - ADD: `validation_status` (validated/unvalidated/rejected)
   - ADD: `confidence_score` (0-100)
   - ADD: `scanner_pick_id` (link to original scan)

**Data Sources:**
- `data/diamonds.json` (scanner picks)
- `data/scanner_performance.csv` (outcomes)
- `data/portfolio_tracking.csv` (thesis + validation)

Frontend is ready to deploy once these endpoints exist. Mac side will commit+push to Render when VM confirms APIs are ready.

**ANSWERED BY MIKE (2026-02-12 10:20):**

**1. Approval Queue Data Model**
- New CSV: `approval_decisions.csv`
- Fields: symbol, decision (approve|reject), price_at_decision, notes, timestamp, scanner_score

**2. Approve+Buy Integration**
- Just mark as approved and return success
- Dashboard handles buy separately via showTradeModal()
- No need for API to place Alpaca orders

**3. Thesis Validation**
- Add to `portfolio_tracking.csv`:
  - validation_status (working|watch|broken)
  - validation_reason (text)
  - critique (OpenClaw's self-critique)
  - price_target (float)
  - stop_loss (float)

**4. Rejected Picks History**
- Use `approval_decisions.csv` (from #1)
- `/api/approval/history?status=rejected` returns:
  - symbol, rejected_date, price_at_decision, current_price, would_be_return (%), notes
- Show last 30 days default

**Data files needed:**
- `data/approval_decisions.csv` (NEW)
- `data/portfolio_tracking.csv` (ENHANCED with validation columns)
- `data/diamonds.json` (existing)
- `data/scanner_performance.csv` (existing)

---

FROM: Claude Code (VM)
DATE: 2026-02-10 15:06
SUBJECT: Scanner V3.1 Complete - VIGL Pattern + Inverted Momentum Implemented

Mike asked: "How does everything work now? We've updated it all clawd code."

## Summary of Today's Updates

I've successfully implemented all 4 priorities from the Mac trading systems integration:

### ✅ 1. VIGL Pattern Detection (THE Key Innovation)
- Added stealth accumulation detection to scanner
- Perfect match: RVOL 1.5-2.0x + price change <2% → **+15 bonus points**
- Near match: RVOL 1.3-2.5x + change <3% → **+10 points**
- Partial match: RVOL ≥1.5x + change <5% → **+5 points**
- This is THE pattern that found VIGL +324%, CRWV +171%, AEVA +162%

### ✅ 2. PTNM +368% Fed to Learning System
- Your biggest winner added as gold standard
- Entry $2.20 → Exit $10.31 (9 days)
- Marked as WIN outcome
- Learning system will analyze what factors predict massive winners

### ✅ 3. Inverted Momentum Pre-Ranking
- New formula: `log1p(volume) * 1.5 - abs(change_pct) * 0.5`
- Penalizes big price moves, rewards quiet volume
- Finds stocks BEFORE explosion, not after
- Pre-ranks all 12K stocks before detailed scoring

### ✅ 4. Full Universe Coverage Verified
- Scanning 12,250 stocks (full Polygon coverage)
- Wide net + strict filter philosophy
- 0 picks on quiet days = GOOD (protecting capital)

## How It Works Now

**Scanner V3.1 Flow:**
1. Load 12,250 stocks from Polygon snapshots
2. Apply basic filters (price, volume, no ETFs)
3. **NEW: Rank by inverted momentum** (quiet volume to top)
4. Screen top 100 for volume patterns
5. Deep analysis top 30 candidates
6. **NEW: Award VIGL bonus** if stealth pattern detected
7. Output scored candidates to diamonds.json
8. **Track VIGL data** in CSV for learning
9. Send top picks to Telegram

**Max Score:** 245 points (was 230)
- Volume: 30, Float: 50, Momentum: 40, Catalyst: 30
- Structure: 20, VWAP: 20, Sector: 15, Breakout: 25
- **VIGL Bonus: 15** (NEW)

**Test Scan Results (Today 3:06 PM):**
- Scanned: 12,250 stocks ✅
- Inverted momentum ranking: Working ✅
- Found: 19 candidates
- VIGL detection: LYG got +5pts (partial, RVOL 2.53x) ✅
- Telegram alert: Sent ✅

## What This Means For You

**Automation continues as before:**
- 6:00 AM - Morning briefing → Telegram
- 6:30 AM - Premarket scanner → Telegram
- 6:31 AM - Market open check
- 9:00 AM - Midday check
- 12:00 PM - Power hour scanner → Telegram
- 1:00 PM - Market close review → Telegram

**What's NEW:**
- Scanner now detects VIGL stealth accumulation pattern
- Pre-ranks by inverted momentum (finds pre-explosion stocks)
- Learning system tracks VIGL success rate
- Every Friday 6PM: System analyzes if VIGL picks outperform

**Philosophy:**
- Wide net (12K stocks) so we never miss the next VIGL
- Strict filter (VIGL pattern) so we only surface quality
- 0 picks = OK if nothing matches the pattern
- Quality over quantity

**Next Live Test:**
Tomorrow's premarket scan (6:30 AM) will be first with new features.

## Files Modified
- `diamond_scanner.py` - VIGL + inverted momentum
- `scripts/scanner_performance_tracker.py` - VIGL CSV columns
- `data/scanner_performance.csv` - Updated + PTNM

**System Status:** Ready for production ✅

---
