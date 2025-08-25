Shadow operations
1. Health: curl -s -w "\nHTTP %{http_code}\n" $API/health
2. Discovery: curl -s -X POST $API/discovery/run
3. Metrics: curl -s $API/metrics | head
4. Verify inserts: c0=$(curl -s $API/recommendations?limit=1000 | jq length); sleep 660; c1=$(curl -s $API/recommendations?limit=1000 | jq length); echo "$c0 -> $c1"

Risk guardrails for live flip
- Set LIVE_TRADING=0 until a full day of green runs.
- Configure MAX_POSITION_USD, MAX_PORTFOLIO_ALLOCATION_PCT, and KILL_SWITCH in Render before enabling live.
