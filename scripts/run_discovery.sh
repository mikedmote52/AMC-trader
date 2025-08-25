#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${BASE_URL:-https://amc-trader.onrender.com}"

# Try POST first, fall back to GET if the route is implemented that way
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/discovery/run")
if [ "$code" -ge 400 ]; then
  curl -fsSL "$BASE_URL/discovery/run" | jq .
else
  curl -fsSL -X POST "$BASE_URL/discovery/run" | jq .
fi