# Alpha Calculation - Quick Start Guide

## What Changed?

Your scanner performance tracker now automatically calculates **alpha** (market-adjusted returns) for every trade.

## TL;DR

**Alpha = Your Return - Market Return**

- Positive alpha = You beat the market ✅
- Negative alpha = Market beat you ⚠️

## How to Use

### Nothing Changes!

The system works automatically. Just use it as before:

```python
# When closing a position (same as always)
from scanner_performance_tracker import update_trade_outcome

update_trade_outcome('AAPL', exit_price=185.50)
```

**New Output:**
```
📊 Alpha calculation: Stock +15.2% - SPY +2.1% = +13.1%
✅ Recorded AAPL outcome: WIN (+15.2% in 5 days)
```

### View Your Alpha

Run the performance report:

```bash
python3 scanner_performance_tracker.py
```

**New Section:**
```
🎯 Market-Adjusted Performance (Alpha):
   Avg Alpha: +6.2% (outperformance vs SPY)
   Positive Alpha Rate: 76.0%
   ✅ Strategy is generating alpha (beating the market)
```

## Why This Matters

### Example 1: Fool's Gold
- Your trade: +8% gain ✅
- SPY that week: +12% 📈
- Alpha: -4% ❌
- **Reality**: You underperformed - should've bought SPY instead

### Example 2: True Skill
- Your trade: +3% gain ✅
- SPY that week: -5% 📉
- Alpha: +8% 🎯
- **Reality**: You outperformed in a down market - real edge!

## CSV Changes

Three new columns in `scanner_performance.csv`:

| Column | What It Shows |
|--------|---------------|
| spy_return | How SPY performed during your trade |
| alpha | Your outperformance vs SPY |
| sector_return | Reserved for future sector analysis |

## Key Insights You'll Get

1. **Real Win Rate**: Not just W/L, but market-beating trades
2. **True Edge**: Separate skill from market momentum
3. **Strategy Quality**: High alpha = real edge, Low alpha = market rider

## Example Scenarios

### Scenario A: Bull Market
```
Your trades: 70% win rate, +8% avg return
But SPY: +10% during same period
Result: -2% alpha = You're underperforming!
```

### Scenario B: Choppy Market
```
Your trades: 55% win rate, +4% avg return
But SPY: -2% during same period
Result: +6% alpha = You have real edge!
```

## What to Track

Focus on these new metrics:

1. **Average Alpha**: Should be positive over time
2. **Positive Alpha Rate**: Aim for >60%
3. **Alpha by Score Range**: Which scanner scores give best alpha?
4. **Alpha by Factor**: Float size, catalyst presence, etc.

## Files Created/Modified

1. ✅ `scanner_performance_tracker.py` - Enhanced with alpha calculation
2. ✅ `test_alpha_calculation.py` - Test the functionality
3. ✅ `migrate_scanner_csv.py` - Migrate existing data
4. ✅ `ALPHA_CALCULATION_README.md` - Full documentation
5. ✅ `scanner_performance.csv` - Now includes alpha columns

## Migration Complete

Your existing 675 scanner records have been preserved and updated with the new columns. Future trade closures will automatically calculate alpha.

## Questions?

**Q: What if SPY data is unavailable?**
A: Trade is still recorded, alpha fields are left empty. No errors.

**Q: Can I backfill alpha for old trades?**
A: Yes, but you'd need to manually call `update_trade_outcome()` again with the same exit data. The system will recalculate with alpha.

**Q: What about sector-relative returns?**
A: Coming soon! Need to add sector mapping first (XLF for financials, XLK for tech, etc.)

**Q: Does this slow down the system?**
A: No - it's a single API call per trade closure. Takes <1 second.

---

**Bottom Line**: You now have a more accurate picture of your actual trading edge. Use it to refine your strategy and focus on what truly works!
