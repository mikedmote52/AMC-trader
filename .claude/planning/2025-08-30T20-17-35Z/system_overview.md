---
run_id: 2025-08-30T20-17-35Z
version: 1
---

# AMC-TRADER System Overview

## Core Services Architecture

### Discovery Job (`backend/src/jobs/discover.py`)
- **Cadence**: Every 5 minutes during market hours (9:30-16:00 EST)
- **Purpose**: Identify explosive-growth stock opportunities using VIGL pattern detection
- **Process**: Polygon API → Multi-factor scoring → Redis publish → API consumption
- **Key Features**: 
  - VIGL pattern matching (324% winner analysis)
  - Squeeze detection with 7-factor weighted scoring
  - Volume spike analysis (target: 20.9x like VIGL)
  - Short interest and float size filtering

### Redis Cache Layer
- **Primary Keys**:
  - `amc:discovery:contenders.latest` (TTL: 600s)
  - `amc:discovery:explain.latest` (TTL: 600s)
  - `discovery_job_lock` (TTL: 240s)
- **Purpose**: Real-time data sharing between discovery job and API layer
- **Data**: Scored opportunities, pipeline traces, job coordination

### FastAPI Backend (`backend/src/app.py`)
- **Architecture**: Async FastAPI with structured logging
- **Core Routes**:
  - `/discovery/*` - Discovery pipeline output
  - `/portfolio/*` - Alpaca position sync
  - `/trades/*` - Order execution with guardrails
  - `/thesis/*` - AI-powered analysis
- **Middleware**: CORS, trace headers, exception handling
- **Health**: `/health` with component status checks

### React Frontend (`frontend/src/`)
- **Components**:
  - `TopRecommendations` - Discovery output display
  - `SqueezeMonitor` - Real-time squeeze alerts
  - `TradeModal` - Order entry interface
- **Polling**: 15-60 second intervals for real-time updates
- **State**: React hooks for API integration

### Alpaca Integration (`backend/src/services/broker_alpaca.py`)
- **Sync Frequency**: On-demand via API calls
- **Functions**: Account data, position queries, order placement
- **Mode**: Paper trading with live trading capability
- **Guardrails**: Price caps, position limits, kill switch

## Service Dependencies
```
Polygon API → Discovery Job → Redis → FastAPI → React Dashboard
                                  ↓
Alpaca API ←─────────────────── Trade Execution
```

## Current State Analysis
- Discovery job active and publishing to Redis
- UI components fetching from FastAPI endpoints  
- Alpaca sync operational in paper trading mode
- VIGL pattern detection calibrated for explosive opportunities