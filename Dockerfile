# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Print discovery build marker for Render logs
RUN echo "DOCKERFILE_MARKER: DISCOVERY_V1" && python -V

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Copy files needed for installation
COPY backend ./backend
COPY data ./data
COPY scripts ./scripts
COPY pyproject.toml* requirements*.txt* ./

# Install Python dependencies from backend/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install -r backend/requirements.txt && \
    python - <<'PY'
import pkgutil, importlib
print("HAS_ASYNCPG:", "asyncpg" in [m.name for m in pkgutil.iter_modules()])
import asyncpg, fastapi
print("ASYNC_PG_VERSION:", asyncpg.__version__)
print("FASTAPI_VERSION:", fastapi.__version__)
PY

# Verify app module exists for API service
RUN python - <<'PY'
try:
    import importlib
    m = importlib.import_module("backend.app.main")
    print("API_MODULE_OK: backend.app.main imported successfully")
except ImportError as e:
    print("API_MODULE_WARNING:", str(e))
    # Don't fail build since this might be discovery-only image
PY

EXPOSE 10000
# Default to API service, but can be overridden for discovery
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "10000"]
