"""
Universe Loader - Efficient stock universe fetching with local filtering
Ensures full market coverage with proper filtering for <$100 stocks
"""
import os
import re
import logging
import asyncio
import aiohttp
from typing import List, Tuple, Dict, Any
from datetime import datetime, timedelta

from backend.src.constants import (
    UNIVERSE_MIN_EXPECTED, PRICE_MIN, PRICE_MAX, MIN_DOLLAR_VOL_M,
    EXCLUDE_TYPES, EXCLUDE_SYMBOL_PATTERNS, POLYGON_API_KEY,
    POLYGON_TIMEOUT_SECONDS, POLYGON_MAX_RETRIES, get_trading_date, is_fund_symbol
)

logger = logging.getLogger(__name__)

class UniverseLoader:
    """Loads and filters the complete stock universe from Polygon"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or POLYGON_API_KEY
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY required")
        
        self.session = None
        self.stats = {
            'total_fetched': 0,
            'after_price_filter': 0,
            'after_fund_filter': 0,
            'after_volume_filter': 0,
            'final_count': 0
        }
    
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=POLYGON_TIMEOUT_SECONDS)
        connector = aiohttp.TCPConnector(limit=20)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={'Accept-Encoding': 'gzip,deflate'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_grouped_data(self, date_str: str) -> List[Dict]:
        """Fetch grouped market data for all stocks on given date"""
        url = f"https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/{date_str}"
        params = {
            'apikey': self.api_key,
            'adjusted': 'true',
            'include_otc': 'false'
        }
        
        for attempt in range(POLYGON_MAX_RETRIES):
            try:
                logger.info(f"Fetching grouped data for {date_str} (attempt {attempt + 1})")
                async with self.session.get(url, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    results = data.get('results', [])
                    
                    if not results:
                        logger.warning(f"No results for {date_str}, trying previous day")
                        # Try previous day (up to 5 days back)
                        if attempt < 4:  # Try different dates on first few attempts
                            prev_date = (datetime.strptime(date_str, '%Y-%m-%d') - timedelta(days=attempt+1))
                            date_str = prev_date.strftime('%Y-%m-%d')
                            continue
                        else:
                            # On final attempt, fallback to reference endpoint
                            logger.warning("No grouped data available, will use reference endpoint")
                            return []
                    
                    logger.info(f"Fetched {len(results)} stocks from grouped endpoint")
                    return results
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == POLYGON_MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return []
    
    async def fetch_reference_data(self) -> List[Dict]:
        """Fallback: fetch from reference tickers endpoint"""
        logger.info("Fetching from reference tickers endpoint...")
        all_stocks = []
        next_url = None
        page = 1
        
        while page <= 10:  # Limit to prevent infinite loops
            if next_url:
                url = next_url
                params = {'apikey': self.api_key}
            else:
                url = "https://api.polygon.io/v3/reference/tickers"
                params = {
                    'apikey': self.api_key,
                    'active': 'true',
                    'market': 'stocks',
                    'type': 'CS',  # Common stock only
                    'limit': 1000,
                    'sort': 'ticker'
                }
            
            try:
                async with self.session.get(url, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    results = data.get('results', [])
                    if not results:
                        break
                    
                    # Convert to grouped format (without OHLCV data)
                    for ticker_data in results:
                        if ticker_data.get('type') == 'CS':  # Common stock
                            all_stocks.append({
                                'T': ticker_data['ticker'],
                                # No price/volume data from reference endpoint
                                'c': 0.0, 'v': 0, 'h': 0.0, 'l': 0.0, 'o': 0.0
                            })
                    
                    logger.info(f"Page {page}: +{len(results)} stocks (total: {len(all_stocks)})")
                    
                    # Check for next page
                    if data.get('next_url'):
                        next_url = data['next_url']
                        page += 1
                    else:
                        break
                        
            except Exception as e:
                logger.error(f"Error fetching reference data page {page}: {e}")
                break
            
            await asyncio.sleep(0.1)  # Rate limiting
        
        logger.info(f"Fetched {len(all_stocks)} stocks from reference endpoint")
        return all_stocks
    
    def apply_filters(self, raw_data: List[Dict]) -> Tuple[List[Tuple], Dict]:
        """Apply business filters locally after fetching universe"""
        logger.info(f"Applying filters to {len(raw_data)} stocks...")
        
        self.stats['total_fetched'] = len(raw_data)
        filtered_stocks = []
        
        for item in raw_data:
            symbol = item.get('T', '').strip().upper()
            if not symbol:
                continue
            
            price = float(item.get('c', 0))
            volume = int(item.get('v', 0))
            
            # Step 1: Price filter (<$100 rule)
            if not (PRICE_MIN <= price <= PRICE_MAX):
                continue
            
            self.stats['after_price_filter'] += 1
            
            # Step 2: Fund/ETF exclusion  
            if is_fund_symbol(symbol):
                continue
                
            self.stats['after_fund_filter'] += 1
            
            # Step 3: Volume filter (be more permissive for data availability)
            if volume > 0:  # Only apply volume filter if we have volume data
                dollar_volume_m = (price * volume) / 1_000_000.0
                if dollar_volume_m < MIN_DOLLAR_VOL_M:
                    continue
            # If volume is 0 or missing, include the stock (will be filtered later in BMS scoring)
            
            self.stats['after_volume_filter'] += 1
            
            # Keep basic info for scoring
            filtered_stocks.append((symbol, price, volume))
        
        self.stats['final_count'] = len(filtered_stocks)
        
        # Log filtering results
        logger.info(f"📊 Filtering Results:")
        logger.info(f"  Total fetched: {self.stats['total_fetched']}")
        logger.info(f"  After price filter (${PRICE_MIN}-${PRICE_MAX}): {self.stats['after_price_filter']}")
        logger.info(f"  After fund exclusion: {self.stats['after_fund_filter']}")
        logger.info(f"  After volume filter (${MIN_DOLLAR_VOL_M}M+): {self.stats['after_volume_filter']}")
        logger.info(f"  ✅ Final universe: {self.stats['final_count']} stocks")
        
        return filtered_stocks, self.stats.copy()
    
    async def load_and_filter_universe(self, date_str: str = None) -> Tuple[List[Tuple], Dict]:
        """Main entry point: load universe and apply filters"""
        if not date_str:
            date_str = get_trading_date()
        
        logger.info(f"Loading universe for {date_str}...")
        
        try:
            # Try grouped endpoint first (has OHLCV data)
            raw_data = await self.fetch_grouped_data(date_str)
            
            # If grouped fails or returns too few results, use reference
            if len(raw_data) < UNIVERSE_MIN_EXPECTED:
                logger.warning(f"Grouped data insufficient ({len(raw_data)} < {UNIVERSE_MIN_EXPECTED})")
                raw_data = await self.fetch_reference_data()
        
        except Exception as e:
            logger.error(f"Grouped fetch failed: {e}, trying reference endpoint")
            raw_data = await self.fetch_reference_data()
        
        # Coverage tripwire - ensure we have enough stocks
        if len(raw_data) < UNIVERSE_MIN_EXPECTED:
            raise RuntimeError(
                f"🚨 COVERAGE TRIPWIRE: Universe too small! "
                f"Got {len(raw_data)} stocks, expected ≥{UNIVERSE_MIN_EXPECTED}"
            )
        
        # Apply local filtering
        filtered_stocks, stats = self.apply_filters(raw_data)
        
        logger.info(f"✅ Universe loaded: {len(filtered_stocks)} qualified stocks")
        return filtered_stocks, stats


async def load_universe(date_str: str = None) -> Tuple[List[Tuple], Dict]:
    """Convenience function for loading universe"""
    async with UniverseLoader() as loader:
        return await loader.load_and_filter_universe(date_str)