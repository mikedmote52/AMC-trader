from typing import Dict, List, Optional
import structlog
from app.services.market import MarketService
from app.services.sentiment import SentimentService
from app.deps import get_db, get_redis
from app.models import Recommendation
import json
import math

logger = structlog.get_logger()

class ScoringService:
    def __init__(self):
        self.market_service = MarketService()
        self.sentiment_service = SentimentService()
        self.redis = get_redis()
    
    def _calculate_vigl_score(self, market_data: Dict) -> float:
        """Calculate VIGL pattern score based on volume and price action"""
        try:
            volume = market_data.get("volume", 0)
            avg_volume = market_data.get("avg_volume", volume)
            price = market_data.get("price", 0)
            
            if avg_volume == 0 or price == 0:
                return 0.0
            
            # Volume spike calculation (target: 20.9x average for VIGL pattern)
            volume_ratio = volume / avg_volume if avg_volume > 0 else 0
            volume_score = min(volume_ratio / 20.9, 1.0)  # Normalize to 1.0
            
            # Price range analysis (VIGL pattern: $2.94-$4.66)
            price_score = 1.0 if 2.94 <= price <= 4.66 else 0.5
            
            # Combined VIGL score
            vigl_score = (volume_score * 0.7 + price_score * 0.3)
            
            return min(vigl_score, 1.0)
            
        except Exception as e:
            logger.error("VIGL score calculation error", error=str(e))
            return 0.0
    
    def _calculate_momentum_score(self, market_data: Dict) -> float:
        """Calculate momentum score based on price movement"""
        try:
            # Placeholder momentum calculation
            # In production, this would analyze price trends, moving averages, etc.
            current_price = market_data.get("price", 0)
            prev_close = market_data.get("prev_close", current_price)
            
            if prev_close == 0:
                return 0.5
            
            price_change = (current_price - prev_close) / prev_close
            # Convert price change to 0-1 score
            momentum_score = max(0, min(1, 0.5 + price_change * 2))
            
            return momentum_score
            
        except Exception as e:
            logger.error("Momentum score calculation error", error=str(e))
            return 0.5
    
    def _calculate_technical_score(self, market_data: Dict) -> float:
        """Calculate technical analysis score"""
        try:
            # Placeholder for technical indicators
            # In production: RSI, MACD, Bollinger Bands, etc.
            volume = market_data.get("volume", 0)
            avg_volume = market_data.get("avg_volume", 1)
            
            # Simple volume-based technical score
            volume_strength = min(volume / avg_volume / 5, 1.0) if avg_volume > 0 else 0.5
            
            return volume_strength
            
        except Exception as e:
            logger.error("Technical score calculation error", error=str(e))
            return 0.5
    
    async def score_stock(self, symbol: str) -> Optional[Dict]:
        """Calculate comprehensive score for a stock"""
        try:
            # Get market data
            market_data = await self.market_service.get_stock_price(symbol)
            if not market_data:
                logger.warning("No market data for symbol", symbol=symbol)
                return None
            
            # Get volume data for VIGL scoring
            volume_data = await self.market_service.get_volume_data(symbol)
            if volume_data and volume_data.get("results"):
                recent_volumes = [bar.get("v", 0) for bar in volume_data["results"][-30:]]
                avg_volume = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 0
                market_data["avg_volume"] = avg_volume
            
            # Calculate individual scores
            vigl_score = self._calculate_vigl_score(market_data)
            momentum_score = self._calculate_momentum_score(market_data)
            technical_score = self._calculate_technical_score(market_data)
            sentiment_score = await self.sentiment_service.get_sentiment_score(symbol) or 0.5
            
            # Volume score (separate from VIGL)
            volume_score = min(market_data.get("volume", 0) / market_data.get("avg_volume", 1) / 10, 1.0) if market_data.get("avg_volume", 1) > 0 else 0.5
            
            # Calculate overall confidence score
            weights = {
                "vigl": 0.3,      # VIGL pattern is critical
                "momentum": 0.25,  # Price momentum
                "technical": 0.2,  # Technical indicators
                "sentiment": 0.15, # Market sentiment
                "volume": 0.1      # Volume strength
            }
            
            confidence_score = (
                vigl_score * weights["vigl"] +
                momentum_score * weights["momentum"] +
                technical_score * weights["technical"] +
                sentiment_score * weights["sentiment"] +
                volume_score * weights["volume"]
            )
            
            return {
                "symbol": symbol,
                "confidence_score": confidence_score,
                "vigl_score": vigl_score,
                "momentum_score": momentum_score,
                "technical_score": technical_score,
                "sentiment_score": sentiment_score,
                "volume_score": volume_score,
                "current_price": market_data.get("price", 0),
                "features": market_data
            }
            
        except Exception as e:
            logger.error("Stock scoring error", error=str(e), symbol=symbol)
            return None
    
    async def get_top_recommendations(self, limit: int = 20) -> List[Dict]:
        """Get top stock recommendations based on scores"""
        try:
            # In production, this would scan a universe of stocks
            # For now, use a sample set of symbols
            sample_symbols = [
                "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", 
                "NVDA", "META", "NFLX", "ADBE", "CRM",
                "AMD", "INTC", "ORCL", "CSCO", "IBM",
                "UBER", "LYFT", "SNAP", "TWTR", "SQ"
            ]
            
            recommendations = []
            for symbol in sample_symbols[:limit]:
                score_data = await self.score_stock(symbol)
                if score_data:
                    # Determine recommendation type based on confidence score
                    confidence = score_data["confidence_score"]
                    if confidence >= 0.7:
                        rec_type = "BUY"
                    elif confidence <= 0.3:
                        rec_type = "SELL"
                    else:
                        rec_type = "HOLD"
                    
                    score_data["recommendation_type"] = rec_type
                    recommendations.append(score_data)
            
            # Sort by confidence score descending
            recommendations.sort(key=lambda x: x["confidence_score"], reverse=True)
            
            logger.info("Generated recommendations", count=len(recommendations))
            return recommendations[:limit]
            
        except Exception as e:
            logger.error("Top recommendations error", error=str(e))
            return []