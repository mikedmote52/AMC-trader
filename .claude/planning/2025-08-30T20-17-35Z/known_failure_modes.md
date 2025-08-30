---
run_id: 2025-08-30T20-17-35Z
version: 1
---

# AMC-TRADER Known Failure Modes

## Discovery Pipeline Issues

### Symptom: No recommendations showing on UI
**Likely Causes**:
- Discovery job not running or failing
- Redis connection issues
- Polygon API rate limiting
- Universe file empty or corrupted

**Quick Checks**:
```bash
# Check Redis connection and data
redis-cli GET "amc:discovery:contenders.latest"

# Verify discovery job logs
tail -f logs/discovery.log

# Test Polygon API
curl "https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/2025-08-30?apikey=$POLYGON_API_KEY"

# Check universe file
wc -l data/universe.txt
```

### Symptom: Discovery finds no opportunities despite market activity
**Likely Causes**:
- Thresholds too restrictive for current market regime
- VIGL pattern matching too narrow
- Price caps excluding valid candidates
- Volume spike calculations incorrect

**Quick Checks**:
```bash
# Check discovery trace data
curl localhost:8000/discovery/explain | jq '.trace.rejections'

# Review current thresholds
grep -E "(PRICE_CAP|VOLUME_MIN|VIGL_)" backend/src/jobs/discover.py

# Test with relaxed mode
python backend/src/jobs/discover.py --relaxed --dry-run
```

## API Response Issues

### Symptom: UI shows "Loading..." indefinitely
**Likely Causes**:
- FastAPI server down or unresponsive
- CORS configuration blocking requests
- Database connection pool exhausted
- API endpoint returning malformed JSON

**Quick Checks**:
```bash
# Test API health
curl localhost:8000/health

# Check specific endpoint
curl localhost:8000/discovery/contenders

# Verify CORS headers
curl -H "Origin: http://localhost:5173" -v localhost:8000/discovery/contenders

# Check API logs
tail -f logs/api.log
```

### Symptom: Trade execution fails with unclear errors
**Likely Causes**:
- Alpaca API credentials invalid
- Price cap guardrails blocking orders
- Insufficient buying power
- Market closed for trading

**Quick Checks**:
```bash
# Test Alpaca connection
curl -H "APCA-API-KEY-ID: $ALPACA_API_KEY" -H "APCA-API-SECRET-KEY: $ALPACA_SECRET_KEY" https://paper-api.alpaca.markets/v2/account

# Check guardrail settings
curl localhost:8000/defaults/AAPL

# Verify account status
curl localhost:8000/portfolio/summary

# Test paper trade
curl -X POST localhost:8000/trades/execute -H "Content-Type: application/json" -d '{"symbol":"AAPL","action":"BUY","mode":"shadow","qty":1}'
```

## Data Consistency Issues

### Symptom: Stale data persisting in UI after updates
**Likely Causes**:
- Redis TTL too long for current needs
- Frontend caching API responses
- Discovery job stuck or crashing
- Browser cache interfering

**Quick Checks**:
```bash
# Force Redis cache refresh
redis-cli DEL "amc:discovery:contenders.latest"

# Check discovery job status
ps aux | grep discover

# Verify cache headers
curl -v localhost:8000/discovery/contenders | grep -i cache

# Clear browser cache or use incognito mode
```

### Symptom: Portfolio P&L calculations incorrect
**Likely Causes**:
- Alpaca position sync timing issues  
- Price data staleness from Polygon
- Currency/decimal precision errors
- Thesis generator using wrong entry prices

**Quick Checks**:
```bash
# Compare Alpaca vs internal data
curl localhost:8000/portfolio/holdings | jq '.[0]'
curl -H "APCA-API-KEY-ID: $ALPACA_API_KEY" -H "APCA-API-SECRET-KEY: $ALPACA_SECRET_KEY" https://paper-api.alpaca.markets/v2/positions

# Check price data freshness
curl "https://api.polygon.io/v2/aggs/ticker/AAPL/prev?apikey=$POLYGON_API_KEY"

# Verify calculation logic
grep -A 10 "unrealized_pl" backend/src/services/portfolio.py
```

## Performance Degradation

### Symptom: Slow API responses (>2 seconds)
**Likely Causes**:
- Database connection pool exhaustion
- Polygon API rate limiting or timeouts
- Redis memory pressure
- Inefficient SQL queries

**Quick Checks**:
```bash
# Check API response times
time curl localhost:8000/discovery/contenders

# Monitor Redis memory
redis-cli INFO memory

# Check database connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# Profile discovery job
python -m cProfile backend/src/jobs/discover.py --dry-run
```

### Symptom: Frontend updates laggy or missed
**Likely Causes**:
- Polling intervals too long
- JavaScript event loop blocking
- Network connectivity issues
- Component re-render loops

**Quick Checks**:
```bash
# Monitor network requests in dev tools
# Check console for JavaScript errors
# Verify polling intervals in component code
grep -r "setInterval" frontend/src/components/

# Test with shorter polling intervals
# Temporarily set to 5s for debugging
```

## Environment Issues

### Symptom: Different behavior between development and production  
**Likely Causes**:
- Environment variable mismatches
- Database schema differences
- API base URL configuration
- Build process differences

**Quick Checks**:
```bash
# Compare environment variables
env | grep -E "(DATABASE_URL|REDIS_URL|POLYGON_API_KEY|ALPACA_)"

# Check API configuration
grep -r "API_BASE" frontend/src/

# Verify build artifacts
ls -la frontend/dist/

# Test production API endpoints
curl https://amc-trader.onrender.com/health
```

## Recovery Procedures

### Full System Reset
```bash
# Clear all caches
redis-cli FLUSHALL

# Restart discovery job
pkill -f discover.py
python backend/src/jobs/discover.py &

# Restart API server
sudo systemctl restart amc-trader-api

# Clear browser cache and hard refresh
```

### Data Integrity Check
```bash
# Verify all components healthy
curl localhost:8000/health | jq '.components'

# Test end-to-end flow
python scripts/system_test.py

# Validate discovery output
curl localhost:8000/discovery/contenders | jq 'length'
```