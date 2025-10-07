from typing import Dict, List, Optional
import structlog
import json
import math

logger = structlog.get_logger()

class ScoringService:
    def __init__(self):
        # V2 methods (filter_top_momentum, calculate_explosion_probability) don't need these
        # Only initialize if available (for backwards compatibility with V1 methods)
        try:
            from backend.src.services.market import MarketService
            self.market_service = MarketService()
        except ImportError:
            self.market_service = None

        try:
            from app.services.sentiment import SentimentService
            self.sentiment_service = SentimentService()
        except ImportError:
            self.sentiment_service = None

        try:
            from app.deps import get_redis
            self.redis = get_redis()
        except ImportError:
            self.redis = None
    
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

    def calculate_momentum_score_batch(self, snapshots: Dict[str, Dict]) -> List[tuple]:
        """
        Squeeze-Prophet momentum formula for Stage 3 pre-ranking.

        Formula: (abs(%change) × 2.0) + (log(volume) × 1.0)

        This identifies explosive stocks BEFORE expensive RVOL calculation.
        Reduces 8,059 → 1,000 stocks (87.2% reduction).

        CRITICAL: Uses ONLY real data from snapshots.
        NO fake data, NO defaults.

        Args:
            snapshots: Real market data from bulk snapshot

        Returns:
            List of (symbol, momentum_score) tuples, sorted descending
        """
        if not snapshots:
            return []

        momentum_scores = []
        skipped = 0

        for symbol, snapshot in snapshots.items():
            try:
                # Extract real data (skip if missing)
                pct_change = snapshot.get("change_pct")
                volume = snapshot.get("volume")

                if pct_change is None or volume is None:
                    skipped += 1
                    continue

                # Validate data (reject fake/corrupted data)
                if volume <= 0:
                    skipped += 1
                    continue

                # Squeeze-Prophet momentum formula
                # Prioritizes explosive price moves + high volume
                score = (abs(pct_change) * 2.0) + (math.log1p(volume) * 1.0)

                momentum_scores.append((symbol, score))

            except Exception as e:
                logger.debug(f"Skipped {symbol} momentum calc: {e}")
                skipped += 1
                continue

        # Sort by momentum score descending
        momentum_scores.sort(key=lambda x: x[1], reverse=True)

        logger.info(
            "Momentum scores calculated",
            total=len(momentum_scores),
            skipped=skipped
        )

        return momentum_scores

    def filter_top_momentum(
        self,
        snapshots: Dict[str, Dict],
        limit: int = 1000
    ) -> List[str]:
        """
        Pre-rank by momentum and return top N symbols (Stage 3 optimization).

        This is the KEY optimization from Squeeze-Prophet:
        - Reduces 8,059 stocks → 1,000 BEFORE expensive RVOL calculations
        - 87.2% reduction in processing
        - Finds explosive stocks early in pipeline

        CRITICAL: Returns ONLY symbols from real data.
        NO fake data, NO padding to reach limit.

        Args:
            snapshots: Real market data from bulk snapshot
            limit: Maximum number of top momentum stocks to return

        Returns:
            List of top N symbols by momentum score
        """
        # Calculate momentum scores
        momentum_scores = self.calculate_momentum_score_batch(snapshots)

        if not momentum_scores:
            logger.warning("No momentum scores calculated - check snapshot data")
            return []

        # Take top N (or fewer if not enough data)
        top_count = min(limit, len(momentum_scores))
        top_symbols = [symbol for symbol, _ in momentum_scores[:top_count]]

        # Log top performers
        if momentum_scores:
            top_5 = momentum_scores[:5]
            logger.info("Top 5 momentum leaders:")
            for i, (symbol, score) in enumerate(top_5, 1):
                snapshot = snapshots.get(symbol, {})
                logger.info(
                    f"  {i}. {symbol}",
                    momentum_score=f"{score:.2f}",
                    change_pct=f"{snapshot.get('change_pct', 0):+.2f}%",
                    volume=f"{snapshot.get('volume', 0):,}"
                )

        reduction_pct = (len(snapshots) - len(top_symbols)) / len(snapshots) * 100 if snapshots else 0
        logger.info(
            "Momentum pre-rank complete",
            input_stocks=len(snapshots),
            output_stocks=len(top_symbols),
            reduction=f"{reduction_pct:.1f}%"
        )

        return top_symbols

    def calculate_explosion_probability(
        self,
        momentum_score: float,
        rvol: float,
        catalyst_score: float,
        price: float,
        change_pct: float,
        short_interest: Optional[float] = None,
        float_size: Optional[float] = None,
        borrow_rate: Optional[float] = None
    ) -> float:
        """
        Squeeze-Prophet explosion probability formula (Stage 7).

        Predicts likelihood of explosive upside move (0-100 scale).

        8-factor formula:
        - Momentum (25%): Price acceleration
        - RVOL (25%): Relative volume participation
        - Catalyst (20%): News/trigger strength
        - Price (10%): Lower price = higher % upside potential
        - Change (10%): Current price momentum
        - Short Interest (5%): Squeeze fuel
        - Borrow Rate (5%): Short stress
        - Float Size (5%): Smaller = more volatile

        CRITICAL: Uses ONLY real data provided.
        Missing optional data = 0.0 contribution (NO fake defaults).

        Returns:
            Explosion probability (0-100), capped at 95%
        """
        # Normalize helper (0-1 range)
        def norm(value: float, min_val: float, max_val: float) -> float:
            if value is None:
                return 0.0
            return max(0.0, min(1.0, (value - min_val) / (max_val - min_val + 1e-9)))

        # Required components (from real data)
        momentum_component = norm(momentum_score, 0, 200) * 0.25
        # VIGL pattern: 35x+ RVOL is explosive, so expand range to 1-50x
        rvol_component = norm(rvol, 1, 50) * 0.25
        catalyst_component = norm(catalyst_score, 0, 100) * 0.20

        # Price component (inverse: lower price = higher score)
        price_component = (1 - norm(price, 0, 50)) * 0.10

        # Change component (absolute value)
        change_component = norm(abs(change_pct), 0, 100) * 0.10

        # Optional squeeze components (only if real data provided)
        si_component = norm(short_interest or 0, 0, 40) * 0.05
        borrow_component = norm(borrow_rate or 0, 0, 100) * 0.05

        # Float size component (inverse: smaller = higher)
        if float_size and float_size > 0:
            float_component = (1 - norm(float_size, 0, 50_000_000)) * 0.05
        else:
            float_component = 0.0

        # Calculate total probability
        probability = (
            momentum_component +
            rvol_component +
            catalyst_component +
            price_component +
            change_component +
            si_component +
            borrow_component +
            float_component
        ) * 100

        # Cap at 95% (never 100% certain)
        return round(min(probability, 95.0), 1)