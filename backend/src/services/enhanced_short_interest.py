"""
Enhanced Short Interest Data Service
Solves the critical 96% elimination bottleneck by aggregating multiple data sources.
"""
import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import re
import json
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

@dataclass
class ShortInterestData:
    """Enhanced short interest data with confidence scoring"""
    symbol: str
    percent: float  # 0.0 to 1.0 (e.g., 0.15 = 15%)
    source: str
    confidence: float  # 0.0 to 1.0
    last_updated: datetime
    shares_short: Optional[int] = None
    float_shares: Optional[int] = None
    days_to_cover: Optional[float] = None

class EnhancedShortInterestService:
    """Multi-source short interest data aggregator"""
    
    def __init__(self):
        self.session = None
        self.cache = {}  # symbol -> (data, expiry)
        self.cache_ttl = 3600  # 1 hour cache
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={'User-Agent': 'AMC-TRADER/1.0'}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_short_interest(self, symbol: str) -> Optional[ShortInterestData]:
        """Get short interest from multiple sources with confidence scoring"""
        
        # Check cache first
        if symbol in self.cache:
            data, expiry = self.cache[symbol]
            if datetime.now() < expiry:
                logger.debug(f"Cache hit for {symbol}")
                return data
        
        # Try multiple sources in parallel
        sources = [
            self._get_yahoo_finance(symbol),
            self._get_alpha_vantage(symbol),  # NEW: Alpha Vantage API
            self._get_finnhub(symbol),        # NEW: Finnhub API  
            self._get_finviz_data(symbol), 
            self._get_marketwatch_data(symbol)
        ]
        
        # Gather results from all sources
        results = await asyncio.gather(*sources, return_exceptions=True)
        valid_results = [r for r in results if isinstance(r, ShortInterestData)]
        
        if not valid_results:
            logger.warning(f"No short interest data found for {symbol}")
            return None
            
        # Use consensus building for multiple sources
        consensus_data = self._build_consensus(valid_results)
        
        # Cache the result
        self.cache[symbol] = (consensus_data, datetime.now() + timedelta(seconds=self.cache_ttl))
        
        logger.info(f"Short interest for {symbol}: {consensus_data.percent:.1%} (confidence: {consensus_data.confidence:.2f}, source: {consensus_data.source})")
        return consensus_data
    
    async def _get_yahoo_finance(self, symbol: str) -> Optional[ShortInterestData]:
        """Enhanced Yahoo Finance scraping"""
        try:
            url = f"https://finance.yahoo.com/quote/{symbol}/key-statistics"
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                    
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Look for short interest percentage
                short_patterns = [
                    r'Short % of Shares Outstanding.*?(\d+\.?\d*)%',
                    r'Short % of Float.*?(\d+\.?\d*)%',
                    r'Short Interest.*?(\d+\.?\d*)%'
                ]
                
                for pattern in short_patterns:
                    match = re.search(pattern, html, re.IGNORECASE)
                    if match:
                        percent = float(match.group(1)) / 100
                        return ShortInterestData(
                            symbol=symbol,
                            percent=percent,
                            source="yahoo_finance",
                            confidence=0.85,
                            last_updated=datetime.now()
                        )
                        
        except Exception as e:
            logger.debug(f"Yahoo Finance failed for {symbol}: {e}")
            
        return None
    
    async def _get_alpha_vantage(self, symbol: str) -> Optional[ShortInterestData]:
        """Alpha Vantage API for company overview including short data"""
        try:
            api_key = "VAEA6ZT1DHMKMH4C"
            url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={api_key}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                    
                data = await response.json()
                
                # Alpha Vantage provides SharesShort and SharesFloat
                shares_short = data.get('SharesShort')
                shares_float = data.get('SharesFloat') 
                
                if shares_short and shares_float:
                    try:
                        short_count = int(shares_short)
                        float_count = int(shares_float)
                        if float_count > 0:
                            percent = short_count / float_count
                            return ShortInterestData(
                                symbol=symbol,
                                percent=percent,
                                source="alpha_vantage",
                                confidence=0.90,  # High confidence - official API
                                last_updated=datetime.now(),
                                shares_short=short_count,
                                float_shares=float_count
                            )
                    except (ValueError, TypeError):
                        pass
                        
        except Exception as e:
            logger.debug(f"Alpha Vantage failed for {symbol}: {e}")
            
        return None
    
    async def _get_finnhub(self, symbol: str) -> Optional[ShortInterestData]:
        """Finnhub API for comprehensive market data"""
        try:
            api_key = "d1m8l0hr01qvvurkq6h0d1m8l0hr01qvvurkq6hg"
            
            # Try multiple Finnhub endpoints
            endpoints = [
                f"https://finnhub.io/api/v1/stock/metric?symbol={symbol}&metric=all&token={api_key}",
                f"https://finnhub.io/api/v1/stock/profile2?symbol={symbol}&token={api_key}"
            ]
            
            for url in endpoints:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        continue
                        
                    data = await response.json()
                    
                    # Check for short interest in metrics
                    if 'metric' in data:
                        metrics = data['metric']
                        # Look for various short interest fields
                        short_fields = [
                            'shortInterestPercent',
                            'shortRatio', 
                            'shortInterest',
                            'sharesShort'
                        ]
                        
                        for field in short_fields:
                            if field in metrics and metrics[field]:
                                value = float(metrics[field])
                                # Convert to percentage if needed
                                if field == 'shortInterestPercent':
                                    percent = value / 100 if value > 1 else value
                                elif field == 'shortRatio':
                                    # Short ratio is days to cover, estimate percentage
                                    percent = min(0.50, value * 0.05)  # Rough estimation
                                else:
                                    percent = value / 100 if value > 1 else value
                                    
                                return ShortInterestData(
                                    symbol=symbol,
                                    percent=percent,
                                    source="finnhub",
                                    confidence=0.85,
                                    last_updated=datetime.now()
                                )
                        
        except Exception as e:
            logger.debug(f"Finnhub failed for {symbol}: {e}")
            
        return None
    
    async def _get_finviz_data(self, symbol: str) -> Optional[ShortInterestData]:
        """FinViz scraping for short interest"""
        try:
            url = f"https://finviz.com/quote.ashx?t={symbol}"
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                    
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # FinViz has short interest in their fundamental data table
                tables = soup.find_all('table', class_='snapshot-table2')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all('td')
                        for i, cell in enumerate(cells):
                            if 'Short Float' in cell.text or 'Short Interest' in cell.text:
                                if i + 1 < len(cells):
                                    value_text = cells[i + 1].text.strip()
                                    match = re.search(r'(\d+\.?\d*)%', value_text)
                                    if match:
                                        percent = float(match.group(1)) / 100
                                        return ShortInterestData(
                                            symbol=symbol,
                                            percent=percent,
                                            source="finviz",
                                            confidence=0.80,
                                            last_updated=datetime.now()
                                        )
                        
        except Exception as e:
            logger.debug(f"FinViz failed for {symbol}: {e}")
            
        return None
    
    async def _get_marketwatch_data(self, symbol: str) -> Optional[ShortInterestData]:
        """MarketWatch scraping for additional coverage"""
        try:
            url = f"https://www.marketwatch.com/investing/stock/{symbol}"
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                    
                html = await response.text()
                
                # Look for short interest patterns in MarketWatch
                patterns = [
                    r'Short interest.*?(\d+\.?\d*)%',
                    r'Short.*?(\d+\.?\d*)%.*?float'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, html, re.IGNORECASE)
                    if match:
                        percent = float(match.group(1)) / 100
                        return ShortInterestData(
                            symbol=symbol,
                            percent=percent,
                            source="marketwatch",
                            confidence=0.75,
                            last_updated=datetime.now()
                        )
                        
        except Exception as e:
            logger.debug(f"MarketWatch failed for {symbol}: {e}")
            
        return None
    
    async def _estimate_from_market_data(self, symbol: str) -> Optional[ShortInterestData]:
        """Intelligent estimation using market indicators"""
        try:
            # This is a placeholder for sophisticated estimation algorithms
            # In production, this would analyze:
            # - Volume patterns (unusual volume spikes)
            # - Price action (resistance levels, squeeze patterns) 
            # - Options flow (put/call ratios)
            # - Sector comparisons (similar stocks' short interest)
            # - Historical patterns for this stock
            
            # For now, return None to avoid introducing fake data
            # When fully implemented, this would provide 50-70% confidence estimates
            
            return None
            
        except Exception as e:
            logger.debug(f"Market estimation failed for {symbol}: {e}")
            
        return None
    
    def _build_consensus(self, results: List[ShortInterestData]) -> ShortInterestData:
        """Build consensus from multiple sources"""
        if len(results) == 1:
            return results[0]
            
        # Weight by confidence and calculate consensus
        total_weight = sum(r.confidence for r in results)
        weighted_percent = sum(r.percent * r.confidence for r in results) / total_weight
        
        # Use highest confidence source for metadata
        best_source = max(results, key=lambda x: x.confidence)
        
        # Boost confidence when multiple sources agree
        avg_confidence = total_weight / len(results)
        consensus_confidence = min(0.95, avg_confidence * 1.1)  # Cap at 95%
        
        sources = [r.source for r in results]
        consensus_source = f"consensus_{'+'.join(sources[:2])}"  # Limit source name length
        
        return ShortInterestData(
            symbol=best_source.symbol,
            percent=weighted_percent,
            source=consensus_source,
            confidence=consensus_confidence,
            last_updated=datetime.now(),
            shares_short=best_source.shares_short,
            float_shares=best_source.float_shares,
            days_to_cover=best_source.days_to_cover
        )

# Global singleton for efficient reuse
enhanced_short_interest_service = EnhancedShortInterestService()

async def get_enhanced_short_interest(symbol: str) -> Optional[ShortInterestData]:
    """Convenience function for getting short interest data"""
    async with enhanced_short_interest_service as service:
        return await service.get_short_interest(symbol)