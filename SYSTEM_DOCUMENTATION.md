# AMC-TRADER System Documentation

## Executive Summary

AMC-TRADER is a sophisticated automated trading system designed to discover high-potential stock opportunities and manage portfolio positions in real-time. The system combines market data analysis, sentiment scoring, technical indicators, and intelligent risk management to execute trades on the Alpaca trading platform.

## System Architecture Overview

### Tech Stack
- **Backend**: Python FastAPI, async architecture
- **Frontend**: React with TypeScript, Vite build system
- **Database**: PostgreSQL for persistence, Redis for caching
- **Trading Platform**: Alpaca Markets API (paper/live trading)
- **Market Data**: Polygon.io API for real-time and historical data
- **Deployment**: Render.com cloud platform
- **Monitoring**: Prometheus metrics, structured logging

### Core Components

```
AMC-TRADER/
├── backend/               # FastAPI server & trading logic
│   ├── src/
│   │   ├── app.py        # Main application entry
│   │   ├── routes/       # API endpoints
│   │   ├── services/     # Business logic & integrations
│   │   ├── jobs/         # Discovery pipeline
│   │   └── shared/       # Database, Redis, utilities
│   └── requirements.txt
├── frontend/             # React trading dashboard
│   ├── src/
│   │   ├── components/   # UI components
│   │   ├── hooks/        # Custom React hooks
│   │   └── lib/          # API client
│   └── package.json
└── data/
    └── universe.txt      # Stock symbols to monitor
```

## Key Features & Functionality

### 1. Stock Discovery Pipeline

The discovery system (`backend/src/jobs/discover.py`) runs every 5 minutes during market hours to identify trading opportunities:

**Process Flow:**
1. **Universe Loading**: Reads target symbols from `data/universe.txt`
2. **Market Data Collection**: Fetches real-time prices, volumes, and technical data from Polygon API
3. **Multi-Factor Scoring**: Evaluates each stock on 7 weighted factors:
   - Volume patterns (25% weight): Unusual volume spikes
   - Short interest (20%): High short interest opportunities
   - Catalyst events (20%): News, earnings, corporate actions
   - Sentiment (15%): Market sentiment analysis
   - Options flow (10%): Unusual options activity
   - Technical indicators (10%): RSI, moving averages
   - Sector momentum (5%): Relative sector performance

4. **Candidate Selection**: Filters and ranks stocks by composite score
5. **Thesis Generation**: Creates detailed trading thesis with entry/exit targets
6. **Redis Publishing**: Stores recommendations for API consumption

**Configuration (Environment Variables):**
```bash
AMC_PRICE_CAP=100         # Max stock price to consider
AMC_REL_VOL_MIN=3         # Min relative volume threshold
AMC_ATR_PCT_MIN=0.04      # Min volatility (ATR%)
AMC_FLOAT_MAX=50000000    # Max float for small caps
AMC_W_VOLUME=0.25         # Volume factor weight
AMC_W_SHORT=0.20          # Short interest weight
# ... additional weights
```

### 2. Trade Execution System

**Trade Flow (`backend/src/routes/trades.py`):**

1. **Request Validation**: Validates symbol, quantity, price limits
2. **Risk Guardrails**:
   - Price cap check ($100 default)
   - Position size limits
   - Kill switch override
   - Mode determination (live/shadow/auto)

3. **Order Types Supported**:
   - Market orders
   - Limit orders
   - Bracket orders (with stop loss & take profit)
   - Dollar-based sizing (notional trades)

4. **Position Management**:
   - TAKE_PROFITS: Sell 50% at gains
   - TRIM_POSITION: Reduce by 25%
   - EXIT_POSITION: Close entire position
   - ADD_POSITION: Dollar-cost averaging

**Trade Request Schema:**
```python
{
    "symbol": "AAPL",
    "action": "BUY",        # BUY/SELL
    "mode": "live",         # live/shadow/auto
    "qty": 10,              # Or use notional_usd
    "bracket": true,        # Enable stops
    "stop_loss_pct": 0.03,  # 3% stop loss
    "take_profit_pct": 0.10 # 10% take profit
}
```

### 3. Portfolio Management

**Holdings Analysis (`backend/src/routes/portfolio.py`):**
- Real-time P&L tracking
- Position-level thesis generation
- Intelligent recommendations based on performance
- Risk assessment per position
- Sector diversification monitoring

**Thesis Generator (`backend/src/services/thesis_generator.py`):**
- Analyzes 30-day price patterns
- Calculates volatility and momentum
- Generates context-aware recommendations
- Provides reasoning for learning system

### 4. Frontend Dashboard

**Main Components:**

1. **TopRecommendations**: Displays discovery pipeline output
   - Real-time score updates
   - One-click trade execution
   - Detailed thesis modal

2. **PortfolioTiles**: Current holdings view
   - Live P&L tracking
   - Position-specific actions
   - Risk indicators

3. **UpdatesPage**: Daily market updates
   - SMS alerts configuration
   - Market pulse summaries
   - Timeline of events

4. **TradeModal**: Order entry interface
   - Pre-filled from recommendations
   - Bracket order configuration
   - Risk calculations

### 5. External Integrations

**Alpaca Markets (`backend/src/services/broker_alpaca.py`):**
- Account management
- Order placement & tracking
- Position queries
- Real-time market data backup

**Polygon.io (`backend/src/services/polygon_client.py`):**
- Real-time quotes
- Historical bars
- Market status
- Corporate actions

**Redis Caching:**
- Discovery results: `amc:discovery:contenders.latest`
- Trace data: `amc:discovery:explain.latest`
- Job locks: `discovery_job_lock` (4-min TTL)

## API Endpoints

### Core Trading APIs

```
POST /trades/execute         # Execute a trade
POST /trades/position        # Position-specific trades
GET  /trades/position/{symbol}/preview  # Preview trades
GET  /defaults/{symbol}      # Get trade defaults
```

### Discovery APIs

```
GET /discovery/contenders    # Latest recommendations
GET /discovery/explain       # Pipeline trace data
GET /discovery/status        # Job status
GET /discovery/policy        # Active configuration
GET /discovery/audit         # Detailed scoring
```

### Portfolio APIs

```
GET /portfolio/holdings      # Current positions
GET /portfolio/summary       # Account overview
GET /portfolio/enhanced      # Positions with thesis
```

### System APIs

```
GET /health                  # Health check
GET /_whoami                 # Environment info
GET /_routes                 # Available routes
GET /metrics                 # Prometheus metrics
```

## Deployment & Operations

### Environment Configuration

Required environment variables:
```bash
# Database
DATABASE_URL=postgresql://user:pass@host/db
REDIS_URL=redis://host:6379

# Trading Platform
ALPACA_API_KEY=your_key
ALPACA_API_SECRET=your_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Market Data
POLYGON_API_KEY=your_polygon_key

# Trading Controls
LIVE_TRADING=0          # 0=paper, 1=live
KILL_SWITCH=1           # 0=enabled, 1=disabled
AMC_PRICE_CAP=100       # Max price per share
```

### Deployment on Render

The system auto-deploys from git commits:
1. Push to main branch
2. Render detects changes
3. Builds Docker container
4. Deploys with zero downtime
5. Runs health checks

### Monitoring & Observability

**Prometheus Metrics:**
- Trade submissions by mode
- Guardrail blocks by reason
- Discovery job executions
- API response times

**Structured Logging:**
- JSON formatted logs
- Request tracing
- Error aggregation
- Performance metrics

### Scheduled Jobs

**Discovery Pipeline (Cron):**
```cron
*/5 9-16 * * 1-5  python discover.py  # Every 5min during market hours
```

## Security & Risk Management

### Trading Safeguards

1. **Price Caps**: No trades above configured limit
2. **Position Limits**: Max dollar exposure per position
3. **Kill Switch**: Emergency trading halt
4. **Mode Control**: Shadow mode for testing
5. **Bracket Orders**: Automatic stop losses

### API Security

- CORS configured for frontend origins
- API key authentication for external services
- Rate limiting on public endpoints
- Input validation on all requests

## Development Workflow

### Local Development

```bash
# Setup
cp .env.example .env.local
pip install -r backend/requirements.txt
npm install --prefix frontend

# Start services
make redis          # Redis on :6379
make api           # API on :8000
npm run dev --prefix frontend  # UI on :5173

# Test discovery
make discovery-dry  # Dry run
make discovery-publish  # With Redis
```

### Testing Trade Execution

```bash
# Shadow trade (no execution)
curl -X POST http://localhost:8000/trades/execute \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL","action":"BUY","mode":"shadow","qty":1}'

# Live trade (if enabled)
curl -X POST http://localhost:8000/trades/execute \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL","action":"BUY","mode":"live","qty":1}'
```

## Data Flow Architecture

```mermaid
graph TD
    A[Polygon API] --> B[Discovery Pipeline]
    B --> C[Redis Cache]
    C --> D[FastAPI Backend]
    D --> E[React Frontend]
    D --> F[Alpaca API]
    F --> G[Trade Execution]
    D --> H[PostgreSQL]
    H --> I[Learning System]
    I --> B
```

## Key Algorithms

### Composite Scoring Formula

```python
score = (
    volume_score * 0.25 +
    short_score * 0.20 +
    catalyst_score * 0.20 +
    sentiment_score * 0.15 +
    options_score * 0.10 +
    technical_score * 0.10 +
    sector_score * 0.05
)
```

### Risk-Reward Calculation

```python
stop_price = current_price - (atr * 1.5)
target_price = current_price + (risk * r_multiple)
position_size = account_value * 0.02 / risk
```

## Performance Optimization

1. **Async Architecture**: All I/O operations are async
2. **Redis Caching**: 15-minute TTL on discovery results
3. **Connection Pooling**: Database and HTTP client pools
4. **Batch Processing**: Parallel API calls where possible
5. **Frontend Polling**: Intelligent intervals (15s-45s)

## Troubleshooting Guide

### Common Issues

**No recommendations showing:**
- Check Redis connection
- Verify discovery job is running
- Check Polygon API key/limits
- Review universe.txt symbols

**Trades not executing:**
- Verify Alpaca credentials
- Check LIVE_TRADING and KILL_SWITCH
- Review price caps and limits
- Check account buying power

**Database connection errors:**
- Verify DATABASE_URL format
- Check PostgreSQL is running
- Review connection pool settings

## Future Enhancements

1. **Machine Learning**: Incorporate ML models for prediction
2. **Options Trading**: Add options strategies
3. **WebSocket Feeds**: Real-time price streaming
4. **Mobile App**: Native iOS/Android apps
5. **Advanced Analytics**: Backtesting and performance analytics
6. **Social Features**: Follow top traders, share strategies

## Contact & Support

- **API Status**: https://amc-trader.onrender.com/health
- **Documentation**: This file and inline code comments
- **Issues**: Check logs in Render dashboard
- **Monitoring**: Prometheus metrics at /metrics

---

This documentation provides a comprehensive understanding of the AMC-TRADER system. The codebase is well-structured for expansion and follows modern async patterns for high-performance trading operations.