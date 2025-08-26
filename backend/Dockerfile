# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/backend

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt && \
    pip show fastapi

COPY backend /app/backend

RUN python - <<'PY'
import importlib
m = importlib.import_module("src.app")
assert hasattr(m, "app"), "src.app:app not found"
print("IMPORT_OK")
PY

EXPOSE 8000
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]