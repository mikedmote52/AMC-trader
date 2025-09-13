"""
Market data service using Polygon API.
Real data only - no mocks or stubs.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import httpx

from ..config import settings
from ..utils.logging import logger, log_duration
from ..utils.errors import HTTPError, TimeoutError, RateLimitError, BadResponseError
from ..deps import HTTPClientWithRetry


class MarketService:
    """Service for fetching real market data from Polygon."""
    
    def __init__(self, http_client: HTTPClientWithRetry):
        self.http_client = http_client
        self.base_url = "https://api.polygon.io"
        self.api_key = settings.polygon_api_key
    
    async def get_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get latest quotes for multiple symbols.
        Returns partial data if some symbols fail.
        """
        results = {}
        errors = []
        
        for symbol in symbols:
            try:
                with log_duration(logger, f"Fetching quote for {symbol}", symbol=symbol):
                    # Get last trade for each symbol
                    url = f"{self.base_url}/v2/last/trade/{symbol}"
                    response = await self.http_client.get(
                        url,
                        params={"apiKey": self.api_key}
                    )
                    data = response.json()
                    
                    if data.get("status") == "OK" and "results" in data:
                        trade = data["results"]
                        results[symbol] = {
                            "price": trade.get("p"),
                            "size": trade.get("s"),
                            "timestamp": trade.get("t"),
                            "exchange": trade.get("x")
                        }
                    else:
                        errors.append({"symbol": symbol, "error": data.get("message", "No data")})
                        
            except httpx.TimeoutException:
                logger.warning(f"Timeout fetching quote for {symbol}")
                errors.append({"symbol": symbol, "error": "timeout"})
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    raise RateLimitError("Polygon rate limit exceeded")
                logger.error(f"HTTP error fetching quote for {symbol}: {e}")
                errors.append({"symbol": symbol, "error": f"HTTP {e.response.status_code}"})
            except Exception as e:
                logger.error(f"Error fetching quote for {symbol}: {e}")
                errors.append({"symbol": symbol, "error": str(e)})
        
        if errors:
            logger.warning(f"Failed to fetch quotes for {len(errors)} symbols")
        
        return {"quotes": results, "errors": errors}
    
    async def get_aggregates(self, symbol: str, days: int = 5) -> Dict[str, Any]:
        """
        Get aggregate bars for a symbol over the last N days.
        Used for momentum and volatility calculations.
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days + 10)  # Extra days for market holidays
            
            url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/1/day/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
            
            response = await self.http_client.get(
                url,
                params={
                    "apiKey": self.api_key,
                    "adjusted": "true",
                    "sort": "desc",
                    "limit": days
                }
            )
            data = response.json()
            
            if data.get("status") == "OK" and "results" in data:
                bars = data["results"]
                return {
                    "symbol": symbol,
                    "bars": [
                        {
                            "date": datetime.fromtimestamp(bar["t"] / 1000).isoformat(),
                            "open": bar["o"],
                            "high": bar["h"],
                            "low": bar["l"],
                            "close": bar["c"],
                            "volume": bar["v"],
                            "vwap": bar.get("vw")
                        }
                        for bar in bars
                    ]
                }
            else:
                raise BadResponseError(f"Invalid response for {symbol}: {data.get('message', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Failed to get aggregates for {symbol}: {e}")
            raise
    
    async def get_snapshot(self, symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive snapshot for a symbol.
        Includes price, volume, and daily stats.
        """
        try:
            url = f"{self.base_url}/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}"
            
            response = await self.http_client.get(
                url,
                params={"apiKey": self.api_key}
            )
            data = response.json()
            
            if data.get("status") == "OK" and "ticker" in data:
                ticker = data["ticker"]
                return {
                    "symbol": symbol,
                    "price": ticker.get("day", {}).get("c"),
                    "prev_close": ticker.get("prevDay", {}).get("c"),
                    "volume": ticker.get("day", {}).get("v"),
                    "change": ticker.get("todaysChange"),
                    "change_percent": ticker.get("todaysChangePerc"),
                    "day_high": ticker.get("day", {}).get("h"),
                    "day_low": ticker.get("day", {}).get("l"),
                    "vwap": ticker.get("day", {}).get("vw"),
                    "updated": ticker.get("updated")
                }
            else:
                raise BadResponseError(f"Invalid snapshot for {symbol}: {data.get('message', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Failed to get snapshot for {symbol}: {e}")
            raise
    
    async def calculate_momentum(self, symbol: str, days: int = 5) -> float:
        """
        Calculate price momentum over N days.
        Returns percentage change from oldest to newest close.
        """
        try:
            aggregates = await self.get_aggregates(symbol, days)
            bars = aggregates["bars"]
            
            if len(bars) < 2:
                logger.warning(f"Insufficient data for momentum calculation: {symbol}")
                return 0.0
            
            # Bars are sorted desc, so first is newest
            newest_close = bars[0]["close"]
            oldest_close = bars[-1]["close"]
            
            if oldest_close == 0:
                return 0.0
                
            momentum = ((newest_close - oldest_close) / oldest_close) * 100
            return round(momentum, 2)
            
        except Exception as e:
            logger.error(f"Failed to calculate momentum for {symbol}: {e}")
            return 0.0
    
    async def calculate_volatility(self, symbol: str, days: int = 20) -> float:
        """
        Calculate historical volatility (standard deviation of returns).
        """
        try:
            aggregates = await self.get_aggregates(symbol, days)
            bars = aggregates["bars"]
            
            if len(bars) < 2:
                logger.warning(f"Insufficient data for volatility calculation: {symbol}")
                return 0.0
            
            # Calculate daily returns
            returns = []
            for i in range(len(bars) - 1):
                if bars[i+1]["close"] > 0:
                    daily_return = (bars[i]["close"] - bars[i+1]["close"]) / bars[i+1]["close"]
                    returns.append(daily_return)
            
            if not returns:
                return 0.0
            
            # Calculate standard deviation
            mean = sum(returns) / len(returns)
            variance = sum((r - mean) ** 2 for r in returns) / len(returns)
            volatility = (variance ** 0.5) * 100  # Convert to percentage
            
            return round(volatility, 2)
            
        except Exception as e:
            logger.error(f"Failed to calculate volatility for {symbol}: {e}")
            return 0.0