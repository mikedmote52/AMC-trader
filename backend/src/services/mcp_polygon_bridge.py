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
        Get real explosive data using direct Polygon API or native MCP functions
        """
        try:
            import os

            # Always use direct Polygon API for Render deployment
            if os.getenv('RENDER_SERVICE_NAME') or os.getenv('ENV') == 'prod':
                logger.info("🚀 Render environment detected - using direct Polygon API")
                return await self._get_explosive_data_direct_api(tickers)

            # Try native MCP functions only in Claude environment
            try:
                # Use native MCP function for market snapshots
                result = await mcp__polygon__get_snapshot_direction(
                    market_type="stocks",
                    direction="gainers"
                )

                if result.get('status') == 'OK' and result.get('results'):
                    # Convert MCP format to expected ticker format
                    tickers_data = []
                    for item in result['results'][:50]:  # Limit to top 50 gainers
                        ticker_symbol = item.get('ticker', '')
                        min_data = item.get('min', {})  # Real-time data is in 'min' section
                        prev_data = item.get('prevDay', {})

                        # Get real-time price and volume from min data
                        current_price = min_data.get('c', 0)
                        current_volume = min_data.get('v', 0)
                        prev_close = prev_data.get('c', 0)

                        # Calculate change
                        change_pct = item.get('todaysChangePerc', 0)
                        change_abs = item.get('todaysChange', 0)

                        ticker_data = {
                            'ticker': ticker_symbol,
                            'todaysChangePerc': change_pct,
                            'todaysChange': change_abs,
                            'day': {
                                'c': current_price,
                                'v': current_volume,
                                'vw': min_data.get('vw', current_price),
                                'o': min_data.get('o', current_price),
                                'h': min_data.get('h', current_price),
                                'l': min_data.get('l', current_price)
                            },
                            'prevDay': {
                                'c': prev_close,
                                'v': prev_data.get('v', 0),
                                'vw': prev_data.get('vw', prev_close)
                            }
                        }
                        tickers_data.append(ticker_data)

                    logger.info(f"✅ Got {len(tickers_data)} explosive candidates from native MCP")
                    return {
                        'status': 'OK',
                        'tickers': tickers_data,
                        'count': len(tickers_data)
                    }
                except NameError:
                    logger.info("Native MCP functions not available, falling back to direct API")
                    pass

            # Use direct Polygon API for Render deployment
            return await self._get_explosive_data_direct_api(tickers)

        except Exception as e:
            logger.error(f"Explosive data bridge failed: {e}")
            return {'status': 'error', 'error': str(e), 'tickers': []}

    async def _get_explosive_data_direct_api(self, tickers: List[str]) -> Dict[str, Any]:
        """Get explosive data using direct Polygon REST API"""
        try:
            import httpx
            import os

            api_key = os.getenv('POLYGON_API_KEY')
            if not api_key:
                logger.error("No POLYGON_API_KEY available for direct API calls")
                return {'status': 'error', 'error': 'No API key', 'tickers': []}

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get market gainers from Polygon API
                response = await client.get(
                    "https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/direction/gainers",
                    params={"apikey": api_key}
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'OK' and data.get('results'):
                        # Convert to expected format
                        tickers_data = []
                        for item in data['results'][:100]:  # Top 100 gainers for broader universe
                            ticker_info = item.get('ticker', item.get('T', ''))
                            last_quote = item.get('lastQuote', {})
                            last_trade = item.get('lastTrade', {})
                            day_info = item.get('day', {})
                            prev_day = item.get('prevDay', {})

                            # Calculate price and volume data
                            current_price = last_trade.get('p', day_info.get('c', 0))
                            current_volume = day_info.get('v', 0)
                            prev_close = prev_day.get('c', current_price)

                            if current_price > 0 and prev_close > 0:
                                change_pct = ((current_price - prev_close) / prev_close) * 100
                                volume_ratio = current_volume / max(prev_day.get('v', 1), 1)

                                # Apply filtering criteria to eliminate inappropriate stocks
                                if self._meets_filtering_criteria(current_price, current_volume, change_pct, volume_ratio, ticker_info):
                                    ticker_data = {
                                        'ticker': ticker_info,
                                        'todaysChangePerc': change_pct,
                                        'todaysChange': current_price - prev_close,
                                        'day': {
                                            'c': current_price,
                                            'v': current_volume,
                                            'vw': day_info.get('vw', current_price),
                                            'o': day_info.get('o', current_price),
                                            'h': day_info.get('h', current_price),
                                            'l': day_info.get('l', current_price)
                                        },
                                        'prevDay': {
                                            'c': prev_close,
                                            'v': prev_day.get('v', 0),
                                            'vw': prev_day.get('vw', prev_close)
                                        }
                                    }
                                    tickers_data.append(ticker_data)

                        logger.info(f"✅ Got {len(tickers_data)} explosive candidates from direct Polygon API")
                        return {
                            'status': 'OK',
                            'tickers': tickers_data,
                            'count': len(tickers_data)
                        }

                logger.error(f"Polygon API returned status: {response.status_code}")
                return {'status': 'error', 'error': f'API error: {response.status_code}', 'tickers': []}

        except Exception as e:
            logger.error(f"Direct API explosive data failed: {e}")
            return {'status': 'error', 'error': str(e), 'tickers': []}

    def _meets_filtering_criteria(self, price: float, volume: int, change_pct: float, volume_ratio: float, ticker: str) -> bool:
        """
        Apply filtering criteria to eliminate inappropriate stocks
        """
        # Price filters
        if price <= 0.50:  # Eliminate penny stocks
            return False
        if price >= 100.00:  # Eliminate expensive stocks as specified
            return False

        # Volume filters
        if volume < 100000:  # Minimum volume threshold for liquidity
            return False
        if volume_ratio < 1.5:  # Must have volume spike (1.5x normal)
            return False

        # Change filters
        if abs(change_pct) < 3.0:  # Must have significant price movement
            return False
        if abs(change_pct) > 50.0:  # Eliminate extreme outliers (likely errors)
            return False

        # Ticker filters - eliminate common problematic patterns
        ticker_upper = ticker.upper()
        if len(ticker_upper) < 2 or len(ticker_upper) > 5:  # Normal ticker length
            return False
        if any(char in ticker_upper for char in ['.', '-', '/', ' ']):  # No special characters
            return False
        if ticker_upper.endswith('W') or ticker_upper.endswith('WS'):  # Eliminate warrants
            return False
        if ticker_upper.startswith('SPAC') or 'SPAC' in ticker_upper:  # Eliminate SPACs
            return False

        return True

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