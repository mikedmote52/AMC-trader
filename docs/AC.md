# AMC Trading System - Acceptance Criteria

## Overview

This document defines the acceptance criteria for the AMC Trading System API, expressed as executable commands and JSON shape validations using `jq`. These tests ensure the system meets functional requirements and handles failure cases appropriately.

## Prerequisites

- `curl` command-line tool
- `jq` JSON processor
- System running on `http://localhost:8000` (or set `BASE_URL` environment variable)
- All required environment variables set (see Environment Variables section)

## Test Execution

```bash
# Run all acceptance tests
./scripts/smoke.sh && ./scripts/failcases.sh

# Run individual test suites
./scripts/smoke.sh      # Basic functionality tests
./scripts/failcases.sh  # Environment failure tests

# Set custom base URL
BASE_URL=https://your-app.onrender.com ./scripts/smoke.sh
```

## Smoke Test Acceptance Criteria

### 1. Health Check Endpoint

**Command:**
```bash
curl -s http://localhost:8000/health
```

**Expected Response Shape:**
```bash
# Status Code: 200
# JSON Shape Validation:
jq -e '.status == "healthy" and .components and (.components | type) == "object"'
```

**Required Fields:**
- `status`: Must be `"healthy"`
- `components`: Object containing health status of system components

**Example Response:**
```json
{
  "status": "healthy",
  "components": {
    "alpaca_connection": true,
    "claude_api": true,
    "market_data": true,
    "database": true
  }
}
```

### 2. Discovery Execution

**Command:**
```bash
curl -s -X POST http://localhost:8000/discovery/run
```

**Expected Response Shape:**
```bash
# Status Code: 200
# JSON Shape Validation:
jq -e '.opportunities and (.opportunities | type) == "array"'
```

**Required Fields:**
- `opportunities`: Array of discovered trading opportunities
- Each opportunity should contain relevant market data

**Example Response:**
```json
{
  "opportunities": [
    {
      "symbol": "AAPL",
      "score": 85.5,
      "pattern": "VIGL",
      "entry_point": 150.25,
      "target_price": 165.00
    }
  ],
  "scan_time": "2024-01-15T10:30:00Z",
  "total_scanned": 2500
}
```

### 3. Trading Recommendations

**Command:**
```bash
curl -s http://localhost:8000/recommendations
```

**Expected Response Shape:**
```bash
# Status Code: 200
# JSON Shape Validation:
jq -e '.recommendations and (.recommendations | type) == "array"'
```

**Required Fields:**
- `recommendations`: Array of trading recommendations

**Example Response:**
```json
{
  "recommendations": [
    {
      "symbol": "TSLA",
      "action": "BUY",
      "confidence": 0.87,
      "price_target": 245.00,
      "stop_loss": 210.00,
      "reasoning": "Strong VIGL pattern detected"
    }
  ],
  "generated_at": "2024-01-15T10:35:00Z"
}
```

### 4. Current Holdings

**Command:**
```bash
curl -s http://localhost:8000/holdings
```

**Expected Response Shape:**
```bash
# Status Code: 200
# JSON Shape Validation:
jq -e '.holdings and (.holdings | type) == "array"'
```

**Required Fields:**
- `holdings`: Array of current portfolio positions

**Example Response:**
```json
{
  "holdings": [
    {
      "symbol": "AAPL",
      "quantity": 100,
      "avg_cost": 145.50,
      "current_price": 150.25,
      "unrealized_pnl": 475.00,
      "position_value": 15025.00
    }
  ],
  "total_value": 25000.00,
  "total_pnl": 1250.00,
  "cash_balance": 5000.00
}
```

### 5. Shadow Trade Execution

**Command:**
```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL","action":"BUY","quantity":10,"mode":"shadow"}' \
  http://localhost:8000/trades/execute
```

**Expected Response Shape:**
```bash
# Status Code: 200
# JSON Shape Validation:
jq -e '.trade_id and .mode == "shadow" and .status'
```

**Required Fields:**
- `trade_id`: Unique identifier for the trade
- `mode`: Must be `"shadow"` for test trades
- `status`: Trade execution status

**Example Response:**
```json
{
  "trade_id": "shadow_12345",
  "mode": "shadow",
  "status": "executed",
  "symbol": "AAPL",
  "action": "BUY",
  "quantity": 10,
  "executed_price": 150.25,
  "timestamp": "2024-01-15T10:40:00Z"
}
```

## Failure Case Acceptance Criteria

### Environment Variable Validation

Each critical environment variable must cause the `/health` endpoint to return status 503 when missing:

#### Required Environment Variables:
- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY` 
- `ALPACA_BASE_URL`
- `CLAUDE_API_KEY`
- `POLYGON_API_KEY`

#### Test Pattern for Each Variable:

**Command:**
```bash
# Unset environment variable
unset ALPACA_API_KEY
# Test health endpoint
curl -s -w "\n%{http_code}" http://localhost:8000/health
```

**Expected Response:**
```bash
# Status Code: 503
# JSON Shape Validation:
jq -e '.status == "unhealthy" and .components and (.components.alpaca_connection == false)'
```

**Component Mapping:**
- `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `ALPACA_BASE_URL` → `components.alpaca_connection`
- `CLAUDE_API_KEY` → `components.claude_api`
- `POLYGON_API_KEY` → `components.market_data`

**Example Failure Response:**
```json
{
  "status": "unhealthy",
  "components": {
    "alpaca_connection": false,
    "claude_api": true,
    "market_data": true,
    "database": true
  },
  "error": "Missing required environment variable: ALPACA_API_KEY"
}
```

## Test Data Validation

### JSON Schema Validations

**Health Check Response:**
```bash
jq -e '
  .status and 
  .components and 
  (.components | keys | length > 0) and
  (.status == "healthy" or .status == "unhealthy")
'
```

**Discovery Response:**
```bash
jq -e '
  .opportunities and 
  (.opportunities | type) == "array" and
  (.opportunities[] | has("symbol") and has("score"))
'
```

**Recommendations Response:**
```bash
jq -e '
  .recommendations and 
  (.recommendations | type) == "array" and
  (.recommendations[] | has("symbol") and has("action") and has("confidence"))
'
```

**Holdings Response:**
```bash
jq -e '
  .holdings and 
  (.holdings | type) == "array" and
  has("total_value") and
  has("cash_balance")
'
```

**Trade Execution Response:**
```bash
jq -e '
  .trade_id and 
  .mode and 
  .status and 
  .symbol and 
  .action and 
  .quantity
'
```

## Performance Criteria

- All API endpoints must respond within 30 seconds
- Health check must respond within 5 seconds
- Shadow trades must complete without affecting real positions
- Discovery runs must complete and return results (may take longer for full scans)

## Security Criteria

- No sensitive environment variables should appear in API responses
- Shadow mode trades must not execute real orders
- Authentication headers must be properly validated (if implemented)
- Error messages must not expose internal system details

## Deployment Criteria

### Local Development
```bash
# All tests should pass locally
./scripts/smoke.sh
./scripts/failcases.sh
```

### Render Deployment
```bash
# Set production URL and run tests
BASE_URL=https://your-app.onrender.com ./scripts/smoke.sh
BASE_URL=https://your-app.onrender.com ./scripts/failcases.sh
```

### CI/CD Integration
```bash
# Exit codes for automation:
# 0 = All tests passed
# 1 = One or more tests failed

# Example GitHub Actions usage:
- name: Run Acceptance Tests
  run: |
    ./scripts/smoke.sh
    ./scripts/failcases.sh
```

## Troubleshooting

### Common Issues

**Connection Refused:**
```bash
# Check if service is running
curl -v http://localhost:8000/health
```

**JSON Parse Errors:**
```bash
# Validate JSON response manually
curl -s http://localhost:8000/health | jq '.'
```

**Environment Variable Issues:**
```bash
# Check required variables are set
echo $ALPACA_API_KEY
echo $CLAUDE_API_KEY
echo $POLYGON_API_KEY
```

**Timeout Issues:**
```bash
# Increase timeout for discovery operations
CURL_TIMEOUT=60 ./scripts/smoke.sh
```

### Log Analysis

Monitor application logs during test execution to ensure:
- No error messages during successful operations
- Appropriate error messages during failure case tests
- Performance metrics within acceptable ranges
- Security events logged appropriately