# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/backend

WORKDIR /app

# Marker to verify correct Dockerfile is used
RUN echo "DOCKERFILE_MARKER: BACKEND_V5_RENDER_FIX" && python -V

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# 1) Install deps FIRST and SHOW fastapi info
COPY backend/requirements.txt /tmp/requirements.txt
RUN echo "REQUIREMENTS_CONTENT:" && cat /tmp/requirements.txt && \
    python -m pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/requirements.txt && \
    echo "PIP_LIST_AFTER_INSTALL:" && pip list | grep -i fastapi && \
    python - <<'PY'
import fastapi, pkgutil
print("FASTAPI_PRESENT:", fastapi.__version__)
print("FASTAPI_IN_PKG_LIST:", "fastapi" in [m.name for m in pkgutil.iter_modules()])
PY

# 2) Copy backend code
COPY backend /app/backend

RUN python - <<'PY'
import importlib
mods = (
    "backend.src.app","app.main","backend.src.jobs.discover","backend.src.jobs.discovery",
    "src.app","src.jobs.discover","src.jobs.discovery"
)
ok, warn = [], []
for m in mods:
    try:
        importlib.import_module(m); ok.append(m)
    except Exception as e:
        warn.append((m, repr(e)))
print("PROOF_OK:", ",".join(ok))
for m,e in warn:
    print("PROOF_WARN:", m, e)

# Holdings field validation proof (warn-only)
try:
    from backend.src.routes.portfolio import build_holding_with_accurate_math
    sample_holding = {
        "symbol": "AAPL",
        "qty": 100,
        "avg_entry_price": 150.0,
        "last_price": 160.0
    }
    result = build_holding_with_accurate_math(sample_holding, {})
    required_fields = ["symbol", "qty", "avg_entry_price", "last_price", "market_value", "unrealized_pl", "unrealized_pl_pct", "suggestion"]
    missing = [f for f in required_fields if f not in result]
    present = [f for f in required_fields if f in result]
    print("HOLDINGS_PROOF_OK:", ",".join(present))
    if missing:
        print("HOLDINGS_PROOF_WARN: missing fields:", ",".join(missing))
except Exception as e:
    print("HOLDINGS_PROOF_WARN:", repr(e))
PY

EXPOSE 8000
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]