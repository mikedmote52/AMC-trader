# Dependencies for AMC-TRADER Redis Caching and Background Worker System

## Summary
AMC-TRADER currently has production failures due to 5+ minute discovery times instead of sub-second cached responses. The system has Redis integration and background worker code in place, but requires proper initialization, connection handling, and deployment configuration to achieve the expected cached performance. This plan details all technical dependencies needed to implement a robust Redis caching system with background workers for continuous discovery cycles.

## Package Dependencies

### Backend (Python)

**Core Redis Dependencies:**
- **redis** (5.0.8): Async Redis client with connection pooling
  - Installation: Already in requirements.txt
  - Used by: Discovery worker, cache management, distributed locks
  - Configuration: Supports `redis://` and `rediss://` URLs with SSL

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
  - Used by: All Redis operations, worker cache storage
  - Validation: Must be accessible from application environment

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

### Cache Key Strategy

**Key Patterns:**
```
# Candidate caching
bms:candidates:all           # All discovered candidates
bms:candidates:trade_ready   # Action-filtered candidates
bms:candidates:monitor       # Monitor-only candidates

# Metadata caching
bms:meta                     # Discovery cycle metadata
bms:worker:health           # Worker health status
bms:universe:counts         # Universe statistics

# Symbol-specific caching
squeeze_cache:{symbol}       # Individual symbol analysis
market_metrics:{symbol}     # Market data for TTL calculation
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

## Implementation Order

### Phase 1: Redis Infrastructure Setup (Day 1)
1. **Add Redis service to render.yaml**
   - Configure standard Redis instance
   - Set up connection string environment variable
   - Deploy infrastructure changes

2. **Update Redis client configuration**
   - Implement async connection pooling
   - Add connection retry logic with exponential backoff
   - Configure SSL support for production

3. **Validate Redis connectivity**
   - Test Redis connection in health endpoint
   - Implement connection monitoring
   - Add Redis metrics to application logging

### Phase 2: Worker Process Enhancement (Day 2)
1. **Fix worker initialization in app startup**
   - Ensure background worker starts on application boot
   - Add proper error handling for worker failures
   - Implement graceful shutdown procedures

2. **Enhance worker health monitoring**
   - Add worker status to health endpoint
   - Implement cache age monitoring
   - Configure alerting for stale cache detection

3. **Optimize discovery cycle timing**
   - Fine-tune 60-second cycle intervals
   - Add jitter to prevent synchronized load spikes
   - Implement adaptive cycle timing based on market hours

### Phase 3: Cache Performance Optimization (Day 3)
1. **Implement dynamic TTL strategy**
   - Configure volume-based cache expiration
   - Add squeeze detection for hot stock caching
   - Optimize memory usage with intelligent eviction

2. **Add cache warming strategies**
   - Pre-populate cache for high-volume symbols
   - Implement predictive cache loading
   - Add cache hit/miss ratio monitoring

3. **Frontend integration testing**
   - Test sub-second response times for cached endpoints
   - Validate loading states and error handling
   - Implement retry mechanisms with exponential backoff

### Phase 4: Production Monitoring (Day 4)
1. **Deploy comprehensive monitoring**
   - Configure cache performance metrics
   - Add worker lifecycle event logging
   - Set up alerting for cache misses and worker failures

2. **Load testing and performance validation**
   - Test cache performance under high request volume
   - Validate worker stability during market hours
   - Measure end-to-end response times

3. **Documentation and runbook creation**
   - Create operational procedures for cache management
   - Document troubleshooting steps for common issues
   - Provide rollback procedures for production incidents

## Risk Assessment

### Compatibility Risks
- **Redis Version Compatibility**: Using redis-py 5.0.8 with async support
  - Mitigation: Stick to stable redis-py version, avoid bleeding-edge features
  - Rollback: Can disable caching and fallback to direct database queries

- **Connection Pool Exhaustion**: High concurrent load may exhaust Redis connections
  - Mitigation: Configure appropriate pool size, implement connection monitoring
  - Rollback: Graceful degradation to non-cached responses

### Performance Impacts
- **Memory Usage**: Redis caching will increase server memory requirements
  - Expected Impact: +100-200MB for full universe cache
  - Mitigation: Configure LRU eviction policy, monitor memory usage

- **Network Latency**: Additional network hop to Redis for cache operations
  - Expected Impact: +2-5ms per cached operation
  - Mitigation: Redis co-located with application server (same region)

### Security Considerations
- **Redis Authentication**: Production Redis instance requires authentication
  - Configuration: Use REDIS_URL with embedded credentials
  - Access Control: Limit Redis access to application services only

- **Cache Data Sensitivity**: Market data cached temporarily
  - Encryption: Use Redis SSL/TLS (rediss://) for data in transit
  - Data Retention: Configure TTL to minimize data exposure window

## Rollback Procedures

### Emergency Cache Disable
```bash
# 1. Disable worker via environment variable
curl -X POST "$API/admin/worker/stop"

# 2. Clear all cached data
curl -X POST "$API/admin/cache/flush"

# 3. Verify direct database fallback
curl -s "$API/discovery/contenders?force_refresh=true"
```

### Worker Restart Procedure
```bash
# 1. Check worker health
curl -s "$API/worker/health" | jq .

# 2. Restart worker if unhealthy
curl -X POST "$API/admin/worker/restart"

# 3. Monitor restart success
curl -s "$API/health" | jq '.components.worker'
```

### Redis Connection Recovery
```bash
# 1. Test Redis connectivity
curl -s "$API/health" | jq '.components.redis'

# 2. If Redis unavailable, verify fallback mode
curl -s "$API/discovery/contenders" | jq '.cached'

# 3. Monitor for automatic Redis reconnection
tail -f logs/app.log | grep -i redis
```

This comprehensive dependency plan addresses all critical aspects of implementing a production-ready Redis caching and background worker system for AMC-TRADER, with specific focus on resolving the current 5+ minute discovery time failures through sub-second cached responses.

**Key Implementation Benefits:**
1. **Performance**: 5+ minutes → <1 second cached response times
2. **Reliability**: Continuous background discovery with cache warmup
3. **Scalability**: Connection pooling and intelligent cache management
4. **Monitoring**: Comprehensive health checks and performance metrics
5. **Fault Tolerance**: Graceful degradation and automatic recovery

**Critical Success Factors:**
- Redis service properly configured in Render environment
- Background worker initialization on application startup
- Health monitoring with cache age validation
- Dynamic TTL strategy for hot stock optimization
- Comprehensive error handling and rollback procedures

**Expected Outcome**: Production AMC-TRADER system will deliver sub-second discovery responses through Redis caching, eliminating the current 5+ minute performance failures and providing real-time squeeze opportunity detection for users.
