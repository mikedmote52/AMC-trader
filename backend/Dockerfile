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

# 3) Import-proof AFTER deps + code (both src.app and app.main entrypoints)
RUN python - <<'PY'
import importlib, os
print("IMPORT_PROOF_USING_PYTHONPATH", os.getenv("PYTHONPATH"))
# Test original src.app entrypoint
m = importlib.import_module("src.app")
assert hasattr(m, "app"), "src.app:app not found"
print("IMPORT_OK")
# Test new app.main compatibility entrypoint
app_main = importlib.import_module("app.main")
assert hasattr(app_main, "app"), "app.main:app not found"
print("IMPORT_OK_ALIAS")
PY

# 4) Prove select_candidates is available at build time
RUN python - <<'PY'
import importlib
mods = ("src.jobs.discovery","src.jobs.discover")
found = []
for mod in mods:
    try:
        m = importlib.import_module(mod)
        f = getattr(m, "select_candidates", None)
        if callable(f):
            found.append(mod)
    except Exception:
        pass
assert found, "No select_candidates in src.jobs.discovery or src.jobs.discover"
print("SELECTOR_OK:", ",".join(found))
PY

EXPOSE 8000
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]