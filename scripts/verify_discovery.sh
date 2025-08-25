#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${BASE_URL:-https://amc-trader.onrender.com}"

echo "[verify] health:"
curl -fsSL "$BASE_URL/health" | jq .

echo "[verify] baseline recommendation count:"
c0=$(curl -fsSL "$BASE_URL/recommendations?limit=1000" | jq 'length')
echo "baseline_count=$c0"

echo "[verify] trigger discovery once (no need to wait for cron):"
scripts/run_discovery.sh >/dev/null || true

echo "[verify] fetch after trigger:"
sleep "${WAIT_SECONDS:-8}"
c1=$(curl -fsSL "$BASE_URL/recommendations?limit=1000" | jq 'length')
echo "after_count=$c1"

if [ "$c1" -gt "$c0" ]; then
  echo "[verify] OK: count increased"
  exit 0
else
  echo "[verify] No increase detected. If market is closed your job may no-op; try during market hours or inspect API logs."
  exit 1
fi