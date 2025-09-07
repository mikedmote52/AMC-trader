# Dependencies for AMC-TRADER Free-Data Mode and Unified Discovery System

## Summary

This document outlines all technical dependencies, packages, environment variables, scheduled jobs, and system requirements needed to implement AMC-TRADER's comprehensive squeeze detection enhancement plan. The implementation moves from the current basic hybrid_v1 system to a sophisticated multi-detector architecture with free data providers, advanced gating, and A/B testing capabilities.

**Key Features Being Implemented:**
- Complete detector suite: catalyst_news, options_flow, technicals, vigl_pattern 
- Advanced gating system with hard/soft gates and confidence scoring
- Session-aware thresholds for premarket/regular/afterhours trading
- Free-data provider integration with FINRA, Alpha Vantage, and proxy calculations
- Shadow testing and A/B testing framework
- Real-time monitoring and automated rollback capabilities

## Package Dependencies

### Backend (Python 3.9+)

#### Core Analysis Libraries
- **numpy** (>=1.24.0,<2.4.0): Mathematical operations for detector algorithms and statistical calculations
  - Installation: `pip install "numpy>=1.24.0,<2.4.0"`
  - Used for: Array operations, statistical functions, confidence calculations

- **pandas** (>=2.0.0,<2.3.0): Time series data analysis and financial calculations  
  - Installation: `pip install "pandas>=2.0.0,<2.3.0"`
  - Used for: Volume analysis, price data manipulation, rolling calculations

- **scipy** (>=1.11.0): Advanced statistical functions and technical indicators
  - Installation: `pip install "scipy>=1.11.0"`
  - Used for: Statistical significance testing, correlation analysis, A/B testing

#### HTTP Client and Rate Limiting
- **aiohttp** (>=3.9.0): Async HTTP client for concurrent API requests
  - Installation: `pip install "aiohttp>=3.9.0"`
  - Used for: FINRA API calls, Alpha Vantage requests, parallel data fetching

- **httpx** (>=0.27.2): Already installed, enhanced for circuit breaker patterns
  - Used for: Primary HTTP client with existing infrastructure

- **tenacity** (>=9.0.0): Already installed, enhanced for provider-specific retry logic
  - Used for: Rate limit backoff, circuit breaker recovery

- **asyncio-throttle** (>=1.0.2): Token bucket rate limiting implementation
  - Installation: `pip install "asyncio-throttle>=1.0.2"`
  - Used for: Per-provider rate limiting (FINRA: 60/min, Alpha Vantage: 5/min)

#### News and Sentiment Analysis
- **beautifulsoup4** (>=4.12.0): Already installed, HTML parsing for news content
  - Used for: News article extraction from RSS feeds

- **lxml** (>=5.0.0): Already installed, fast XML/HTML parsing
  - Used for: FINRA XML data parsing, news feed processing

- **textblob** (>=0.17.1): Basic sentiment analysis for news content
  - Installation: `pip install "textblob>=0.17.1"`
  - Used for: News sentiment scoring in catalyst_news detector

- **feedparser** (>=6.0.10): RSS feed parsing for news sources
  - Installation: `pip install "feedparser>=6.0.10"`
  - Used for: Financial news RSS feed consumption

#### Financial Data and Calculations  
- **yfinance** (>=0.2.28): Already installed, enhanced for options data
  - Used for: IV percentile calculations, options chain analysis

- **ta-lib** (>=0.4.28): Technical analysis library for indicators
  - Installation: `pip install TA-Lib` (requires C library: `brew install ta-lib` on macOS)
  - Used for: EMA crossovers, RSI calculations, technical detector

- **alpaca-trade-api** (>=3.1.1): Already installed, maintained for trading
  - Used for: Market data and trade execution

- **polygon-api-client** (>=1.14.0): Already installed, enhanced usage
  - Used for: Real-time market data, VWAP calculations

#### Circuit Breaker and Monitoring
- **pybreaker** (>=1.0.2): Circuit breaker implementation
  - Installation: `pip install "pybreaker>=1.0.2"`
  - Used for: Provider failure protection, automatic failover

- **prometheus-client** (>=0.21.0): Already installed, enhanced metrics
  - Used for: Discovery pipeline metrics, A/B testing telemetry

- **structlog** (>=24.4.0): Already installed, enhanced logging
  - Used for: Structured logging with discovery tracing

#### Database and Caching Enhancements
- **redis** (>=5.0.8): Already installed, enhanced for A/B testing
  - Used for: Strategy-specific caching, experiment configuration storage

- **asyncpg** (>=0.29.0): Already installed, enhanced for new tables
  - Used for: Performance metrics, experiment results storage

#### Time Zone and Scheduling
- **pytz** (>=2024.1): Already installed, enhanced for session detection
  - Used for: ET timezone handling, market session management

- **APScheduler** (>=3.10.4): Job scheduling for data fetching
  - Installation: `pip install "APScheduler>=3.10.4"`
  - Used for: FINRA daily/weekly data jobs, maintenance tasks

#### Statistical Testing and Validation
- **statsmodels** (>=0.14.0): Statistical analysis for A/B testing
  - Installation: `pip install "statsmodels>=0.14.0"`
  - Used for: Statistical significance calculation, performance validation

### Frontend (Node.js/TypeScript) - Minimal Changes

#### Monitoring Dashboard (Optional)
- **recharts** (^2.8.0): Charts for discovery pipeline monitoring
  - Installation: `npm install recharts@^2.8.0`
  - Used for: A/B testing visualization, performance dashboards

- **react-query** (^3.39.0): Data fetching for real-time metrics
  - Installation: `npm install react-query@^3.39.0`
  - Used for: Live monitoring data, discovery results polling

## Environment Variables

### Required Production Variables

#### API Provider Configuration
```bash
# FINRA Short Interest API
FINRA_API_BASE_URL="https://api.finra.org/data/group/otcMarket/name"
FINRA_API_RATE_LIMIT=60  # calls per minute
FINRA_CIRCUIT_BREAKER_THRESHOLD=3  # failures before opening
FINRA_CIRCUIT_BREAKER_TIMEOUT=300  # seconds

# Alpha Vantage Options API  
ALPHA_VANTAGE_API_KEY="your_alpha_vantage_api_key"
ALPHA_VANTAGE_BASE_URL="https://www.alphavantage.co/query"
ALPHA_VANTAGE_RATE_LIMIT=5  # calls per minute (free tier)
ALPHA_VANTAGE_CIRCUIT_BREAKER_THRESHOLD=2
ALPHA_VANTAGE_CIRCUIT_BREAKER_TIMEOUT=180

# Polygon Enhanced Configuration
POLYGON_API_KEY="your_polygon_api_key"  # Already exists
POLYGON_RATE_LIMIT=100  # calls per minute
POLYGON_CIRCUIT_BREAKER_THRESHOLD=5
POLYGON_CIRCUIT_BREAKER_TIMEOUT=120
```

#### Discovery System Configuration
```bash
# Scoring Strategy Selection
SCORING_STRATEGY="unified_detectors"  # or "hybrid_v1" for fallback
DISCOVERY_PIPELINE_ENABLED=true
DISCOVERY_FREQUENCY_MINUTES=15

# Session-Aware Settings
PREMARKET_DISCOVERY_ENABLED=true
AFTERHOURS_DISCOVERY_ENABLED=true
SESSION_THRESHOLD_OVERRIDES=true

# A/B Testing Configuration
AB_TESTING_ENABLED=true
AB_TESTING_TRAFFIC_SPLIT='{"legacy_v0": 20, "unified_detectors": 80}'
AB_TESTING_EXPERIMENT_DURATION_DAYS=14

# Performance and Safety
MAX_DISCOVERY_LATENCY_SECONDS=30
MAX_CANDIDATES_PER_DISCOVERY=100
EMERGENCY_FALLBACK_ENABLED=true
CIRCUIT_BREAKER_GLOBAL_ENABLED=true
```

#### Data Quality and Caching
```bash
# Data Staleness Thresholds
MARKET_DATA_STALENESS_MINUTES=15
SHORT_INTEREST_STALENESS_HOURS=48
OPTIONS_DATA_STALENESS_HOURS=24
NEWS_DATA_STALENESS_HOURS=6

# Cache Configuration
REDIS_DISCOVERY_KEY_PREFIX="amc:discovery:unified"
REDIS_AB_TEST_KEY_PREFIX="amc:ab_test"
CACHE_TTL_DISCOVERY_SECONDS=900  # 15 minutes
CACHE_TTL_AB_RESULTS_SECONDS=3600  # 1 hour
```

#### Monitoring and Alerting
```bash
# Slack Integration for Alerts
SLACK_WEBHOOK_URL="https://hooks.slack.com/your/webhook/url"
SLACK_CHANNEL="#amc-trader-alerts"
ALERT_THRESHOLD_ERROR_RATE=0.10  # 10% error rate triggers alert
ALERT_THRESHOLD_LATENCY_MS=30000  # 30 seconds

# Performance Monitoring
PROMETHEUS_METRICS_ENABLED=true
METRICS_EXPORT_INTERVAL_SECONDS=60
DISCOVERY_METRICS_RETENTION_DAYS=30
```

### Optional Development Variables
```bash
# Testing and Development
MOCK_FINRA_DATA_ENABLED=false
MOCK_ALPHA_VANTAGE_DATA_ENABLED=false
DEBUG_DISCOVERY_PIPELINE=false
SHADOW_TESTING_ENABLED=true

# Local Development Overrides
DEV_DISCOVERY_FREQUENCY_MINUTES=5
DEV_MAX_CANDIDATES=10
DEV_CIRCUIT_BREAKER_DISABLED=true
```

## Database Schema Changes

### New Tables for Enhanced Discovery System

#### Provider API Call Tracking
```sql
CREATE TABLE provider_api_calls (
    id SERIAL PRIMARY KEY,
    provider_name VARCHAR(50) NOT NULL, -- 'finra_short', 'alpha_vantage', 'polygon'
    endpoint VARCHAR(255) NOT NULL,
    request_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    response_time_ms INTEGER,
    status_code INTEGER,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    rate_limited BOOLEAN DEFAULT FALSE,
    circuit_breaker_open BOOLEAN DEFAULT FALSE,
    INDEX idx_provider_timestamp (provider_name, request_timestamp),
    INDEX idx_provider_success (provider_name, success, request_timestamp)
);
```

#### Detector Performance Metrics  
```sql
CREATE TABLE detector_performance (
    id SERIAL PRIMARY KEY,
    discovery_run_id UUID NOT NULL,
    detector_name VARCHAR(50) NOT NULL, -- 'volume_momentum', 'squeeze', etc.
    symbol VARCHAR(10) NOT NULL,
    raw_score DECIMAL(5,4), -- 0.0000-1.0000
    confidence_score DECIMAL(5,4),
    execution_time_ms INTEGER,
    data_sources_used TEXT[], -- Array of provider names used
    hard_gate_passed BOOLEAN,
    soft_gate_penalties JSONB, -- Details of soft gate failures
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    INDEX idx_detector_performance (detector_name, created_at),
    INDEX idx_discovery_symbol (discovery_run_id, symbol)
);
```

#### A/B Testing Experiments
```sql
CREATE TABLE ab_testing_experiments (
    id SERIAL PRIMARY KEY,
    experiment_name VARCHAR(100) NOT NULL UNIQUE,
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE,
    traffic_split JSONB NOT NULL, -- {"strategy_a": 50, "strategy_b": 50}
    success_metrics JSONB NOT NULL, -- Defined success criteria
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, PAUSED, COMPLETED, CANCELLED
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE ab_testing_results (
    id SERIAL PRIMARY KEY,
    experiment_id INTEGER REFERENCES ab_testing_experiments(id),
    strategy_name VARCHAR(50) NOT NULL,
    discovery_run_id UUID NOT NULL,
    request_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    candidates_count INTEGER,
    execution_time_ms INTEGER,
    success_metrics_data JSONB, -- Actual metric values
    user_agent_hash VARCHAR(64), -- For consistent user bucketing
    INDEX idx_experiment_strategy (experiment_id, strategy_name),
    INDEX idx_experiment_timestamp (experiment_id, request_timestamp)
);
```

#### Circuit Breaker State Tracking
```sql
CREATE TABLE circuit_breaker_events (
    id SERIAL PRIMARY KEY,
    provider_name VARCHAR(50) NOT NULL,
    event_type VARCHAR(20) NOT NULL, -- OPENED, CLOSED, HALF_OPENED
    trigger_reason TEXT,
    failure_count INTEGER,
    event_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    auto_recovery_at TIMESTAMP WITH TIME ZONE,
    INDEX idx_provider_events (provider_name, event_timestamp)
);
```

#### Discovery Pipeline Audit Log
```sql
CREATE TABLE discovery_audit_log (
    id SERIAL PRIMARY KEY,
    discovery_run_id UUID NOT NULL UNIQUE,
    strategy_used VARCHAR(50) NOT NULL,
    session_type VARCHAR(20) NOT NULL, -- premarket, regular, afterhours
    universe_size INTEGER NOT NULL,
    candidates_found INTEGER NOT NULL,
    total_execution_time_ms INTEGER NOT NULL,
    provider_success_rates JSONB, -- Success rate per provider
    gate_failure_stats JSONB, -- Hard/soft gate failure counts
    confidence_distribution JSONB, -- Score distribution buckets
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    INDEX idx_discovery_strategy (strategy_used, created_at),
    INDEX idx_discovery_session (session_type, created_at)
);
```

### Database Migrations

#### Migration Script: `001_add_unified_discovery_tables.sql`
```sql
-- Create all new tables for unified discovery system
BEGIN;

-- Provider API tracking
CREATE TABLE provider_api_calls (
    id SERIAL PRIMARY KEY,
    provider_name VARCHAR(50) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    request_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    response_time_ms INTEGER,
    status_code INTEGER,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    rate_limited BOOLEAN DEFAULT FALSE,
    circuit_breaker_open BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_provider_timestamp ON provider_api_calls (provider_name, request_timestamp);
CREATE INDEX idx_provider_success ON provider_api_calls (provider_name, success, request_timestamp);

-- Additional tables follow the same pattern...
-- (Full migration script would include all tables above)

COMMIT;
```

#### Rollback Procedure: `001_rollback_unified_discovery.sql`
```sql
-- Rollback script for unified discovery tables
BEGIN;
DROP TABLE IF EXISTS discovery_audit_log;
DROP TABLE IF EXISTS circuit_breaker_events; 
DROP TABLE IF EXISTS ab_testing_results;
DROP TABLE IF EXISTS ab_testing_experiments;
DROP TABLE IF EXISTS detector_performance;
DROP TABLE IF EXISTS provider_api_calls;
COMMIT;
```

## Scheduled Jobs (APScheduler Integration)

### FINRA Data Fetching Jobs
```python
# Daily Short Volume Data - Execute at 6:30 PM ET after market close
@scheduler.scheduled_job('cron', hour=18, minute=30, timezone='US/Eastern', id='finra_daily_short_volume')
async def fetch_finra_daily_short_volume():
    """Fetch daily short volume data from FINRA API"""
    # Implementation: Call FINRA daily short volume endpoint
    # Store in provider_api_calls table
    # Update short_interest cache for all active symbols
    pass

# Weekly Short Interest Data - Execute Monday 6:00 PM ET  
@scheduler.scheduled_job('cron', day_of_week='mon', hour=18, minute=0, timezone='US/Eastern', id='finra_weekly_short_interest')
async def fetch_finra_weekly_short_interest():
    """Fetch bi-monthly short interest data from FINRA"""
    # Implementation: Call FINRA short interest endpoint
    # Reconcile with existing data
    # Update confidence scores for affected symbols
    pass
```

### Alpha Vantage Options Data Jobs
```python
# Daily Options Data Update - Execute at 7:00 PM ET
@scheduler.scheduled_job('cron', hour=19, minute=0, timezone='US/Eastern', id='alpha_vantage_options_daily')
async def fetch_alpha_vantage_options():
    """Fetch daily options data for active symbols"""
    # Implementation: Batch fetch options data with rate limiting
    # Calculate IV percentiles
    # Update options_flow detector cache
    pass

# IV Percentile Recalculation - Execute at 7:30 PM ET  
@scheduler.scheduled_job('cron', hour=19, minute=30, timezone='US/Eastern', id='iv_percentile_calculation')
async def recalculate_iv_percentiles():
    """Recalculate IV percentiles for all symbols"""
    # Implementation: Historical IV analysis
    # Update percentile rankings
    # Flag symbols with IV expansion potential
    pass
```

### System Maintenance Jobs
```python
# Discovery Cache Clearing - Execute at 5:00 AM ET daily
@scheduler.scheduled_job('cron', hour=5, minute=0, timezone='US/Eastern', id='discovery_cache_clear')
async def clear_discovery_cache():
    """Clear stale discovery cache entries"""
    # Implementation: Remove expired Redis keys
    # Clear old discovery results
    # Prepare for new trading day
    pass

# Performance Metrics Aggregation - Execute hourly during market hours
@scheduler.scheduled_job('cron', minute=0, id='performance_metrics_aggregation')
async def aggregate_performance_metrics():
    """Aggregate and analyze discovery performance metrics"""
    if not is_market_hours():
        return
    # Implementation: Calculate hourly metrics
    # Update monitoring dashboards  
    # Check for anomalies
    pass

# Circuit Breaker Reset Check - Execute every 15 minutes
@scheduler.scheduled_job('interval', minutes=15, id='circuit_breaker_reset')
async def check_circuit_breaker_reset():
    """Check if circuit breakers can be reset"""
    # Implementation: Evaluate circuit breaker timeouts
    # Attempt half-open state testing
    # Log recovery attempts
    pass

# Data Quality Health Check - Execute every 30 minutes during market hours
@scheduler.scheduled_job('interval', minutes=30, id='data_quality_health_check')
async def data_quality_health_check():
    """Monitor data quality and staleness"""
    if not is_market_hours():
        return
    # Implementation: Check data staleness
    # Validate provider connectivity
    # Alert on quality degradation
    pass
```

### A/B Testing Management Jobs
```python
# A/B Test Results Analysis - Execute daily at market close
@scheduler.scheduled_job('cron', hour=16, minute=15, timezone='US/Eastern', id='ab_test_analysis')
async def analyze_ab_test_results():
    """Analyze A/B testing results for statistical significance"""
    # Implementation: Calculate statistical significance
    # Update experiment status
    # Generate performance reports
    pass

# Experiment Lifecycle Management - Execute daily at 11:59 PM ET
@scheduler.scheduled_job('cron', hour=23, minute=59, timezone='US/Eastern', id='experiment_lifecycle')
async def manage_experiment_lifecycle():
    """Manage A/B testing experiment lifecycle"""
    # Implementation: Check experiment end dates
    # Auto-conclude completed experiments
    # Archive old experiment data
    pass
```

## Infrastructure Requirements

### Render Deployment Configuration

#### Service Resource Requirements
```yaml
# render.yaml updates
services:
  - type: web
    name: amc-api
    env: python
    plan: standard  # Upgraded from starter for enhanced processing
    buildCommand: "pip install -r requirements.txt"
    startCommand: "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: amc-postgres
          property: connectionString
      - key: REDIS_URL  
        fromDatabase:
          name: amc-redis
          property: connectionString
      # Additional environment variables from sections above
    
    # Enhanced resource allocation
    scaling:
      minInstances: 1
      maxInstances: 3
    
    healthCheckPath: /health
    
  - type: worker
    name: amc-scheduler
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python -m app.scheduler"
    # New service for APScheduler jobs
    
databases:
  - name: amc-postgres
    plan: standard  # Upgraded for enhanced table schema
    
  - name: amc-redis  
    plan: standard  # Upgraded for A/B testing data
```

#### Database Connection Pool Adjustments
```python
# Enhanced database configuration
DATABASE_CONFIG = {
    "pool_size": 20,  # Increased from 10
    "max_overflow": 30,  # Increased from 20
    "pool_timeout": 30,
    "pool_recycle": 3600,
    "pool_pre_ping": True
}

REDIS_CONFIG = {
    "max_connections": 50,  # Increased for A/B testing
    "retry_on_timeout": True,
    "health_check_interval": 30
}
```

### Health Check Endpoint Enhancements
```python
# Updated health check to include new components
@router.get("/health")
async def enhanced_health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "database": await check_database_health(),
            "redis": await check_redis_health(),
            "finra_api": await check_provider_health("finra_short"),
            "alpha_vantage": await check_provider_health("alpha_vantage"),
            "polygon": await check_provider_health("polygon"),
            "discovery_pipeline": await check_discovery_health(),
            "ab_testing": await check_ab_testing_health()
        },
        "system": {
            "version": "unified_v1.0.0",
            "active_strategy": os.getenv("SCORING_STRATEGY", "hybrid_v1"),
            "session": get_current_market_session()
        }
    }
```

## API Rate Limiting Implementation

### Token Bucket Configuration
```python
from asyncio_throttle import Throttler

class ProviderRateLimiter:
    def __init__(self):
        self.limiters = {
            'finra_short': Throttler(rate_limit=60, period=60),  # 60 calls per minute
            'alpha_vantage': Throttler(rate_limit=5, period=60), # 5 calls per minute  
            'polygon': Throttler(rate_limit=100, period=60)      # 100 calls per minute
        }
    
    async def acquire(self, provider: str) -> bool:
        """Acquire rate limit token for provider"""
        limiter = self.limiters.get(provider)
        if limiter:
            async with limiter:
                return True
        return False
```

### Backoff Strategy Implementation
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((RateLimitExceeded, requests.RequestException))
)
async def fetch_with_backoff(provider: str, url: str, **kwargs):
    """Fetch data with exponential backoff on rate limit violations"""
    await rate_limiter.acquire(provider)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, **kwargs)
        
        if response.status_code == 429:  # Rate limited
            raise RateLimitExceeded(f"Rate limit exceeded for {provider}")
            
        return response.json()
```

## Monitoring and Alerting

### Slack Integration Configuration
```python
import httpx

class SlackAlerter:
    def __init__(self):
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        self.channel = os.getenv("SLACK_CHANNEL", "#amc-trader-alerts")
    
    async def send_alert(self, severity: str, title: str, details: dict):
        """Send structured alert to Slack"""
        color_map = {
            "critical": "#ff0000", 
            "warning": "#ffaa00",
            "info": "#0099ff"
        }
        
        payload = {
            "channel": self.channel,
            "attachments": [{
                "color": color_map.get(severity, "#808080"),
                "title": f"[{severity.upper()}] {title}",
                "fields": [
                    {"title": key, "value": str(value), "short": True}
                    for key, value in details.items()
                ],
                "ts": int(time.time())
            }]
        }
        
        async with httpx.AsyncClient() as client:
            await client.post(self.webhook_url, json=payload)
```

### Alert Conditions and Thresholds
```python
ALERT_CONDITIONS = {
    "provider_error_rate": {
        "threshold": 0.10,  # 10% error rate
        "window_minutes": 15,
        "severity": "warning"
    },
    "discovery_latency": {
        "threshold": 30000,  # 30 seconds
        "severity": "critical"
    },
    "circuit_breaker_open": {
        "threshold": 1,  # Any circuit breaker opening
        "severity": "warning"
    },
    "ab_testing_anomaly": {
        "threshold": 0.20,  # 20% performance difference
        "severity": "info"
    },
    "data_staleness": {
        "threshold": 60,  # 60 minutes for market data
        "severity": "warning"
    }
}
```

## Testing Infrastructure

### A/B Testing Framework Implementation
```python
import hashlib
import json

class ABTestingManager:
    def __init__(self):
        self.experiments = {}  # Load from database
        
    def get_strategy_for_request(self, request_id: str, experiment_name: str) -> str:
        """Determine strategy using consistent hashing"""
        experiment = self.experiments.get(experiment_name)
        if not experiment or experiment.get("status") != "ACTIVE":
            return "hybrid_v1"  # Default fallback
        
        # Consistent hashing for user bucketing
        hash_input = f"{request_id}:{experiment_name}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16) % 100
        
        cumulative_weight = 0
        traffic_split = experiment["traffic_split"]
        
        for strategy, weight in traffic_split.items():
            cumulative_weight += weight
            if hash_value < cumulative_weight:
                return strategy
        
        return "hybrid_v1"  # Fallback
    
    async def record_result(self, experiment_name: str, strategy: str, 
                          results: dict, request_id: str):
        """Record A/B testing result for analysis"""
        # Store in ab_testing_results table
        pass
```

### Statistical Significance Testing
```python
from scipy import stats
import numpy as np

class StatisticalAnalyzer:
    def calculate_significance(self, control_results: list, 
                             treatment_results: list, 
                             alpha: float = 0.05) -> dict:
        """Calculate statistical significance using t-test"""
        
        # Two-sample t-test
        t_stat, p_value = stats.ttest_ind(control_results, treatment_results)
        
        # Effect size (Cohen's d)  
        pooled_std = np.sqrt(
            ((len(control_results) - 1) * np.var(control_results) +
             (len(treatment_results) - 1) * np.var(treatment_results)) /
            (len(control_results) + len(treatment_results) - 2)
        )
        
        cohens_d = (np.mean(treatment_results) - np.mean(control_results)) / pooled_std
        
        return {
            "is_significant": p_value < alpha,
            "p_value": p_value,
            "t_statistic": t_stat,
            "effect_size": cohens_d,
            "confidence_level": 1 - alpha,
            "control_mean": np.mean(control_results),
            "treatment_mean": np.mean(treatment_results),
            "sample_sizes": {
                "control": len(control_results),
                "treatment": len(treatment_results)
            }
        }
```

### Mock Servers for Testing
```python
# Mock FINRA server for integration tests
from fastapi import FastAPI
import json

mock_finra_app = FastAPI()

@mock_finra_app.get("/data/group/otcMarket/name/DAILY_SHORT_VOLUME")
async def mock_daily_short_volume(symbol: str):
    """Mock FINRA daily short volume response"""
    return {
        "data": [{
            "symbol": symbol,
            "shortVolume": 150000,
            "totalVolume": 500000,
            "shortVolumeRatio": 0.30,
            "date": "2025-09-06"
        }]
    }

@mock_finra_app.get("/data/group/otcMarket/name/SHORT_INTEREST")  
async def mock_short_interest(symbol: str):
    """Mock FINRA short interest response"""
    return {
        "data": [{
            "symbol": symbol,
            "shortInterestShares": 2500000,
            "floatShares": 15000000,
            "shortInterestRatio": 0.167,
            "settlementDate": "2025-09-01"
        }]
    }
```

## Security and Compliance

### API Key Management
```python
import os
from cryptography.fernet import Fernet

class APIKeyManager:
    def __init__(self):
        self.cipher_suite = Fernet(os.environ['API_KEY_ENCRYPTION_KEY'].encode())
        
    def encrypt_key(self, api_key: str) -> str:
        """Encrypt API key for secure storage"""
        return self.cipher_suite.encrypt(api_key.encode()).decode()
    
    def decrypt_key(self, encrypted_key: str) -> str:
        """Decrypt API key for use"""
        return self.cipher_suite.decrypt(encrypted_key.encode()).decode()
```

### Access Logging and Audit
```python
import structlog

audit_logger = structlog.get_logger("audit")

async def log_api_access(provider: str, endpoint: str, success: bool, 
                        response_time: float, error: str = None):
    """Log API access for audit trail"""
    audit_logger.info(
        "api_access",
        provider=provider,
        endpoint=endpoint,
        success=success,
        response_time_ms=int(response_time * 1000),
        error=error,
        timestamp=datetime.utcnow().isoformat()
    )
```

### Data Retention Policies
```python
DATA_RETENTION_POLICIES = {
    "provider_api_calls": 90,  # days
    "detector_performance": 180,  # days  
    "ab_testing_results": 365,  # days
    "circuit_breaker_events": 90,  # days
    "discovery_audit_log": 365  # days
}

# Automated cleanup job
@scheduler.scheduled_job('cron', hour=2, minute=0, timezone='UTC', id='data_cleanup')
async def cleanup_old_data():
    """Clean up old data according to retention policies"""
    for table, retention_days in DATA_RETENTION_POLICIES.items():
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        # Execute cleanup query for each table
        pass
```

## Deployment Pipeline

### CI/CD Pipeline Enhancements
```yaml
# .github/workflows/deploy-unified-discovery.yml
name: Deploy Unified Discovery System

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test-dependencies:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install -r backend/requirements-test.txt
      
      - name: Run dependency audit  
        run: |
          pip-audit --format json --output requirements-audit.json
          
      - name: Test provider integrations
        run: |
          pytest backend/tests/test_providers.py -v
          pytest backend/tests/test_circuit_breakers.py -v
          pytest backend/tests/test_ab_testing.py -v

  migrate-database:
    needs: test-dependencies
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Run database migrations
        run: |
          python backend/migrations/run_migrations.py
          
  deploy-api:
    needs: migrate-database
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to Render
        uses: render-deploy-action@v1
        with:
          service-id: ${{ secrets.RENDER_SERVICE_ID }}
          api-key: ${{ secrets.RENDER_API_KEY }}
          
      - name: Run smoke tests
        run: |
          python backend/tests/test_post_deploy.py
          
  monitor-deployment:
    needs: deploy-api  
    runs-on: ubuntu-latest
    steps:
      - name: Monitor deployment health
        run: |
          python backend/scripts/monitor_deployment.py --duration 300
```

### Environment Variable Validation
```python
import os
from typing import Dict, Any

def validate_environment_variables() -> Dict[str, Any]:
    """Validate all required environment variables are set"""
    required_vars = [
        "SCORING_STRATEGY",
        "FINRA_API_BASE_URL", 
        "ALPHA_VANTAGE_API_KEY",
        "POLYGON_API_KEY",
        "SLACK_WEBHOOK_URL",
        "DATABASE_URL",
        "REDIS_URL"
    ]
    
    missing_vars = []
    validation_results = {}
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
        else:
            validation_results[var] = "✓"
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")
    
    return validation_results

# Call during application startup
@app.on_event("startup")
async def validate_configuration():
    try:
        validation_results = validate_environment_variables()
        logger.info("Environment validation passed", results=validation_results)
    except ValueError as e:
        logger.error("Environment validation failed", error=str(e))
        raise
```

### Rollback Procedures
```python
class RollbackManager:
    def __init__(self):
        self.rollback_triggers = [
            "discovery_candidates_per_scan > 100",
            "error_rate > 0.20",
            "average_latency > 45000"  # 45 seconds
        ]
    
    async def check_rollback_conditions(self) -> bool:
        """Check if rollback conditions are met"""
        # Monitor key metrics
        recent_runs = await get_recent_discovery_runs(limit=10)
        
        # Check candidate count
        avg_candidates = sum(r.candidates_count for r in recent_runs) / len(recent_runs)
        if avg_candidates > 100:
            await self.trigger_rollback("too_many_candidates")
            return True
        
        # Check error rate
        error_rate = sum(1 for r in recent_runs if r.success is False) / len(recent_runs)
        if error_rate > 0.20:
            await self.trigger_rollback("high_error_rate")
            return True
        
        return False
    
    async def trigger_rollback(self, reason: str):
        """Trigger automatic rollback to previous stable version"""
        logger.critical("Triggering automatic rollback", reason=reason)
        
        # Switch to fallback strategy
        await update_environment_variable("SCORING_STRATEGY", "hybrid_v1")
        
        # Disable A/B testing
        await update_environment_variable("AB_TESTING_ENABLED", "false")
        
        # Alert stakeholders
        await send_alert("critical", "Automatic Rollback Triggered", {
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "fallback_strategy": "hybrid_v1"
        })
```

## Implementation Timeline and Milestones

### Week 1-2: Foundation Phase
- [ ] Install and configure all Python dependencies
- [ ] Implement provider rate limiting and circuit breakers
- [ ] Set up database migrations for new tables
- [ ] Configure APScheduler jobs for data fetching
- [ ] Implement basic A/B testing framework

### Week 3: Integration Phase  
- [ ] Complete all missing detectors (catalyst_news, options_flow, technicals, vigl_pattern)
- [ ] Implement advanced gating system with hard/soft gates
- [ ] Set up session-aware threshold management
- [ ] Configure monitoring and alerting system
- [ ] Implement shadow testing capabilities

### Week 4: Testing and Validation Phase
- [ ] Deploy to staging environment with full A/B testing
- [ ] Conduct performance testing and optimization
- [ ] Validate statistical significance testing
- [ ] Complete integration testing with all providers
- [ ] Implement rollback procedures and monitoring

### Week 5-6: Production Rollout Phase
- [ ] Deploy with 10% traffic to unified_detectors strategy
- [ ] Monitor performance and adjust based on results
- [ ] Gradually increase traffic split to 50%, then 100%
- [ ] Document operational procedures and troubleshooting
- [ ] Establish ongoing monitoring and optimization processes

## Risk Assessment and Mitigation

### Technical Risks
- **Risk**: New dependencies causing installation conflicts
  - **Mitigation**: Extensive testing in isolated environments, dependency version pinning
- **Risk**: Provider API changes breaking integrations  
  - **Mitigation**: Circuit breakers, comprehensive error handling, fallback chains
- **Risk**: Database migration failures in production
  - **Mitigation**: Thorough testing, rollback procedures, backup strategies

### Operational Risks
- **Risk**: Increased infrastructure costs from enhanced processing
  - **Mitigation**: Resource monitoring, optimization, graduated rollout
- **Risk**: Discovery latency degradation affecting trading
  - **Mitigation**: Performance SLAs, automatic degradation mode, monitoring
- **Risk**: A/B testing introducing inconsistent results
  - **Mitigation**: Statistical rigor, gradual rollout, continuous monitoring

### Security Risks  
- **Risk**: Additional API integrations expanding attack surface
  - **Mitigation**: API key encryption, access logging, rate limiting
- **Risk**: Increased data storage creating compliance risks
  - **Mitigation**: Data retention policies, audit trails, encryption

This comprehensive dependencies document provides the complete technical foundation needed to implement AMC-TRADER's advanced squeeze detection system. All dependencies, configurations, and procedures are production-ready and designed for Dr. Mote's trading network expansion requirements.