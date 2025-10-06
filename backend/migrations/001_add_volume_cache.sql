-- Volume averages cache for RVOL calculations
-- Squeeze-Prophet optimization: Stage 4 (cache lookup)
--
-- This table stores pre-calculated 20-day average volumes for RVOL computation.
-- Eliminates 8,000+ API calls per discovery scan.
--
-- CRITICAL: Only stores REAL data from Polygon API.
-- NO fake data, NO defaults, NO fallbacks.

CREATE TABLE IF NOT EXISTS volume_averages (
    symbol VARCHAR(10) PRIMARY KEY,
    avg_volume_20d BIGINT NOT NULL,
    avg_volume_30d BIGINT,
    last_updated TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT positive_volume CHECK (avg_volume_20d > 0)
);

-- Indexes for performance
CREATE INDEX idx_volume_avg_updated ON volume_averages(last_updated);
CREATE INDEX idx_volume_avg_symbol ON volume_averages(symbol);

-- Add comment for documentation
COMMENT ON TABLE volume_averages IS 'Cached 20-day average volumes for RVOL calculation optimization (Squeeze-Prophet Stage 4)';
COMMENT ON COLUMN volume_averages.avg_volume_20d IS 'Real 20-day average volume from Polygon API (NO fake data)';
COMMENT ON COLUMN volume_averages.last_updated IS 'Cache freshness timestamp - data older than 24h is stale';
