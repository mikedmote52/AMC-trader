# Render Deployment Fix - Missing Alpaca Credentials

**Problem:** Website shows $0.00 and "Connecting..." because Render doesn't have Alpaca API keys.

**Solution:** Add environment variables in Render dashboard.

---

## Fix Steps:

### 1. Go to Render Dashboard
https://dashboard.render.com/web/srv-YOUR-SERVICE-ID

### 2. Click "Environment" Tab

### 3. Add These Variables:

**Variable:** `ALPACA_API_KEY`  
**Value:** `PKZ6EG2MCPTTD6S4EVXNCDET6H`

**Variable:** `ALPACA_API_SECRET`  
**Value:** `4dSYTkBZVgqh3myNQEGYV51fdvwv4NZx9C92zsqEqrxi`

**Variable:** `ALPACA_BASE_URL`  
**Value:** `https://paper-api.alpaca.markets/v2`

### 4. Click "Save Changes"

Render will automatically redeploy with the new environment variables.

---

## Verification:

After redeployment (takes ~2-3 minutes):

1. Visit https://amc-trader.onrender.com/
2. Portfolio Value should show **$101,580** (your current balance)
3. Positions should show **19 stocks**
4. You'll see PTNM, RIG, RIVN, etc.

---

## Alternative: Quick Test Locally

To verify the app works with your credentials:

```bash
cd /Users/mikeclawd/.openclaw/workspace
python3 app.py
```

Then visit http://localhost:5000 - should show your portfolio immediately.

---

## Security Note:

These are **paper trading** credentials, so it's safe to use them on Render. If you ever switch to live trading, consider using Render's secret management or environment variable encryption.

---

**Next:** Add the environment variables in Render and wait for redeploy!
