"""
Scoring service for ranking stock opportunities.
Combines multiple signals into a single score.
"""
from typing import Dict, List, Optional
import math

from ..config import settings
from ..utils.logging import logger


class ScoringService:
    """
    Service for computing composite scores for stock recommendations.
    All features must come from real data sources.
    """
    
    def compose_score(self, features: Dict[str, any]) -> float:
        """
        Compose a score from multiple features.
        Returns score in [0, 1] range.
        
        Features expected:
        - momentum_5d: 5-day price momentum percentage
        - volume_ratio: Current volume vs 30-day average
        - sentiment_score: Social sentiment [-1, 1]
        - sentiment_count: Number of social mentions
        - volatility: Historical volatility percentage
        - price: Current price
        """
        try:
            # Extract features with defaults
            momentum = features.get("momentum_5d", 0.0)
            volume_ratio = features.get("volume_ratio", 1.0)
            sentiment_score = features.get("sentiment_score", 0.0)
            sentiment_count = features.get("sentiment_count", 0)
            volatility = features.get("volatility", 0.0)
            price = features.get("price", 0.0)
            
            # Price filter - skip penny stocks
            if price < settings.min_price:
                return 0.0
            
            # Component scores (each 0-1)
            scores = []
            weights = []
            
            # 1. Momentum score (positive momentum is good)
            # Convert momentum from percentage to score
            # +10% momentum = 0.8 score, -10% = 0.2 score
            momentum_score = self._sigmoid(momentum / 10, steepness=1.0)
            scores.append(momentum_score)
            weights.append(0.3)  # 30% weight
            
            # 2. Volume score (high volume ratio is good)
            # 2x average volume = 0.7 score, 5x = 0.9 score
            volume_score = min(1.0, math.log(max(volume_ratio, 1.0)) / math.log(10))
            scores.append(volume_score)
            weights.append(0.2)  # 20% weight
            
            # 3. Sentiment score (convert from [-1,1] to [0,1])
            sentiment_normalized = (sentiment_score + 1) / 2
            
            # Apply confidence factor based on post count
            confidence = min(sentiment_count / settings.sentiment_min_posts, 1.0)
            
            # If insufficient sentiment data, reduce score
            if sentiment_count < settings.sentiment_min_posts:
                sentiment_normalized *= confidence
            
            scores.append(sentiment_normalized)
            weights.append(0.25)  # 25% weight
            
            # 4. Volatility score (moderate volatility is good)
            # Too low = no opportunity, too high = too risky
            # Optimal around 2-4% daily volatility
            if volatility < 1:
                vol_score = volatility  # Linear up to 1%
            elif volatility < 4:
                vol_score = 1.0  # Optimal range
            else:
                vol_score = max(0.2, 1.0 - (volatility - 4) / 10)  # Decay after 4%
            
            scores.append(vol_score)
            weights.append(0.15)  # 15% weight
            
            # 5. Liquidity score (based on price and volume)
            # Higher priced stocks with good volume get bonus
            liquidity_score = min(1.0, math.log(max(price, 1)) / math.log(1000))
            scores.append(liquidity_score)
            weights.append(0.1)  # 10% weight
            
            # Calculate weighted average
            total_weight = sum(weights)
            weighted_sum = sum(s * w for s, w in zip(scores, weights))
            final_score = weighted_sum / total_weight
            
            # Apply penalties
            # Penalty for no sentiment data
            if sentiment_count == 0:
                final_score *= 0.7
            
            # Penalty for extreme volatility
            if volatility > 10:
                final_score *= 0.5
            
            return round(min(1.0, max(0.0, final_score)), 3)
            
        except Exception as e:
            logger.error(f"Error computing score: {e}")
            return 0.0
    
    def _sigmoid(self, x: float, steepness: float = 1.0) -> float:
        """
        Sigmoid function for smooth score transitions.
        Maps (-inf, inf) to (0, 1).
        """
        return 1 / (1 + math.exp(-steepness * x))
    
    def rank_opportunities(self, candidates: List[Dict]) -> List[Dict]:
        """
        Rank a list of candidates by score.
        Returns sorted list with scores added.
        """
        scored = []
        
        for candidate in candidates:
            # Compute score
            score = self.compose_score(candidate.get("features", {}))
            
            # Add to list with score
            scored_candidate = candidate.copy()
            scored_candidate["score"] = score
            scored.append(scored_candidate)
        
        # Sort by score descending
        scored.sort(key=lambda x: x["score"], reverse=True)
        
        return scored
    
    def filter_by_threshold(self, candidates: List[Dict], min_score: float = 0.5) -> List[Dict]:
        """
        Filter candidates by minimum score threshold.
        """
        return [c for c in candidates if c.get("score", 0) >= min_score]
    
    def get_top_n(self, candidates: List[Dict], n: int = None) -> List[Dict]:
        """
        Get top N candidates by score.
        """
        if n is None:
            n = settings.discovery_top_n
        
        ranked = self.rank_opportunities(candidates)
        return ranked[:n]