# AMC-TRADER MCP Integration Guide

## Overview
This guide explains how MCP (Model Context Protocol) data flows from Polygon.io through the backend to the frontend, enabling real-time explosive stock discovery and trading.

## Architecture Flow

```
Polygon.io MCP Functions → Backend Discovery Engine → API Endpoints → Frontend UI → Trade Execution
```

## 1. MCP Data Sources (Backend)

### Official Polygon MCP Integration
AMC-TRADER uses the official Polygon.io MCP server from https://github.com/polygon-io/mcp_polygon

### Available MCP Functions
The system uses these official Polygon MCP functions for enhanced data:

```python
# In backend/src/mcp_client_enhanced.py
- mcp__polygon__get_snapshot_all() - Market snapshots
- mcp__polygon__list_short_interest() - Short squeeze data
- mcp__polygon__list_ticker_news() - News sentiment
- mcp__polygon__get_aggs() - Price/volume aggregates
- mcp__polygon__list_dividends() - Corporate actions
- mcp__polygon__list_splits() - Stock splits
- mcp__polygon__get_snapshot_option() - Options flow (premium)
- mcp__polygon__list_trades() - Real-time trades (premium)
```

### 8-Pillar Scoring System
The enhanced discovery engine (`backend/src/discovery/polygon_explosive_discovery.py`) uses:

1. **Price Momentum** (20%) - Price changes and trends
2. **Volume Surge** (20%) - Relative volume spikes
3. **Float/Short** (15%) - Short interest for squeeze potential
4. **Catalyst** (15%) - News and events
5. **Sentiment** (10%) - News sentiment analysis
6. **Technical** (10%) - Technical indicators
7. **Options Flow** (5%) - Unusual options activity
8. **Realtime Momentum** (5%) - Live trade momentum

## 2. API Endpoints

### Discovery Endpoints
```javascript
// Main explosive discovery endpoint with MCP data
GET /discovery/discovery/explosive?limit=50

// Returns:
{
  "success": true,
  "data": [
    {
      "symbol": "QUBT",
      "score": 50.91,
      "price": 23.27,
      "price_change_pct": 26.81,
      "volume": 98555890,
      "action_tag": "watch",
      "confidence": 0.8,
      "subscores": {
        "volume_surge": 25.0,
        "price_momentum": 100,
        "news_catalyst": 20,
        "technical_breakout": 0
      }
    }
  ]
}
```

### Trade Execution Endpoint
```javascript
POST /trades/execute
{
  "symbol": "QUBT",
  "action": "BUY",
  "mode": "paper",  // or "live"
  "notional_usd": 100
}
```

## 3. Frontend Integration

### SqueezeMonitor Component
Located in `frontend/src/components/SqueezeMonitor.tsx`:

```typescript
// Fetch MCP-enhanced discovery data
const fetchData = async () => {
  const discoveryURL = 'https://amc-trader.onrender.com';
  const response = await fetch(`${discoveryURL}/discovery/discovery/explosive?limit=50`);
  const data = await response.json();

  // Map to frontend format
  const candidates = data.data.map(candidate => ({
    symbol: candidate.symbol,
    score: candidate.score,
    price: candidate.price,
    action_tag: candidate.action_tag,
    subscores: candidate.subscores,
    confidence: candidate.confidence
  }));

  setCandidates(candidates);
};

// Execute trades
const placeOrder = async (ticker: string) => {
  const payload = {
    symbol: ticker,
    action: "BUY",
    mode: "paper",
    notional_usd: 100
  };

  const result = await postJSON('/trades/execute', payload);
};
```

## 4. Data Flow Example

### Step 1: MCP Data Collection
```python
# Backend collects real-time data from Polygon
short_data = await mcp__polygon__list_short_interest(ticker="QUBT")
news_data = await mcp__polygon__list_ticker_news(ticker="QUBT")
price_data = await mcp__polygon__get_aggs(ticker="QUBT", timespan="day")
```

### Step 2: Scoring & Analysis
```python
# Calculate 8-pillar score
score = engine.calculate_explosive_score(
    ticker="QUBT",
    short_data=short_data,
    news_data=news_data,
    price_data=price_data
)
# Result: QUBT scores 50.91/100
```

### Step 3: API Response
```json
GET /discovery/discovery/explosive

{
  "data": [
    {
      "symbol": "QUBT",
      "score": 50.91,
      "price": 23.27,
      "action_tag": "watch"
    }
  ]
}
```

### Step 4: Frontend Display
The SqueezeMonitor displays candidates in categories:
- 🚀 **Trade Ready** - Score ≥ 75, immediate buy enabled
- 📊 **Watchlist** - Score 50-74, monitoring for entry
- 🔍 **Monitoring** - Score < 50, tracking for changes

### Step 5: Trade Execution
When user clicks "Buy Paper":
1. Frontend sends POST to `/trades/execute`
2. Backend validates and executes via Alpaca API
3. Position appears in Holdings view

## 5. Real-Time Updates

### WebSocket Integration
```javascript
// Frontend WebSocket connection
const socket = io(WS_URL, {
  path: '/v1/stream/socket.io'
});

socket.on('explosive', (data) => {
  // Real-time explosive candidate alert
  updateCandidates(data);
});

socket.on('candidate', (data) => {
  // New discovery candidate
  addCandidate(data);
});
```

## 6. Current Live Candidates

As of the last run, the system is discovering:
- **QUBT** - Quantum computing stock, score 50.91
- **BBAI** - AI analytics company, score 42.67

These are real stocks found using MCP-enhanced discovery with:
- Live price data from Polygon
- Short interest analysis
- News sentiment scoring
- Volume surge detection
- Technical breakout patterns

## 7. Testing the Integration

### Backend Test
```bash
# Test explosive discovery
curl -s "https://amc-trader.onrender.com/discovery/discovery/explosive?limit=10" | jq .

# Test trade execution
curl -s -X POST "https://amc-trader.onrender.com/trades/execute" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"QUBT","action":"BUY","mode":"paper","notional_usd":100}' | jq .
```

### Frontend Test
1. Navigate to https://amc-frontend.onrender.com/squeeze
2. Should see QUBT, BBAI in the monitor
3. Click "Buy Paper" to test trade execution

## 8. Deployment

### Environment Variables Required
```bash
# Backend (.env)
POLYGON_API_KEY=your_key
ALPACA_API_KEY=your_key
ALPACA_API_SECRET=your_secret
REDIS_URL=redis://...
DATABASE_URL=postgresql://...
```

### Deployment Commands
```bash
# Deploy backend changes
git add -A
git commit -m "Update discovery system"
git push

# Frontend auto-deploys from main branch
# Check deployment at https://amc-frontend.onrender.com
```

## 9. Troubleshooting

### MCP Integration Issues
1. **MCP Functions Not Available**: Ensure you're running in Claude Code environment or Render deployment
2. **API Rate Limits**: Polygon.io API has rate limits; check console for HTTP 429 errors
3. **Missing API Key**: Verify `POLYGON_API_KEY` environment variable is set

### If no candidates appear:
1. Check backend health: `curl https://amc-trader.onrender.com/health`
2. Verify discovery endpoint: `curl https://amc-trader.onrender.com/discovery/discovery/explosive`
3. Check browser console for errors
4. Verify WebSocket connection in Network tab
5. Check MCP availability: Look for "MCP functions available" in backend logs

### If trades fail:
1. Check Alpaca API credentials
2. Verify account has sufficient buying power
3. Check if market is open
4. Review trade payload in Network tab

## 10. Future Enhancements

### Planned MCP Integrations:
- Real-time options flow analysis
- Institutional ownership changes
- Analyst rating changes
- Social media sentiment
- Dark pool activity
- Earnings whisper numbers

This completes the MCP integration, connecting Polygon.io data through the backend discovery engine to the frontend UI with full buy functionality.