#!/usr/bin/env python3
"""
Learning Analytics API Routes
Advanced analytics and insights from the learning system for performance optimization
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
import json
import asyncio
from datetime import datetime, timedelta
from ..services.learning_engine import get_learning_engine
from ..shared.database import get_db_pool

router = APIRouter()

@router.post("/init-enhanced-learning")
async def initialize_enhanced_learning():
    """Initialize enhanced learning system with all required tables"""
    try:
        learning_engine = await get_learning_engine()
        success = await learning_engine.initialize_learning_database()
        
        if success:
            return {
                "success": True, 
                "message": "Enhanced learning system initialized successfully",
                "tables_created": [
                    "explosive_patterns",
                    "market_regimes", 
                    "thesis_accuracy",
                    "discovery_performance",
                    "pattern_features"
                ]
            }
        else:
            return {"success": False, "error": "Failed to initialize learning database"}
            
    except Exception as e:
        return {"success": False, "error": f"Learning system initialization failed: {str(e)}"}

@router.get("/explosive-patterns/winners")
async def get_explosive_winners(
    min_return: float = Query(50.0, description="Minimum return percentage"),
    days_back: int = Query(90, description="Days to look back"),
    limit: int = Query(20, description="Maximum number of results")
):
    """Get historical explosive winners to learn from their patterns"""
    try:
        pool = await get_db_pool()
        if not pool:
            raise HTTPException(status_code=500, detail="Database connection failed")
            
        async with pool.acquire() as conn:
            winners = await conn.fetch("""
                SELECT 
                    symbol,
                    discovery_date,
                    pattern_features,
                    vigl_score,
                    volume_spike_ratio,
                    price_momentum_1d,
                    price_momentum_5d,
                    atr_pct,
                    compression_pct,
                    outcome_return_pct,
                    days_to_peak,
                    market_regime
                FROM explosive_patterns
                WHERE pattern_success = true 
                    AND outcome_return_pct >= $1
                    AND discovery_date >= $2
                ORDER BY outcome_return_pct DESC
                LIMIT $3
            """, min_return, datetime.now() - timedelta(days=days_back), limit)
        
        results = []
        for winner in winners:
            pattern_features = json.loads(winner['pattern_features']) if winner['pattern_features'] else {}
            
            results.append({
                'symbol': winner['symbol'],
                'discovery_date': winner['discovery_date'].isoformat(),
                'return_pct': winner['outcome_return_pct'],
                'days_to_peak': winner['days_to_peak'],
                'pattern_features': pattern_features,
                'key_metrics': {
                    'vigl_score': winner['vigl_score'],
                    'volume_spike_ratio': winner['volume_spike_ratio'],
                    'momentum_1d': winner['price_momentum_1d'],
                    'momentum_5d': winner['price_momentum_5d'],
                    'atr_pct': winner['atr_pct'],
                    'compression_pct': winner['compression_pct']
                },
                'market_regime': winner['market_regime']
            })
        
        return {
            'success': True,
            'explosive_winners': results,
            'total_winners': len(results),
            'avg_return': sum(r['return_pct'] for r in results) / len(results) if results else 0,
            'avg_days_to_peak': sum(r['days_to_peak'] for r in results if r['days_to_peak']) / len([r for r in results if r['days_to_peak']]) if results else 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch explosive winners: {str(e)}")

@router.get("/pattern-analysis/feature-importance")
async def get_feature_importance(
    market_regime: Optional[str] = Query(None, description="Market regime filter"),
    min_correlation: float = Query(0.3, description="Minimum correlation threshold")
):
    """Get feature importance analysis for explosive pattern detection"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            query = """
                SELECT 
                    feature_name,
                    AVG(feature_weight) as avg_weight,
                    AVG(success_correlation) as avg_correlation,
                    COUNT(*) as sample_count,
                    market_regime
                FROM pattern_features
                WHERE success_correlation >= $1
            """
            params = [min_correlation]
            
            if market_regime:
                query += " AND market_regime = $2"
                params.append(market_regime)
                
            query += """
                GROUP BY feature_name, market_regime
                ORDER BY avg_correlation DESC
            """
            
            features = await conn.fetch(query, *params)
        
        feature_analysis = []
        for feature in features:
            feature_analysis.append({
                'feature_name': feature['feature_name'],
                'importance_weight': round(feature['avg_weight'], 4),
                'success_correlation': round(feature['avg_correlation'], 4),
                'sample_count': feature['sample_count'],
                'market_regime': feature['market_regime'],
                'importance_rank': len(feature_analysis) + 1
            })
        
        return {
            'success': True,
            'feature_importance': feature_analysis,
            'total_features': len(feature_analysis),
            'analysis_date': datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feature importance analysis failed: {str(e)}")

@router.get("/discovery/adaptive-parameters")
async def get_adaptive_discovery_parameters(
    market_regime: Optional[str] = Query(None, description="Override market regime")
):
    """Get adaptive discovery parameters based on learning from historical performance"""
    try:
        learning_engine = await get_learning_engine()
        adaptive_params = await learning_engine.get_adaptive_discovery_parameters(market_regime)
        
        # Get current market regime info
        regime_info = await learning_engine.detect_market_regime_change()
        
        return {
            'success': True,
            'adaptive_parameters': adaptive_params,
            'market_regime_info': regime_info,
            'parameter_source': 'learning_engine_adaptive',
            'last_updated': datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get adaptive parameters: {str(e)}")

@router.post("/discovery/log-performance")
async def log_discovery_performance(
    discovery_date: datetime,
    symbols_discovered: int,
    avg_7d_return: Optional[float] = None,
    avg_30d_return: Optional[float] = None,
    success_rate: Optional[float] = None,
    explosive_winners: int = 0,
    discovery_parameters: Optional[Dict] = None
):
    """Log discovery performance for learning optimization"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Calculate parameter effectiveness
            parameter_effectiveness = 0.5  # Default
            if success_rate is not None and avg_30d_return is not None:
                # Combine success rate and return performance
                parameter_effectiveness = min((success_rate * 0.6) + (max(0, avg_30d_return) / 50.0 * 0.4), 1.0)
            
            await conn.execute("""
                INSERT INTO discovery_performance 
                (discovery_date, discovery_parameters, symbols_discovered, avg_7d_return,
                 avg_30d_return, success_rate, explosive_winners, total_tracked, parameter_effectiveness)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
                discovery_date, json.dumps(discovery_parameters or {}), symbols_discovered,
                avg_7d_return, avg_30d_return, success_rate, explosive_winners,
                symbols_discovered, parameter_effectiveness
            )
        
        return {
            'success': True,
            'message': 'Discovery performance logged successfully',
            'performance_score': parameter_effectiveness
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log discovery performance: {str(e)}")

@router.post("/patterns/log-explosive-winner")
async def log_explosive_winner(
    symbol: str,
    discovery_features: Dict,
    outcome_return_pct: float,
    days_to_peak: int,
    max_drawdown: Optional[float] = None
):
    """Log an explosive winner for pattern learning"""
    try:
        learning_engine = await get_learning_engine()
        
        pattern = await learning_engine.learn_from_explosive_winner(
            symbol=symbol,
            discovery_features=discovery_features,
            outcome_return=outcome_return_pct,
            days_held=days_to_peak
        )
        
        return {
            'success': True,
            'message': f'Explosive winner {symbol} logged successfully',
            'pattern_confidence': pattern.pattern_confidence,
            'learning_impact': 'pattern_weights_updated'
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log explosive winner: {str(e)}")

@router.get("/thesis/accuracy-analysis")
async def get_thesis_accuracy_analysis(
    days_back: int = Query(30, description="Days to analyze"),
    recommendation_type: Optional[str] = Query(None, description="Filter by recommendation type")
):
    """Analyze thesis prediction accuracy over time"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            query = """
                SELECT 
                    recommendation,
                    AVG(accuracy_score) as avg_accuracy,
                    AVG(confidence_score) as avg_confidence,
                    COUNT(*) as total_predictions,
                    AVG(actual_return_7d) as avg_actual_return_7d,
                    AVG(actual_return_30d) as avg_actual_return_30d
                FROM thesis_accuracy
                WHERE thesis_date >= $1
            """
            params = [datetime.now() - timedelta(days=days_back)]
            
            if recommendation_type:
                query += " AND recommendation = $2"
                params.append(recommendation_type)
                
            query += " GROUP BY recommendation ORDER BY avg_accuracy DESC"
            
            accuracy_stats = await conn.fetch(query, *params)
        
        analysis_results = []
        for stat in accuracy_stats:
            analysis_results.append({
                'recommendation': stat['recommendation'],
                'accuracy_score': round(stat['avg_accuracy'], 3),
                'avg_confidence': round(stat['avg_confidence'], 3),
                'total_predictions': stat['total_predictions'],
                'avg_actual_return_7d': round(stat['avg_actual_return_7d'], 2),
                'avg_actual_return_30d': round(stat['avg_actual_return_30d'], 2),
                'confidence_calibration': 'good' if abs(stat['avg_accuracy'] - stat['avg_confidence']) < 0.2 else 'needs_adjustment'
            })
        
        return {
            'success': True,
            'thesis_accuracy_analysis': analysis_results,
            'analysis_period_days': days_back,
            'total_recommendations_analyzed': sum(r['total_predictions'] for r in analysis_results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Thesis accuracy analysis failed: {str(e)}")

@router.get("/market-regime/current")
async def get_current_market_regime():
    """Get current market regime and recent changes"""
    try:
        learning_engine = await get_learning_engine()
        regime_info = await learning_engine.detect_market_regime_change()
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Get recent regime history
            regime_history = await conn.fetch("""
                SELECT regime_date, regime_type, explosive_success_rate, avg_pattern_return
                FROM market_regimes
                ORDER BY regime_date DESC
                LIMIT 10
            """)
        
        history = []
        for regime in regime_history:
            history.append({
                'date': regime['regime_date'].isoformat(),
                'regime_type': regime['regime_type'],
                'explosive_success_rate': regime['explosive_success_rate'],
                'avg_pattern_return': regime['avg_pattern_return']
            })
        
        return {
            'success': True,
            'current_regime': regime_info,
            'regime_history': history,
            'regime_stability': len(set(r['regime_type'] for r in history[:5])) <= 2  # Stable if <= 2 different regimes in last 5 periods
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Market regime analysis failed: {str(e)}")

@router.get("/learning/performance-summary")
async def get_learning_performance_summary(days_back: int = Query(30)):
    """Get comprehensive learning system performance summary"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Get explosive pattern stats
            pattern_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_patterns,
                    COUNT(*) FILTER (WHERE pattern_success = true) as successful_patterns,
                    AVG(outcome_return_pct) FILTER (WHERE pattern_success = true) as avg_success_return,
                    MAX(outcome_return_pct) as max_return
                FROM explosive_patterns
                WHERE discovery_date >= $1
            """, datetime.now() - timedelta(days=days_back))
            
            # Get discovery performance stats
            discovery_stats = await conn.fetchrow("""
                SELECT 
                    AVG(success_rate) as avg_success_rate,
                    AVG(parameter_effectiveness) as avg_parameter_effectiveness,
                    SUM(explosive_winners) as total_explosive_winners,
                    SUM(total_tracked) as total_tracked
                FROM discovery_performance
                WHERE discovery_date >= $1
            """, datetime.now() - timedelta(days=days_back))
            
            # Get thesis accuracy stats
            thesis_stats = await conn.fetchrow("""
                SELECT 
                    AVG(accuracy_score) as avg_accuracy,
                    COUNT(*) as total_thesis_predictions
                FROM thesis_accuracy
                WHERE thesis_date >= $1
            """, datetime.now() - timedelta(days=days_back))
        
        # Calculate overall learning system health score
        health_components = []
        
        if pattern_stats and pattern_stats['total_patterns'] > 0:
            pattern_success_rate = pattern_stats['successful_patterns'] / pattern_stats['total_patterns']
            health_components.append(pattern_success_rate)
        
        if discovery_stats and discovery_stats['avg_parameter_effectiveness']:
            health_components.append(discovery_stats['avg_parameter_effectiveness'])
        
        if thesis_stats and thesis_stats['avg_accuracy']:
            health_components.append(thesis_stats['avg_accuracy'])
        
        overall_health = sum(health_components) / len(health_components) if health_components else 0.5
        
        return {
            'success': True,
            'learning_performance_summary': {
                'analysis_period_days': days_back,
                'overall_health_score': round(overall_health, 3),
                'pattern_learning': {
                    'total_patterns_tracked': pattern_stats['total_patterns'] if pattern_stats else 0,
                    'successful_patterns': pattern_stats['successful_patterns'] if pattern_stats else 0,
                    'success_rate': round(pattern_stats['successful_patterns'] / max(pattern_stats['total_patterns'], 1), 3) if pattern_stats else 0,
                    'avg_success_return': round(pattern_stats['avg_success_return'], 2) if pattern_stats and pattern_stats['avg_success_return'] else 0,
                    'max_winner_return': round(pattern_stats['max_return'], 2) if pattern_stats and pattern_stats['max_return'] else 0
                },
                'discovery_optimization': {
                    'avg_success_rate': round(discovery_stats['avg_success_rate'], 3) if discovery_stats and discovery_stats['avg_success_rate'] else 0,
                    'parameter_effectiveness': round(discovery_stats['avg_parameter_effectiveness'], 3) if discovery_stats and discovery_stats['avg_parameter_effectiveness'] else 0,
                    'total_explosive_winners': discovery_stats['total_explosive_winners'] if discovery_stats else 0,
                    'explosion_rate': round((discovery_stats['total_explosive_winners'] or 0) / max(discovery_stats['total_tracked'] or 1, 1), 3) if discovery_stats else 0
                },
                'thesis_accuracy': {
                    'avg_accuracy_score': round(thesis_stats['avg_accuracy'], 3) if thesis_stats and thesis_stats['avg_accuracy'] else 0,
                    'total_predictions': thesis_stats['total_thesis_predictions'] if thesis_stats else 0
                }
            },
            'system_status': 'excellent' if overall_health > 0.8 else 'good' if overall_health > 0.6 else 'needs_improvement'
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Performance summary failed: {str(e)}")