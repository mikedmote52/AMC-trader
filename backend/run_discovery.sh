#!/usr/bin/env sh
set -euo pipefail
cd "$(dirname "$0")"   # -> backend/
export PYTHONPATH="$PWD:${PYTHONPATH:-}"
exec python -m src.jobs.discover