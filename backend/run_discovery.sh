#!/usr/bin/env sh
set -euo pipefail
cd "$(dirname "$0")"     # -> /app/backend in container
export PYTHONPATH="$PWD:${PYTHONPATH:-}"
exec python -m src.jobs.discover_no_fallback