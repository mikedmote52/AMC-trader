---
run_id: TEMPLATE
version: 1
---

# system_overview.md
Services and topology: discovery job cadence, Redis, FastAPI routes, React components, Alpaca sync.

# dataflow.md
End-to-end pipelines with producer → consumer arrows and data shapes.

# api_contracts.md
Route table with example JSON payloads that the UI expects.

# state_contracts.md
DB tables, Redis keys, TTLs, file caches; who writes and who reads.

# ui_contracts.md
Which component fetches which route, polling/SSE interval, and TS types.

# known_failure_modes.md
For each symptom, list likely causes and quick checks.