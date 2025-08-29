#!/usr/bin/env python3
"""
Pattern Memory API Routes
Provides access to pattern learning, evolution tracking, and alerting system.
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Dict, Optional
import json
import asyncio
from datetime import datetime, timedelta
from ..services.pattern_learner import get_pattern_learner
from ..services.feedback_integration import get_feedback_integrator
from ..shared.database import get_db_pool

router = APIRouter()

@router.post("/initialize")
async def initialize_pattern_memory():
    """Initialize pattern memory system with database schema and reference patterns"""
    try:
        pattern_learner = await get_pattern_learner()
        success = await pattern_learner.initialize_pattern_memory()
        
        if success:
            return {
                "success": True,
                "message": "Pattern memory system initialized successfully",
                "reference_patterns": ["VIGL", "CRWV"],
                "system_status": "active"
            }
        else:
            return {"success": False, "error": "Pattern memory initialization failed"}
            
    except Exception as e:
        return {"success": False, "error": f"Initialization error: {str(e)}"}

@router.post("/log-trade-entry")
async def log_trade_entry(
    symbol: str,
    trade_data: Dict = Body(...)
):
    """Log trade entry with pattern data for learning"""
    try:
        feedback_integrator = await get_feedback_integrator()
        result = await feedback_integrator.log_trade_entry(symbol, trade_data)
        
        return {
            "success": result.get('success', False),
            "entry_logged": result.get('entry_logged', False),
            "pattern_hash": result.get('pattern_hash'),
            "tracking_active": result.get('tracking_active', False),
            "message": "Trade entry logged for pattern learning"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error logging trade entry: {str(e)}")

@router.post("/log-trade-exit")
async def log_trade_exit(
    symbol: str,
    exit_data: Dict = Body(...)
):
    """Log trade exit and trigger pattern learning"""
    try:
        feedback_integrator = await get_feedback_integrator()
        result = await feedback_integrator.log_trade_exit(symbol, exit_data)
        
        return {
            "success": result.get('success', False),
            "exit_logged": result.get('exit_logged', False),
            "performance_summary": result.get('performance_summary'),
            "learning_result": result.get('learning_result'),
            "pattern_updated": result.get('pattern_updated', False),
            "message": "Trade exit logged and pattern learning triggered"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error logging trade exit: {str(e)}")

@router.get("/similar-patterns")
async def find_similar_patterns(
    symbol: str,
    volume_spike: float = Query(..., description="Volume spike ratio vs 30-day average"),
    short_interest: float = Query(0.0, description="Short interest percentage"),
    float_shares: int = Query(50000000, description="Float size in shares"),
    squeeze_score: float = Query(0.0, description="Overall squeeze score"),
    price: float = Query(5.0, description="Current stock price"),
    min_similarity: float = Query(0.80, description="Minimum similarity threshold")
):
    """Find historical patterns similar to current opportunity"""
    try:
        pattern_learner = await get_pattern_learner()
        
        current_data = {
            'symbol': symbol,
            'volume_spike': volume_spike,
            'short_interest': short_interest,
            'float_shares': float_shares,
            'squeeze_score': squeeze_score,
            'price': price
        }
        
        similar_patterns = await pattern_learner.find_similar_patterns(
            current_data, min_similarity
        )
        
        pattern_matches = []
        for match in similar_patterns:
            pattern_matches.append({
                'historical_symbol': match.symbol,
                'similarity_score': round(match.similarity_score, 3),
                'expected_return': round(match.expected_return, 1),
                'confidence': round(match.confidence, 3),
                'historical_pattern': match.historical_pattern,
                'risk_factors': match.risk_factors
            })
        
        return {
            'success': True,
            'current_symbol': symbol,
            'similar_patterns_found': len(pattern_matches),
            'pattern_matches': pattern_matches,
            'min_similarity_used': min_similarity
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding similar patterns: {str(e)}")

@router.get("/adaptive-thresholds")
async def get_adaptive_thresholds(
    pattern_type: str = Query('squeeze', description="Pattern type for threshold adaptation")
):
    """Get adaptive detection thresholds based on recent pattern performance"""
    try:
        pattern_learner = await get_pattern_learner()
        thresholds_data = await pattern_learner.get_adaptive_thresholds(pattern_type)
        
        return {
            'success': True,
            'pattern_type': pattern_type,
            'adaptive_thresholds': thresholds_data.get('thresholds'),
            'performance_basis': thresholds_data.get('performance_basis'),
            'adjustment_reason': thresholds_data.get('adjustment_reason'),
            'last_updated': thresholds_data.get('last_updated')
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting adaptive thresholds: {str(e)}")

@router.get("/pattern-evolution")
async def detect_pattern_evolution(
    days_back: int = Query(90, description="Days to analyze for pattern evolution")
):
    """Detect how patterns are evolving over time"""
    try:
        pattern_learner = await get_pattern_learner()
        evolution_data = await pattern_learner.detect_pattern_evolution(days_back)
        
        return {
            'success': True,
            'evolution_analysis': evolution_data,
            'critical_changes_detected': evolution_data.get('evolution_detected', False),
            'analysis_period_days': days_back
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error detecting pattern evolution: {str(e)}")

@router.get("/explosive-winners")
async def get_explosive_winners(
    min_return: float = Query(100.0, description="Minimum return percentage for explosive classification"),
    days_back: int = Query(180, description="Days to look back for winners"),
    limit: int = Query(20, description="Maximum number of results")
):
    """Get historical explosive winners for pattern analysis"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            winners = await conn.fetch("""
                SELECT 
                    symbol,
                    pattern_date,
                    entry_price,
                    exit_price,
                    max_price,
                    outcome_pct,
                    max_gain_pct,
                    days_held,
                    volume_spike,
                    short_interest,
                    float_shares,
                    squeeze_score,
                    vigl_similarity,
                    pattern_hash,
                    sector,
                    notes,
                    created_at
                FROM squeeze_patterns
                WHERE explosive = TRUE 
                    AND outcome_pct >= $1
                    AND created_at >= NOW() - INTERVAL '%s days'
                ORDER BY outcome_pct DESC
                LIMIT $2
            """ % days_back, min_return, limit)
        
        explosive_winners = []
        for winner in winners:
            explosive_winners.append({
                'symbol': winner['symbol'],
                'pattern_date': winner['pattern_date'].isoformat(),
                'entry_price': float(winner['entry_price']),
                'exit_price': float(winner['exit_price']) if winner['exit_price'] else None,
                'max_price': float(winner['max_price']) if winner['max_price'] else None,
                'outcome_pct': winner['outcome_pct'],
                'max_gain_pct': winner['max_gain_pct'],
                'days_to_peak': winner['days_held'],
                'pattern_characteristics': {
                    'volume_spike': winner['volume_spike'],
                    'short_interest': winner['short_interest'],
                    'float_shares': winner['float_shares'],
                    'squeeze_score': winner['squeeze_score'],
                    'vigl_similarity': winner['vigl_similarity']
                },
                'pattern_hash': winner['pattern_hash'],
                'sector': winner['sector'],
                'discovery_notes': winner['notes'],
                'created_at': winner['created_at'].isoformat()
            })
        
        # Calculate summary statistics
        if explosive_winners:
            avg_return = sum(w['outcome_pct'] for w in explosive_winners) / len(explosive_winners)
            avg_days = sum(w['days_to_peak'] for w in explosive_winners if w['days_to_peak']) / len([w for w in explosive_winners if w['days_to_peak']])
            avg_volume_spike = sum(w['pattern_characteristics']['volume_spike'] for w in explosive_winners) / len(explosive_winners)
        else:
            avg_return = avg_days = avg_volume_spike = 0
        
        return {
            'success': True,
            'explosive_winners': explosive_winners,
            'total_found': len(explosive_winners),
            'analysis_summary': {
                'avg_return_pct': round(avg_return, 1),
                'avg_days_to_peak': round(avg_days, 1),
                'avg_volume_spike': round(avg_volume_spike, 1),
                'min_return_threshold': min_return,
                'analysis_period_days': days_back
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting explosive winners: {str(e)}")

@router.get("/pattern-failures")
async def get_pattern_failures(
    max_loss: float = Query(-20.0, description="Maximum loss percentage (negative number)"),
    days_back: int = Query(90, description="Days to look back for failures"),
    limit: int = Query(15, description="Maximum number of results")
):
    """Get pattern failures for learning what doesn't work"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            failures = await conn.fetch("""
                SELECT 
                    symbol,
                    pattern_date,
                    entry_price,
                    exit_price,
                    outcome_pct,
                    days_held,
                    volume_spike,
                    short_interest,
                    float_shares,
                    squeeze_score,
                    pattern_hash,
                    sector,
                    notes,
                    created_at
                FROM squeeze_patterns
                WHERE success = FALSE 
                    AND outcome_pct <= $1
                    AND created_at >= NOW() - INTERVAL '%s days'
                ORDER BY outcome_pct ASC
                LIMIT $2
            """ % days_back, max_loss, limit)
        
        pattern_failures = []
        for failure in failures:
            pattern_failures.append({
                'symbol': failure['symbol'],
                'pattern_date': failure['pattern_date'].isoformat(),
                'entry_price': float(failure['entry_price']),
                'exit_price': float(failure['exit_price']) if failure['exit_price'] else None,
                'loss_pct': failure['outcome_pct'],
                'days_held': failure['days_held'],
                'failed_characteristics': {
                    'volume_spike': failure['volume_spike'],
                    'short_interest': failure['short_interest'],
                    'float_shares': failure['float_shares'],
                    'squeeze_score': failure['squeeze_score']
                },
                'pattern_hash': failure['pattern_hash'],
                'sector': failure['sector'],
                'failure_analysis': failure['notes'],
                'created_at': failure['created_at'].isoformat()
            })
        
        # Identify common failure patterns
        common_factors = {}
        if pattern_failures:
            # Analyze common characteristics in failures
            low_volume_failures = len([f for f in pattern_failures if f['failed_characteristics']['volume_spike'] < 10])
            low_squeeze_failures = len([f for f in pattern_failures if f['failed_characteristics']['squeeze_score'] < 0.5])
            large_float_failures = len([f for f in pattern_failures if f['failed_characteristics']['float_shares'] > 100000000])
            
            common_factors = {
                'low_volume_spike_rate': low_volume_failures / len(pattern_failures),
                'low_squeeze_score_rate': low_squeeze_failures / len(pattern_failures),
                'large_float_rate': large_float_failures / len(pattern_failures),
                'avg_loss_pct': sum(f['loss_pct'] for f in pattern_failures) / len(pattern_failures)
            }
        
        return {
            'success': True,
            'pattern_failures': pattern_failures,
            'total_found': len(pattern_failures),
            'failure_analysis': {
                'common_failure_factors': common_factors,
                'max_loss_threshold': max_loss,
                'analysis_period_days': days_back,
                'learning_insights': [
                    f"Low volume spike in {common_factors.get('low_volume_spike_rate', 0):.1%} of failures",
                    f"Low squeeze score in {common_factors.get('low_squeeze_score_rate', 0):.1%} of failures",
                    f"Large float size in {common_factors.get('large_float_rate', 0):.1%} of failures"
                ] if common_factors else []
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting pattern failures: {str(e)}")

@router.get("/alerts")
async def get_pattern_alerts(
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    unresolved_only: bool = Query(True, description="Show only unresolved alerts"),
    days_back: int = Query(30, description="Days to look back for alerts")
):
    """Get pattern-related alerts and notifications"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            query = """
                SELECT 
                    id,
                    alert_type,
                    pattern_type,
                    alert_level,
                    message,
                    details,
                    acknowledged,
                    resolved,
                    created_at,
                    acknowledged_at,
                    resolved_at
                FROM pattern_alerts
                WHERE created_at >= NOW() - INTERVAL '%s days'
            """ % days_back
            
            params = []
            if alert_type:
                query += " AND alert_type = $1"
                params.append(alert_type)
            
            if unresolved_only:
                query += f" AND resolved = ${'2' if alert_type else '1'}"
                params.append(False)
            
            query += " ORDER BY created_at DESC LIMIT 50"
            
            alerts = await conn.fetch(query, *params)
        
        alert_list = []
        for alert in alerts:
            alert_data = {
                'id': alert['id'],
                'alert_type': alert['alert_type'],
                'pattern_type': alert['pattern_type'],
                'alert_level': alert['alert_level'],
                'message': alert['message'],
                'details': json.loads(alert['details']) if alert['details'] else {},
                'status': {
                    'acknowledged': alert['acknowledged'],
                    'resolved': alert['resolved'],
                    'created_at': alert['created_at'].isoformat(),
                    'acknowledged_at': alert['acknowledged_at'].isoformat() if alert['acknowledged_at'] else None,
                    'resolved_at': alert['resolved_at'].isoformat() if alert['resolved_at'] else None
                }
            }
            alert_list.append(alert_data)
        
        # Count alerts by type and level
        alert_counts = {}
        level_counts = {}
        for alert in alert_list:
            alert_type = alert['alert_type']
            alert_level = alert['alert_level']
            
            alert_counts[alert_type] = alert_counts.get(alert_type, 0) + 1
            level_counts[alert_level] = level_counts.get(alert_level, 0) + 1
        
        return {
            'success': True,
            'alerts': alert_list,
            'total_alerts': len(alert_list),
            'alert_summary': {
                'by_type': alert_counts,
                'by_level': level_counts,
                'unresolved_count': len([a for a in alert_list if not a['status']['resolved']])
            },
            'filters_applied': {
                'alert_type': alert_type,
                'unresolved_only': unresolved_only,
                'days_back': days_back
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting pattern alerts: {str(e)}")

@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int):
    """Acknowledge a pattern alert"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE pattern_alerts 
                SET acknowledged = TRUE, acknowledged_at = NOW()
                WHERE id = $1 AND acknowledged = FALSE
            """, alert_id)
            
            if result == "UPDATE 0":
                raise HTTPException(status_code=404, detail="Alert not found or already acknowledged")
        
        return {
            'success': True,
            'alert_id': alert_id,
            'acknowledged_at': datetime.now().isoformat(),
            'message': 'Alert acknowledged successfully'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error acknowledging alert: {str(e)}")

@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: int):
    """Mark a pattern alert as resolved"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE pattern_alerts 
                SET resolved = TRUE, resolved_at = NOW(),
                    acknowledged = TRUE, acknowledged_at = COALESCE(acknowledged_at, NOW())
                WHERE id = $1 AND resolved = FALSE
            """, alert_id)
            
            if result == "UPDATE 0":
                raise HTTPException(status_code=404, detail="Alert not found or already resolved")
        
        return {
            'success': True,
            'alert_id': alert_id,
            'resolved_at': datetime.now().isoformat(),
            'message': 'Alert resolved successfully'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resolving alert: {str(e)}")

@router.get("/performance-tracking")
async def get_active_positions_performance():
    """Get performance tracking for actively monitored positions"""
    try:
        feedback_integrator = await get_feedback_integrator()
        performance_data = await feedback_integrator.get_active_positions_performance()
        
        return {
            'success': performance_data.get('success', False),
            'performance_summary': performance_data.get('performance_summary'),
            'tracking_status': 'active' if performance_data.get('success') else 'error',
            'last_updated': datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting performance tracking: {str(e)}")

@router.post("/update-position-tracking")
async def update_position_tracking(
    symbol: str,
    current_price: float,
    additional_data: Optional[Dict] = None
):
    """Update position tracking with current price and performance"""
    try:
        feedback_integrator = await get_feedback_integrator()
        update_result = await feedback_integrator.update_position_tracking(
            symbol, current_price, additional_data
        )
        
        return {
            'success': update_result.get('success', False),
            'tracking_updated': update_result.get('tracking_updated', False),
            'performance': update_result.get('performance'),
            'alerts_generated': update_result.get('alerts_generated', 0),
            'updated_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating position tracking: {str(e)}")

@router.post("/trigger-learning-update")
async def trigger_periodic_learning():
    """Trigger periodic learning update based on recent outcomes"""
    try:
        feedback_integrator = await get_feedback_integrator()
        learning_result = await feedback_integrator.trigger_periodic_learning_update()
        
        return {
            'success': learning_result.get('success', False),
            'learning_summary': learning_result.get('learning_summary'),
            'evolution_detected': learning_result.get('evolution_detected', False),
            'update_timestamp': datetime.now().isoformat(),
            'message': 'Periodic learning update completed'
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error triggering learning update: {str(e)}")

@router.get("/system-health")
async def get_pattern_memory_health():
    """Get overall pattern memory system health status"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Get system statistics
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_patterns,
                    COUNT(*) FILTER (WHERE success = TRUE) as successful_patterns,
                    COUNT(*) FILTER (WHERE explosive = TRUE) as explosive_patterns,
                    COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days') as recent_patterns,
                    AVG(outcome_pct) FILTER (WHERE success = TRUE) as avg_success_return,
                    MAX(outcome_pct) as max_return_achieved
                FROM squeeze_patterns
                WHERE created_at >= NOW() - INTERVAL '365 days'
            """)
            
            # Get recent alert counts
            alert_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_alerts,
                    COUNT(*) FILTER (WHERE resolved = FALSE) as unresolved_alerts,
                    COUNT(*) FILTER (WHERE alert_level = 'CRITICAL') as critical_alerts
                FROM pattern_alerts
                WHERE created_at >= NOW() - INTERVAL '30 days'
            """)
        
        # Calculate health metrics
        total_patterns = stats['total_patterns'] or 0
        success_rate = (stats['successful_patterns'] or 0) / max(total_patterns, 1)
        explosive_rate = (stats['explosive_patterns'] or 0) / max(total_patterns, 1)
        
        # Determine system health
        if success_rate >= 0.6 and explosive_rate >= 0.15:
            health_status = 'EXCELLENT'
        elif success_rate >= 0.4 and explosive_rate >= 0.10:
            health_status = 'GOOD'
        elif success_rate >= 0.3:
            health_status = 'FAIR'
        else:
            health_status = 'NEEDS_ATTENTION'
        
        return {
            'success': True,
            'system_health': health_status,
            'pattern_statistics': {
                'total_patterns': total_patterns,
                'successful_patterns': stats['successful_patterns'] or 0,
                'explosive_patterns': stats['explosive_patterns'] or 0,
                'recent_patterns_30d': stats['recent_patterns'] or 0,
                'success_rate': round(success_rate, 3),
                'explosive_rate': round(explosive_rate, 3),
                'avg_success_return': round(stats['avg_success_return'] or 0, 1),
                'max_return_achieved': round(stats['max_return_achieved'] or 0, 1)
            },
            'alert_statistics': {
                'total_alerts_30d': alert_stats['total_alerts'] or 0,
                'unresolved_alerts': alert_stats['unresolved_alerts'] or 0,
                'critical_alerts': alert_stats['critical_alerts'] or 0
            },
            'health_assessment': {
                'learning_active': total_patterns > 0,
                'feedback_loops_working': stats['recent_patterns'] > 0,
                'pattern_evolution_tracking': True,
                'alert_system_active': True
            },
            'last_updated': datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting system health: {str(e)}")