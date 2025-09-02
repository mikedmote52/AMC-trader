---
run_id: 2025-09-02
analysis_date: 2025-09-02
system: AMC-TRADER
focus: Discovery Pipeline API Resilience & Fallback System
---

# Dependencies for AMC-TRADER Discovery Pipeline Resilience

> **URGENT**: This document addresses the critical issue where the discovery pipeline returns 0 results due to Polygon API grouped aggregates failures. Implementation focuses on immediate fixes and robust fallback mechanisms.

## Summary

This document outlines all technical dependencies required to fix the AMC-TRADER discovery pipeline API failure issues and implement robust fallback mechanisms. The current system fails when Polygon's grouped aggregates API returns 0 results, causing the entire discovery pipeline to find 0 stocks. This analysis provides comprehensive requirements for making the system resilient to API failures while maintaining discovery functionality.

## Root Cause Analysis

### Current Discovery Pipeline Flow
```mermaid
graph TD
    A[select_candidates()] --> B[Call Polygon grouped API]
    B --> C{API Returns Data?}
    C -->|Yes| D[Apply Bulk Filters]
    C -->|No| E[Use UNIVERSE_FALLBACK]
    E --> F[Continue with 58 symbols from universe.txt]
    D --> G[Filter & Score Candidates]
    F --> G
    G --> H[Return Top Candidates]
```

### Identified Issues
1. **Polygon API Dependency**: `select_candidates()` relies on `/v2/aggs/grouped/locale/us/market/stocks/{date}` 
2. **API Parameter Issues**: Missing required parameters or date format problems
3. **Insufficient Error Handling**: Generic exception catch doesn't distinguish API vs network issues
4. **Fallback Isolation**: UNIVERSE_FALLBACK and DiscoveryPipeline.read_universe() are separate systems
5. **No Circuit Breaker**: No prevention of repeated API calls when service is degraded

## Package Dependencies

### Backend Dependencies (Python)

**New Packages Required:**
- **tenacity** (>=8.2.0): Retry mechanism with exponential backoff for API calls
  - Installation: `pip install tenacity>=8.2.0`
  - Purpose: Intelligent retry logic, circuit breaker pattern, API failure recovery
  - Used by: Enhanced Polygon client wrapper, resilient API calls

- **circuit-breaker** (>=1.4.0): Circuit breaker pattern for external API protection
  - Installation: `pip install pybreaker>=1.0.0`
  - Purpose: Prevent cascade failures, protect against flaky APIs, automatic recovery
  - Used by: Polygon API wrapper, external service protection

- **httpx-cache** (>=0.13.0): HTTP caching middleware for httpx client
  - Installation: `pip install httpx-cache>=0.13.0`
  - Purpose: Cache successful API responses, reduce redundant calls, improve resilience
  - Used by: Polygon API client, market data caching

- **pydantic** (>=2.0.0): Enhanced data validation and settings management
  - Installation: `pip install pydantic>=2.0.0`
  - Purpose: Validate API responses, configuration management, error handling
  - Used by: API response validation, configuration classes

- **backoff** (>=2.2.0): Exponential backoff decorators for retry logic
  - Installation: `pip install backoff>=2.2.0`
  - Purpose: Smart retry strategies, jitter for API calls, failure recovery
  - Used by: API client methods, discovery pipeline resilience

- **aiofiles** (>=23.0.0): Async file operations for universe file management
  - Installation: `pip install aiofiles>=23.0.0`
  - Purpose: Non-blocking file operations, universe file updates, fallback data loading
  - Used by: Universe management, fallback data sources

**Package Upgrades Required:**
- **httpx**: Upgrade to >=0.27.0 for improved timeout handling and retry mechanisms
- **polygon-api-client**: Upgrade to >=1.14.0 for better error handling and rate limiting  
- **redis**: Keep current 5.0.8 but enhance with connection pooling
- **fastapi**: Upgrade from 0.115.2 to >=0.115.4 for improved error handling

### Frontend Dependencies (React/TypeScript)

**New Packages Required:**
- **react-error-boundary** (>=4.0.0): Error boundary components for API failure handling
  - Installation: `npm install react-error-boundary@>=4.0.0`
  - Purpose: Graceful error handling, fallback UI states, user-friendly error messages
  - Used by: Discovery components, API error boundaries

- **@tanstack/react-query** (>=5.0.0): Advanced data fetching with built-in retry logic
  - Installation: `npm install @tanstack/react-query@>=5.0.0`
  - Purpose: Automatic retry, stale-while-revalidate caching, API failure recovery
  - Migration: Replace manual polling with resilient data fetching

- **react-toast-notifications** (>=2.6.0): User-friendly error and status notifications
  - Installation: `npm install react-toast-notifications@>=2.6.0`
  - Purpose: Inform users of API issues, fallback mode activation, system status
  - Used by: Discovery status notifications, error feedback

**Development Dependencies:**
- **@types/react-error-boundary** (>=4.0.0): TypeScript definitions for error boundaries

## External API Requirements

### Polygon API Configuration Issues

**Root Cause Analysis:**
- **Current Issue**: `/v2/aggs/grouped/locale/us/market/stocks/{date}` returns 0 results
- **Probable Causes**:
  1. **Date Format**: Using weekends/holidays vs trading days
  2. **API Subscription**: Free tier may not support grouped aggregates
  3. **Rate Limiting**: Hitting rate limits causing empty responses
  4. **Parameter Missing**: Missing required query parameters

**Required API Endpoints (in priority order):**
- **Primary**: `/v2/aggs/ticker/{symbol}/prev` (individual symbol previous day data)
- **Secondary**: `/v1/open-close/{symbol}/{date}` (individual symbol daily OHLCV)
- **Fallback**: `/v3/reference/tickers` (symbol metadata and basic info)
- **Current Problematic**: `/v2/aggs/grouped/locale/us/market/stocks/{date}` (bulk market data)

**API Configuration Fixes:**
```python
POLYGON_API_CONFIG = {
    # Resilient endpoint strategy
    'primary_endpoint': '/v2/aggs/ticker/{symbol}/prev',  # Individual symbol calls
    'fallback_endpoint': '/v1/open-close/{symbol}/{date}',  # Backup individual calls
    'problematic_endpoint': '/v2/aggs/grouped/locale/us/market/stocks/{date}',  # Currently failing
    
    # Rate limiting and retry
    'calls_per_second': 5,    # Conservative for free tier
    'max_retries': 3,         # Retry failed calls
    'backoff_factor': 2,      # Exponential backoff
    'timeout_seconds': 30,    # Request timeout
    
    # Date handling
    'use_previous_trading_day': True,  # Always use valid trading days
    'weekend_handling': 'skip_to_friday',  # Handle weekend dates
    'holiday_calendar': 'NYSE',  # Use market holiday calendar
}
```

### Alternative Data Sources (Fallback Strategy)

**Primary Fallback: Yahoo Finance**
- **Package**: `yfinance` (>=0.2.28)
- **Endpoints**: Historical data, current prices, basic fundamentals
- **Rate Limits**: More lenient than Polygon for basic data
- **Usage**: Fallback when Polygon API fails

**Secondary Fallback: Alpha Vantage**
- **Package**: `alpha-vantage` (>=2.3.1)
- **Endpoints**: Daily prices, technical indicators
- **Rate Limits**: 500 calls/day free tier
- **Usage**: Emergency fallback for critical symbols

**Local Data Cache (Tertiary Fallback)**:
```python
FALLBACK_DATA_SOURCES = {
    'priority_1': 'polygon_api',        # Primary source
    'priority_2': 'yahoo_finance',      # First fallback
    'priority_3': 'alpha_vantage',      # Second fallback 
    'priority_4': 'cached_data',        # Local cache
    'priority_5': 'universe_file',      # Static symbol list
}
```

### API Resilience Pattern Implementation

**Circuit Breaker Configuration:**
```python
CIRCUIT_BREAKER_CONFIG = {
    'failure_threshold': 5,      # Open circuit after 5 failures
    'recovery_timeout': 60,      # Wait 60s before retry
    'expected_exception': requests.exceptions.RequestException,
    'fallback_function': 'use_fallback_data_source',
}
```

**Retry Strategy:**
```python
RETRY_CONFIG = {
    'max_attempts': 3,
    'backoff_strategy': 'exponential',
    'base_delay': 1.0,          # Start with 1 second
    'max_delay': 30.0,          # Cap at 30 seconds
    'jitter': True,             # Add randomization
}
```

## Infrastructure Requirements

### API Resilience Infrastructure

**Current Issues:**
- **Single Point of Failure**: Discovery pipeline depends entirely on Polygon API
- **No Fallback Strategy**: When API fails, entire system returns 0 results
- **No Circuit Protection**: Repeated calls to failing API waste resources
- **Poor Error Distinction**: Generic exception handling doesn't identify specific failures

**Required Resilience Features:**
- **Multiple Data Sources**: Primary/secondary/tertiary fallback chain
- **Circuit Breaker**: Automatic API failure detection and bypass
- **Smart Retry Logic**: Exponential backoff with jitter
- **Response Caching**: Store successful API responses for reuse
- **Graceful Degradation**: System continues with reduced functionality

**Memory Allocation for Resilience:**
```python
MEMORY_REQUIREMENTS = {
    'api_response_cache': '256MB',   # Cache successful API calls
    'fallback_data_store': '128MB',  # Local symbol data cache
    'circuit_breaker_state': '32MB', # Track API health status
    'retry_queue': '64MB',           # Failed request retry buffer
    'discovery_pipeline': '256MB',   # Core discovery processing
    'total_required': '736MB'        # Conservative estimate
}
```

### Database Storage Requirements  

**PostgreSQL Storage for API Resilience:**
- **Current**: ~50MB for basic recommendations
- **Required**: ~200MB for API caching and fallback data
- **API Cache Tables**: Store successful API responses (50MB)
- **Fallback Symbol Data**: Local symbol metadata (25MB)
- **Error Tracking**: API failure logs and metrics (25MB)
- **Backup Requirements**: Daily automated backups with 7-day retention

**Table Size Estimates:**
```sql
-- Storage requirements by table
api_response_cache:    ~50MB (cached successful API calls)
api_failure_log:       ~25MB (track API errors and patterns)
fallback_symbol_data:  ~25MB (local symbol metadata)
discovery_metrics:     ~20MB (pipeline performance tracking)
system_health_log:     ~10MB (overall system status)
```

### Redis Memory Allocation

**Cache Strategy for API Resilience:**
- **Current**: 64MB Redis cache
- **Required**: 128MB Redis cache for API response caching
- **Key Distribution**:
  - API Response Cache: 64MB (successful API calls with TTL)
  - Circuit Breaker State: 16MB (API health status)
  - Discovery Results: 32MB (processed discovery data)
  - System Health: 16MB (job status, error counters)

**Cache TTL Strategy:**
```python
CACHE_TTL_STRATEGY = {
    'api_success_response': 300,     # 5min for successful API calls
    'api_failure_state': 60,         # 1min for API failure status
    'discovery_results': 300,        # 5min for discovery results
    'circuit_breaker_state': 120,    # 2min for circuit breaker status
    'symbol_metadata': 3600,         # 1hour for static symbol data
    'fallback_data': 1800,           # 30min for fallback data sources
}
```

### Deployment Infrastructure

**Production Environment (Render.com):**
- **Service Tier**: Keep current tier, optimize for reliability over performance
- **Health Checks**: Enhanced API failure detection and automatic restart
- **Environment Variables**: Multiple API keys for fallback sources
- **Monitoring**: API response times, error rates, fallback activation

**API Resilience Testing:**
- **Chaos Engineering**: Intentionally fail APIs to test fallback mechanisms
- **Load Testing**: Simulate API rate limit scenarios
- **Fallback Validation**: Ensure fallback data sources work correctly
- **Recovery Testing**: Verify system recovery when APIs come back online

## Configuration Changes

### Environment Variables

**Required New Variables:**
```bash
# API Resilience Configuration
API_CIRCUIT_BREAKER_ENABLED=true
API_MAX_RETRIES=3
API_RETRY_BACKOFF_FACTOR=2
API_TIMEOUT_SECONDS=30
API_CACHE_TTL_SECONDS=300

# Fallback Data Sources
POLYGON_API_KEY=your_polygon_key          # Primary API
YAHOO_FINANCE_ENABLED=true                # First fallback
ALPHA_VANTAGE_API_KEY=your_av_key        # Second fallback
ALPHA_VANTAGE_ENABLED=true                # Enable AV fallback
FALLBACK_TO_UNIVERSE_FILE=true           # Final fallback

# External API Configuration  
POLYGON_RATE_LIMIT=5             # Conservative calls per second for free tier
POLYGON_USE_INDIVIDUAL_CALLS=true # Use /v2/aggs/ticker/{symbol}/prev instead of grouped
POLYGON_SKIP_GROUPED_API=true    # Skip problematic grouped aggregates API
POLYGON_VALIDATE_TRADING_DAY=true # Ensure date is a valid trading day

# Redis Configuration for API Caching
REDIS_MAX_MEMORY=128MB
REDIS_EVICTION_POLICY=allkeys-lru
REDIS_CONNECTION_POOL_SIZE=10
REDIS_API_CACHE_PREFIX=api_cache
REDIS_CIRCUIT_BREAKER_PREFIX=cb_state

# Discovery Pipeline Resilience
DISCOVERY_FALLBACK_ENABLED=true
DISCOVERY_MIN_SYMBOLS_REQUIRED=20  # Minimum symbols to proceed
DISCOVERY_MAX_API_FAILURES=3       # Switch to fallback after 3 failures
DISCOVERY_HEALTH_CHECK_ENABLED=true

# Performance Monitoring
ENABLE_API_MONITORING=true
API_ERROR_THRESHOLD=0.10        # 10% error rate threshold
API_RESPONSE_TIME_THRESHOLD=5000 # 5 second response time threshold
LOG_API_FAILURES=true
MONITOR_FALLBACK_USAGE=true
```

**Modified Existing Variables:**
```bash
# Updated for API resilience (conservative approach)
AMC_PRICE_CAP=500.0             # Keep current conservative cap
AMC_MIN_DOLLAR_VOL=5000000      # Keep current volume threshold
AMC_UNIVERSE_SIZE=58            # Current universe.txt size (no expansion yet)
AMC_DISCOVERY_FREQUENCY=300     # 5 minutes (keep current frequency)
```

### Feature Flags for API Resilience Rollout

```python
FEATURE_FLAGS = {
    # API Resilience Features
    'FF_API_CIRCUIT_BREAKER': 'false',   # Circuit breaker protection
    'FF_API_RETRY_LOGIC': 'false',       # Intelligent retry with backoff
    'FF_MULTIPLE_DATA_SOURCES': 'false', # Yahoo Finance and Alpha Vantage fallback
    'FF_INDIVIDUAL_API_CALLS': 'false',  # Use individual calls vs grouped
    'FF_API_RESPONSE_CACHING': 'false',  # Cache successful API responses
    
    # Discovery Pipeline Enhancements
    'FF_ENHANCED_ERROR_HANDLING': 'false', # Better error classification
    'FF_FALLBACK_DATA_SOURCES': 'false',   # Use cached/local data on API failure
    'FF_DISCOVERY_HEALTH_MONITORING': 'false', # Track pipeline health
    
    # User Experience
    'FF_API_STATUS_DISPLAY': 'false',    # Show API status to users
    'FF_FALLBACK_MODE_NOTICE': 'false',  # Notify users when using fallback data
    'FF_GRACEFUL_DEGRADATION': 'false',  # Continue with reduced functionality
}
```

### API Configuration Changes

**New Health and Status Endpoints:**
```python
# API Health Monitoring
/health/api-status             # Overall API health status
/health/polygon-status         # Polygon API specific health
/health/fallback-status        # Fallback data sources status
/discovery/health              # Discovery pipeline health

# Data Source Management
/discovery/data-sources        # Available data sources and status
/discovery/fallback-mode       # Check if system is in fallback mode
/admin/force-fallback         # Force switch to fallback data sources
/admin/reset-circuit-breaker  # Reset API circuit breakers

# Debugging and Diagnostics
/debug/api-errors             # Recent API error logs
/debug/fallback-usage         # Fallback usage statistics
/debug/discovery-trace        # Discovery pipeline execution trace
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

### API Resilience Schema Additions

**Migration Script: 001_api_resilience_system.sql**
```sql
-- API Response Cache Table
CREATE TABLE IF NOT EXISTS api_response_cache (
    id SERIAL PRIMARY KEY,
    endpoint_hash VARCHAR(64) NOT NULL,  -- MD5 hash of endpoint + params
    response_data JSONB NOT NULL,        -- Cached API response
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,       -- TTL for cache entry
    api_source VARCHAR(50) NOT NULL,     -- 'polygon', 'yahoo', 'alpha_vantage'
    symbol VARCHAR(10),                   -- Symbol if applicable
    
    INDEX idx_endpoint_hash (endpoint_hash),
    INDEX idx_expires_at (expires_at),
    INDEX idx_symbol_source (symbol, api_source)
);
```

**Migration Script: 002_api_health_monitoring.sql**
```sql
-- API Health and Error Tracking
CREATE TABLE IF NOT EXISTS api_health_log (
    id SERIAL PRIMARY KEY,
    api_source VARCHAR(50) NOT NULL,     -- 'polygon', 'yahoo', 'alpha_vantage'
    endpoint VARCHAR(200) NOT NULL,      -- API endpoint called
    status VARCHAR(20) NOT NULL,         -- 'success', 'error', 'timeout'
    response_time_ms INTEGER,            -- Response time in milliseconds
    error_message TEXT,                  -- Error details if applicable
    http_status_code INTEGER,            -- HTTP status code
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_api_source_status (api_source, status),
    INDEX idx_created_at (created_at),
    INDEX idx_endpoint (endpoint)
);

-- Circuit Breaker State Tracking  
CREATE TABLE IF NOT EXISTS circuit_breaker_state (
    id SERIAL PRIMARY KEY,
    api_source VARCHAR(50) NOT NULL,     -- 'polygon', 'yahoo', 'alpha_vantage'
    state VARCHAR(20) NOT NULL,          -- 'closed', 'open', 'half_open'
    failure_count INTEGER DEFAULT 0,
    last_failure_at TIMESTAMP,
    last_success_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(api_source),
    INDEX idx_state_updated (state, updated_at)
);

-- Discovery Pipeline Health
CREATE TABLE IF NOT EXISTS discovery_health (
    id SERIAL PRIMARY KEY,
    run_timestamp TIMESTAMP DEFAULT NOW(),
    symbols_attempted INTEGER NOT NULL,
    symbols_successful INTEGER NOT NULL,
    api_failures INTEGER DEFAULT 0,
    fallback_used BOOLEAN DEFAULT FALSE,
    primary_api_source VARCHAR(50),      -- Which API was primary
    processing_time_ms INTEGER NOT NULL,
    error_details JSONB,
    
    INDEX idx_run_timestamp (run_timestamp),
    INDEX idx_fallback_used (fallback_used)
);
```

### Data Migration Requirements

**Initialize Circuit Breaker States:**
```sql
-- Initialize circuit breaker states for all API sources
INSERT INTO circuit_breaker_state (api_source, state, failure_count)
VALUES 
    ('polygon', 'closed', 0),
    ('yahoo', 'closed', 0), 
    ('alpha_vantage', 'closed', 0)
ON CONFLICT (api_source) DO NOTHING;
```

**API Resilience Setup Migration:**
```python
# Migration script for API resilience setup
async def setup_api_resilience():
    """Initialize API resilience components"""
    
    # Initialize circuit breaker states
    await initialize_circuit_breakers()
    
    # Warm cache with current universe symbols
    current_symbols = load_universe_file()
    await warm_api_cache(current_symbols)
    
    # Test all fallback data sources
    await validate_fallback_sources()
    
    # Initialize health monitoring
    await setup_health_monitoring()
    
    logger.info(f"API resilience setup completed for {len(current_symbols)} symbols")
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

### Phase 1: API Resilience Foundation (Week 1)
1. **Backend Package Installation**
   - Install tenacity, circuit-breaker, httpx-cache for API resilience
   - Install backoff, aiofiles for retry and file operations
   - Upgrade httpx, polygon-api-client for better error handling

2. **Database Schema Migration**
   - Deploy api_resilience_system.sql
   - Create api_health_log and circuit_breaker_state tables
   - Initialize circuit breaker states for all APIs

3. **Environment Variable Configuration**
   - Add API resilience environment variables
   - Configure multiple API keys for fallback sources
   - Set up feature flags for gradual rollout

### Phase 2: Fallback Data Sources (Week 2)
1. **Alternative API Integration**
   - Implement Yahoo Finance fallback integration
   - Add Alpha Vantage secondary fallback
   - Create unified data source interface

2. **Circuit Breaker Implementation**
   - Deploy circuit breaker pattern for all APIs
   - Implement intelligent retry logic with exponential backoff
   - Add API response caching layer

3. **Discovery Pipeline Enhancement**
   - Modify select_candidates() to use individual API calls instead of grouped
   - Implement graceful fallback when primary API fails
   - Add comprehensive error handling and logging

### Phase 3: Frontend Integration (Week 3)
1. **React Package Installation**
   - Install react-error-boundary for error handling
   - Add @tanstack/react-query for resilient data fetching
   - Implement user-friendly error notifications

2. **User Experience Enhancement**
   - Add API status indicators to UI
   - Implement fallback mode notifications
   - Create graceful error states and retry mechanisms

3. **Testing and Validation**
   - Test API failure scenarios and fallback mechanisms
   - Validate data consistency across different sources
   - User acceptance testing for error scenarios

### Phase 4: Production Rollout (Week 4)
1. **Gradual Feature Enablement**
   - Enable API circuit breaker (FF_API_CIRCUIT_BREAKER=true)
   - Enable retry logic (FF_API_RETRY_LOGIC=true)
   - Enable fallback data sources (FF_MULTIPLE_DATA_SOURCES=true)

2. **System Hardening**
   - Enable individual API calls (FF_INDIVIDUAL_API_CALLS=true)
   - Activate API response caching (FF_API_RESPONSE_CACHING=true)
   - Enable comprehensive error handling (FF_ENHANCED_ERROR_HANDLING=true)

3. **Monitoring and Alerting**
   - Enable discovery health monitoring (FF_DISCOVERY_HEALTH_MONITORING=true)
   - Set up API failure alerting thresholds
   - Implement automated fallback triggers

## Risk Assessment and Mitigation

### API Failure Risks

**Primary API Dependency Risk:**
- **Risk**: Polygon grouped aggregates API continues to return 0 results
- **Impact**: Discovery pipeline finds 0 candidates, system appears broken
- **Mitigation**: Switch to individual API calls (`/v2/aggs/ticker/{symbol}/prev`)
- **Fallback**: Use Yahoo Finance or Alpha Vantage APIs
- **Monitoring**: Track API success rates and response times

**Rate Limiting Risks:**
- **Risk**: Free tier Polygon API rate limits cause failures
- **Impact**: Intermittent discovery failures during market hours
- **Mitigation**: Implement exponential backoff and request queuing
- **Fallback**: Circuit breaker pattern with automatic fallback to alternative sources
- **Monitoring**: Track rate limit headers and adjust request frequency

**Data Freshness Risks:**
- **Risk**: Fallback data sources may have stale or delayed data
- **Impact**: Trading decisions based on outdated information
- **Mitigation**: Timestamp all data sources and display data age to users
- **Fallback**: Use cached data with clear staleness warnings
- **Monitoring**: Track data age across all sources

### Data Quality Risks

**Inconsistent Data Sources:**
- **Risk**: Different APIs return different values for same symbol/date
- **Impact**: Inconsistent trading signals and user confusion
- **Mitigation**: Implement data validation and cross-source verification
- **Fallback**: Prefer most reliable source (Polygon > Yahoo > Alpha Vantage)
- **Monitoring**: Log and alert on significant data discrepancies

**API Response Validation:**
- **Risk**: Malformed or incomplete API responses cause processing errors
- **Impact**: Discovery pipeline crashes or returns invalid recommendations
- **Mitigation**: Strict response validation using Pydantic schemas
- **Fallback**: Skip invalid responses and continue with valid data
- **Monitoring**: Track validation failure rates by API source

### Operational Risks

**Deployment Risks:**
- **Risk**: API resilience changes may introduce new failure modes
- **Impact**: System may fail in unexpected ways during rollout
- **Mitigation**: Feature flags for gradual rollout with immediate rollback
- **Testing**: Comprehensive chaos engineering testing of failure scenarios
- **Monitoring**: Enhanced error tracking and automatic rollback triggers

**Fallback System Complexity:**
- **Risk**: Multiple fallback systems increase complexity and potential failure points
- **Impact**: Difficult to debug and maintain the system
- **Mitigation**: Clear documentation and comprehensive logging of data source usage
- **Testing**: Regular testing of all fallback paths
- **Monitoring**: Dashboard showing which data sources are active

## Success Metrics and Monitoring

### Key Performance Indicators

**API Resilience Performance:**
```python
SUCCESS_METRICS = {
    'api_success_rate': {'target': 0.95, 'min': 0.90},     # 95%+ API success
    'discovery_completion_rate': {'target': 0.98, 'min': 0.95}, # 98%+ discovery success
    'fallback_usage_rate': {'target': 0.05, 'max': 0.20},  # <20% fallback usage
    'api_response_time': {'target': 2000, 'max': 5000},    # 2s target, 5s max
    'data_freshness': {'target': 300, 'max': 1800},       # <30min data age
    'candidates_found': {'target': 5, 'min': 1},          # At least 1 candidate
}
```

**API Health Monitoring Thresholds:**
```python
API_HEALTH_THRESHOLDS = {
    'polygon_error_rate': {'warning': 0.05, 'critical': 0.15},
    'fallback_activation_rate': {'warning': 0.10, 'critical': 0.25},
    'circuit_breaker_open_duration': {'warning': 300, 'critical': 1800},  # seconds
    'api_response_time': {'warning': 3000, 'critical': 8000},  # milliseconds
    'discovery_failure_rate': {'warning': 0.02, 'critical': 0.10},
    'data_staleness': {'warning': 1800, 'critical': 3600},  # seconds
}
```

### Automated Monitoring Setup

**API Resilience Alerting:**
```python
ALERT_RULES = {
    'critical': {
        'channels': ['email', 'slack'],
        'conditions': ['all_apis_down', 'discovery_pipeline_failed', 'zero_candidates_found']
    },
    'warning': {
        'channels': ['slack'],
        'conditions': ['primary_api_degraded', 'fallback_activated', 'high_api_error_rate']
    },
    'info': {
        'channels': ['log_only'],
        'conditions': ['circuit_breaker_opened', 'data_source_switched', 'api_recovered']
    }
}
```

## Implementation Priority

**Critical Path (Fix Discovery Pipeline Immediately):**
1. **Week 1**: Fix select_candidates() function to use individual API calls instead of grouped
2. **Week 1**: Implement basic circuit breaker for Polygon API  
3. **Week 2**: Add Yahoo Finance fallback integration
4. **Week 2**: Deploy enhanced error handling and logging

**Success Criteria:**
- Discovery pipeline finds >0 candidates consistently
- System continues working when Polygon API fails
- Users see clear status when fallback data is used
- All API failures are logged and monitored

This focused dependencies document addresses the immediate AMC-TRADER discovery pipeline API failures while building a foundation for long-term system resilience.