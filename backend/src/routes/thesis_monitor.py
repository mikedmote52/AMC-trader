"""
API Routes for Automated Thesis Monitoring System

Provides endpoints for creating monitoring rules, checking conditions,
and receiving intelligent notifications based on thesis criteria.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import os

from ..services.thesis_monitor import (
    ThesisMonitoringSystem, 
    create_thesis_monitoring_system,
    MonitoringRule,
    ThesisAlert,
    AlertPriority
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Global monitoring system instance
monitoring_system: Optional[ThesisMonitoringSystem] = None

def get_monitoring_system() -> ThesisMonitoringSystem:
    """Get or create monitoring system instance"""
    global monitoring_system
    if monitoring_system is None:
        monitoring_system = create_thesis_monitoring_system()
    return monitoring_system

@router.post("/create-monitoring-rule")
async def create_monitoring_rule(
    symbol: str,
    thesis_data: Dict[str, Any]
):
    """Create automated monitoring rule from thesis data"""
    try:
        system = get_monitoring_system()
        
        # Validate required fields
        if not thesis_data.get('thesis'):
            raise HTTPException(status_code=400, detail="Thesis text is required")
        
        rule = await system.create_monitoring_rule_from_thesis(symbol, thesis_data)
        
        return {
            "success": True,
            "data": {
                "rule_id": rule.thesis_id,
                "symbol": rule.symbol,
                "conditions_created": len(rule.conditions),
                "expiry_date": rule.expiry_date.isoformat() if rule.expiry_date else None,
                "conditions": [
                    {
                        "type": condition.condition_type.value,
                        "description": condition.description,
                        "threshold": condition.threshold_value,
                        "priority": condition.priority.value,
                        "timeframe": condition.timeframe
                    }
                    for condition in rule.conditions
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating monitoring rule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create monitoring rule: {str(e)}")

@router.get("/monitoring-rules")
async def get_monitoring_rules(
    symbol: Optional[str] = None,
    active_only: bool = True
):
    """Get all monitoring rules, optionally filtered by symbol"""
    try:
        system = get_monitoring_system()
        
        rules = []
        for rule_id, rule in system.monitoring_rules.items():
            if symbol and rule.symbol != symbol:
                continue
            if active_only and rule.status != "active":
                continue
                
            rule_data = {
                "rule_id": rule.thesis_id,
                "symbol": rule.symbol,
                "thesis_text": rule.thesis_text[:200] + "..." if len(rule.thesis_text) > 200 else rule.thesis_text,
                "conditions_count": len(rule.conditions),
                "status": rule.status,
                "created_at": rule.created_at.isoformat(),
                "last_checked": rule.last_checked.isoformat() if rule.last_checked else None,
                "expiry_date": rule.expiry_date.isoformat() if rule.expiry_date else None
            }
            rules.append(rule_data)
        
        return {
            "success": True,
            "data": {
                "rules": rules,
                "total_rules": len(rules),
                "filtered_by_symbol": symbol is not None,
                "active_only": active_only
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting monitoring rules: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get monitoring rules: {str(e)}")

@router.get("/monitoring-rules/{rule_id}")
async def get_monitoring_rule_detail(rule_id: str):
    """Get detailed information about a specific monitoring rule"""
    try:
        system = get_monitoring_system()
        
        rule = system.monitoring_rules.get(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="Monitoring rule not found")
        
        # Get recent alerts for this rule
        rule_alerts = [
            {
                "condition_type": alert.condition.condition_type.value,
                "message": alert.message,
                "priority": alert.priority.value,
                "current_value": alert.current_value,
                "threshold_value": alert.threshold_value,
                "triggered_at": alert.triggered_at.isoformat()
            }
            for alert in system.active_alerts
            if alert.thesis_id == rule_id and alert.triggered_at > datetime.now() - timedelta(days=7)
        ]
        
        return {
            "success": True,
            "data": {
                "rule": {
                    "rule_id": rule.thesis_id,
                    "symbol": rule.symbol,
                    "thesis_text": rule.thesis_text,
                    "status": rule.status,
                    "created_at": rule.created_at.isoformat(),
                    "last_checked": rule.last_checked.isoformat() if rule.last_checked else None,
                    "expiry_date": rule.expiry_date.isoformat() if rule.expiry_date else None,
                    "conditions": [
                        {
                            "type": condition.condition_type.value,
                            "description": condition.description,
                            "threshold_value": condition.threshold_value,
                            "threshold_type": condition.threshold_type,
                            "comparison": condition.comparison,
                            "timeframe": condition.timeframe,
                            "priority": condition.priority.value,
                            "metadata": condition.metadata
                        }
                        for condition in rule.conditions
                    ]
                },
                "recent_alerts": rule_alerts,
                "alerts_count": len(rule_alerts)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting rule detail: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get rule detail: {str(e)}")

@router.post("/check-conditions")
async def check_monitoring_conditions():
    """Manually trigger monitoring condition checks for all active rules"""
    try:
        system = get_monitoring_system()
        
        new_alerts = await system.check_monitoring_rules()
        
        # Group alerts by priority
        alerts_by_priority = {}
        for alert in new_alerts:
            priority = alert.priority.value
            if priority not in alerts_by_priority:
                alerts_by_priority[priority] = []
            alerts_by_priority[priority].append({
                "symbol": alert.symbol,
                "condition": alert.condition.condition_type.value,
                "message": alert.message,
                "current_value": alert.current_value,
                "threshold_value": alert.threshold_value,
                "triggered_at": alert.triggered_at.isoformat()
            })
        
        return {
            "success": True,
            "data": {
                "new_alerts": len(new_alerts),
                "alerts_by_priority": alerts_by_priority,
                "total_active_rules": len([r for r in system.monitoring_rules.values() if r.status == "active"]),
                "check_timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error checking conditions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check conditions: {str(e)}")

@router.get("/portfolio-monitoring")
async def get_portfolio_monitoring():
    """Get comprehensive portfolio monitoring summary"""
    try:
        system = get_monitoring_system()
        
        summary = await system.get_portfolio_monitoring_summary()
        
        return {
            "success": True,
            "data": summary
        }
        
    except Exception as e:
        logger.error(f"Error getting portfolio monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get portfolio monitoring: {str(e)}")

@router.get("/notifications")
async def get_intelligent_notifications(
    priority: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = 50
):
    """Get intelligent notifications based on thesis monitoring"""
    try:
        system = get_monitoring_system()
        
        notifications = await system.get_intelligent_notifications()
        
        # Apply filters
        if priority:
            notifications = [n for n in notifications if n["type"] == priority.lower()]
        
        if symbol:
            notifications = [n for n in notifications if n["symbol"] == symbol]
        
        # Limit results
        notifications = notifications[:limit]
        
        return {
            "success": True,
            "data": {
                "notifications": notifications,
                "total_count": len(notifications),
                "filters_applied": {
                    "priority": priority,
                    "symbol": symbol,
                    "limit": limit
                },
                "generated_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get notifications: {str(e)}")

@router.get("/alerts")
async def get_thesis_alerts(
    symbol: Optional[str] = None,
    priority: Optional[str] = None,
    hours_back: int = 24,
    limit: int = 100
):
    """Get thesis alerts with filtering options"""
    try:
        system = get_monitoring_system()
        
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        # Filter alerts
        filtered_alerts = []
        for alert in system.active_alerts:
            if alert.triggered_at < cutoff_time:
                continue
            if symbol and alert.symbol != symbol:
                continue
            if priority and alert.priority.value != priority.lower():
                continue
            
            filtered_alerts.append({
                "symbol": alert.symbol,
                "thesis_id": alert.thesis_id,
                "condition": {
                    "type": alert.condition.condition_type.value,
                    "description": alert.condition.description,
                    "priority": alert.condition.priority.value
                },
                "message": alert.message,
                "current_value": alert.current_value,
                "threshold_value": alert.threshold_value,
                "priority": alert.priority.value,
                "triggered_at": alert.triggered_at.isoformat(),
                "market_context": alert.market_context
            })
        
        # Limit and sort by recency
        filtered_alerts = sorted(filtered_alerts, key=lambda x: x["triggered_at"], reverse=True)[:limit]
        
        return {
            "success": True,
            "data": {
                "alerts": filtered_alerts,
                "total_count": len(filtered_alerts),
                "filters": {
                    "symbol": symbol,
                    "priority": priority,
                    "hours_back": hours_back,
                    "limit": limit
                },
                "query_timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")

@router.post("/update-rule/{rule_id}")
async def update_monitoring_rule(
    rule_id: str,
    status: Optional[str] = None,
    extend_expiry_days: Optional[int] = None
):
    """Update monitoring rule status or expiry"""
    try:
        system = get_monitoring_system()
        
        rule = system.monitoring_rules.get(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="Monitoring rule not found")
        
        changes_made = []
        
        if status:
            if status not in ["active", "disabled", "expired", "triggered"]:
                raise HTTPException(status_code=400, detail="Invalid status")
            rule.status = status
            changes_made.append(f"Status updated to {status}")
        
        if extend_expiry_days:
            if rule.expiry_date:
                rule.expiry_date = rule.expiry_date + timedelta(days=extend_expiry_days)
            else:
                rule.expiry_date = datetime.now() + timedelta(days=extend_expiry_days)
            changes_made.append(f"Expiry extended by {extend_expiry_days} days")
        
        return {
            "success": True,
            "data": {
                "rule_id": rule_id,
                "changes_made": changes_made,
                "updated_status": rule.status,
                "expiry_date": rule.expiry_date.isoformat() if rule.expiry_date else None,
                "updated_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error updating rule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update rule: {str(e)}")

@router.delete("/rule/{rule_id}")
async def delete_monitoring_rule(rule_id: str):
    """Delete a monitoring rule"""
    try:
        system = get_monitoring_system()
        
        if rule_id not in system.monitoring_rules:
            raise HTTPException(status_code=404, detail="Monitoring rule not found")
        
        rule = system.monitoring_rules[rule_id]
        symbol = rule.symbol
        
        # Remove the rule
        del system.monitoring_rules[rule_id]
        
        # Remove associated alerts
        system.active_alerts = [
            alert for alert in system.active_alerts 
            if alert.thesis_id != rule_id
        ]
        
        return {
            "success": True,
            "data": {
                "deleted_rule_id": rule_id,
                "symbol": symbol,
                "deleted_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error deleting rule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete rule: {str(e)}")

@router.get("/effectiveness-report")
async def get_monitoring_effectiveness_report():
    """Get effectiveness report for the monitoring system"""
    try:
        system = get_monitoring_system()
        
        report = await system.get_monitoring_effectiveness_report()
        
        return {
            "success": True,
            "data": report
        }
        
    except Exception as e:
        logger.error(f"Error generating effectiveness report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate effectiveness report: {str(e)}")

@router.post("/batch-create-rules")
async def batch_create_monitoring_rules():
    """Create monitoring rules for all current portfolio positions"""
    try:
        system = get_monitoring_system()
        
        # Get current portfolio positions
        from ..routes.portfolio import get_holdings
        holdings_response = await get_holdings()
        
        if not holdings_response.get("success"):
            raise HTTPException(status_code=500, detail="Could not fetch portfolio data")
        
        positions = holdings_response["data"]["positions"]
        
        created_rules = []
        skipped_positions = []
        
        for position in positions:
            symbol = position.get("symbol", "")
            thesis = position.get("thesis", "")
            
            # Skip if no meaningful thesis
            if not thesis or len(thesis.strip()) < 20:
                skipped_positions.append({
                    "symbol": symbol,
                    "reason": "No meaningful thesis available"
                })
                continue
            
            # Check if rule already exists
            existing_rule = None
            for rule in system.monitoring_rules.values():
                if rule.symbol == symbol and rule.status == "active":
                    existing_rule = rule
                    break
            
            if existing_rule:
                skipped_positions.append({
                    "symbol": symbol,
                    "reason": "Active monitoring rule already exists"
                })
                continue
            
            try:
                rule = await system.create_monitoring_rule_from_thesis(symbol, {"thesis": thesis})
                created_rules.append({
                    "symbol": symbol,
                    "rule_id": rule.thesis_id,
                    "conditions_count": len(rule.conditions)
                })
            except Exception as e:
                skipped_positions.append({
                    "symbol": symbol,
                    "reason": f"Error creating rule: {str(e)}"
                })
        
        return {
            "success": True,
            "data": {
                "created_rules": created_rules,
                "skipped_positions": skipped_positions,
                "total_positions": len(positions),
                "rules_created": len(created_rules),
                "positions_skipped": len(skipped_positions),
                "batch_created_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error batch creating rules: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to batch create rules: {str(e)}")

@router.post("/start-monitoring")
async def start_continuous_monitoring(background_tasks: BackgroundTasks):
    """Start continuous monitoring in the background"""
    try:
        system = get_monitoring_system()
        
        async def continuous_monitoring():
            """Background task for continuous monitoring"""
            while True:
                try:
                    await system.check_monitoring_rules()
                    # Wait 5 minutes between checks
                    await asyncio.sleep(300)
                except Exception as e:
                    logger.error(f"Error in continuous monitoring: {e}")
                    # Wait 1 minute before retrying on error
                    await asyncio.sleep(60)
        
        background_tasks.add_task(continuous_monitoring)
        
        return {
            "success": True,
            "data": {
                "message": "Continuous monitoring started",
                "check_interval": "5 minutes",
                "started_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error starting continuous monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start continuous monitoring: {str(e)}")

@router.get("/system-status")
async def get_monitoring_system_status():
    """Get current status of the monitoring system"""
    try:
        system = get_monitoring_system()
        
        # Count rules by status
        rules_by_status = {}
        for rule in system.monitoring_rules.values():
            status = rule.status
            rules_by_status[status] = rules_by_status.get(status, 0) + 1
        
        # Count alerts by priority
        alerts_by_priority = {}
        for alert in system.active_alerts:
            priority = alert.priority.value
            alerts_by_priority[priority] = alerts_by_priority.get(priority, 0) + 1
        
        # Get symbols being monitored
        monitored_symbols = list(set(rule.symbol for rule in system.monitoring_rules.values()))
        
        status = {
            "system_health": "operational",
            "monitoring_rules": {
                "total": len(system.monitoring_rules),
                "by_status": rules_by_status
            },
            "active_alerts": {
                "total": len(system.active_alerts),
                "by_priority": alerts_by_priority,
                "recent_24h": len([a for a in system.active_alerts 
                                 if a.triggered_at > datetime.now() - timedelta(hours=24)])
            },
            "monitored_positions": {
                "symbols": monitored_symbols,
                "count": len(monitored_symbols)
            },
            "system_info": {
                "monitoring_active": True,
                "parser_version": "1.0.0",
                "market_data_provider": "polygon" if os.getenv("POLYGON_API_KEY") else "fallback",
                "database_connected": bool(os.getenv("DATABASE_URL"))
            },
            "status_timestamp": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "data": status
        }
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {str(e)}")