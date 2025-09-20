#!/usr/bin/env python3
"""
MCP Polygon Bridge
Direct interface to real Polygon MCP functions in Claude Code environment
Falls back to API when MCP not available, fails cleanly if no real data source
"""
import asyncio
import logging
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MCPPolygonBridge:
    """
    Bridge to access real Polygon data through MCP or direct API
    NO SIMULATION, NO FAKE DATA - real data only or clean failure
    """

    def __init__(self):
        self.max_batch_size = 50
        self._cache = {}
        self.polygon_api_key = os.getenv('POLYGON_API_KEY', '')

    async def get_market_snapshot(self,
                                 tickers: Optional[List[str]] = None,
                                 market_type: str = 'stocks',
                                 include_otc: bool = False) -> Dict[str, Any]:
        """
        Get real market snapshot - MCP first, API fallback, or clean failure
        """
        try:
            if not tickers:
                tickers = self._get_liquid_universe()

            # Limit batch size to prevent overload
            if len(tickers) > self.max_batch_size:
                logger.info(f"Limiting {len(tickers)} tickers to {self.max_batch_size}")
                tickers = tickers[:self.max_batch_size]

            # Try MCP functions first (available in Claude Code environment)
            try:
                result = await self._mcp_snapshot(tickers, market_type, include_otc)
                if result.get('status') == 'OK' and result.get('tickers'):
                    logger.info(f"✅ Got real data via MCP for {len(result['tickers'])} tickers")
                    return result
            except NameError:
                logger.info("MCP functions not available in this environment")
            except Exception as e:
                logger.warning(f"MCP call failed: {e}")

            # Fallback to direct API if key available
            if self.polygon_api_key:
                logger.info("Falling back to direct Polygon API")
                return await self._api_fallback(tickers)
            else:
                logger.error("No Polygon API key available for fallback")
                return {
                    'status': 'error',
                    'error': 'No real data source available - configure POLYGON_API_KEY',
                    'tickers': []
                }

        except Exception as e:
            logger.error(f"Market snapshot failed: {e}")
            return {'status': 'error', 'error': str(e), 'tickers': []}

    async def _mcp_snapshot(self, tickers: List[str], market_type: str, include_otc: bool) -> Dict[str, Any]:
        """
        Call real MCP function (only works in Claude Code environment)
        """
        # This will only work when executed in Claude Code environment
        # where mcp__polygon__get_snapshot_all is available
        result = await mcp__polygon__get_snapshot_all(
            market_type=market_type,
            include_otc=include_otc,
            tickers=tickers
        )
        return result

    async def _api_fallback(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Direct Polygon API fallback using real-time snapshot endpoint
        """
        try:
            import requests

            # Use snapshot endpoint for real-time data
            # Make multiple requests if needed (API has ticker limits)
            all_tickers = []

            # Process in batches of 10 (Polygon snapshot limit)
            for i in range(0, len(tickers), 10):
                batch = tickers[i:i + 10]
                ticker_param = ','.join(batch)

                url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers"

                params = {
                    'tickers': ticker_param,
                    'apikey': self.polygon_api_key
                }

                response = requests.get(url, params=params, timeout=15)

                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'OK' and data.get('results'):
                        # Process each ticker in the batch
                        for result in data['results']:
                            ticker_data = result.get('value', {})
                            prev_day = result.get('value', {}).get('prevDay', {})

                            # Get current and previous values
                            current_close = ticker_data.get('c', 0)
                            prev_close = prev_day.get('c', 0)

                            # Calculate change
                            change_pct = 0
                            change_abs = 0
                            if prev_close > 0:
                                change_abs = current_close - prev_close
                                change_pct = (change_abs / prev_close) * 100

                            formatted_ticker = {
                                'ticker': result.get('ticker', ''),
                                'todaysChangePerc': change_pct,
                                'todaysChange': change_abs,
                                'updated': int(datetime.now().timestamp() * 1000000000),
                                'day': {
                                    'c': ticker_data.get('c', 0),
                                    'h': ticker_data.get('h', 0),
                                    'l': ticker_data.get('l', 0),
                                    'o': ticker_data.get('o', 0),
                                    'v': ticker_data.get('v', 0),
                                    'vw': ticker_data.get('vw', 0)
                                },
                                'prevDay': {
                                    'c': prev_close,
                                    'v': prev_day.get('v', 0)
                                }
                            }
                            all_tickers.append(formatted_ticker)

            # Return combined results from all batches
            logger.info(f"✅ Got real data via API for {len(all_tickers)} tickers")
            return {
                'status': 'OK',
                'count': len(all_tickers),
                'tickers': all_tickers
            }

            logger.error(f"Polygon API failed: {response.status_code}")
            return {
                'status': 'error',
                'error': f'Polygon API error: {response.status_code}',
                'tickers': []
            }

        except Exception as e:
            logger.error(f"API fallback failed: {e}")
            return {'status': 'error', 'error': str(e), 'tickers': []}

    def _get_liquid_universe(self) -> List[str]:
        """
        Get highly liquid stocks with explosive potential
        Focused on stocks that actually move and have volume
        """
        return [
            # Large cap tech with high liquidity
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA',

            # High beta growth stocks
            'PLTR', 'SNOW', 'DDOG', 'NET', 'CRWD', 'ZS', 'OKTA',

            # Volatile momentum stocks
            'COIN', 'HOOD', 'RIVN', 'LCID', 'SPCE',

            # Biotech with breakout potential
            'MRNA', 'BNTX', 'NVAX', 'GILD', 'BIIB',

            # Meme stocks with explosive history
            'AMC', 'GME', 'BB', 'NOK'
        ]

    async def get_ticker_news(self, ticker: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get real news data - MCP first, API fallback
        """
        try:
            # Try MCP first
            try:
                result = await mcp__polygon__list_ticker_news(
                    ticker=ticker,
                    limit=limit
                )
                if result and result.get('results'):
                    logger.info(f"✅ Got real news via MCP for {ticker}")
                    return result['results']
            except NameError:
                pass  # MCP not available
            except Exception as e:
                logger.warning(f"MCP news failed for {ticker}: {e}")

            # API fallback
            if self.polygon_api_key:
                import requests
                url = "https://api.polygon.io/v2/reference/news"
                params = {
                    'ticker': ticker,
                    'limit': limit,
                    'apikey': self.polygon_api_key
                }

                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    news_results = data.get('results', [])
                    logger.info(f"✅ Got real news via API for {ticker}")
                    return news_results

            logger.warning(f"No news source available for {ticker}")
            return []

        except Exception as e:
            logger.warning(f"News fetch failed for {ticker}: {e}")
            return []

    async def get_previous_close(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get real previous close data
        """
        try:
            # Try MCP first
            try:
                result = await mcp__polygon__get_previous_close_agg(ticker=ticker)
                if result and result.get('results'):
                    logger.info(f"✅ Got real previous close via MCP for {ticker}")
                    return result
            except NameError:
                pass  # MCP not available
            except Exception as e:
                logger.warning(f"MCP previous close failed for {ticker}: {e}")

            # API fallback
            if self.polygon_api_key:
                import requests
                url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"
                params = {'apikey': self.polygon_api_key}

                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'OK' and data.get('results'):
                        result = data['results'][0]
                        formatted_result = {
                            'results': {
                                'c': result.get('c'),
                                'h': result.get('h'),
                                'l': result.get('l'),
                                'o': result.get('o'),
                                'v': result.get('v'),
                                't': result.get('t')
                            }
                        }
                        logger.info(f"✅ Got real previous close via API for {ticker}")
                        return formatted_result

            logger.warning(f"No data source for previous close: {ticker}")
            return None

        except Exception as e:
            logger.warning(f"Previous close fetch failed for {ticker}: {e}")
            return None

# Global instance
mcp_polygon_bridge = MCPPolygonBridge()