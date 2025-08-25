# AMC Trading Intelligence System - Master Specification

## System Overview
Professional-grade stock discovery and portfolio management system combining AlphaStack's proven VIGL pattern detection with real-time portfolio analytics.

## Source of Truth: API + Ops Contract at v0.3

Health endpoints:
GET /health and GET /healthz return HTTP 200 with {"status":"healthy","components":{...}} when required env is present. They return HTTP 503 with {"status":"degraded","components":{"env":{"ok":false,"missing":[...]}}} when any required env is absent.

Discovery trigger:
GET or POST /discovery/run returns {"status":"queued","started":true,"cmd":"python -m src.jobs.discover"} and does not block the worker.

Recommendations:
GET /recommendations returns the live discovery feed ordered by most recent. The frontend polls ~every 15 seconds and must not rely on client mocks.

Trading:
Shadow by default with LIVE_TRADING=0. In live mode, requests to /trades/execute must be rejected with HTTP 400 when KILL_SWITCH=1.

Metrics:
GET /metrics exposes Prometheus text including amc_discovery_triggered_total and amc_discovery_errors_total.

Required environment variables on API and discovery cron:
DATABASE_URL, REDIS_URL, POLYGON_API_KEY, ALPACA_API_KEY, ALPACA_API_SECRET, ALPACA_BASE_URL, HTTP_TIMEOUT, HTTP_RETRIES, LIVE_TRADING. Optional guardrails: KILL_SWITCH, MAX_POSITION_USD, MAX_PORTFOLIO_ALLOCATION_PCT.

Operational procedure:
Discovery runs via a Docker cron on Render on schedule */5 * * * MON-FRI using the same Dockerfile as the API. Both services must share the same env set. Any PR that changes endpoints, response shapes, or required env must update this section and the QA smoke scripts in the same PR.

## Architecture Components

### 1. API Service (FastAPI/Python)
**Repository**: `api/`
**Port**: 3000
**Database**: PostgreSQL

#### Core Endpoints
```
GET  /health                 # System health (503 if any dependency down)
GET  /healthz                # Alternative health check
GET  /discovery/run          # Trigger VIGL discovery scan
GET  /recommendations        # Live discovery feed (most recent first)
POST /trades/execute         # Execute trade recommendations
GET  /metrics                # Prometheus metrics
GET  /holdings               # Alpaca cash and positions
```

#### FastAPI Application Requirements
- JSON logging throughout
- `/metrics` endpoint
- Strict environment validation on import (fail fast)

#### Dependencies (deps.py)
- HTTPx client
- SQLAlchemy session
- Redis client

#### Services Required
- market
- sentiment  
- scoring
- portfolio
- execution

### 2. Database Schema
```sql
-- Discovery Results
CREATE TABLE discovery_results (
    id SERIAL PRIMARY KEY,
    scan_id UUID NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    vigl_score DECIMAL(5,2),
    confidence_level VARCHAR(20),
    entry_price DECIMAL(10,2),
    target_price DECIMAL(10,2),
    stop_loss DECIMAL(10,2),
    volume_ratio DECIMAL(10,2),
    wolf_risk_score DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Portfolio Positions
CREATE TABLE portfolio_positions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    shares INTEGER NOT NULL,
    entry_price DECIMAL(10,2),
    current_price DECIMAL(10,2),
    unrealized_pnl DECIMAL(10,2),
    recommendation VARCHAR(20),
    vigl_pattern_match BOOLEAN,
    wolf_pattern_risk BOOLEAN,
    last_analysis TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Analysis History
CREATE TABLE analysis_history (
    id SERIAL PRIMARY KEY,
    position_id INTEGER REFERENCES portfolio_positions(id),
    analysis_type VARCHAR(50),
    confidence_score DECIMAL(5,2),
    recommendation VARCHAR(20),
    thesis TEXT,
    risk_assessment TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 3. Discovery Service (Python)
**Repository**: `discovery/`
**Core**: VIGL Pattern Detection (Protected Algorithm)

#### Integration Points
- Execute `VIGL_Discovery_Complete.py` via subprocess
- Parse JSON output and store in PostgreSQL
- Cache results in Redis with 5-minute TTL
- Never modify core algorithm logic

#### VIGL Pattern Thresholds
- Volume spike: 20.9x average
- Price range: $2.94-$4.66
- Momentum: >0.7
- WOLF risk: <0.6
- Confidence: >85%

### 4. Frontend UI (React/TypeScript)
**Repository**: `ui/`
**Port**: 3001

#### Dashboard Components
```
src/
├── components/
│   ├── Dashboard/
│   │   ├── DiscoveryPanel.tsx     # VIGL scan results
│   │   ├── PortfolioPanel.tsx     # Current positions
│   │   ├── MetricsPanel.tsx       # Performance metrics
│   │   └── AlertsPanel.tsx        # Trading alerts
│   ├── Discovery/
│   │   ├── ScanButton.tsx         # Trigger scan
│   │   ├── ResultsTable.tsx       # Display opportunities
│   │   └── PatternChart.tsx       # VIGL pattern visualization
│   └── Portfolio/
│       ├── PositionsTable.tsx     # Current holdings
│       ├── AnalysisCard.tsx       # Position analysis
│       └── TradeExecutor.tsx      # Execute recommendations
```

#### API Integration
```typescript
interface DiscoveryResult {
  symbol: string;
  viglScore: number;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  entryPrice: number;
  targetPrice: number;
  stopLoss: number;
  volumeRatio: number;
  wolfRiskScore: number;
}

interface PortfolioPosition {
  symbol: string;
  shares: number;
  entryPrice: number;
  currentPrice: number;
  unrealizedPnl: number;
  recommendation: 'BUY_MORE' | 'HOLD' | 'SELL';
  viglPatternMatch: boolean;
  wolfPatternRisk: boolean;
}
```

### 5. Infrastructure (Docker/Render)

#### Docker Compose
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: amc_trader
      POSTGRES_USER: trader
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  api:
    build: ./api
    ports:
      - "3000:3000"
    depends_on:
      - postgres
      - redis
    environment:
      - DATABASE_URL=postgresql://trader:secure_password@postgres:5432/amc_trader
      - REDIS_URL=redis://redis:6379

  ui:
    build: ./ui
    ports:
      - "3001:3001"
    depends_on:
      - api
    environment:
      - REACT_APP_API_URL=http://localhost:3000

volumes:
  postgres_data:
```

#### Render Configuration
```yaml
services:
  - type: web
    name: amc-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: amc-postgres
          property: connectionString
      - key: REDIS_URL
        fromService:
          name: amc-redis
          property: connectionString

  - type: web
    name: amc-ui
    env: static
    buildCommand: cd ui && npm install && npm run build
    staticPublishPath: ./ui/build
    routes:
      - type: rewrite
        source: /*
        destination: /index.html

  - type: redis
    name: amc-redis
    plan: starter

databases:
  - name: amc-postgres
    plan: starter
```

## Integration Requirements

### Critical Constraints
1. **AlphaStack Protection**: Never modify VIGL discovery algorithm
2. **Real Data Only**: No mock data in production pipeline
3. **System Independence**: VIGL and Portfolio systems remain isolated
4. **Interface Contracts**: All endpoints must match exact specifications
5. **Health Monitoring**: /health returns 503 if ANY dependency fails

### PR Acceptance Criteria
- [ ] Endpoints match specification exactly (names, methods, payloads)
- [ ] Database schema matches specification
- [ ] Environment variables match specification
- [ ] No modifications to protected algorithms
- [ ] Health check properly reports dependency status
- [ ] Frontend types match API response shapes
- [ ] Render deployment configs aligned

### Daily Workflow Integration
1. **08:00 EST**: Automated VIGL discovery scan (cron schedule: */5 * * * MON-FRI)
2. **09:30 EST**: Portfolio position analysis
3. **12:30 EST**: Mid-day position monitoring
4. **16:00 EST**: End-of-day comprehensive analysis
5. **18:00 EST**: After-hours risk assessment

### Testing Requirements
- API endpoints return correct status codes
- Discovery service executes real VIGL scanner
- Portfolio analyzer processes actual positions
- Frontend properly displays all data fields
- Health endpoint accurately reports system state
- Preflight script (`scripts/preflight.py`) exits non-zero on any failure

## Deployment Checklist

### Local Development
```bash
# Start infrastructure
docker-compose up -d postgres redis

# Run API
cd api && pip install -r requirements.txt && uvicorn main:app --reload

# Run UI
cd ui && npm install && npm start

# Test health
curl http://localhost:3000/health
```

### Production Deployment
1. Push to main branch
2. Render auto-deploys services
3. Verify health endpoints
4. Test discovery scan
5. Verify portfolio analysis
6. Check dashboard displays

## Success Metrics
- VIGL Pattern detection accuracy: >85%
- Portfolio analysis confidence: >80%
- System uptime: >99.5%
- Response time: <500ms p95
- Zero data loss or corruption

## Contact & Support
- GitHub Issues: Feature requests and bugs
- PR Reviews: Integration alignment checks
- Slack: #amc-trader-dev (urgent issues)