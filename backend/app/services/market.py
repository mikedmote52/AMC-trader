import httpx
from typing import Dict, List, Optional
import structlog
from app.config import settings

logger = structlog.get_logger()

class MarketService:
    def __init__(self):
        self.polygon_api_key = settings.polygon_api_key
        self.base_url = "https://api.polygon.io"
    
    async def get_stock_price(self, symbol: str) -> Optional[Dict]:
        """Get current stock price from Polygon"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/v2/last/trade/{symbol}",
                    params={"apikey": self.polygon_api_key}
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("results", {})
                else:
                    logger.error("Failed to get stock price", 
                               symbol=symbol, 
                               status_code=response.status_code)
                    return None
        except Exception as e:
            logger.error("Market service error", error=str(e), symbol=symbol)
            return None
    
    async def get_market_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """Get market data for multiple symbols"""
        results = {}
        for symbol in symbols:
            price_data = await self.get_stock_price(symbol)
            if price_data:
                results[symbol] = price_data
        return results
    
    async def get_volume_data(self, symbol: str, days: int = 30) -> Optional[Dict]:
        """Get volume data for a symbol over specified days"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/v2/aggs/ticker/{symbol}/range/1/day/{days}days/ago/now",
                    params={"apikey": self.polygon_api_key}
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error("Failed to get volume data",
                               symbol=symbol,
                               status_code=response.status_code)
                    return None
        except Exception as e:
            logger.error("Volume data error", error=str(e), symbol=symbol)
            return None