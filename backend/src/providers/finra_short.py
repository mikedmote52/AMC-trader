"""
FINRA Short Interest Data Provider
Provides bi-monthly short interest and daily short volume data with no fabrication
"""

import asyncio
import aiohttp
import structlog
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import json
import os

logger = structlog.get_logger()

class FINRAShortProvider:
    """
    Provider for FINRA short interest and short volume data
    - Short Interest: Bi-monthly official FINRA reports
    - Short Volume: Daily short sale volume from FINRA
    - DTCR: Days to Cover Ratio = shares_short / ADV30
    - SVR: Short Volume Ratio = short_volume / total_volume
    """
    
    def __init__(self):
        self.base_url = "https://api.finra.org/data/group/otcmarket/name"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'Accept': 'application/json'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_short_interest(self, symbol: str) -> Dict:
        """
        Get latest short interest data for symbol
        Returns: {
            'short_interest_shares': int,
            'shares_outstanding': int,
            'short_interest_pct': float,
            'report_date': str (ISO),
            'asof': str (ISO),
            'source': 'finra',
            'staleness_policy_pass': bool,
            'latency_sec': float
        }
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            if not self.session:
                raise RuntimeError("Provider not initialized - use async context manager")
            
            # FINRA Short Interest API endpoint
            url = f"{self.base_url}/shortInterest"
            params = {
                'limit': 1,
                'offset': 0,
                'symbol': symbol,
                'sortBy': 'reportDate',
                'sortOrder': 'desc'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 429:
                    logger.warning("FINRA API rate limited", symbol=symbol)
                    await asyncio.sleep(1)  # Brief backoff
                    return self._empty_response(start_time, "rate_limited")
                
                if response.status != 200:
                    logger.error("FINRA API error", symbol=symbol, status=response.status)
                    return self._empty_response(start_time, f"api_error_{response.status}")
                
                data = await response.json()
                
                if not data or len(data) == 0:
                    logger.info("No FINRA short interest data found", symbol=symbol)
                    return self._empty_response(start_time, "no_data")
                
                record = data[0]
                report_date = datetime.fromisoformat(record['reportDate']).replace(tzinfo=timezone.utc)
                
                # Check if data is fresh enough (bi-monthly reports, allow up to 20 days)
                age_days = (datetime.now(timezone.utc) - report_date).days
                staleness_pass = age_days <= 20
                
                latency_sec = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                result = {
                    'short_interest_shares': int(record.get('shortInterest', 0)),
                    'shares_outstanding': int(record.get('totalSharesOutstanding', 0)),
                    'short_interest_pct': float(record.get('shortInterest', 0)) / max(float(record.get('totalSharesOutstanding', 1)), 1) * 100,
                    'report_date': report_date.isoformat(),
                    'asof': datetime.now(timezone.utc).isoformat(),
                    'source': 'finra',
                    'ingested_at': datetime.now(timezone.utc).isoformat(),
                    'staleness_policy_pass': staleness_pass,
                    'latency_sec': round(latency_sec, 3)
                }
                
                logger.info("FINRA short interest retrieved", symbol=symbol, si_pct=result['short_interest_pct'], age_days=age_days)
                return result
                
        except Exception as e:
            logger.error("FINRA short interest fetch failed", symbol=symbol, error=str(e))
            return self._empty_response(start_time, f"error_{str(e)[:20]}")
    
    async def get_daily_short_volume(self, symbol: str) -> Dict:
        """
        Get latest daily short volume data
        Returns: {
            'short_volume': int,
            'total_volume': int,
            'svr': float (short_volume / total_volume),
            'trade_date': str (ISO),
            'asof': str (ISO),
            'source': 'finra',
            'staleness_policy_pass': bool,
            'latency_sec': float
        }
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            if not self.session:
                raise RuntimeError("Provider not initialized - use async context manager")
            
            # FINRA Daily Short Volume API
            url = f"{self.base_url}/dailyShortSaleVolume"
            params = {
                'limit': 1,
                'offset': 0,
                'symbol': symbol,
                'sortBy': 'tradeDate',
                'sortOrder': 'desc'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 429:
                    logger.warning("FINRA API rate limited", symbol=symbol)
                    await asyncio.sleep(1)
                    return self._empty_response(start_time, "rate_limited")
                
                if response.status != 200:
                    logger.error("FINRA API error", symbol=symbol, status=response.status)
                    return self._empty_response(start_time, f"api_error_{response.status}")
                
                data = await response.json()
                
                if not data or len(data) == 0:
                    logger.info("No FINRA short volume data found", symbol=symbol)
                    return self._empty_response(start_time, "no_data")
                
                record = data[0]
                trade_date = datetime.fromisoformat(record['tradeDate']).replace(tzinfo=timezone.utc)
                
                # Check freshness (allow up to 36 hours for daily data)
                age_hours = (datetime.now(timezone.utc) - trade_date).total_seconds() / 3600
                staleness_pass = age_hours <= 36
                
                short_volume = int(record.get('shortVolume', 0))
                total_volume = int(record.get('totalVolume', 0))
                svr = short_volume / max(total_volume, 1) * 100 if total_volume > 0 else 0
                
                latency_sec = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                result = {
                    'short_volume': short_volume,
                    'total_volume': total_volume,
                    'svr': round(svr, 2),
                    'trade_date': trade_date.isoformat(),
                    'asof': datetime.now(timezone.utc).isoformat(),
                    'source': 'finra',
                    'ingested_at': datetime.now(timezone.utc).isoformat(),
                    'staleness_policy_pass': staleness_pass,
                    'latency_sec': round(latency_sec, 3)
                }
                
                logger.info("FINRA short volume retrieved", symbol=symbol, svr=svr, age_hours=round(age_hours, 1))
                return result
                
        except Exception as e:
            logger.error("FINRA short volume fetch failed", symbol=symbol, error=str(e))
            return self._empty_response(start_time, f"error_{str(e)[:20]}")
    
    def calculate_dtcr(self, short_interest_shares: int, adv30: float) -> float:
        """
        Calculate Days to Cover Ratio
        DTCR = short_interest_shares / adv30
        """
        if adv30 <= 0:
            return 0.0
        return short_interest_shares / adv30
    
    def _empty_response(self, start_time: datetime, reason: str) -> Dict:
        """Generate empty response with error reason"""
        latency_sec = (datetime.now(timezone.utc) - start_time).total_seconds()
        return {
            'short_interest_shares': 0,
            'shares_outstanding': 0,
            'short_interest_pct': 0.0,
            'short_volume': 0,
            'total_volume': 0,
            'svr': 0.0,
            'report_date': None,
            'trade_date': None,
            'asof': datetime.now(timezone.utc).isoformat(),
            'source': 'finra',
            'ingested_at': datetime.now(timezone.utc).isoformat(),
            'staleness_policy_pass': False,
            'latency_sec': round(latency_sec, 3),
            'error_reason': reason
        }

# Async context manager usage example:
# async with FINRAShortProvider() as provider:
#     si_data = await provider.get_short_interest('AAPL')
#     sv_data = await provider.get_daily_short_volume('AAPL')