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

# Enhanced Learning Intelligence API Endpoints

@router.get("/intelligence/discovery-parameters")
async def get_discovery_parameters():
    """Get AI-optimized discovery parameters based on learning"""
    try:
        from ..services.learning_engine import get_learning_engine

        learning_engine = await get_learning_engine()

        # Get current market regime
        regime_data = await learning_engine.detect_market_regime_change()
        current_regime = regime_data['current_regime']

        # Get adaptive parameters
        optimized_params = await learning_engine.get_adaptive_discovery_parameters(current_regime)

        return {
            "success": True,
            "data": {
                "current_regime": current_regime,
                "regime_changed": regime_data['regime_changed'],
                "optimized_parameters": optimized_params,
                "last_updated": datetime.now().isoformat(),
                "confidence": 0.8
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/intelligence/pattern-analysis")
async def get_pattern_analysis():
    """Get advanced pattern analysis and insights"""
    try:
        from ..services.learning_engine import get_learning_engine

        learning_engine = await get_learning_engine()
        analysis = await learning_engine.analyze_winning_patterns()

        return {
            "success": True,
            "data": analysis,
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/intelligence/market-regime")
async def get_market_regime():
    """Get current market regime and regime-specific insights"""
    try:
        from ..services.learning_engine import get_learning_engine

        learning_engine = await get_learning_engine()
        regime_data = await learning_engine.detect_market_regime_change()

        # Get regime-specific performance
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            regime_performance = await conn.fetchrow("""
                SELECT
                    AVG(return_7d) as avg_return_7d,
                    COUNT(*) as trade_count,
                    COUNT(CASE WHEN return_7d > 0 THEN 1 END) as win_count
                FROM learning_intelligence.trade_outcomes to
                JOIN learning_intelligence.candidate_features cf ON to.candidate_id = cf.id
                JOIN learning_intelligence.market_regimes mr ON DATE(cf.created_at) = mr.regime_date
                WHERE mr.regime_type = $1
                AND to.return_7d IS NOT NULL
            """, regime_data['current_regime'])

        regime_stats = {}
        if regime_performance and regime_performance['trade_count'] > 0:
            regime_stats = {
                "avg_return_7d": round(regime_performance['avg_return_7d'] or 0.0, 2),
                "win_rate": round((regime_performance['win_count'] / regime_performance['trade_count']) * 100, 1),
                "trade_count": regime_performance['trade_count']
            }

        return {
            "success": True,
            "data": {
                "regime_info": regime_data,
                "regime_performance": regime_stats,
                "recommendations": _get_regime_recommendations(regime_data['current_regime'])
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/intelligence/confidence-calibration")
async def get_confidence_calibration():
    """Get confidence score calibration data"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Analyze confidence vs actual performance
            calibration_data = await conn.fetch("""
                SELECT
                    CASE
                        WHEN cf.score >= 0.9 THEN '0.9+'
                        WHEN cf.score >= 0.8 THEN '0.8-0.9'
                        WHEN cf.score >= 0.7 THEN '0.7-0.8'
                        WHEN cf.score >= 0.6 THEN '0.6-0.7'
                        ELSE '<0.6'
                    END as confidence_bucket,
                    AVG(to.return_7d) as avg_return,
                    COUNT(*) as sample_size,
                    COUNT(CASE WHEN to.return_7d > 0 THEN 1 END) as positive_count
                FROM learning_intelligence.candidate_features cf
                JOIN learning_intelligence.trade_outcomes to ON cf.id = to.candidate_id
                WHERE to.return_7d IS NOT NULL
                GROUP BY confidence_bucket
                ORDER BY confidence_bucket DESC
            """)

        calibration_results = []
        for row in calibration_data:
            calibration_results.append({
                "confidence_range": row['confidence_bucket'],
                "avg_return_7d": round(row['avg_return'] or 0.0, 2),
                "success_rate": round((row['positive_count'] / row['sample_size']) * 100, 1) if row['sample_size'] > 0 else 0,
                "sample_size": row['sample_size']
            })

        return {
            "success": True,
            "data": {
                "calibration_table": calibration_results,
                "calibration_quality": "good" if len(calibration_results) >= 4 else "limited_data"
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/intelligence/track-outcome")
async def track_trade_outcome(
    symbol: str,
    entry_price: float,
    exit_price: float,
    days_held: int
):
    """Track actual trade outcome for learning"""
    try:
        from ..services.learning_integration import track_trade_outcome

        await track_trade_outcome(symbol, entry_price, exit_price, days_held)

        return {
            "success": True,
            "message": f"Outcome tracked for {symbol}",
            "return_pct": round(((exit_price - entry_price) / entry_price) * 100, 2)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/intelligence/learning-summary")
async def get_learning_summary():
    """Get comprehensive learning system summary"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Get overall stats
            summary_stats = await conn.fetchrow("""
                SELECT
                    COUNT(DISTINCT de.id) as discovery_events,
                    COUNT(DISTINCT cf.id) as candidates_tracked,
                    COUNT(DISTINCT to.id) as outcomes_recorded,
                    AVG(to.return_7d) as avg_return_7d,
                    MAX(de.event_timestamp) as last_discovery
                FROM learning_intelligence.discovery_events de
                LEFT JOIN learning_intelligence.candidate_features cf ON de.id = cf.discovery_event_id
                LEFT JOIN learning_intelligence.trade_outcomes to ON cf.id = to.candidate_id
            """)

            # Get recent learning activity
            recent_activity = await conn.fetch("""
                SELECT
                    DATE(de.event_timestamp) as activity_date,
                    COUNT(*) as discovery_count,
                    AVG(de.candidates_found) as avg_candidates
                FROM learning_intelligence.discovery_events de
                WHERE de.event_timestamp >= NOW() - INTERVAL '7 days'
                GROUP BY DATE(de.event_timestamp)
                ORDER BY activity_date DESC
            """)

        return {
            "success": True,
            "data": {
                "system_stats": {
                    "discovery_events_tracked": summary_stats['discovery_events'] or 0,
                    "candidates_analyzed": summary_stats['candidates_tracked'] or 0,
                    "trade_outcomes_recorded": summary_stats['outcomes_recorded'] or 0,
                    "avg_7d_return": round(summary_stats['avg_return_7d'] or 0.0, 2),
                    "last_discovery": summary_stats['last_discovery'].isoformat() if summary_stats['last_discovery'] else None
                },
                "recent_activity": [
                    {
                        "date": row['activity_date'].isoformat(),
                        "discoveries": row['discovery_count'],
                        "avg_candidates": round(row['avg_candidates'] or 0.0, 1)
                    }
                    for row in recent_activity
                ],
                "learning_status": "active" if summary_stats['discovery_events'] and summary_stats['discovery_events'] > 0 else "initializing"
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def _get_regime_recommendations(regime: str) -> Dict[str, str]:
    """Get trading recommendations for specific market regime"""

    recommendations = {
        "explosive_bull": {
            "strategy": "Aggressive momentum plays",
            "risk_level": "High",
            "focus": "High-momentum, low-float stocks with strong volume",
            "caution": "Watch for overextension signals"
        },
        "squeeze_setup": {
            "strategy": "Squeeze catalyst plays",
            "risk_level": "Medium-High",
            "focus": "Short interest + catalyst combinations",
            "caution": "Verify catalyst authenticity"
        },
        "low_opportunity": {
            "strategy": "Defensive, high-conviction only",
            "risk_level": "Low",
            "focus": "Quality setups with strong fundamentals",
            "caution": "Reduce position sizes"
        },
        "high_volatility": {
            "strategy": "Rapid momentum trades",
            "risk_level": "Very High",
            "focus": "Quick entries and exits",
            "caution": "Use tight stops"
        }
    }

    return recommendations.get(regime, {
        "strategy": "Standard discovery approach",
        "risk_level": "Medium",
        "focus": "Balanced scoring approach",
        "caution": "Monitor market conditions"
    })