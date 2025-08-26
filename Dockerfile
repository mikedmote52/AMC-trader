FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app

# 1) copy and install deps (cacheable)
COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt

# 2) copy code
COPY backend ./backend
COPY data ./data
COPY scripts ./scripts

# 3) prove the app module exists at build time
RUN python - <<'PY'
import importlib
m = importlib.import_module("backend.src.app")
assert hasattr(m, "app"), "backend.src.app:app not found"
print("IMPORT_OK")
PY

EXPOSE 10000
CMD ["uvicorn", "backend.src.app:app", "--host", "0.0.0.0", "--port", "10000"]