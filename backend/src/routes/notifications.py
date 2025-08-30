#!/usr/bin/env python3
"""
Notification API Routes
Manage notification system configuration and send alerts
"""

from fastapi import APIRouter, HTTPException, Body, Query
from typing import Dict, List, Optional
import json
import asyncio
from datetime import datetime
from ..services.notification_system import (
    get_notification_system, 
    NotificationMessage, 
    NotificationChannel, 
    NotificationPriority, 
    AlertType,
    NotificationConfig
)

router = APIRouter()

@router.post("/test")
async def test_notification():
    """Test notification system with sample alert"""
    try:
        notif_system = get_notification_system()
        
        result = await notif_system.send_discovery_alert(
            symbol="TEST",
            pattern_type="VIGL",
            confidence=0.92,
            price=5.67,
            volume_spike=23.4,
            thesis="Test notification from AMC-TRADER system"
        )
        
        return {
            'success': True,
            'test_result': result,
            'message': 'Test notification sent successfully'
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test notification failed: {str(e)}")

@router.post("/discovery-alert")
async def send_discovery_alert(
    symbol: str,
    pattern_type: str,
    confidence: float,
    price: float,
    volume_spike: float,
    thesis: str = ""
):
    """Send discovery pattern alert"""
    try:
        notif_system = get_notification_system()
        result = await notif_system.send_discovery_alert(
            symbol, pattern_type, confidence, price, volume_spike, thesis
        )
        
        return {
            'success': True,
            'notification_result': result,
            'alert_type': 'discovery_alert'
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Discovery alert failed: {str(e)}")

@router.post("/squeeze-alert") 
async def send_squeeze_alert(
    symbol: str,
    squeeze_score: float,
    short_interest: float,
    thesis: str = ""
):
    """Send squeeze detection alert"""
    try:
        notif_system = get_notification_system()
        result = await notif_system.send_squeeze_alert(
            symbol, squeeze_score, short_interest, thesis
        )
        
        return {
            'success': True,
            'notification_result': result,
            'alert_type': 'squeeze_alert'
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Squeeze alert failed: {str(e)}")

@router.post("/position-update")
async def send_position_update(
    symbol: str,
    current_pl: float,
    recommendation: str,
    thesis: str = ""
):
    """Send position update notification"""
    try:
        notif_system = get_notification_system()
        result = await notif_system.send_position_update(
            symbol, current_pl, recommendation, thesis
        )
        
        return {
            'success': True,
            'notification_result': result,
            'alert_type': 'position_update'
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Position update failed: {str(e)}")

@router.post("/trade-execution")
async def send_trade_execution(
    symbol: str,
    action: str,
    quantity: int,
    price: float,
    order_id: str = ""
):
    """Send trade execution confirmation"""
    try:
        notif_system = get_notification_system()
        result = await notif_system.send_trade_execution(
            symbol, action, quantity, price, order_id
        )
        
        return {
            'success': True,
            'notification_result': result,
            'alert_type': 'trade_execution'
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trade execution alert failed: {str(e)}")

@router.post("/performance-milestone")
async def send_performance_milestone(
    milestone: str,
    current_return: float,
    details: Dict = Body(...)
):
    """Send performance milestone notification"""
    try:
        notif_system = get_notification_system()
        result = await notif_system.send_performance_milestone(
            milestone, current_return, details
        )
        
        return {
            'success': True,
            'notification_result': result,
            'alert_type': 'performance_milestone'
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Performance milestone alert failed: {str(e)}")

@router.post("/custom")
async def send_custom_notification(
    title: str,
    message: str,
    alert_type: str = "custom",
    priority: str = "medium",
    channels: List[str] = Body(default=[]),
    data: Dict = Body(default={})
):
    """Send custom notification"""
    try:
        notif_system = get_notification_system()
        
        # Convert string enums
        try:
            alert_type_enum = AlertType(alert_type) if alert_type in [e.value for e in AlertType] else AlertType.DISCOVERY_ALERT
            priority_enum = NotificationPriority(priority)
            channel_enums = [NotificationChannel(ch) for ch in channels if ch in [e.value for e in NotificationChannel]]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid enum value: {str(e)}")
        
        notification = NotificationMessage(
            alert_type=alert_type_enum,
            priority=priority_enum,
            title=title,
            message=message,
            data=data,
            channels=channel_enums
        )
        
        result = await notif_system.send_notification(notification)
        
        return {
            'success': True,
            'notification_result': result,
            'alert_type': 'custom'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Custom notification failed: {str(e)}")

@router.get("/config")
async def get_notification_config():
    """Get current notification system configuration"""
    try:
        notif_system = get_notification_system()
        config = notif_system.config
        
        return {
            'success': True,
            'config': {
                'enabled_channels': [ch.value for ch in config.enabled_channels],
                'priority_filter': config.priority_filter.value,
                'rate_limit_seconds': config.rate_limit_seconds,
                'max_daily_notifications': config.max_daily_notifications,
                'sms_configured': bool(config.twilio_account_sid and config.twilio_auth_token),
                'sms_recipients_count': len(config.sms_recipients),
                'slack_configured': bool(config.slack_webhook_url),
                'slack_channel': config.slack_channel
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Config retrieval failed: {str(e)}")

@router.get("/status")
async def get_notification_status():
    """Get notification system status and recent activity"""
    try:
        notif_system = get_notification_system()
        
        # Get today's notification count
        today = datetime.now().strftime('%Y-%m-%d')
        daily_count = notif_system.daily_counts.get(today, 0)
        
        return {
            'success': True,
            'status': {
                'system_active': True,
                'daily_notifications_sent': daily_count,
                'daily_limit': notif_system.config.max_daily_notifications,
                'daily_remaining': max(0, notif_system.config.max_daily_notifications - daily_count),
                'rate_limiter_active': len(notif_system.rate_limiter) > 0,
                'twilio_client_ready': notif_system.twilio_client is not None,
                'enabled_channels': [ch.value for ch in notif_system.config.enabled_channels]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")

@router.post("/daily-summary")
async def send_daily_summary():
    """Send daily trading summary notification"""
    try:
        # This would integrate with portfolio and discovery systems
        # For now, sending a sample summary
        
        notif_system = get_notification_system()
        
        summary_data = {
            'discoveries': 12,
            'new_positions': 2,
            'portfolio_pl': 5.7,
            'best_performer': 'UP',
            'best_return': 95.0,
            'win_rate': 73.5
        }
        
        result = await notif_system.send_performance_milestone(
            milestone="Daily Trading Summary",
            current_return=summary_data['portfolio_pl'],
            details={
                'discoveries_today': summary_data['discoveries'],
                'new_positions': summary_data['new_positions'],
                'best_performer': summary_data['best_performer'],
                'best_return_pct': f"+{summary_data['best_return']}%",
                'win_rate': f"{summary_data['win_rate']}%",
                'status': 'Strong Performance' if summary_data['portfolio_pl'] > 0 else 'Recovery Mode'
            }
        )
        
        return {
            'success': True,
            'notification_result': result,
            'summary_data': summary_data,
            'alert_type': 'daily_summary'
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Daily summary failed: {str(e)}")

# Integration with discovery system
@router.post("/integrate-discovery")
async def integrate_with_discovery_pipeline():
    """Send notifications for current discovery results"""
    try:
        from ..shared.redis_client import get_redis_client
        
        # Get current discovery results
        redis_client = get_redis_client()
        discovery_data = redis_client.get("amc:discovery:contenders.latest")
        
        if not discovery_data:
            return {
                'success': False,
                'message': 'No discovery data available',
                'notifications_sent': 0
            }
        
        import json
        contenders = json.loads(discovery_data)
        
        if not contenders:
            return {
                'success': True,
                'message': 'No contenders to notify about',
                'notifications_sent': 0
            }
        
        notif_system = get_notification_system()
        notifications_sent = 0
        
        # Send notifications for high-confidence discoveries
        for contender in contenders[:3]:  # Top 3 opportunities
            if contender.get('confidence', 0) > 0.75:  # High confidence threshold
                await notif_system.send_discovery_alert(
                    symbol=contender['symbol'],
                    pattern_type=contender.get('pattern_type', 'SQUEEZE'),
                    confidence=contender.get('confidence', 0.8),
                    price=contender.get('price', 0),
                    volume_spike=contender.get('factors', {}).get('volume_spike_ratio', 1),
                    thesis=contender.get('thesis', '')[:200]
                )
                notifications_sent += 1
        
        return {
            'success': True,
            'message': f'Sent notifications for {notifications_sent} high-confidence discoveries',
            'notifications_sent': notifications_sent,
            'total_contenders': len(contenders)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Discovery integration failed: {str(e)}")