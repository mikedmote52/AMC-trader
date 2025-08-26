# 🚦 Handoff: AMC-Trader — Shadow v0.3

## Live URLs
- API: `https://amc-trader.onrender.com`
- Frontend: `https://amc-frontend.onrender.com`

## Current State (v0.3-shadow)
- API hardened and deployed. Spec-compliant health at `/health` and `/healthz` returns 503 when required envs are missing, 200 when healthy. Discovery trigger at `/discovery/run`. Prometheus metrics at `/metrics`.
- Discovery cron Dockerized on Render using the same Dockerfile as the API. Schedule `*/5 * * * MON-FRI`. "Run now" works.
- Env hygiene done. Required keys present on API and cron; also declared in `render.yaml`.
- QA smoke against live is green. Endpoints verified: `/`, `/health`, `/recommendations`, `/holdings`, `/trades/execute` (shadow), `/docs`. Discovery confirms inserts during market hours.
- Observability in place. `/metrics` exposes counters `amc_discovery_triggered_total`, `amc_discovery_errors_total`.
- Release tagged: `v0.3-shadow`.
- Runbook added: `docs/RUNBOOK.md`.

## What changed since the original plan
- Health contract updated to a strict, ops-friendly shape with HTTP 503 on env gaps, plus duplicate `/healthz`.
- Discovery moved to Docker cron to avoid Python 3.13 build traps.
- Infra declares required env keys to prevent future drift.
- Metrics added for basic ops visibility.

## Known gaps / open threads
- UI lacks a prominent "Buy Now" surface; recommendations exist but are not foregrounded.
- Kill-switch and risk limits are not yet enforced server-side. Env knobs exist (`KILL_SWITCH`, `MAX_POSITION_USD`, `MAX_PORTFOLIO_ALLOCATION_PCT`) but the execute path does not read them yet.
- CI does not gate merges on a smoke job; Manager relies on agent checks.

## Next Actions (do in this order)
1) Frontend: add a "Buy Now" panel fed by `/recommendations`. Branch `feat/frontend-buy-now`. Create `frontend/src/components/BuyNow.tsx`, mount at top of dashboard, poll ~15s, filter for BUY with score ≥ 0.6 and risk ≤ 0.5. Build and deploy.
2) API: enforce guardrails on `/trades/execute`. Branch `feat/api-killswitch-and-limits`. Reject with 400 when `KILL_SWITCH=1` and `LIVE_TRADING=1`. Enforce `MAX_POSITION_USD` and `MAX_PORTFOLIO_ALLOCATION_PCT` with clear errors.
3) QA: acceptance for guardrails. Branch `qa/killswitch-check`. Expect 400 under killswitch and over-limit scenarios.
4) Infra/Manager: merge sequence API → QA → Frontend. Add a GitHub Action that runs `scripts/smoke.sh` against live and require it in branch protection. Update `docs/MASTER_PROMPT.md` contract.

## Quick verification
```bash
API=https://amc-trader.onrender.com
curl -s -w "\nHTTP %{http_code}\n" "$API/health"
curl -s -X POST "$API/discovery/run" | jq .
curl -s "$API/metrics" | head -20
c0=$(curl -s "$API/recommendations?limit=1000" | jq length); sleep 660; c1=$(curl -s "$API/recommendations?limit=1000" | jq length); echo "$c0 -> $c1"
```

## Environment baseline (API + cron)

```
DATABASE_URL, REDIS_URL
POLYGON_API_KEY
ALPACA_API_KEY, ALPACA_API_SECRET
ALPACA_BASE_URL=https://paper-api.alpaca.markets
HTTP_TIMEOUT=5, HTTP_RETRIES=2
LIVE_TRADING=0
KILL_SWITCH=1
MAX_POSITION_USD=<e.g., 100>
MAX_PORTFOLIO_ALLOCATION_PCT=<e.g., 15>
```

## Roles for Claude Code tabs

* Manager: gate merges in sequence; update `docs/MASTER_PROMPT.md` and `docs/HANDOFF.md`; add branch protections and CI requirement.
* API: implement kill-switch and risk-limit enforcement; redeploy; expose helpful 400s.
* Frontend: ship Buy Now panel; verify it reads live recommendations.
* QA: extend smoke to assert guardrails; keep a `/health` shape assertion.
* Infra: keep `render.yaml` authoritative; Docker cron and env sets must match API.

## Roadmap of progression

* v0.3 shadow (current): hardened health, Docker cron, QA green, metrics, runbook, env hygiene.
* v0.3.1: Buy Now shipped; guardrails enforced server-side; QA checks added; CI smoke required on merges.
* v0.4 shadow: one full market day of green runs with guardrails; add SLO monitors for `/health`, `/recommendations` freshness, and cron success.
* v0.5 live-ready: dry-run playbook executed; flip `LIVE_TRADING=1` with `KILL_SWITCH=1`, validate 400; then set `KILL_SWITCH=0` for limited live trades; monitor and roll back on any breach.
* v0.6+: strategy iteration, risk tuning, richer metrics and alerting.