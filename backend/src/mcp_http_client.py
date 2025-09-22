#!/usr/bin/env python3
"""
HTTP-based MCP Client for Polygon Data
Calls the deployed Polygon MCP server via HTTP instead of direct function calls
"""
import asyncio
import logging
import httpx
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PolygonMCPHTTPClient:
    """HTTP-based Polygon MCP client for Render deployment"""

    def __init__(self):
        # Use environment variable for MCP server URL, fallback to expected Render URL
        self.mcp_url = os.getenv('POLYGON_MCP_URL', 'https://amc-polygon-mcp.onrender.com/mcp')
        self.base_url = os.getenv('POLYGON_MCP_BASE_URL', 'https://amc-polygon-mcp.onrender.com')
        self.timeout = 30.0

    async def _call_mcp_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call MCP tool via HTTP"""
        try:
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": parameters
                }
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.mcp_url, json=mcp_request)
                response.raise_for_status()

                result = response.json()
                if "error" in result:
                    raise Exception(f"MCP Error: {result['error']}")

                return result.get("result", {})

        except Exception as e:
            logger.error(f"MCP HTTP call failed for {tool_name}: {e}")
            return {"error": str(e), "available": False}

    async def get_market_snapshots(self, tickers: List[str] = None) -> Dict[str, Any]:
        """Get market snapshots for explosive discovery"""
        try:
            params = {"market_type": "stocks"}
            if tickers:
                params["tickers"] = tickers

            result = await self._call_mcp_tool("get_snapshot_all", params)
            return result

        except Exception as e:
            logger.error(f"Failed to get market snapshots: {e}")
            return {'tickers': [], 'status': 'ERROR'}

    async def get_short_interest(self, ticker: str) -> Dict[str, Any]:
        """Get latest short interest data for squeeze detection"""
        try:
            params = {
                "ticker": ticker,
                "limit": 1,
                "order": "desc"
            }

            result = await self._call_mcp_tool("list_short_interest", params)

            if result.get('results'):
                latest = result['results'][0]
                return {
                    'short_interest': latest.get('short_interest', 0),
                    'avg_daily_volume': latest.get('avg_daily_volume', 0),
                    'days_to_cover': latest.get('days_to_cover', 0),
                    'settlement_date': latest.get('settlement_date'),
                    'available': True
                }

            return {'available': False}

        except Exception as e:
            logger.error(f"Failed to get short interest for {ticker}: {e}")
            return {'available': False}

    async def get_news_sentiment(self, ticker: str, hours_back: int = 24) -> Dict[str, Any]:
        """Get recent news with sentiment analysis"""
        try:
            params = {
                "ticker": ticker,
                "limit": 10,
                "sort": "published_utc",
                "order": "desc"
            }

            result = await self._call_mcp_tool("list_ticker_news", params)

            if not result.get('results'):
                return {'sentiment_score': 0, 'news_count': 0, 'available': False}

            # Analyze sentiment from insights
            positive_count = 0
            negative_count = 0
            total_news = 0

            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

            for article in result['results']:
                # Check if recent enough
                try:
                    pub_time = datetime.fromisoformat(article['published_utc'].replace('Z', '+00:00'))
                    if pub_time < cutoff_time:
                        continue
                except:
                    continue

                total_news += 1

                # Check insights for sentiment
                insights = article.get('insights', [])
                for insight in insights:
                    if insight.get('ticker') == ticker:
                        sentiment = insight.get('sentiment', 'neutral')
                        if sentiment == 'positive':
                            positive_count += 1
                        elif sentiment == 'negative':
                            negative_count += 1

            # Calculate sentiment score (-1 to 1)
            if total_news > 0:
                sentiment_score = (positive_count - negative_count) / max(total_news, 1)
            else:
                sentiment_score = 0

            return {
                'sentiment_score': sentiment_score,
                'news_count': total_news,
                'positive_count': positive_count,
                'negative_count': negative_count,
                'available': True
            }

        except Exception as e:
            logger.error(f"Failed to get news sentiment for {ticker}: {e}")
            return {'sentiment_score': 0, 'news_count': 0, 'available': False}

    async def get_detailed_aggregates(self, ticker: str, days_back: int = 5) -> Dict[str, Any]:
        """Get detailed price/volume data for technical analysis"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            params = {
                "ticker": ticker,
                "multiplier": 1,
                "timespan": "day",
                "from_": start_date.strftime("%Y-%m-%d"),
                "to": end_date.strftime("%Y-%m-%d"),
                "adjusted": True
            }

            result = await self._call_mcp_tool("get_aggs", params)

            if result.get('results'):
                return {
                    'data': result['results'],
                    'available': True
                }

            return {'available': False}

        except Exception as e:
            logger.error(f"Failed to get aggregates for {ticker}: {e}")
            return {'available': False}

    async def get_market_movers(self, direction: str = "gainers") -> Dict[str, Any]:
        """Get market gainers/losers for discovery filtering"""
        try:
            params = {
                "market_type": "stocks",
                "direction": direction  # "gainers" or "losers"
            }

            result = await self._call_mcp_tool("get_snapshot_direction", params)

            if result.get('results'):
                movers = result['results']

                # Filter for explosive candidates
                explosive_movers = []
                for mover in movers[:50]:  # Top 50 movers
                    ticker_data = mover.get('ticker', {})
                    day_data = ticker_data.get('day', {})

                    change_pct = day_data.get('change_percent', 0)
                    volume = day_data.get('volume', 0)

                    # Filter for significant moves with volume
                    if abs(change_pct) >= 5 and volume >= 100000:
                        explosive_movers.append({
                            'symbol': ticker_data.get('ticker', ''),
                            'price': day_data.get('close', 0),
                            'change_pct': change_pct,
                            'volume': volume,
                            'vwap': day_data.get('vwap', 0)
                        })

                return {
                    'available': True,
                    'movers': explosive_movers,
                    'total_count': len(explosive_movers),
                    'direction': direction
                }

            return {'available': False}

        except Exception as e:
            logger.error(f"Failed to get market movers: {e}")
            return {'available': False}

    async def health_check(self) -> bool:
        """Check if MCP server is responding"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/")
                return response.status_code == 200
        except:
            return False

# Global instance for easy import
mcp_http_client = PolygonMCPHTTPClient()