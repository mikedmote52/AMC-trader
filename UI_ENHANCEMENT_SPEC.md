# UI Enhancement Spec - Trading Dashboard Upgrades

**For:** Codex/Claude Code  
**Project:** amc-trader (https://amc-trader.onrender.com)  
**Date:** 2026-02-12

---

## Overview

Enhance the trading dashboard with:
1. **Sortable portfolio table** (by any column)
2. **Buy/Sell actions** (dollars or shares)
3. **Thesis display** for each position
4. **Thesis tracking** & learning system integration

---

## Feature 1: Sortable Portfolio Table

### Current State:
Portfolio shows positions in a table, but no sorting.

### Required:
Make every column header **clickable** to sort:

**Columns to make sortable:**
- Symbol (A-Z, Z-A)
- Shares (high to low, low to high)
- Avg Cost ($)
- Current Price ($)
- Market Value ($)
- P&L $ (biggest gain/loss first)
- P&L % (best/worst performers)
- Thesis (A-Z by thesis text)

**UX:**
- Click header → sort ascending
- Click again → sort descending
- Show arrow indicator (▲/▼) on sorted column
- Default sort: **P&L %** (biggest winners first)

**Implementation:**
```javascript
// Add to app.js
function sortTable(columnIndex, type = 'number') {
    const table = document.getElementById('positionsTable');
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    
    rows.sort((a, b) => {
        const aVal = a.cells[columnIndex].textContent;
        const bVal = b.cells[columnIndex].textContent;
        
        if (type === 'number') {
            return parseFloat(aVal.replace(/[$,%]/g, '')) - parseFloat(bVal.replace(/[$,%]/g, ''));
        } else {
            return aVal.localeCompare(bVal);
        }
    });
    
    rows.forEach(row => table.querySelector('tbody').appendChild(row));
}

// Add click handlers to headers
document.querySelectorAll('th[data-sortable]').forEach(th => {
    th.addEventListener('click', () => sortTable(th.cellIndex, th.dataset.type));
});
```

---

## Feature 2: Buy/Sell Actions Per Position

### Current State:
No way to trade from dashboard.

### Required:
Add **Buy More** / **Sell** buttons to each position row.

**UI Design:**
```
Actions Column:
┌─────────────────────┐
│ [Buy More] [Sell]  │
└─────────────────────┘
```

**Click "Buy More" → Modal opens:**
```
┌───────────────────────────────┐
│  Buy More RIVN                │
├───────────────────────────────┤
│  Current: 13 shares @ $14.40  │
│  Price now: $15.35            │
│                               │
│  [ ] Buy by Dollar Amount     │
│      $_____ (enter amount)    │
│      = ~__ shares             │
│                               │
│  [✓] Buy by Share Count       │
│      ___ shares               │
│      = ~$____ total           │
│                               │
│  [Cancel] [Execute Buy]       │
└───────────────────────────────┘
```

**Click "Sell" → Modal opens:**
```
┌───────────────────────────────┐
│  Sell RIVN                    │
├───────────────────────────────┤
│  Holding: 13 shares @ $14.40  │
│  Current P&L: +$12.35 (+8.6%) │
│                               │
│  [ ] Sell by Dollar Amount    │
│      $_____ worth             │
│      = ~__ shares             │
│                               │
│  [✓] Sell by Share Count      │
│      ___ shares (max: 13)     │
│                               │
│  Quick Actions:               │
│  [Sell 25%] [Sell 50%]        │
│  [Sell 100% (Close)]          │
│                               │
│  [Cancel] [Execute Sell]      │
└───────────────────────────────┘
```

**Backend Endpoint:**
```python
@app.route('/api/trade', methods=['POST'])
def execute_trade():
    """
    Execute buy/sell order via Alpaca API
    Request body:
    {
        "symbol": "RIVN",
        "action": "buy" or "sell",
        "quantity": 10,  # shares
        "notional": 150  # dollars (alternative to quantity)
    }
    """
    data = request.json
    symbol = data['symbol']
    action = data['action']
    
    # Build Alpaca order
    order_data = {
        'symbol': symbol,
        'side': action,
        'type': 'market',
        'time_in_force': 'day'
    }
    
    # Either qty or notional (dollar amount)
    if 'quantity' in data:
        order_data['qty'] = data['quantity']
    elif 'notional' in data:
        order_data['notional'] = data['notional']
    
    # Submit to Alpaca
    response = requests.post(
        f'{ALPACA_BASE_URL}/orders',
        headers=ALPACA_HEADERS,
        json=order_data
    )
    
    if response.status_code in [200, 201]:
        return jsonify({'success': True, 'order': response.json()})
    else:
        return jsonify({'success': False, 'error': response.text}), 400
```

**Daily Limit Check:**
```python
# Before executing buy, check daily budget
def check_daily_limit(amount):
    """
    Read today's trades from portfolio_tracking.csv
    Ensure total buys < $300/day
    """
    import csv
    from datetime import datetime
    
    today = datetime.now().strftime('%Y-%m-%d')
    total_spent = 0
    
    with open('data/portfolio_tracking.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['entry_date'] == today and row['entered'] == 'Yes':
                total_spent += float(row['entry_price']) * float(row.get('shares', 0))
    
    remaining = 300 - total_spent
    
    if amount > remaining:
        return False, f"Daily limit: ${remaining:.2f} remaining"
    
    return True, remaining
```

---

## Feature 3: Thesis Display

### Current State:
No thesis shown on dashboard.

### Required:
**Add "Thesis" column** to portfolio table showing why each position was entered.

**Data Source:**
`data/portfolio_tracking.csv` has `entry_thesis` column with thesis for each position.

**Backend Endpoint:**
```python
@app.route('/api/portfolio/thesis')
def get_portfolio_thesis():
    """
    Returns thesis for each active position
    """
    import csv
    
    positions = []
    
    with open('data/portfolio_tracking.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get('exit_date'):  # Still open
                positions.append({
                    'symbol': row['symbol'],
                    'entry_date': row['entry_date'],
                    'entry_thesis': row['entry_thesis'],
                    'scanner_score': row.get('scanner_score', 0),
                    'vigl_match': row.get('vigl_match', 'unknown')
                })
    
    return jsonify({'positions': positions})
```

**Frontend Display:**

Expand each row to show thesis:

```
┌────────────────────────────────────────────────┐
│ RIVN  13 shares  $14.40  $15.35  +$12.35 (+8.6%) │
│                                                │
│ 📝 Thesis (Feb 11):                           │
│ Scanner top pick (155 pts). +1.8% PERFECT     │
│ momentum, 4/4 days accelerating volume,       │
│ earnings beat catalyst, breakout detected.    │
│ Entry before move. Large float (1.2B) is      │
│ only concern but strong fundamentals.         │
│                                                │
│ ✅ Thesis Status: VALID                       │
│ Days held: 1 | Target: +30% | Stop: -15%     │
└────────────────────────────────────────────────┘
```

**Implementation:**
```javascript
// Click row to expand thesis
row.addEventListener('click', () => {
    const thesisRow = row.nextElementSibling;
    thesisRow.classList.toggle('hidden');
});
```

**CSS:**
```css
.thesis-row {
    background: #f9fafb;
    border-left: 4px solid #3b82f6;
}

.thesis-content {
    padding: 1rem;
    font-size: 0.9rem;
    line-height: 1.5;
}

.thesis-status {
    display: flex;
    gap: 1rem;
    margin-top: 0.5rem;
    font-size: 0.85rem;
    color: #6b7280;
}
```

---

## Feature 4: Thesis Tracking & Learning

### Current State:
Thesis is static text.

### Required:
**Dynamic thesis validation** that updates based on performance.

**Thesis Status Indicators:**

1. **✅ VALID** - Thesis playing out as expected
   - Price moving toward target
   - Volume/momentum continuing
   - No contrary signals

2. **⚠️ WATCH** - Thesis under pressure
   - Price stalling or reversing
   - Volume declining
   - Approaching stop-loss

3. **❌ INVALID** - Thesis broken
   - Price hit stop-loss
   - Catalyst delayed/cancelled
   - Fundamentals changed

**Backend Logic:**
```python
def validate_thesis(position):
    """
    Analyze if thesis is still valid based on:
    - Price action (vs entry, vs target, vs stop)
    - Days held (vs expected hold time)
    - Volume trends (vs entry volume)
    - News/catalysts (delayed or happened)
    """
    entry_price = position['entry_price']
    current_price = position['current_price']
    stop_loss = entry_price * 0.85  # -15%
    target = entry_price * 1.30  # +30%
    
    pct_change = ((current_price - entry_price) / entry_price) * 100
    
    # Status logic
    if pct_change <= -12:
        return '⚠️ WATCH', 'Approaching stop-loss'
    elif pct_change >= 25:
        return '✅ VALID', 'Approaching profit target'
    elif pct_change > 0:
        return '✅ VALID', 'Thesis playing out'
    else:
        return '⚠️ WATCH', 'Price below entry'
```

**Learning Integration:**

When position closes, analyze thesis performance:

```python
def analyze_thesis_outcome(position, outcome):
    """
    Add to learning_updates.json:
    - What thesis factors predicted success?
    - Which failed?
    - Update recommendations
    """
    thesis_factors = {
        'scanner_score': position['scanner_score'],
        'vigl_match': position['vigl_match'],
        'entry_momentum': position['change_pct'],
        'float_size': position.get('float_shares'),
        'catalyst': position.get('catalyst_text')
    }
    
    learning_entry = {
        'date': datetime.now().isoformat(),
        'symbol': position['symbol'],
        'outcome': outcome,  # 'WIN' or 'LOSS'
        'return_pct': position['return_pct'],
        'thesis_factors': thesis_factors,
        'lesson': generate_lesson(thesis_factors, outcome)
    }
    
    # Append to learning_updates.json
    with open('data/learning_updates.json', 'a') as f:
        json.dump(learning_entry, f)
        f.write('\n')
```

**Learning Dashboard Tab:**

Add new tab showing:
```
┌─────────────────────────────────────────┐
│ Thesis Performance Analysis             │
├─────────────────────────────────────────┤
│                                         │
│ Win Rate by Thesis Type:                │
│                                         │
│ Scanner 150+ pts:  75% (3 wins, 1 loss) │
│ Scanner 110-149:   60% (6 wins, 4 loss) │
│ Scanner <110:      40% (2 wins, 3 loss) │
│                                         │
│ VIGL Perfect Match: 80% win rate        │
│ VIGL Near Match:    65% win rate        │
│ No VIGL:            50% win rate        │
│                                         │
│ 💡 Recommendation:                      │
│ Focus on 150+ score + VIGL pattern      │
│ Avoid <110 scores (low success rate)   │
└─────────────────────────────────────────┘
```

---

## Implementation Priority

**Phase 1 (Essential):**
1. ✅ Sortable portfolio table (1 hour)
2. ✅ Buy/Sell modals with dollar/share input (2 hours)
3. ✅ Thesis column display (1 hour)

**Phase 2 (Enhanced):**
4. ✅ Thesis validation logic (1 hour)
5. ✅ Learning integration on close (1 hour)
6. ✅ Learning dashboard tab (2 hours)

**Total Time:** ~8 hours for full implementation

---

## Files to Modify

### Backend (`app.py`):
- Add `/api/trade` endpoint (buy/sell)
- Add `/api/portfolio/thesis` endpoint
- Add `/api/thesis/validate` endpoint
- Add daily limit checking

### Frontend (`static/js/app.js`):
- Add table sorting functions
- Add trade modal UI
- Add thesis expand/collapse
- Add thesis status indicators

### CSS (`static/css/style.css`):
- Modal styles
- Thesis row styles
- Sort indicator arrows
- Status badge colors

### Data Integration:
- Read from `data/portfolio_tracking.csv`
- Write to `data/learning_updates.json`
- Link to `data/scanner_performance.csv`

---

## Testing Checklist

- [ ] Portfolio sorts by each column
- [ ] Buy modal calculates shares from dollars
- [ ] Sell modal shows max shares
- [ ] Quick sell buttons (25%/50%/100%) work
- [ ] Daily limit prevents >$300 buys
- [ ] Thesis displays for all positions
- [ ] Thesis status updates correctly
- [ ] Closed positions log to learning system
- [ ] Learning tab shows thesis performance

---

## Security Notes

- Validate all trade inputs server-side
- Enforce daily $300 limit
- Log all trades to CSV for audit
- Show confirmation before executing
- Prevent duplicate orders (debounce buttons)

---

**Ready for Codex!** 

Give this spec to Claude Code and it will implement all features. Estimated completion: 8 hours of work.
