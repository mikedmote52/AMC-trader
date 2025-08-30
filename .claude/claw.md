## Workflow: AMC-TRADER Agent Factory

Intent
Audit the whole system, verify that discovery seeks explosive-growth stocks similar to prior winners, repair the UI data flow if needed, and surface actionable new tickers on the dashboard. Always leave a paper trail under a timestamped run folder.

Run bootstrap
At the start of a run, create `.claude/planning/<ISO_TIMESTAMP>/` and write `status.json` with `{ run_id, phase, artifacts }`. All artifacts for this run live inside that folder.

Context pack
Before planning, generate these files inside the run folder so every agent works from the same map:
- system_overview.md (services: discovery job, Redis, FastAPI, React, Alpaca sync)
- dataflow.md (Polygon → discovery → Redis → FastAPI → React; and Alpaca → holdings)
- api_contracts.md (FastAPI routes with request/response shapes used by the UI)
- state_contracts.md (Postgres tables, Redis keys, cache TTLs, file caches)
- ui_contracts.md (which component fetches what, polling or SSE, expected JSON shape)
- known_failure_modes.md (symptoms → likely causes → quick checks)

If any file is missing, synthesize it by reading the repo and running light introspection. Each file must begin with a YAML header `{ run_id, version }`.

Phase 0 — Clarify
Ask up to six targeted questions about today's goal. Save answers to `requirements.md` in the run folder. Update `status.json.phase = "clarified"`.

Phase 1 — Plan
Call agent: squeeze-planner.
Inputs: requirements.md + all context pack files + the June–July winners list (VIGL, CRWV, AEVA, etc.) and their trigger-time stats if available.
Output: `initial.md` in the run folder with sections:
- Context digest (prove you read the pack)
- Verification plan for discovery (signals, thresholds, regime assumptions)
- Hypotheses for "no new opportunities" (true market state vs pipeline bug)
- Tests for UI data flow (Redis → API → React)
- Acceptance criteria and rollback

Block until `initial.md` exists and its YAML header run_id matches.

Phase 2 — Parallel planning
Kick off three agents in parallel and wait for all outputs:
- prompt-architect → `prompts.md` (thesis/validator prompts and IO contracts)
- trading-tools-architect → `tools.md` (APIs, enrichers, schemas, retries, latency)
- dependency-planner → `dependencies.md` (packages, env, migrations, config)

Each file starts with a five-line "Context digest" citing concrete endpoints, Redis keys, or UI fetches.

Phase 3 — Implementation
Primary Claude edits code and config per planning files. Keep changes minimal and cohesive. Honor `tools.md` function signatures and `dependencies.md` steps. If you change an API response, update the corresponding React fetch and types.

Phase 4 — Validation
Call agent: amc-validation-engine (Validator).
Inputs: codebase, planning files, data/learning/*, calibration/active.json.
Outputs in the run folder:
- `validation_report.md` with unit tests on discovery, contract checks on FastAPI responses used by the UI, and a shadow backtest to ensure explosive-pattern search still fires under current regime.
- `calibration/proposed.json` if tier calibration drift exceeds thresholds from `initial.md`.

If validation fails twice, stop and summarize blockers with file paths and diffs.

Promotion
If `calibration/proposed.json` exists and acceptance criteria are met, write a short summary to `docs/calibration.md` and copy `proposed.json` to `calibration/active.json` with an `effective_at` timestamp.

Status file
Maintain `status.json` with the current phase and artifact readiness.