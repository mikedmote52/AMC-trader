FROM python:3.11-slim

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy application code
COPY src/ ./src/
COPY ../scripts/preflight.py ./scripts/

# Run preflight checks on startup
# If preflight fails, container will exit
CMD ["sh", "-c", "python scripts/preflight.py && uvicorn src.app:app --host 0.0.0.0 --port 8000"]