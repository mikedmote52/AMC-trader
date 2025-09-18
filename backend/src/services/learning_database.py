#!/usr/bin/env python3
"""
Learning Database Schema Initialization
Creates the enhanced learning intelligence database schema
"""

import asyncio
import logging
from typing import Dict, Any
from ..shared.database import get_db_pool

logger = logging.getLogger(__name__)

async def initialize_learning_database():
    """
    Initialize the complete learning intelligence database schema
    Safe to run multiple times (idempotent)
    """
    try:
        pool = await get_db_pool()
        if not pool:
            logger.error("Could not connect to database")
            return False

        async with pool.acquire() as conn:
            # Create learning schema
            await conn.execute("CREATE SCHEMA IF NOT EXISTS learning_intelligence;")

            # Core learning tables
            await _create_core_tables(conn)

            # Advanced pattern tables
            await _create_pattern_tables(conn)

            # Performance tracking tables
            await _create_performance_tables(conn)

            # Create indexes
            await _create_indexes(conn)

            logger.info("✅ Learning intelligence database schema initialized")
            return True

    except Exception as e:
        logger.error(f"Failed to initialize learning database: {e}")
        return False

async def _create_core_tables(conn):
    """Create core learning tables"""

    # Discovery events tracking
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_intelligence.discovery_events (
            id SERIAL PRIMARY KEY,
            event_timestamp TIMESTAMP NOT NULL,
            universe_size INTEGER NOT NULL,
            candidates_found INTEGER NOT NULL,
            execution_time_ms FLOAT NOT NULL,
            market_conditions JSONB NOT NULL,
            scoring_distribution JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    # Candidate features for pattern learning
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_intelligence.candidate_features (
            id SERIAL PRIMARY KEY,
            discovery_event_id INTEGER REFERENCES learning_intelligence.discovery_events(id),
            symbol VARCHAR(10) NOT NULL,
            score FLOAT NOT NULL,
            action_tag VARCHAR(20) NOT NULL,
            volume_momentum_score FLOAT,
            squeeze_score FLOAT,
            catalyst_score FLOAT,
            sentiment_score FLOAT,
            options_score FLOAT,
            technical_score FLOAT,
            price FLOAT,
            volume BIGINT,
            rel_vol FLOAT,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    # Thesis decisions tracking
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_intelligence.thesis_decisions (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL,
            decision_timestamp TIMESTAMP NOT NULL,
            recommendation VARCHAR(20) NOT NULL,
            confidence_score FLOAT NOT NULL,
            thesis_text TEXT,
            ai_generated BOOLEAN DEFAULT FALSE,
            market_regime VARCHAR(20),
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    # Trade outcomes tracking
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_intelligence.trade_outcomes (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL,
            candidate_id INTEGER REFERENCES learning_intelligence.candidate_features(id),
            thesis_id INTEGER REFERENCES learning_intelligence.thesis_decisions(id),
            entry_timestamp TIMESTAMP,
            exit_timestamp TIMESTAMP,
            entry_price FLOAT,
            exit_price FLOAT,
            return_1d FLOAT,
            return_7d FLOAT,
            return_30d FLOAT,
            max_favorable_excursion FLOAT,
            max_adverse_excursion FLOAT,
            position_size_pct FLOAT,
            exit_reason VARCHAR(50),
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

async def _create_pattern_tables(conn):
    """Create pattern analysis tables"""

    # Pattern performance tracking
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_intelligence.pattern_performance (
            id SERIAL PRIMARY KEY,
            pattern_signature VARCHAR(100) NOT NULL,
            pattern_features JSONB NOT NULL,
            success_rate FLOAT NOT NULL,
            avg_return FLOAT NOT NULL,
            sample_size INTEGER NOT NULL,
            confidence_interval JSONB,
            market_regime VARCHAR(20),
            last_updated TIMESTAMP DEFAULT NOW()
        );
    """)

    # Feature importance tracking
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_intelligence.feature_importance (
            id SERIAL PRIMARY KEY,
            feature_name VARCHAR(50) NOT NULL,
            feature_weight FLOAT NOT NULL,
            success_correlation FLOAT NOT NULL,
            market_regime VARCHAR(20),
            measurement_date DATE DEFAULT CURRENT_DATE,
            sample_size INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT NOW(),
            UNIQUE(feature_name, market_regime, measurement_date)
        );
    """)

    # Explosive patterns library
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_intelligence.explosive_patterns (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL,
            discovery_date TIMESTAMP NOT NULL,
            pattern_features JSONB NOT NULL,
            vigl_score FLOAT NOT NULL,
            volume_spike_ratio FLOAT NOT NULL,
            price_momentum_1d FLOAT NOT NULL,
            price_momentum_5d FLOAT NOT NULL,
            atr_pct FLOAT NOT NULL,
            compression_pct FLOAT NOT NULL,
            wolf_risk_score FLOAT NOT NULL,
            market_regime VARCHAR(20),
            outcome_return_pct FLOAT,
            peak_return_pct FLOAT,
            days_to_peak INTEGER,
            max_drawdown FLOAT,
            pattern_success BOOLEAN,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

async def _create_performance_tables(conn):
    """Create performance tracking tables"""

    # Market regime tracking
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_intelligence.market_regimes (
            id SERIAL PRIMARY KEY,
            regime_date DATE NOT NULL UNIQUE,
            regime_type VARCHAR(20) NOT NULL,
            vix_level FLOAT,
            market_trend VARCHAR(20),
            explosive_success_rate FLOAT,
            avg_pattern_return FLOAT,
            pattern_confidence_adjustment FLOAT,
            detection_confidence FLOAT DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    # Discovery performance tracking
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_intelligence.discovery_performance (
            id SERIAL PRIMARY KEY,
            discovery_date TIMESTAMP NOT NULL,
            discovery_parameters JSONB NOT NULL,
            symbols_discovered INTEGER NOT NULL,
            avg_7d_return FLOAT,
            avg_30d_return FLOAT,
            success_rate FLOAT,
            explosive_winners INTEGER DEFAULT 0,
            total_tracked INTEGER DEFAULT 0,
            parameter_effectiveness FLOAT,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    # Thesis accuracy tracking
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_intelligence.thesis_accuracy (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL,
            thesis_date TIMESTAMP NOT NULL,
            recommendation VARCHAR(20) NOT NULL,
            confidence_score FLOAT NOT NULL,
            predicted_direction VARCHAR(10),
            actual_return_1d FLOAT,
            actual_return_7d FLOAT,
            actual_return_30d FLOAT,
            accuracy_score FLOAT,
            market_regime VARCHAR(20),
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    # Learning insights cache
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_intelligence.learning_insights (
            id SERIAL PRIMARY KEY,
            insight_type VARCHAR(50) NOT NULL,
            insight_data JSONB NOT NULL,
            confidence_score FLOAT NOT NULL,
            applicable_regime VARCHAR(20),
            generated_at TIMESTAMP DEFAULT NOW(),
            expires_at TIMESTAMP,
            UNIQUE(insight_type, applicable_regime)
        );
    """)

    # Create position_tracking table for trade outcome learning
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_intelligence.position_tracking (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL,
            action VARCHAR(10) NOT NULL,  -- BUY/SELL
            entry_price DECIMAL(10,4) NOT NULL,
            quantity INTEGER NOT NULL,
            entry_time TIMESTAMP NOT NULL,
            alpaca_order_id VARCHAR(50) UNIQUE,
            discovery_source BOOLEAN DEFAULT FALSE,
            learning_tracked BOOLEAN DEFAULT FALSE,
            exit_price DECIMAL(10,4),
            exit_time TIMESTAMP,
            outcome_recorded BOOLEAN DEFAULT FALSE,
            return_pct DECIMAL(8,4),
            days_held INTEGER,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """)

async def _create_indexes(conn):
    """Create database indexes for performance"""

    indexes = [
        # Discovery events indexes
        "CREATE INDEX IF NOT EXISTS idx_discovery_events_timestamp ON learning_intelligence.discovery_events(event_timestamp);",

        # Candidate features indexes
        "CREATE INDEX IF NOT EXISTS idx_candidate_features_symbol ON learning_intelligence.candidate_features(symbol);",
        "CREATE INDEX IF NOT EXISTS idx_candidate_features_score ON learning_intelligence.candidate_features(score);",
        "CREATE INDEX IF NOT EXISTS idx_candidate_features_action_tag ON learning_intelligence.candidate_features(action_tag);",

        # Trade outcomes indexes
        "CREATE INDEX IF NOT EXISTS idx_trade_outcomes_symbol ON learning_intelligence.trade_outcomes(symbol);",
        "CREATE INDEX IF NOT EXISTS idx_trade_outcomes_return_7d ON learning_intelligence.trade_outcomes(return_7d);",

        # Pattern performance indexes
        "CREATE INDEX IF NOT EXISTS idx_pattern_performance_signature ON learning_intelligence.pattern_performance(pattern_signature);",
        "CREATE INDEX IF NOT EXISTS idx_pattern_performance_success_rate ON learning_intelligence.pattern_performance(success_rate);",

        # Explosive patterns indexes
        "CREATE INDEX IF NOT EXISTS idx_explosive_patterns_symbol ON learning_intelligence.explosive_patterns(symbol);",

        # Position tracking indexes
        "CREATE INDEX IF NOT EXISTS idx_position_tracking_symbol ON learning_intelligence.position_tracking(symbol);",
        "CREATE INDEX IF NOT EXISTS idx_position_tracking_alpaca_order ON learning_intelligence.position_tracking(alpaca_order_id);",
        "CREATE INDEX IF NOT EXISTS idx_position_tracking_discovery_source ON learning_intelligence.position_tracking(discovery_source);",
        "CREATE INDEX IF NOT EXISTS idx_explosive_patterns_date ON learning_intelligence.explosive_patterns(discovery_date);",
        "CREATE INDEX IF NOT EXISTS idx_explosive_patterns_success ON learning_intelligence.explosive_patterns(pattern_success);",

        # Market regimes indexes
        "CREATE INDEX IF NOT EXISTS idx_market_regimes_date ON learning_intelligence.market_regimes(regime_date);",
        "CREATE INDEX IF NOT EXISTS idx_market_regimes_type ON learning_intelligence.market_regimes(regime_type);",

        # Discovery performance indexes
        "CREATE INDEX IF NOT EXISTS idx_discovery_performance_date ON learning_intelligence.discovery_performance(discovery_date);",

        # Thesis accuracy indexes
        "CREATE INDEX IF NOT EXISTS idx_thesis_accuracy_symbol ON learning_intelligence.thesis_accuracy(symbol);",
        "CREATE INDEX IF NOT EXISTS idx_thesis_accuracy_date ON learning_intelligence.thesis_accuracy(thesis_date);",

        # Feature importance indexes
        "CREATE INDEX IF NOT EXISTS idx_feature_importance_name ON learning_intelligence.feature_importance(feature_name);",
        "CREATE INDEX IF NOT EXISTS idx_feature_importance_regime ON learning_intelligence.feature_importance(market_regime);",

        # Learning insights indexes
        "CREATE INDEX IF NOT EXISTS idx_learning_insights_type ON learning_intelligence.learning_insights(insight_type);",
        "CREATE INDEX IF NOT EXISTS idx_learning_insights_regime ON learning_intelligence.learning_insights(applicable_regime);"
    ]

    for index_sql in indexes:
        await conn.execute(index_sql)

# Public function to initialize database
async def init_learning_database():
    """Public function to initialize learning database"""
    return await initialize_learning_database()

if __name__ == "__main__":
    # For direct execution
    async def main():
        success = await initialize_learning_database()
        if success:
            print("✅ Learning database initialized successfully")
        else:
            print("❌ Failed to initialize learning database")

    asyncio.run(main())