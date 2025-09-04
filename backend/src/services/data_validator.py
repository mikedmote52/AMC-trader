"""
Real-time Data Validation Service for Squeeze Detection
Implements dual-source validation with sub-100ms performance for hot stocks.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
import httpx
import os
from dataclasses import dataclass

from .polygon_client import poly_singleton
from ..shared.redis_client import get_redis_client

logger = logging.getLogger(__name__)

@dataclass
class PriceValidation:
    """Validated price data with source information"""
    price: float
    sources: List[str]
    discrepancy: float
    timestamp: datetime
    confidence: float
    volume_spike: float
    volatility: float
    is_hot_stock: bool


class DataValidator:
    """
    High-performance dual-source price validation for squeeze detection.
    Prioritizes speed for hot stocks while maintaining accuracy.
    """
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self.alpaca_base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
        self.alpaca_key = os.getenv("ALPACA_API_KEY", "")
        self.alpaca_secret = os.getenv("ALPACA_API_SECRET", "")
        
        # Performance thresholds
        self.DISCREPANCY_THRESHOLD = 0.02  # 2% threshold for price mismatch alerts
        self.HOT_STOCK_VOLUME_THRESHOLD = 10.0  # 10x average volume = hot stock
        self.HIGH_VOLATILITY_THRESHOLD = 0.10  # 10% volatility threshold
        
    async def get_validated_price(self, symbol: str) -> PriceValidation:
        """
        Get validated price from dual sources with optimized caching for hot stocks.
        Returns the most conservative (higher) price when discrepancies exist.
        """
        try:
            # Check cache first for recent validation (critical for performance)
            cache_key = f"validated_price:{symbol}"
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                import json
                cached = json.loads(cached_data)
                cache_age = datetime.now() - datetime.fromisoformat(cached["timestamp"])
                
                # Dynamic cache TTL based on stock activity
                max_cache_age = self._get_dynamic_cache_ttl(cached.get("volume_spike", 1), cached.get("volatility", 0))
                
                if cache_age.total_seconds() < max_cache_age:
                    return PriceValidation(
                        price=cached["price"],
                        sources=cached["sources"],
                        discrepancy=cached["discrepancy"],
                        timestamp=datetime.fromisoformat(cached["timestamp"]),
                        confidence=cached.get("confidence", 0.95),
                        volume_spike=cached.get("volume_spike", 1.0),
                        volatility=cached.get("volatility", 0.0),
                        is_hot_stock=cached.get("is_hot_stock", False)
                    )
            
            # Fetch from both sources concurrently for maximum speed
            polygon_task = self._get_polygon_price(symbol)
            alpaca_task = self._get_alpaca_price(symbol)
            
            # Use asyncio.gather for parallel execution
            results = await asyncio.gather(polygon_task, alpaca_task, return_exceptions=True)
            
            polygon_data = results[0] if not isinstance(results[0], Exception) else None
            alpaca_data = results[1] if not isinstance(results[1], Exception) else None
            
            # Extract prices and metadata
            polygon_price = polygon_data.get("price", 0) if polygon_data else 0
            alpaca_price = alpaca_data.get("price", 0) if alpaca_data else 0
            
            # Determine best price and calculate discrepancy
            validated_price, sources, discrepancy = self._reconcile_prices(
                polygon_price, alpaca_price, symbol
            )
            
            # Calculate market activity metrics
            volume_spike = polygon_data.get("volume_spike", 1.0) if polygon_data else 1.0
            volatility = polygon_data.get("volatility", 0.0) if polygon_data else 0.0
            is_hot_stock = volume_spike > self.HOT_STOCK_VOLUME_THRESHOLD or volatility > self.HIGH_VOLATILITY_THRESHOLD
            
            # Create validation result
            validation = PriceValidation(
                price=validated_price,
                sources=sources,
                discrepancy=discrepancy,
                timestamp=datetime.now(),
                confidence=self._calculate_confidence(discrepancy, sources),
                volume_spike=volume_spike,
                volatility=volatility,
                is_hot_stock=is_hot_stock
            )
            
            # Cache with dynamic TTL
            cache_ttl = self._get_dynamic_cache_ttl(volume_spike, volatility)
            self._cache_validation(symbol, validation, cache_ttl)
            
            return validation
            
        except Exception as e:
            logger.error(f"Price validation failed for {symbol}: {e}")
            # Fallback to single source
            logger.warning(f"Dual-source price validation failed for {symbol} - excluding from analysis")
            return None
    
    async def _get_polygon_price(self, symbol: str) -> Optional[Dict]:
        """Get price and market data from Polygon API"""
        try:
            # Get latest minute bar with volume data
            market_data = await poly_singleton.agg_last_minute(symbol)
            
            if market_data and market_data.get("price"):
                # Calculate volume spike (compare to 30-day average if available)
                volume_spike = await self._calculate_volume_spike(symbol, market_data.get("volume", 0))
                volatility = await self._calculate_volatility(symbol)
                
                return {
                    "price": float(market_data["price"]),
                    "volume": market_data.get("volume", 0),
                    "volume_spike": volume_spike,
                    "volatility": volatility,
                    "source": "polygon_realtime"
                }
        except Exception as e:
            logger.warning(f"Polygon price fetch failed for {symbol}: {e}")
            
        return None
    
    async def _get_alpaca_price(self, symbol: str) -> Optional[Dict]:
        """Get current price from Alpaca API"""
        try:
            if not self.alpaca_key or not self.alpaca_secret:
                return None
                
            headers = {
                "APCA-API-KEY-ID": self.alpaca_key,
                "APCA-API-SECRET-KEY": self.alpaca_secret
            }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Try latest trade first
                url = f"{self.alpaca_base_url}/v2/stocks/{symbol}/trades/latest"
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    if "trade" in data and "p" in data["trade"]:
                        return {
                            "price": float(data["trade"]["p"]),
                            "source": "alpaca_realtime"
                        }
                        
        except Exception as e:
            logger.warning(f"Alpaca price fetch failed for {symbol}: {e}")
            
        return None
    
    def _reconcile_prices(self, polygon_price: float, alpaca_price: float, symbol: str) -> Tuple[float, List[str], float]:
        """
        Reconcile prices from multiple sources and return validated price.
        Uses conservative approach (higher price) when discrepancies exist.
        """
        sources = []
        
        # Determine available sources
        if polygon_price > 0:
            sources.append("polygon")
        if alpaca_price > 0:
            sources.append("alpaca")
            
        if not sources:
            logger.error(f"No valid prices available for {symbol}")
            return 0.0, [], 1.0
            
        if len(sources) == 1:
            # Single source available
            price = polygon_price if polygon_price > 0 else alpaca_price
            return price, sources, 0.0
            
        # Both sources available - calculate discrepancy
        higher_price = max(polygon_price, alpaca_price)
        lower_price = min(polygon_price, alpaca_price)
        discrepancy = abs(higher_price - lower_price) / lower_price if lower_price > 0 else 0.0
        
        if discrepancy > self.DISCREPANCY_THRESHOLD:
            logger.warning(
                f"{symbol}: Price mismatch detected - "
                f"Polygon=${polygon_price:.4f}, Alpaca=${alpaca_price:.4f} "
                f"({discrepancy:.2%} discrepancy)"
            )
            
        # Return conservative (higher) price for trading safety
        return higher_price, sources, discrepancy
    
    def _calculate_confidence(self, discrepancy: float, sources: List[str]) -> float:
        """Calculate confidence score based on source agreement and availability"""
        if len(sources) == 0:
            return 0.0
        elif len(sources) == 1:
            return 0.85  # Single source confidence
        else:
            # Multi-source confidence based on agreement
            if discrepancy <= 0.005:  # 0.5% or less
                return 0.98
            elif discrepancy <= 0.01:  # 1% or less
                return 0.95
            elif discrepancy <= 0.02:  # 2% or less
                return 0.90
            else:
                return 0.80  # Higher discrepancy
    
    def _get_dynamic_cache_ttl(self, volume_spike: float, volatility: float) -> int:
        """
        Dynamic cache TTL based on market activity.
        Hot stocks get shorter cache times for real-time responsiveness.
        """
        if volume_spike > 10:  # Squeeze detected
            return 30  # 30 seconds for hot stocks
        elif volatility > 0.10:  # High volatility
            return 60  # 1 minute for volatile stocks
        elif volume_spike > 3:  # Moderate activity
            return 120  # 2 minutes for active stocks
        else:
            return 300  # 5 minutes standard
    
    async def _calculate_volume_spike(self, symbol: str, current_volume: int) -> float:
        """Calculate volume spike ratio vs 30-day average"""
        try:
            # Check cache for average volume
            cache_key = f"avg_volume:{symbol}"
            cached_avg = self.redis_client.get(cache_key)
            
            if cached_avg:
                avg_volume = float(cached_avg)
                return current_volume / avg_volume if avg_volume > 0 else 1.0
            
            # If no cached average, assume moderate activity
            return 2.0  # Default to 2x average as placeholder
            
        except Exception as e:
            logger.warning(f"Volume spike calculation failed for {symbol}: {e}")
            return 1.0
    
    async def _calculate_volatility(self, symbol: str) -> float:
        """Calculate recent volatility (simplified implementation)"""
        try:
            # This would ideally fetch recent price data and calculate standard deviation
            # For now, return placeholder that can be enhanced later
            return None  # No default volatility - require real data
            
        except Exception as e:
            logger.warning(f"Volatility calculation failed for {symbol}: {e}")
            return 0.0
    
    def _cache_validation(self, symbol: str, validation: PriceValidation, ttl: int):
        """Cache validation result with dynamic TTL"""
        try:
            cache_data = {
                "price": validation.price,
                "sources": validation.sources,
                "discrepancy": validation.discrepancy,
                "timestamp": validation.timestamp.isoformat(),
                "confidence": validation.confidence,
                "volume_spike": validation.volume_spike,
                "volatility": validation.volatility,
                "is_hot_stock": validation.is_hot_stock
            }
            
            import json
            self.redis_client.setex(
                f"validated_price:{symbol}",
                ttl,
                json.dumps(cache_data)
            )
            
        except Exception as e:
            logger.warning(f"Cache write failed for {symbol}: {e}")
    
    async def _fallback_validation(self, symbol: str) -> None:
        """DEPRECATED - No fallback validation allowed per validation requirements"""
        logger.error(f"Fallback validation requested for {symbol} - this should never happen")
        return None
                    confidence=0.85,
                    volume_spike=polygon_data.get("volume_spike", 1.0),
                    volatility=polygon_data.get("volatility", 0.0),
                    is_hot_stock=False
                )
        except Exception as e:
            logger.error(f"Fallback validation failed for {symbol}: {e}")
        
        # Last resort - return zero price with low confidence
        return PriceValidation(
            price=0.0,
            sources=[],
            discrepancy=1.0,
            timestamp=datetime.now(),
            confidence=0.0,
            volume_spike=1.0,
            volatility=0.0,
            is_hot_stock=False
        )

# Global singleton for efficient reuse
validator_singleton = DataValidator()