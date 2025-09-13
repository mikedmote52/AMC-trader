"""
Automated Thesis Monitoring System

Parses thesis text to extract specific criteria and creates real-time monitoring rules
for portfolio positions. Provides intelligent notifications when thesis conditions
are met or violated.
"""

import asyncio
import re
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import statistics
import logging

from .thesis_generator import ThesisGenerator
from .thesis_accuracy_tracker import ThesisAccuracyTracker

logger = logging.getLogger(__name__)

class MonitoringCondition(Enum):
    """Types of monitoring conditions that can be extracted from thesis"""
    MOMENTUM_CONTINUE = "momentum_continue"
    SIGNS_OF_TOPPING = "signs_of_topping"
    MOMENTUM_ACCELERATION = "momentum_acceleration"
    MOMENTUM_STALLING = "momentum_stalling"
    VOLUME_EXPANSION = "volume_expansion"
    VOLUME_DECLINE = "volume_decline"
    PRICE_BREAKOUT = "price_breakout"
    PRICE_BREAKDOWN = "price_breakdown"
    SUPPORT_HOLD = "support_hold"
    RESISTANCE_BREAK = "resistance_break"
    PROFIT_TAKING = "profit_taking"
    STOP_LOSS_TRIGGER = "stop_loss_trigger"

class AlertPriority(Enum):
    """Alert priority levels"""
    CRITICAL = "critical"    # Immediate action required (stop loss, major breakdown)
    HIGH = "high"           # Important thesis milestone (breakout, topping signs)
    MEDIUM = "medium"       # Moderate importance (momentum changes)
    LOW = "low"             # Informational (small movements)

@dataclass
class ThesisCondition:
    """Individual monitoring condition extracted from thesis"""
    condition_type: MonitoringCondition
    description: str
    threshold_value: Optional[float] = None
    threshold_type: str = "percentage"  # percentage, price, volume_ratio, etc.
    comparison: str = "greater_than"  # greater_than, less_than, equals, range
    timeframe: str = "1d"  # 1d, 1h, 15m, etc.
    priority: AlertPriority = AlertPriority.MEDIUM
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MonitoringRule:
    """Complete monitoring rule for a thesis"""
    symbol: str
    thesis_id: str
    thesis_text: str
    conditions: List[ThesisCondition]
    created_at: datetime
    last_checked: Optional[datetime] = None
    status: str = "active"  # active, triggered, expired, disabled
    expiry_date: Optional[datetime] = None

@dataclass
class ThesisAlert:
    """Alert generated when thesis condition is met"""
    symbol: str
    thesis_id: str
    condition: ThesisCondition
    current_value: float
    threshold_value: float
    message: str
    priority: AlertPriority
    triggered_at: datetime
    market_context: Dict[str, Any] = field(default_factory=dict)
    
class ThesisTextParser:
    """Parse thesis text to extract actionable monitoring conditions"""
    
    def __init__(self):
        # Regex patterns for extracting specific conditions
        self.patterns = {
            # Momentum patterns
            MonitoringCondition.MOMENTUM_CONTINUE: [
                r"let momentum continue",
                r"momentum continuing",
                r"maintain momentum",
                r"positive momentum building"
            ],
            
            MonitoringCondition.SIGNS_OF_TOPPING: [
                r"signs of topping",
                r"topping signals",
                r"exhaustion signs",
                r"momentum slowing",
                r"pace slowing"
            ],
            
            MonitoringCondition.MOMENTUM_ACCELERATION: [
                r"momentum accelerat",
                r"acceleration",
                r"gaining steam",
                r"building momentum"
            ],
            
            MonitoringCondition.MOMENTUM_STALLING: [
                r"momentum stall",
                r"stalling",
                r"losing steam",
                r"fading momentum"
            ],
            
            # Volume patterns
            MonitoringCondition.VOLUME_EXPANSION: [
                r"volume expansion",
                r"volume increasing",
                r"volume surge",
                r"high volume"
            ],
            
            MonitoringCondition.VOLUME_DECLINE: [
                r"volume decline",
                r"low volume",
                r"volume drying up",
                r"reduced volume"
            ],
            
            # Price action patterns
            MonitoringCondition.PRICE_BREAKOUT: [
                r"breakout",
                r"breaking out",
                r"above resistance",
                r"new highs"
            ],
            
            MonitoringCondition.PRICE_BREAKDOWN: [
                r"breakdown",
                r"breaking down",
                r"below support",
                r"new lows"
            ],
            
            # Risk management patterns
            MonitoringCondition.PROFIT_TAKING: [
                r"profit.taking",
                r"take profits",
                r"trim position",
                r"lock in gains"
            ],
            
            MonitoringCondition.STOP_LOSS_TRIGGER: [
                r"stop.loss",
                r"cut losses",
                r"exit position",
                r"preserve capital"
            ]
        }
        
        # Threshold extraction patterns
        self.threshold_patterns = [
            r"([+-]?\d+\.?\d*)%",  # Percentage thresholds
            r"\$(\d+\.?\d*)",      # Price thresholds
            r"(\d+\.?\d*)x",       # Ratio thresholds
        ]
    
    def parse_thesis(self, thesis_text: str, symbol: str) -> List[ThesisCondition]:
        """Parse thesis text to extract monitoring conditions"""
        conditions = []
        thesis_lower = thesis_text.lower()
        
        for condition_type, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, thesis_lower):
                    # Extract threshold if present nearby
                    threshold_value = self._extract_threshold_near_pattern(thesis_text, pattern)
                    
                    # Determine priority based on condition type
                    priority = self._determine_priority(condition_type, thesis_text)
                    
                    # Extract timeframe context
                    timeframe = self._extract_timeframe(thesis_text)
                    
                    condition = ThesisCondition(
                        condition_type=condition_type,
                        description=f"{symbol}: {pattern} condition detected",
                        threshold_value=threshold_value,
                        priority=priority,
                        timeframe=timeframe,
                        metadata={
                            "original_text": thesis_text,
                            "pattern_matched": pattern,
                            "context": self._extract_context(thesis_text, pattern)
                        }
                    )
                    conditions.append(condition)
                    break  # Only match first pattern per condition type
        
        return conditions
    
    def _extract_threshold_near_pattern(self, text: str, pattern: str) -> Optional[float]:
        """Extract numerical threshold near a matched pattern"""
        # Find the pattern location
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            return None
            
        # Look for thresholds within 50 characters of the pattern
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 50)
        context = text[start:end]
        
        # Try different threshold patterns
        for threshold_pattern in self.threshold_patterns:
            threshold_match = re.search(threshold_pattern, context)
            if threshold_match:
                try:
                    return float(threshold_match.group(1))
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _determine_priority(self, condition_type: MonitoringCondition, thesis_text: str) -> AlertPriority:
        """Determine alert priority based on condition type and context"""
        # Critical conditions
        if condition_type in [MonitoringCondition.STOP_LOSS_TRIGGER, MonitoringCondition.PRICE_BREAKDOWN]:
            return AlertPriority.CRITICAL
            
        # High priority conditions
        if condition_type in [MonitoringCondition.SIGNS_OF_TOPPING, MonitoringCondition.PROFIT_TAKING, 
                              MonitoringCondition.PRICE_BREAKOUT]:
            return AlertPriority.HIGH
            
        # Context-based priority adjustment
        if any(word in thesis_text.lower() for word in ["critical", "urgent", "immediate"]):
            return AlertPriority.CRITICAL
        elif any(word in thesis_text.lower() for word in ["important", "key", "major"]):
            return AlertPriority.HIGH
            
        return AlertPriority.MEDIUM
    
    def _extract_timeframe(self, thesis_text: str) -> str:
        """Extract timeframe from thesis text"""
        timeframe_patterns = [
            (r"(\d+)\s*day", "d"),
            (r"(\d+)\s*hour", "h"), 
            (r"(\d+)\s*minute", "m"),
            (r"intraday", "1d"),
            (r"short.term", "1d"),
            (r"medium.term", "7d"),
            (r"long.term", "30d")
        ]
        
        for pattern, default_frame in timeframe_patterns:
            match = re.search(pattern, thesis_text.lower())
            if match:
                if match.groups():
                    return f"{match.group(1)}{default_frame[-1]}"
                return default_frame
                
        return "1d"  # Default timeframe
    
    def _extract_context(self, text: str, pattern: str) -> str:
        """Extract context around a matched pattern"""
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            return ""
            
        start = max(0, match.start() - 30)
        end = min(len(text), match.end() + 30)
        return text[start:end].strip()

class MarketDataProvider:
    """Provide real-time market data for condition checking"""
    
    def __init__(self, polygon_api_key: str = None):
        self.polygon_api_key = polygon_api_key
    
    async def get_current_metrics(self, symbol: str) -> Dict[str, Any]:
        """Get current market metrics for a symbol"""
        try:
            # Use enhanced BMS engine
            from .bms_engine_enhanced import EnhancedBMSEngine
            
            if self.polygon_api_key:
                bms_engine = EnhancedBMSEngine(self.polygon_api_key)
                market_data = await bms_engine.get_real_market_data(symbol)
                
                if market_data:
                    return {
                        "price": market_data.get("price", 0.0),
                        "volume_ratio": market_data.get("rel_volume_30d", 1.0),
                        "momentum_1d": market_data.get("momentum_1d", 0.0),
                        "momentum_5d": market_data.get("momentum_5d", 0.0),
                        "rsi": market_data.get("rsi_14", 50.0),
                        "price_change_pct": market_data.get("price_change_pct", 0.0),
                        "volume": market_data.get("volume", 0),
                        "avg_volume": market_data.get("avg_volume_30d", 0),
                        "high_52w": market_data.get("high_52w", 0.0),
                        "low_52w": market_data.get("low_52w", 0.0)
                    }
            
            # Fallback: Try to get from portfolio data
            from ..routes.portfolio import fetch_current_prices
            prices = await fetch_current_prices([symbol])
            
            return {
                "price": prices.get(symbol, 0.0),
                "volume_ratio": 1.0,  # Default values when detailed data unavailable
                "momentum_1d": 0.0,
                "momentum_5d": 0.0,
                "rsi": 50.0,
                "price_change_pct": 0.0,
                "volume": 0,
                "avg_volume": 0,
                "high_52w": 0.0,
                "low_52w": 0.0
            }
            
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {e}")
            return {
                "price": 0.0,
                "volume_ratio": 1.0,
                "momentum_1d": 0.0,
                "momentum_5d": 0.0,
                "rsi": 50.0,
                "price_change_pct": 0.0,
                "volume": 0,
                "avg_volume": 0,
                "high_52w": 0.0,
                "low_52w": 0.0
            }

class ConditionEvaluator:
    """Evaluate monitoring conditions against current market data"""
    
    def __init__(self, market_data_provider: MarketDataProvider):
        self.market_data_provider = market_data_provider
    
    async def evaluate_condition(self, symbol: str, condition: ThesisCondition) -> Tuple[bool, float, str]:
        """
        Evaluate a single condition against current market data
        Returns: (condition_met, current_value, evaluation_message)
        """
        try:
            market_data = await self.market_data_provider.get_current_metrics(symbol)
            
            # Map condition types to market data evaluation
            evaluation_map = {
                MonitoringCondition.MOMENTUM_CONTINUE: self._evaluate_momentum_continue,
                MonitoringCondition.SIGNS_OF_TOPPING: self._evaluate_signs_of_topping,
                MonitoringCondition.MOMENTUM_ACCELERATION: self._evaluate_momentum_acceleration,
                MonitoringCondition.MOMENTUM_STALLING: self._evaluate_momentum_stalling,
                MonitoringCondition.VOLUME_EXPANSION: self._evaluate_volume_expansion,
                MonitoringCondition.VOLUME_DECLINE: self._evaluate_volume_decline,
                MonitoringCondition.PRICE_BREAKOUT: self._evaluate_price_breakout,
                MonitoringCondition.PRICE_BREAKDOWN: self._evaluate_price_breakdown,
                MonitoringCondition.PROFIT_TAKING: self._evaluate_profit_taking,
                MonitoringCondition.STOP_LOSS_TRIGGER: self._evaluate_stop_loss_trigger,
            }
            
            evaluator = evaluation_map.get(condition.condition_type)
            if evaluator:
                return await evaluator(market_data, condition)
            else:
                return False, 0.0, f"Unknown condition type: {condition.condition_type}"
                
        except Exception as e:
            logger.error(f"Error evaluating condition for {symbol}: {e}")
            return False, 0.0, f"Evaluation error: {str(e)}"
    
    async def _evaluate_momentum_continue(self, data: Dict, condition: ThesisCondition) -> Tuple[bool, float, str]:
        """Evaluate momentum continuation condition"""
        momentum_1d = data.get("momentum_1d", 0.0)
        momentum_5d = data.get("momentum_5d", 0.0)
        
        # Momentum is continuing if both short and medium-term momentum are positive
        current_value = (momentum_1d + momentum_5d) / 2
        
        threshold = condition.threshold_value or 1.0  # Default 1% momentum
        condition_met = current_value > threshold
        
        message = f"Momentum: {current_value:.2f}% (1d: {momentum_1d:.2f}%, 5d: {momentum_5d:.2f}%)"
        
        return condition_met, current_value, message
    
    async def _evaluate_signs_of_topping(self, data: Dict, condition: ThesisCondition) -> Tuple[bool, float, str]:
        """Evaluate signs of topping condition"""
        rsi = data.get("rsi", 50.0)
        volume_ratio = data.get("volume_ratio", 1.0)
        momentum_1d = data.get("momentum_1d", 0.0)
        
        # Signs of topping: High RSI + declining volume + slowing momentum
        topping_score = 0
        
        if rsi > 70:  # Overbought
            topping_score += 30
        elif rsi > 60:  # Getting extended
            topping_score += 15
            
        if volume_ratio < 0.7:  # Volume declining
            topping_score += 25
        elif volume_ratio < 1.0:
            topping_score += 10
            
        if momentum_1d < 0:  # Negative momentum
            topping_score += 30
        elif momentum_1d < 2:  # Slowing momentum
            topping_score += 15
        
        threshold = condition.threshold_value or 50.0  # Default 50% topping score
        condition_met = topping_score >= threshold
        
        message = f"Topping signals: {topping_score}% (RSI: {rsi:.1f}, Volume: {volume_ratio:.2f}x, Momentum: {momentum_1d:.2f}%)"
        
        return condition_met, topping_score, message
    
    async def _evaluate_momentum_acceleration(self, data: Dict, condition: ThesisCondition) -> Tuple[bool, float, str]:
        """Evaluate momentum acceleration condition"""
        momentum_1d = data.get("momentum_1d", 0.0)
        volume_ratio = data.get("volume_ratio", 1.0)
        
        # Acceleration: Strong recent momentum + volume confirmation
        acceleration_score = momentum_1d
        
        if volume_ratio > 1.5:  # Volume expansion confirms
            acceleration_score *= 1.5
        elif volume_ratio > 1.2:
            acceleration_score *= 1.2
            
        threshold = condition.threshold_value or 3.0  # Default 3% accelerating momentum
        condition_met = acceleration_score > threshold
        
        message = f"Momentum acceleration: {acceleration_score:.2f}% (volume-adjusted)"
        
        return condition_met, acceleration_score, message
    
    async def _evaluate_momentum_stalling(self, data: Dict, condition: ThesisCondition) -> Tuple[bool, float, str]:
        """Evaluate momentum stalling condition"""
        momentum_1d = data.get("momentum_1d", 0.0)
        momentum_5d = data.get("momentum_5d", 0.0)
        volume_ratio = data.get("volume_ratio", 1.0)
        
        # Stalling: Slowing momentum + declining volume
        stalling_score = 0
        
        if momentum_1d < momentum_5d / 2:  # 1-day momentum much weaker than 5-day
            stalling_score += 40
        elif momentum_1d < momentum_5d:
            stalling_score += 20
            
        if volume_ratio < 0.8:  # Volume declining
            stalling_score += 30
            
        if momentum_1d < 1.0:  # Weak recent momentum
            stalling_score += 30
        
        threshold = condition.threshold_value or 50.0  # Default 50% stalling score
        condition_met = stalling_score >= threshold
        
        message = f"Momentum stalling: {stalling_score}% (1d: {momentum_1d:.2f}%, 5d: {momentum_5d:.2f}%, vol: {volume_ratio:.2f}x)"
        
        return condition_met, stalling_score, message
    
    async def _evaluate_volume_expansion(self, data: Dict, condition: ThesisCondition) -> Tuple[bool, float, str]:
        """Evaluate volume expansion condition"""
        volume_ratio = data.get("volume_ratio", 1.0)
        
        threshold = condition.threshold_value or 1.5  # Default 1.5x volume expansion
        condition_met = volume_ratio >= threshold
        
        message = f"Volume expansion: {volume_ratio:.2f}x average"
        
        return condition_met, volume_ratio, message
    
    async def _evaluate_volume_decline(self, data: Dict, condition: ThesisCondition) -> Tuple[bool, float, str]:
        """Evaluate volume decline condition"""
        volume_ratio = data.get("volume_ratio", 1.0)
        
        threshold = condition.threshold_value or 0.7  # Default 0.7x volume decline
        condition_met = volume_ratio <= threshold
        
        message = f"Volume decline: {volume_ratio:.2f}x average"
        
        return condition_met, volume_ratio, message
    
    async def _evaluate_price_breakout(self, data: Dict, condition: ThesisCondition) -> Tuple[bool, float, str]:
        """Evaluate price breakout condition"""
        price = data.get("price", 0.0)
        high_52w = data.get("high_52w", 0.0)
        momentum_1d = data.get("momentum_1d", 0.0)
        
        if high_52w > 0:
            proximity_to_high = (price / high_52w) * 100
            
            # Breakout: Near/above 52-week high + positive momentum
            breakout_score = proximity_to_high
            
            if momentum_1d > 2:  # Strong momentum
                breakout_score += 10
            elif momentum_1d > 0:
                breakout_score += 5
            
            threshold = condition.threshold_value or 95.0  # Default 95% of 52-week high
            condition_met = breakout_score >= threshold
            
            message = f"Price breakout: {proximity_to_high:.1f}% of 52w high (${price:.2f} vs ${high_52w:.2f})"
        else:
            condition_met = False
            proximity_to_high = 0.0
            message = "Price breakout: No 52w high data available"
        
        return condition_met, proximity_to_high, message
    
    async def _evaluate_price_breakdown(self, data: Dict, condition: ThesisCondition) -> Tuple[bool, float, str]:
        """Evaluate price breakdown condition"""
        price = data.get("price", 0.0)
        low_52w = data.get("low_52w", 0.0)
        momentum_1d = data.get("momentum_1d", 0.0)
        
        if low_52w > 0:
            distance_from_low = ((price - low_52w) / low_52w) * 100
            
            # Breakdown: Near 52-week low + negative momentum
            breakdown_risk = 100 - distance_from_low
            
            if momentum_1d < -2:  # Strong negative momentum
                breakdown_risk += 20
            elif momentum_1d < 0:
                breakdown_risk += 10
            
            threshold = condition.threshold_value or 80.0  # Default 80% breakdown risk
            condition_met = breakdown_risk >= threshold
            
            message = f"Price breakdown risk: {breakdown_risk:.1f}% ({distance_from_low:.1f}% from 52w low)"
        else:
            condition_met = False
            breakdown_risk = 0.0
            message = "Price breakdown: No 52w low data available"
        
        return condition_met, breakdown_risk, message
    
    async def _evaluate_profit_taking(self, data: Dict, condition: ThesisCondition) -> Tuple[bool, float, str]:
        """Evaluate profit taking condition"""
        # This would typically be based on position P&L, which requires position data
        # For now, use momentum and RSI as proxies
        rsi = data.get("rsi", 50.0)
        momentum_1d = data.get("momentum_1d", 0.0)
        
        # Profit taking suggested when overbought + strong gains
        profit_taking_score = 0
        
        if rsi > 80:  # Very overbought
            profit_taking_score += 50
        elif rsi > 70:  # Overbought
            profit_taking_score += 30
            
        if momentum_1d > 10:  # Strong recent gains
            profit_taking_score += 40
        elif momentum_1d > 5:
            profit_taking_score += 20
        
        threshold = condition.threshold_value or 60.0  # Default 60% profit taking score
        condition_met = profit_taking_score >= threshold
        
        message = f"Profit taking signal: {profit_taking_score}% (RSI: {rsi:.1f}, momentum: {momentum_1d:.2f}%)"
        
        return condition_met, profit_taking_score, message
    
    async def _evaluate_stop_loss_trigger(self, data: Dict, condition: ThesisCondition) -> Tuple[bool, float, str]:
        """Evaluate stop loss trigger condition"""
        momentum_1d = data.get("momentum_1d", 0.0)
        momentum_5d = data.get("momentum_5d", 0.0)
        
        # Stop loss triggered by sustained negative momentum
        loss_severity = abs(min(momentum_1d, momentum_5d, 0))
        
        threshold = condition.threshold_value or 8.0  # Default 8% stop loss
        condition_met = loss_severity >= threshold
        
        message = f"Stop loss check: {loss_severity:.2f}% decline detected"
        
        return condition_met, loss_severity, message

class ThesisMonitoringSystem:
    """Main system for automated thesis monitoring"""
    
    def __init__(self, database_url: str = None, polygon_api_key: str = None):
        self.database_url = database_url
        self.parser = ThesisTextParser()
        self.market_data_provider = MarketDataProvider(polygon_api_key)
        self.evaluator = ConditionEvaluator(self.market_data_provider)
        self.thesis_generator = ThesisGenerator()
        self.accuracy_tracker = ThesisAccuracyTracker(database_url)
        
        # In-memory storage for monitoring rules (would be in database in production)
        self.monitoring_rules: Dict[str, MonitoringRule] = {}
        self.active_alerts: List[ThesisAlert] = []
    
    async def create_monitoring_rule_from_thesis(self, symbol: str, thesis_data: Dict) -> MonitoringRule:
        """Create monitoring rule from thesis data"""
        thesis_text = thesis_data.get('thesis', '')
        thesis_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Parse thesis text to extract conditions
        conditions = self.parser.parse_thesis(thesis_text, symbol)
        
        # Set expiry based on thesis type and timeframes
        max_timeframe_days = max([self._timeframe_to_days(c.timeframe) for c in conditions] + [7])
        expiry_date = datetime.now() + timedelta(days=max_timeframe_days * 2)  # 2x max timeframe
        
        rule = MonitoringRule(
            symbol=symbol,
            thesis_id=thesis_id,
            thesis_text=thesis_text,
            conditions=conditions,
            created_at=datetime.now(),
            expiry_date=expiry_date
        )
        
        self.monitoring_rules[thesis_id] = rule
        
        logger.info(f"Created monitoring rule for {symbol} with {len(conditions)} conditions")
        
        return rule
    
    async def check_monitoring_rules(self) -> List[ThesisAlert]:
        """Check all active monitoring rules and generate alerts"""
        new_alerts = []
        
        for rule_id, rule in self.monitoring_rules.items():
            if rule.status != "active":
                continue
                
            if rule.expiry_date and rule.expiry_date < datetime.now():
                rule.status = "expired"
                continue
            
            # Check each condition in the rule
            for condition in rule.conditions:
                try:
                    condition_met, current_value, message = await self.evaluator.evaluate_condition(
                        rule.symbol, condition
                    )
                    
                    if condition_met:
                        alert = ThesisAlert(
                            symbol=rule.symbol,
                            thesis_id=rule.thesis_id,
                            condition=condition,
                            current_value=current_value,
                            threshold_value=condition.threshold_value or 0.0,
                            message=message,
                            priority=condition.priority,
                            triggered_at=datetime.now(),
                            market_context={
                                "thesis_text": rule.thesis_text,
                                "condition_description": condition.description
                            }
                        )
                        
                        new_alerts.append(alert)
                        
                        # Update rule status if critical condition triggered
                        if condition.priority == AlertPriority.CRITICAL:
                            rule.status = "triggered"
                            
                except Exception as e:
                    logger.error(f"Error checking condition for {rule.symbol}: {e}")
                    continue
            
            rule.last_checked = datetime.now()
        
        # Add to active alerts
        self.active_alerts.extend(new_alerts)
        
        # Clean up old alerts (keep last 100)
        if len(self.active_alerts) > 100:
            self.active_alerts = sorted(self.active_alerts, key=lambda x: x.triggered_at, reverse=True)[:100]
        
        return new_alerts
    
    async def get_portfolio_monitoring_summary(self) -> Dict[str, Any]:
        """Get summary of all portfolio monitoring status"""
        try:
            # Get current positions
            from ..routes.portfolio import get_holdings
            holdings_response = await get_holdings()
            
            if not holdings_response.get("success"):
                return {"error": "Could not fetch portfolio data"}
            
            positions = holdings_response["data"]["positions"]
            
            # Create or update monitoring rules for all positions
            monitoring_summary = {
                "total_positions": len(positions),
                "monitored_positions": 0,
                "active_rules": len([r for r in self.monitoring_rules.values() if r.status == "active"]),
                "recent_alerts": len([a for a in self.active_alerts if a.triggered_at > datetime.now() - timedelta(hours=24)]),
                "position_summaries": []
            }
            
            for position in positions:
                symbol = position.get("symbol", "")
                thesis = position.get("thesis", "")
                
                # Check if we have an active monitoring rule for this position
                active_rule = None
                for rule in self.monitoring_rules.values():
                    if rule.symbol == symbol and rule.status == "active":
                        active_rule = rule
                        break
                
                # If no active rule and we have a thesis, create one
                if not active_rule and thesis and len(thesis.strip()) > 20:
                    try:
                        rule = await self.create_monitoring_rule_from_thesis(symbol, {"thesis": thesis})
                        active_rule = rule
                        monitoring_summary["monitored_positions"] += 1
                    except Exception as e:
                        logger.error(f"Error creating monitoring rule for {symbol}: {e}")
                
                # Get recent alerts for this position
                position_alerts = [
                    a for a in self.active_alerts 
                    if a.symbol == symbol and a.triggered_at > datetime.now() - timedelta(hours=24)
                ]
                
                position_summary = {
                    "symbol": symbol,
                    "has_monitoring": active_rule is not None,
                    "conditions_count": len(active_rule.conditions) if active_rule else 0,
                    "recent_alerts": len(position_alerts),
                    "highest_priority_alert": max([a.priority.value for a in position_alerts], default="none"),
                    "last_checked": active_rule.last_checked.isoformat() if active_rule and active_rule.last_checked else None
                }
                
                monitoring_summary["position_summaries"].append(position_summary)
            
            return monitoring_summary
            
        except Exception as e:
            logger.error(f"Error generating portfolio monitoring summary: {e}")
            return {"error": str(e)}
    
    async def get_intelligent_notifications(self) -> List[Dict[str, Any]]:
        """Generate intelligent notifications based on thesis monitoring"""
        notifications = []
        
        # Group alerts by symbol and priority
        alerts_by_symbol = {}
        for alert in self.active_alerts:
            if alert.symbol not in alerts_by_symbol:
                alerts_by_symbol[alert.symbol] = []
            alerts_by_symbol[alert.symbol].append(alert)
        
        for symbol, alerts in alerts_by_symbol.items():
            # Get highest priority alert
            highest_priority = max([AlertPriority[a.priority.value.upper()] for a in alerts])
            
            # Count alerts by type
            alert_types = {}
            for alert in alerts:
                condition_type = alert.condition.condition_type.value
                alert_types[condition_type] = alert_types.get(condition_type, 0) + 1
            
            # Create intelligent notification
            if highest_priority == AlertPriority.CRITICAL:
                notification_title = f"🚨 CRITICAL: {symbol}"
                notification_type = "critical"
            elif highest_priority == AlertPriority.HIGH:
                notification_title = f"⚠️ ATTENTION: {symbol}"
                notification_type = "high"
            else:
                notification_title = f"📊 UPDATE: {symbol}"
                notification_type = "medium"
            
            # Generate contextual message
            latest_alert = max(alerts, key=lambda x: x.triggered_at)
            message = self._generate_contextual_message(symbol, alerts, alert_types)
            
            notification = {
                "title": notification_title,
                "message": message,
                "symbol": symbol,
                "type": notification_type,
                "priority": highest_priority.value,
                "alert_count": len(alerts),
                "triggered_at": latest_alert.triggered_at.isoformat(),
                "conditions_met": list(alert_types.keys()),
                "actionable": self._determine_if_actionable(alerts)
            }
            
            notifications.append(notification)
        
        # Sort by priority and recency
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        notifications.sort(key=lambda x: (priority_order.get(x["type"], 3), -len(x["conditions_met"])))
        
        return notifications
    
    def _generate_contextual_message(self, symbol: str, alerts: List[ThesisAlert], alert_types: Dict[str, int]) -> str:
        """Generate contextual notification message"""
        if "stop_loss_trigger" in alert_types:
            return f"{symbol} has triggered stop-loss conditions. Consider immediate position review."
        elif "signs_of_topping" in alert_types:
            return f"{symbol} showing signs of topping. Thesis validation suggests considering profit-taking."
        elif "momentum_acceleration" in alert_types:
            return f"{symbol} momentum accelerating. Thesis conditions indicate potential for continued upside."
        elif "momentum_stalling" in alert_types:
            return f"{symbol} momentum stalling. Watch for signs of reversal or consolidation."
        elif "price_breakout" in alert_types:
            return f"{symbol} achieving price breakout. Thesis suggests this could validate upward movement."
        elif "volume_expansion" in alert_types:
            return f"{symbol} seeing volume expansion. Institutional interest may be increasing."
        else:
            condition_names = [name.replace("_", " ").title() for name in alert_types.keys()]
            return f"{symbol} thesis conditions met: {', '.join(condition_names[:3])}."
    
    def _determine_if_actionable(self, alerts: List[ThesisAlert]) -> bool:
        """Determine if alerts require immediate action"""
        actionable_conditions = [
            MonitoringCondition.STOP_LOSS_TRIGGER,
            MonitoringCondition.PROFIT_TAKING,
            MonitoringCondition.PRICE_BREAKDOWN,
            MonitoringCondition.SIGNS_OF_TOPPING
        ]
        
        return any(alert.condition.condition_type in actionable_conditions for alert in alerts)
    
    def _timeframe_to_days(self, timeframe: str) -> int:
        """Convert timeframe string to days"""
        if timeframe.endswith('d'):
            return int(timeframe[:-1])
        elif timeframe.endswith('h'):
            return max(1, int(timeframe[:-1]) // 24)
        elif timeframe.endswith('m'):
            return 1
        else:
            return 7  # Default to weekly
    
    async def update_thesis_monitoring_with_performance(self, symbol: str, performance_data: Dict):
        """Update monitoring rules based on actual performance vs thesis predictions"""
        try:
            # Find active monitoring rules for this symbol
            symbol_rules = [rule for rule in self.monitoring_rules.values() 
                          if rule.symbol == symbol and rule.status == "active"]
            
            if not symbol_rules:
                return
            
            # Track thesis accuracy
            for rule in symbol_rules:
                thesis_data = {
                    "thesis": rule.thesis_text,
                    "confidence": 0.7,  # Default confidence
                    "recommendation": "MONITOR",
                    "conditions": [asdict(c) for c in rule.conditions]
                }
                
                # Use the accuracy tracker to update learning
                await self.accuracy_tracker.record_thesis_prediction(symbol, thesis_data, performance_data)
            
            logger.info(f"Updated thesis monitoring for {symbol} with performance data")
            
        except Exception as e:
            logger.error(f"Error updating thesis monitoring for {symbol}: {e}")
    
    async def get_monitoring_effectiveness_report(self) -> Dict[str, Any]:
        """Generate report on monitoring system effectiveness"""
        try:
            total_rules = len(self.monitoring_rules)
            active_rules = len([r for r in self.monitoring_rules.values() if r.status == "active"])
            triggered_rules = len([r for r in self.monitoring_rules.values() if r.status == "triggered"])
            
            # Alert statistics
            total_alerts = len(self.active_alerts)
            alerts_by_priority = {}
            for alert in self.active_alerts:
                priority = alert.priority.value
                alerts_by_priority[priority] = alerts_by_priority.get(priority, 0) + 1
            
            # Condition effectiveness
            condition_effectiveness = {}
            for alert in self.active_alerts:
                condition_type = alert.condition.condition_type.value
                condition_effectiveness[condition_type] = condition_effectiveness.get(condition_type, 0) + 1
            
            report = {
                "monitoring_rules": {
                    "total": total_rules,
                    "active": active_rules,
                    "triggered": triggered_rules,
                    "effectiveness_rate": (triggered_rules / max(total_rules, 1)) * 100
                },
                "alerts_generated": {
                    "total": total_alerts,
                    "by_priority": alerts_by_priority,
                    "recent_24h": len([a for a in self.active_alerts 
                                    if a.triggered_at > datetime.now() - timedelta(hours=24)])
                },
                "condition_effectiveness": condition_effectiveness,
                "top_performing_conditions": sorted(condition_effectiveness.items(), 
                                                  key=lambda x: x[1], reverse=True)[:5],
                "system_health": {
                    "rules_per_position": total_rules / max(len(set(r.symbol for r in self.monitoring_rules.values())), 1),
                    "alert_frequency": total_alerts / max(total_rules, 1),
                    "response_time": "Real-time",  # As monitoring is real-time
                    "accuracy_tracking": "Integrated with thesis accuracy system"
                },
                "generated_at": datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating effectiveness report: {e}")
            return {"error": str(e)}

# Helper function to create monitoring system instance
def create_thesis_monitoring_system(database_url: str = None, polygon_api_key: str = None) -> ThesisMonitoringSystem:
    """Create and configure thesis monitoring system"""
    import os
    
    database_url = database_url or os.getenv("DATABASE_URL")
    polygon_api_key = polygon_api_key or os.getenv("POLYGON_API_KEY")
    
    return ThesisMonitoringSystem(database_url, polygon_api_key)