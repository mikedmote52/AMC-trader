# AlphaStack 4.1 Discovery Engine - Canonical Output Contract

## Executive Summary

This document defines the **exact output format** that AlphaStack 4.1 Discovery Engine produces after Stage 5 completion. All backend/UI systems must parse according to this canonical schema.

---

## 1. SCORING ENGINE EVENT FORMAT & FREQUENCY

### Event Emission Pattern
```javascript
// Discovery runs emit a single atomic result after Stage 5
// Frequency: On-demand (API triggered) | Batch (scheduled jobs)
// Event Type: "discovery_result"
// Schema Version: "4.1"
```

### Primary Output Schema
```typescript
interface AlphaStack41Response {
  // Metadata
  schema: "4.1";                    // Fixed version identifier
  regime: string;                   // "normal" | "high_vol" | "squeeze"
  status: "live" | "closed" | "stale_data";
  timestamp: string;                // ISO format
  execution_time_sec: number;       // Pipeline execution time

  // Core Results
  items: CandidateScore[];          // Main scored candidates
  explosive_top: ExplosiveCandidate[]; // EGS/SER filtered shortlist
  count: number;                    // items.length

  // System Health & Monitoring
  system_health: SystemHealth;
  pipeline_stats: PipelineStats;
  telemetry: TelemetryMetrics;
}
```

---

## 2. HARD GUARDS vs SOFT SCORES

### Hard Guards (Must Pass Before Scoring)
**Located in FilteringPipeline class - NEVER bypassed**

```typescript
interface HardGuards {
  // Price bounds (absolutely enforced)
  price_min: 0.10,         // Below = rejected
  price_max: 100.00,       // Above = rejected

  // Volume requirements (absolute minimums)
  min_dollar_vol_m: 5.0,   // $5M daily dollar volume minimum

  // Microstructure (liquidity requirements)
  effective_spread_bps_max: 60,    // Max 60bps spread
  value_traded_min: 1_000_000,     // Min $1M value traded

  // Price point exclusions
  price_floor: 1.50,       // For explosive shortlist only
}
```

### Soft Scores (Influence ranking only)
**All scoring components are soft - influence position, not exclusion**

```typescript
interface SoftScoreComponents {
  volume_momentum_score: 0-100,    // S1: Time-normalized RelVol
  squeeze_score: 0-100,            // S2: Float rotation + friction
  catalyst_score: 0-100,           // S3: News/events with decay
  sentiment_score: 0-100,          // S4: Social Z-score anomaly
  options_score: 0-100,            // S5: Gamma pressure + flow
  technical_score: 0-100,          // S6: Regime-aware technicals
}
```

---

## 3. STALE DATA DETECTION & FLAGGING

### Stale Data Logic
```typescript
interface StaleDataCheck {
  trigger_condition: "market_open && data_age > 5_minutes";

  stale_response: {
    schema: "4.1",
    regime: string,
    status: "stale_data",        // ⚠️ Critical flag
    items: [],                   // Empty array
    explosive_top: [],           // Empty array
    error: "Market is open but data is X.X minutes old",
    age_minutes: number,         // Actual staleness
    execution_time_sec: number
  };
}
```

### Data Freshness in Normal Response
```typescript
interface FreshnessIndicators {
  telemetry: {
    production_health: {
      stale_data_detected: false,    // Boolean flag
      market_open: boolean,          // Current market status
      system_timestamp: string       // ISO timestamp of check
    }
  }
}
```

---

## 4. MINIMAL CANDIDATE PAYLOAD SCHEMA

### Core CandidateScore Structure
```typescript
interface CandidateScore {
  // Identity
  symbol: string;                    // Ticker symbol

  // Composite Scoring
  total_score: number;               // 0-100 final score
  confidence: number;                // 0-1.0 confidence level

  // Component Breakdown (all 0-100)
  volume_momentum_score: number;     // S1 component
  squeeze_score: number;             // S2 component
  catalyst_score: number;            // S3 component
  sentiment_score: number;           // S4 component
  options_score: number;             // S5 component
  technical_score: number;           // S6 component

  // Action Classification
  action_tag: "trade_ready" | "watchlist" | "monitor";

  // Risk Management
  risk_flags: string[];              // ["high_spread", "low_liquidity", etc.]

  // Raw Market Data
  snapshot: TickerSnapshot;          // Complete market data
}
```

### Essential TickerSnapshot Fields
```typescript
interface TickerSnapshot {
  // Required Core Data
  symbol: string;
  price: Decimal;                    // Current price
  volume: number;                    // Session volume
  data_timestamp: DateTime;          // Data freshness marker

  // Volume Analysis
  avg_volume_30d: number;            // 30-day average volume
  rel_vol_30d: number;               // Relative volume ratio

  // Market Microstructure
  bid_ask_spread_bps: number;        // Spread in basis points
  value_traded_usd: number;          // Dollar volume traded

  // Optional Enhancement Data (may be null)
  short_interest_pct?: number;       // Short interest %
  call_put_ratio?: number;           // Options flow ratio
  social_rank?: number;              // Social sentiment rank
  catalysts?: string[];              // News/event catalysts
  rsi?: number;                      // Technical RSI
  vwap?: number;                     // Volume weighted avg price
}
```

---

## 5. EGS + SER SCORE SURFACING

### Explosive Shortlist Format
**EGS (Explosive Gate Score) & SER (Structured Explosive Rank) are surfaced in separate `explosive_top` array**

```typescript
interface ExplosiveCandidate {
  // Core Identity
  symbol: string;
  price: number;
  tag: "trade_ready" | "watchlist" | "monitor";

  // Explosive Scores
  egs: number;                       // 0-100 Explosive Gate Score
  ser: number;                       // 0-100 Structured Explosive Rank
  score: number;                     // Standard total_score for reference

  // EGS Component Breakdown
  relvol_tod: number;                // Time-of-day normalized RelVol
  relvol_tod_sustain_min: number;    // Sustain minutes above threshold
  float_rotation: number;            // % of float traded
  squeeze_friction: number;          // Short squeeze pressure
  gamma_pressure: number;            // Options gamma pressure
  catalyst_freshness: number;        // Catalyst recency score
  sentiment_anomaly: number;         // Social sentiment Z-score
  vwap_adherence_30m: number;        // VWAP adherence %

  // Options Flow Metrics
  atm_call_oi: number;              // At-the-money call open interest
  options_volume: number;           // Total options volume
  delta_oi_calls_frac: number;      // Delta OI calls fraction

  // Liquidity Metrics
  effective_spread_bps: number;     // Effective spread in bps
  value_traded_usd: number;         // Value traded in USD
  atr_pct: number;                  // Average True Range %

  // Full candidate reference
  candidate: CandidateScore;        // Complete candidate object
}
```

### EGS Tier Thresholds
```typescript
interface EGSTiers {
  prime_tier: 60,        // EGS >= 60 (highest quality)
  strong_tier: 50,       // EGS >= 50 (good quality)
  floor_tier: 45,        // EGS >= 45 (minimum acceptable)
  elastic_fallback: true // Will decrease threshold by 5 if needed
}
```

---

## 6. TELEMETRY & COVERAGE HEALTH SIGNALS

### System Health Structure
```typescript
interface SystemHealth {
  system_ready: boolean;             // Overall system readiness
  timestamp: string;                 // ISO timestamp

  provider_health: {
    [provider_name: string]: {
      status: "HEALTHY" | "DEGRADED" | "FAILED";
      latency_ms?: number;
      error_message?: string;
      last_success?: string;
    }
  };

  summary: {
    healthy: number;                 // Count of healthy providers
    degraded: number;                // Count of degraded providers
    failed: number;                  // Count of failed providers
    total: number;                   // Total providers
  };
}
```

### Data Coverage Telemetry
```typescript
interface TelemetryMetrics {
  data_coverage: {
    options_data: number;            // % of stocks with options data
    short_data: number;              // % with short interest data
    social_data: number;             // % with social sentiment data
    catalyst_data: number;           // % with catalyst data
    technical_data: number;          // % with technical indicators
    overall_enrichment: number;      // Average coverage %
  };

  scoring_metrics: {
    min_score: number;               // Lowest total_score in batch
    max_score: number;               // Highest total_score in batch
    avg_score: number;               // Average total_score
    trade_ready_count: number;       // Count of trade_ready candidates
    watchlist_count: number;         // Count of watchlist candidates
    monitor_count: number;           // Count of monitor candidates
  };

  production_health: {
    stale_data_detected: boolean;    // Critical production flag
    market_open: boolean;            // Current market status
    system_timestamp: string;        // System time for sync checks
  };
}
```

### Pipeline Statistics
```typescript
interface PipelineStats {
  universe_size: number;             // Initial universe count
  enriched: number;                  // Successfully enriched
  filtered: number;                  // Passed hard guards
  scored: number;                    // Successfully scored

  // Derived metrics
  enrichment_rate: number;           // enriched / universe_size
  filter_pass_rate: number;          // filtered / enriched
  scoring_success_rate: number;      // scored / filtered
}
```

---

## 7. ERROR STATES & EDGE CASES

### System Not Ready
```typescript
interface NotReadyResponse {
  error: "ReadinessError";
  message: "System not ready for discovery - price provider unavailable";
  status: 503;                       // HTTP status code
}
```

### Stale Data During Market Hours
```typescript
interface StaleDataResponse {
  schema: "4.1";
  status: "stale_data";
  items: [];
  explosive_top: [];
  error: "Market is open but data is X.X minutes old";
  age_minutes: number;
}
```

### No Qualified Candidates
```typescript
interface NoResultsResponse {
  schema: "4.1";
  status: "live" | "closed";
  items: [];                         // Empty but valid
  explosive_top: [];                 // Empty but valid
  count: 0;
  // ... rest of normal structure
}
```

---

## 8. BACKEND/UI PARSING GUIDELINES

### Minimum Safe Parsing
```typescript
// Always check schema version first
if (response.schema !== "4.1") {
  throw new Error("Unsupported schema version");
}

// Check for error states
if (response.status === "stale_data") {
  showStaleDataWarning(response.age_minutes);
  return [];
}

// Safe candidate extraction
const candidates = response.items || [];
const explosiveList = response.explosive_top || [];

// Always validate core fields exist
candidates.forEach(candidate => {
  if (!candidate.symbol || candidate.total_score === undefined) {
    console.warn("Invalid candidate structure", candidate);
  }
});
```

### Telemetry Integration for OMS
```typescript
// Extract critical health metrics for risk management
const healthCheck = {
  systemReady: response.system_health?.system_ready ?? false,
  dataFresh: !response.telemetry?.production_health?.stale_data_detected,
  marketOpen: response.telemetry?.production_health?.market_open,
  coverageLevel: response.telemetry?.data_coverage?.overall_enrichment,
  candidateCount: response.count
};

// Risk management thresholds
if (!healthCheck.systemReady || healthCheck.dataFresh === false) {
  // Block trading operations
  return { status: "SYSTEM_DEGRADED", candidates: [] };
}
```

---

## 9. VERSIONING & COMPATIBILITY

### Schema Evolution
- Current: `"schema": "4.1"`
- Backward compatibility: None required (fresh implementation)
- Forward compatibility: Schema version must be checked

### Breaking Changes
Any changes to the core `items` array structure or `explosive_top` format constitute breaking changes and require schema version increment.

### Non-Breaking Changes
- Adding new telemetry fields
- Adding new optional TickerSnapshot fields
- Adding new risk_flags values
- Extending provider_health details

---

This canonical contract ensures that backend/UI parsing matches exactly what AlphaStack 4.1 produces, preventing integration failures and data misinterpretation.