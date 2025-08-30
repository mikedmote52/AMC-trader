-- Pattern Memory System Database Schema
-- Maintains explosive growth edge by learning from squeeze patterns like VIGL (+324%)

-- Main squeeze patterns table for pattern memory
CREATE TABLE IF NOT EXISTS squeeze_patterns (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    pattern_date DATE NOT NULL,
    discovery_timestamp TIMESTAMP DEFAULT NOW(),
    
    -- Core squeeze metrics (based on VIGL analysis)
    volume_spike FLOAT NOT NULL,           -- Volume vs 30-day average (VIGL: 20.9x)
    short_interest FLOAT,                  -- Short interest percentage (VIGL: 18%)
    float_shares BIGINT,                   -- Float size in shares (VIGL: 15.2M)
    days_to_cover FLOAT,                   -- Short interest / avg daily volume
    
    -- Price data
    entry_price DECIMAL(10,4) NOT NULL,    -- Discovery/entry price
    exit_price DECIMAL(10,4),              -- Exit price (if closed)
    max_price DECIMAL(10,4),               -- Highest price achieved
    current_price DECIMAL(10,4),           -- Latest known price
    
    -- Pattern characteristics
    pattern_score FLOAT NOT NULL,          -- Overall pattern strength (0.0-1.0)
    squeeze_score FLOAT NOT NULL,          -- Specific squeeze potential (0.0-1.0)
    vigl_similarity FLOAT DEFAULT 0.0,     -- Similarity to VIGL pattern (0.0-1.0)
    
    -- Performance outcomes
    outcome_pct FLOAT,                     -- Total return percentage
    max_gain_pct FLOAT,                    -- Maximum gain achieved
    max_drawdown_pct FLOAT,                -- Maximum drawdown from peak
    days_held INTEGER DEFAULT 0,           -- Days between entry and exit
    
    -- Pattern validation
    pattern_hash VARCHAR(64) NOT NULL,     -- Unique pattern fingerprint
    success BOOLEAN DEFAULT NULL,          -- TRUE if >50% gain achieved
    explosive BOOLEAN DEFAULT NULL,        -- TRUE if >100% gain achieved
    
    -- Metadata
    market_cap_at_entry BIGINT,           -- Market cap at discovery
    sector VARCHAR(50),                    -- Stock sector
    catalyst_type VARCHAR(100),            -- Primary catalyst if known
    notes TEXT,                           -- Additional pattern notes
    
    -- Tracking
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    closed_at TIMESTAMP,                  -- When position was closed
    
    -- Unique constraint on symbol + pattern_date to prevent duplicates
    UNIQUE(symbol, pattern_date)
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_squeeze_success ON squeeze_patterns(success, outcome_pct DESC);
CREATE INDEX IF NOT EXISTS idx_squeeze_pattern_score ON squeeze_patterns(pattern_score DESC);
CREATE INDEX IF NOT EXISTS idx_squeeze_explosive ON squeeze_patterns(explosive, max_gain_pct DESC);
CREATE INDEX IF NOT EXISTS idx_squeeze_vigl_similarity ON squeeze_patterns(vigl_similarity DESC);
CREATE INDEX IF NOT EXISTS idx_squeeze_symbol ON squeeze_patterns(symbol);
CREATE INDEX IF NOT EXISTS idx_squeeze_date ON squeeze_patterns(pattern_date DESC);
CREATE INDEX IF NOT EXISTS idx_squeeze_hash ON squeeze_patterns(pattern_hash);

-- Pattern evolution tracking table
CREATE TABLE IF NOT EXISTS pattern_evolution (
    id SERIAL PRIMARY KEY,
    evolution_date DATE NOT NULL,
    pattern_type VARCHAR(50) NOT NULL,     -- 'VIGL_SQUEEZE', 'HIGH_SHORT', etc.
    
    -- Pattern performance metrics over time
    total_patterns INTEGER NOT NULL DEFAULT 0,
    successful_patterns INTEGER NOT NULL DEFAULT 0,
    explosive_patterns INTEGER NOT NULL DEFAULT 0,
    success_rate FLOAT NOT NULL DEFAULT 0.0,
    avg_return FLOAT NOT NULL DEFAULT 0.0,
    avg_max_gain FLOAT NOT NULL DEFAULT 0.0,
    
    -- Pattern characteristic drift
    avg_volume_spike FLOAT,
    avg_short_interest FLOAT,
    avg_float_size BIGINT,
    pattern_confidence FLOAT DEFAULT 0.5,
    
    -- Market context
    market_regime VARCHAR(20),             -- Bull, bear, volatile, etc.
    market_volatility FLOAT,               -- VIX level
    
    -- Adaptation metrics
    threshold_adjustments JSONB,          -- Historical threshold changes
    detection_parameters JSONB,           -- Current detection parameters
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Unique constraint on date + pattern_type
    UNIQUE(evolution_date, pattern_type)
);

CREATE INDEX IF NOT EXISTS idx_evolution_date ON pattern_evolution(evolution_date DESC);
CREATE INDEX IF NOT EXISTS idx_evolution_type ON pattern_evolution(pattern_type);
CREATE INDEX IF NOT EXISTS idx_evolution_success ON pattern_evolution(success_rate DESC);

-- Pattern similarity matrix for quick lookups
CREATE TABLE IF NOT EXISTS pattern_similarity (
    id SERIAL PRIMARY KEY,
    pattern_id_1 INTEGER REFERENCES squeeze_patterns(id),
    pattern_id_2 INTEGER REFERENCES squeeze_patterns(id),
    similarity_score FLOAT NOT NULL,      -- Cosine similarity (0.0-1.0)
    feature_correlation JSONB,            -- Which features are most similar
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Ensure no duplicate pairs
    UNIQUE(pattern_id_1, pattern_id_2)
);

CREATE INDEX IF NOT EXISTS idx_similarity_score ON pattern_similarity(similarity_score DESC);
CREATE INDEX IF NOT EXISTS idx_similarity_pattern1 ON pattern_similarity(pattern_id_1);

-- Pattern alerts table for monitoring pattern health
CREATE TABLE IF NOT EXISTS pattern_alerts (
    id SERIAL PRIMARY KEY,
    alert_type VARCHAR(50) NOT NULL,       -- 'PATTERN_DEGRADATION', 'NEW_PATTERN', 'THRESHOLD_BREACH'
    pattern_type VARCHAR(50) NOT NULL,     -- 'VIGL_SQUEEZE', etc.
    alert_level VARCHAR(20) NOT NULL,      -- 'INFO', 'WARNING', 'CRITICAL'
    
    message TEXT NOT NULL,
    details JSONB,                         -- Alert-specific data
    
    -- Alert status
    acknowledged BOOLEAN DEFAULT FALSE,
    resolved BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT NOW(),
    acknowledged_at TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alerts_type ON pattern_alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_alerts_unresolved ON pattern_alerts(resolved) WHERE resolved = FALSE;
CREATE INDEX IF NOT EXISTS idx_alerts_date ON pattern_alerts(created_at DESC);

-- Update trigger for squeeze_patterns
CREATE OR REPLACE FUNCTION update_squeeze_pattern_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    
    -- Auto-calculate success flags based on performance
    IF NEW.outcome_pct IS NOT NULL THEN
        NEW.success = NEW.outcome_pct >= 50.0;
        NEW.explosive = NEW.outcome_pct >= 100.0;
    END IF;
    
    -- Update max_gain_pct if current price is higher
    IF NEW.current_price IS NOT NULL AND NEW.entry_price IS NOT NULL THEN
        NEW.max_gain_pct = GREATEST(
            COALESCE(NEW.max_gain_pct, 0),
            ((NEW.current_price - NEW.entry_price) / NEW.entry_price) * 100
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_squeeze_pattern_timestamp
    BEFORE UPDATE ON squeeze_patterns
    FOR EACH ROW
    EXECUTE FUNCTION update_squeeze_pattern_timestamp();

-- Insert initial VIGL reference pattern
INSERT INTO squeeze_patterns (
    symbol, pattern_date, volume_spike, short_interest, float_shares,
    entry_price, max_price, outcome_pct, max_gain_pct, pattern_score,
    squeeze_score, vigl_similarity, success, explosive, days_held,
    pattern_hash, sector, catalyst_type, notes
) VALUES (
    'VIGL', '2024-06-15', 20.9, 0.18, 15200000,
    2.94, 12.46, 324.0, 324.0, 1.0,
    1.0, 1.0, TRUE, TRUE, 14,
    '324pct_vigl_reference_pattern', 'Biotech', 'FDA_catalyst',
    'Reference VIGL pattern: +324% explosive winner with 20.9x volume spike, 18% short interest, 15.2M float'
) ON CONFLICT (symbol, pattern_date) DO NOTHING;

-- Insert CRWV reference pattern
INSERT INTO squeeze_patterns (
    symbol, pattern_date, volume_spike, short_interest, float_shares,
    entry_price, max_price, outcome_pct, max_gain_pct, pattern_score,
    squeeze_score, vigl_similarity, success, explosive, days_held,
    pattern_hash, sector, catalyst_type, notes
) VALUES (
    'CRWV', '2024-07-02', 35.2, 0.22, 8500000,
    1.45, 8.92, 515.0, 515.0, 1.0,
    1.0, 0.85, TRUE, TRUE, 18,
    '515pct_crwv_reference_pattern', 'Cannabis', 'Acquisition',
    'Reference CRWV pattern: +515% explosive winner with 35.2x volume spike, 22% short interest, 8.5M float'
) ON CONFLICT (symbol, pattern_date) DO NOTHING;

-- Create view for quick pattern analysis
CREATE OR REPLACE VIEW pattern_performance_summary AS
SELECT 
    DATE_TRUNC('month', pattern_date) as month,
    COUNT(*) as total_patterns,
    COUNT(*) FILTER (WHERE success = TRUE) as successful_patterns,
    COUNT(*) FILTER (WHERE explosive = TRUE) as explosive_patterns,
    ROUND(AVG(outcome_pct), 2) as avg_return_pct,
    ROUND(AVG(max_gain_pct), 2) as avg_max_gain_pct,
    ROUND(AVG(pattern_score), 3) as avg_pattern_score,
    ROUND(AVG(vigl_similarity), 3) as avg_vigl_similarity,
    ROUND(
        COUNT(*) FILTER (WHERE success = TRUE)::FLOAT / 
        GREATEST(COUNT(*), 1) * 100, 1
    ) as success_rate_pct
FROM squeeze_patterns 
WHERE pattern_date >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY DATE_TRUNC('month', pattern_date)
ORDER BY month DESC;

-- Grant permissions (adjust as needed for your user)
-- GRANT ALL PRIVILEGES ON squeeze_patterns TO your_app_user;
-- GRANT ALL PRIVILEGES ON pattern_evolution TO your_app_user;  
-- GRANT ALL PRIVILEGES ON pattern_similarity TO your_app_user;
-- GRANT ALL PRIVILEGES ON pattern_alerts TO your_app_user;