---
run_id: 2025-08-30T20-17-35Z
version: 1
---

# AMC-TRADER Audit Requirements

## Primary Objective: Maximize Monthly Profit Potential

**Core Mission**: Find optimal thresholds and expand system capabilities to identify stocks with highest profit probability over monthly timeframes, following the June-July success pattern.

## 1. Discovery System Optimization (HIGHEST PRIORITY)

### Profit-Maximizing Thresholds
- **Current State**: VIGL pattern (324% winner) with 20.9x volume, $3-12 sweet spot
- **Requirement**: AI-driven threshold optimization for maximum monthly returns
- **Approach**: Analyze June-July winners, backtest various threshold combinations
- **Expansion**: Beyond VIGL - identify additional profitable patterns
- **Learning**: System must adapt thresholds based on success/failure feedback

### Success Criteria
- Discovery finds stocks with highest monthly profit potential
- Thresholds dynamically adjust based on market regime
- Pattern recognition expands beyond current VIGL-only approach

## 2. UI Data Flow Critical Repairs

### Discovery Results Display
- **Issue**: No results showing in TopRecommendations component
- **Requirement**: Reliable Redis → FastAPI → React pipeline
- **Fix**: Ensure real data flows from discovery job to UI consistently

### Squeeze Alerts System
- **Issue**: No consistent alerts, wrong/vague/mock data displaying  
- **Requirement**: Real-time squeeze detection with accurate data
- **Fix**: SqueezeMonitor must show actual opportunities, not placeholder data

### Trade Execution Streamlining
- **Current**: Basic order placement
- **Requirement**: Integrated stop-loss and profit-taking in single workflow
- **Enhancement**: One-click trading with automatic risk management

### AI Thesis Integration
- **Missing**: Detailed purchase reasoning for each recommendation
- **Requirement**: Every stock recommendation includes AI-generated thesis
- **Content**: Why to buy, profit potential, risk factors, entry/exit strategy

## 3. Market Regime Intelligence

**Approach**: AI-determined adaptive thresholds
- Analyze current market conditions vs June-July winning environment
- Implement regime-aware scoring adjustments
- Create fallback strategies for different market phases

## 4. June-July Winner Pattern Analysis

**Learning Integration**:
- Extract patterns from actual June-July profitable trades
- Update VIGL matching to include new successful patterns
- Implement continuous learning from trade outcomes
- Backtest new patterns against historical data

## 5. Actionable Ticker Definition

**AI-Driven Profitability Assessment**:
- Stocks ranked by expected monthly return potential
- Confidence scoring based on historical pattern success rates  
- Tiered recommendations (High/Medium/Low profit probability)
- Dynamic threshold adjustment based on win/loss tracking

## 6. Validation Success Metrics

### Discovery Performance
- Pipeline finds 3-7 high-probability opportunities daily
- Monthly return predictions achieve >60% accuracy
- False positive rate <30% for high-confidence recommendations

### UI Functionality  
- Real data displays within 30 seconds of generation
- All squeeze alerts show actual market conditions
- Trade execution completes with stop/profit integration

### Profit Optimization
- System learns from each trade outcome
- Threshold adjustments improve monthly returns over time
- AI thesis accuracy improves with feedback integration

## Expected Outcomes

1. **Immediate**: Fix UI data flow, display real opportunities with thesis
2. **Short-term**: Optimize discovery thresholds for current market regime  
3. **Long-term**: Self-improving system that adapts to market changes and maximizes monthly profits

## CRITICAL CONSTRAINT: Preserve Existing Functionality

**Non-Disruptive Enhancement Only**:
- Current working components must remain operational
- All improvements must be additive or safe extensions
- No breaking changes to existing discovery pipeline
- Maintain backwards compatibility for all API endpoints
- Test all changes in shadow/validation mode before deployment
- Rollback capability required for any modifications

## Implementation Strategy
1. **Analysis First**: Understand what's working before changing anything
2. **Shadow Testing**: New features run parallel to existing system
3. **Gradual Enhancement**: Incremental improvements with validation
4. **Fallback Mechanisms**: Always preserve current functionality as backup

## Key Success Indicator
The system consistently identifies stocks that generate significant monthly profits, following the June-July success model, with AI-driven continuous improvement **while maintaining all current operational capabilities**.