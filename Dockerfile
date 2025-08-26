# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/backend

WORKDIR /app

RUN echo "DOCKERFILE_MARKER: DISCOVERY_V1" && python -V

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/requirements.txt && \
    python - <<'PY'
import pkgutil, importlib
print("HAS_ASYNCPG:", "asyncpg" in [m.name for m in pkgutil.iter_modules()])
import asyncpg, fastapi
print("ASYNC_PG_VERSION:", asyncpg.__version__)
print("FASTAPI_VERSION:", fastapi.__version__)
PY

COPY backend /app/backend

# default command can be overridden by Render, but make this sensible for local test
CMD ["python", "-m", "src.jobs.discovery"]