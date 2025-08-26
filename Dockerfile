# --- runtime image ---
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# install system deps if you have any (optional)
# RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# copy only what we need
COPY backend ./backend
COPY data ./data
COPY scripts ./scripts
COPY pyproject.toml* requirements*.txt* ./

# install python deps
RUN python -m pip install --upgrade pip && \
    ( [ -f requirements.txt ] && pip install -r requirements.txt || true ) && \
    ( [ -f pyproject.toml ] && pip install . || true )

# PROVE the app module exists at build-time; FAIL if not
RUN python - <<'PY'
import importlib
m = importlib.import_module("backend.src.app")
assert hasattr(m, "app"), "backend.src.app:app not found"
print("IMPORT_OK")
PY

EXPOSE 10000
CMD ["uvicorn", "backend.src.app:app", "--host", "0.0.0.0", "--port", "10000"]