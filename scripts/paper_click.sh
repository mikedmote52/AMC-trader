#!/usr/bin/env bash
set -euo pipefail
API="${API:-https://amc-trader.onrender.com}"
resp=$(curl -s -X POST "$API/trades/execute" -H "content-type: application/json" \
  -d '{"symbol":"AAPL","action":"BUY","qty":1,"mode":"auto"}')
echo "$resp" | jq -e '.mode=="live"' >/dev/null