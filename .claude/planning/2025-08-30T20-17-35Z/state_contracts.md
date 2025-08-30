---
run_id: 2025-08-30T20-17-35Z
version: 1
---

# AMC-TRADER State Contracts

## PostgreSQL Tables

### `recommendations` table
**Written by**: Discovery job (`discover.py:466`)
**Read by**: Historical analysis, learning system
**Schema**:
```sql
CREATE TABLE recommendations (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    sentiment_score FLOAT,
    technical_score FLOAT,
    composite_score FLOAT,
    price DECIMAL(10,2),
    volume BIGINT,
    reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Redis State Management

### Discovery Pipeline Keys

#### `amc:discovery:contenders.latest`
**Written by**: Discovery job (`discover.py:610`, `discover.py:1236`)
**Read by**: FastAPI `/discovery/contenders` endpoint
**TTL**: 600 seconds (10 minutes)
**Data Format**:
```json
[
  {
    "symbol": "QUBT",
    "score": 0.847,
    "price": 3.95,
    "thesis": "EXTREME SQUEEZE ALERT...",
    "factors": {"vigl_similarity": 0.89},
    "squeeze_score": 0.87
  }
]
```

#### `amc:discovery:explain.latest` 
**Written by**: Discovery job (`discover.py:615`, `discover.py:1237`)
**Read by**: `/discovery/explain` endpoint for debugging
**TTL**: 600 seconds
**Data Format**:
```json
{
  "ts": "2025-08-30T20:15:00Z",
  "count": 7,
  "trace": {
    "stages": ["universe", "vigl_filter"],
    "counts_in": {"universe": 8400},
    "rejections": {"vigl_filter": {"low_vigl_similarity": 45}}
  }
}
```

#### `discovery_job_lock`
**Written by**: Discovery job coordination (`discover.py:1225`)
**Purpose**: Prevent overlapping discovery runs
**TTL**: 240 seconds (4 minutes)
**Data**: Simple lock value

## File System Caches

### Universe Data
**File**: `data/universe.txt`
**Updated by**: Manual process or configuration
**Read by**: Discovery job (`discover.py:337`)
**Format**: One symbol per line
**Purpose**: Define search universe for discovery

### Learning System Data
**Directory**: `data/learning/`
**Files**: Decision logs, outcome tracking, pattern performance
**Written by**: Learning system routes
**Read by**: Analytics, validation engine

## Cache Invalidation Strategy

### Discovery Data Lifecycle
1. **Generate**: Discovery job runs every 5 minutes
2. **Cache**: Results stored in Redis with 10-minute TTL
3. **Serve**: API endpoints serve cached data
4. **Expire**: Auto-expiry prevents stale data
5. **Refresh**: Next discovery run repopulates cache

### State Synchronization Points
- **Redis → Database**: Discovery results persisted for historical analysis
- **Alpaca → API**: Real-time position sync on demand
- **Frontend → Backend**: Polling maintains UI freshness

## Data Consistency Guarantees

### Discovery Pipeline
- **At-most-once**: Job locking prevents duplicate runs
- **Eventually consistent**: 10-minute cache TTL balances freshness vs performance
- **Fault tolerant**: Job failures don't corrupt state

### Portfolio Data
- **Source of truth**: Alpaca API is authoritative
- **Caching**: In-memory only, no persistence
- **Consistency**: Real-time sync on user interactions

### Trade Execution
- **Idempotent**: Duplicate trade submissions detected
- **Atomic**: Order success/failure is binary
- **Auditable**: All trades logged for reconciliation

## Memory Usage Patterns
- **Redis**: ~1MB for discovery results, minimal memory footprint
- **PostgreSQL**: Growing historical data, archived periodically
- **Frontend**: Stateless except for UI state, auto-refresh prevents staleness