# Polygon.io Setup Guide

## What We Get with Polygon.io

### **Starter Plan ($200/mo):**
✅ **Unlimited API calls**
✅ **Real-time stock data**
✅ **Historical data (5+ years)**
✅ **Options data** (OI, IV, Greeks)
✅ **Reference data:**
  - Float (shares outstanding)
  - Market cap
  - Sector/Industry
✅ **Aggregates** (bars: 1min, 5min, 15min, daily)
✅ **Ticker news**
✅ **Financial statements**

**Perfect for the Squeeze Strategy framework!**

---

## Setup Steps

### 1. Sign Up for Polygon.io

1. Go to: https://polygon.io/pricing
2. Sign up for **Starter Plan** ($200/mo)
3. Get your API key from dashboard

### 2. Save Credentials

Create file: `~/.openclaw/secrets/polygon.json`

```json
{
  "apiKey": "YOUR_API_KEY_HERE",
  "baseUrl": "https://api.polygon.io"
}
```

### 3. Install Python SDK

```bash
pip3 install --user polygon-api-client
```

### 4. Test Connection

```python
from polygon import RESTClient
import json

# Load credentials
with open('/Users/mikeclawd/.openclaw/secrets/polygon.json', 'r') as f:
    creds = json.load(f)

client = RESTClient(api_key=creds['apiKey'])

# Test: Get ticker details
ticker = client.get_ticker_details("AAPL")
print(f"Float: {ticker.share_class_shares_outstanding}")
print(f"Market Cap: ${ticker.market_cap:,.0f}")
```

---

## What the Scanner Will Get

Once Polygon is set up, the scanner will have:

### **Universe Filter:**
✅ Price: $0.50 - $100
✅ Volume: > 1M shares (30-day avg)
✅ Float: < 50M (for small-cap squeezes)

### **Early Momentum:**
✅ Intraday bars (5/15 min) for VWAP/EMA
✅ Multi-day structure (2-4 green days)
✅ Gain: +5% to +20% (not chasing)

### **Supply Constraint:**
✅ Float data
✅ Short interest (via Polygon)
✅ Options OI & IV (gamma squeeze detection)
✅ Call/put ratio

### **Catalyst Detection:**
✅ Recent news (via Polygon news API)
✅ Earnings dates
✅ Financial filings

### **Full 0-100 Scoring:**
Instead of current 60-point max, we'll have all data for true 100-point scores.

---

## Cost Breakdown

**Polygon Starter:** $200/mo
**Alpaca Paper Trading:** Free
**Total:** $200/mo

**ROI:**
- If scanner finds **one** 63.8% winner on a $300 position = **$191 profit**
- Pays for itself with **1 good trade per month**
- June-July framework found 2-4 winners every month

---

## Next Steps

**Once you have the API key:**

1. Save to `~/.openclaw/secrets/polygon.json`
2. I'll rebuild the scanner with full Polygon integration
3. Run first scan to validate setup
4. Schedule 6x daily scans via cron

**Want me to:**
- Wait for you to sign up and provide API key?
- Or build the integration now using a test/placeholder?

---

_Created: 2026-02-03 09:53 PT_
