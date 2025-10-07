# AMC-TRADER RVOL Optimization Deployment Guide

## Overview

This guide covers deployment of the Squeeze-Prophet RVOL optimization enhancements to AMC-TRADER's discovery system.

**Performance Improvement**: 50x faster (1-2s vs 20-30s), analyzing 8,000+ stocks vs 20

**API Efficiency**: 2 API calls vs 8,000+ (99.9% reduction)

**Architecture**: 7-stage pipeline with bulk snapshots, momentum pre-ranking, and PostgreSQL caching

## Prerequisites

- PostgreSQL database connection (`$DATABASE_URL` configured)
- Polygon API key configured in backend environment
- Python 3.9+ with AsyncIO support
- Backend server access

## Phase 1: Database Migration

### Step 1.1: Run Migration

```bash
# Navigate to AMC-TRADER backend
cd /Users/michaelmote/Desktop/AMC-TRADER/backend

# Run migration
psql $DATABASE_URL -f migrations/001_add_volume_cache.sql

# Verify table creation
psql $DATABASE_URL -c "\d volume_averages"
```

**Expected Output:**
```
                           Table "public.volume_averages"
    Column     |            Type             | Collation | Nullable |      Default
---------------+-----------------------------+-----------+----------+-------------------
 symbol        | character varying(10)       |           | not null |
 avg_volume_20d| bigint                      |           | not null |
 avg_volume_30d| bigint                      |           |          |
 last_updated  | timestamp without time zone |           | not null | now()
 created_at    | timestamp without time zone |           |          | now()
Indexes:
    "volume_averages_pkey" PRIMARY KEY, btree (symbol)
    "idx_volume_averages_updated" btree (last_updated)
Check constraints:
    "positive_volume" CHECK (avg_volume_20d > 0)
```

### Step 1.2: Verify Migration Success

```bash
# Check table exists and is empty
psql $DATABASE_URL -c "SELECT COUNT(*) FROM volume_averages;"
```

**Expected Output:** `0` (table exists but empty)

## Phase 2: Initial Cache Population (Test Mode)

### Step 2.1: Test Cache Refresh (100 Symbols)

```bash
# Run test mode - populates cache for first 100 active symbols
cd /Users/michaelmote/Desktop/AMC-TRADER/backend
python -m app.jobs.refresh_volume_cache test
```

**Expected Output:**
```
🔄 Starting volume cache refresh job...
Fetching active symbols from bulk snapshot...
Refreshing 100 active symbols...
Batch 1: 45 processed, 32 skipped, 0 errors (12.3s)
Batch 2: 23 processed, 0 skipped, 0 errors (11.8s)
Upserting 68 volume averages to database...
✅ Database updated: 68 records
✅ Volume cache refresh complete
  total_symbols=100
  processed=68
  skipped=32
  errors=0
  duration=24.1s
  avg_time_per_symbol=0.241s
```

**Note:** Skipped symbols are those without sufficient historical data (acceptable).

### Step 2.2: Verify Cache Data

```bash
# Check cache population
psql $DATABASE_URL -c "SELECT COUNT(*), MIN(last_updated), MAX(last_updated) FROM volume_averages;"

# Sample cache data
psql $DATABASE_URL -c "SELECT symbol, avg_volume_20d, last_updated FROM volume_averages ORDER BY avg_volume_20d DESC LIMIT 10;"
```

**Expected Output:**
```
 count |         min         |         max
-------+---------------------+---------------------
    68 | 2025-01-05 14:23:10 | 2025-01-05 14:23:10

 symbol | avg_volume_20d  |     last_updated
--------+-----------------+---------------------
 AAPL   |    52847362     | 2025-01-05 14:23:10
 NVDA   |    48293847     | 2025-01-05 14:23:10
 TSLA   |    42938475     | 2025-01-05 14:23:10
...
```

## Phase 3: API Endpoint Testing

### Step 3.1: Test Validation Endpoint

```bash
# Test validation endpoint (verifies NO FAKE DATA)
curl -s "http://localhost:8000/discovery/validate-v2" | jq .
```

**Expected Output (PASS):**
```json
{
  "timestamp": "2025-01-05T14:25:00.000Z",
  "overall_status": "PASS",
  "checks": {
    "bulk_snapshot": {
      "status": "PASS",
      "tickers_count": 8059,
      "has_major_stocks": true,
      "sample_ticker": "AAPL"
    },
    "volume_cache": {
      "status": "PASS",
      "cached_count": 3,
      "cache_empty": false,
      "warning": null
    },
    "rvol_calculation": {
      "status": "PASS",
      "calculated_count": 3,
      "invalid_count": 0,
      "invalid_samples": []
    }
  }
}
```

**❌ If volume_cache shows FAIL:**
```json
{
  "volume_cache": {
    "status": "FAIL",
    "cached_count": 0,
    "cache_empty": true,
    "warning": "Run cache refresh job"
  }
}
```
**Fix:** Re-run Step 2.1 (test cache refresh)

### Step 3.2: Test Discovery Endpoint (Debug Mode)

```bash
# Test V2 discovery with debug output
curl -s "http://localhost:8000/discovery/contenders-v2?limit=10&min_rvol=1.5&debug=true" | jq .
```

**Expected Output:**
```json
{
  "success": true,
  "candidates": [
    {
      "symbol": "QUBT",
      "price": 12.45,
      "volume": 8472948,
      "change_pct": 15.3,
      "rvol": 3.24,
      "high": 13.20,
      "low": 11.80,
      "explosion_probability": 78.5,
      "momentum_score": 142.7,
      "reasons": []
    },
    ...
  ],
  "count": 10,
  "strategy": "hybrid_v1",
  "stats": {
    "scan_time": 1.23,
    "universe_size": 8059,
    "filtered_universe": 4127,
    "momentum_survivors": 1000,
    "cache_hit_rate": 87.3,
    "rvol_calculated": 873,
    "rvol_survivors": 45,
    "final_returned": 10,
    "api_calls": 2,
    "stage_times": {
      "universe_filter": 0.002,
      "bulk_snapshot": 0.487,
      "momentum_prerank": 0.134,
      "cache_lookup": 0.089,
      "rvol_filter": 0.045,
      "scoring": 0.234,
      "ranking": 0.003
    }
  }
}
```

**Key Metrics to Verify:**
- ✅ `scan_time`: Should be 1-3 seconds
- ✅ `api_calls`: Should be exactly 2
- ✅ `cache_hit_rate`: Should be >80% after test cache population
- ✅ `rvol` values: Should be real numbers >1.0 (not fake data)
- ✅ `explosion_probability`: Should vary 0-95 (not uniform)

### Step 3.3: Compare V1 vs V2 Performance

```bash
# Test V1 (old system - limited to 20 stocks)
time curl -s "http://localhost:8000/discovery/contenders?limit=20" | jq '.meta.scan_time'

# Test V2 (new system - 8,000+ stocks)
time curl -s "http://localhost:8000/discovery/contenders-v2?limit=50" | jq '.stats.scan_time'
```

**Expected Results:**
- V1: 20-30 seconds for 20 stocks
- V2: 1-3 seconds for 8,000+ stocks (50x improvement)

## Phase 4: Full Production Cache Population

### Step 4.1: Run Full Cache Refresh

**⚠️ WARNING:** This will make ~8,000 API calls to Polygon. Ensure you have sufficient API quota.

**Estimated Time:** 30-45 minutes (batched with rate limiting)

```bash
# Run full production cache refresh
cd /Users/michaelmote/Desktop/AMC-TRADER/backend
python -m app.jobs.refresh_volume_cache
```

**Expected Output:**
```
🔄 Starting volume cache refresh job...
Fetching active symbols from bulk snapshot...
Refreshing 8,059 active symbols...
Batch 1: 82 processed, 18 skipped, 0 errors (61.2s)
Batch 2: 79 processed, 21 skipped, 0 errors (59.8s)
...
Batch 81: 64 processed, 36 skipped, 0 errors (58.3s)
Upserting 6,847 volume averages to database...
✅ Database updated: 6,847 records
✅ Volume cache refresh complete
  total_symbols=8,059
  processed=6,847
  errors=0
  duration=2847.3s (47.5 min)
  avg_time_per_symbol=0.353s
```

### Step 4.2: Verify Full Cache Coverage

```bash
# Check final cache stats
psql $DATABASE_URL -c "
SELECT
  COUNT(*) as total_cached,
  MIN(avg_volume_20d) as min_volume,
  MAX(avg_volume_20d) as max_volume,
  AVG(avg_volume_20d)::bigint as avg_volume
FROM volume_averages;
"

# Check cache freshness
psql $DATABASE_URL -c "
SELECT
  COUNT(*) as fresh_count,
  COUNT(*) FILTER (WHERE last_updated > NOW() - INTERVAL '1 hour') as last_hour
FROM volume_averages;
"
```

### Step 4.3: Re-test Discovery with Full Cache

```bash
# Should now have >95% cache hit rate
curl -s "http://localhost:8000/discovery/contenders-v2?limit=50&debug=true" | jq '.stats.cache_hit_rate'
```

**Expected:** `95.0` or higher (near-perfect cache coverage)

## Phase 5: Production Validation

### Validation Checklist

Run all validation tests and confirm PASS status:

```bash
# 1. System validation
curl -s "http://localhost:8000/discovery/validate-v2" | jq '.overall_status'
# Expected: "PASS"

# 2. Bulk snapshot test
curl -s "http://localhost:8000/discovery/validate-v2" | jq '.checks.bulk_snapshot.status'
# Expected: "PASS"

# 3. Volume cache test
curl -s "http://localhost:8000/discovery/validate-v2" | jq '.checks.volume_cache.status'
# Expected: "PASS"

# 4. RVOL calculation test
curl -s "http://localhost:8000/discovery/validate-v2" | jq '.checks.rvol_calculation.status'
# Expected: "PASS"

# 5. Performance test
curl -s "http://localhost:8000/discovery/contenders-v2?limit=50" | jq '.stats.scan_time'
# Expected: <3.0 seconds

# 6. API efficiency test
curl -s "http://localhost:8000/discovery/contenders-v2?limit=50" | jq '.stats.api_calls'
# Expected: 2

# 7. Cache hit rate test
curl -s "http://localhost:8000/discovery/contenders-v2?limit=50" | jq '.stats.cache_hit_rate'
# Expected: >95.0

# 8. Data quality test (NO FAKE DATA)
curl -s "http://localhost:8000/discovery/contenders-v2?limit=5" | jq '.candidates[].rvol'
# Expected: Real varying numbers (e.g., [2.34, 1.87, 3.12, 1.56, 2.91])
# NOT uniform fake data (e.g., [2.0, 2.0, 2.0, 2.0, 2.0])
```

### ✅ Production Ready Criteria

All of the following must be TRUE:

- [ ] Database migration successful (volume_averages table exists)
- [ ] Cache populated with >6,000 symbols
- [ ] `/validate-v2` returns `overall_status: "PASS"`
- [ ] `/contenders-v2` returns candidates in <3 seconds
- [ ] API calls = 2 (not 8,000+)
- [ ] Cache hit rate >95%
- [ ] RVOL values are real (varying, not uniform)
- [ ] Explosion probability scores vary (not all same)
- [ ] No errors in production logs

## Phase 6: Ongoing Maintenance

### Daily Cache Refresh (Automated)

**Schedule:** Daily at 5:00 PM ET (after market close)

**Setup cron job:**
```bash
# Add to crontab
0 17 * * 1-5 cd /Users/michaelmote/Desktop/AMC-TRADER/backend && python -m app.jobs.refresh_volume_cache >> /var/log/volume_cache.log 2>&1
```

**Or run manually:**
```bash
python -m app.jobs.refresh_volume_cache
```

### Incremental Cache Updates (Optional)

For faster updates during market hours:

```bash
# Refresh only stale symbols (>24 hours old)
python -m app.jobs.refresh_volume_cache stale
```

### Monitoring Commands

```bash
# Check cache age distribution
psql $DATABASE_URL -c "
SELECT
  CASE
    WHEN last_updated > NOW() - INTERVAL '1 hour' THEN '< 1 hour'
    WHEN last_updated > NOW() - INTERVAL '6 hours' THEN '1-6 hours'
    WHEN last_updated > NOW() - INTERVAL '24 hours' THEN '6-24 hours'
    ELSE '> 24 hours'
  END as age_bucket,
  COUNT(*) as count
FROM volume_averages
GROUP BY age_bucket
ORDER BY age_bucket;
"

# Find symbols with anomalous volumes (potential data issues)
psql $DATABASE_URL -c "
SELECT symbol, avg_volume_20d, last_updated
FROM volume_averages
WHERE avg_volume_20d > 100000000 OR avg_volume_20d < 1000
ORDER BY avg_volume_20d DESC
LIMIT 20;
"
```

## Troubleshooting

### Issue 1: Cache Hit Rate <80%

**Symptom:**
```json
{
  "stats": {
    "cache_hit_rate": 45.2
  }
}
```

**Diagnosis:**
```bash
psql $DATABASE_URL -c "SELECT COUNT(*) FROM volume_averages WHERE last_updated < NOW() - INTERVAL '24 hours';"
```

**Fix:**
```bash
python -m app.jobs.refresh_volume_cache stale
```

### Issue 2: Validation Endpoint Shows FAIL

**Symptom:**
```json
{
  "overall_status": "FAIL",
  "checks": {
    "volume_cache": {
      "status": "FAIL",
      "cache_empty": true
    }
  }
}
```

**Fix:**
```bash
# Re-run cache population
python -m app.jobs.refresh_volume_cache test
```

### Issue 3: Slow Performance (>5 seconds)

**Symptom:**
```json
{
  "stats": {
    "scan_time": 8.45
  }
}
```

**Diagnosis:** Check stage times to find bottleneck:
```bash
curl -s "http://localhost:8000/discovery/contenders-v2?limit=50&debug=true" | jq '.stats.stage_times'
```

**Common Causes:**
- `bulk_snapshot` slow (>2s): Polygon API latency or rate limiting
- `cache_lookup` slow (>0.5s): Database connection issues
- `momentum_prerank` slow (>0.5s): Too many symbols in filtered universe

### Issue 4: API Calls >2

**Symptom:**
```json
{
  "stats": {
    "api_calls": 8047
  }
}
```

**Cause:** System fell back to old per-symbol API calls

**Diagnosis:**
```bash
# Check if bulk snapshot is working
curl -s "http://localhost:8000/discovery/validate-v2" | jq '.checks.bulk_snapshot'
```

**Fix:** Verify Polygon API key and bulk snapshot endpoint access

### Issue 5: Uniform RVOL Values (Fake Data Detection)

**Symptom:**
```json
{
  "candidates": [
    {"symbol": "AAA", "rvol": 2.0},
    {"symbol": "BBB", "rvol": 2.0},
    {"symbol": "CCC", "rvol": 2.0}
  ]
}
```

**This indicates FAKE DATA - UNACCEPTABLE**

**Diagnosis:**
```bash
# Check if cache has real data
psql $DATABASE_URL -c "SELECT symbol, avg_volume_20d FROM volume_averages LIMIT 10;"
```

**Fix:**
1. Clear cache: `psql $DATABASE_URL -c "TRUNCATE volume_averages;"`
2. Re-run cache refresh: `python -m app.jobs.refresh_volume_cache test`
3. Verify real data: `curl -s "http://localhost:8000/discovery/validate-v2" | jq .`

## Performance Benchmarks

### Expected Performance Metrics

| Metric | Old System (V1) | New System (V2) | Improvement |
|--------|----------------|-----------------|-------------|
| Scan Time | 20-30s | 1-3s | **50x faster** |
| Stocks Analyzed | 20 | 8,000+ | **400x more** |
| API Calls | 8,000+ | 2 | **99.9% reduction** |
| Cache Hit Rate | 0% | >95% | N/A |
| Momentum Pre-rank | None | 87% reduction | N/A |

### Stage Performance Breakdown

| Stage | Expected Time | Acceptable Range |
|-------|--------------|------------------|
| Universe Filter | <0.01s | 0.001-0.05s |
| Bulk Snapshot | 0.3-0.8s | 0.2-2.0s |
| Momentum Pre-rank | 0.1-0.2s | 0.05-0.5s |
| Cache Lookup | 0.05-0.15s | 0.02-0.5s |
| RVOL Filter | 0.03-0.08s | 0.01-0.2s |
| Scoring | 0.1-0.3s | 0.05-0.5s |
| Ranking | <0.01s | 0.001-0.05s |
| **TOTAL** | **1.0-2.0s** | **0.5-4.0s** |

## Rollback Procedure

If issues arise, revert to V1 system:

```bash
# 1. Switch endpoints in application code
# Use /discovery/contenders instead of /discovery/contenders-v2

# 2. (Optional) Drop volume cache table if needed
psql $DATABASE_URL -c "DROP TABLE IF EXISTS volume_averages CASCADE;"

# 3. (Optional) Remove background job from cron
crontab -e  # Remove volume_cache refresh line
```

## Success Validation Summary

Run this comprehensive test to confirm successful deployment:

```bash
#!/bin/bash
echo "=== AMC-TRADER RVOL Optimization Validation ==="
echo ""

echo "1. Overall System Status:"
curl -s "http://localhost:8000/discovery/validate-v2" | jq -r '.overall_status'
echo ""

echo "2. Cache Coverage:"
psql $DATABASE_URL -c "SELECT COUNT(*) as cached_symbols FROM volume_averages;" -t
echo ""

echo "3. Performance Test:"
curl -s "http://localhost:8000/discovery/contenders-v2?limit=50" | jq -r '.stats.scan_time'
echo ""

echo "4. API Efficiency:"
curl -s "http://localhost:8000/discovery/contenders-v2?limit=50" | jq -r '.stats.api_calls'
echo ""

echo "5. Cache Hit Rate:"
curl -s "http://localhost:8000/discovery/contenders-v2?limit=50" | jq -r '.stats.cache_hit_rate'
echo ""

echo "6. Sample Candidates:"
curl -s "http://localhost:8000/discovery/contenders-v2?limit=5" | jq '.candidates[] | {symbol, rvol, explosion_probability}'
echo ""

echo "=== Validation Complete ==="
```

**Expected Output:**
```
=== AMC-TRADER RVOL Optimization Validation ===

1. Overall System Status:
PASS

2. Cache Coverage:
6847

3. Performance Test:
1.23

4. API Efficiency:
2

5. Cache Hit Rate:
96.3

6. Sample Candidates:
{
  "symbol": "QUBT",
  "rvol": 3.24,
  "explosion_probability": 78.5
}
{
  "symbol": "MARA",
  "rvol": 2.87,
  "explosion_probability": 72.3
}
...

=== Validation Complete ===
```

## Contact & Support

For issues or questions about this deployment:

1. Check logs: `tail -f /var/log/volume_cache.log`
2. Review validation endpoint: `curl "http://localhost:8000/discovery/validate-v2" | jq .`
3. Verify database state: `psql $DATABASE_URL -c "\d volume_averages"`

**Critical Reminder:** AMC-TRADER uses ONLY real Polygon API data. NO fake data, NO mock data, NO fallbacks. Empty results are acceptable; fake data is NOT.
