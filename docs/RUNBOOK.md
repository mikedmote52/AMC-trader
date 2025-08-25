# AMC-Trader Shadow Runbook

Verify end-to-end:
1. BASE_URL=https://amc-trader.onrender.com ./scripts/verify_discovery.sh
2. Open the dashboard; recommendations should refresh every ~15s.

Manual discovery run (useful off the cron cadence):
- BASE_URL=https://amc-trader.onrender.com ./scripts/run_discovery.sh

Cut a shadow release tag after green checks:
- ./scripts/tag_shadow.sh v0.1-shadow

If cron was created natively and not with Docker, delete it. Only the Docker cron should exist.