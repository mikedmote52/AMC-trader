# Alpha Calculation Enhancement

## Overview

The scanner performance tracker has been enhanced to calculate **market-adjusted returns (alpha)** for all completed trades. This allows you to see whether your strategy is truly generating edge or just riding the market's momentum.

## What is Alpha?

**Alpha** measures your stock pick's performance relative to the market (SPY):

```
Alpha = Stock Return - SPY Return
```

### Examples:

1. **Positive Alpha (Good)**
   - Stock: +15% return
   - SPY: +2% return
   - Alpha: +13%
   - Interpretation: Your pick outperformed the market by 13%

2. **Negative Alpha (Warning)**
   - Stock: +5% return
   - SPY: +8% return
   - Alpha: -3%
   - Interpretation: You underperformed - would've done better in SPY

3. **The Importance**
   - A +5% return during a +10% market rally is actually poor performance (alpha = -5%)
   - A +2% return during a -5% market drop is excellent (alpha = +7%)

## New CSV Columns

Three new columns have been added to `scanner_performance.csv`:

| Column | Description | Example |
|--------|-------------|---------|
| `spy_return` | SPY percentage return for the same holding period | 2.50 |
| `alpha` | Stock return minus SPY return | 12.50 |
| `sector_return` | Sector ETF return (placeholder for future) | - |

## How It Works

### 1. Automatic Calculation

When you close a position using `update_trade_outcome()`, the system now:

1. Fetches SPY daily bars from Alpaca Data API for the exact holding period
2. Calculates SPY return using entry date and exit date
3. Computes alpha = stock_return - spy_return
4. Stores all metrics in the CSV

### 2. Error Handling

The system gracefully handles API failures:

- If SPY data is unavailable, `spy_return` and `alpha` columns are left empty
- Existing functionality continues to work
- Warning message is printed but trade outcome is still recorded

### 3. Performance Analysis

The `analyze_performance()` function now includes alpha metrics:

- Average alpha across all trades
- Average SPY return for comparison
- Number of trades with positive alpha
- Positive alpha rate (% of trades that beat the market)

## Usage Examples

### Recording a Trade Outcome

```python
from scanner_performance_tracker import update_trade_outcome

# When you close a position
update_trade_outcome(
    symbol='AAPL',
    exit_price=185.50,
    exit_date='2026-02-15',
    notes='Took profit at resistance'
)

# Output:
# 📊 Alpha calculation: Stock +15.2% - SPY +2.1% = +13.1%
# ✅ Recorded AAPL outcome: WIN (+15.2% in 5 days)
```

### Viewing Performance Report

```bash
cd /Users/mikeclawd/.openclaw/workspace/scripts
python3 scanner_performance_tracker.py
```

You'll now see:

```
📊 Overall Performance:
   Total Trades: 25
   Wins: 18 | Losses: 7
   Win Rate: 72.0%
   Avg Return: +8.5%
   Avg Win: +12.3% | Avg Loss: -4.2%

🎯 Market-Adjusted Performance (Alpha):
   Trades with Alpha Data: 25
   Avg Alpha: +6.2% (outperformance vs SPY)
   Avg SPY Return: +2.3%
   Positive Alpha Rate: 76.0% (19/25 trades)
   ✅ Strategy is generating alpha (beating the market)
```

## Testing

A test script is included to verify functionality:

```bash
cd /Users/mikeclawd/.openclaw/workspace/scripts
python3 test_alpha_calculation.py
```

This tests:
- SPY data fetching for various date ranges
- Alpha calculation logic
- Edge cases (same-day trades, weekends, etc.)

## Data Source

- **Market Data**: Alpaca Markets Data API v2
- **Benchmark**: SPY (S&P 500 ETF)
- **Adjustment**: Split and dividend adjusted prices

## Future Enhancements

### Planned:
1. **Sector-Relative Returns**
   - Add sector ETF mapping (XLF, XLK, XLE, etc.)
   - Calculate sector-relative alpha
   - Identify if outperformance is stock-specific or sector-wide

2. **Risk-Adjusted Alpha**
   - Calculate Sharpe ratio
   - Volatility-adjusted returns
   - Maximum drawdown analysis

3. **Market Regime Analysis**
   - Separate alpha by market conditions (bull/bear/sideways)
   - Identify which conditions your strategy excels in

## Technical Details

### API Endpoint

```
GET https://data.alpaca.markets/v2/stocks/bars
```

### Parameters:
- `symbols`: SPY
- `timeframe`: 1Day
- `start`: Entry date minus 7 days (safety buffer)
- `end`: Exit date
- `adjustment`: all (split and dividend adjusted)

### Return Calculation:

```python
spy_return = ((end_close - start_close) / start_close) * 100
alpha = stock_return - spy_return
```

## Files Modified

1. **scanner_performance_tracker.py**
   - Added `get_spy_return()` function
   - Enhanced `update_trade_outcome()` to calculate alpha
   - Updated `analyze_performance()` to include alpha statistics
   - Modified `print_performance_report()` to display alpha metrics
   - Updated CSV headers with new columns

2. **Data Files**
   - `scanner_performance.csv` - Now includes spy_return, alpha, sector_return columns

## Backward Compatibility

- Existing scanner performance data is preserved
- Old trades without alpha data won't break reports
- The system detects and handles missing alpha data gracefully
- All existing functions continue to work as before

## Safety Features

1. **Optional Calculation**: If SPY data is unavailable, the trade is still recorded
2. **Error Handling**: API failures are caught and logged, but don't stop execution
3. **Date Validation**: Handles weekends, holidays, and market closures
4. **Buffer Period**: Fetches extra days to ensure data availability

## Key Insights

This enhancement helps you answer critical questions:

1. **Am I Actually Skilled?**
   - Positive alpha = Real edge
   - Negative alpha = Just riding the market (or worse)

2. **When Do I Perform Best?**
   - Compare alpha in different market conditions
   - Identify patterns in your outperformance

3. **Is My Scanner Working?**
   - High win rate with low alpha = Following momentum
   - Lower win rate with high alpha = True edge on picks

4. **Portfolio Optimization**
   - Focus on strategies/setups with highest alpha
   - Eliminate negative-alpha patterns

---

**Remember**: A 50% win rate with high alpha beats a 70% win rate with negative alpha!
