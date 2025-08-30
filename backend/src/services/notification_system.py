#!/usr/bin/env python3
"""
AMC-TRADER Notification System
Supports SMS (Twilio) and Slack notifications for trading alerts
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import aiohttp

# Optional Twilio imports
try:
    from twilio.rest import Client as TwilioClient
    from twilio.base.exceptions import TwilioException
    TWILIO_AVAILABLE = True
except ImportError:
    TwilioClient = None
    TwilioException = Exception
    TWILIO_AVAILABLE = False

logger = logging.getLogger(__name__)

class NotificationChannel(Enum):
    SMS = "sms"
    SLACK = "slack"
    EMAIL = "email"
    PUSH = "push"

class NotificationPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(Enum):
    DISCOVERY_ALERT = "discovery_alert"
    SQUEEZE_DETECTED = "squeeze_detected"
    POSITION_UPDATE = "position_update"
    TRADE_EXECUTION = "trade_execution"
    SYSTEM_ERROR = "system_error"
    PERFORMANCE_MILESTONE = "performance_milestone"

@dataclass
class NotificationConfig:
    """Notification configuration settings"""
    # SMS Configuration
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_from_number: Optional[str] = None
    sms_recipients: List[str] = field(default_factory=list)
    
    # Slack Configuration  
    slack_webhook_url: Optional[str] = None
    slack_channel: str = "#amc-trader"
    slack_username: str = "AMC-TRADER Bot"
    
    # General Settings
    enabled_channels: List[NotificationChannel] = field(default_factory=lambda: [NotificationChannel.SLACK])
    priority_filter: NotificationPriority = NotificationPriority.MEDIUM
    rate_limit_seconds: int = 60
    max_daily_notifications: int = 50

@dataclass
class NotificationMessage:
    """Individual notification message"""
    alert_type: AlertType
    priority: NotificationPriority
    title: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    channels: List[NotificationChannel] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

class NotificationSystem:
    """
    Comprehensive notification system for AMC-TRADER alerts
    Supports SMS via Twilio and Slack webhooks
    """
    
    def __init__(self, config: Optional[NotificationConfig] = None):
        self.config = config or self._load_config()
        self.twilio_client = None
        self.rate_limiter = {}
        self.daily_counts = {}
        self._initialize_clients()
    
    def _load_config(self) -> NotificationConfig:
        """Load configuration from environment variables"""
        return NotificationConfig(
            # Twilio SMS
            twilio_account_sid=os.getenv('TWILIO_ACCOUNT_SID'),
            twilio_auth_token=os.getenv('TWILIO_AUTH_TOKEN'),
            twilio_from_number=os.getenv('TWILIO_FROM_NUMBER'),
            sms_recipients=[r.strip() for r in os.getenv('SMS_RECIPIENTS', '').split(',') if r.strip()],
            
            # Slack
            slack_webhook_url=os.getenv('SLACK_WEBHOOK_URL'),
            slack_channel=os.getenv('SLACK_CHANNEL', '#amc-trader'),
            slack_username=os.getenv('SLACK_USERNAME', 'AMC-TRADER Bot'),
            
            # Settings
            enabled_channels=[
                NotificationChannel(ch.strip()) 
                for ch in os.getenv('NOTIFICATION_CHANNELS', 'slack').split(',')
            ],
            priority_filter=NotificationPriority(os.getenv('NOTIFICATION_PRIORITY_FILTER', 'medium')),
            rate_limit_seconds=int(os.getenv('NOTIFICATION_RATE_LIMIT', '60')),
            max_daily_notifications=int(os.getenv('MAX_DAILY_NOTIFICATIONS', '50'))
        )
    
    def _initialize_clients(self):
        """Initialize notification service clients"""
        # Initialize Twilio client
        if (TWILIO_AVAILABLE and 
            self.config.twilio_account_sid and 
            self.config.twilio_auth_token and 
            NotificationChannel.SMS in self.config.enabled_channels):
            try:
                self.twilio_client = TwilioClient(
                    self.config.twilio_account_sid, 
                    self.config.twilio_auth_token
                )
                logger.info("Twilio SMS client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
                self.twilio_client = None
        else:
            if not TWILIO_AVAILABLE:
                logger.warning("Twilio not available - SMS notifications disabled. Install with: pip install twilio")
            self.twilio_client = None
    
    def _should_send_notification(self, notification: NotificationMessage) -> bool:
        """Check if notification should be sent based on filters and rate limits"""
        # Priority filter
        priority_levels = {
            NotificationPriority.LOW: 0,
            NotificationPriority.MEDIUM: 1,
            NotificationPriority.HIGH: 2,
            NotificationPriority.CRITICAL: 3
        }
        
        if priority_levels[notification.priority] < priority_levels[self.config.priority_filter]:
            logger.debug(f"Notification filtered out by priority: {notification.priority}")
            return False
        
        # Rate limiting
        now = datetime.now()
        rate_key = f"{notification.alert_type.value}_{now.strftime('%Y-%m-%d_%H_%M')}"
        
        if rate_key in self.rate_limiter:
            time_since_last = (now - self.rate_limiter[rate_key]).seconds
            if time_since_last < self.config.rate_limit_seconds:
                logger.debug(f"Notification rate limited: {notification.alert_type}")
                return False
        
        # Daily limit
        daily_key = now.strftime('%Y-%m-%d')
        if daily_key not in self.daily_counts:
            self.daily_counts = {daily_key: 0}  # Reset for new day
        
        if self.daily_counts[daily_key] >= self.config.max_daily_notifications:
            logger.warning("Daily notification limit reached")
            return False
        
        # Update rate limiter and daily count
        self.rate_limiter[rate_key] = now
        self.daily_counts[daily_key] += 1
        
        return True
    
    async def send_notification(self, notification: NotificationMessage) -> Dict[str, Any]:
        """Send notification through configured channels"""
        if not self._should_send_notification(notification):
            return {'success': False, 'reason': 'filtered_or_rate_limited'}
        
        results = {}
        channels_to_use = notification.channels if notification.channels else self.config.enabled_channels
        
        # Send to each enabled channel
        for channel in channels_to_use:
            try:
                if channel == NotificationChannel.SMS:
                    result = await self._send_sms(notification)
                    results['sms'] = result
                elif channel == NotificationChannel.SLACK:
                    result = await self._send_slack(notification)
                    results['slack'] = result
                    
            except Exception as e:
                logger.error(f"Error sending {channel.value} notification: {e}")
                results[channel.value] = {'success': False, 'error': str(e)}
        
        return {
            'success': any(r.get('success', False) for r in results.values()),
            'channels': results,
            'timestamp': notification.timestamp.isoformat()
        }
    
    async def _send_sms(self, notification: NotificationMessage) -> Dict[str, Any]:
        """Send SMS notification via Twilio"""
        if not self.twilio_client or not self.config.sms_recipients:
            return {'success': False, 'reason': 'sms_not_configured'}
        
        # Format SMS message
        sms_body = f"🚨 {notification.title}\n\n{notification.message}"
        if len(sms_body) > 1600:  # SMS limit
            sms_body = sms_body[:1590] + "...[truncated]"
        
        results = []
        for recipient in self.config.sms_recipients:
            try:
                message = self.twilio_client.messages.create(
                    body=sms_body,
                    from_=self.config.twilio_from_number,
                    to=recipient
                )
                results.append({
                    'recipient': recipient,
                    'message_sid': message.sid,
                    'success': True
                })
                logger.info(f"SMS sent to {recipient}: {message.sid}")
            except TwilioException as e:
                logger.error(f"Twilio error sending to {recipient}: {e}")
                results.append({
                    'recipient': recipient,
                    'error': str(e),
                    'success': False
                })
        
        return {
            'success': any(r['success'] for r in results),
            'results': results
        }
    
    async def _send_slack(self, notification: NotificationMessage) -> Dict[str, Any]:
        """Send Slack notification via webhook"""
        if not self.config.slack_webhook_url:
            return {'success': False, 'reason': 'slack_not_configured'}
        
        # Format Slack message
        color = {
            NotificationPriority.LOW: "#36a64f",      # Green
            NotificationPriority.MEDIUM: "#ff9500",   # Orange
            NotificationPriority.HIGH: "#ff4444",     # Red
            NotificationPriority.CRITICAL: "#8B0000"  # Dark Red
        }[notification.priority]
        
        emoji = {
            AlertType.DISCOVERY_ALERT: "🎯",
            AlertType.SQUEEZE_DETECTED: "🚀",
            AlertType.POSITION_UPDATE: "📈",
            AlertType.TRADE_EXECUTION: "💰",
            AlertType.SYSTEM_ERROR: "❌",
            AlertType.PERFORMANCE_MILESTONE: "🏆"
        }.get(notification.alert_type, "📊")
        
        # Build Slack payload
        slack_payload = {
            "channel": self.config.slack_channel,
            "username": self.config.slack_username,
            "icon_emoji": emoji,
            "attachments": [
                {
                    "color": color,
                    "title": f"{emoji} {notification.title}",
                    "text": notification.message,
                    "fields": [],
                    "footer": "AMC-TRADER",
                    "ts": int(notification.timestamp.timestamp())
                }
            ]
        }
        
        # Add data fields if present
        if notification.data:
            for key, value in notification.data.items():
                slack_payload["attachments"][0]["fields"].append({
                    "title": key.replace('_', ' ').title(),
                    "value": str(value),
                    "short": True
                })
        
        # Send to Slack
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.slack_webhook_url,
                    json=slack_payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info("Slack notification sent successfully")
                        return {'success': True, 'response_status': response.status}
                    else:
                        error_text = await response.text()
                        logger.error(f"Slack webhook error: {response.status} - {error_text}")
                        return {'success': False, 'error': f"HTTP {response.status}: {error_text}"}
                        
        except asyncio.TimeoutError:
            logger.error("Slack notification timeout")
            return {'success': False, 'error': 'timeout'}
        except Exception as e:
            logger.error(f"Slack notification error: {e}")
            return {'success': False, 'error': str(e)}
    
    # Convenience methods for common alert types
    async def send_discovery_alert(self, symbol: str, pattern_type: str, confidence: float, 
                                   price: float, volume_spike: float, thesis: str = "") -> Dict[str, Any]:
        """Send discovery alert notification"""
        notification = NotificationMessage(
            alert_type=AlertType.DISCOVERY_ALERT,
            priority=NotificationPriority.HIGH if confidence > 0.8 else NotificationPriority.MEDIUM,
            title=f"New {pattern_type} Pattern Detected: {symbol}",
            message=f"🎯 **{symbol}** - {pattern_type} pattern detected!\n\n"
                   f"💪 **Confidence**: {confidence:.1%}\n"
                   f"💰 **Price**: ${price:.2f}\n"
                   f"📊 **Volume Spike**: {volume_spike:.1f}x\n"
                   f"{thesis[:200]}{'...' if len(thesis) > 200 else ''}",
            data={
                'symbol': symbol,
                'pattern_type': pattern_type,
                'confidence': f"{confidence:.1%}",
                'price': f"${price:.2f}",
                'volume_spike': f"{volume_spike:.1f}x"
            }
        )
        return await self.send_notification(notification)
    
    async def send_squeeze_alert(self, symbol: str, squeeze_score: float, 
                               short_interest: float, thesis: str = "") -> Dict[str, Any]:
        """Send squeeze detection alert"""
        notification = NotificationMessage(
            alert_type=AlertType.SQUEEZE_DETECTED,
            priority=NotificationPriority.CRITICAL if squeeze_score > 0.8 else NotificationPriority.HIGH,
            title=f"🚀 SQUEEZE ALERT: {symbol}",
            message=f"🚀 **EXTREME SQUEEZE DETECTED: {symbol}**\n\n"
                   f"⚡ **Squeeze Score**: {squeeze_score:.1%}\n"
                   f"🎯 **Short Interest**: {short_interest:.1%}\n"
                   f"💡 **Analysis**: {thesis[:150]}{'...' if len(thesis) > 150 else ''}",
            data={
                'symbol': symbol,
                'squeeze_score': f"{squeeze_score:.1%}",
                'short_interest': f"{short_interest:.1%}",
                'alert_level': 'EXTREME' if squeeze_score > 0.8 else 'HIGH'
            }
        )
        return await self.send_notification(notification)
    
    async def send_position_update(self, symbol: str, current_pl: float, 
                                  recommendation: str, thesis: str = "") -> Dict[str, Any]:
        """Send position update notification"""
        notification = NotificationMessage(
            alert_type=AlertType.POSITION_UPDATE,
            priority=NotificationPriority.HIGH if abs(current_pl) > 20 else NotificationPriority.MEDIUM,
            title=f"Position Update: {symbol}",
            message=f"📈 **{symbol} Position Update**\n\n"
                   f"💰 **Current P&L**: {current_pl:+.1f}%\n"
                   f"🎯 **Recommendation**: {recommendation}\n"
                   f"💡 **Thesis**: {thesis[:200]}{'...' if len(thesis) > 200 else ''}",
            data={
                'symbol': symbol,
                'pl_pct': f"{current_pl:+.1f}%",
                'recommendation': recommendation
            }
        )
        return await self.send_notification(notification)
    
    async def send_trade_execution(self, symbol: str, action: str, quantity: int, 
                                  price: float, order_id: str = "") -> Dict[str, Any]:
        """Send trade execution confirmation"""
        notification = NotificationMessage(
            alert_type=AlertType.TRADE_EXECUTION,
            priority=NotificationPriority.HIGH,
            title=f"Trade Executed: {action} {symbol}",
            message=f"💰 **Trade Confirmation**\n\n"
                   f"📊 **Symbol**: {symbol}\n"
                   f"⚡ **Action**: {action}\n"
                   f"📈 **Quantity**: {quantity} shares\n"
                   f"💵 **Price**: ${price:.2f}\n"
                   f"🔖 **Order ID**: {order_id}",
            data={
                'symbol': symbol,
                'action': action,
                'quantity': quantity,
                'price': f"${price:.2f}",
                'order_id': order_id
            }
        )
        return await self.send_notification(notification)
    
    async def send_performance_milestone(self, milestone: str, current_return: float, 
                                       details: Dict[str, Any]) -> Dict[str, Any]:
        """Send performance milestone notification"""
        notification = NotificationMessage(
            alert_type=AlertType.PERFORMANCE_MILESTONE,
            priority=NotificationPriority.HIGH,
            title=f"🏆 Performance Milestone: {milestone}",
            message=f"🏆 **{milestone}**\n\n"
                   f"📊 **Current Return**: {current_return:+.1f}%\n"
                   f"🎯 **Portfolio Status**: {details.get('status', 'Growing')}\n"
                   f"⭐ **Best Performer**: {details.get('best_stock', 'N/A')}\n"
                   f"📈 **Win Rate**: {details.get('win_rate', 0):.1f}%",
            data={
                'milestone': milestone,
                'return_pct': f"{current_return:+.1f}%",
                **details
            }
        )
        return await self.send_notification(notification)


# Singleton instance
_notification_system = None

def get_notification_system() -> NotificationSystem:
    """Get singleton notification system instance"""
    global _notification_system
    if _notification_system is None:
        _notification_system = NotificationSystem()
    return _notification_system


# Quick test function
async def test_notification_system():
    """Test notification system with sample alerts"""
    notif = get_notification_system()
    
    # Test discovery alert
    await notif.send_discovery_alert(
        symbol="QUBT",
        pattern_type="VIGL",
        confidence=0.89,
        price=14.20,
        volume_spike=25.7,
        thesis="Quantum computing breakthrough with institutional buying support"
    )
    
    # Test squeeze alert
    await notif.send_squeeze_alert(
        symbol="UP", 
        squeeze_score=0.87,
        short_interest=0.25,
        thesis="Cannabis sector squeeze with 34x volume surge and strong technical setup"
    )
    
    print("✅ Notification system test completed")

if __name__ == "__main__":
    asyncio.run(test_notification_system())