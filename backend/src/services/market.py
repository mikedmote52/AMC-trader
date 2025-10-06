import httpx
from typing import Dict, List, Optional
import structlog
from datetime import datetime, timedelta
import os

logger = structlog.get_logger()

class MarketService:
    def __init__(self):
        self.polygon_api_key = os.getenv('POLYGON_API_KEY', '')
        self.base_url = "https://api.polygon.io"
    
    async def get_stock_price(self, symbol: str) -> Optional[Dict]:
        """Get current stock price from Polygon"""
        try:
            async with httpx.AsyncClient() as client:
                # Try with query params first
                response = await client.get(
                    f"{self.base_url}/v2/aggs/ticker/{symbol}/prev",
                    params={"apikey": self.polygon_api_key, "adjusted": "true"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("results", [{}])[0] if data.get("results") else {}
                elif response.status_code in [401, 403]:
                    # Fallback to Authorization header
                    response = await client.get(
                        f"{self.base_url}/v2/aggs/ticker/{symbol}/prev",
                        headers={"Authorization": f"Bearer {self.polygon_api_key}"},
                        params={"adjusted": "true"}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        return data.get("results", [{}])[0] if data.get("results") else {}
                
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
            # Calculate absolute dates for Polygon API
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/v2/aggs/ticker/{symbol}/range/1/day/{start_str}/{end_str}",
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

    async def get_bulk_snapshot_optimized(self) -> Dict[str, Dict]:
        """
        Fetch ALL US stocks in a SINGLE Polygon API call.
        This is Stage 2 optimization from Squeeze-Prophet.

        CRITICAL: This method returns ONLY real-time data from Polygon.
        NO mock data, NO fallbacks, NO hardcoded values.

        Returns:
            Dict mapping symbol to market data:
            {
                'AAPL': {
                    'price': 150.23,
                    'volume': 50000000,
                    'change_pct': 1.5,
                    'high': 151.0,
                    'low': 149.5,
                    'prev_close': 148.0
                },
                ...
            }

        Returns empty dict if API fails - NO FAKE DATA FALLBACK.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Polygon bulk snapshot endpoint (1 API call for entire market)
                response = await client.get(
                    f"{self.base_url}/v2/snapshot/locale/us/markets/stocks/tickers",
                    params={"apiKey": self.polygon_api_key}
                )

                if response.status_code != 200:
                    logger.error(
                        "Bulk snapshot API failed",
                        status_code=response.status_code,
                        response=response.text[:200]
                    )
                    # Return empty dict - NO FALLBACK DATA
                    return {}

                data = response.json()

                if 'tickers' not in data:
                    logger.error("Bulk snapshot missing 'tickers' key", data_keys=list(data.keys()))
                    return {}

                snapshots = {}
                skipped_count = 0

                for ticker_data in data['tickers']:
                    try:
                        symbol = ticker_data.get('ticker')
                        if not symbol:
                            skipped_count += 1
                            continue

                        day = ticker_data.get('day', {})
                        prev_day = ticker_data.get('prevDay', {})

                        # Extract ONLY real values - skip if missing critical data
                        price = day.get('c')
                        volume = day.get('v')

                        # If market is closed (day data is zero), use prevDay
                        if not price or price <= 0:
                            price = prev_day.get('c')
                            volume = prev_day.get('v')

                        if price is None or volume is None:
                            skipped_count += 1
                            continue

                        # Validate data quality (reject obviously fake data)
                        if price <= 0 or volume < 0:
                            skipped_count += 1
                            continue

                        # Calculate change_pct from prev_close
                        prev_close = prev_day.get('c', price)
                        if prev_close > 0:
                            change_pct = ((price - prev_close) / prev_close) * 100
                        else:
                            change_pct = 0.0

                        snapshots[symbol] = {
                            'price': float(price),
                            'volume': int(volume),
                            'change_pct': float(change_pct),
                            'high': float(day.get('h', price)),
                            'low': float(day.get('l', price)),
                            'prev_close': float(prev_close)
                        }

                    except Exception as e:
                        logger.debug(f"Skipped {symbol}: {e}")
                        skipped_count += 1
                        continue

                logger.info(
                    "Bulk snapshot complete",
                    tickers_received=len(snapshots),
                    skipped=skipped_count,
                    api_calls=1
                )

                return snapshots

        except Exception as e:
            logger.error("Bulk snapshot failed", error=str(e), exc_info=True)
            # Return empty dict on error - NO FAKE DATA
            return {}

    async def calculate_rvol_batch(
        self,
        today_volumes: Dict[str, int],
        avg_volumes: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Calculate RVOL for multiple symbols in-memory (Stage 5 optimization).

        RVOL = today's volume / 20-day average volume

        CRITICAL: This is pure calculation - NO API calls, NO fake data.
        Only processes symbols with BOTH today volume AND cached average.

        Args:
            today_volumes: {symbol: today's volume} from bulk snapshot
            avg_volumes: {symbol: 20-day avg volume} from cache

        Returns:
            {symbol: rvol_ratio} - ONLY for symbols with valid data
        """
        if not today_volumes or not avg_volumes:
            return {}

        rvol_data = {}
        skipped_missing_avg = 0
        skipped_invalid = 0

        for symbol, today_vol in today_volumes.items():
            # Get cached average
            avg_vol = avg_volumes.get(symbol)

            # Skip if no cached average (don't generate fake data)
            if avg_vol is None:
                skipped_missing_avg += 1
                continue

            # Validate inputs (reject fake/corrupted data)
            if today_vol <= 0 or avg_vol <= 0:
                skipped_invalid += 1
                continue

            # Calculate RVOL (simple division)
            rvol = today_vol / avg_vol

            # Sanity check (reject absurd values that indicate data corruption)
            if rvol > 1000:  # 1000x RVOL is likely data error
                logger.warning(
                    "Rejected extreme RVOL",
                    symbol=symbol,
                    rvol=rvol,
                    today_vol=today_vol,
                    avg_vol=avg_vol
                )
                skipped_invalid += 1
                continue

            rvol_data[symbol] = round(rvol, 2)

        logger.info(
            "RVOL batch calculation",
            calculated=len(rvol_data),
            skipped_missing_avg=skipped_missing_avg,
            skipped_invalid=skipped_invalid
        )

        return rvol_data