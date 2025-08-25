# API Backend Requirements

## Backend Implementation

### FastAPI Application
- JSON logging throughout
- `/metrics` endpoint
- Strict environment validation on import (fail fast)

### Dependencies (deps.py)
- HTTPx client
- SQLAlchemy session
- Redis client

### Routes Required
- `/health` - Returns 200 only if DB, Redis, Polygon, Alpaca are healthy; else 503 with booleans
- `/holdings` - Returns Alpaca cash and positions
- `/recommendations` - Returns latest top 20 with features
- `/trades/execute` - Accepts `{"mode":"shadow"|"live"}` and logs orders

### Services
- market
- sentiment  
- scoring
- portfolio
- execution

### Data Models & Migrations
- Alembic migrations setup
- Proper data models

### Preflight Script
- `scripts/preflight.py` that exits non-zero on any failure

### Contract Requirements
- No mock data anywhere
- Real data only
- Proper error handling
- JSON logging