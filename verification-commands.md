# AMC-TRADER Production Fixes Verification

## Browser Console Test
Open browser console and run:
```javascript
fetch("https://amc-trader.onrender.com/discovery/contenders")
  .then(r => r.json())
  .then(d => console.log(d.length || d.count || 0, d[0] || d.data?.[0]))
```

Expected: Should show number and an object with ticker/score

## Deep Link Test
1. Open: https://amc-frontend.onrender.com/squeeze
2. Check that page loads (no 404)
3. Check Network tab for GET to https://amc-trader.onrender.com/discovery/contenders
4. Expected: 200 status, cards showing even for scores ~46.5 with "Monitoring" label

## Test Results Expected
- ✅ No 404 on /squeeze (SPA rewrite works)
- ✅ Network requests hit absolute backend URL (not relative /squeeze/discovery/...)
- ✅ "System Online" badge appears after ping()
- ✅ Contenders render even when score < 70, sorted by score desc
- ✅ Cards show "Monitoring" action for scores ~46.5

## Manual Verification
Run this HTML test file to verify API integration:
```bash
open test-frontend-api.html
```

## Backend Status Check
```bash
curl -s "https://amc-trader.onrender.com/health" | jq .
curl -s "https://amc-trader.onrender.com/_routes" | grep discovery
```

## Success Criteria
1. Frontend loads on deep links like /squeeze
2. API calls use absolute URLs to backend
3. System Online/Offline status works
4. All candidates display regardless of score
5. No score-based filtering in UI
6. Proper error handling and fallbacks