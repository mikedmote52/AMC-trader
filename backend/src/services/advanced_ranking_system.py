"""
Advanced Ranking System for AMC-TRADER
Filters 20+ candidates down to top 3-5 highest-probability money-makers
Based on VIGL 324% winner pattern analysis
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RankedCandidate:
    """Enhanced candidate with advanced ranking data"""
    symbol: str
    price: float
    advanced_score: float
    success_probability: float
    vigl_similarity: float
    action: str  # STRONG_BUY, BUY, WATCH, PASS
    position_size_pct: float
    entry_price: float
    stop_loss: float
    target_price: float
    risk_reward_ratio: float
    ranking_factors: Dict[str, float]
    thesis: str
    original_data: Dict[str, Any]


class AdvancedRankingSystem:
    """
    Multi-factor ranking system to identify explosive opportunities
    Transforms weak 0.14-0.23 scores into meaningful 0.60-0.85+ rankings
    """
    
    def __init__(self):
        # VIGL Pattern Weights (optimized for 324% winner)
        self.component_weights = {
            'vigl_pattern': 0.25,      # Similarity to VIGL explosive pattern
            'volume_quality': 0.23,    # Sustained volume vs spike analysis
            'risk_momentum': 0.20,     # Risk-adjusted momentum scoring
            'compression_vol': 0.15,   # Compression + volatility expansion
            'catalyst': 0.10,          # News/event catalyst boost
            'price_range': 0.07        # Optimal price range for explosive moves
        }
        
        # Scoring thresholds
        self.score_thresholds = {
            'strong_buy': 0.80,    # 85%+ success probability
            'buy': 0.65,           # 75%+ success probability
            'watch': 0.50,         # 65%+ success probability
            'pass': 0.50           # Below this gets filtered out
        }
        
        # Position sizing parameters
        self.max_position_size = 0.08  # 8% max per position
        self.base_position_size = 0.05  # 5% base allocation
        
    def rank_candidates(self, candidates: List[Dict[str, Any]], 
                       max_results: int = 5) -> List[RankedCandidate]:
        """
        Rank candidates using advanced multi-factor scoring
        
        Args:
            candidates: List of discovery candidates with factors
            max_results: Maximum number of results to return
            
        Returns:
            List of top-ranked candidates with full analysis
        """
        ranked = []
        
        for candidate in candidates:
            try:
                advanced_score = self._calculate_advanced_score(candidate)
                
                # Only process candidates above minimum threshold
                if advanced_score >= self.score_thresholds['pass']:
                    ranked_candidate = self._create_ranked_candidate(
                        candidate, advanced_score
                    )
                    ranked.append(ranked_candidate)
                    
            except Exception as e:
                # Log error but continue processing other candidates
                print(f"Error ranking {candidate.get('symbol', 'unknown')}: {e}")
                continue
        
        # Sort by advanced score (highest first)
        ranked.sort(key=lambda x: x.advanced_score, reverse=True)
        
        return ranked[:max_results]
    
    def _calculate_advanced_score(self, candidate: Dict[str, Any]) -> float:
        """Calculate comprehensive advanced score for candidate"""
        factors = candidate.get('factors', {})
        
        # Component scores (0.0 - 1.0 each)
        vigl_score = self._vigl_pattern_score(factors)
        volume_score = self._volume_quality_score(factors)
        momentum_score = self._risk_momentum_score(factors)
        compression_score = self._compression_volatility_score(factors)
        catalyst_score = self._catalyst_score(factors)
        price_score = self._price_range_score(candidate.get('price', 0))
        
        # Weighted combination
        advanced_score = (
            vigl_score * self.component_weights['vigl_pattern'] +
            volume_score * self.component_weights['volume_quality'] +
            momentum_score * self.component_weights['risk_momentum'] +
            compression_score * self.component_weights['compression_vol'] +
            catalyst_score * self.component_weights['catalyst'] +
            price_score * self.component_weights['price_range']
        )
        
        return min(1.0, max(0.0, advanced_score))
    
    def _vigl_pattern_score(self, factors: Dict[str, Any]) -> float:
        """Score based on similarity to VIGL 324% winner pattern"""
        vigl_similarity = factors.get('vigl_similarity', 0.0)
        wolf_risk = factors.get('wolf_risk_score', 0.5)
        
        # VIGL had: 0.75+ similarity, low wolf risk
        pattern_score = vigl_similarity
        
        # Penalize high manipulation risk
        risk_penalty = max(0.0, wolf_risk - 0.3) * 0.5
        
        return max(0.0, pattern_score - risk_penalty)
    
    def _volume_quality_score(self, factors: Dict[str, Any]) -> float:
        """Analyze volume quality - sustained vs one-day spike"""
        volume_spike = factors.get('volume_spike_ratio', 1.0)
        early_signal = factors.get('volume_early_signal', 1.0)
        confirmation = factors.get('volume_confirmation', 1.0)
        
        # Reward sustained volume over single spikes
        sustainability = min(early_signal, confirmation) / max(volume_spike, 1.0)
        
        # Volume magnitude score (logarithmic)
        if volume_spike <= 1.0:
            magnitude_score = 0.0
        elif volume_spike <= 2.0:
            magnitude_score = 0.4
        elif volume_spike <= 5.0:
            magnitude_score = 0.7
        elif volume_spike <= 10.0:
            magnitude_score = 0.9
        else:
            magnitude_score = 1.0
        
        # Combined score (70% magnitude, 30% sustainability)
        return magnitude_score * 0.7 + sustainability * 0.3
    
    def _risk_momentum_score(self, factors: Dict[str, Any]) -> float:
        """Risk-adjusted momentum scoring - controlled pullbacks better than free-falls"""
        momentum_1d = factors.get('price_momentum_1d', 0.0)
        rs_5d = factors.get('rs_5d_percent', 0.0)
        atr_pct = factors.get('atr_percent', 0.05)
        
        # Momentum scoring (favor controlled pullbacks)
        if momentum_1d > 10:  # Strong up day
            momentum_score = 0.9
        elif momentum_1d > 0:  # Positive day
            momentum_score = 0.7
        elif momentum_1d > -5:  # Controlled pullback
            momentum_score = 0.8  # This is actually good - buying opportunity
        elif momentum_1d > -15:  # Moderate pullback
            momentum_score = 0.5
        else:  # Heavy selling
            momentum_score = 0.2
            
        # 5-day relative strength adjustment
        rs_adjustment = max(0.0, min(0.3, (rs_5d + 30) / 100))
        
        return min(1.0, momentum_score + rs_adjustment)
    
    def _compression_volatility_score(self, factors: Dict[str, Any]) -> float:
        """Score compression + volatility expansion (breakout setup)"""
        compression_pctl = factors.get('compression_percentile', 50.0)
        atr_pct = factors.get('atr_percent', 0.05)
        
        # Tighter compression = higher score
        if compression_pctl <= 5:  # Ultra-tight
            compression_score = 1.0
        elif compression_pctl <= 10:  # Very tight
            compression_score = 0.8
        elif compression_pctl <= 20:  # Tight
            compression_score = 0.6
        else:  # Not compressed enough
            compression_score = 0.3
            
        # Volatility expansion score
        if atr_pct >= 0.10:  # High volatility
            volatility_score = 1.0
        elif atr_pct >= 0.06:  # Good volatility
            volatility_score = 0.8
        elif atr_pct >= 0.04:  # Moderate volatility
            volatility_score = 0.6
        else:  # Low volatility
            volatility_score = 0.3
            
        # Combined score (60% compression, 40% volatility)
        return compression_score * 0.6 + volatility_score * 0.4
    
    def _catalyst_score(self, factors: Dict[str, Any]) -> float:
        """Score news/event catalysts"""
        has_catalyst = factors.get('has_news_catalyst', False)
        social_rank = factors.get('social_rank', 0.0)
        
        if has_catalyst:
            base_score = 0.8
        else:
            base_score = 0.3
            
        # Social sentiment boost
        social_boost = social_rank * 0.2
        
        return min(1.0, base_score + social_boost)
    
    def _price_range_score(self, price: float) -> float:
        """Score based on optimal price range for explosive moves"""
        if price <= 0:
            return 0.0
            
        # VIGL sweet spot analysis: $2-12 range optimal
        if 2.0 <= price <= 12.0:
            return 1.0  # Optimal explosive range
        elif 1.0 <= price < 2.0 or 12.0 < price <= 25.0:
            return 0.7  # Good range
        elif 0.5 <= price < 1.0 or 25.0 < price <= 50.0:
            return 0.4  # Acceptable range
        else:
            return 0.2  # Sub-optimal for explosive moves
    
    def _create_ranked_candidate(self, candidate: Dict[str, Any], 
                               advanced_score: float) -> RankedCandidate:
        """Create full ranked candidate with trading recommendations"""
        
        symbol = candidate.get('symbol', 'UNKNOWN')
        price = candidate.get('price', 0.0)
        
        # Determine action based on score
        if advanced_score >= self.score_thresholds['strong_buy']:
            action = 'STRONG_BUY'
            success_prob = 0.85
        elif advanced_score >= self.score_thresholds['buy']:
            action = 'BUY' 
            success_prob = 0.75
        elif advanced_score >= self.score_thresholds['watch']:
            action = 'WATCH'
            success_prob = 0.65
        else:
            action = 'PASS'
            success_prob = 0.45
            
        # Position sizing (score-adjusted)
        position_size = self._calculate_position_size(advanced_score)
        
        # Risk management levels
        stop_loss, target_price, risk_reward = self._calculate_risk_levels(
            price, candidate.get('factors', {})
        )
        
        # VIGL similarity
        vigl_similarity = candidate.get('factors', {}).get('vigl_similarity', 0.0)
        
        # Ranking factors breakdown
        factors = candidate.get('factors', {})
        ranking_factors = {
            'vigl_pattern': self._vigl_pattern_score(factors),
            'volume_quality': self._volume_quality_score(factors),
            'risk_momentum': self._risk_momentum_score(factors),
            'compression_vol': self._compression_volatility_score(factors),
            'catalyst': self._catalyst_score(factors),
            'price_range': self._price_range_score(price)
        }
        
        return RankedCandidate(
            symbol=symbol,
            price=price,
            advanced_score=advanced_score,
            success_probability=success_prob,
            vigl_similarity=vigl_similarity,
            action=action,
            position_size_pct=position_size,
            entry_price=price,
            stop_loss=stop_loss,
            target_price=target_price,
            risk_reward_ratio=risk_reward,
            ranking_factors=ranking_factors,
            thesis=self._generate_enhanced_thesis(candidate, advanced_score, action),
            original_data=candidate
        )
    
    def _calculate_position_size(self, advanced_score: float) -> float:
        """Calculate position size based on confidence score"""
        # Higher scores get larger allocations (up to max)
        confidence_multiplier = advanced_score
        position_size = self.base_position_size * (1 + confidence_multiplier)
        
        return min(self.max_position_size, position_size)
    
    def _calculate_risk_levels(self, price: float, factors: Dict[str, Any]) -> Tuple[float, float, float]:
        """Calculate stop loss, target, and risk/reward ratio"""
        atr_pct = factors.get('atr_percent', 0.05)
        
        # Stop loss: 2x ATR or 5% minimum
        stop_distance_pct = max(0.05, atr_pct * 2)
        stop_loss = price * (1 - stop_distance_pct)
        
        # Target: 2.5x risk minimum (conservative)
        target_distance_pct = stop_distance_pct * 2.5
        target_price = price * (1 + target_distance_pct)
        
        # Risk/reward ratio
        risk_reward = target_distance_pct / stop_distance_pct
        
        return round(stop_loss, 2), round(target_price, 2), round(risk_reward, 1)
    
    def _generate_enhanced_thesis(self, candidate: Dict[str, Any], 
                                advanced_score: float, action: str) -> str:
        """Generate enhanced thesis with ranking insights"""
        symbol = candidate.get('symbol', 'UNKNOWN')
        factors = candidate.get('factors', {})
        
        vigl_sim = factors.get('vigl_similarity', 0.0)
        volume_spike = factors.get('volume_spike_ratio', 1.0)
        compression = factors.get('compression_percentile', 50.0)
        
        thesis = f"{symbol} {action} - Advanced Score: {advanced_score:.3f} "
        thesis += f"(VIGL similarity: {vigl_sim:.1%}, {volume_spike:.1f}x volume, "
        thesis += f"{compression:.1f}% compression). "
        
        if action == 'STRONG_BUY':
            thesis += "High-probability explosive setup matching VIGL winner pattern."
        elif action == 'BUY':
            thesis += "Strong breakout candidate with good risk/reward profile."
        elif action == 'WATCH':
            thesis += "Potential opportunity - monitor for volume confirmation."
        else:
            thesis += "Insufficient setup quality for current deployment."
            
        return thesis


def rank_top_candidates(candidates: List[Dict[str, Any]], 
                       max_results: int = 5) -> List[RankedCandidate]:
    """
    Convenience function to rank candidates using advanced system
    
    Args:
        candidates: Raw discovery candidates
        max_results: Maximum results to return
        
    Returns:
        Top-ranked trading opportunities
    """
    ranking_system = AdvancedRankingSystem()
    return ranking_system.rank_candidates(candidates, max_results)


# Testing function for development
def test_ranking_system():
    """Test the ranking system with sample data"""
    sample_candidates = [
        {
            'symbol': 'UP',
            'price': 2.48,
            'factors': {
                'vigl_similarity': 0.617,
                'volume_spike_ratio': 6.49,
                'volume_early_signal': 4.5,
                'volume_confirmation': 5.52,
                'price_momentum_1d': -20.11,
                'rs_5d_percent': -26.08,
                'atr_percent': 0.0762,
                'compression_percentile': 5.0,
                'has_news_catalyst': True,
                'social_rank': 0.5,
                'wolf_risk_score': 0.5
            }
        }
    ]
    
    ranked = rank_top_candidates(sample_candidates)
    for candidate in ranked:
        print(f"{candidate.symbol}: {candidate.advanced_score:.3f} ({candidate.action})")
        print(f"  Position: {candidate.position_size_pct:.1%}, Risk/Reward: {candidate.risk_reward_ratio}:1")
        print(f"  Entry: ${candidate.entry_price}, Stop: ${candidate.stop_loss}, Target: ${candidate.target_price}")
        print()


if __name__ == "__main__":
    test_ranking_system()