---
run_id: 2025-09-02
analysis_date: 2025-09-02
system: AMC-TRADER
focus: Short Interest Data Integration & Real-Time Enhancement
---

# Dependencies for AMC-TRADER Short Interest Data Integration

> **IMPLEMENTATION FOCUS**: This document outlines all technical dependencies required to integrate real short interest data into the AMC-TRADER system, including FINRA schedule awareness, Yahoo Finance API integration, and enhanced caching mechanisms.

## Summary

This document provides comprehensive dependency requirements for implementing real short interest data integration into the AMC-TRADER platform. The enhancement adds bi-monthly FINRA short interest reporting awareness, Yahoo Finance API access via yfinance library, enhanced Redis caching, circuit breaker patterns, background job scheduling, and robust data validation with quality scoring.

**Key Integration Points:**
- Current system uses Polygon.io API for market data with PostgreSQL + Redis caching
- New requirement adds Yahoo Finance short interest data with FINRA schedule awareness
- Background job system for bi-monthly updates aligned with FINRA reporting calendar
- Enhanced data validation and quality scoring for short interest accuracy

## Package Dependencies

### Backend Dependencies (Python 3.11+)

**New Packages Required for Short Interest Integration:**

- **yfinance** (>=0.2.28): Yahoo Finance API client for short interest data
  - Installation: `pip install yfinance>=0.2.28`
  - Purpose: Access to real-time and historical short interest data, institutional holdings
  - Configuration notes: Rate limiting, error handling, data validation required
  - Used by: Short interest data collection, FINRA reporting schedule alignment

- **pandas** (>=2.0.0): Data manipulation and analysis for short interest processing
  - Installation: `pip install pandas>=2.0.0`
  - Purpose: Data frame operations for short interest analysis, time series processing
  - Configuration notes: Memory optimization for large datasets, vectorized operations
  - Used by: Short interest data processing, quality scoring algorithms

- **numpy** (>=1.24.0,<2.0.0): Numerical computing for short interest calculations  
  - Installation: `pip install numpy>=1.24.0,<2.0.0`
  - Purpose: Mathematical operations, statistical analysis, performance optimization
  - Configuration notes: BLAS/LAPACK optimization for production deployment
  - Used by: Short interest ratio calculations, statistical scoring

- **schedule** (>=1.2.0): Job scheduling for FINRA bi-monthly updates
  - Installation: `pip install schedule>=1.2.0`
  - Purpose: Automated short interest data collection aligned with FINRA calendar
  - Configuration notes: Timezone handling, retry logic for failed jobs
  - Used by: Background job scheduler, FINRA reporting schedule awareness

- **pytz** (>=2024.1): Timezone handling for FINRA reporting schedules
  - Installation: `pip install pytz>=2024.1`
  - Purpose: Accurate timezone conversion for FINRA reporting deadlines
  - Configuration notes: EST/EDT handling for FINRA schedule compliance
  - Used by: Job scheduling, data timestamp normalization

- **beautifulsoup4** (>=4.12.0): HTML parsing for FINRA schedule scraping
  - Installation: `pip install beautifulsoup4>=4.12.0`
  - Purpose: Parse FINRA website for updated reporting schedules
  - Configuration notes: Error handling for website structure changes
  - Used by: FINRA schedule validation, automated schedule updates

- **lxml** (>=5.0.0): XML/HTML processing engine for BeautifulSoup
  - Installation: `pip install lxml>=5.0.0`
  - Purpose: High-performance HTML/XML parsing backend
  - Configuration notes: C library dependencies for production deployment
  - Used by: Fast HTML parsing for FINRA data extraction

**Enhanced Circuit Breaker and Retry Logic:**

- **tenacity** (>=9.0.0): Advanced retry mechanisms with exponential backoff
  - Installation: `pip install tenacity>=9.0.0` 
  - Purpose: Robust retry logic for Yahoo Finance API calls, handles rate limiting
  - Configuration notes: Custom retry strategies for different API endpoints
  - Used by: Yahoo Finance API wrapper, data collection resilience

- **circuitbreaker** (>=1.4.0): Circuit breaker pattern for API protection
  - Installation: `pip install circuitbreaker>=1.4.0`
  - Purpose: Prevent cascade failures when Yahoo Finance API is degraded
  - Configuration notes: Failure threshold tuning, recovery timeout optimization
  - Used by: API client wrappers, external service protection

**Background Job Processing:**

- **celery** (>=5.3.0): Distributed task queue for background processing
  - Installation: `pip install celery[redis]>=5.3.0`
  - Purpose: Asynchronous short interest data collection and processing
  - Configuration notes: Redis broker configuration, worker scaling
  - Used by: Background job execution, task scheduling, data pipeline processing

- **celery-beat** (>=2.5.0): Periodic task scheduler for Celery
  - Installation: `pip install django-celery-beat>=2.5.0` (install as `celery[beat]`)
  - Purpose: Schedule bi-monthly short interest updates based on FINRA calendar
  - Configuration notes: Database-backed scheduling, timezone awareness
  - Used by: FINRA schedule-aware task scheduling

### Package Version Conflicts and Resolutions

**Potential Conflicts:**
- **pandas vs numpy**: Ensure pandas 2.0+ is compatible with numpy <2.0.0
- **yfinance vs requests**: yfinance requires requests>=2.31.0, verify compatibility
- **celery vs redis**: Celery 5.3+ requires redis>=4.5.0, current system uses redis 5.0.8 (compatible)

**Resolution Strategy:**
```txt
# Updated requirements.txt additions
yfinance>=0.2.28
pandas>=2.0.0,<2.2.0
numpy>=1.24.0,<2.0.0
schedule>=1.2.0
pytz>=2024.1
beautifulsoup4>=4.12.0
lxml>=5.0.0
tenacity>=9.0.0
circuitbreaker>=1.4.0
celery[redis]>=5.3.0
celery[beat]>=5.3.0

# Ensure compatibility
requests>=2.31.0
aiohttp>=3.9.0
```

### Frontend Dependencies (React/TypeScript)

**Enhanced Data Visualization:**

- **recharts** (>=2.8.0): Charts for short interest visualization
  - Installation: `npm install recharts@>=2.8.0`
  - Purpose: Display short interest trends, historical patterns, quality scores
  - Used by: Short interest dashboard, data visualization components

- **date-fns** (>=2.30.0): Date manipulation for FINRA schedule display
  - Installation: `npm install date-fns@>=2.30.0`
  - Purpose: Handle FINRA reporting dates, schedule calculations
  - Used by: Schedule displays, date formatting, timezone handling

**No Breaking Changes:**
- All new frontend dependencies are additive
- Existing React 19.1.1 + TypeScript architecture maintained
- No version conflicts with current Vite/ESLint setup

## Environment Variables and Configuration

### Required Environment Variables

```bash
# Short Interest Data Configuration
YAHOO_FINANCE_ENABLED=true
YAHOO_FINANCE_RATE_LIMIT=5              # Requests per second
YAHOO_FINANCE_TIMEOUT=30                # Request timeout seconds
YAHOO_FINANCE_RETRY_ATTEMPTS=3          # Retry failed requests

# FINRA Schedule Configuration
FINRA_SCHEDULE_CHECK_ENABLED=true       # Automatically check FINRA schedule
FINRA_SCHEDULE_URL="https://www.finra.org/filing-reporting/regulatory-filing-systems/short-interest" 
FINRA_TIMEZONE="America/New_York"       # EST/EDT for FINRA schedules
FINRA_BUFFER_DAYS=2                     # Days after FINRA deadline to collect data

# Short Interest Processing
SHORT_INTEREST_UPDATE_FREQUENCY=720     # Minutes (12 hours) between update checks
SHORT_INTEREST_QUALITY_THRESHOLD=0.75   # Minimum quality score (0-1)
SHORT_INTEREST_CACHE_TTL=86400         # 24 hours cache TTL for short interest data
SHORT_INTEREST_BATCH_SIZE=100          # Symbols processed per batch

# Background Job Configuration  
CELERY_BROKER_URL=redis://localhost:6379/1    # Separate Redis DB for Celery
CELERY_RESULT_BACKEND=redis://localhost:6379/1
CELERY_TIMEZONE="America/New_York"
CELERY_BEAT_SCHEDULE_ENABLED=true
CELERY_WORKER_CONCURRENCY=2            # Number of worker processes

# Data Quality and Validation
ENABLE_SHORT_INTEREST_VALIDATION=true
SHORT_INTEREST_MAX_AGE_DAYS=14         # Maximum acceptable data age
SHORT_INTEREST_MIN_VOLUME_FILTER=1000000  # Minimum daily volume for inclusion
ALERT_ON_SHORT_INTEREST_ANOMALIES=true
```

### Optional Configuration Variables

```bash
# Advanced Features (Optional)
ENABLE_INSTITUTIONAL_HOLDINGS=false    # Include institutional holding data
ENABLE_SHORT_BORROW_RATES=false       # Include borrow rate data (if available)
ENABLE_SHORT_INTEREST_PREDICTIONS=false # ML-based short interest predictions
SHORT_INTEREST_HISTORICAL_DEPTH=365   # Days of historical data to maintain

# Performance Tuning (Optional)
YAHOO_FINANCE_CONNECTION_POOL_SIZE=10
YAHOO_FINANCE_USE_CACHE=true
SHORT_INTEREST_MEMORY_LIMIT=512MB      # Memory limit for processing
ENABLE_SHORT_INTEREST_COMPRESSION=true # Compress historical data storage
```

## Database Schema Changes

### New Tables for Short Interest Data

**Migration Script: 003_short_interest_integration.sql**
```sql
-- Short Interest Data Storage
CREATE TABLE IF NOT EXISTS short_interest_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    reporting_date DATE NOT NULL,           -- FINRA reporting period end date  
    settlement_date DATE NOT NULL,          -- Data settlement date
    short_interest_shares BIGINT NOT NULL,  -- Number of shares short
    avg_daily_volume BIGINT,                -- Average daily volume
    days_to_cover DECIMAL(10,2),            -- Short interest ratio
    short_percent_float DECIMAL(5,4),       -- Percentage of float short
    data_source VARCHAR(50) DEFAULT 'yahoo_finance',
    data_quality_score DECIMAL(3,2) DEFAULT 1.0,  -- Quality score 0-1
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(symbol, reporting_date, data_source),
    INDEX idx_symbol_reporting_date (symbol, reporting_date),
    INDEX idx_reporting_date (reporting_date),
    INDEX idx_data_quality (data_quality_score),
    INDEX idx_short_percent (short_percent_float)
);

-- FINRA Reporting Schedule Tracking
CREATE TABLE IF NOT EXISTS finra_reporting_schedule (
    id SERIAL PRIMARY KEY,
    settlement_date DATE NOT NULL,          -- Settlement date for reporting period
    due_date DATE NOT NULL,                 -- FINRA deadline for data submission  
    published_date DATE,                    -- When data becomes available
    status VARCHAR(20) DEFAULT 'pending',   -- pending, available, processed
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(settlement_date),
    INDEX idx_due_date (due_date),
    INDEX idx_status (status),
    INDEX idx_published_date (published_date)
);

-- Short Interest Quality Metrics
CREATE TABLE IF NOT EXISTS short_interest_quality (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    reporting_date DATE NOT NULL,
    data_source VARCHAR(50) NOT NULL,
    completeness_score DECIMAL(3,2),       -- Data completeness (0-1)
    accuracy_score DECIMAL(3,2),           -- Cross-validation accuracy
    freshness_score DECIMAL(3,2),          -- Data timeliness score
    consistency_score DECIMAL(3,2),        -- Historical consistency
    overall_quality DECIMAL(3,2),          -- Composite quality score
    validation_notes JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_symbol_date (symbol, reporting_date),
    INDEX idx_overall_quality (overall_quality),
    INDEX idx_data_source (data_source)
);

-- Background Job Status Tracking
CREATE TABLE IF NOT EXISTS short_interest_jobs (
    id SERIAL PRIMARY KEY,
    job_type VARCHAR(50) NOT NULL,          -- 'data_collection', 'schedule_check', 'quality_validation'
    status VARCHAR(20) DEFAULT 'pending',   -- pending, running, completed, failed
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    symbols_processed INTEGER DEFAULT 0,
    symbols_successful INTEGER DEFAULT 0,
    symbols_failed INTEGER DEFAULT 0,
    error_details JSONB,
    processing_time_seconds INTEGER,
    next_run_at TIMESTAMP,
    
    INDEX idx_job_type_status (job_type, status),
    INDEX idx_started_at (started_at),
    INDEX idx_next_run (next_run_at)
);
```

### Integration with Existing Schema

**Enhanced Recommendations Table:**
```sql
-- Add short interest columns to existing recommendations table
ALTER TABLE recommendations 
ADD COLUMN IF NOT EXISTS short_interest_shares BIGINT,
ADD COLUMN IF NOT EXISTS short_percent_float DECIMAL(5,4),
ADD COLUMN IF NOT EXISTS days_to_cover DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS short_interest_quality DECIMAL(3,2),
ADD COLUMN IF NOT EXISTS short_interest_updated_at TIMESTAMP;

-- Add indexes for short interest queries
CREATE INDEX IF NOT EXISTS idx_recommendations_short_percent 
ON recommendations(short_percent_float) WHERE short_percent_float IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_recommendations_days_cover 
ON recommendations(days_to_cover) WHERE days_to_cover IS NOT NULL;
```

## Infrastructure Requirements

### Redis Memory Allocation for Short Interest Caching

**Enhanced Cache Strategy:**
- **Current**: 64MB Redis cache for basic market data
- **Required**: 256MB Redis cache for comprehensive short interest caching
- **Key Distribution**:
  - Short Interest Data: 128MB (historical and current short interest by symbol)
  - FINRA Schedule Cache: 32MB (reporting dates and deadlines)
  - Data Quality Metrics: 32MB (validation scores and quality indicators)
  - Job Status Cache: 32MB (background job coordination and status)
  - Market Data Cache: 32MB (existing market data, reduced allocation)

**Redis Configuration Updates:**
```ini
# redis.conf updates for short interest integration
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000

# Additional Redis databases for separation
# Database 0: Market data and discovery (existing)
# Database 1: Celery broker and results  
# Database 2: Short interest data cache
# Database 3: Job coordination and locks
```

### Background Job Processing Infrastructure

**Celery Worker Configuration:**
```python
# celery_config.py
CELERY_CONFIG = {
    'broker_url': 'redis://localhost:6379/1',
    'result_backend': 'redis://localhost:6379/1',
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'America/New_York',
    
    # Task routing
    'task_routes': {
        'short_interest.collect_data': {'queue': 'short_interest'},
        'short_interest.validate_quality': {'queue': 'data_quality'},
        'short_interest.update_schedule': {'queue': 'schedule_check'},
    },
    
    # Beat schedule for bi-monthly updates
    'beat_schedule': {
        'check-finra-schedule': {
            'task': 'short_interest.check_finra_schedule',
            'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
        },
        'collect-short-interest-data': {
            'task': 'short_interest.collect_data',
            'schedule': crontab(hour=10, minute=0, day_of_week='1,3'),  # Mon/Wed
        },
        'validate-data-quality': {
            'task': 'short_interest.validate_quality', 
            'schedule': crontab(hour=11, minute=0, day_of_week='1,3'),  # After collection
        },
    }
}
```

### API Rate Limiting and Circuit Breaker Configuration

**Yahoo Finance API Protection:**
```python
YAHOO_FINANCE_CONFIG = {
    # Circuit breaker settings
    'failure_threshold': 5,        # Open after 5 failures
    'recovery_timeout': 300,       # 5 minutes recovery time
    'expected_exception': (ConnectionError, Timeout, HTTPError),
    
    # Rate limiting  
    'requests_per_second': 5,      # Conservative rate limit
    'burst_limit': 10,             # Burst allowance
    'backoff_factor': 2,           # Exponential backoff multiplier
    'max_retries': 3,              # Maximum retry attempts
    
    # Data validation
    'required_fields': ['shortRatio', 'sharesShort', 'floatShares'],
    'quality_checks': ['range_validation', 'consistency_check', 'freshness_check'],
    'fallback_enabled': True,      # Fall back to cached data
}
```

### Memory and Storage Requirements

**Production Resource Allocation:**
```python
RESOURCE_REQUIREMENTS = {
    # Memory allocation
    'python_process_memory': '512MB',      # Base FastAPI + libraries
    'pandas_processing_memory': '256MB',   # DataFrame operations
    'redis_cache_memory': '256MB',         # Enhanced caching
    'celery_worker_memory': '128MB',       # Background job processing
    'total_memory_required': '1152MB',     # Conservative estimate
    
    # Storage allocation  
    'short_interest_data': '150MB',        # Historical short interest data
    'quality_metrics': '50MB',             # Data quality tracking
    'job_logs': '100MB',                   # Background job logs and status
    'finra_schedule_data': '25MB',         # FINRA reporting schedule cache
    'total_storage_required': '325MB',     # Additional PostgreSQL storage
}
```

## Integration Testing Requirements

### Testing Dependencies

**Additional Test Packages:**
```txt
# Test requirements for short interest integration
pytest-asyncio>=0.21.0          # Async testing support
pytest-celery>=0.0.0            # Celery task testing
pytest-mock>=3.11.0             # Mocking Yahoo Finance API
responses>=0.23.0                # HTTP request mocking
fakeredis>=2.18.0               # Redis mocking for tests
freezegun>=1.2.2                # Time mocking for FINRA schedules
factory-boy>=3.3.0              # Test data generation
```

**Test Environment Configuration:**
```bash
# Test-specific environment variables
TEST_MODE=true
YAHOO_FINANCE_MOCK=true          # Use mock responses in tests
FINRA_SCHEDULE_MOCK=true         # Mock FINRA schedule API
CELERY_TASK_ALWAYS_EAGER=true    # Execute tasks synchronously in tests
SHORT_INTEREST_CACHE_TTL=1       # Short TTL for test isolation
```

### Integration Test Scenarios

**Critical Test Cases:**
1. **FINRA Schedule Integration**: Verify correct parsing of FINRA reporting dates
2. **Yahoo Finance API Resilience**: Test API failure handling and fallback mechanisms
3. **Data Quality Validation**: Verify quality scoring algorithms and thresholds
4. **Background Job Processing**: Test Celery task execution and error handling
5. **Cache Management**: Verify Redis caching and TTL handling
6. **Circuit Breaker**: Test API protection during failures

## Monitoring and Observability

### Enhanced Monitoring Dependencies

**Monitoring Packages:**
```txt
# Monitoring and observability for short interest features
prometheus-client>=0.21.0       # Metrics collection (already installed)
structlog>=24.4.0               # Structured logging (already installed)
sentry-sdk>=1.32.0              # Error tracking and performance monitoring
```

**Monitoring Configuration:**
```python
SHORT_INTEREST_METRICS = {
    # Data collection metrics
    'short_interest_symbols_processed_total': 'Counter',
    'short_interest_api_calls_total': 'Counter', 
    'short_interest_data_quality_score': 'Histogram',
    'short_interest_processing_time_seconds': 'Histogram',
    
    # API health metrics
    'yahoo_finance_api_requests_total': 'Counter',
    'yahoo_finance_api_errors_total': 'Counter',
    'yahoo_finance_circuit_breaker_state': 'Gauge',
    'yahoo_finance_response_time_seconds': 'Histogram',
    
    # Background job metrics
    'celery_short_interest_jobs_total': 'Counter',
    'celery_short_interest_job_duration_seconds': 'Histogram',
    'finra_schedule_check_success': 'Counter',
    
    # Data freshness metrics
    'short_interest_data_age_hours': 'Gauge',
    'finra_data_availability_delay_hours': 'Gauge',
}
```

## Implementation Order and Risk Assessment

### Phase 1: Core Infrastructure (Week 1-2)
1. **Package Installation and Testing**
   - Install yfinance, pandas, numpy, schedule with version conflict testing
   - Set up pytest environment with mock dependencies
   - Validate package compatibility with existing system

2. **Database Schema Migration**
   - Deploy short_interest_data and supporting tables
   - Test migration rollback procedures
   - Validate schema performance with sample data

3. **Basic Yahoo Finance Integration**
   - Implement yfinance wrapper with rate limiting
   - Add circuit breaker pattern for API protection
   - Test API connectivity and data validation

### Phase 2: Background Job System (Week 2-3)
1. **Celery Integration**
   - Set up Celery broker and worker configuration
   - Implement basic short interest data collection tasks
   - Test task scheduling and error handling

2. **FINRA Schedule Awareness**
   - Implement FINRA schedule parsing and caching
   - Add bi-monthly job scheduling based on FINRA calendar
   - Test timezone handling and schedule accuracy

3. **Data Quality System**
   - Implement quality scoring algorithms
   - Add data validation and consistency checks
   - Test quality metrics and thresholds

### Phase 3: Frontend Integration (Week 3-4)
1. **Data Visualization**
   - Add short interest charts and displays
   - Implement quality score indicators
   - Test responsive design and performance

2. **User Experience Enhancement**
   - Add FINRA schedule awareness to UI
   - Implement data freshness indicators
   - Test user feedback for stale or low-quality data

### Risk Assessment

**High-Risk Dependencies:**
- **yfinance reliability**: Yahoo Finance API may change without notice
  - **Mitigation**: Implement robust error handling and fallback to cached data
  - **Monitoring**: Track API success rates and response format changes

- **Pandas memory usage**: Large datasets may cause memory issues
  - **Mitigation**: Implement chunked processing and memory monitoring
  - **Monitoring**: Track memory usage during data processing

**Medium-Risk Dependencies:**
- **Celery complexity**: Background job system adds operational complexity
  - **Mitigation**: Comprehensive logging and monitoring of job execution
  - **Monitoring**: Track job success rates and execution times

- **FINRA schedule changes**: FINRA may modify reporting schedules
  - **Mitigation**: Automated schedule validation and manual override capability
  - **Monitoring**: Alert on schedule parsing failures or unexpected changes

**Performance Considerations:**
- **Memory Requirements**: Total memory footprint increases from ~256MB to ~1.2GB
- **Storage Requirements**: PostgreSQL storage increases by ~325MB
- **Network Usage**: Additional API calls to Yahoo Finance (rate limited)
- **Processing Load**: Background jobs may impact system performance during execution

### Success Criteria

**Implementation Success Metrics:**
```python
SUCCESS_CRITERIA = {
    'short_interest_data_coverage': 0.95,      # 95%+ of tracked symbols have SI data
    'data_quality_score_average': 0.80,        # Average quality score ≥0.80
    'api_success_rate': 0.95,                  # 95%+ Yahoo Finance API success
    'background_job_success_rate': 0.98,       # 98%+ Celery job success
    'data_freshness_compliance': 0.90,         # 90%+ data within 14 days
    'system_performance_impact': 0.10,         # <10% performance degradation
    'memory_usage_increase': 0.80,             # Memory increase within 80% of estimate
}
```

This comprehensive dependencies document provides the technical foundation for integrating real short interest data into the AMC-TRADER system while maintaining system reliability and performance standards.