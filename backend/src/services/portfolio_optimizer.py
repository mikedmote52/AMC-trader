#!/usr/bin/env python3
"""
Enhanced Portfolio Optimization System for AMC-TRADER
Implements sophisticated rebalancing, stop-loss automation, and thesis-weighted allocation
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class PositionCategory(Enum):
    STRONG_PERFORMER = "strong_performer"
    DEVELOPING = "developing" 
    HIGH_RISK = "high_risk"
    CASH = "cash"

class ActionSignal(Enum):
    # Strong Performer sub-signals
    ADD_ON_STRENGTH = "add_on_strength"      # Scale in on momentum
    RIDE_AND_HOLD = "ride_and_hold"          # Maintain, no adds
    TAKE_PARTIAL_PROFITS = "take_partial_profits"  # Trim into strength
    
    # Developing position signals
    HOLD_AND_MONITOR = "hold_and_monitor"
    REVIEW_THESIS = "review_thesis"
    
    # Risk control signals
    TRIM_POSITION = "trim_position"
    STOP_LOSS = "stop_loss"
    FULL_EXIT = "full_exit"

@dataclass
class PositionAnalysis:
    """Enhanced position analysis with optimization recommendations"""
    symbol: str
    current_price: float
    position_size: float
    market_value: float
    unrealized_pl_pct: float
    
    # Thesis analysis
    thesis_strength: str  # STRONG, MODERATE, WEAK, FAILED
    confidence_score: float
    thesis_source: str
    
    # Category and action
    category: PositionCategory
    action_signal: ActionSignal
    
    # Optimization recommendations
    current_weight_pct: float
    recommended_weight_pct: float
    weight_adjustment_pct: float  # + for add, - for trim
    
    # Risk management
    stop_loss_level: float
    target_price: Optional[float]
    risk_score: float
    
    # Reasoning
    reasoning: List[str]
    optimization_priority: int  # 1=highest, 10=lowest

@dataclass
class PortfolioOptimization:
    """Complete portfolio optimization recommendation"""
    analysis_date: str
    total_portfolio_value: float
    
    # Current allocation
    current_allocation: Dict[str, float]  # category -> percentage
    
    # Target allocation
    target_allocation: Dict[str, float]
    
    # Rebalancing actions
    positions_to_trim: List[Dict[str, Any]]
    positions_to_add: List[Dict[str, Any]]
    stop_loss_alerts: List[Dict[str, Any]]
    
    # Optimization metrics
    concentration_risk: float
    diversification_score: float
    thesis_weighted_score: float
    
    # Implementation plan
    immediate_actions: List[str]
    monitoring_watchlist: List[str]
    
    reasoning: str

class PortfolioOptimizer:
    """
    Advanced portfolio optimization system with thesis weighting and automated rebalancing
    """
    
    def __init__(self):
        # Target portfolio allocation percentages
        self.target_allocations = {
            PositionCategory.STRONG_PERFORMER: 35.0,  # 30-40%
            PositionCategory.DEVELOPING: 45.0,        # 40-50% 
            PositionCategory.HIGH_RISK: 12.5,         # max 10-15%
            PositionCategory.CASH: 7.5                # 5-10%
        }
        
        # Stop-loss thresholds by confidence level
        self.stop_loss_thresholds = {
            'high_confidence': -12.0,    # ≥0.7 confidence
            'medium_confidence': -10.0,  # 0.4-0.69 confidence  
            'low_confidence': -7.0       # <0.4 confidence
        }
        
        # Position sizing limits
        self.max_position_weight = 8.0  # 8% max per position
        self.min_position_weight = 1.0  # 1% min per position
        
        # Profit-taking thresholds
        self.profit_taking_levels = {
            'partial_trim_1': 25.0,    # Trim 20% at +25%
            'partial_trim_2': 50.0,    # Trim 30% at +50% 
            'major_trim': 75.0         # Trim 40% at +75%
        }
    
    def analyze_portfolio(self, holdings: List[Dict[str, Any]]) -> PortfolioOptimization:
        """
        Comprehensive portfolio analysis with optimization recommendations
        """
        total_value = sum(pos.get('market_value', 0) for pos in holdings)
        position_analyses = []
        
        # Analyze each position
        for position in holdings:
            analysis = self._analyze_position(position, total_value)
            position_analyses.append(analysis)
        
        # Calculate portfolio metrics
        current_allocation = self._calculate_current_allocation(position_analyses)
        concentration_risk = self._calculate_concentration_risk(position_analyses)
        diversification_score = self._calculate_diversification_score(position_analyses)
        thesis_weighted_score = self._calculate_thesis_weighted_score(position_analyses)
        
        # Generate rebalancing recommendations
        positions_to_trim = self._identify_trim_candidates(position_analyses)
        positions_to_add = self._identify_add_candidates(position_analyses)
        stop_loss_alerts = self._identify_stop_loss_alerts(position_analyses)
        
        # Generate immediate action plan
        immediate_actions = self._generate_immediate_actions(
            positions_to_trim, positions_to_add, stop_loss_alerts
        )
        
        # Create monitoring watchlist
        monitoring_watchlist = self._create_monitoring_watchlist(position_analyses)
        
        return PortfolioOptimization(
            analysis_date=datetime.now().isoformat(),
            total_portfolio_value=total_value,
            current_allocation=current_allocation,
            target_allocation={cat.value: pct for cat, pct in self.target_allocations.items()},
            positions_to_trim=positions_to_trim,
            positions_to_add=positions_to_add,
            stop_loss_alerts=stop_loss_alerts,
            concentration_risk=concentration_risk,
            diversification_score=diversification_score,
            thesis_weighted_score=thesis_weighted_score,
            immediate_actions=immediate_actions,
            monitoring_watchlist=monitoring_watchlist,
            reasoning=self._generate_optimization_reasoning(
                current_allocation, concentration_risk, len(stop_loss_alerts)
            )
        )
    
    def _analyze_position(self, position: Dict[str, Any], total_value: float) -> PositionAnalysis:
        """Analyze individual position for optimization"""
        
        symbol = position.get('symbol', '')
        current_price = position.get('last_price', 0)
        market_value = position.get('market_value', 0)
        unrealized_pl_pct = position.get('unrealized_pl_pct', 0)
        confidence_score = position.get('confidence', 0.5)
        
        current_weight = (market_value / total_value * 100) if total_value > 0 else 0
        
        # Categorize position
        category = self._categorize_position(unrealized_pl_pct, confidence_score)
        
        # Determine action signal
        action_signal = self._determine_action_signal(
            unrealized_pl_pct, confidence_score, category, current_weight
        )
        
        # Calculate recommended weight
        recommended_weight = self._calculate_recommended_weight(
            category, confidence_score, unrealized_pl_pct, current_weight
        )
        
        # Risk management
        stop_loss_level = self._calculate_stop_loss_level(
            current_price, confidence_score, unrealized_pl_pct
        )
        
        target_price = self._calculate_target_price(current_price, unrealized_pl_pct)
        risk_score = self._calculate_risk_score(confidence_score, unrealized_pl_pct, current_weight)
        
        # Generate reasoning
        reasoning = self._generate_position_reasoning(
            symbol, unrealized_pl_pct, confidence_score, action_signal
        )
        
        return PositionAnalysis(
            symbol=symbol,
            current_price=current_price,
            position_size=position.get('qty', 0),
            market_value=market_value,
            unrealized_pl_pct=unrealized_pl_pct,
            thesis_strength=position.get('thesis_source', 'Unknown'),
            confidence_score=confidence_score,
            thesis_source=position.get('thesis_source', 'Unknown'),
            category=category,
            action_signal=action_signal,
            current_weight_pct=current_weight,
            recommended_weight_pct=recommended_weight,
            weight_adjustment_pct=recommended_weight - current_weight,
            stop_loss_level=stop_loss_level,
            target_price=target_price,
            risk_score=risk_score,
            reasoning=reasoning,
            optimization_priority=self._calculate_optimization_priority(action_signal, risk_score)
        )
    
    def _categorize_position(self, pl_pct: float, confidence: float) -> PositionCategory:
        """Categorize position based on performance and confidence"""
        if pl_pct >= 10.0 and confidence >= 0.6:
            return PositionCategory.STRONG_PERFORMER
        elif pl_pct <= -15.0 or confidence < 0.3:
            return PositionCategory.HIGH_RISK
        else:
            return PositionCategory.DEVELOPING
    
    def _determine_action_signal(self, pl_pct: float, confidence: float, 
                               category: PositionCategory, weight: float) -> ActionSignal:
        """Determine specific action signal for position"""
        
        if category == PositionCategory.STRONG_PERFORMER:
            if pl_pct >= 30.0:  # Significant gains
                return ActionSignal.TAKE_PARTIAL_PROFITS
            elif confidence >= 0.8 and weight < self.max_position_weight:
                return ActionSignal.ADD_ON_STRENGTH
            else:
                return ActionSignal.RIDE_AND_HOLD
        
        elif category == PositionCategory.HIGH_RISK:
            if pl_pct <= -15.0:
                return ActionSignal.STOP_LOSS
            elif confidence < 0.3:
                return ActionSignal.TRIM_POSITION
            else:
                return ActionSignal.REVIEW_THESIS
        
        else:  # DEVELOPING
            if confidence < 0.4:
                return ActionSignal.REVIEW_THESIS
            else:
                return ActionSignal.HOLD_AND_MONITOR
    
    def _calculate_recommended_weight(self, category: PositionCategory, confidence: float,
                                    pl_pct: float, current_weight: float) -> float:
        """Calculate optimal position weight based on thesis strength"""
        
        base_weight = current_weight
        
        if category == PositionCategory.STRONG_PERFORMER:
            # Scale up high-confidence winners
            if confidence >= 0.8:
                target_weight = min(self.max_position_weight, current_weight * 1.2)
            else:
                target_weight = min(self.max_position_weight * 0.8, current_weight)
                
        elif category == PositionCategory.HIGH_RISK:
            # Scale down risky positions
            if pl_pct <= -15.0:
                target_weight = max(0, current_weight * 0.3)  # Trim 70%
            elif confidence < 0.3:
                target_weight = max(self.min_position_weight, current_weight * 0.6)  # Trim 40%
            else:
                target_weight = current_weight * 0.8  # Trim 20%
                
        else:  # DEVELOPING
            # Maintain or slightly adjust
            if confidence >= 0.7:
                target_weight = min(current_weight * 1.1, self.max_position_weight * 0.8)
            elif confidence < 0.4:
                target_weight = max(current_weight * 0.8, self.min_position_weight)
            else:
                target_weight = current_weight
        
        return round(target_weight, 2)
    
    def _calculate_stop_loss_level(self, current_price: float, confidence: float, pl_pct: float) -> float:
        """Calculate dynamic stop-loss level"""
        
        # Determine threshold based on confidence
        if confidence >= 0.7:
            threshold = self.stop_loss_thresholds['high_confidence']
        elif confidence >= 0.4:
            threshold = self.stop_loss_thresholds['medium_confidence'] 
        else:
            threshold = self.stop_loss_thresholds['low_confidence']
        
        # For winners, use trailing stops
        if pl_pct > 0:
            # Trailing stop: protect 50% of gains
            protected_gain = pl_pct * 0.5
            threshold = max(threshold, -protected_gain)
        
        stop_price = current_price * (1 + threshold / 100)
        return round(stop_price, 2)
    
    def _calculate_target_price(self, current_price: float, pl_pct: float) -> Optional[float]:
        """Calculate price target for profit-taking"""
        if pl_pct < 20:  # Only set targets for positions with room to run
            return round(current_price * 1.3, 2)  # 30% upside target
        return None
    
    def _calculate_risk_score(self, confidence: float, pl_pct: float, weight: float) -> float:
        """Calculate overall risk score for position (0-1, higher = riskier)"""
        confidence_risk = 1 - confidence
        pl_risk = max(0, -pl_pct / 20)  # Normalize losses to 0-1 scale
        concentration_risk = max(0, (weight - 5) / 10)  # Risk increases above 5% weight
        
        return min(1.0, (confidence_risk * 0.4 + pl_risk * 0.4 + concentration_risk * 0.2))
    
    def _calculate_optimization_priority(self, action_signal: ActionSignal, risk_score: float) -> int:
        """Calculate optimization priority (1=highest, 10=lowest)"""
        if action_signal in [ActionSignal.STOP_LOSS, ActionSignal.FULL_EXIT]:
            return 1
        elif action_signal == ActionSignal.TAKE_PARTIAL_PROFITS:
            return 2
        elif risk_score >= 0.7:
            return 3
        elif action_signal == ActionSignal.TRIM_POSITION:
            return 4
        elif action_signal == ActionSignal.ADD_ON_STRENGTH:
            return 5
        else:
            return 7
    
    def _generate_position_reasoning(self, symbol: str, pl_pct: float, 
                                   confidence: float, action: ActionSignal) -> List[str]:
        """Generate human-readable reasoning for position recommendation"""
        reasoning = []
        
        if pl_pct >= 25:
            reasoning.append(f"{symbol}: Strong +{pl_pct:.1f}% performance validates thesis")
        elif pl_pct <= -10:
            reasoning.append(f"{symbol}: Concerning -{abs(pl_pct):.1f}% loss requires attention")
        
        if confidence >= 0.8:
            reasoning.append("High confidence thesis supports continued holding")
        elif confidence <= 0.3:
            reasoning.append("Low confidence suggests thesis may be flawed")
        
        if action == ActionSignal.TAKE_PARTIAL_PROFITS:
            reasoning.append("Take partial profits to lock in gains while maintaining exposure")
        elif action == ActionSignal.ADD_ON_STRENGTH:
            reasoning.append("Consider adding on pullbacks - momentum building")
        elif action == ActionSignal.STOP_LOSS:
            reasoning.append("URGENT: Position approaching stop-loss level")
        
        return reasoning
    
    def _calculate_current_allocation(self, positions: List[PositionAnalysis]) -> Dict[str, float]:
        """Calculate current portfolio allocation by category"""
        total_value = sum(pos.market_value for pos in positions)
        allocation = {}
        
        for category in PositionCategory:
            category_value = sum(
                pos.market_value for pos in positions 
                if pos.category == category
            )
            allocation[category.value] = round(
                (category_value / total_value * 100) if total_value > 0 else 0, 2
            )
        
        return allocation
    
    def _calculate_concentration_risk(self, positions: List[PositionAnalysis]) -> float:
        """Calculate portfolio concentration risk"""
        weights = [pos.current_weight_pct for pos in positions]
        return max(weights) if weights else 0
    
    def _calculate_diversification_score(self, positions: List[PositionAnalysis]) -> float:
        """Calculate diversification score (higher is more diversified)"""
        if len(positions) <= 1:
            return 0.0
        
        # Calculate Herfindahl-Hirschman Index (HHI)
        weights = [pos.current_weight_pct / 100 for pos in positions]
        hhi = sum(w * w for w in weights)
        
        # Convert to diversification score (0-1, higher is better)
        max_hhi = 1.0  # Perfectly concentrated
        min_hhi = 1.0 / len(positions)  # Perfectly diversified
        
        diversification = (max_hhi - hhi) / (max_hhi - min_hhi) if max_hhi > min_hhi else 0
        return round(diversification, 3)
    
    def _calculate_thesis_weighted_score(self, positions: List[PositionAnalysis]) -> float:
        """Calculate portfolio score weighted by thesis strength"""
        total_weight = sum(pos.current_weight_pct for pos in positions)
        if total_weight == 0:
            return 0
        
        weighted_score = sum(
            pos.confidence_score * pos.current_weight_pct for pos in positions
        ) / total_weight
        
        return round(weighted_score, 3)
    
    def _identify_trim_candidates(self, positions: List[PositionAnalysis]) -> List[Dict[str, Any]]:
        """Identify positions that should be trimmed"""
        candidates = []
        
        for pos in positions:
            if pos.weight_adjustment_pct < -1.0:  # Recommend trimming >1%
                trim_pct = abs(pos.weight_adjustment_pct / pos.current_weight_pct * 100)
                candidates.append({
                    'symbol': pos.symbol,
                    'current_weight': pos.current_weight_pct,
                    'target_weight': pos.recommended_weight_pct,
                    'trim_percentage': round(trim_pct, 1),
                    'reason': pos.action_signal.value,
                    'priority': pos.optimization_priority,
                    'stop_loss_level': pos.stop_loss_level
                })
        
        return sorted(candidates, key=lambda x: x['priority'])
    
    def _identify_add_candidates(self, positions: List[PositionAnalysis]) -> List[Dict[str, Any]]:
        """Identify positions that should be increased"""
        candidates = []
        
        for pos in positions:
            if pos.weight_adjustment_pct > 1.0:  # Recommend adding >1%
                add_pct = pos.weight_adjustment_pct / pos.current_weight_pct * 100
                candidates.append({
                    'symbol': pos.symbol,
                    'current_weight': pos.current_weight_pct,
                    'target_weight': pos.recommended_weight_pct,
                    'add_percentage': round(add_pct, 1),
                    'reason': pos.action_signal.value,
                    'confidence': pos.confidence_score,
                    'target_price': pos.target_price
                })
        
        return sorted(candidates, key=lambda x: x['confidence'], reverse=True)
    
    def _identify_stop_loss_alerts(self, positions: List[PositionAnalysis]) -> List[Dict[str, Any]]:
        """Identify positions approaching stop-loss levels"""
        alerts = []
        
        for pos in positions:
            if pos.action_signal in [ActionSignal.STOP_LOSS, ActionSignal.FULL_EXIT]:
                distance_to_stop = ((pos.current_price - pos.stop_loss_level) / pos.current_price) * 100
                alerts.append({
                    'symbol': pos.symbol,
                    'current_price': pos.current_price,
                    'stop_loss_level': pos.stop_loss_level,
                    'distance_pct': round(distance_to_stop, 1),
                    'unrealized_pl_pct': pos.unrealized_pl_pct,
                    'confidence': pos.confidence_score,
                    'urgency': 'HIGH' if distance_to_stop <= 2 else 'MEDIUM'
                })
        
        return sorted(alerts, key=lambda x: x['distance_pct'])
    
    def _generate_immediate_actions(self, trim_candidates: List[Dict], 
                                  add_candidates: List[Dict], 
                                  stop_loss_alerts: List[Dict]) -> List[str]:
        """Generate prioritized immediate action plan"""
        actions = []
        
        # Stop-loss alerts first
        for alert in stop_loss_alerts[:3]:  # Top 3 most urgent
            if alert['urgency'] == 'HIGH':
                actions.append(f"URGENT: {alert['symbol']} within {alert['distance_pct']}% of stop-loss")
            else:
                actions.append(f"Monitor {alert['symbol']} approaching stop-loss at ${alert['stop_loss_level']}")
        
        # High priority trims
        for candidate in trim_candidates[:3]:  # Top 3 trim priorities
            if candidate['priority'] <= 3:
                actions.append(f"Trim {candidate['symbol']} by {candidate['trim_percentage']:.1f}% - {candidate['reason']}")
        
        # High confidence adds
        for candidate in add_candidates[:2]:  # Top 2 add candidates
            if candidate['confidence'] >= 0.8:
                actions.append(f"Consider adding to {candidate['symbol']} on pullbacks - high confidence")
        
        return actions[:5]  # Limit to 5 immediate actions
    
    def _create_monitoring_watchlist(self, positions: List[PositionAnalysis]) -> List[str]:
        """Create monitoring watchlist for positions needing attention"""
        watchlist = []
        
        for pos in positions:
            if pos.action_signal == ActionSignal.REVIEW_THESIS:
                watchlist.append(f"{pos.symbol}: Review thesis (confidence: {pos.confidence_score:.2f})")
            elif pos.risk_score >= 0.6:
                watchlist.append(f"{pos.symbol}: High risk score ({pos.risk_score:.2f})")
            elif pos.action_signal == ActionSignal.HOLD_AND_MONITOR:
                watchlist.append(f"{pos.symbol}: Monitor for momentum acceleration")
        
        return watchlist[:8]  # Limit watchlist
    
    def _generate_optimization_reasoning(self, current_allocation: Dict[str, float],
                                       concentration_risk: float, stop_loss_count: int) -> str:
        """Generate overall portfolio optimization reasoning"""
        reasoning_parts = []
        
        strong_pct = current_allocation.get('strong_performer', 0)
        developing_pct = current_allocation.get('developing', 0)
        high_risk_pct = current_allocation.get('high_risk', 0)
        
        if strong_pct < 25:
            reasoning_parts.append("Portfolio underweighted in strong performers - consider reallocating winners")
        elif strong_pct > 45:
            reasoning_parts.append("Portfolio overweighted in strong performers - consider taking profits")
        
        if developing_pct > 55:
            reasoning_parts.append("Too much capital in developing positions - trim laggards")
        
        if high_risk_pct > 20:
            reasoning_parts.append("URGENT: High-risk allocation exceeds safe limits")
        
        if concentration_risk > 12:
            reasoning_parts.append(f"Concentration risk at {concentration_risk:.1f}% - consider position sizing")
        
        if stop_loss_count > 0:
            reasoning_parts.append(f"{stop_loss_count} positions approaching stop-loss levels")
        
        if not reasoning_parts:
            reasoning_parts.append("Portfolio allocation within acceptable parameters")
        
        return " | ".join(reasoning_parts)


# Convenience functions for API integration
def optimize_portfolio(holdings_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Optimize portfolio and return comprehensive recommendations"""
    optimizer = PortfolioOptimizer()
    optimization = optimizer.analyze_portfolio(holdings_data)
    return asdict(optimization)

def get_immediate_actions(holdings_data: List[Dict[str, Any]]) -> List[str]:
    """Get immediate action recommendations only"""
    optimizer = PortfolioOptimizer()
    optimization = optimizer.analyze_portfolio(holdings_data)
    return optimization.immediate_actions


if __name__ == "__main__":
    # Test with sample data
    sample_holdings = [
        {
            'symbol': 'UP',
            'last_price': 2.205,
            'market_value': 200,
            'qty': 90,
            'unrealized_pl_pct': 35.53,
            'confidence': 0.6,
            'thesis_source': 'Enhanced Analysis'
        },
        {
            'symbol': 'AMDL', 
            'last_price': 9.215,
            'market_value': 150,
            'qty': 16,
            'unrealized_pl_pct': -20.43,
            'confidence': 0.1,
            'thesis_source': 'Enhanced Analysis'
        }
    ]
    
    optimization = optimize_portfolio(sample_holdings)
    print(json.dumps(optimization, indent=2, default=str))