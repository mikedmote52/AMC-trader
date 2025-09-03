#!/usr/bin/env python3
"""
AMC-TRADER Monitoring API Routes
Comprehensive monitoring endpoints for discovery pipeline, recommendation tracking, and buy-the-dip analysis
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Dict, Optional, Union
import json
import asyncio
from datetime import datetime, timedelta
from ..services.discovery_monitor import get_discovery_monitor
from ..services.recommendation_tracker import get_recommendation_tracker
from ..services.buy_the_dip_detector import get_buy_the_dip_detector
from ..shared.database import get_db_pool
from ..shared.redis_client import get_redis_client

router = APIRouter()

# ====== DISCOVERY PIPELINE MONITORING ======

@router.get("/discovery/health")
async def get_discovery_health():
    """Get current discovery pipeline health status with alerts"""
    try:
        monitor = get_discovery_monitor()
        health_status = await monitor.get_current_health_status()
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "health": health_status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get discovery health: {str(e)}")

@router.get("/discovery/flow-stats")
async def get_discovery_flow_stats(
    hours_back: int = Query(24, description="Hours to look back for flow statistics"),
    limit: int = Query(50, description="Maximum number of flow records")
):
    """Get recent discovery flow statistics showing stock filtering stages"""
    try:
        monitor = get_discovery_monitor()
        flow_stats = await monitor.get_recent_flow_stats(hours=hours_back)
        
        # Calculate summary metrics
        total_runs = len(flow_stats)
        avg_health = sum(stat.health_score for stat in flow_stats) / max(total_runs, 1)
        avg_universe = sum(stat.universe_size for stat in flow_stats) / max(total_runs, 1)
        avg_candidates = sum(stat.final_candidates for stat in flow_stats) / max(total_runs, 1)
        
        return {
            "success": True,
            "summary": {
                "total_discovery_runs": total_runs,
                "avg_health_score": round(avg_health, 3),
                "avg_universe_size": int(avg_universe),
                "avg_final_candidates": round(avg_candidates, 1),
                "time_window": f"Last {hours_back} hours"
            },
            "flow_data": [
                {
                    "timestamp": stat.timestamp,
                    "universe_size": stat.universe_size,
                    "filtering_stages": stat.filtering_stages,
                    "final_candidates": stat.final_candidates,
                    "processing_time_ms": stat.processing_time_ms,
                    "health_score": stat.health_score,
                    "alerts": stat.alerts
                } for stat in flow_stats[:limit]
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get flow stats: {str(e)}")

@router.get("/discovery/alerts")
async def get_discovery_alerts(limit: int = Query(20, description="Maximum number of alerts")):
    """Get recent discovery pipeline alerts"""
    try:
        redis = get_redis_client()
        alert_key = "amc:monitor:discovery:alerts"
        
        # Get recent alerts from Redis
        alert_data = redis.lrange(alert_key, 0, limit - 1)
        alerts = [json.loads(alert.decode() if isinstance(alert, bytes) else alert) for alert in alert_data]
        
        return {
            "success": True,
            "total_alerts": len(alerts),
            "alerts": alerts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get discovery alerts: {str(e)}")

# ====== RECOMMENDATION TRACKING & LEARNING ======

@router.get("/recommendations/missed-opportunities")
async def get_missed_opportunities(
    days_back: int = Query(30, description="Days to look back for missed opportunities"),
    min_performance: float = Query(15.0, description="Minimum performance percentage to qualify as missed")
):
    """Get missed opportunities - stocks that performed well but weren't bought"""
    try:
        tracker = get_recommendation_tracker()
        missed_opportunities = await tracker.get_missed_opportunities(days=days_back)
        
        # Filter by minimum performance if specified
        if min_performance > 0:
            missed_opportunities = [
                opp for opp in missed_opportunities 
                if opp.get('performance_30d', 0) >= min_performance
            ]
        
        return {
            "success": True,
            "total_missed": len(missed_opportunities),
            "missed_opportunities": [
                {
                    "symbol": opp['symbol'],
                    "recommendation_date": opp['recommendation_date'].isoformat() if hasattr(opp['recommendation_date'], 'isoformat') else str(opp['recommendation_date']),
                    "discovery_price": float(opp['discovery_price']),
                    "performance_30d": float(opp['performance_30d']) if opp['performance_30d'] else None,
                    "peak_return": float(opp['peak_return']) if opp['peak_return'] else None,
                    "days_to_peak": opp['days_to_peak'],
                    "discovery_reason": opp['discovery_reason'],
                    "thesis": opp['thesis'],
                    "learning_insights": json.loads(opp['learning_insights']) if isinstance(opp['learning_insights'], str) else opp['learning_insights']
                } for opp in missed_opportunities
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get missed opportunities: {str(e)}")

@router.get("/recommendations/performance-insights")
async def get_recommendation_performance_insights():
    """Get learning insights from all tracked recommendations"""
    try:
        tracker = get_recommendation_tracker()
        insights = await tracker.get_learning_insights()
        
        return {
            "success": True,
            "insights": insights,
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance insights: {str(e)}")

@router.post("/recommendations/manual-track")
async def manually_track_recommendation(
    symbol: str,
    price: float,
    score: float,
    reason: str,
    thesis: str = "",
    confidence: float = 0.0
):
    """Manually track a recommendation (for testing or manual entries)"""
    try:
        tracker = get_recommendation_tracker()
        
        candidate = {
            "symbol": symbol,
            "price": price,
            "squeeze_score": score,
            "reason": reason,
            "thesis": thesis,
            "confidence": confidence
        }
        
        rec_id = await tracker.save_recommendation(candidate, from_portfolio=False)
        
        return {
            "success": True,
            "recommendation_id": rec_id,
            "message": f"Started tracking {symbol} at ${price:.2f}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track recommendation: {str(e)}")

# ====== BUY-THE-DIP ANALYSIS ======

@router.get("/dip-analysis/opportunities")
async def get_buy_the_dip_opportunities(
    min_drop_pct: float = Query(10.0, description="Minimum price drop percentage"),
    days_back: int = Query(7, description="Days to look back for opportunities")
):
    """Get current buy-the-dip opportunities from recent analysis"""
    try:
        detector = get_buy_the_dip_detector()
        opportunities = await detector.get_recent_opportunities(
            min_drop_pct=min_drop_pct,
            days_back=days_back
        )
        
        return {
            "success": True,
            "total_opportunities": len(opportunities),
            "opportunities": [
                {
                    "symbol": opp['symbol'],
                    "analysis_date": opp['analysis_date'].isoformat() if hasattr(opp['analysis_date'], 'isoformat') else str(opp['analysis_date']),
                    "current_price": float(opp['current_price']),
                    "price_drop_pct": float(opp['price_drop_pct']),
                    "thesis_strength": opp['thesis_strength'],
                    "dip_buy_recommendation": opp['dip_buy_recommendation'],
                    "recommended_entry_price": float(opp['recommended_entry_price']) if opp['recommended_entry_price'] else None,
                    "recommended_position_size": float(opp['recommended_position_size']) if opp['recommended_position_size'] else None,
                    "risk_score": float(opp['risk_score']) if opp['risk_score'] else None,
                    "reasoning": json.loads(opp['reasoning']) if isinstance(opp['reasoning'], str) else opp['reasoning'],
                    "rsi": float(opp['rsi']) if opp['rsi'] else None,
                    "volume_spike": float(opp['volume_spike']) if opp['volume_spike'] else None
                } for opp in opportunities
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dip opportunities: {str(e)}")

@router.post("/dip-analysis/run")
async def trigger_dip_analysis(background_tasks: BackgroundTasks):
    """Trigger buy-the-dip analysis for current portfolio"""
    try:
        detector = get_buy_the_dip_detector()
        
        # Run analysis in background to avoid blocking the API
        background_tasks.add_task(detector.analyze_portfolio_dips)
        
        return {
            "success": True,
            "message": "Buy-the-dip analysis started",
            "status": "running_in_background"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger dip analysis: {str(e)}")

@router.get("/dip-analysis/history")
async def get_dip_analysis_history(
    symbol: Optional[str] = Query(None, description="Filter by specific symbol"),
    days_back: int = Query(30, description="Days to look back")
):
    """Get historical buy-the-dip analysis results"""
    try:
        pool = await get_db_pool()
        if not pool:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        async with pool.acquire() as conn:
            if symbol:
                query = """
                    SELECT * FROM monitoring.buy_the_dip_analysis 
                    WHERE symbol = $1 AND analysis_date >= $2
                    ORDER BY analysis_date DESC
                    LIMIT 100
                """
                rows = await conn.fetch(query, symbol, datetime.now() - timedelta(days=days_back))
            else:
                query = """
                    SELECT * FROM monitoring.buy_the_dip_analysis 
                    WHERE analysis_date >= $1
                    ORDER BY analysis_date DESC
                    LIMIT 100
                """
                rows = await conn.fetch(query, datetime.now() - timedelta(days=days_back))
            
            history = [dict(row) for row in rows]
            
            return {
                "success": True,
                "total_records": len(history),
                "filter": {"symbol": symbol, "days_back": days_back},
                "history": [
                    {
                        **record,
                        "analysis_date": record['analysis_date'].isoformat() if hasattr(record['analysis_date'], 'isoformat') else str(record['analysis_date']),
                        "current_price": float(record['current_price']),
                        "price_drop_pct": float(record['price_drop_pct']) if record['price_drop_pct'] else None,
                        "recommended_entry_price": float(record['recommended_entry_price']) if record['recommended_entry_price'] else None,
                        "risk_score": float(record['risk_score']) if record['risk_score'] else None,
                        "outcome_7d": float(record['outcome_7d']) if record['outcome_7d'] else None,
                        "outcome_30d": float(record['outcome_30d']) if record['outcome_30d'] else None
                    } for record in history
                ]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dip analysis history: {str(e)}")

# ====== COMPREHENSIVE MONITORING DASHBOARD ======

@router.get("/dashboard")
async def get_monitoring_dashboard():
    """Get comprehensive monitoring dashboard with all key metrics"""
    try:
        pool = await get_db_pool()
        if not pool:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        async with pool.acquire() as conn:
            # Get dashboard view data
            dashboard_data = await conn.fetchrow("SELECT * FROM monitoring.performance_dashboard")
            
            if dashboard_data:
                dashboard = dict(dashboard_data)
                return {
                    "success": True,
                    "dashboard": {
                        "discovery_health": {
                            "score": float(dashboard['discovery_health_score']) if dashboard['discovery_health_score'] else 0.0,
                            "latest_candidates": dashboard['latest_candidates_count'],
                            "universe_size": dashboard['latest_universe_size']
                        },
                        "recommendations": {
                            "missed_opportunities_30d": dashboard['missed_opportunities_30d'],
                            "avg_30d_performance": float(dashboard['avg_30d_performance']) if dashboard['avg_30d_performance'] else 0.0,
                            "success_rate_pct": float(dashboard['success_rate_pct']) if dashboard['success_rate_pct'] else 0.0
                        },
                        "buy_the_dip": {
                            "active_opportunities": dashboard['active_dip_opportunities']
                        },
                        "system_health": {
                            "critical_alerts_1h": dashboard['critical_alerts_1h']
                        },
                        "last_updated": dashboard['dashboard_updated_at'].isoformat() if hasattr(dashboard['dashboard_updated_at'], 'isoformat') else str(dashboard['dashboard_updated_at'])
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "No dashboard data available - monitoring may not be initialized"
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get monitoring dashboard: {str(e)}")

# ====== ALERTS & NOTIFICATIONS ======

@router.get("/alerts/missed-opportunities")
async def get_missed_opportunity_alerts(limit: int = Query(10, description="Maximum number of alerts")):
    """Get recent missed opportunity alerts"""
    try:
        redis = get_redis_client()
        alert_key = "amc:tracker:alerts:missed"
        
        alert_data = redis.lrange(alert_key, 0, limit - 1)
        alerts = [json.loads(alert.decode() if isinstance(alert, bytes) else alert) for alert in alert_data]
        
        return {
            "success": True,
            "total_alerts": len(alerts),
            "alerts": alerts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get missed opportunity alerts: {str(e)}")

@router.get("/alerts/system")
async def get_system_alerts(limit: int = Query(20, description="Maximum number of system alerts")):
    """Get comprehensive system alerts from all monitoring components"""
    try:
        redis = get_redis_client()
        
        # Get alerts from different sources
        discovery_alerts_key = "amc:monitor:discovery:alerts"
        missed_alerts_key = "amc:tracker:alerts:missed"
        
        discovery_alerts = redis.lrange(discovery_alerts_key, 0, limit // 2)
        missed_alerts = redis.lrange(missed_alerts_key, 0, limit // 2)
        
        all_alerts = []
        
        # Process discovery alerts
        for alert in discovery_alerts:
            alert_data = json.loads(alert.decode() if isinstance(alert, bytes) else alert)
            alert_data['source'] = 'DISCOVERY_PIPELINE'
            all_alerts.append(alert_data)
        
        # Process missed opportunity alerts
        for alert in missed_alerts:
            alert_data = json.loads(alert.decode() if isinstance(alert, bytes) else alert)
            alert_data['source'] = 'MISSED_OPPORTUNITY'
            all_alerts.append(alert_data)
        
        # Sort by timestamp (most recent first)
        all_alerts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return {
            "success": True,
            "total_alerts": len(all_alerts),
            "alerts": all_alerts[:limit]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system alerts: {str(e)}")

# ====== INITIALIZATION & HEALTH CHECKS ======

@router.post("/initialize")
async def initialize_monitoring_system():
    """Initialize the complete monitoring system"""
    try:
        # Run the database migration
        pool = await get_db_pool()
        if not pool:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        # Read and execute the migration script
        try:
            with open('/Users/michaelmote/Desktop/AMC-TRADER/database/migrations/001_monitoring_schema.sql', 'r') as f:
                migration_sql = f.read()
            
            async with pool.acquire() as conn:
                await conn.execute(migration_sql)
                
            return {
                "success": True,
                "message": "Monitoring system initialized successfully",
                "components": [
                    "Database schema created",
                    "Discovery monitoring active",
                    "Recommendation tracking enabled", 
                    "Buy-the-dip detection ready",
                    "Alert system operational"
                ]
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "Migration file not found. Please ensure 001_monitoring_schema.sql exists."
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize monitoring system: {str(e)}")

@router.get("/status")
async def get_monitoring_status():
    """Get overall monitoring system status"""
    try:
        status = {
            "monitoring_system": "operational",
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }
        
        # Check discovery monitor
        try:
            monitor = get_discovery_monitor()
            health = await monitor.get_current_health_status()
            status["components"]["discovery_monitor"] = {
                "status": health.get("status", "unknown"),
                "last_update": health.get("last_update")
            }
        except Exception as e:
            status["components"]["discovery_monitor"] = {"status": "error", "error": str(e)}
        
        # Check recommendation tracker
        try:
            tracker = get_recommendation_tracker()
            insights = await tracker.get_learning_insights()
            status["components"]["recommendation_tracker"] = {
                "status": insights.get("learning_status", "unknown"),
                "total_tracked": insights.get("total_tracked", 0)
            }
        except Exception as e:
            status["components"]["recommendation_tracker"] = {"status": "error", "error": str(e)}
        
        # Check buy-the-dip detector
        try:
            detector = get_buy_the_dip_detector()
            status["components"]["buy_the_dip_detector"] = {"status": "ready"}
        except Exception as e:
            status["components"]["buy_the_dip_detector"] = {"status": "error", "error": str(e)}
        
        return {"success": True, "status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get monitoring status: {str(e)}")