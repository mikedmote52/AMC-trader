# AMC Trading API Backend

FastAPI-based trading intelligence and execution API with JSON logging, metrics, and strict environment validation.

## Architecture

- **FastAPI** application with automatic OpenAPI docs
- **JSON structured logging** throughout
- **Prometheus metrics** at `/metrics`
- **Strict environment validation** (fail-fast on startup)
- **Service-oriented architecture** with dedicated modules
- **SQLAlchemy** with Alembic migrations
- **Redis** for caching
- **HTTPx** for external API calls

## Environment Variables

Required environment variables (application will fail to start if missing):

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/amc_trading

# Redis
REDIS_URL=redis://localhost:6379/0

# Alpaca Trading API
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET_KEY=your_alpaca_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Polygon Market Data API
POLYGON_API_KEY=your_polygon_key

# Optional
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## API Endpoints

### Core Routes

- `GET /` - API status and version
- `GET /health` - Health check (200 if all services healthy, 503 otherwise)
- `GET /metrics` - Prometheus metrics

### Trading Routes

- `GET /holdings` - Alpaca cash and positions
- `GET /recommendations` - Latest top 20 stock recommendations with features
- `POST /trades/execute` - Execute trades with `{"mode":"shadow"|"live"}`
- `POST /trades/custom` - Execute custom trade with specific parameters

### Health Check Response

Returns 200 only if all services are healthy:
```json
{
  "database": true,
  "redis": true,
  "polygon": true,
  "alpaca": true,
  "overall": true
}
```

Returns 503 with boolean status for each service if any fail.

## Installation & Local Development

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create `.env` file in the backend directory:

```bash
cp .env.example .env
# Edit .env with your API keys and database URL
```

### 3. Run Preflight Checks

```bash
python ../scripts/preflight.py
```

This script validates:
- All environment variables are set
- Python dependencies are installed
- Database connectivity
- Redis connectivity
- External API accessibility (Polygon, Alpaca)

**The script exits with non-zero code on any failure.**

### 4. Database Setup

```bash
# Create initial migration
alembic revision --autogenerate -m "Initial tables"

# Run migrations
alembic upgrade head
```

### 5. Start the API

```bash
# Development mode with auto-reload
python -m app.main

# Or using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Smoke Test Instructions

### Quick Smoke Test

1. **Run preflight checks**:
   ```bash
   python scripts/preflight.py
   ```
   Should exit with code 0 and show all ✅ PASS.

2. **Start the API**:
   ```bash
   cd backend && python -m app.main
   ```

3. **Test core endpoints**:
   ```bash
   # API status
   curl http://localhost:8000/
   
   # Health check (should return 200 if all services up)
   curl http://localhost:8000/health
   
   # Holdings from Alpaca
   curl http://localhost:8000/holdings
   
   # Top recommendations
   curl http://localhost:8000/recommendations
   
   # Shadow trade execution
   curl -X POST http://localhost:8000/trades/execute \
        -H "Content-Type: application/json" \
        -d '{"mode":"shadow"}'
   
   # Metrics endpoint
   curl http://localhost:8000/metrics
   ```

4. **Check API docs**:
   Open http://localhost:8000/docs for interactive Swagger UI.

### Expected Responses

- `/` returns API status with version 1.0.0
- `/health` returns 200 with all service booleans true (or 503 if any service down)
- `/holdings` returns Alpaca account info and positions
- `/recommendations` returns array of top 20 stocks with scores
- `/trades/execute` with shadow mode logs trade without execution
- `/metrics` returns Prometheus metrics in text format

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app with logging & metrics
│   ├── config.py            # Environment validation (fail-fast)
│   ├── deps.py              # HTTPx, SQLAlchemy, Redis clients
│   ├── models.py            # SQLAlchemy models
│   ├── routes/              # API route handlers
│   │   ├── health.py        # Health checks
│   │   ├── holdings.py      # Portfolio data
│   │   ├── recommendations.py # Stock recommendations
│   │   └── trades.py        # Trade execution
│   └── services/            # Business logic services
│       ├── market.py        # Market data (Polygon)
│       ├── sentiment.py     # Sentiment analysis
│       ├── scoring.py       # VIGL scoring algorithm
│       ├── portfolio.py     # Alpaca integration
│       └── execution.py     # Trade execution
├── alembic/                 # Database migrations
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Contract Compliance

✅ **FastAPI app** with JSON logging and `/metrics`  
✅ **Strict env validation** on import (fail fast)  
✅ **deps.py** with httpx client, SQLAlchemy session, Redis client  
✅ **Routes**: `/health`, `/holdings`, `/recommendations`, `/trades/execute`  
✅ **Services**: market, sentiment, scoring, portfolio, execution  
✅ **Data models** and Alembic migrations  
✅ **scripts/preflight.py** exits non-zero on any failure  
✅ **No mock data** - all real data from APIs  

## Logging

All logs are structured JSON format using `structlog`:
- Request/response logging with timing
- Service operation logging
- Error logging with context
- All logs include relevant metadata (symbol, trade_id, etc.)

## Metrics

Prometheus metrics available at `/metrics`:
- HTTP request counts by method/endpoint
- Request duration histograms
- Custom business metrics can be added to services