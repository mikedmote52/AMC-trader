# Dependencies for AMC-TRADER Discovery System Overhaul

## Summary

This document outlines the comprehensive dependencies required for implementing a production-ready discovery system overhaul for AMC-TRADER. The enhancement introduces a robust background job processing system with Redis caching, non-blocking FastAPI endpoints, full universe coverage with local filtering, and proper separation of concerns between API routes and background workers.

**Key Improvements:**
- Redis Queue (RQ) background job processing with progress tracking
- Non-blocking API with 202 Accepted pattern for long-running discovery jobs
- Universe loader supporting 4,500+ stocks with comprehensive filtering
- Constants and cache contract system for single source of truth
- Enhanced worker process architecture for scalable background processing
- Price filtering (stocks under $100) with coverage tripwire (minimum 4,500 stocks)
- ETF/fund exclusion patterns and concurrent processing with rate limiting

## Package Dependencies

### Backend (Python)

**Core Redis Dependencies:**
- **redis** (5.0.8): Async Redis client with connection pooling
  - Installation: Already in requirements.txt
  - Used by: Discovery worker, cache management, distributed locks
  - Configuration: Supports `redis://` and `rediss://` URLs with SSL

- **rq** (1.15.1): Redis Queue for background job processing
  - Installation: Already in requirements.txt
  - Used by: Non-blocking discovery jobs, progress tracking, job status
  - Configuration: Queue management with job retry and failure handling

- **redis-py-cluster** (2.1.3): Redis cluster support (optional for scaling)
  - Installation: `pip install redis-py-cluster==2.1.3`
  - Used by: High-availability Redis deployments
  - Configuration: Only needed if using Redis Cluster

**Async Processing Dependencies:**
- **asyncio**: Built-in Python async library
  - Used by: Background worker scheduler, concurrent discovery tasks
  - Configuration: Already available in Python 3.7+

- **aioredis** (2.0.1): Alternative async Redis client (currently using redis-py async)
  - Installation: `pip install aioredis==2.0.1` (optional upgrade)
  - Used by: Enhanced async Redis operations
  - Configuration: Drop-in replacement for current redis.asyncio

**Worker Management Dependencies:**
- **psutil** (6.0.0): Process monitoring and system resource tracking
  - Installation: Already in requirements.txt
  - Used by: Worker health monitoring, memory usage tracking
  - Configuration: Cross-platform process utilities

- **tenacity** (9.0.0): Retry and circuit breaker patterns
  - Installation: Already in requirements.txt
  - Used by: Redis connection retries, API failure handling
  - Configuration: Exponential backoff for resilience

**Monitoring Dependencies:**
- **prometheus-client** (0.21.0): Metrics collection and export
  - Installation: Already in requirements.txt
  - Used by: Cache hit/miss rates, worker performance metrics
  - Configuration: Metrics endpoint at `/metrics`

- **structlog** (24.4.0): Structured logging for debugging
  - Installation: Already in requirements.txt
  - Used by: Worker lifecycle logging, cache operation tracing
  - Configuration: JSON formatted logs for production

## Environment Variables

### Required Production Variables

**Redis Configuration:**
- `REDIS_URL`: Redis connection string
  - Format: `redis://[username:password@]host:port[/database]` or `rediss://` for SSL
  - Example: `REDIS_URL=redis://localhost:6379/0`
  - Used by: All Redis operations, worker cache storage, RQ job processing
  - Validation: Must be accessible from application environment

**RQ Job Processing:**
- `RQ_DEFAULT_QUEUE`: Default queue name for discovery jobs
  - Format: String (default: "discovery")
  - Example: `RQ_DEFAULT_QUEUE=discovery`
  - Used by: Job enqueueing and worker process targeting

- `RQ_JOB_TIMEOUT`: Maximum job execution time in seconds
  - Format: Integer seconds (default: 1800)
  - Example: `RQ_JOB_TIMEOUT=1800`
  - Used by: RQ job timeout configuration for long-running discovery

- `RQ_RESULT_TTL`: Job result cache time-to-live in seconds
  - Format: Integer seconds (default: 3600)
  - Example: `RQ_RESULT_TTL=3600`
  - Used by: How long to keep job results for polling

**Universe & Filtering Configuration:**
- `UNIVERSE_SIZE_THRESHOLD`: Minimum universe size for coverage tripwire
  - Format: Integer (default: 4500)
  - Example: `UNIVERSE_SIZE_THRESHOLD=4500`
  - Used by: Universe validation and health checks

- `MAX_STOCK_PRICE`: Maximum price for stock filtering
  - Format: Float (default: 100.0)
  - Example: `MAX_STOCK_PRICE=100.0`
  - Used by: Price-based filtering to exclude high-priced stocks

- `MIN_MARKET_CAP`: Minimum market cap for stock inclusion
  - Format: Integer (default: 50000000)
  - Example: `MIN_MARKET_CAP=50000000`
  - Used by: Market cap filtering for liquidity requirements

**Worker Configuration:**
- `BMS_CYCLE_SECONDS`: Background discovery cycle interval
  - Format: Integer seconds (default: 60)
  - Example: `BMS_CYCLE_SECONDS=60`
  - Used by: Worker scheduler loop timing
  - Validation: Minimum 30 seconds, maximum 300 seconds

- `SCORING_STRATEGY`: Discovery scoring algorithm
  - Format: String enum ("legacy_v0" | "hybrid_v1")
  - Example: `SCORING_STRATEGY=hybrid_v1`
  - Used by: Strategy selection in discovery engine
  - Validation: Must match supported strategy types

**Performance Tuning:**
- `REDIS_CONNECTION_POOL_SIZE`: Max Redis connections
  - Format: Integer (default: 10)
  - Example: `REDIS_CONNECTION_POOL_SIZE=20`
  - Used by: Connection pool configuration
  - Validation: Should match expected concurrent operations

- `CACHE_TTL_SECONDS`: Default cache time-to-live
  - Format: Integer seconds (default: 120)
  - Example: `CACHE_TTL_SECONDS=120`
  - Used by: Standard cache expiration timing
  - Validation: Balance between freshness and performance

### Optional Configuration Variables

**Advanced Redis Settings:**
- `REDIS_SSL_CERT_REQS`: SSL certificate requirements ("none" | "optional" | "required")
  - Default: "none"
  - Used by: SSL/TLS Redis connections (Render Redis instances)

- `REDIS_SOCKET_KEEPALIVE`: Keep-alive for Redis connections
  - Format: Boolean (default: true)
  - Used by: Long-lived connection stability

**Worker Behavior:**
- `WORKER_MAX_CANDIDATES`: Maximum candidates to cache
  - Format: Integer (default: 100)
  - Example: `WORKER_MAX_CANDIDATES=200`
  - Used by: Memory usage control for large discovery sets

- `ENABLE_WORKER_AUTO_START`: Automatically start background worker
  - Format: Boolean (default: true)
  - Example: `ENABLE_WORKER_AUTO_START=true`
  - Used by: Production deployment worker initialization

## Redis Infrastructure Requirements

### Redis Instance Specifications

**Development Environment:**
- **Service**: Local Redis server or Docker container
- **Memory**: 256MB minimum, 1GB recommended
- **Persistence**: RDB snapshots enabled (save 900 1)
- **Configuration**: 
  ```redis
  maxmemory-policy allkeys-lru
  timeout 300
  tcp-keepalive 60
  ```

**Production Environment (Render):**
- **Service**: Render Redis (managed service)
- **Plan**: Standard ($7/month minimum for persistent storage)
- **Memory**: 256MB minimum, 1GB recommended for full universe caching
- **SSL**: Enabled (rediss:// protocol)
- **Backup**: Automated daily snapshots

**High Availability (Future):**
- **Service**: Redis Sentinel or Cluster setup
- **Nodes**: 3+ instances for fault tolerance
- **Failover**: Automatic primary election
- **Replication**: Master-slave with read replicas

### Redis Schema & Cache Contracts

**Core Discovery Cache Keys:**
```
# Primary discovery results (TTL: 5-10 minutes)
amc:discovery:v3:candidates:{strategy}  # Strategy-specific candidates
amc:discovery:v3:universe:latest        # Full universe with filters applied
amc:discovery:v3:metadata:{timestamp}   # Discovery run metadata

# RQ Job Management (TTL: 1 hour)
rq:job:{job_id}                        # RQ job status and progress
amc:jobs:discovery:active              # List of active job IDs
amc:jobs:discovery:results:{job_id}    # Job results cache

# Constants & Filters (TTL: 4 hours) 
amc:constants:filters                  # Price/volume/market cap filters
amc:constants:exclusions               # ETF/fund exclusion patterns
amc:universe:tripwire:status           # Coverage tripwire status

# Worker Health & Monitoring (TTL: 2 minutes)
amc:worker:health:last_heartbeat       # Worker process heartbeat
amc:worker:stats:performance           # Worker performance metrics
amc:discovery:stats:api_calls          # API usage statistics
```

**Discovery Results Schema:**
```json
{
  "candidates": [
    {
      "symbol": "TSLA", 
      "score": 85.7,
      "subscores": {
        "volume_momentum": 0.89,
        "squeeze": 0.82,
        "catalyst": 0.91,
        "options": 0.84,
        "technical": 0.78
      },
      "filters_passed": {
        "price_under_100": true,
        "market_cap_over_50m": true,
        "not_etf": true,
        "adequate_volume": true
      },
      "data_quality": {
        "price_age_minutes": 2,
        "volume_age_minutes": 1,
        "confidence": 0.96
      }
    }
  ],
  "meta": {
    "job_id": "discovery_20250909_101530_abc123",
    "strategy": "hybrid_v1",
    "universe_size": 4567,
    "candidates_found": 47,
    "execution_time_ms": 28500,
    "timestamp": "2025-09-09T10:15:30Z",
    "filters_applied": {
      "max_price": 100.0,
      "min_market_cap": 50000000,
      "excluded_types": ["ETF", "FUND", "WARRANT"]
    },
    "api_usage": {
      "polygon_calls": 4567,
      "rate_limit_hits": 0,
      "success_rate": 0.98
    }
  }
}
```

**RQ Job Status Schema:**
```json
{
  "job_id": "discovery_20250909_101530_abc123",
  "status": "in_progress",
  "progress": {
    "percentage": 45,
    "stage": "universe_loading",
    "current_step": "filtering_by_price",
    "symbols_processed": 2050,
    "symbols_remaining": 2517,
    "estimated_completion": "2025-09-09T10:25:00Z"
  },
  "timing": {
    "queued_at": "2025-09-09T10:00:00Z",
    "started_at": "2025-09-09T10:00:15Z",
    "stage_timings": {
      "universe_loading": 5200,
      "price_filtering": 850,
      "volume_analysis": 12300
    }
  },
  "partial_results": {
    "candidates_found_so_far": 23,
    "top_candidates": ["TSLA", "AMD", "NVDA"]
  },
  "errors": [],
  "worker_id": "worker_01_render_east"
}
```

**TTL Strategy:**
- **Hot stocks** (>10x volume): 30 seconds
- **Active stocks** (3-10x volume): 60 seconds
- **Normal stocks** (1.5-3x volume): 120 seconds
- **Quiet stocks** (<1.5x volume): 300 seconds
- **Metadata**: 120 seconds (aligned with discovery cycles)

### Connection Pool Configuration

**Pool Settings:**
```python
redis_pool_config = {
    'max_connections': 20,          # Handle concurrent API requests
    'socket_keepalive': True,       # Prevent connection drops
    'socket_keepalive_options': {
        1: 1,                       # TCP_KEEPIDLE
        2: 3,                       # TCP_KEEPINTVL  
        3: 5                        # TCP_KEEPCNT
    },
    'health_check_interval': 30,    # Connection health validation
    'retry_on_timeout': True,       # Automatic retry for timeouts
    'decode_responses': True        # UTF-8 string decoding
}
```

## Background Worker System Architecture

### Worker Process Design

**Scheduler Loop Structure:**
```python
class DiscoveryWorker:
    async def scheduler_loop(self):
        """Continuous 60-second discovery cycles"""
        while self.running:
            try:
                # 1. Run discovery (RealBMSEngine)
                candidates = await self.engine.discover_real_candidates(limit=100)
                
                # 2. Re-validate cached candidates
                candidates = await self._revalidate_candidates(candidates)
                
                # 3. Cache results with TTL
                await self._cache_results(candidates, metadata)
                
                # 4. Sleep until next cycle
                await asyncio.sleep(self.cycle_seconds)
                
            except Exception as e:
                logger.error(f"Cycle failed: {e}")
                await asyncio.sleep(min(self.cycle_seconds, 30))
```

**Process Lifecycle Management:**
- **Startup**: Initialize Redis connections, validate API keys
- **Health Checks**: Monitor Redis connectivity, cache freshness
- **Graceful Shutdown**: Complete current cycle, close connections
- **Error Recovery**: Automatic restart with exponential backoff

### Worker Initialization

**Application Startup Integration:**
```python
# In backend/src/app.py startup event
@app.on_event("startup")
async def startup_background_worker():
    try:
        polygon_key = os.getenv('POLYGON_API_KEY')
        redis_url = os.getenv('REDIS_URL')
        
        if polygon_key and redis_url:
            bms_engine = RealBMSEngine(polygon_key)
            await start_background_worker(bms_engine, redis_url)
            log.info("✅ Background discovery worker started")
        else:
            log.error("❌ Missing POLYGON_API_KEY or REDIS_URL - worker not started")
    except Exception as e:
        log.error(f"❌ Worker startup failed: {e}")
```

### Health Monitoring Endpoints

**Worker Status Monitoring:**
```python
@app.get("/worker/health")
async def worker_health():
    worker = get_worker()
    if not worker:
        return {"status": "not_running", "error": "Worker not initialized"}
    
    health = await worker.health_check()
    return {
        "status": "healthy" if health.get('redis_connected') else "degraded",
        "worker_running": health.get('worker_running'),
        "cache_age_seconds": health.get('cache_age_seconds'),
        "last_successful_cycle": health.get('last_cache_update')
    }
```

## Database Migration Requirements

### No Database Schema Changes Required
The current implementation uses Redis for caching and existing PostgreSQL for persistent data. No new database migrations are needed.

**Cache-Only Architecture Benefits:**
- **No Schema Changes**: All caching data is ephemeral and self-healing
- **No Data Migration**: Cache warmup happens automatically on first worker cycle
- **Rollback Safe**: Cache can be flushed without data loss
- **Version Independent**: Cache keys include strategy awareness for A/B testing

## API Route Patterns for Non-Blocking Discovery System

### 202 Accepted → 200 OK Polling Pattern

**Primary Discovery Endpoint:**
```
POST /discovery/v3/trigger
GET  /discovery/v3/candidates
GET  /discovery/v3/status/{job_id}
```

**Flow 1: Trigger New Discovery Job**
```bash
# 1. Trigger new discovery job
curl -X POST "$API/discovery/v3/trigger" \
  -H "Content-Type: application/json" \
  -d '{"strategy":"hybrid_v1","limit":100}'

# Response: 202 Accepted
{
  "status": "accepted",
  "job_id": "discovery_20250909_101530_abc123",
  "estimated_completion": "2025-09-09T10:25:00Z",
  "polling_url": "/discovery/v3/status/discovery_20250909_101530_abc123"
}

# 2. Poll job status
curl "$API/discovery/v3/status/discovery_20250909_101530_abc123"

# Response: 200 OK (in progress)
{
  "status": "in_progress", 
  "progress": 45,
  "stage": "universe_loading",
  "estimated_completion": "2025-09-09T10:25:00Z"
}

# 3. Poll until complete
curl "$API/discovery/v3/status/discovery_20250909_101530_abc123"

# Response: 200 OK (completed)
{
  "status": "completed",
  "progress": 100,
  "results_url": "/discovery/v3/candidates",
  "candidates_found": 47,
  "execution_time_ms": 28500
}
```

**Flow 2: Get Cached Candidates (Immediate Response)**
```bash
# Get cached results immediately
curl "$API/discovery/v3/candidates?strategy=hybrid_v1&limit=50"

# Response: 200 OK (cached)
{
  "status": "cached",
  "candidates": [...],
  "count": 47,
  "cache_age_seconds": 45,
  "from_job": "discovery_20250909_101530_abc123"
}

# OR Response: 204 No Content (no cache available)
# Client should trigger new discovery job
```

**Flow 3: Get Candidates with Auto-Trigger**
```bash
# Smart endpoint - returns cache or triggers job
curl "$API/discovery/v3/candidates?auto_trigger=true&strategy=hybrid_v1"

# If cached: 200 OK with data immediately
# If no cache: 202 Accepted with job_id for polling
```

### Detailed API Specification

**POST /discovery/v3/trigger**
```json
{
  "strategy": "hybrid_v1",        // optional, defaults to env SCORING_STRATEGY
  "limit": 100,                   // optional, defaults to 100
  "filters": {                    // optional overrides
    "max_price": 100.0,
    "min_market_cap": 50000000,
    "exclude_etfs": true
  },
  "force_refresh": false,         // optional, bypass cache
  "priority": "normal"            // optional: normal|high
}
```

**Response Codes:**
- `202 Accepted`: Job queued successfully
- `409 Conflict`: Similar job already running 
- `429 Too Many Requests`: Queue at capacity
- `500 Internal Server Error`: Job queue failure

**GET /discovery/v3/candidates**
```
Query Parameters:
- strategy: hybrid_v1|legacy_v0 (optional)
- limit: integer, max candidates (optional)
- auto_trigger: boolean, auto-start job if no cache (optional)
- format: json|minimal (optional)
```

**Response Codes:**
- `200 OK`: Cached results returned
- `202 Accepted`: No cache, job triggered (if auto_trigger=true)
- `204 No Content`: No cache available, no auto-trigger
- `400 Bad Request`: Invalid parameters

**GET /discovery/v3/status/{job_id}**
```
Response includes:
- status: queued|in_progress|completed|failed
- progress: 0-100 percentage
- stage: current processing stage
- estimated_completion: ISO timestamp
- partial_results: preview of candidates found so far
- errors: array of any errors encountered
```

**Response Codes:**
- `200 OK`: Job status returned
- `404 Not Found`: Job ID not found or expired
- `410 Gone`: Job completed and results expired

### Worker Health & Admin Endpoints

**GET /discovery/v3/worker/health**
```json
{
  "workers_active": 2,
  "queue_depth": 3,
  "last_job_completed": "2025-09-09T10:10:00Z",
  "cache_hit_rate": 0.85,
  "universe_last_updated": "2025-09-09T06:00:00Z",
  "redis_connected": true,
  "tripwire_status": "healthy"  // coverage >= 4500 stocks
}
```

**POST /discovery/v3/admin/cache/clear**
- Clear all discovery caches
- Requires admin authentication
- Returns: 200 OK with cache clear confirmation

**POST /discovery/v3/admin/queue/clear**
- Clear pending jobs from queue
- Requires admin authentication  
- Returns: 200 OK with cleared job count

## Configuration Changes

### Application Configuration Updates

**FastAPI Startup Configuration:**
```python
# backend/src/app.py modifications needed:

@app.on_event("startup") 
async def startup():
    # Existing health checks...
    
    # Initialize background worker
    await startup_background_worker()
    
    # Validate Redis connection
    await validate_redis_connectivity()

@app.on_event("shutdown")
async def shutdown():
    # Gracefully stop worker
    worker = get_worker()
    if worker:
        worker.stop()
        # Allow current cycle to complete
        await asyncio.sleep(5)
```

**Redis Client Configuration:**
```python
# backend/src/shared/redis_client.py updates needed:

async def get_async_redis_client():
    """Async Redis client with production-ready configuration"""
    return redis.from_url(
        os.getenv('REDIS_URL'),
        encoding='utf-8',
        decode_responses=True,
        max_connections=20,
        health_check_interval=30,
        socket_keepalive=True,
        retry_on_timeout=True,
        retry_on_error=[ConnectionError, TimeoutError]
    )
```

### Render.yaml Service Configuration

**Current Configuration Analysis:**
- ✅ Redis service should be added to render.yaml
- ✅ Web service health check path configured
- ✅ Environment variables properly mapped

**Required Additions to render.yaml:**
```yaml
services:
  # Add Redis service
  - type: redis
    name: amc-redis
    plan: standard
    region: oregon
    ipAllowList: []  # Allow from all Render services
    
  # Update existing web service
  - type: web
    name: amc-trader
    # ... existing configuration ...
    envVars:
      # Add Redis connection
      - key: REDIS_URL
        fromService:
          type: redis
          name: amc-redis
          property: connectionString
      
      # Worker configuration
      - key: BMS_CYCLE_SECONDS
        value: "60"
      - key: ENABLE_WORKER_AUTO_START
        value: "true"
      - key: CACHE_TTL_SECONDS
        value: "120"
```

### Health Check Endpoint Enhancement

**Enhanced Health Check Implementation:**
```python
@app.get("/health")
async def health_check():
    """Enhanced health check with Redis and worker status"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": {
            "tag": APP_TAG,
            "commit": APP_COMMIT,
            "build": APP_BUILD
        },
        "components": {
            "api": "healthy",
            "redis": "unknown",
            "worker": "unknown"
        }
    }
    
    # Check Redis connectivity
    try:
        redis_client = get_redis_client()
        await redis_client.ping()
        health_status["components"]["redis"] = "healthy"
    except Exception as e:
        health_status["components"]["redis"] = f"unhealthy: {e}"
        health_status["status"] = "degraded"
    
    # Check worker status
    try:
        worker = get_worker()
        if worker:
            worker_health = await worker.health_check()
            if worker_health.get('worker_running'):
                age = worker_health.get('cache_age_seconds', 0)
                if age < 180:  # Cache less than 3 minutes old
                    health_status["components"]["worker"] = "healthy"
                else:
                    health_status["components"]["worker"] = f"stale_cache_{age}s"
                    health_status["status"] = "degraded"
            else:
                health_status["components"]["worker"] = "not_running"
                health_status["status"] = "degraded"
        else:
            health_status["components"]["worker"] = "not_initialized"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["worker"] = f"error: {e}"
        health_status["status"] = "unhealthy"
    
    return health_status
```

## Deployment Architecture for Worker Service

### Render.com Service Configuration

**New Worker Service Required:**
```yaml
# Add to render.yaml
services:
  # Existing web service
  - type: web
    name: amc-trader-api
    # ... existing configuration ...
  
  # NEW: Background worker service
  - type: worker
    name: amc-trader-discovery-worker
    env: python
    repo: https://github.com/your-org/AMC-TRADER
    buildCommand: pip install -r backend/requirements.txt
    startCommand: cd backend && python -m rq worker discovery --url $REDIS_URL --verbose
    envVars:
      - key: REDIS_URL
        fromService:
          type: redis
          name: amc-redis
          property: connectionString
      - key: POLYGON_API_KEY
        sync: false
      - key: RQ_DEFAULT_QUEUE
        value: discovery
      - key: RQ_JOB_TIMEOUT
        value: "1800"
      - key: UNIVERSE_SIZE_THRESHOLD
        value: "4500"
      - key: MAX_STOCK_PRICE
        value: "100.0"
    scaling:
      minInstances: 1
      maxInstances: 3
```

**Resource Requirements:**
- **Worker Memory**: 1GB minimum (full universe processing)
- **Worker CPU**: 1 vCPU minimum (concurrent symbol analysis)
- **Redis Memory**: 256MB minimum for cache + job queue
- **Scaling**: Auto-scale workers based on queue depth

### Integration Points with Existing BMS Engine

**Current Integration:**
1. **BMS Engine Compatibility**: Existing `RealBMSEngine` becomes the core worker job function
2. **Strategy Resolver**: Existing strategy switching (`legacy_v0`, `hybrid_v1`) remains unchanged
3. **Calibration System**: Current `/calibration/active.json` tuning system stays functional
4. **Discovery Routes**: New routes coexist with existing discovery endpoints

**Migration Strategy:**
```python
# Phase 1: Dual-mode operation
# Existing routes continue to work
@router.get("/discovery/contenders")  # Legacy route - keep working
@router.get("/discovery/v3/candidates")  # New non-blocking route

# Phase 2: Gradual traffic migration
# Frontend can switch between modes via feature flag

# Phase 3: Legacy route deprecation (optional)
# After proven stability, legacy routes can be removed
```

## Implementation Order

### Phase 1: Foundation & Infrastructure (Week 1)

**Day 1-2: RQ Infrastructure Setup**
1. **Add RQ worker service to Render**
   - Configure worker service in render.yaml
   - Deploy Redis service if not already present
   - Set up environment variables for job processing
   
2. **Create constants management system**
   ```python
   # backend/src/discovery/constants.py
   class DiscoveryConstants:
       MAX_STOCK_PRICE = 100.0
       MIN_MARKET_CAP = 50_000_000
       UNIVERSE_SIZE_THRESHOLD = 4500
       ETF_EXCLUSION_PATTERNS = ["ETF", "FUND", "TRUST", ...]
   ```
   
3. **Implement universe loader with filters**
   ```python
   # backend/src/discovery/universe_loader.py
   async def load_filtered_universe() -> List[str]:
       # Load from Polygon API
       # Apply price filter (< $100)
       # Apply market cap filter (> $50M)  
       # Exclude ETFs/funds
       # Validate 4500+ stock threshold
   ```

**Day 3-4: Core Worker Implementation**
1. **Create RQ job worker function**
   ```python
   # backend/src/jobs/discovery_job.py
   def run_discovery_job(strategy, limit, filters):
       # Load universe with filters
       # Run BMS engine discovery
       # Cache results in Redis
       # Update job progress throughout
   ```

2. **Implement progress tracking system**
   ```python
   # Progress updates during job execution
   job.meta['progress'] = 25
   job.meta['stage'] = 'universe_loading'
   job.meta['symbols_processed'] = 1250
   job.save_meta()
   ```

### Phase 2: API Implementation (Week 2)

**Day 5-6: Non-blocking API Routes**
1. **POST /discovery/v3/trigger endpoint**
   ```python
   @router.post("/discovery/v3/trigger")
   async def trigger_discovery(request: DiscoveryRequest):
       # Enqueue RQ job
       # Return 202 with job_id
       # Set up job progress tracking
   ```

2. **GET /discovery/v3/status/{job_id} endpoint**
   ```python
   @router.get("/discovery/v3/status/{job_id}")
   async def get_job_status(job_id: str):
       # Check RQ job status
       # Return progress, stage, partial results
       # Handle completed/failed states
   ```

3. **GET /discovery/v3/candidates endpoint** 
   ```python
   @router.get("/discovery/v3/candidates")
   async def get_candidates(auto_trigger: bool = False):
       # Check cache first
       # If no cache and auto_trigger: start job, return 202
       # If cached: return 200 with data
       # If no cache and no auto_trigger: return 204
   ```

**Day 7-8: Cache Management**
1. **Implement cache contract system**
   ```python
   # backend/src/discovery/cache_manager.py
   class DiscoveryCacheManager:
       async def store_results(job_id, strategy, candidates)
       async def get_cached_results(strategy)
       async def invalidate_cache(strategy=None)
   ```

2. **Add worker health monitoring**
   ```python
   @router.get("/discovery/v3/worker/health")
   async def worker_health():
       # Check active workers
       # Check queue depth  
       # Check cache freshness
       # Check universe coverage tripwire
   ```

### Phase 3: Testing & Integration (Week 3)

**Day 9-10: Load Testing**
1. **Full universe processing test**
   ```bash
   # Test with complete 4500+ stock universe
   curl -X POST "$API/discovery/v3/trigger" \
     -d '{"strategy":"hybrid_v1","limit":100}'
   ```

2. **Concurrent job handling**
   ```bash
   # Test multiple simultaneous discovery requests
   # Validate queue management and worker scaling
   ```

**Day 11-12: Error Handling & Recovery**
1. **Job failure scenarios**
   - Polygon API rate limits
   - Redis connection failures  
   - Worker process crashes
   - Invalid universe data

2. **Cache invalidation strategies**
   - Stale data detection
   - Forced cache refresh
   - Partial result handling

### Phase 4: Production Deployment (Week 4)

**Day 13-14: Production Readiness**
1. **Deploy worker service**
   - Configure Render worker service
   - Validate environment variables
   - Test worker startup and health checks

2. **Monitor system performance**
   - Worker scaling under load
   - Cache hit/miss ratios
   - API response times
   - Universe coverage validation

**Day 15-16: Traffic Migration**
1. **Frontend integration**
   - Update frontend to use new discovery endpoints
   - Implement polling for job status
   - Add loading states for async operations

2. **Performance validation**
   - Measure end-to-end discovery times
   - Validate sub-30-second response times for cached results
   - Monitor system stability during market hours

## Risk Assessment

### Technical Risks

**RQ Job Queue Reliability**
- **Risk**: Job failures causing incomplete discovery results
- **Mitigation**: Implement job retry logic, dead letter queues, and graceful degradation
- **Rollback**: Disable async processing, fallback to synchronous discovery

**Redis Memory Pressure**
- **Risk**: Large universe datasets (4500+ stocks) exhausting Redis memory
- **Mitigation**: Implement LRU eviction, compress cached data, monitor memory usage
- **Impact**: 256MB-1GB Redis memory requirement for full system operation

**Worker Scaling Challenges**
- **Risk**: Single worker insufficient for market hours load, multiple workers causing race conditions
- **Mitigation**: Configure auto-scaling (1-3 workers), implement job deduplication
- **Monitoring**: Queue depth alerts, worker health checks every 30 seconds

### Integration Risks

**Existing BMS Engine Compatibility**
- **Risk**: Changes to existing discovery logic breaking current functionality  
- **Mitigation**: Dual-mode operation during migration, comprehensive testing
- **Rollback Strategy**: Feature flag to disable new system, revert to legacy routes

**API Breaking Changes**
- **Risk**: Frontend disruption from new API patterns
- **Mitigation**: New routes (/v3/) coexist with existing ones, gradual migration
- **Compatibility**: Legacy routes remain functional throughout transition

### Operational Risks

**Coverage Tripwire Failures**
- **Risk**: Universe drops below 4500 stocks, reducing discovery effectiveness
- **Mitigation**: Automated alerts, fallback to cached universe, manual intervention procedures
- **Monitoring**: Universe size validation in worker health checks

**Discovery Job Timeouts**
- **Risk**: Long-running jobs (30+ seconds) timing out under heavy load
- **Mitigation**: 30-minute job timeout, progress tracking, partial result caching
- **Performance Target**: 95% of jobs complete within 60 seconds

## Success Metrics & Validation

### Performance Benchmarks

**Primary Success Criteria:**
- **Discovery Response Time**: Sub-30 seconds for full universe scan (currently 5+ minutes)
- **Cache Hit Rate**: >80% for repeat requests within cache TTL period
- **Universe Coverage**: Maintain 4500+ stocks consistently (coverage tripwire)
- **API Availability**: 99%+ uptime during market hours (9:30 AM - 4:00 PM ET)

**Quality Metrics:**
- **Job Success Rate**: >95% of discovery jobs complete without errors
- **Data Freshness**: Cache age <10 minutes during active trading hours
- **Worker Health**: Workers respond to health checks within 5 seconds
- **Queue Processing**: Jobs processed within 2 minutes of enqueueing (95th percentile)

### Validation Tests

**Load Testing Scenarios:**
```bash
# 1. Full universe processing under load
curl -X POST "$API/discovery/v3/trigger" \
  -d '{"strategy":"hybrid_v1","limit":100}' &
# Repeat 10x simultaneously

# 2. Cache performance validation  
for i in {1..100}; do
  curl "$API/discovery/v3/candidates?strategy=hybrid_v1"
done

# 3. Worker failure recovery
# Kill worker process, validate auto-restart and job recovery
```

**Integration Test Matrix:**
- ✅ New API routes work with existing frontend
- ✅ Legacy discovery routes remain functional
- ✅ Strategy switching (hybrid_v1 ↔ legacy_v0) works across both systems
- ✅ Calibration system updates affect both discovery systems
- ✅ Authentication and rate limiting work with new endpoints

### Production Monitoring Dashboard

**Key Metrics to Track:**
```python
# Worker Performance
- discovery_jobs_completed_total
- discovery_job_duration_seconds (histogram)
- discovery_worker_health_status
- discovery_queue_depth

# Cache Performance  
- discovery_cache_hit_rate
- discovery_cache_size_bytes
- discovery_cache_age_seconds

# API Performance
- discovery_api_request_duration (by endpoint)
- discovery_api_error_rate
- discovery_concurrent_jobs

# Business Metrics
- discovery_universe_size_current
- discovery_candidates_found_per_run
- discovery_api_usage_by_strategy
```

**Alerting Thresholds:**
- 🚨 **Critical**: Universe size drops below 4000 stocks
- ⚠️ **Warning**: Cache hit rate below 70% for 10+ minutes
- 📊 **Info**: Queue depth exceeds 5 jobs (scale workers)
- 🔧 **Action**: Worker health check failures (restart required)

This comprehensive dependency plan ensures the AMC-TRADER discovery system can efficiently process the full universe of 4,500+ stocks while maintaining sub-30-second response times through intelligent caching, background job processing, and robust error handling. The phased implementation approach minimizes risk while delivering significant performance improvements over the current system.
