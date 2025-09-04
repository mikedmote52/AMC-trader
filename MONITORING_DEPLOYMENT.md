# AMC-TRADER Monitoring System - Deployment & Testing Guide

## 📋 Current Status

The comprehensive monitoring system has been implemented locally but needs to be deployed to production. Here's what's ready:

### ✅ Completed Implementation

1. **Core Services** (Ready for deployment)
   - `backend/src/services/discovery_monitor.py` - Discovery pipeline tracking
   - `backend/src/services/recommendation_tracker.py` - 30-day recommendation tracking
   - `backend/src/services/buy_the_dip_detector.py` - Dip-buying opportunity detection
   - `backend/src/services/monitoring_worker.py` - Background job system

2. **API Endpoints** (Ready for deployment)
   - `backend/src/routes/monitoring.py` - Complete monitoring API
   - Already integrated into `backend/src/app.py`

3. **Database Schema** (Ready for deployment)
   - `database/migrations/001_monitoring_schema.sql` - Monitoring tables

4. **Testing Tools** (Ready to use)
   - `test_monitoring.py` - Interactive Python tester
   - `TEST_MONITORING.sh` - Bash test suite
   - `scripts/start_monitoring.py` - Initialization script

## 🚀 Deployment Steps

### Step 1: Deploy to Production

```bash
# Commit and push the monitoring system
git add .
git commit -m "feat: comprehensive monitoring system with learning and buy-the-dip detection

- Discovery pipeline monitoring (10K+ stocks → filtering → candidates)
- 30-day recommendation tracking for learning
- Buy-the-dip detection with thesis validation
- Real-time alert system
- Zero disruption to existing functionality"

git push origin main
```

### Step 2: Initialize Database (After Deployment)

Once deployed to Render, run the database migration:

```bash
# Option 1: Use the initialization endpoint (after deploy)
curl -X POST https://amc-trader.onrender.com/monitoring/initialize

# Option 2: Run locally against production DB
python scripts/start_monitoring.py
```

### Step 3: Verify Deployment

```bash
# Check monitoring system status
curl https://amc-trader.onrender.com/monitoring/status | jq .

# Check comprehensive dashboard
curl https://amc-trader.onrender.com/monitoring/dashboard | jq .
```

## 🧪 Testing Features (What You Can Do Now)

### 1. Test Locally First

```bash
# Run the interactive tester
python test_monitoring.py

# Choose from menu:
# 1 - Run full test suite
# 2 - Check discovery pipeline health
# 3 - Check missed opportunities  
# 4 - Check buy-the-dip opportunities
# 5 - Check system alerts
```

### 2. Monitor Discovery Pipeline Flow

After deployment, you'll see:
- How many stocks enter the pipeline (10,325+ normally)
- Each filtering stage (price, volume, short interest, etc.)
- Final candidate count
- Health score and alerts when using fallback data

### 3. Track Missed Opportunities

The system will show you:
- Stocks recommended but not bought
- Their 30-day performance
- Alerts when they gain >15%
- Learning insights to improve future selections

### 4. Find Buy-the-Dip Opportunities

Get notified about:
- Portfolio holdings down >10%
- Thesis strength validation
- Risk-adjusted position sizing
- Entry price recommendations

## 📊 Key Endpoints to Explore

### Discovery Monitoring
```bash
# Pipeline health
GET /monitoring/discovery/health

# Flow statistics (see filtering stages)
GET /monitoring/discovery/flow-stats?hours_back=24

# Discovery alerts
GET /monitoring/discovery/alerts
```

### Learning System
```bash
# Missed opportunities (stocks that performed well)
GET /monitoring/recommendations/missed-opportunities?min_performance=15

# Performance insights
GET /monitoring/recommendations/performance-insights
```

### Buy-the-Dip
```bash
# Current opportunities
GET /monitoring/dip-analysis/opportunities?min_drop_pct=10

# Trigger analysis
POST /monitoring/dip-analysis/run
```

### Alerts
```bash
# All system alerts
GET /monitoring/alerts/system

# Missed opportunity alerts
GET /monitoring/alerts/missed-opportunities
```

## 🎯 What to Look For

### Healthy System Indicators:
- Discovery health score > 0.7
- Universe size > 5000 stocks
- 10-50 final candidates per run
- Success rate > 20% on recommendations

### Warning Signs:
- Universe size < 1000 (using fallback)
- 0 candidates found
- Many missed opportunities (>10 with >30% gains)
- Critical system alerts

### Opportunities:
- Buy-the-dip: STRONG_BUY recommendations
- Missed opportunities: Research why you didn't buy
- Pattern insights: Common traits of winners

## 💡 Usage Tips

1. **Daily Routine**:
   - Check `/monitoring/dashboard` for overview
   - Review missed opportunities
   - Check dip-buying opportunities
   - Monitor system alerts

2. **Weekly Analysis**:
   - Review discovery flow patterns
   - Analyze learning insights
   - Adjust strategies based on missed opportunities

3. **Real-time Monitoring**:
   - Watch discovery health during market hours
   - Get alerts for critical issues
   - Track recommendation performance

## 🔧 Troubleshooting

If monitoring isn't working after deployment:

1. **Check database migration**:
   ```bash
   curl -X POST https://amc-trader.onrender.com/monitoring/initialize
   ```

2. **Verify API status**:
   ```bash
   curl https://amc-trader.onrender.com/monitoring/status
   ```

3. **Check logs**:
   - Look for "Discovery monitoring error (non-critical)" 
   - These errors won't break trading but indicate monitoring issues

4. **Test discovery trigger**:
   ```bash
   curl -X POST https://amc-trader.onrender.com/discovery/trigger
   ```

## 📈 Expected Results

Once deployed and running:

- **Discovery Monitoring**: Track every discovery run with full flow visibility
- **Learning System**: All recommendations tracked for 30 days automatically
- **Buy-the-Dip**: Daily analysis of portfolio for dip opportunities
- **Alerts**: Real-time notifications for important events
- **Zero Disruption**: All monitoring is non-blocking and wrapped in error handlers

The system is designed to start learning immediately and improve over time!