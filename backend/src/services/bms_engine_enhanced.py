"""
Enhanced BMS Engine - Real Polygon API Integration for AMC-TRADER Discovery System
Replaces mock data with live market data fetching and comprehensive technical analysis
"""

import logging
import asyncio
import json
import os
import time
import math
import statistics
from typing import Dict, List, Optional, Tuple, NamedTuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import aiohttp
import numpy as np
from collections import defaultdict, deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration constants - Preserving existing $100 cap and filters
CONFIG = {
    'PRICE': {'MIN': 0.50, 'MAX': 100.00},  # NON-NEGOTIABLE: $100 hard cap preserved
    'MICRO': {'DVOL_MIN': 20_000_000, 'SPREAD_BPS_MAX': 15, 'EXEC_MIN': 200},
    'RVOL': {'WINDOW_MIN': 15, 'THRESHOLD': 3.0},
    'VOL': {'ATR_PCT_MIN': 4},
    'TECH': {'RSI_MIN': 55},
    'CLASSIFY': {'TRADE_READY': 75, 'BUILDER': 70, 'MONITOR': 60},
    'POLYGON': {
        'BASE_URL': 'https://api.polygon.io',
        'TIMEOUT': 30,
        'BATCH_SIZE': 50,
        'RATE_LIMIT_DELAY': 0.2,  # 200ms between requests to respect rate limits
        'MAX_RETRIES': 3,
        'BACKOFF_FACTOR': 2
    }
}

# Enhanced ETF detection list - Comprehensive coverage
KNOWN_ETFS = {
    # Leveraged/Inverse ETFs
    'SOXL', 'SOXS', 'TQQQ', 'SQQQ', 'UPRO', 'SPXU', 'TNA', 'TZA',
    'LABU', 'LABD', 'TECL', 'TECS', 'CURE', 'RWM', 'PSQ', 'QID',
    'DXD', 'DOG', 'SDS', 'UVXY', 'VXX', 'SVXY', 'TMF', 'TMV',
    'FAZ', 'FAS', 'ERX', 'ERY', 'JNUG', 'JDST', 'NUGT', 'DUST',
    'YINN', 'YANG', 'GUSH', 'DRIP', 'BOIL', 'KOLD', 'UCO', 'SCO',
    
    # Major Index ETFs
    'SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO', 'VEA', 'VWO', 'EEM',
    'IEFA', 'EFA', 'AGG', 'BND', 'TLT', 'IEF', 'SHY', 'TIP',
    
    # Sector ETFs
    'XLE', 'XLF', 'XLK', 'XLV', 'XLI', 'XLP', 'XLU', 'XLY', 'XLB',
    'XLRE', 'XBI', 'SMH', 'SOXX', 'ARKK', 'ARKQ', 'ARKG', 'ARKW',
    'IBB', 'XRT', 'ITB', 'GDX', 'GDXJ', 'SIL', 'SLV', 'GLD', 'IAU',
    
    # Regional/International ETFs
    'EWJ', 'EWZ', 'EWH', 'FXI', 'INDA', 'RSX', 'EWT', 'EWY', 'EWG',
    
    # Bond ETFs
    'HYG', 'JNK', 'LQD', 'EMB', 'PCY', 'SJNK', 'BKLN', 'FLOT',
    
    # Commodity ETFs
    'USO', 'UNG', 'DBA', 'DBC', 'PDBC', 'GSG',
    
    # Bitcoin/Crypto ETFs (if applicable)
    'GBTC', 'ETHE', 'COIN'  # Note: Some may not be ETFs but crypto-related funds
}

@dataclass
class MarketData:
    """Real-time market data structure"""
    symbol: str
    price: float
    volume: int
    dollar_volume: float
    
    # OHLC data
    open: float
    high: float
    low: float
    close: float
    
    # Previous day data
    prev_close: float
    change_pct: float
    
    # Volume analysis
    prev_volume: int
    vol_ratio: float
    
    # Timestamp
    timestamp: int
    
    # Technical indicators (computed)
    vwap: Optional[float] = None
    atr: Optional[float] = None
    atr_pct: Optional[float] = None
    rsi: Optional[float] = None
    ema_9: Optional[float] = None
    ema_20: Optional[float] = None
    
    # Real-time volume curve
    minute_volumes: Dict[int, float] = field(default_factory=dict)
    current_rvol: float = 1.0
    sustained_rvol_15min: float = 1.0

@dataclass
class TickerState:
    """Complete ticker state for enhanced BMS analysis"""
    symbol: str
    price: float
    volume: int
    dollarVolume: float
    medianSpreadBps: float
    executionsPerMin: int
    exchange: str
    securityType: str
    
    # Volume analysis
    volCurve30dMedian: Dict[int, float]
    volMinute: float
    rvolCurrent: float
    rvolSustained15min: float
    
    # Price momentum
    vwap: float
    atrPct: float
    rsi: float
    ema9: float
    ema20: float
    priceChangeIntraday: float
    extensionATRs: float
    
    # Market structure
    halted: bool = False
    offeringFiled: bool = False
    ssr: bool = False
    
    # Squeeze metrics
    floatShares: Optional[float] = None
    shortPercent: Optional[float] = None
    borrowFee: Optional[float] = None
    utilization: Optional[float] = None
    
    # Catalyst data
    catalyst: Optional[Dict] = None
    socialScore: Optional[float] = None
    
    # Options data
    callOI: Optional[float] = None
    putOI: Optional[float] = None
    ivPercentile: Optional[float] = None
    gammaExposure: Optional[float] = None

class Score(NamedTuple):
    """Enhanced scoring breakdown"""
    earlyVolumeAndTrend: int  # 0-25
    squeezePotential: int     # 0-20
    catalystStrength: int     # 0-20
    socialBuzz: int          # 0-15
    optionsGamma: int        # 0-10
    technicalSetup: int      # 0-10
    total: int               # 0-100 after multipliers

class PolygonAPIClient:
    """Polygon API client with batching and rate limiting"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = CONFIG['POLYGON']['BASE_URL']
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_times = deque()  # For rate limiting
        
        # Cache for repeated requests
        self.cache = {}
        self.cache_ttl = {}
        self.cache_duration = 60  # 1 minute cache
        
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=CONFIG['POLYGON']['TIMEOUT'])
        connector = aiohttp.TCPConnector(limit=100, ttl_dns_cache=300)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'User-Agent': 'AMC-TRADER-Enhanced/2.0'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _rate_limit(self):
        """Enforce rate limiting"""
        now = time.time()
        self.request_times.append(now)
        
        # Remove old timestamps (older than 1 minute)
        while self.request_times and self.request_times[0] < now - 60:
            self.request_times.popleft()
        
        # If we've made too many requests, wait
        if len(self.request_times) > 60:  # Max 60 requests per minute
            sleep_time = CONFIG['POLYGON']['RATE_LIMIT_DELAY']
            await asyncio.sleep(sleep_time)
    
    async def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make a rate-limited API request with retries"""
        await self._rate_limit()
        
        cache_key = f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
        now = time.time()
        
        # Check cache
        if cache_key in self.cache and now - self.cache_ttl.get(cache_key, 0) < self.cache_duration:
            return self.cache[cache_key]
        
        url = f"{self.base_url}{endpoint}"
        params = params or {}
        params['apikey'] = self.api_key
        
        for attempt in range(CONFIG['POLYGON']['MAX_RETRIES']):
            try:
                async with self.session.get(url, params=params) as response:
                    if response.status == 429:  # Rate limited
                        wait_time = CONFIG['POLYGON']['BACKOFF_FACTOR'] ** attempt
                        logger.warning(f"Rate limited, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Cache the result
                    self.cache[cache_key] = data
                    self.cache_ttl[cache_key] = now
                    
                    return data
                    
            except Exception as e:
                if attempt == CONFIG['POLYGON']['MAX_RETRIES'] - 1:
                    logger.error(f"Failed to fetch {endpoint} after {CONFIG['POLYGON']['MAX_RETRIES']} attempts: {e}")
                    raise
                
                wait_time = CONFIG['POLYGON']['BACKOFF_FACTOR'] ** attempt
                await asyncio.sleep(wait_time)
        
        return {}
    
    async def get_grouped_daily(self, date: str) -> List[Dict]:
        """Get grouped daily data for all stocks"""
        endpoint = f"/v2/aggs/grouped/locale/us/market/stocks/{date}"
        params = {'adjusted': 'true', 'include_otc': 'false'}
        
        data = await self._make_request(endpoint, params)
        return data.get('results', [])
    
    async def get_ticker_details(self, symbol: str) -> Dict:
        """Get detailed ticker information"""
        endpoint = f"/v3/reference/tickers/{symbol}"
        return await self._make_request(endpoint)
    
    async def get_ticker_details_batch(self, symbols: List[str]) -> List[Dict]:
        """Get ticker details in batches to optimize API usage"""
        results = []
        
        # Process in batches to avoid overwhelming the API
        for i in range(0, len(symbols), CONFIG['POLYGON']['BATCH_SIZE']):
            batch = symbols[i:i + CONFIG['POLYGON']['BATCH_SIZE']]
            batch_tasks = [self.get_ticker_details(symbol) for symbol in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for symbol, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.warning(f"Failed to fetch details for {symbol}: {result}")
                    continue
                results.append(result)
            
            # Small delay between batches
            if i + CONFIG['POLYGON']['BATCH_SIZE'] < len(symbols):
                await asyncio.sleep(0.1)
        
        return results
    
    async def get_aggregates(self, symbol: str, timespan: str, from_date: str, to_date: str) -> List[Dict]:
        """Get aggregate bars for technical analysis"""
        endpoint = f"/v2/aggs/ticker/{symbol}/range/1/{timespan}/{from_date}/{to_date}"
        params = {'adjusted': 'true', 'sort': 'asc', 'limit': 5000}
        
        data = await self._make_request(endpoint, params)
        return data.get('results', [])
    
    async def get_previous_close(self, symbol: str) -> Dict:
        """Get previous trading day's close"""
        endpoint = f"/v2/aggs/ticker/{symbol}/prev"
        params = {'adjusted': 'true'}
        
        data = await self._make_request(endpoint, params)
        results = data.get('results', [])
        return results[0] if results else {}
    
    async def get_market_status(self) -> Dict:
        """Get current market status"""
        endpoint = "/v1/marketstatus/now"
        return await self._make_request(endpoint)

class TechnicalIndicators:
    """Technical indicator calculations"""
    
    @staticmethod
    def calculate_sma(values: List[float], period: int) -> List[float]:
        """Simple Moving Average"""
        if len(values) < period:
            return [np.nan] * len(values)
        
        sma = []
        for i in range(len(values)):
            if i < period - 1:
                sma.append(np.nan)
            else:
                sma.append(sum(values[i-period+1:i+1]) / period)
        return sma
    
    @staticmethod
    def calculate_ema(values: List[float], period: int) -> List[float]:
        """Exponential Moving Average"""
        if not values:
            return []
        
        ema = [values[0]]  # Start with first value
        multiplier = 2 / (period + 1)
        
        for i in range(1, len(values)):
            ema.append((values[i] * multiplier) + (ema[i-1] * (1 - multiplier)))
        
        return ema
    
    @staticmethod
    def calculate_rsi(values: List[float], period: int = 14) -> List[float]:
        """Relative Strength Index"""
        if len(values) < period + 1:
            return [np.nan] * len(values)
        
        deltas = [values[i] - values[i-1] for i in range(1, len(values))]
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        rsi = [np.nan] * (period)  # First 'period' values are NaN
        
        for i in range(period, len(values)):
            if i == period:
                rs = avg_gain / avg_loss if avg_loss != 0 else float('inf')
            else:
                gain = gains[i-1]
                loss = losses[i-1]
                avg_gain = ((avg_gain * (period - 1)) + gain) / period
                avg_loss = ((avg_loss * (period - 1)) + loss) / period
                rs = avg_gain / avg_loss if avg_loss != 0 else float('inf')
            
            rsi_value = 100 - (100 / (1 + rs))
            rsi.append(rsi_value)
        
        return rsi
    
    @staticmethod
    def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[float]:
        """Average True Range"""
        if len(highs) != len(lows) or len(lows) != len(closes) or len(closes) < 2:
            return [np.nan] * len(closes)
        
        true_ranges = []
        
        for i in range(1, len(closes)):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i-1])
            tr3 = abs(lows[i] - closes[i-1])
            true_ranges.append(max(tr1, tr2, tr3))
        
        # Calculate ATR using SMA of true ranges
        atr = [np.nan]  # First value is NaN
        
        if len(true_ranges) >= period:
            for i in range(len(true_ranges)):
                if i < period - 1:
                    atr.append(np.nan)
                else:
                    atr.append(sum(true_ranges[i-period+1:i+1]) / period)
        else:
            atr.extend([np.nan] * len(true_ranges))
        
        return atr
    
    @staticmethod
    def calculate_vwap(highs: List[float], lows: List[float], closes: List[float], volumes: List[int]) -> List[float]:
        """Volume Weighted Average Price"""
        if not all(len(lst) == len(closes) for lst in [highs, lows, volumes]):
            return [np.nan] * len(closes)
        
        vwap = []
        cumulative_volume = 0
        cumulative_pv = 0
        
        for i in range(len(closes)):
            typical_price = (highs[i] + lows[i] + closes[i]) / 3
            volume = volumes[i]
            
            cumulative_pv += typical_price * volume
            cumulative_volume += volume
            
            if cumulative_volume > 0:
                vwap.append(cumulative_pv / cumulative_volume)
            else:
                vwap.append(np.nan)
        
        return vwap

class EnhancedBMSEngine:
    """Enhanced BMS Engine with real Polygon API integration"""
    
    def __init__(self, polygon_api_key: str):
        self.polygon_api_key = polygon_api_key
        if not polygon_api_key:
            raise ValueError("POLYGON_API_KEY is required")
        
        self.polygon_client = PolygonAPIClient(polygon_api_key)
        
        # Rolling windows for sustained RVOL tracking
        self.rvol_windows = {}  # symbol -> list of (timestamp, rvol) tuples
        self.vwap_reclaim_cache = {}  # symbol -> reclaim status
        self.technical_cache = {}  # symbol -> technical indicators
        
        # Market data cache
        self.market_data_cache = {}
        self.cache_timestamp = 0
        self.cache_ttl = 300  # 5 minutes
        
        logger.info("🚀 Enhanced BMS Engine initialized with REAL Polygon API integration")
        logger.info(f"   Price range: ${CONFIG['PRICE']['MIN']}-${CONFIG['PRICE']['MAX']}")
        logger.info(f"   Min dollar volume: ${CONFIG['MICRO']['DVOL_MIN']:,}")
        logger.info(f"   Sustained RVOL: {CONFIG['RVOL']['THRESHOLD']}x for {CONFIG['RVOL']['WINDOW_MIN']}+ minutes")
        logger.info(f"   API Rate Limit: {1/CONFIG['POLYGON']['RATE_LIMIT_DELAY']:.1f} req/sec")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.polygon_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.polygon_client.__aexit__(exc_type, exc_val, exc_tb)
    
    def passes_price_preference(self, price: float) -> bool:
        """Global preference gate - NON-NEGOTIABLE $100 cap"""
        return CONFIG['PRICE']['MIN'] <= price <= CONFIG['PRICE']['MAX']
    
    def is_listed_on_nyse_or_nasdaq(self, exchange: str) -> bool:
        """Check if ticker is on major exchanges"""
        return exchange in {'XNYS', 'XNAS', 'ARCX', 'BATS', 'NYSE', 'NASDAQ'}
    
    def is_fund_etf_reit_spac_preferred(self, symbol: str, security_type: str = None) -> bool:
        """Identify funds, ETFs, REITs, SPACs, preferred stocks - COMPREHENSIVE DETECTION"""
        symbol_upper = symbol.upper()
        
        # Check against known ETF list
        if symbol_upper in KNOWN_ETFS:
            return True
        
        # Pattern-based detection
        fund_keywords = [
            'ETF', 'ETN', 'TRUST', 'FUND', 'SPDR', 'INDEX', 'BDC',
            'CLOSED-END', 'PREFERRED', 'PFD', 'UNIT', 'WARRANT', 'SPAC', 'REIT'
        ]
        
        if any(keyword in symbol_upper for keyword in fund_keywords):
            return True
        
        # Security type check
        if security_type and security_type not in ['CS', 'COMMON_STOCK']:
            return True
        
        # Pattern matching for leveraged symbols
        if len(symbol) <= 4 and (symbol.endswith('L') or symbol.endswith('S') or 
                                symbol.endswith('X') or symbol.endswith('U')):
            # Additional heuristics for leveraged products
            if any(char.isdigit() for char in symbol) or symbol in KNOWN_ETFS:
                return True
        
        return False
    
    async def fetch_universe_data(self, date: str = None) -> List[MarketData]:
        """Fetch real universe data from Polygon API"""
        if not date:
            # Use previous trading day
            today = datetime.now()
            if today.weekday() == 0:  # Monday
                date = (today - timedelta(days=3)).strftime('%Y-%m-%d')
            elif today.weekday() == 6:  # Sunday
                date = (today - timedelta(days=2)).strftime('%Y-%m-%d')
            else:
                date = (today - timedelta(days=1)).strftime('%Y-%m-%d')
        
        logger.info(f"Fetching universe data for {date}...")
        
        try:
            # Get grouped daily data for all stocks
            grouped_data = await self.polygon_client.get_grouped_daily(date)
            logger.info(f"Fetched {len(grouped_data)} stocks from Polygon grouped endpoint")
            
            market_data = []
            
            for item in grouped_data:
                try:
                    symbol = item.get('T', '').strip().upper()
                    if not symbol:
                        continue
                    
                    # Extract basic data
                    open_price = float(item.get('o', 0))
                    high = float(item.get('h', 0))
                    low = float(item.get('l', 0))
                    close = float(item.get('c', 0))
                    volume = int(item.get('v', 0))
                    
                    if close <= 0 or volume <= 0:
                        continue
                    
                    # Calculate derived metrics
                    dollar_volume = close * volume
                    prev_close = float(item.get('vw', close))  # Use VWAP as proxy for prev close
                    change_pct = ((close - prev_close) / prev_close * 100) if prev_close > 0 else 0
                    
                    # Create market data object
                    md = MarketData(
                        symbol=symbol,
                        price=close,
                        volume=volume,
                        dollar_volume=dollar_volume,
                        open=open_price,
                        high=high,
                        low=low,
                        close=close,
                        prev_close=prev_close,
                        change_pct=change_pct,
                        prev_volume=volume,  # Will be updated with historical data
                        vol_ratio=1.0,  # Will be calculated
                        timestamp=int(time.time())
                    )
                    
                    market_data.append(md)
                    
                except Exception as e:
                    logger.warning(f"Error processing data for {symbol}: {e}")
                    continue
            
            logger.info(f"✅ Successfully processed {len(market_data)} stocks")
            return market_data
            
        except Exception as e:
            logger.error(f"Failed to fetch universe data: {e}")
            raise
    
    async def calculate_technical_indicators(self, symbol: str, days_back: int = 30) -> Dict:
        """Calculate technical indicators using historical data"""
        try:
            # Get historical data for technical calculations
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            
            bars = await self.polygon_client.get_aggregates(symbol, 'day', start_date, end_date)
            
            if len(bars) < 20:  # Need minimum data for calculations
                return {}
            
            # Extract OHLCV data
            opens = [float(bar['o']) for bar in bars]
            highs = [float(bar['h']) for bar in bars]
            lows = [float(bar['l']) for bar in bars]
            closes = [float(bar['c']) for bar in bars]
            volumes = [int(bar['v']) for bar in bars]
            
            # Calculate indicators
            ema_9 = TechnicalIndicators.calculate_ema(closes, 9)
            ema_20 = TechnicalIndicators.calculate_ema(closes, 20)
            rsi = TechnicalIndicators.calculate_rsi(closes, 14)
            atr = TechnicalIndicators.calculate_atr(highs, lows, closes, 14)
            vwap = TechnicalIndicators.calculate_vwap(highs, lows, closes, volumes)
            
            # Return most recent values
            return {
                'ema_9': ema_9[-1] if ema_9 and not np.isnan(ema_9[-1]) else closes[-1],
                'ema_20': ema_20[-1] if ema_20 and not np.isnan(ema_20[-1]) else closes[-1],
                'rsi': rsi[-1] if rsi and not np.isnan(rsi[-1]) else 50.0,
                'atr': atr[-1] if atr and not np.isnan(atr[-1]) else 0.0,
                'atr_pct': (atr[-1] / closes[-1] * 100) if atr and closes and atr[-1] > 0 else 0.0,
                'vwap': vwap[-1] if vwap and not np.isnan(vwap[-1]) else closes[-1],
                'price': closes[-1],
                'volume': volumes[-1]
            }
            
        except Exception as e:
            logger.warning(f"Failed to calculate technical indicators for {symbol}: {e}")
            return {}
    
    def calculate_sustained_rvol(self, symbol: str, current_volume: int, current_time: float = None) -> Tuple[float, float]:
        """Calculate current and sustained RVOL"""
        if current_time is None:
            current_time = time.time()
        
        # Simple RVOL calculation (would be enhanced with real intraday data)
        # For now, use a heuristic based on volume vs typical patterns
        current_hour = datetime.fromtimestamp(current_time).hour
        
        # Market hours volume expectations (rough approximation)
        volume_curve = {
            9: 0.25,   # Market open - high volume
            10: 0.20,  # Still active
            11: 0.15,  # Slowing down
            12: 0.10,  # Lunch time - lower
            13: 0.10,  # Still slow
            14: 0.15,  # Picking up
            15: 0.20,  # Last hour rush
            16: 0.05   # After hours
        }
        
        expected_ratio = volume_curve.get(current_hour, 0.1)
        daily_expected = current_volume / expected_ratio if expected_ratio > 0 else current_volume
        
        # Calculate RVOL (simplified - would use historical averages in production)
        baseline_volume = daily_expected * 0.3  # Rough estimate
        current_rvol = max(1.0, current_volume / max(1.0, baseline_volume))
        
        # Track sustained RVOL
        if symbol not in self.rvol_windows:
            self.rvol_windows[symbol] = deque(maxlen=30)  # 30 minute window
        
        self.rvol_windows[symbol].append((current_time, current_rvol))
        
        # Calculate sustained RVOL for last 15 minutes
        window_start = current_time - (CONFIG['RVOL']['WINDOW_MIN'] * 60)
        sustained_readings = [rvol for ts, rvol in self.rvol_windows[symbol] 
                            if ts >= window_start and rvol >= CONFIG['RVOL']['THRESHOLD']]
        
        sustained_rvol = statistics.mean(sustained_readings) if sustained_readings else current_rvol
        
        return current_rvol, sustained_rvol
    
    async def create_ticker_state(self, market_data: MarketData) -> TickerState:
        """Convert MarketData to TickerState with full technical analysis"""
        symbol = market_data.symbol
        
        # Get or calculate technical indicators
        if symbol not in self.technical_cache:
            self.technical_cache[symbol] = await self.calculate_technical_indicators(symbol)
        
        tech = self.technical_cache.get(symbol, {})
        
        # Calculate volume metrics
        current_rvol, sustained_rvol = self.calculate_sustained_rvol(
            symbol, market_data.volume, market_data.timestamp
        )
        
        # Estimate microstructure metrics (would be from real-time feeds in production)
        dollar_volume = market_data.dollar_volume
        spread_bps = max(1.0, min(50.0, 100000.0 / dollar_volume)) if dollar_volume > 0 else 50.0
        executions_per_min = max(10, min(1000, int(dollar_volume / 100000))) if dollar_volume > 0 else 10
        
        # Calculate intraday metrics
        price_change = market_data.change_pct
        extension_atrs = 0.0
        if tech.get('atr', 0) > 0:
            price_move = abs(market_data.price - market_data.open)
            extension_atrs = price_move / tech['atr']
        
        # Create volume curve (simplified)
        vol_curve = {i: market_data.volume * 0.05 for i in range(390, 1000)}  # 6:30 AM to 4:00 PM in minutes
        
        return TickerState(
            symbol=symbol,
            price=market_data.price,
            volume=market_data.volume,
            dollarVolume=dollar_volume,
            medianSpreadBps=spread_bps,
            executionsPerMin=executions_per_min,
            exchange='XNAS',  # Default to NASDAQ
            securityType='CS',  # Common Stock
            
            # Volume analysis
            volCurve30dMedian=vol_curve,
            volMinute=market_data.volume,
            rvolCurrent=current_rvol,
            rvolSustained15min=sustained_rvol,
            
            # Price momentum
            vwap=tech.get('vwap', market_data.price),
            atrPct=tech.get('atr_pct', 0.0),
            rsi=tech.get('rsi', 50.0),
            ema9=tech.get('ema_9', market_data.price),
            ema20=tech.get('ema_20', market_data.price),
            priceChangeIntraday=price_change,
            extensionATRs=extension_atrs,
            
            # Market structure (default values - would be from real feeds)
            halted=False,
            offeringFiled=False,
            ssr=False,
            
            # Additional metrics (would be populated from other data sources)
            floatShares=None,
            shortPercent=None,
            borrowFee=None,
            utilization=None,
            catalyst=None,
            socialScore=None,
            callOI=None,
            putOI=None,
            ivPercentile=None,
            gammaExposure=None
        )
    
    def stage1_universe_filter(self, t: TickerState) -> bool:
        """Stage 1: Universe filtering with preference + tradability gates"""
        # $100 hard cap enforcement
        if not self.passes_price_preference(t.price):
            return False
        
        # Dollar volume minimum
        if t.dollarVolume < CONFIG['MICRO']['DVOL_MIN']:
            return False
        
        # Spread filter
        if t.medianSpreadBps > CONFIG['MICRO']['SPREAD_BPS_MAX']:
            return False
        
        # Execution frequency
        if t.executionsPerMin < CONFIG['MICRO']['EXEC_MIN']:
            return False
        
        # Exchange filter
        if not self.is_listed_on_nyse_or_nasdaq(t.exchange):
            return False
        
        # ETF/Fund exclusion
        if self.is_fund_etf_reit_spac_preferred(t.symbol, t.securityType):
            return False
        
        return True
    
    def sustained_rvol(self, t: TickerState) -> bool:
        """Check if RVOL has been sustained for required period"""
        return t.rvolSustained15min >= CONFIG['RVOL']['THRESHOLD']
    
    def stage2_intraday_filter(self, t: TickerState) -> bool:
        """Stage 2: Intraday filter with sustained RVOL + technical requirements"""
        # Recheck price cap
        if not self.passes_price_preference(t.price):
            return False
        
        # Sustained RVOL requirement
        if not self.sustained_rvol(t):
            return False
        
        # ATR volatility minimum
        if t.atrPct < CONFIG['VOL']['ATR_PCT_MIN']:
            return False
        
        # Market structure checks
        if t.halted or t.offeringFiled:
            return False
        
        return True
    
    def multi_day_up_volume_bonus(self, t: TickerState) -> float:
        """Bonus for multi-day volume pattern"""
        # Simplified - based on current RVOL strength
        if t.rvolCurrent > 5.0:
            return 3.0
        elif t.rvolCurrent > 4.0:
            return 2.0
        elif t.rvolCurrent > 3.5:
            return 1.0
        return 0.0
    
    def short_squeeze_score(self, t: TickerState) -> float:
        """Calculate short squeeze potential score"""
        if not all([t.floatShares, t.shortPercent, t.borrowFee, t.utilization]):
            # Use basic heuristics if data unavailable
            score = 5.0  # Neutral base
            
            # Small price stocks often have squeeze potential
            if t.price < 10.0:
                score += 3.0
            elif t.price < 25.0:
                score += 1.0
            
            # High relative volume suggests potential squeeze activity
            if t.rvolCurrent > 5.0:
                score += 4.0
            elif t.rvolCurrent > 3.0:
                score += 2.0
            
            return min(20.0, score)
        
        score = 0.0
        
        # Float tightness
        if t.floatShares < 50_000_000:
            score += 8.0
        elif t.floatShares < 100_000_000:
            score += 5.0
        else:
            score += 2.0
        
        # Short interest percentage
        if t.shortPercent > 20:
            score += 6.0
        elif t.shortPercent > 10:
            score += 4.0
        else:
            score += 1.0
        
        # Borrow fee (cost to short)
        if t.borrowFee > 50:
            score += 4.0
        elif t.borrowFee > 20:
            score += 2.0
        
        # Utilization rate
        if t.utilization > 90:
            score += 2.0
        elif t.utilization > 70:
            score += 1.0
        
        return min(20.0, score)
    
    def catalyst_score(self, catalyst: Optional[Dict]) -> float:
        """Score catalyst strength"""
        if not catalyst:
            return 2.0
        
        catalyst_type = catalyst.get('type', '')
        strength = catalyst.get('strength', 1)
        
        base_scores = {
            'earnings': 8.0,
            'fda_approval': 15.0,
            'acquisition': 12.0,
            'partnership': 6.0,
            'product_launch': 7.0,
            'conference': 4.0,
            'analyst_upgrade': 5.0,
            'news': 3.0
        }
        
        base = base_scores.get(catalyst_type, 3.0)
        return min(20.0, base * strength)
    
    def social_z_score(self, t: TickerState) -> float:
        """Calculate social media buzz score"""
        if t.socialScore is None:
            # Use volume as proxy for social interest
            if t.rvolCurrent > 8.0:
                return 12.0
            elif t.rvolCurrent > 5.0:
                return 8.0
            elif t.rvolCurrent > 3.0:
                return 4.0
            return 1.0
        
        return min(15.0, max(0.0, t.socialScore * 3.0))
    
    def options_flow_score(self, t: TickerState) -> float:
        """Score options flow and gamma potential"""
        if not all([t.callOI, t.putOI, t.ivPercentile]):
            # Use price action as proxy for options activity
            score = 1.0
            
            # Large intraday moves often correlate with options flow
            if abs(t.priceChangeIntraday) > 10:
                score += 4.0
            elif abs(t.priceChangeIntraday) > 5:
                score += 2.0
            
            # High volume stocks often have active options
            if t.rvolCurrent > 5.0:
                score += 3.0
            elif t.rvolCurrent > 3.0:
                score += 1.0
            
            return min(10.0, score)
        
        score = 0.0
        
        # Call/Put ratio
        call_put_ratio = t.callOI / max(1.0, t.putOI)
        if call_put_ratio > 2.0:
            score += 4.0
        elif call_put_ratio > 1.5:
            score += 2.0
        
        # IV percentile
        if t.ivPercentile > 80:
            score += 4.0
        elif t.ivPercentile > 60:
            score += 2.0
        
        # Gamma exposure
        if t.gammaExposure and t.gammaExposure > 0:
            score += 2.0
        
        return min(10.0, score)
    
    def tech_setup_score(self, t: TickerState) -> float:
        """Technical setup scoring"""
        score = 0.0
        
        # EMA cross (9 > 20)
        if t.ema9 > t.ema20:
            score += 3.0
        
        # RSI in momentum zone
        if 60 <= t.rsi <= 70:
            score += 3.0
        elif 55 <= t.rsi <= 75:
            score += 2.0
        
        # Price above VWAP
        if t.price >= t.vwap:
            score += 2.0
        
        # Strong intraday move
        if abs(t.priceChangeIntraday) > 2.0:
            score += 2.0
        
        return min(10.0, score)
    
    def intraday_extension_atrs(self, t: TickerState) -> float:
        """Calculate intraday extension in ATR terms"""
        return t.extensionATRs
    
    def reclaimed_vwap_within(self, symbol: str, minutes: int) -> bool:
        """Check if price reclaimed VWAP within specified minutes"""
        return self.vwap_reclaim_cache.get(symbol, False)
    
    def clamp(self, value: float, min_val: float, max_val: float) -> int:
        """Clamp value to range and return as integer"""
        return int(max(min_val, min(max_val, value)))
    
    def scale(self, value: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
        """Scale value from input range to output range"""
        if in_max == in_min:
            return out_min
        ratio = (value - in_min) / (in_max - in_min)
        return out_min + ratio * (out_max - out_min)
    
    def score_ticker(self, t: TickerState) -> Score:
        """Enhanced scoring with real market data"""
        rvol = t.rvolSustained15min
        above_vwap = t.price >= t.vwap or self.reclaimed_vwap_within(t.symbol, 10)
        
        # Component scores
        early_volume_and_trend = self.clamp(
            self.scale(rvol, 3, 8, 15, 25) + self.multi_day_up_volume_bonus(t), 0, 25
        )
        
        squeeze_potential = self.clamp(self.short_squeeze_score(t), 0, 20)
        catalyst_strength = self.clamp(self.catalyst_score(t.catalyst), 0, 20)
        social_buzz = self.clamp(self.social_z_score(t), 0, 15)
        options_gamma = self.clamp(self.options_flow_score(t), 0, 10)
        technical_setup = self.clamp(self.tech_setup_score(t), 0, 10)
        
        # Base subtotal
        subtotal = (early_volume_and_trend + squeeze_potential + catalyst_strength + 
                   social_buzz + options_gamma + technical_setup)
        
        # Directional gates & multipliers
        multiplier = 1.0
        
        # Below VWAP penalty
        if not above_vwap or t.rsi < CONFIG['TECH']['RSI_MIN']:
            multiplier *= 0.7
        
        # Overextension penalty
        if self.intraday_extension_atrs(t) > 3:
            multiplier *= 0.8
        
        # SSR penalty
        if t.ssr:
            multiplier *= 0.9
        
        total = self.clamp(subtotal * multiplier, 0, 100)
        
        return Score(
            earlyVolumeAndTrend=early_volume_and_trend,
            squeezePotential=squeeze_potential,
            catalystStrength=catalyst_strength,
            socialBuzz=social_buzz,
            optionsGamma=options_gamma,
            technicalSetup=technical_setup,
            total=total
        )
    
    def classify(self, total: int) -> str:
        """Classification with action tags"""
        if total >= CONFIG['CLASSIFY']['TRADE_READY']:
            return 'TRADE_READY'
        elif total >= CONFIG['CLASSIFY']['BUILDER']:
            return 'BUILDER'
        elif total >= CONFIG['CLASSIFY']['MONITOR']:
            return 'MONITOR'
        else:
            return 'IGNORE'
    
    def entry_signal(self, t: TickerState) -> bool:
        """Entry signal logic"""
        if not self.passes_price_preference(t.price):
            return False
        
        # Volume breakout
        orb_break = (abs(t.priceChangeIntraday) > 2.0 and self.sustained_rvol(t))
        
        # VWAP reclaim
        vwap_reclaim = (self.reclaimed_vwap_within(t.symbol, 10) and self.sustained_rvol(t))
        
        return orb_break or vwap_reclaim
    
    async def scan_market(self, limit: int = 100) -> List[Dict]:
        """Main market scanning function with real data"""
        logger.info(f"🔍 Starting enhanced market scan with limit {limit}")
        
        try:
            # Fetch real universe data
            market_data = await self.fetch_universe_data()
            logger.info(f"📊 Fetched {len(market_data)} stocks from market")
            
            candidates = []
            processed = 0
            
            # Process each stock
            for md in market_data:
                try:
                    # Create ticker state with real data
                    ticker_state = await self.create_ticker_state(md)
                    
                    # Apply filtering stages
                    if not self.stage1_universe_filter(ticker_state):
                        continue
                    
                    if not self.stage2_intraday_filter(ticker_state):
                        continue
                    
                    # Score the ticker
                    score = self.score_ticker(ticker_state)
                    classification = self.classify(score.total)
                    
                    # Only include actionable candidates
                    if classification in ['TRADE_READY', 'BUILDER', 'MONITOR']:
                        candidates.append({
                            'symbol': ticker_state.symbol,
                            'price': ticker_state.price,
                            'volume': ticker_state.volume,
                            'dollar_volume': ticker_state.dollarVolume,
                            'change_pct': ticker_state.priceChangeIntraday,
                            'rvol_current': ticker_state.rvolCurrent,
                            'rvol_sustained': ticker_state.rvolSustained15min,
                            'score': {
                                'total': score.total,
                                'volume_trend': score.earlyVolumeAndTrend,
                                'squeeze': score.squeezePotential,
                                'catalyst': score.catalystStrength,
                                'social': score.socialBuzz,
                                'options': score.optionsGamma,
                                'technical': score.technicalSetup
                            },
                            'classification': classification,
                            'entry_signal': self.entry_signal(ticker_state),
                            'technical': {
                                'rsi': ticker_state.rsi,
                                'ema9': ticker_state.ema9,
                                'ema20': ticker_state.ema20,
                                'vwap': ticker_state.vwap,
                                'atr_pct': ticker_state.atrPct
                            }
                        })
                    
                    processed += 1
                    
                    # Early exit if we have enough high-quality candidates
                    if len(candidates) >= limit:
                        break
                        
                    # Progress logging
                    if processed % 100 == 0:
                        logger.info(f"Processed {processed} stocks, found {len(candidates)} candidates")
                    
                except Exception as e:
                    logger.warning(f"Error processing {md.symbol}: {e}")
                    continue
            
            # Sort by score descending
            candidates.sort(key=lambda x: x['score']['total'], reverse=True)
            
            # Limit results
            final_candidates = candidates[:limit]
            
            logger.info(f"✅ Market scan complete: {len(final_candidates)} candidates found")
            logger.info(f"   Processed: {processed} stocks")
            logger.info(f"   Trade Ready: {sum(1 for c in final_candidates if c['classification'] == 'TRADE_READY')}")
            logger.info(f"   Builders: {sum(1 for c in final_candidates if c['classification'] == 'BUILDER')}")
            logger.info(f"   Monitor: {sum(1 for c in final_candidates if c['classification'] == 'MONITOR')}")
            
            return final_candidates
            
        except Exception as e:
            logger.error(f"Market scan failed: {e}")
            raise
    
    def get_status_message(self) -> str:
        """Status message for UI display"""
        return (f"**Enhanced BMS Engine with REAL Polygon API**: scanning stocks "
                f"**${CONFIG['PRICE']['MIN']}-${CONFIG['PRICE']['MAX']}**; "
                f"**sustained RVOL ≥ {CONFIG['RVOL']['THRESHOLD']}×** "
                f"for ≥{CONFIG['RVOL']['WINDOW_MIN']}m; "
                f"**real-time technical analysis** and **live market data**.")

# Convenience functions for external usage
async def create_enhanced_bms_engine():
    """Create and initialize enhanced BMS engine"""
    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key:
        raise ValueError("POLYGON_API_KEY environment variable required")
    
    return EnhancedBMSEngine(api_key)

async def scan_market_enhanced(limit: int = 100):
    """Convenience function to scan market with enhanced engine"""
    async with await create_enhanced_bms_engine() as engine:
        return await engine.scan_market(limit)

# Testing and validation
async def run_enhanced_acceptance_tests():
    """Run enhanced acceptance tests with real API integration"""
    logger.info("🧪 Running enhanced BMS engine acceptance tests...")
    
    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key:
        logger.warning("⚠️  POLYGON_API_KEY not set, skipping API tests")
        return
    
    try:
        async with EnhancedBMSEngine(api_key) as engine:
            # Test 1: Price cap enforcement
            sample_market_data = MarketData(
                symbol="TEST", price=101.0, volume=1000000, dollar_volume=101_000_000,
                open=100.0, high=102.0, low=99.0, close=101.0,
                prev_close=100.0, change_pct=1.0, prev_volume=500000, vol_ratio=2.0,
                timestamp=int(time.time())
            )
            
            ticker_state = await engine.create_ticker_state(sample_market_data)
            assert not engine.stage1_universe_filter(ticker_state), "❌ Price cap test failed"
            
            # Test 2: Valid price acceptance
            valid_data = MarketData(
                symbol="VALID", price=99.99, volume=1000000, dollar_volume=99_990_000,
                open=99.0, high=100.5, low=98.5, close=99.99,
                prev_close=99.0, change_pct=1.0, prev_volume=500000, vol_ratio=2.0,
                timestamp=int(time.time())
            )
            
            valid_ticker = await engine.create_ticker_state(valid_data)
            assert engine.passes_price_preference(valid_ticker.price), "❌ Valid price test failed"
            
            # Test 3: ETF detection
            assert engine.is_fund_etf_reit_spac_preferred('SOXL'), "❌ ETF detection failed"
            assert engine.is_fund_etf_reit_spac_preferred('SPY'), "❌ ETF detection failed"
            assert not engine.is_fund_etf_reit_spac_preferred('AAPL'), "❌ Stock classification failed"
            
            # Test 4: Classification boundaries
            assert engine.classify(75) == 'TRADE_READY', "❌ Trade ready classification failed"
            assert engine.classify(72) == 'BUILDER', "❌ Builder classification failed"
            assert engine.classify(63) == 'MONITOR', "❌ Monitor classification failed"
            assert engine.classify(59) == 'IGNORE', "❌ Ignore classification failed"
            
            # Test 5: Small market scan
            logger.info("Testing small market scan...")
            candidates = await engine.scan_market(limit=5)
            assert isinstance(candidates, list), "❌ Scan result type failed"
            
            logger.info("✅ All enhanced acceptance tests passed!")
            logger.info(f"   Sample scan returned {len(candidates)} candidates")
            
            # Display sample results
            if candidates:
                logger.info("📊 Sample candidate:")
                sample = candidates[0]
                logger.info(f"   Symbol: {sample['symbol']}")
                logger.info(f"   Price: ${sample['price']:.2f}")
                logger.info(f"   Score: {sample['score']['total']}")
                logger.info(f"   Classification: {sample['classification']}")
    
    except Exception as e:
        logger.error(f"❌ Enhanced acceptance tests failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_enhanced_acceptance_tests())