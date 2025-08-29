from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
import json
import asyncpg
import os
from datetime import datetime, timedelta
from ..shared.database import get_db_pool

router = APIRouter()

@router.post("/init-database")
async def init_learning_database():
    """Initialize learning system database tables"""
    try:
        pool = await get_db_pool()
        if not pool:
            return {"success": False, "error": "Database connection failed"}
        
        async with pool.acquire() as conn:
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
            
            # Create indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_learning_decisions_symbol 
                ON learning_decisions(symbol);
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_learning_outcomes_symbol 
                ON learning_outcomes(symbol);
            """)
        
        return {"success": True, "message": "Learning database tables created successfully"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

# Learning system: Track decisions, outcomes, and adapt recommendations
class LearningSystem:
    """
    Tracks portfolio decisions and outcomes to optimize future recommendations.
    
    Key learning areas:
    - Which recommendations led to gains/losses
    - Optimal timing for buy/sell decisions
    - Market condition patterns that affect performance
    - User behavior patterns and preferences
    """
    
    @staticmethod
    async def log_decision(
        symbol: str,
        decision_type: str,  # "buy", "sell", "hold", "ignore_recommendation"
        recommendation_source: str,  # "discovery", "portfolio_health", "user_manual"
        confidence_score: float,
        price_at_decision: float,
        market_time: str,  # "premarket", "open", "midday", "close", "afterhours"
        reasoning: str,
        metadata: Dict = None
    ):
        """Log a trading decision for learning purposes"""
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO learning_decisions 
                    (symbol, decision_type, recommendation_source, confidence_score, 
                     price_at_decision, market_time, reasoning, metadata, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """, symbol, decision_type, recommendation_source, confidence_score,
                    price_at_decision, market_time, reasoning, 
                    json.dumps(metadata or {}), datetime.utcnow())
        except Exception as e:
            print(f"Learning system error: {e}")

    @staticmethod
    async def log_outcome(
        symbol: str,
        decision_id: int,
        outcome_type: str,  # "gain", "loss", "neutral"
        price_at_outcome: float,
        return_pct: float,
        days_held: int,
        market_conditions: Dict = None
    ):
        """Log the outcome of a previous decision"""
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO learning_outcomes 
                    (decision_id, symbol, outcome_type, price_at_outcome, 
                     return_pct, days_held, market_conditions, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, decision_id, symbol, outcome_type, price_at_outcome,
                    return_pct, days_held, json.dumps(market_conditions or {}), 
                    datetime.utcnow())
        except Exception as e:
            print(f"Learning outcome error: {e}")

    @staticmethod
    async def get_learning_insights(days_back: int = 30) -> Dict:
        """Get insights from recent learning data"""
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Get decision success rates by type
                decision_stats = await conn.fetch("""
                    SELECT d.decision_type, d.market_time, d.recommendation_source,
                           AVG(o.return_pct) as avg_return,
                           COUNT(*) as decision_count,
                           SUM(CASE WHEN o.return_pct > 0 THEN 1 ELSE 0 END) as wins
                    FROM learning_decisions d
                    LEFT JOIN learning_outcomes o ON d.id = o.decision_id
                    WHERE d.created_at >= $1
                    GROUP BY d.decision_type, d.market_time, d.recommendation_source
                """, datetime.utcnow() - timedelta(days=days_back))
                
                # Best performing patterns
                patterns = await conn.fetch("""
                    SELECT d.reasoning, AVG(o.return_pct) as avg_return, COUNT(*) as occurrences
                    FROM learning_decisions d
                    JOIN learning_outcomes o ON d.id = o.decision_id
                    WHERE d.created_at >= $1 AND o.return_pct IS NOT NULL
                    GROUP BY d.reasoning
                    HAVING COUNT(*) >= 3
                    ORDER BY avg_return DESC
                    LIMIT 5
                """, datetime.utcnow() - timedelta(days=days_back))

                return {
                    "decision_stats": [dict(row) for row in decision_stats],
                    "best_patterns": [dict(row) for row in patterns],
                    "learning_period_days": days_back,
                    "total_decisions": len(decision_stats)
                }
        except Exception as e:
            print(f"Learning insights error: {e}")
            return {"error": str(e)}

@router.post("/log-decision")
async def log_trading_decision(
    symbol: str,
    decision_type: str,
    recommendation_source: str,
    confidence_score: float,
    price_at_decision: float,
    market_time: str,
    reasoning: str,
    metadata: Optional[Dict] = None
):
    """Log a trading decision for learning"""
    await LearningSystem.log_decision(
        symbol, decision_type, recommendation_source, confidence_score,
        price_at_decision, market_time, reasoning, metadata
    )
    return {"success": True, "message": "Decision logged for learning"}

@router.get("/insights")
async def get_learning_insights(days_back: int = 30):
    """Get learning insights from recent decisions"""
    insights = await LearningSystem.get_learning_insights(days_back)
    return {"success": True, "data": insights}

@router.get("/optimize-recommendations")
async def optimize_recommendations():
    """Get AI-optimized recommendations based on learning data"""
    insights = await LearningSystem.get_learning_insights(30)
    
    # Use learning data to optimize recommendations
    optimizations = {
        "best_market_times": [],
        "successful_patterns": [],
        "recommended_adjustments": []
    }
    
    if insights.get("decision_stats"):
        # Find best performing market times
        market_performance = {}
        for stat in insights["decision_stats"]:
            time = stat["market_time"]
            if time and stat["avg_return"]:
                if time not in market_performance:
                    market_performance[time] = []
                market_performance[time].append(stat["avg_return"])
        
        # Average returns by market time
        for time, returns in market_performance.items():
            avg_return = sum(returns) / len(returns)
            optimizations["best_market_times"].append({
                "market_time": time,
                "avg_return": round(avg_return, 2),
                "recommendation": f"{'Strong' if avg_return > 5 else 'Good' if avg_return > 0 else 'Avoid'} timing for decisions"
            })
    
    if insights.get("best_patterns"):
        optimizations["successful_patterns"] = [
            {
                "pattern": pattern["reasoning"],
                "avg_return": round(pattern["avg_return"], 2),
                "frequency": pattern["occurrences"]
            }
            for pattern in insights["best_patterns"]
        ]
    
    return {
        "success": True,
        "data": {
            "optimizations": optimizations,
            "learning_summary": f"Analyzed {insights.get('total_decisions', 0)} decisions over {insights.get('learning_period_days', 30)} days"
        }
    }