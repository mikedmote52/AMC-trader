-- AMC-TRADER Monitoring Schema Migration
-- Adds monitoring infrastructure with ZERO disruption to existing system
-- Can be rolled back instantly if needed

-- Create monitoring schema (separate from existing tables)
CREATE SCHEMA IF NOT EXISTS monitoring;

-- Discovery Flow Statistics Table
CREATE TABLE IF NOT EXISTS monitoring.discovery_flow_stats (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    universe_size INTEGER NOT NULL,
    filtering_stages JSONB NOT NULL,
    final_candidates INTEGER NOT NULL,
    processing_time_ms INTEGER NOT NULL,
    health_score FLOAT NOT NULL CHECK (health_score >= 0 AND health_score <= 1),
    alerts JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_discovery_flow_timestamp 
ON monitoring.discovery_flow_stats (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_discovery_flow_health 
ON monitoring.discovery_flow_stats (health_score, timestamp DESC);

-- Recommendation Tracking Table
CREATE TABLE IF NOT EXISTS monitoring.recommendation_tracking (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    recommendation_date TIMESTAMPTZ NOT NULL,
    discovery_price DECIMAL(10,4) NOT NULL,
    discovery_score DECIMAL(6,4) NOT NULL,
    discovery_reason TEXT NOT NULL,
    thesis TEXT,
    confidence DECIMAL(6,4) NOT NULL,
    
    -- Portfolio integration
    was_bought BOOLEAN DEFAULT FALSE,
    buy_price DECIMAL(10,4),
    position_size DECIMAL(15,4),
    
    -- Performance tracking
    performance_1h DECIMAL(8,4),
    performance_4h DECIMAL(8,4), 
    performance_1d DECIMAL(8,4),
    performance_3d DECIMAL(8,4),
    performance_7d DECIMAL(8,4),
    performance_14d DECIMAL(8,4),
    performance_30d DECIMAL(8,4),
    
    -- Outcome classification
    outcome_classification VARCHAR(20) DEFAULT 'PENDING' 
        CHECK (outcome_classification IN ('PENDING', 'EXPLOSIVE', 'STRONG', 'MODERATE', 'POOR', 'FAILED', 'NO_DATA')),
    peak_return DECIMAL(8,4),
    days_to_peak INTEGER,
    
    -- Learning insights
    missed_opportunity BOOLEAN DEFAULT FALSE,
    learning_insights JSONB DEFAULT '[]'::jsonb,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for recommendation tracking
CREATE INDEX IF NOT EXISTS idx_recommendation_symbol_date 
ON monitoring.recommendation_tracking (symbol, recommendation_date DESC);

CREATE INDEX IF NOT EXISTS idx_recommendation_classification 
ON monitoring.recommendation_tracking (outcome_classification, performance_30d DESC);

CREATE INDEX IF NOT EXISTS idx_recommendation_missed 
ON monitoring.recommendation_tracking (missed_opportunity, performance_30d DESC) 
WHERE missed_opportunity = TRUE;

-- Buy-the-Dip Analysis Table
CREATE TABLE IF NOT EXISTS monitoring.buy_the_dip_analysis (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    analysis_date TIMESTAMPTZ NOT NULL,
    current_price DECIMAL(10,4) NOT NULL,
    original_thesis TEXT NOT NULL,
    thesis_strength VARCHAR(20) NOT NULL CHECK (thesis_strength IN ('STRONG', 'MODERATE', 'WEAK', 'FAILED')),
    
    -- Price analysis
    price_drop_pct DECIMAL(8,4) NOT NULL,
    support_level DECIMAL(10,4),
    resistance_level DECIMAL(10,4),
    
    -- Technical indicators
    rsi DECIMAL(5,2),
    volume_spike DECIMAL(8,4),
    oversold_indicator BOOLEAN DEFAULT FALSE,
    
    -- Position analysis
    current_position_size DECIMAL(15,4),
    position_cost_basis DECIMAL(10,4),
    unrealized_pl_pct DECIMAL(8,4),
    
    -- Buy recommendation
    dip_buy_recommendation VARCHAR(20) NOT NULL 
        CHECK (dip_buy_recommendation IN ('STRONG_BUY', 'BUY', 'HOLD', 'WAIT', 'AVOID')),
    recommended_entry_price DECIMAL(10,4),
    recommended_position_size DECIMAL(15,4),
    risk_score DECIMAL(4,3) CHECK (risk_score >= 0 AND risk_score <= 1),
    
    -- Outcome tracking
    action_taken VARCHAR(20) DEFAULT 'PENDING',
    outcome_7d DECIMAL(8,4),
    outcome_30d DECIMAL(8,4),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for buy-the-dip analysis
CREATE INDEX IF NOT EXISTS idx_buy_dip_symbol_date 
ON monitoring.buy_the_dip_analysis (symbol, analysis_date DESC);

CREATE INDEX IF NOT EXISTS idx_buy_dip_recommendation 
ON monitoring.buy_the_dip_analysis (dip_buy_recommendation, risk_score DESC);

-- System Health Monitoring Table
CREATE TABLE IF NOT EXISTS monitoring.system_health (
    id SERIAL PRIMARY KEY,
    check_timestamp TIMESTAMPTZ NOT NULL,
    component VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('HEALTHY', 'WARNING', 'CRITICAL', 'ERROR')),
    health_score DECIMAL(4,3) CHECK (health_score >= 0 AND health_score <= 1),
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    alerts JSONB NOT NULL DEFAULT '[]'::jsonb,
    response_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for system health
CREATE INDEX IF NOT EXISTS idx_system_health_component_time 
ON monitoring.system_health (component, check_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_system_health_status 
ON monitoring.system_health (status, check_timestamp DESC) 
WHERE status IN ('CRITICAL', 'ERROR');

-- Learning Insights Aggregation Table
CREATE TABLE IF NOT EXISTS monitoring.learning_insights (
    id SERIAL PRIMARY KEY,
    insight_date TIMESTAMPTZ NOT NULL,
    insight_type VARCHAR(50) NOT NULL,
    insight_category VARCHAR(50) NOT NULL,
    
    -- Quantified insights
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,6) NOT NULL,
    metric_change_pct DECIMAL(8,4),
    confidence_level DECIMAL(4,3) CHECK (confidence_level >= 0 AND confidence_level <= 1),
    
    -- Actionable recommendations
    recommendation TEXT,
    action_priority VARCHAR(20) CHECK (action_priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    estimated_impact VARCHAR(50),
    
    -- Metadata
    data_sources JSONB NOT NULL DEFAULT '[]'::jsonb,
    related_symbols JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for learning insights
CREATE INDEX IF NOT EXISTS idx_learning_insights_date_type 
ON monitoring.learning_insights (insight_date DESC, insight_type);

CREATE INDEX IF NOT EXISTS idx_learning_insights_priority 
ON monitoring.learning_insights (action_priority, confidence_level DESC) 
WHERE action_priority IN ('HIGH', 'CRITICAL');

-- Performance Analytics View
CREATE OR REPLACE VIEW monitoring.performance_dashboard AS
SELECT 
    -- Discovery pipeline health
    (SELECT health_score FROM monitoring.discovery_flow_stats ORDER BY timestamp DESC LIMIT 1) as discovery_health_score,
    (SELECT final_candidates FROM monitoring.discovery_flow_stats ORDER BY timestamp DESC LIMIT 1) as latest_candidates_count,
    (SELECT universe_size FROM monitoring.discovery_flow_stats ORDER BY timestamp DESC LIMIT 1) as latest_universe_size,
    
    -- Recommendation performance
    (SELECT COUNT(*) FROM monitoring.recommendation_tracking WHERE missed_opportunity = true AND recommendation_date >= NOW() - INTERVAL '30 days') as missed_opportunities_30d,
    (SELECT AVG(performance_30d) FROM monitoring.recommendation_tracking WHERE outcome_classification != 'PENDING') as avg_30d_performance,
    (SELECT COUNT(*) FILTER (WHERE outcome_classification IN ('EXPLOSIVE', 'STRONG')) * 100.0 / NULLIF(COUNT(*), 0) FROM monitoring.recommendation_tracking WHERE outcome_classification != 'PENDING') as success_rate_pct,
    
    -- Buy-the-dip opportunities
    (SELECT COUNT(*) FROM monitoring.buy_the_dip_analysis WHERE dip_buy_recommendation IN ('STRONG_BUY', 'BUY') AND analysis_date >= NOW() - INTERVAL '7 days') as active_dip_opportunities,
    
    -- System health
    (SELECT COUNT(*) FROM monitoring.system_health WHERE status IN ('CRITICAL', 'ERROR') AND check_timestamp >= NOW() - INTERVAL '1 hour') as critical_alerts_1h,
    
    -- Last update
    NOW() as dashboard_updated_at;

-- Grant permissions (assuming existing user structure)
-- GRANT USAGE ON SCHEMA monitoring TO amc_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA monitoring TO amc_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA monitoring TO amc_user;

-- Data retention policies (optional - clean old data automatically)
-- Discovery flow stats: keep 90 days
CREATE OR REPLACE FUNCTION monitoring.cleanup_old_data() RETURNS void AS $$
BEGIN
    DELETE FROM monitoring.discovery_flow_stats WHERE timestamp < NOW() - INTERVAL '90 days';
    DELETE FROM monitoring.recommendation_tracking WHERE recommendation_date < NOW() - INTERVAL '180 days' AND outcome_classification != 'EXPLOSIVE';
    DELETE FROM monitoring.buy_the_dip_analysis WHERE analysis_date < NOW() - INTERVAL '90 days';
    DELETE FROM monitoring.system_health WHERE check_timestamp < NOW() - INTERVAL '30 days' AND status = 'HEALTHY';
    DELETE FROM monitoring.learning_insights WHERE insight_date < NOW() - INTERVAL '180 days' AND action_priority = 'LOW';
END;
$$ LANGUAGE plpgsql;

-- Auto-update trigger for recommendation tracking
CREATE OR REPLACE FUNCTION monitoring.update_recommendation_timestamp() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_recommendation_tracking_timestamp
    BEFORE UPDATE ON monitoring.recommendation_tracking
    FOR EACH ROW EXECUTE FUNCTION monitoring.update_recommendation_timestamp();

-- Rollback script (uncomment if needed to remove monitoring)
-- DROP SCHEMA monitoring CASCADE;