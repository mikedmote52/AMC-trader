# SCANNER V2 - Finding Diamonds BEFORE They Pop

## The Real Problem

Current scanner finds stocks **AFTER** they've moved. VIGL was found at +5% on day 1, then went to +369%. We need to find stocks at +0-3% BEFORE the big move.

## What Actually Predicted the Winners

Looking at VIGL, CRWV, AEVA success:

### 1️⃣ **VOLUME ACCELERATION (Most Important)**
- Not "3x average" - that's too late
- Need: Volume ramping UP day-over-day for 2-3 days BEFORE breakout
- Example: Day 1: 1.5x → Day 2: 2x → Day 3: 3x → Day 4: BREAKOUT

### 2️⃣ **FLOAT + SHORT INTEREST COMBO**
- Float < 50M alone isn't enough
- Need: Float < 50M AND (Short % > 15% OR borrow fee > 10%)
- This is the SQUEEZE setup

### 3️⃣ **FRESH CATALYST (Within 48 Hours)**
- Not "recent news" - needs to be BREAKING
- FDA approval, earnings beat, contract win
- Social sentiment ACCELERATING (not just "high")

### 4️⃣ **PRICE CONSOLIDATION → BREAKOUT**
- Stock trading sideways for 5-10 days
- Then volume spike + price move = breakout starting
- NOT already up 10%+

### 5️⃣ **OPTIONS ACTIVITY (For Larger Caps)**
- Call volume spiking
- Unusual options activity
- IV increasing
- This predicts gamma squeezes (NVDA/TSLA)

---

## New Scanner Architecture

### **Phase 1: Pre-Filter (10 seconds)**
Use Polygon snapshot API:
- Price: $0.50-$100
- Volume: > 500K (lower threshold to catch early)
- NO momentum filter yet (we want stocks at 0-3%)
Result: ~500-800 stocks

### **Phase 2: Volume Pattern Detection (30 seconds)**
For each stock, check last 5 days:
- Is volume increasing day-over-day?
- Is today's volume > yesterday > day before?
- Score: volume_acceleration_score (0-20 pts)
Result: ~100-200 stocks with volume patterns

### **Phase 3: Float + Short Analysis (60 seconds)**
Get float and short data from Polygon:
- Float < 50M: +30 pts
- Float < 20M: +40 pts
- Float < 10M: +50 pts
- Short % > 15%: +20 pts
- Short % > 30%: +30 pts
Result: ~50-100 stocks with squeeze potential

### **Phase 4: Catalyst Detection (30 seconds)**
Check news from last 48 hours:
- FDA/regulatory: +30 pts
- Earnings beat: +25 pts
- Contract/partnership: +20 pts
- Insider buying: +15 pts
- High social sentiment: +10 pts
Result: ~20-40 stocks with catalysts

### **Phase 5: Technical Confirmation (20 seconds)**
For remaining stocks:
- Breaking consolidation? +15 pts
- Above key moving averages? +10 pts
- RSI 50-70? +10 pts
- MACD crossover? +10 pts
Result: ~10-20 trade-ready stocks

### **Phase 6: Options Flow (If Applicable) (20 seconds)**
For stocks with options:
- Unusual call activity? +15 pts
- IV increasing? +10 pts
- Call/put ratio > 3? +10 pts

---

## Scoring System (0-200 pts)

- **50 pts:** Float (ultra-low = 50)
- **30 pts:** Short interest
- **30 pts:** Catalyst (breaking news)
- **20 pts:** Volume acceleration
- **20 pts:** Technical breakout
- **20 pts:** Options flow
- **15 pts:** Multi-day structure
- **10 pts:** RSI/momentum
- **5 pts:** Other factors

**Threshold:**
- **≥ 120 pts:** TRADE-READY (high conviction)
- **100-119 pts:** STRONG WATCH
- **80-99 pts:** MONITOR

---

## Key Differences from Current Scanner

| Old Scanner | New Scanner |
|-------------|-------------|
| Looks for +5-15% moves | Looks for 0-3% before breakout |
| Volume 3x avg (too late) | Volume ACCELERATING (early) |
| Float check only | Float + Short combo |
| "Recent" news | News within 48 hours |
| Static scoring | Pattern detection |
| Misses early setups | Catches pre-breakout |

---

## Implementation Priority

**Week 1 (This Week):**
1. ✅ Build volume acceleration detector
2. ✅ Integrate float + short data (Polygon has this)
3. ✅ Add 48-hour catalyst filter
4. ✅ Test on historical data (did it find VIGL early?)

**Week 2:**
1. Add options flow detection
2. Build consolidation/breakout detector
3. Add social sentiment tracking (Reddit/StockTwits)
4. Backtest on June-July winners

**Week 3:**
1. Machine learning on historical patterns
2. Optimize scoring weights
3. Add paper trading validation
4. Full automation

---

## Success Metrics

**The scanner is working when:**
1. It finds stocks at +0-5% that go to +20%+ within 3 days
2. It alerts BEFORE breakout, not after
3. 70%+ of alerts score 120+ are profitable
4. It replicates the 63.8% basket return

**Current scanner:** Finds stocks already moving (too late)
**Target scanner:** Finds stocks ABOUT to move (early)

---

## Next Steps

1. Build volume acceleration detector (TODAY)
2. Test on today's market data
3. Compare to stocks that moved 10%+ tomorrow
4. Iterate until it works

This is what will find the diamonds.

---

_Created: 2026-02-03 11:47 AM PT_
