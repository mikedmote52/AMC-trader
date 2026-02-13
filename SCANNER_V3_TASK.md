# Scanner V3 - Intraday + Sector Rotation

**Task for Claude Code:**

Build an enhanced version of `diamond_scanner.py` that adds:

## 1. Intraday VWAP Tracking

**Requirements:**
- Fetch 5-minute bars for candidates using Polygon API
- Calculate VWAP (Volume Weighted Average Price) for today
- Detect when price crosses above VWAP (bullish breakout signal)
- Add scoring bonus (+20 pts) for stocks currently above VWAP with volume

**Implementation:**
```python
def get_intraday_vwap(symbol):
    """
    Fetch today's 5-min bars and calculate VWAP
    Returns: (current_price, vwap, above_vwap, volume_ratio)
    """
    # Use Polygon: /v2/aggs/ticker/{symbol}/range/5/minute/{date}/{date}
    # VWAP = sum(price * volume) / sum(volume)
    # Check if current price > VWAP
    pass
```

**Scoring adjustment:**
- Price above VWAP + volume spike: +20 pts
- Price above VWAP (normal volume): +10 pts
- Price below VWAP: 0 pts

## 2. Sector Rotation Detection

**Requirements:**
- Fetch sector performance using Polygon snapshots
- Group stocks by sector (use ticker details API)
- Calculate sector strength: % of stocks in sector that are up today
- Identify "hot sectors" (>60% stocks green + avg gain >2%)
- Add scoring bonus (+15 pts) for stocks in hot sectors

**Implementation:**
```python
def get_sector_performance():
    """
    Analyze all sectors and return hot ones
    Returns: dict of {sector: {'pct_green': 0.65, 'avg_gain': 3.2}}
    """
    # Group by sector from ticker details
    # Calculate % green and avg % change
    # Return top 3 sectors
    pass

def is_hot_sector(sector, sector_data):
    """
    Check if sector is currently hot
    """
    if sector not in sector_data:
        return False
    
    data = sector_data[sector]
    return data['pct_green'] > 0.6 and data['avg_gain'] > 2.0
```

## 3. Real-Time Breakout Detection

**Requirements:**
- Check if stock is breaking out RIGHT NOW (intraday)
- Compare current 5-min volume to average 5-min volume
- Detect consolidation breakouts (tight range then expansion)

**Implementation:**
```python
def detect_intraday_breakout(symbol):
    """
    Check if stock is breaking out in current session
    Returns: bool + breakout_details
    """
    # Get last 10 bars (5-min)
    # Check for consolidation (low volatility) followed by expansion
    # Detect volume spike on breakout bar
    pass
```

## Files to Modify

1. **diamond_scanner.py** - Main scanner logic
   - Add intraday functions
   - Update scoring to include new factors
   - Keep existing volume/float/momentum logic

2. **Create new file: sector_tracker.py**
   - Sector grouping and analysis
   - Can be imported by scanner

## API Credentials

Already configured at: `/Users/mikeclawd/.openclaw/secrets/polygon.json`

```json
{
  "apiKey": "1ORwpSzeOV20X6uaA8G3Zuxx7hLJ0KIC",
  "baseUrl": "https://api.polygon.io"
}
```

## Testing

After implementation:
1. Run scanner manually: `python3 diamond_scanner.py`
2. Verify intraday data is fetching correctly
3. Check sector hot list makes sense
4. Compare scores to current scanner output

## Expected Outcome

**New scoring (max 230 points):**
- Volume acceleration: 30 pts (unchanged)
- Float: 50 pts (unchanged)
- Momentum (daily): 40 pts (unchanged)
- Catalyst: 30 pts (unchanged)
- Structure: 20 pts (unchanged)
- **VWAP position: 20 pts (NEW)**
- **Hot sector: 15 pts (NEW)**
- **Intraday breakout: 25 pts (NEW)**

**Better detection of:**
- Stocks breaking out RIGHT NOW (not just yesterday's data)
- Sector rotation trends
- Institutional buying (VWAP cross signals)

## Notes

- Don't break existing scanner functionality
- Keep caching logic for snapshots
- Rate limit Polygon API calls (5 requests/sec max)
- Add error handling for missing data
- Write results to same `data/diamonds.json` format

---

**When completely finished, run:**
```bash
openclaw gateway wake --text "Scanner V3 complete: Added intraday VWAP + sector rotation + breakout detection" --mode now
```
