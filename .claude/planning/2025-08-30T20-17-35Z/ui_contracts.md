---
run_id: 2025-08-30T20-17-35Z
version: 1
---

# AMC-TRADER UI Contracts

## Component Fetch Patterns

### TopRecommendations Component
**File**: `frontend/src/components/TopRecommendations.tsx:22-74`
**Fetches**: `GET /discovery/contenders`
**Polling**: 60 seconds (`setInterval(loadRecommendations, 60000)`)
**TypeScript Interface**:
```typescript
type Recommendation = {
  symbol: string;
  thesis: string;
  current_price: number;
  target_price: number;
  confidence: number;
  score: number;
};
```

### SqueezeMonitor Component
**File**: `frontend/src/components/SqueezeMonitor.tsx:42-80`
**Fetches**: `GET /discovery/squeeze-candidates`
**Polling**: 30 seconds (`setInterval(loadSqueezeOpportunities, 30000)`)
**TypeScript Interface**:
```typescript
interface SqueezeOpportunity {
  symbol: string;
  squeeze_score: number;
  volume_spike: number;
  short_interest: number;
  price: number;
  pattern_type?: string;
  confidence?: number;
  detected_at: string;
}
```

### Portfolio Components
**Fetches**: `GET /portfolio/holdings` and `GET /portfolio/enhanced`
**Polling**: Variable based on component needs
**Data Processing**: Enhanced with thesis generation and P&L calculations

## API Client Configuration

### Base Configuration
**File**: `frontend/src/lib/api.ts`
**Base URL**: Determined by `API_BASE` from config
**Error Handling**: JSON parsing with fallback messages
**Helper Function**: `getJSON<T>(url: string): Promise<T>`

### Request/Response Flow
1. **Component**: Calls `getJSON()` with endpoint
2. **API Client**: Adds base URL, handles fetch
3. **Error Handling**: Catches network/parsing errors
4. **Type Safety**: Returns typed data matching interfaces

## Real-Time Update Strategy

### Discovery Data Updates
- **Primary**: TopRecommendations polls every 60s
- **Secondary**: SqueezeMonitor polls every 30s  
- **Rationale**: Discovery runs every 5 minutes, so polling captures all updates

### Portfolio Data Updates
- **Trigger**: User actions (trade execution, manual refresh)
- **Frequency**: On-demand rather than polling
- **Rationale**: Position changes are infrequent and user-initiated

### Trade Execution Flow
1. **TradeModal**: User inputs order details
2. **Validation**: Frontend validates required fields
3. **Submission**: `POST /trades/execute` with order data
4. **Response**: Success/error handling with user feedback
5. **Refresh**: Trigger portfolio and discovery updates

## Data Transformation Patterns

### Discovery Results Processing
**Location**: `TopRecommendations.tsx:27-63`
```typescript
const mapped = data.map((rec: any) => {
  const currentPrice = rec.price || rec.current_price || 0;
  // Calculate realistic targets based on ATR and momentum
  const atrPct = rec.factors?.atr_percent || 4.0;
  const viglScore = rec.factors?.vigl_similarity || 0;
  const targetMultiplier = 1 + (atrPct / 100) * Math.min(viglScore * 1.2, 1.0);
  const targetPrice = currentPrice * targetMultiplier;
  
  return {
    symbol: rec.symbol || "N/A",
    thesis: rec.thesis || "Technical signals suggest upward momentum potential.",
    current_price: currentPrice,
    target_price: targetPrice,
    confidence: Math.round((rec.confidence || rec.score || 0.75) * 100),
    score: rec.score || 75
  };
});
```

### Squeeze Alert Categorization
**Location**: `SqueezeMonitor.tsx:89-95`
```typescript
const categorizeOpportunities = (opportunities: SqueezeOpportunity[]) => {
  const critical = opportunities.filter(opp => opp.squeeze_score >= 0.70);
  const developing = opportunities.filter(opp => 
    opp.squeeze_score >= 0.40 && opp.squeeze_score < 0.70
  );
  const early = opportunities.filter(opp => 
    opp.squeeze_score >= 0.25 && opp.squeeze_score < 0.40
  );
  return { critical, developing, early };
};
```

## Error Handling Patterns

### Network Error Recovery
- **Retry Strategy**: Manual retry buttons in error states
- **User Feedback**: Clear error messages with actionable steps
- **Graceful Degradation**: Show cached data when possible

### Data Validation
- **Frontend**: Type checking with TypeScript interfaces
- **Runtime**: Null checks and fallback values
- **User Input**: Form validation before API submission

## Performance Optimization

### Polling Strategy
- **Staggered Intervals**: Different components poll at different rates
- **Conditional Updates**: Only update UI when data actually changes
- **Background Updates**: Continue polling when components unmounted

### Memory Management  
- **Cleanup**: Clear intervals on component unmount
- **State Management**: Minimal state, prefer API as source of truth
- **Caching**: Rely on browser HTTP cache and API-level Redis cache