# Ghost Portfolio API Specification

## Endpoint: GET /api/ghost/portfolio

This endpoint tracks closed positions and calculates what their current value would be if still held.

### Response Structure

```json
{
  "summary": {
    "total_realized_gains": 45000.00,
    "theoretical_current_value": 112000.00,
    "total_closed_positions": 23,
    "avg_hold_days": 12.5
  },
  "closed_positions": [
    {
      "symbol": "NVDA",
      "exit_date": "2024-01-15T14:30:00Z",
      "exit_price": 120.50,
      "entry_price": 92.30,
      "qty": 100,
      "actual_gain": 2820.00,
      "actual_gain_percent": 30.5,
      "current_price": 310.25,
      "theoretical_gain": 21795.00,
      "theoretical_gain_percent": 236.1,
      "hold_days": 45
    }
  ]
}
```

### Field Descriptions

**summary:**
- `total_realized_gains` - Sum of all actual profits from closed positions
- `theoretical_current_value` - What those positions would be worth if still held
- `total_closed_positions` - Count of closed positions tracked
- `avg_hold_days` - Average days held before exit

**closed_positions:**
- `symbol` - Stock ticker
- `exit_date` - When position was sold (ISO 8601 format)
- `exit_price` - Price at which position was sold
- `entry_price` - Original purchase price
- `qty` - Number of shares sold
- `actual_gain` - Realized profit: (exit_price - entry_price) * qty
- `actual_gain_percent` - ((exit_price - entry_price) / entry_price) * 100
- `current_price` - Current market price (live)
- `theoretical_gain` - What profit would be if still held: (current_price - entry_price) * qty
- `theoretical_gain_percent` - ((current_price - entry_price) / entry_price) * 100
- `hold_days` - Days between entry and exit

### Data Source

Track all position exits (sells) in database with:
- Entry date, entry price, qty
- Exit date, exit price
- Symbol

For each closed position, fetch current price from market data API and calculate theoretical values.

### Sorting

Frontend sorts by "missed profit" (theoretical_gain - actual_gain) DESC to show biggest regrets first.

### Error Handling

If tracking not yet implemented:
```json
{
  "error": "Ghost portfolio tracking not available",
  "offline": true
}
```

### Update Frequency

Should refresh current prices whenever `/api/positions` updates (every 30 seconds during market hours).

### Implementation Notes

1. Create `closed_positions` table:
   ```sql
   CREATE TABLE closed_positions (
     id INT PRIMARY KEY,
     symbol VARCHAR(10),
     entry_date TIMESTAMP,
     entry_price DECIMAL(10,2),
     exit_date TIMESTAMP,
     exit_price DECIMAL(10,2),
     qty INT,
     user_id INT
   );
   ```

2. When position is fully closed (qty = 0), move from `positions` to `closed_positions`

3. Calculate current price for each closed position using same price feed as live positions

4. Frontend handles all display logic and calculations for "missed profit"
