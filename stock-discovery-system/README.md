# Stock Discovery System

Real-time stock discovery and portfolio management system with **ZERO mock data**.

## Features

- ✅ Live market data from Polygon API
- ✅ Real portfolio positions from Alpaca
- ✅ Sentiment analysis from Reddit/Twitter (when configured)
- ✅ Shadow trading mode for testing strategies
- ✅ Strict risk management and position limits
- ✅ Health checks with real dependency validation
- ❌ NO mock data, fixtures, or stubs

## Quick Start

### 1. Set Environment Variables

Copy `.env.example` to `.env` and add your real API keys:

```bash
cp .env.example .env
# Edit .env with your actual API keys
```

Required:
- `POLYGON_API_KEY` - Get from polygon.io
- `ALPACA_API_KEY` - Get from alpaca.markets
- `ALPACA_API_SECRET` - From Alpaca dashboard
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string

### 2. Install Dependencies

```bash
cd backend
pip install -e .
```

### 3. Run Preflight Checks

Verify all external services are accessible:

```bash
python scripts/preflight.py
```

This will check:
- Environment variables are set correctly
- Database connection works
- Redis is accessible
- Polygon API returns real data
- Alpaca account is accessible

### 4. Start the Server

```bash
cd backend
uvicorn src.app:app --reload
```

### 5. Verify Health

```bash
curl http://localhost:8000/health
```

Returns 200 only if ALL services are healthy.

## API Endpoints

- `GET /health` - System health with real dependency checks
- `GET /holdings` - Live positions from Alpaca
- `GET /recommendations` - Top stock recommendations
- `POST /trades/execute` - Execute trades (shadow or live mode)
- `GET /metrics` - Prometheus metrics

## Testing with Real Data

Run the test script to verify real API connections:

```bash
python test_local.py
```

This will:
1. Fetch real quotes from Polygon
2. Calculate actual momentum and volatility
3. Test all market data functions with live data

## Architecture

```
backend/
  src/
    app.py           # FastAPI application
    config.py        # Env validation (fails fast)
    deps.py          # Shared resources
    routes/          # API endpoints
      health.py      # Real health checks
      holdings.py    # Live Alpaca positions
    services/
      market.py      # Polygon real data only
    utils/
      logging.py     # Structured JSON logs
      errors.py      # Explicit error types
```

## No Mock Data Policy

This system **NEVER** uses mock data:
- All market prices come from Polygon API
- All positions come from Alpaca API
- All trades execute through Alpaca (in paper mode)
- If an API is unavailable, the system returns 503

## Deployment

Deploy to Render using the included `render.yaml`:

```bash
git push origin main
# Render auto-deploys on push
```

## Monitoring

- Structured logs in JSON format
- Prometheus metrics at `/metrics`
- Health endpoint for uptime monitoring
- Optional Slack notifications

## Safety Features

- Shadow mode for testing strategies
- Position size limits (2% max)
- Sector exposure limits (20% max)
- Minimum price/volume filters
- Daily trade count limits
- Pre-trade validation checks

## License

Proprietary - All rights reserved