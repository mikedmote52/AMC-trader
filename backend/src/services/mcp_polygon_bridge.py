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
        Use real explosive data from HTTP MCP bridge
        """
        logger.info("🎯 Using real explosive data from HTTP MCP bridge")
        return await self._explosive_data_bridge(tickers)

    async def _explosive_data_bridge(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Get real explosive data using HTTP MCP client
        """
        try:
            from backend.src.mcp_http_client import mcp_http_client

            # First try to get market movers for explosive candidates
            movers_data = await mcp_http_client.get_market_movers(direction="gainers")

            if movers_data.get('available') and movers_data.get('movers'):
                # Convert movers data to ticker format
                tickers_data = []
                for mover in movers_data['movers']:
                    symbol = mover.get('symbol', '')
                    if symbol and (not tickers or symbol in tickers):
                        # Convert mover data to expected ticker format
                        ticker_data = {
                            'ticker': symbol,
                            'todaysChangePerc': mover.get('change_pct', 0),
                            'todaysChange': mover.get('change_pct', 0) * mover.get('price', 0) / 100,
                            'day': {
                                'c': mover.get('price', 0),
                                'v': mover.get('volume', 0),
                                'vw': mover.get('vwap', mover.get('price', 0))
                            },
                            'prevDay': {
                                'c': mover.get('price', 0) / (1 + mover.get('change_pct', 0) / 100)
                            }
                        }
                        tickers_data.append(ticker_data)

                logger.info(f"✅ Got {len(tickers_data)} explosive candidates from HTTP MCP")
                return {
                    'status': 'OK',
                    'tickers': tickers_data,
                    'count': len(tickers_data)
                }

            # Fallback to market snapshots if movers not available
            snapshot_data = await mcp_http_client.get_market_snapshots(tickers=tickers[:20])
            if snapshot_data.get('tickers'):
                logger.info(f"✅ Got {len(snapshot_data['tickers'])} tickers from HTTP MCP snapshots")
                return {
                    'status': 'OK',
                    'tickers': snapshot_data['tickers'],
                    'count': len(snapshot_data['tickers'])
                }

            logger.warning("No data available from HTTP MCP client")
            return {'status': 'error', 'error': 'No data from HTTP MCP', 'tickers': []}

        except Exception as e:
            logger.error(f"HTTP MCP bridge failed: {e}")
            return {'status': 'error', 'error': str(e), 'tickers': []}

        # Filter for requested tickers and format as expected by discovery system
        result_tickers = []
        for ticker in tickers:
            if ticker in explosive_data:
                result_tickers.append(explosive_data[ticker])

        logger.info(f"✅ MCP bridge returning {len(result_tickers)} explosive candidates")
        return {
            'status': 'OK',
            'count': len(result_tickers),
            'tickers': result_tickers
        }

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
                            # Extract ticker data directly
                            ticker_symbol = result.get('ticker', '')

                            # Get day and prevDay data
                            day_data = result.get('day', {})
                            prev_data = result.get('prevDay', {})

                            # Get current and previous values
                            current_close = day_data.get('c', 0)
                            prev_close = prev_data.get('c', 0)

                            # Calculate change
                            change_pct = 0
                            change_abs = 0
                            if prev_close > 0:
                                change_abs = current_close - prev_close
                                change_pct = (change_abs / prev_close) * 100

                            formatted_ticker = {
                                'ticker': ticker_symbol,
                                'todaysChangePerc': change_pct,
                                'todaysChange': change_abs,
                                'updated': int(datetime.now().timestamp() * 1000000000),
                                'day': day_data,
                                'prevDay': prev_data
                            }
                            all_tickers.append(formatted_ticker)

                else:
                    logger.warning(f"Polygon API failed for batch: {response.status_code}")

            # Return combined results from all batches
            if all_tickers:
                logger.info(f"✅ Got real data via API for {len(all_tickers)} tickers")
                return {
                    'status': 'OK',
                    'count': len(all_tickers),
                    'tickers': all_tickers
                }
            else:
                logger.error("No ticker data retrieved from API")
                return {
                    'status': 'error',
                    'error': 'No ticker data available from API',
                    'tickers': []
                }

        except Exception as e:
            logger.error(f"API fallback failed: {e}")
            return {'status': 'error', 'error': str(e), 'tickers': []}

    def _get_liquid_universe(self) -> List[str]:
        """
        Get stocks with explosive potential for discovery
        Focused on small/mid caps and high-beta stocks that can move explosively
        """
        return [
            # AI/Quantum stocks (high volatility)
            'QUBT', 'IONQ', 'RGTI', 'BBAI', 'SOUN', 'LUNR',

            # Crypto mining and blockchain
            'MARA', 'RIOT', 'CLSK', 'HUT', 'BITF', 'COIN', 'HOOD',

            # High beta growth stocks
            'PLTR', 'SNOW', 'DDOG', 'NET', 'CRWD', 'ZS',

            # Volatile momentum stocks
            'RIVN', 'LCID', 'SPCE', 'RBLX', 'SOFI',

            # Biotech with breakout potential
            'SAVA', 'MRNA', 'BNTX', 'NVAX', 'BIIB', 'VRTX',

            # Energy/EV growth plays
            'NIO', 'XPEV', 'LI', 'PLUG', 'FCEL', 'BE',

            # Recent IPOs and SPACs
            'WISH', 'CLOV', 'SKLZ', 'DKNG', 'NKLA'
        ]

    async def get_ticker_news(self, ticker: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get real news data - MCP first, API fallback
        """
        try:
            # MCP not available in backend - skip to API fallback

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
            # MCP not available in backend - skip to API fallback

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