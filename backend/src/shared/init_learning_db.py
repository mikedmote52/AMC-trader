#!/usr/bin/env python3
"""
Initialize learning system database tables
Run this script to create the required tables for the learning system
"""

import asyncio
import asyncpg
import os

async def create_learning_tables():
    """Create learning system database tables"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return False
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Create learning_decisions table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS learning_decisions (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(10) NOT NULL,
                decision_type VARCHAR(20) NOT NULL,
                recommendation_source VARCHAR(50) NOT NULL,
                confidence_score FLOAT NOT NULL,
                price_at_decision FLOAT NOT NULL,
                market_time VARCHAR(20) NOT NULL,
                reasoning TEXT,
                decision_data JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # Create learning_outcomes table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS learning_outcomes (
                id SERIAL PRIMARY KEY,
                decision_id INTEGER REFERENCES learning_decisions(id),
                symbol VARCHAR(10) NOT NULL,
                outcome_type VARCHAR(20) NOT NULL,
                price_at_outcome FLOAT NOT NULL,
                return_pct FLOAT NOT NULL,
                days_held INTEGER NOT NULL,
                market_conditions JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # Create indexes for performance
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_learning_decisions_symbol 
            ON learning_decisions(symbol);
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_learning_decisions_created_at 
            ON learning_decisions(created_at);
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_learning_outcomes_symbol 
            ON learning_outcomes(symbol);
        """)
        
        await conn.close()
        print("✅ Learning system database tables created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create learning database tables: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(create_learning_tables())