#!/usr/bin/env python3
"""
Short Interest Service
Real-time short interest data integration with Yahoo Finance API and FINRA schedule awareness.
Replaces placeholder 0.1% short interest values with accurate market data.
"""

import os
import asyncio
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    logging.warning("yfinance not installed - short interest will use fallback data")

from ..shared.redis_client import get_redis_client

logger = logging.getLogger(__name__)

@dataclass
class ShortInterestData:
    """Short interest data with metadata"""
    symbol: str
    short_percent_float: float  # As decimal (0.15 = 15%)
    short_ratio: float         # Days to cover
    shares_short: int         # Absolute number of shares
    source: str               # 'yahoo_finance', 'cache', 'fallback'
    confidence: float         # 0.0-1.0 data quality score
    last_updated: datetime
    settlement_date: Optional[datetime] = None
    expires_at: Optional[datetime] = None

class ShortInterestService:
    """
    Short Interest Service with multi-frequency updates:
    - Bi-monthly: Yahoo Finance (FINRA schedule)
    - Real-time caching with Redis
    - Hierarchical fallbacks for reliability
    """
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self.cache_prefix = "amc:short_interest"
        self.cache_ttl = 30 * 24 * 3600  # 30 days
        
        # FINRA reporting schedule - 15th and last day of month
        self.finra_reporting_days = [15, -1]  # -1 = last day
        
        # Fallback short interest by sector (conservative estimates)
        self.sector_fallbacks = {
            'technology': 0.08,      # 8%
            'healthcare': 0.12,      # 12% 
            'energy': 0.15,          # 15%
            'financial': 0.06,       # 6%
            'consumer': 0.10,        # 10%
            'default': 0.15          # 15% conservative default
        }
    
    async def get_short_interest(self, symbol: str) -> ShortInterestData:
        """
        Get short interest data with hierarchical fallback:
        1. Redis cache (fastest)
        2. Yahoo Finance API (authoritative)  
        3. Historical average (reliable)
        4. Sector average (conservative)
        5. Default 15% (ultra-conservative)
        """
        try:
            # Try cache first
            cached_data = await self._get_cached_short_interest(symbol)
            if cached_data and not self._is_expired(cached_data):
                return cached_data
            
            # Try Yahoo Finance API
            if HAS_YFINANCE:
                yahoo_data = await self._fetch_yahoo_short_interest(symbol)
                if yahoo_data:
                    await self._cache_short_interest(symbol, yahoo_data)
                    return yahoo_data
            
            # Fallback to historical or defaults
            fallback_data = await self._get_fallback_short_interest(symbol)
            return fallback_data
            
        except Exception as e:
            logger.error(f"Error getting short interest for {symbol}: {e}")
            return self._create_default_short_interest(symbol)
    
    async def get_bulk_short_interest(self, symbols: List[str]) -> Dict[str, ShortInterestData]:
        """Get short interest for multiple symbols efficiently"""
        results = {}
        
        # Get cached data first
        cached_results = await self._get_bulk_cached(symbols)
        
        # Identify symbols needing fresh data
        symbols_needing_fetch = [
            symbol for symbol, data in cached_results.items()
            if not data or self._is_expired(data)
        ]
        
        # Fetch fresh data for missing symbols
        if symbols_needing_fetch and HAS_YFINANCE:
            fresh_data = await self._fetch_bulk_yahoo(symbols_needing_fetch)
            cached_results.update(fresh_data)
        
        # Fill remaining gaps with fallbacks
        for symbol in symbols:
            if symbol not in cached_results or cached_results[symbol] is None:
                cached_results[symbol] = await self._get_fallback_short_interest(symbol)
        
        return cached_results
    
    async def _fetch_yahoo_short_interest(self, symbol: str) -> Optional[ShortInterestData]:
        """Fetch short interest from Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Extract short interest data
            short_percent = info.get('shortPercentOfFloat')
            short_ratio = info.get('shortRatio')
            shares_short = info.get('sharesShort')
            
            if short_percent is None:
                return None
            
            # Yahoo Finance already returns decimal format (0.0934 = 9.34%)
            # DO NOT divide by 100 - the value is already in decimal format
            short_percent_decimal = float(short_percent) if short_percent else 0.0
            
            # Data quality scoring
            confidence = self._calculate_confidence(info)
            
            return ShortInterestData(
                symbol=symbol,
                short_percent_float=short_percent_decimal,
                short_ratio=float(short_ratio or 0.0),
                shares_short=int(shares_short or 0),
                source='yahoo_finance',
                confidence=confidence,
                last_updated=datetime.utcnow(),
                settlement_date=self._estimate_settlement_date(),
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
            
        except Exception as e:
            logger.warning(f"Yahoo Finance fetch failed for {symbol}: {e}")
            return None
    
    def _calculate_confidence(self, info: Dict) -> float:
        """Calculate data quality confidence score (0.0-1.0)"""
        confidence = 0.5  # Base confidence
        
        # Increase confidence for complete data
        if info.get('shortPercentOfFloat') is not None:
            confidence += 0.2
        if info.get('shortRatio') is not None:
            confidence += 0.1
        if info.get('sharesShort') is not None:
            confidence += 0.1
        if info.get('floatShares') is not None:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _estimate_settlement_date(self) -> datetime:
        """Estimate last FINRA settlement date"""
        today = datetime.utcnow()
        
        # Check if we're past the 15th
        if today.day >= 18:  # 3 days after 15th for reporting delay
            return datetime(today.year, today.month, 15)
        else:
            # Last month's end-of-month
            last_month = today.replace(day=1) - timedelta(days=1)
            return datetime(last_month.year, last_month.month, last_month.day)
    
    async def _get_cached_short_interest(self, symbol: str) -> Optional[ShortInterestData]:
        """Get cached short interest data"""
        try:
            cache_key = f"{self.cache_prefix}:{symbol}"
            cached_json = self.redis_client.get(cache_key)
            
            if cached_json:
                data = json.loads(cached_json)
                return ShortInterestData(
                    symbol=data['symbol'],
                    short_percent_float=data['short_percent_float'],
                    short_ratio=data['short_ratio'],
                    shares_short=data['shares_short'],
                    source=data['source'],
                    confidence=data['confidence'],
                    last_updated=datetime.fromisoformat(data['last_updated']),
                    settlement_date=datetime.fromisoformat(data['settlement_date']) if data.get('settlement_date') else None,
                    expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None
                )
        except Exception as e:
            logger.warning(f"Cache read failed for {symbol}: {e}")
        
        return None
    
    async def _cache_short_interest(self, symbol: str, data: ShortInterestData):
        """Cache short interest data in Redis"""
        try:
            cache_key = f"{self.cache_prefix}:{symbol}"
            cache_data = {
                'symbol': data.symbol,
                'short_percent_float': data.short_percent_float,
                'short_ratio': data.short_ratio,
                'shares_short': data.shares_short,
                'source': data.source,
                'confidence': data.confidence,
                'last_updated': data.last_updated.isoformat(),
                'settlement_date': data.settlement_date.isoformat() if data.settlement_date else None,
                'expires_at': data.expires_at.isoformat() if data.expires_at else None
            }
            
            self.redis_client.setex(cache_key, self.cache_ttl, json.dumps(cache_data))
            logger.debug(f"Cached short interest for {symbol}: {data.short_percent_float:.1%}")
            
        except Exception as e:
            logger.warning(f"Cache write failed for {symbol}: {e}")
    
    def _is_expired(self, data: ShortInterestData) -> bool:
        """Check if short interest data is expired"""
        if not data.expires_at:
            # If no expiration, assume data older than 35 days is stale
            return datetime.utcnow() - data.last_updated > timedelta(days=35)
        
        return datetime.utcnow() > data.expires_at
    
    async def _get_fallback_short_interest(self, symbol: str) -> ShortInterestData:
        """Get fallback short interest when primary sources fail"""
        # Use sector-based fallback
        sector = self._guess_sector(symbol)
        fallback_percent = self.sector_fallbacks.get(sector, self.sector_fallbacks['default'])
        
        return ShortInterestData(
            symbol=symbol,
            short_percent_float=fallback_percent,
            short_ratio=5.0,  # Conservative 5-day estimate
            shares_short=0,   # Unknown
            source='sector_fallback',
            confidence=0.3,   # Low confidence
            last_updated=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)  # Shorter TTL for fallback
        )
    
    def _guess_sector(self, symbol: str) -> str:
        """Simple sector guessing based on symbol patterns"""
        # This is a simplified heuristic - in production you'd use proper sector data
        tech_patterns = ['NVDA', 'AAPL', 'MSFT', 'GOOGL', 'QUBT', 'PLTR']
        energy_patterns = ['WULF', 'RIOT', 'MARA', 'HUT', 'BITF', 'CLSK']
        healthcare_patterns = ['TEVA', 'RGTI', 'OCGN', 'COTI', 'SERA']
        
        if symbol in tech_patterns or any(pattern in symbol for pattern in ['TECH', 'SOFT', 'DATA']):
            return 'technology'
        elif symbol in energy_patterns or any(pattern in symbol for pattern in ['MINE', 'OIL', 'GAS']):
            return 'energy'  
        elif symbol in healthcare_patterns or any(pattern in symbol for pattern in ['BIO', 'PHARM', 'MED']):
            return 'healthcare'
        else:
            return 'default'
    
    def _create_default_short_interest(self, symbol: str) -> ShortInterestData:
        """Create ultra-conservative default when all else fails"""
        return ShortInterestData(
            symbol=symbol,
            short_percent_float=0.15,  # 15% conservative default
            short_ratio=5.0,
            shares_short=0,
            source='default_fallback',
            confidence=0.1,  # Very low confidence
            last_updated=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1)  # Very short TTL
        )
    
    async def _get_bulk_cached(self, symbols: List[str]) -> Dict[str, Optional[ShortInterestData]]:
        """Get cached data for multiple symbols efficiently"""
        results = {}
        
        for symbol in symbols:
            cached_data = await self._get_cached_short_interest(symbol)
            results[symbol] = cached_data
        
        return results
    
    async def _fetch_bulk_yahoo(self, symbols: List[str]) -> Dict[str, ShortInterestData]:
        """Fetch Yahoo Finance data for multiple symbols"""
        results = {}
        
        # Batch fetch to avoid rate limiting
        for symbol in symbols[:10]:  # Limit batch size
            data = await self._fetch_yahoo_short_interest(symbol)
            if data:
                results[symbol] = data
                await self._cache_short_interest(symbol, data)
                
                # Small delay to respect rate limits
                await asyncio.sleep(0.1)
        
        return results
    
    def is_finra_reporting_day(self, date: datetime = None) -> bool:
        """Check if today (or given date) is a FINRA reporting day"""
        if date is None:
            date = datetime.utcnow()
        
        # Check 15th or last day of month
        if date.day == 15:
            return True
        
        # Check if it's the last day of the month
        next_month = date.replace(day=28) + timedelta(days=4)
        last_day = (next_month - timedelta(days=next_month.day)).day
        return date.day == last_day
    
    async def refresh_all_short_interest(self, symbols: List[str] = None) -> Dict[str, bool]:
        """Force refresh short interest data for all symbols"""
        if symbols is None:
            # Get symbols from fallback universe
            from ..jobs.discover import UNIVERSE_FALLBACK
            symbols = UNIVERSE_FALLBACK
        
        results = {}
        logger.info(f"Refreshing short interest for {len(symbols)} symbols")
        
        for symbol in symbols:
            try:
                if HAS_YFINANCE:
                    data = await self._fetch_yahoo_short_interest(symbol)
                    if data:
                        await self._cache_short_interest(symbol, data)
                        results[symbol] = True
                        logger.debug(f"Refreshed {symbol}: {data.short_percent_float:.1%}")
                    else:
                        results[symbol] = False
                else:
                    results[symbol] = False
                
                # Rate limiting
                await asyncio.sleep(0.2)
                
            except Exception as e:
                logger.error(f"Failed to refresh {symbol}: {e}")
                results[symbol] = False
        
        success_count = sum(results.values())
        logger.info(f"Short interest refresh complete: {success_count}/{len(symbols)} successful")
        
        return results

# Global service instance
_short_interest_service = None

async def get_short_interest_service() -> ShortInterestService:
    """Get global short interest service instance"""
    global _short_interest_service
    if _short_interest_service is None:
        _short_interest_service = ShortInterestService()
    return _short_interest_service