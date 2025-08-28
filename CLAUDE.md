- API=https://amc-trader.onrender.com

# 1. Verify health (should include tag/commit/build now)
curl -s "$API/health" | jq .

# 2. Verify whoami (new endpoint)
curl -s "$API/_whoami" | jq .

# 3. Trigger a small test trade (should return error details if blocked)
curl -s -X POST "$API/trades/execute" \
  -H 'content-type: application/json' \
  -d '{"symbol":"QUBT","action":"BUY","mode":"live","notional_usd":10}' | jq .