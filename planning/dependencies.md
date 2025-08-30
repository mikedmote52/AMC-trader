---
run_id: 2025-08-30T20-17-35Z
analysis_date: 2025-08-30
system: AMC-TRADER
focus: Squeeze Detection Enhancement & Monthly Profit Optimization Dependencies
---

# Dependencies for AMC-TRADER Squeeze Intelligence Enhancements

## Summary

This document outlines all technical dependencies required to implement the squeeze detection enhancements and monthly profit optimization features for AMC-TRADER. The enhancements focus on expanding the discovery universe from 14 to 1000+ symbols, improving pattern detection algorithms, and implementing advanced caching strategies while maintaining backward compatibility.

## Package Dependencies

### Backend Dependencies (Python)

**New Packages Required:**
- **scikit-learn** (>=1.3.0): Machine learning for pattern recognition and threshold optimization
  - Installation: `pip install scikit-learn>=1.3.0`
  - Purpose: Cosine similarity calculations, pattern clustering, dynamic threshold ML optimization
  - Used by: Pattern memory integration, learning engine, similarity matrix calculations

- **numpy** (>=1.24.0): Numerical computing for matrix operations and statistical analysis
  - Installation: `pip install numpy>=1.24.0` 
  - Purpose: Volume spike calculations, statistical analysis, pattern similarity scoring
  - Used by: SqueezeDetector, pattern memory system, performance analytics

- **pandas** (>=2.0.0): Data manipulation and analysis for historical pattern tracking
  - Installation: `pip install pandas>=2.0.0`
  - Purpose: Historical data analysis, pattern evolution tracking, performance reporting
  - Used by: Learning engine, pattern memory integration, analytics dashboards

- **aioredis** (>=2.0.0): Enhanced async Redis client for improved caching performance
  - Installation: `pip install aioredis>=2.0.0`
  - Purpose: Async Redis operations, pipeline support, better connection pooling
  - Migration: Gradual replacement of current `redis` package for performance-critical operations

- **apscheduler** (>=3.10.0): Advanced job scheduling for discovery pipeline optimization
  - Installation: `pip install apscheduler>=3.10.0`
  - Purpose: Market-aware job scheduling, dynamic frequency adjustment, job health monitoring
  - Used by: Enhanced discovery scheduler, market timing analysis

- **requests-cache** (>=1.0.0): HTTP request caching for external API optimization
  - Installation: `pip install requests-cache>=1.0.0`
  - Purpose: Cache Polygon API responses, reduce API calls, improve performance
  - Used by: Polygon client wrapper, rate limiting optimization

**Package Upgrades Required:**
- **psycopg[binary]**: Upgrade from 3.2.3 to >=3.2.6 for improved async performance
- **redis**: Keep current 5.0.8 but add aioredis alongside for gradual migration  
- **fastapi**: Upgrade from 0.115.2 to >=0.115.4 for latest async improvements
- **uvicorn[standard]**: Upgrade from 0.30.6 to >=0.30.8 for WebSocket support (future feature)

### Frontend Dependencies (React/TypeScript)

**New Packages Required:**
- **recharts** (>=2.8.0): Advanced charting library for performance analytics dashboard
  - Installation: `npm install recharts@>=2.8.0`
  - Purpose: Volume spike visualization, squeeze score charts, performance trending
  - Used by: PerformanceAnalyticsDashboard, SqueezeVisualization components

- **react-query** (@tanstack/react-query >=5.0.0): Advanced data fetching and caching
  - Installation: `npm install @tanstack/react-query@>=5.0.0`
  - Purpose: Intelligent API caching, real-time data synchronization, optimistic updates
  - Migration: Replace manual polling with smart caching layer

- **date-fns** (>=2.30.0): Date manipulation and formatting for analytics
  - Installation: `npm install date-fns@>=2.30.0`  
  - Purpose: Date range calculations, market hours detection, analytics time formatting
  - Used by: Analytics components, pattern evolution tracking

- **react-window** (>=1.8.8): Virtualized lists for large dataset rendering
  - Installation: `npm install react-window@>=1.8.8`
  - Purpose: Handle 1000+ symbol universe efficiently, virtual scrolling for performance
  - Used by: UniverseSelector, LargeSymbolList components

- **lodash** (>=4.17.21): Utility functions for data manipulation
  - Installation: `npm install lodash@>=4.17.21 @types/lodash`
  - Purpose: Debouncing, throttling, data transformation utilities
  - Used by: API polling optimization, data processing utilities

**Development Dependencies:**
- **@types/lodash** (>=4.14.200): TypeScript definitions for lodash
- **eslint-plugin-react-query** (>=5.0.0): ESLint rules for react-query best practices

## External API Requirements

### Polygon API Subscription Upgrade

**Current vs Required:**
- **Current**: Basic tier with limited calls/minute  
- **Required**: Advanced tier for 1000+ symbol universe support
- **Rate Limits**: Increase from 5 calls/second to 100 calls/second minimum
- **Endpoints Needed**:
  - `/v2/aggs/ticker/{symbol}/prev` (previous day data)
  - `/v1/open-close/{symbol}/{date}` (daily OHLCV)  
  - `/v2/aggs/ticker/{symbol}/range/1/minute/{from}/{to}` (intraday data)
  - `/v3/reference/tickers` (symbol universe expansion)

**API Quota Management:**
```python
POLYGON_RATE_LIMITS = {
    'calls_per_second': 100,
    'daily_quota': 100000,
    'universe_size': 1000,
    'priority_symbols': 50,  # Hot stocks get preferential treatment
    'batch_size': 50,        # Symbols per batch request
}
```

### Alpaca API Feature Requirements

**Enhanced Trading Features:**
- **Bracket Orders**: Stop-loss and take-profit automation
  - Required: Alpaca Plus or higher subscription
  - Endpoints: `/v2/orders` with bracket order parameters
  - Risk Management: Automatic position sizing based on volatility

- **Real-time Market Data**: 
  - Required: Alpaca Market Data Pro subscription  
  - WebSocket feeds for real-time price updates
  - Level 1 quotes for all 1000+ symbols

**Order Management Features:**
```python
ALPACA_FEATURES = {
    'bracket_orders': True,
    'trailing_stops': True,
    'extended_hours_trading': True,
    'fractional_shares': True,
    'real_time_data': True,
    'order_notifications': True
}
```

### Additional Market Data Sources

**Short Interest Data Provider:**
- **Service**: S3 Partners or similar for accurate short interest data
- **API Integration**: RESTful API for daily short interest updates
- **Cost**: ~$200-500/month for comprehensive short interest data
- **Alternative**: Free short interest scraping service (slower, less reliable)

## Infrastructure Requirements

### Memory and CPU Scaling

**Current vs Required Resources:**

**Backend Server:**
- **Current**: 512MB RAM, 0.5 vCPU (Render free tier)
- **Required**: 2GB RAM, 2 vCPU minimum for 1000+ symbol processing
- **Peak Usage**: 4GB RAM during market hours with full discovery pipeline
- **CPU Intensive Operations**: Pattern similarity calculations, ML model inference

**Memory Allocation:**
```python
MEMORY_REQUIREMENTS = {
    'redis_cache': '512MB',      # Expanded symbol universe caching
    'pattern_memory': '256MB',   # Historical pattern storage
    'discovery_pipeline': '512MB',  # Concurrent symbol processing
    'ml_operations': '256MB',    # Scikit-learn model operations
    'api_buffer': '256MB',       # HTTP request/response buffering
    'total_required': '1.75GB'   # Plus OS overhead = 2GB minimum
}
```

### Database Storage Requirements  

**PostgreSQL Storage Expansion:**
- **Current**: ~50MB for basic recommendations
- **Required**: 2-5GB for pattern memory system
- **Growth Rate**: ~100MB/month with active pattern tracking
- **Backup Requirements**: Daily automated backups with 30-day retention

**Table Size Estimates:**
```sql
-- Storage requirements by table
squeeze_patterns:      ~50MB (10K patterns)
pattern_evolution:     ~10MB (daily aggregations)  
pattern_similarity:    ~100MB (similarity matrix)
discovery_metrics:     ~20MB (job performance tracking)
squeeze_alerts:        ~25MB (alert history)
```

### Redis Memory Allocation

**Cache Strategy Expansion:**
- **Current**: 64MB Redis cache
- **Required**: 256MB Redis cache for expanded universe
- **Key Distribution**:
  - Symbol data: 128MB (1000+ symbols × ~128KB each)
  - Discovery results: 64MB (cached discovery runs)
  - Pattern cache: 32MB (squeeze detection results)
  - System metadata: 32MB (job status, health checks)

**Cache TTL Strategy:**
```python
CACHE_TTL_STRATEGY = {
    'hot_stocks': 30,        # 30s for >10x volume spikes
    'active_stocks': 120,    # 2min for >3x volume  
    'normal_stocks': 300,    # 5min for standard activity
    'quiet_stocks': 600,     # 10min for low activity
    'discovery_results': 300, # 5min for discovery job results
    'pattern_data': 1800,    # 30min for pattern calculations
}
```

### Deployment Infrastructure

**Production Environment (Render.com):**
- **Service Tier**: Professional ($25/month minimum)
- **Auto-scaling**: Enable for market hours traffic spikes
- **Health Checks**: Enhanced monitoring for discovery pipeline
- **Environment Variables**: Secure handling of API keys and feature flags

**Shadow Testing Infrastructure:**
- **Parallel Deployment**: V2 system running alongside V1
- **A/B Testing**: Traffic splitting between v1 and v2 endpoints
- **Rollback Capability**: Instant fallback to v1 on failure
- **Performance Monitoring**: Response time, error rate, cache hit rate tracking

## Configuration Changes

### Environment Variables

**Required New Variables:**
```bash
# Enhanced Discovery Configuration
AMC_UNIVERSE_SIZE=1000
AMC_DISCOVERY_FREQUENCY=180      # 3 minutes during market hours
AMC_PATTERN_MEMORY_ENABLED=true
AMC_LEARNING_ENGINE_ENABLED=true

# Pattern Detection Thresholds
AMC_ENHANCED_PRICE_MIN=0.50      # Minimum price for squeeze detection
AMC_ENHANCED_PRICE_MAX=50.0      # Maximum price for squeeze detection  
AMC_VOLUME_SPIKE_MIN=5.0         # Minimum volume spike (5x vs 2x current)
AMC_VOLUME_SPIKE_TARGET=20.9     # VIGL target volume spike
AMC_FLOAT_MAX=75000000           # Maximum float (75M vs 50M current)
AMC_SHORT_INTEREST_MIN=0.15      # Minimum short interest (15% vs 20% current)
AMC_MARKET_CAP_MAX=1000000000    # Maximum market cap ($1B)

# External API Configuration  
POLYGON_RATE_LIMIT=100           # Calls per second
POLYGON_BATCH_SIZE=50            # Symbols per batch request
POLYGON_PRIORITY_SYMBOLS=50      # Hot stocks processed first

# Redis Configuration
REDIS_MAX_MEMORY=256MB
REDIS_EVICTION_POLICY=allkeys-lru
REDIS_CONNECTION_POOL_SIZE=20

# Machine Learning Configuration
ML_MODEL_RETRAIN_FREQUENCY=daily
ML_PATTERN_SIMILARITY_THRESHOLD=0.85
ML_CONFIDENCE_THRESHOLD=0.75

# Performance Monitoring
ENABLE_PERFORMANCE_ANALYTICS=true
PERFORMANCE_RETENTION_DAYS=90
ALERT_THRESHOLD_API_ERRORS=0.05  # 5% error rate threshold
```

**Modified Existing Variables:**
```bash
# Updated thresholds (more aggressive for squeeze detection)
AMC_PRICE_CAP=50.0               # Increased from 100 to 50 for better focus
AMC_REL_VOL_MIN=5.0             # Increased from 3.0 to 5.0 for quality
AMC_FLOAT_MAX=75000000          # Increased from 50M to 75M for more candidates
AMC_SI_MIN=0.15                 # Decreased from 0.20 to 0.15 for more opportunities
```

### Feature Flags for Gradual Rollout

```python
FEATURE_FLAGS = {
    # Core enhancements
    'FF_ENHANCED_SQUEEZE': 'false',      # Enhanced squeeze detection algorithm
    'FF_EXPANDED_UNIVERSE': 'false',     # 1000+ symbol universe
    'FF_DYNAMIC_THRESHOLDS': 'false',    # ML-based threshold optimization
    'FF_PATTERN_MEMORY': 'false',        # Historical pattern learning
    
    # UI enhancements
    'FF_PERFORMANCE_DASHBOARD': 'false', # Performance analytics UI
    'FF_SQUEEZE_VISUALIZATION': 'false', # Advanced charting
    'FF_REAL_TIME_ALERTS': 'false',     # WebSocket-based alerts
    
    # Advanced features  
    'FF_SHADOW_TESTING': 'false',       # V2 parallel processing
    'FF_AUTO_TRADING': 'false',         # Automated trade execution
    'FF_RISK_MANAGEMENT': 'false',      # Advanced risk controls
    
    # Performance optimizations
    'FF_ASYNC_REDIS': 'false',          # Async Redis operations
    'FF_API_CACHING': 'false',          # Enhanced API response caching
    'FF_BATCH_PROCESSING': 'false',     # Batch API requests
}
```

### API Configuration Changes

**New Endpoint Additions:**
```python
# Enhanced discovery endpoints (non-breaking)
/discovery/v2/contenders          # Enhanced contenders with ML scoring
/discovery/enhanced-squeeze       # Advanced squeeze candidates
/discovery/pattern-memory        # Historical pattern analysis
/discovery/universe-health       # Universe scanning status
/discovery/performance-metrics   # Discovery pipeline analytics

# Analytics and monitoring endpoints
/analytics/performance          # Performance dashboard data
/analytics/pattern-evolution    # Pattern success over time
/analytics/system-health        # Comprehensive system status
/analytics/cache-statistics     # Redis cache performance

# Configuration and management
/config/feature-flags          # Current feature flag status
/config/thresholds            # Live threshold configuration
/admin/rollback               # Emergency rollback trigger
/admin/cache-warm             # Manual cache warming
```

### Build and Deployment Configuration

**Render.yaml Updates:**
```yaml
services:
  - type: web
    name: amc-trader-backend
    runtime: python
    plan: professional  # Upgraded from starter
    autoDeploy: false   # Manual deployments for safety
    buildCommand: |
      pip install -r requirements.txt
      python -m pytest backend/tests/
    startCommand: |
      python -m uvicorn backend.src.app:app --host 0.0.0.0 --port $PORT --workers 2
    envVars:
      - key: AMC_UNIVERSE_SIZE
        value: 1000
      - key: AMC_PATTERN_MEMORY_ENABLED  
        value: true
      - key: REDIS_MAX_MEMORY
        value: 256MB
    scaling:
      minInstances: 1
      maxInstances: 3  # Auto-scale during market hours
      targetCPUPercent: 70
      targetMemoryPercent: 80

databases:
  - name: amc-postgres
    plan: professional  # Upgraded storage and performance
    postgresMajorVersion: 15
```

**Docker Configuration (if applicable):**
```dockerfile
# Enhanced container with ML dependencies
FROM python:3.11-slim

# Install system dependencies for ML packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libatlas-base-dev \
    liblapack-dev \
    gfortran \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set memory limits for containers
ENV MALLOC_MMAP_THRESHOLD_=131072
ENV MALLOC_TRIM_THRESHOLD_=131072
ENV MALLOC_TOP_PAD_=131072
```

## Database Migrations

### New Schema Additions

**Migration Script: 001_pattern_memory_system.sql**
```sql
-- Execute the complete pattern_memory_schema.sql
-- This creates all tables for pattern tracking and learning
\i backend/src/shared/pattern_memory_schema.sql

-- Additional indexes for performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_squeeze_patterns_composite 
ON squeeze_patterns(pattern_score DESC, squeeze_score DESC, vigl_similarity DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_discovery_metrics_date 
ON discovery_metrics(run_timestamp DESC);
```

**Migration Script: 002_discovery_enhancements.sql**
```sql
-- Enhanced discovery tracking
CREATE TABLE IF NOT EXISTS discovery_runs (
    id SERIAL PRIMARY KEY,
    run_timestamp TIMESTAMP DEFAULT NOW(),
    universe_size INTEGER NOT NULL,
    candidates_found INTEGER NOT NULL,
    processing_time_ms INTEGER NOT NULL,
    success_rate FLOAT,
    error_count INTEGER DEFAULT 0,
    version VARCHAR(10) DEFAULT 'v1',
    config_snapshot JSONB,
    performance_metrics JSONB
);

-- Cache performance tracking
CREATE TABLE IF NOT EXISTS cache_metrics (
    id SERIAL PRIMARY KEY,
    metric_date DATE DEFAULT CURRENT_DATE,
    total_requests INTEGER DEFAULT 0,
    cache_hits INTEGER DEFAULT 0,
    cache_misses INTEGER DEFAULT 0,
    hit_rate FLOAT GENERATED ALWAYS AS (
        CASE WHEN total_requests > 0 
        THEN cache_hits::FLOAT / total_requests::FLOAT 
        ELSE 0 END
    ) STORED,
    avg_response_time_ms FLOAT,
    hot_stock_count INTEGER DEFAULT 0,
    
    UNIQUE(metric_date)
);
```

### Data Migration Requirements

**Historical Data Backfill:**
```sql
-- Backfill existing recommendations into pattern memory
INSERT INTO squeeze_patterns (
    symbol, pattern_date, volume_spike, entry_price, 
    pattern_score, squeeze_score, pattern_hash, notes
)
SELECT DISTINCT
    symbol,
    CURRENT_DATE,
    COALESCE(factors->>'volume_spike', '1.0')::FLOAT,
    price,
    score / 100.0,
    COALESCE(confidence, score / 100.0),
    md5(symbol || CURRENT_DATE::TEXT),
    'Migrated from legacy recommendations'
FROM historical_recommendations 
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
ON CONFLICT (symbol, pattern_date) DO NOTHING;
```

**Universe Expansion Migration:**
```python
# Migration script for expanding symbol universe
async def migrate_universe_expansion():
    """Migrate from 14-symbol to 1000+ symbol universe"""
    
    # Load new universe from external source
    new_symbols = await load_extended_universe()
    
    # Validate each symbol exists in market data
    validated_symbols = await validate_symbol_universe(new_symbols)
    
    # Update universe configuration
    await update_universe_file(validated_symbols)
    
    # Warm cache for high-priority symbols
    await warm_cache_for_priority_symbols(validated_symbols[:100])
    
    logger.info(f"Universe expanded from 14 to {len(validated_symbols)} symbols")
```

## Security and Configuration Management

### API Key Management

**Secure Environment Variable Handling:**
```python
# Enhanced API key configuration
API_KEY_CONFIG = {
    'polygon': {
        'key': os.getenv('POLYGON_API_KEY'),
        'rate_limit': int(os.getenv('POLYGON_RATE_LIMIT', '100')),
        'timeout': int(os.getenv('POLYGON_TIMEOUT', '30')),
        'retry_attempts': int(os.getenv('POLYGON_RETRY_ATTEMPTS', '3'))
    },
    'alpaca': {
        'key_id': os.getenv('ALPACA_API_KEY'),
        'secret_key': os.getenv('ALPACA_SECRET_KEY'),
        'base_url': os.getenv('ALPACA_BASE_URL'),
        'paper_trading': os.getenv('ALPACA_PAPER_TRADING', 'true').lower() == 'true'
    },
    'anthropic': {
        'key': os.getenv('ANTHROPIC_API_KEY'),
        'model': os.getenv('ANTHROPIC_MODEL', 'claude-3-sonnet-20241022'),
        'max_tokens': int(os.getenv('ANTHROPIC_MAX_TOKENS', '4000'))
    }
}
```

### Data Privacy and Compliance

**User Data Protection:**
- **No PII Storage**: System stores only market data and trading patterns
- **API Key Encryption**: All third-party API keys encrypted at rest
- **Audit Logging**: All trading decisions and API calls logged for compliance
- **Data Retention**: Automatic cleanup of old pattern data after 2 years

### Access Control Updates

**Role-Based Access Control:**
```python
ACCESS_CONTROL = {
    'admin': ['all_endpoints', 'rollback_capability', 'config_changes'],
    'trader': ['discovery_endpoints', 'trading_endpoints', 'analytics_readonly'],
    'readonly': ['discovery_readonly', 'analytics_readonly'],
    'monitor': ['health_checks', 'performance_metrics']
}
```

## Implementation Order and Dependencies

### Phase 1: Foundation (Week 1-2)
1. **Backend Package Installation**
   - Install scikit-learn, numpy, pandas for ML capabilities
   - Upgrade existing packages (psycopg, fastapi, redis)
   - Add aioredis for async operations

2. **Database Schema Migration**
   - Deploy pattern_memory_schema.sql
   - Create discovery_runs and cache_metrics tables
   - Set up performance indexes

3. **Environment Variable Configuration**
   - Add all new environment variables with default values
   - Configure feature flags (all disabled initially)
   - Update deployment configuration

### Phase 2: Core Enhancements (Week 3-4)
1. **Enhanced Pattern Detection**
   - Deploy improved SqueezeDetector with ML capabilities
   - Implement pattern memory integration
   - Add historical pattern validation

2. **Universe Expansion Infrastructure**
   - Upgrade Polygon API subscription
   - Implement batch processing for 1000+ symbols
   - Deploy enhanced caching strategy

3. **Shadow Testing Implementation**
   - Deploy V2 endpoints alongside V1
   - Implement A/B testing infrastructure
   - Add performance monitoring and comparison

### Phase 3: Frontend Integration (Week 5-6)
1. **React Package Installation**
   - Install recharts, react-query, date-fns
   - Add performance analytics components
   - Implement virtualized lists for large datasets

2. **API Integration**
   - Connect frontend to enhanced discovery endpoints
   - Implement real-time data synchronization
   - Add performance analytics dashboard

3. **User Experience Testing**
   - Test UI responsiveness with expanded universe
   - Validate real-time updates and caching
   - User acceptance testing for new features

### Phase 4: Production Rollout (Week 7-8)
1. **Gradual Feature Enablement**
   - Enable enhanced squeeze detection (FF_ENHANCED_SQUEEZE=true)
   - Enable expanded universe (FF_EXPANDED_UNIVERSE=true)  
   - Enable pattern memory (FF_PATTERN_MEMORY=true)

2. **Performance Optimization**
   - Enable async Redis operations
   - Activate API response caching
   - Optimize batch processing performance

3. **Monitoring and Alerting**
   - Deploy comprehensive system monitoring
   - Set up performance alerting thresholds
   - Implement automated rollback triggers

## Risk Assessment and Mitigation

### Technical Risks

**Performance Risks:**
- **Risk**: 1000+ symbol universe may overwhelm API rate limits
- **Mitigation**: Implement intelligent batching and priority queuing
- **Fallback**: Reduce universe size dynamically based on API performance

**Memory Usage Risks:**  
- **Risk**: Enhanced pattern detection may exceed memory limits
- **Mitigation**: Implement streaming processing and memory monitoring
- **Fallback**: Graceful degradation to simpler algorithms under memory pressure

**Data Consistency Risks:**
- **Risk**: Redis cache and PostgreSQL may become inconsistent
- **Mitigation**: Implement cache invalidation strategies and health checks
- **Fallback**: Automatic cache clearing and rebuild on inconsistency detection

### Security Considerations

**API Key Exposure:**
- **Risk**: New API integrations increase attack surface
- **Mitigation**: Encrypt all API keys, implement key rotation policies
- **Monitoring**: Alert on unusual API usage patterns

**Data Integrity:**
- **Risk**: Pattern data corruption could affect trading decisions
- **Mitigation**: Implement data validation and backup/restore procedures
- **Monitoring**: Automated data integrity checks daily

### Operational Risks

**Deployment Risks:**
- **Risk**: Complex migration may cause extended downtime
- **Mitigation**: Blue-green deployment with instant rollback capability
- **Testing**: Comprehensive staging environment testing before production

**Third-Party Dependencies:**
- **Risk**: External API failures could disable discovery system
- **Mitigation**: Implement circuit breakers and fallback data sources
- **Monitoring**: Real-time API health monitoring with automated failover

## Success Metrics and Monitoring

### Key Performance Indicators

**Discovery Performance:**
```python
SUCCESS_METRICS = {
    'daily_opportunities': {'target': 5, 'min': 3, 'max': 7},
    'average_confidence': {'target': 0.82, 'min': 0.75},
    'false_positive_rate': {'target': 0.18, 'max': 0.25},
    'api_response_time': {'target': 1000, 'max': 1500},  # milliseconds
    'cache_hit_rate': {'target': 0.85, 'min': 0.80},
    'discovery_frequency': {'target': 180, 'max': 300},  # seconds
}
```

**System Health Monitoring:**
```python
HEALTH_THRESHOLDS = {
    'memory_usage': {'warning': 0.75, 'critical': 0.90},
    'cpu_usage': {'warning': 0.70, 'critical': 0.85},
    'api_error_rate': {'warning': 0.02, 'critical': 0.05},
    'discovery_job_failures': {'warning': 2, 'critical': 5},
    'redis_connection_failures': {'warning': 1, 'critical': 3},
}
```

### Automated Monitoring Setup

**Alerting Configuration:**
```python
ALERT_RULES = {
    'critical': {
        'channels': ['email', 'slack'],
        'conditions': ['system_down', 'data_corruption', 'security_breach']
    },
    'warning': {
        'channels': ['slack'],  
        'conditions': ['performance_degradation', 'high_error_rate', 'cache_misses']
    },
    'info': {
        'channels': ['log_only'],
        'conditions': ['feature_flag_changes', 'successful_deployments']
    }
}
```

This comprehensive dependencies document ensures all technical requirements are addressed for successful implementation of the AMC-TRADER squeeze intelligence enhancements while maintaining system stability and providing clear rollback procedures.