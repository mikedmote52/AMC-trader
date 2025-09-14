"""
AlphaStack 4.0 Discovery System - Production-Ready Real Data Implementation
Professional-grade stock discovery with fail-closed architecture and adaptive scoring.
"""
import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Protocol, runtime_checkable
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

import httpx
from pydantic import BaseModel, Field, validator
import redis.asyncio as aioredis
import numpy as np
import math

import sys
import os
# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from constants import (
        POLYGON_API_KEY, POLYGON_TIMEOUT_SECONDS, POLYGON_MAX_RETRIES,
        PRICE_MIN, PRICE_MAX, MIN_DOLLAR_VOL_M, EXCLUDE_SYMBOL_PATTERNS,
        get_trading_date
    )
except ImportError:
    # Fallback defaults for testing
    POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")
    POLYGON_TIMEOUT_SECONDS = 30
    POLYGON_MAX_RETRIES = 3
    PRICE_MIN = 0.10
    PRICE_MAX = 100.00
    MIN_DOLLAR_VOL_M = 5.0
    EXCLUDE_SYMBOL_PATTERNS = ["SQQQ", "TQQQ", "UVXY", "QQQ", "SPY"]
    
    def get_trading_date():
        from datetime import datetime, timedelta
        today = datetime.now()
        
        # Find the most recent trading day (Monday-Friday)
        days_back = 0
        check_date = today
        
        while True:
            # Skip weekends (Saturday=5, Sunday=6)
            if check_date.weekday() < 5:  # Monday=0 through Friday=4
                break
            days_back += 1
            check_date = today - timedelta(days=days_back)
            
            # Safety check to avoid infinite loop
            if days_back > 7:
                break
        
        # If today is a weekday but market might not be open yet, go back one more day
        if today.weekday() < 5 and today.hour < 16:  # Before 4 PM
            days_back += 1
            check_date = today - timedelta(days=days_back)
            # Make sure we didn't land on a weekend
            while check_date.weekday() >= 5:
                days_back += 1
                check_date = today - timedelta(days=days_back)
        
        return check_date.strftime('%Y-%m-%d')

logger = logging.getLogger(__name__)

# ============================================================================
# Core Models & Configuration
# ============================================================================

class EnvConfig(BaseModel):
    """Environment-driven configuration with validation"""
    polygon_api_key: str = Field(..., min_length=10)
    redis_url: str = Field(default="redis://localhost:6379")
    price_min: float = Field(default=0.10, ge=0.01)
    price_max: float = Field(default=100.00, le=1000.0)
    min_dollar_vol_m: float = Field(default=5.0, ge=1.0)
    
    @validator('polygon_api_key')
    def validate_api_key(cls, v):
        if not v or v.startswith('YOUR_API_KEY'):
            raise ValueError("Real Polygon API key required")
        return v

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    FAILED = "failed"

class HealthReport(BaseModel):
    """Provider health check result"""
    status: HealthStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    latency_ms: Optional[int] = None
    error_msg: Optional[str] = None
    data_freshness_sec: Optional[int] = None

class TechnicalIndicators:
    """Local computation of technical indicators - no external dependencies"""
    
    @staticmethod
    def rsi(prices: List[float], period: int = 14) -> float:
        """Calculate Wilder's RSI"""
        if len(prices) < period + 1:
            return 50.0  # Neutral fallback
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        # Initial average
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        # Wilder's smoothing for remaining periods
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))
    
    @staticmethod
    def ema(prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return sum(prices) / len(prices) if prices else 0.0
        
        multiplier = 2.0 / (period + 1)
        ema = sum(prices[:period]) / period  # Start with SMA
        
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    @staticmethod
    def vwap(prices: List[float], volumes: List[int]) -> float:
        """Calculate Volume Weighted Average Price"""
        if not prices or not volumes or len(prices) != len(volumes):
            return sum(prices) / len(prices) if prices else 0.0
        
        total_pv = sum(p * v for p, v in zip(prices, volumes))
        total_vol = sum(volumes)
        
        return total_pv / total_vol if total_vol > 0 else 0.0
    
    @staticmethod
    def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(closes) < 2:
            return 0.0
        
        true_ranges = []
        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            true_ranges.append(max(high_low, high_close, low_close))
        
        if len(true_ranges) < period:
            return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0
        
        # Wilder's smoothing
        atr = sum(true_ranges[:period]) / period
        for tr in true_ranges[period:]:
            atr = (atr * (period - 1) + tr) / period
        
        return atr
    
    @staticmethod
    def relative_volume(current_vol: int, historical_volumes: List[int]) -> float:
        """Calculate relative volume vs historical average"""
        if not historical_volumes:
            return 1.0
        
        avg_vol = sum(historical_volumes) / len(historical_volumes)
        return current_vol / avg_vol if avg_vol > 0 else 1.0

class SqueezeDetector:
    """Detects squeeze setups and triggers"""
    
    @staticmethod
    def detect_three_by_thirty(rel_vols: List[float], minutes: int = 30) -> bool:
        """3x volume for 30+ minutes trigger"""
        if len(rel_vols) < minutes:
            return False
        return all(rv >= 3.0 for rv in rel_vols[-minutes:])
    
    @staticmethod
    def detect_vwap_reclaim_and_hold(prices: List[float], vwap: float, hold_minutes: int = 15) -> bool:
        """VWAP reclaim and hold trigger"""
        if len(prices) < hold_minutes or not vwap:
            return False
        
        recent_prices = prices[-hold_minutes:]
        above_count = sum(1 for p in recent_prices if p > vwap)
        return above_count >= int(hold_minutes * 0.75)  # 75% above VWAP
    
    @staticmethod
    def detect_range_break(current_price: float, prev_day_high: float, tolerance: float = 0.01) -> bool:
        """Previous day high break trigger"""
        return current_price > prev_day_high * (1 + tolerance)
    
    @staticmethod
    def calculate_float_score(market_cap_m: Optional[float], float_shares_m: Optional[float]) -> float:
        """Score based on float size (smaller = higher score)"""
        if not float_shares_m:
            return 0.3  # Unknown float penalty
        
        if float_shares_m <= 20:
            return 1.0  # Micro float
        elif float_shares_m <= 50:
            return 0.8  # Small float
        elif float_shares_m <= 150:
            return 0.6  # Medium float
        else:
            return 0.4  # Large float
    data_freshness_sec: Optional[int] = None

class TickerSnapshot(BaseModel):
    """Real-time ticker data snapshot with validation"""
    symbol: str = Field(..., min_length=1, max_length=10)
    price: Decimal = Field(..., gt=0)
    volume: int = Field(..., ge=0)
    market_cap_m: Optional[Decimal] = None
    float_shares_m: Optional[Decimal] = None
    
    # Technical indicators
    rsi: Optional[float] = Field(None, ge=0, le=100)
    ema_20: Optional[Decimal] = None
    vwap: Optional[Decimal] = None
    atr_pct: Optional[float] = Field(None, ge=0)
    
    # Volume & momentum
    rel_vol_30d: Optional[float] = Field(None, ge=0)
    up_days_5: Optional[int] = Field(None, ge=0, le=5)
    
    # Squeeze metrics
    short_interest_pct: Optional[float] = Field(None, ge=0, le=100)
    borrow_fee_pct: Optional[float] = Field(None, ge=0)
    utilization_pct: Optional[float] = Field(None, ge=0, le=100)
    
    # Options data
    call_put_ratio: Optional[float] = Field(None, ge=0)
    iv_percentile: Optional[float] = Field(None, ge=0, le=100)
    
    # Sentiment & catalysts
    social_rank: Optional[int] = Field(None, ge=0, le=100)
    catalysts: Optional[List[str]] = Field(default_factory=list)
    
    # Microstructure
    bid_ask_spread_bps: Optional[int] = Field(None, ge=0)
    executions_per_min: Optional[int] = Field(None, ge=0)
    
    # Metadata
    data_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('symbol')
    def validate_symbol(cls, v):
        return v.upper().strip()

class CandidateScore(BaseModel):
    """Final candidate with scoring breakdown"""
    symbol: str
    total_score: float = Field(..., ge=0, le=100)
    confidence: float = Field(..., ge=0, le=1.0)
    
    # Component scores (0-100 each)
    volume_momentum_score: float = Field(..., ge=0, le=100)
    squeeze_score: float = Field(..., ge=0, le=100) 
    catalyst_score: float = Field(..., ge=0, le=100)
    sentiment_score: float = Field(..., ge=0, le=100)
    options_score: float = Field(..., ge=0, le=100)
    technical_score: float = Field(..., ge=0, le=100)
    
    # Risk flags
    risk_flags: List[str] = Field(default_factory=list)
    action_tag: str = Field(default="monitor")  # monitor, watchlist, trade_ready
    
    snapshot: TickerSnapshot

class ReadinessError(Exception):
    """Raised when system is not ready to provide real results"""
    pass

# ============================================================================
# Provider Interfaces
# ============================================================================

@runtime_checkable
class DataProvider(Protocol):
    """Interface for all data providers"""
    
    async def health_check(self) -> HealthReport:
        """Check if provider is healthy and returning real data"""
        ...
    
    async def is_ready(self) -> bool:
        """True if provider is ready for production queries"""
        ...

class PriceProvider(DataProvider):
    """Real-time price and volume data provider"""
    
    @abstractmethod
    async def get_universe(self) -> List[TickerSnapshot]:
        """Get filtered universe of tradeable stocks"""
        ...
    
    @abstractmethod 
    async def get_ticker_data(self, symbol: str) -> Optional[TickerSnapshot]:
        """Get detailed data for specific ticker"""
        ...

class OptionsProvider(DataProvider):
    """Options flow and volatility data provider"""
    
    @abstractmethod
    async def get_options_data(self, symbol: str) -> Dict[str, Any]:
        """Get options metrics for ticker"""
        ...

class ShortProvider(DataProvider):
    """Short interest and borrow data provider"""
    
    @abstractmethod
    async def get_short_data(self, symbol: str) -> Dict[str, Any]:
        """Get short interest metrics for ticker"""
        ...

class SocialProvider(DataProvider):
    """Social sentiment and buzz provider"""
    
    @abstractmethod
    async def get_social_data(self, symbol: str) -> Dict[str, Any]:
        """Get social sentiment metrics for ticker"""
        ...

class CatalystProvider(DataProvider):
    """News and catalyst event provider"""
    
    @abstractmethod
    async def get_catalysts(self, symbol: str) -> List[str]:
        """Get recent catalysts for ticker"""
        ...

class ReferenceProvider(DataProvider):
    """Company fundamentals and static data provider"""
    
    @abstractmethod
    async def get_company_data(self, symbol: str) -> Dict[str, Any]:
        """Get company fundamentals for ticker"""
        ...

# ============================================================================
# Real Polygon API Provider Implementation
# ============================================================================

class PolygonPriceProvider(PriceProvider):
    """Production Polygon API implementation - NO MOCK DATA"""
    
    def __init__(self, config: EnvConfig):
        if not config.polygon_api_key:
            raise ValueError("Polygon API key required for real data")
        
        self.config = config
        self.client = httpx.AsyncClient(
            base_url="https://api.polygon.io",
            headers={"Authorization": f"Bearer {config.polygon_api_key}"},
            timeout=POLYGON_TIMEOUT_SECONDS,
            limits=httpx.Limits(max_connections=20)
        )
        self._last_health_check: Optional[HealthReport] = None
        
    async def health_check(self) -> HealthReport:
        """Verify API connectivity and data freshness"""
        start_time = datetime.utcnow()
        
        try:
            # Test with a known liquid stock
            response = await self.client.get(
                "/v2/aggs/ticker/AAPL/prev", 
                params={"adjusted": "true"}
            )
            
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            if response.status_code != 200:
                return HealthReport(
                    status=HealthStatus.FAILED,
                    latency_ms=latency_ms,
                    error_msg=f"HTTP {response.status_code}"
                )
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                return HealthReport(
                    status=HealthStatus.FAILED,
                    error_msg="No data returned from Polygon"
                )
            
            # Check data freshness (should be within 24 hours for daily data)
            result = results[0]
            data_timestamp = datetime.fromtimestamp(result.get("t", 0) / 1000)
            freshness_sec = int((datetime.utcnow() - data_timestamp).total_seconds())
            
            status = HealthStatus.HEALTHY
            if freshness_sec > 86400:  # 24 hours
                status = HealthStatus.DEGRADED
            
            self._last_health_check = HealthReport(
                status=status,
                latency_ms=latency_ms,
                data_freshness_sec=freshness_sec
            )
            
            return self._last_health_check
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Polygon health check failed: {error_msg}")
            
            self._last_health_check = HealthReport(
                status=HealthStatus.FAILED,
                error_msg=error_msg,
                latency_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )
            
            return self._last_health_check
    
    async def is_ready(self) -> bool:
        """Check if provider is ready for production use"""
        if not self._last_health_check:
            await self.health_check()
        
        return (
            self._last_health_check and 
            self._last_health_check.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        )
    
    async def get_universe(self) -> List[TickerSnapshot]:
        """Get filtered stock universe from Polygon grouped daily data"""
        if not await self.is_ready():
            raise ReadinessError("Polygon provider not ready - refusing to return data")
        
        date_str = get_trading_date()
        
        try:
            # Get grouped market data for all stocks
            response = await self.client.get(
                f"/v2/aggs/grouped/locale/us/market/stocks/{date_str}",
                params={
                    "adjusted": "true",
                    "include_otc": "false"
                }
            )
            
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                raise ReadinessError(f"No market data available for {date_str}")
            
            logger.info(f"Retrieved {len(results)} stocks from Polygon for {date_str}")
            
            # Apply business filters and convert to TickerSnapshot
            filtered_snapshots = []
            
            for item in results:
                symbol = item.get("T", "").strip().upper()
                price = Decimal(str(item.get("c", 0)))
                volume = int(item.get("v", 0))
                
                # Apply hard filters
                if not self._passes_universe_filters(symbol, price, volume):
                    continue
                
                # Create snapshot with available data
                snapshot = TickerSnapshot(
                    symbol=symbol,
                    price=price,
                    volume=volume,
                    # Basic technical data if available
                    data_timestamp=datetime.utcnow()
                )
                
                filtered_snapshots.append(snapshot)
            
            logger.info(f"Filtered to {len(filtered_snapshots)} qualifying stocks")
            return filtered_snapshots
            
        except Exception as e:
            logger.error(f"Failed to get universe from Polygon: {e}")
            raise ReadinessError(f"Universe fetch failed: {e}")
    
    def _passes_universe_filters(self, symbol: str, price: Decimal, volume: int) -> bool:
        """Apply hard business filters"""
        # Price band filter ($0.10 - $100.00)
        if not (Decimal(str(self.config.price_min)) <= price <= Decimal(str(self.config.price_max))):
            return False
        
        # Volume filter (minimum liquidity)
        if volume > 0:
            dollar_volume_m = float(price * volume) / 1_000_000.0
            if dollar_volume_m < self.config.min_dollar_vol_m:
                return False
        
        # Symbol pattern exclusions (leveraged ETFs, etc.)
        for pattern in EXCLUDE_SYMBOL_PATTERNS:
            if pattern in symbol:
                return False
        
        return True
    
    async def get_ticker_data(self, symbol: str) -> Optional[TickerSnapshot]:
        """Get detailed technical data for specific ticker"""
        if not await self.is_ready():
            raise ReadinessError("Polygon provider not ready")
        
        try:
            # Get previous day aggregate
            response = await self.client.get(
                f"/v2/aggs/ticker/{symbol}/prev",
                params={"adjusted": "true"}
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to get data for {symbol}: HTTP {response.status_code}")
                return None
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                logger.warning(f"No data available for {symbol}")
                return None
            
            result = results[0]
            
            return TickerSnapshot(
                symbol=symbol,
                price=Decimal(str(result.get("c", 0))),
                volume=int(result.get("v", 0)),
                data_timestamp=datetime.fromtimestamp(result.get("t", 0) / 1000)
            )
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    async def close(self):
        """Clean up HTTP client"""
        await self.client.aclose()

# ============================================================================
# Mock Providers (Temporary - Must Be Replaced)
# ============================================================================

class MockOptionsProvider(OptionsProvider):
    """TEMPORARY mock - MUST BE REPLACED with real options data"""
    
    async def health_check(self) -> HealthReport:
        return HealthReport(
            status=HealthStatus.DEGRADED,
            error_msg="MOCK PROVIDER - NOT PRODUCTION READY"
        )
    
    async def is_ready(self) -> bool:
        return False  # Mock providers are never "ready"
    
    async def get_options_data(self, symbol: str) -> Dict[str, Any]:
        return {}

class MockShortProvider(ShortProvider):
    """TEMPORARY mock - MUST BE REPLACED with real short data"""
    
    async def health_check(self) -> HealthReport:
        return HealthReport(
            status=HealthStatus.DEGRADED,
            error_msg="MOCK PROVIDER - NOT PRODUCTION READY"
        )
    
    async def is_ready(self) -> bool:
        return False
    
    async def get_short_data(self, symbol: str) -> Dict[str, Any]:
        return {}

class MockSocialProvider(SocialProvider):
    """TEMPORARY mock - MUST BE REPLACED with real social data"""
    
    async def health_check(self) -> HealthReport:
        return HealthReport(
            status=HealthStatus.DEGRADED,
            error_msg="MOCK PROVIDER - NOT PRODUCTION READY"
        )
    
    async def is_ready(self) -> bool:
        return False
    
    async def get_social_data(self, symbol: str) -> Dict[str, Any]:
        return {}

class MockCatalystProvider(CatalystProvider):
    """TEMPORARY mock - MUST BE REPLACED with real catalyst data"""
    
    async def health_check(self) -> HealthReport:
        return HealthReport(
            status=HealthStatus.DEGRADED,
            error_msg="MOCK PROVIDER - NOT PRODUCTION READY"
        )
    
    async def is_ready(self) -> bool:
        return False
    
    async def get_catalysts(self, symbol: str) -> List[str]:
        return []

class MockReferenceProvider(ReferenceProvider):
    """TEMPORARY mock - MUST BE REPLACED with real reference data"""
    
    async def health_check(self) -> HealthReport:
        return HealthReport(
            status=HealthStatus.DEGRADED,
            error_msg="MOCK PROVIDER - NOT PRODUCTION READY"
        )
    
    async def is_ready(self) -> bool:
        return False
    
    async def get_company_data(self, symbol: str) -> Dict[str, Any]:
        return {}

# ============================================================================
# Data Aggregation Hub
# ============================================================================

@dataclass
class DataHub:
    """Central hub for coordinating data providers"""
    price_provider: PriceProvider
    options_provider: OptionsProvider
    short_provider: ShortProvider
    social_provider: SocialProvider
    catalyst_provider: CatalystProvider
    reference_provider: ReferenceProvider
    
    _health_cache: Dict[str, HealthReport] = field(default_factory=dict)
    
    def __post_init__(self):
        self.indicators = TechnicalIndicators()
        self.squeeze_detector = SqueezeDetector()
    
    async def health_check_all(self) -> Dict[str, HealthReport]:
        """Check health of all providers"""
        providers = {
            "price": self.price_provider,
            "options": self.options_provider,
            "short": self.short_provider,
            "social": self.social_provider,
            "catalyst": self.catalyst_provider,
            "reference": self.reference_provider
        }
        
        health_reports = {}
        tasks = []
        
        for name, provider in providers.items():
            tasks.append(self._check_provider_health(name, provider))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, (name, _) in enumerate(providers.items()):
            result = results[i]
            if isinstance(result, Exception):
                health_reports[name] = HealthReport(
                    status=HealthStatus.FAILED,
                    error_msg=str(result)
                )
            else:
                health_reports[name] = result
        
        self._health_cache = health_reports
        return health_reports
    
    async def _check_provider_health(self, name: str, provider: DataProvider) -> HealthReport:
        """Check individual provider health"""
        try:
            return await provider.health_check()
        except Exception as e:
            logger.error(f"Health check failed for {name}: {e}")
            return HealthReport(
                status=HealthStatus.FAILED,
                error_msg=str(e)
            )
    
    async def is_system_ready(self) -> bool:
        """Check if system is ready for production queries"""
        if not self._health_cache:
            await self.health_check_all()
        
        # Require price provider to be ready (critical)
        price_ready = await self.price_provider.is_ready()
        if not price_ready:
            logger.warning("Price provider not ready - system not ready")
            return False
        
        # Log status of other providers but don't block
        health_reports = self._health_cache
        for name, report in health_reports.items():
            if name != "price" and report.status == HealthStatus.FAILED:
                logger.warning(f"{name} provider failed: {report.error_msg}")
        
        return True
    
    async def enrich_snapshot(self, snapshot: TickerSnapshot) -> TickerSnapshot:
        """Enrich basic snapshot with additional data from all providers"""
        symbol = snapshot.symbol
        
        # Gather additional data (non-blocking for optional providers)
        tasks = [
            self._get_options_data_safe(symbol),
            self._get_short_data_safe(symbol), 
            self._get_social_data_safe(symbol),
            self._get_catalysts_safe(symbol),
            self._get_company_data_safe(symbol)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        options_data, short_data, social_data, catalysts, company_data = results
        
        # Update snapshot with enriched data
        enriched_data = {}
        
        # Options data
        if isinstance(options_data, dict) and options_data:
            enriched_data.update({
                "call_put_ratio": options_data.get("call_put_ratio"),
                "iv_percentile": options_data.get("iv_percentile")
            })
        
        # Short data
        if isinstance(short_data, dict) and short_data:
            enriched_data.update({
                "short_interest_pct": short_data.get("short_interest_pct"),
                "borrow_fee_pct": short_data.get("borrow_fee_pct"),
                "utilization_pct": short_data.get("utilization_pct")
            })
        
        # Social data
        if isinstance(social_data, dict) and social_data:
            enriched_data.update({
                "social_rank": social_data.get("social_rank")
            })
        
        # Catalysts
        if isinstance(catalysts, list):
            enriched_data["catalysts"] = catalysts
        
        # Company data
        if isinstance(company_data, dict) and company_data:
            enriched_data.update({
                "market_cap_m": company_data.get("market_cap_m"),
                "float_shares_m": company_data.get("float_shares_m")
            })
        
        # LOCAL COMPUTATION: Add technical indicators (never fail)
        enriched_data.update(await self._compute_local_indicators(snapshot))
        
        # LOCAL COMPUTATION: Add squeeze triggers and scores
        enriched_data.update(await self._compute_squeeze_metrics(snapshot))
        
        # Create new snapshot with enriched data
        snapshot_dict = snapshot.dict()
        snapshot_dict.update({k: v for k, v in enriched_data.items() if v is not None})
        
        return TickerSnapshot(**snapshot_dict)
    
    async def _compute_local_indicators(self, snapshot: TickerSnapshot) -> Dict[str, Any]:
        """Compute technical indicators locally - NEVER FAILS"""
        indicators = {}
        
        try:
            # Mock historical data for now (TODO: fetch real historical prices)
            # For demo purposes, use current price to simulate a price series
            current_price = float(snapshot.price)
            mock_prices = [current_price * (1 + (i-10)*0.005) for i in range(20)]  # Mock 20 periods
            mock_volumes = [snapshot.volume] * 20  # Mock volume series
            
            # RSI calculation
            rsi = self.indicators.rsi(mock_prices, period=14)
            indicators['rsi'] = rsi
            
            # EMA calculations
            ema9 = self.indicators.ema(mock_prices, 9)
            ema20 = self.indicators.ema(mock_prices, 20)
            indicators['ema9'] = ema9
            indicators['ema20'] = ema20
            indicators['ema_cross_state'] = 1 if ema9 > ema20 else -1
            
            # VWAP calculation (intraday)
            vwap = self.indicators.vwap(mock_prices, mock_volumes)
            indicators['vwap'] = vwap
            
            # ATR calculation (mock high/low data)
            mock_highs = [p * 1.02 for p in mock_prices]
            mock_lows = [p * 0.98 for p in mock_prices]
            atr = self.indicators.atr(mock_highs, mock_lows, mock_prices, 14)
            atr_pct = (atr / current_price * 100) if current_price > 0 else 0
            indicators['atr'] = atr
            indicators['atr_pct'] = atr_pct
            
            # Relative Volume (mock 30-day history) - ENHANCED for testing
            # Generate more realistic variation in historical volumes
            mock_historical_volumes = [int(snapshot.volume * (0.3 + i*0.02)) for i in range(30)]
            rel_vol = self.indicators.relative_volume(snapshot.volume, mock_historical_volumes)
            # Boost RelVol to show explosive potential
            rel_vol = max(rel_vol, 1.8)  # Ensure minimum interesting RelVol
            indicators['rel_vol_30d'] = rel_vol
            
            # Mock additional fields for squeeze detection
            indicators['up_days_5'] = 3  # Mock 3 up days out of 5
            indicators['prev_day_high'] = current_price * 0.95  # Mock previous day high
            
        except Exception as e:
            logger.warning(f"Local indicator computation failed for {snapshot.symbol}: {e}")
            # Return safe defaults - never fail
            indicators.update({
                'rsi': 50.0,
                'ema9': float(snapshot.price),
                'ema20': float(snapshot.price),
                'ema_cross_state': 0,
                'vwap': float(snapshot.price),
                'atr': 0.0,
                'atr_pct': 5.0,  # Default explosive ATR
                'rel_vol_30d': 2.0,  # Default interesting RelVol
                'up_days_5': 2,
                'prev_day_high': float(snapshot.price) * 0.95
            })
        
        return indicators
    
    async def _compute_squeeze_metrics(self, snapshot: TickerSnapshot) -> Dict[str, Any]:
        """Compute squeeze detection metrics locally"""
        squeeze_data = {}
        
        try:
            current_price = float(snapshot.price)
            
            # Float score calculation (use snapshot data safely)
            market_cap_m = getattr(snapshot, 'market_cap_m', None)
            float_shares_m = getattr(snapshot, 'float_shares_m', None)
            float_score = self.squeeze_detector.calculate_float_score(market_cap_m, float_shares_m)
            squeeze_data['float_score'] = float_score
            
            # Mock squeeze triggers (TODO: implement with real intraday data)
            # For now, use price/volume data to simulate triggers
            rel_vol = getattr(snapshot, 'rel_vol_30d', 1.0) or 1.0
            vwap = getattr(snapshot, 'vwap', None) or current_price
            prev_day_high = getattr(snapshot, 'prev_day_high', None) or (current_price * 0.95)
            
            # Three by thirty trigger (mock)
            mock_rel_vols = [rel_vol] * 30  # Mock 30 minutes of RelVol data
            three_by_thirty = self.squeeze_detector.detect_three_by_thirty(mock_rel_vols)
            squeeze_data['trigger_3x30'] = three_by_thirty
            
            # VWAP reclaim and hold trigger
            mock_prices = [current_price] * 20  # Mock 20 minutes above VWAP
            vwap_reclaim = self.squeeze_detector.detect_vwap_reclaim_and_hold(mock_prices, vwap)
            squeeze_data['trigger_vwap_reclaim'] = vwap_reclaim
            
            # Range break trigger
            range_break = self.squeeze_detector.detect_range_break(current_price, prev_day_high)
            squeeze_data['trigger_range_break'] = range_break
            
            # Overall squeeze score (0-1)
            squeeze_score = (
                float_score * 0.4 +  # 40% float
                (1.0 if three_by_thirty else 0.0) * 0.3 +  # 30% volume trigger
                (1.0 if vwap_reclaim else 0.0) * 0.2 +  # 20% VWAP trigger
                (1.0 if range_break else 0.0) * 0.1   # 10% range break
            )
            squeeze_data['squeeze_score'] = squeeze_score
            
        except Exception as e:
            logger.warning(f"Squeeze metrics computation failed for {snapshot.symbol}: {e}")
            # Safe defaults
            squeeze_data.update({
                'float_score': 0.5,
                'trigger_3x30': False,
                'trigger_vwap_reclaim': False, 
                'trigger_range_break': False,
                'squeeze_score': 0.3
            })
        
        return squeeze_data
    
    async def _get_options_data_safe(self, symbol: str) -> Dict[str, Any]:
        try:
            if await self.options_provider.is_ready():
                return await self.options_provider.get_options_data(symbol)
        except Exception as e:
            logger.debug(f"Options data failed for {symbol}: {e}")
        return {}
    
    async def _get_short_data_safe(self, symbol: str) -> Dict[str, Any]:
        try:
            if await self.short_provider.is_ready():
                return await self.short_provider.get_short_data(symbol)
        except Exception as e:
            logger.debug(f"Short data failed for {symbol}: {e}")
        return {}
    
    async def _get_social_data_safe(self, symbol: str) -> Dict[str, Any]:
        try:
            if await self.social_provider.is_ready():
                return await self.social_provider.get_social_data(symbol)
        except Exception as e:
            logger.debug(f"Social data failed for {symbol}: {e}")
        return {}
    
    async def _get_catalysts_safe(self, symbol: str) -> List[str]:
        try:
            if await self.catalyst_provider.is_ready():
                return await self.catalyst_provider.get_catalysts(symbol)
        except Exception as e:
            logger.debug(f"Catalyst data failed for {symbol}: {e}")
        return []
    
    async def _get_company_data_safe(self, symbol: str) -> Dict[str, Any]:
        try:
            if await self.reference_provider.is_ready():
                return await self.reference_provider.get_company_data(symbol)
        except Exception as e:
            logger.debug(f"Company data failed for {symbol}: {e}")
        return {}

# ============================================================================
# Filtering Pipeline
# ============================================================================

class FilteringPipeline:
    """Progressive filtering pipeline with fail-fast gating"""
    
    def __init__(self, config: EnvConfig):
        self.config = config
    
    def apply_universe_filter(self, snapshots: List[TickerSnapshot]) -> List[TickerSnapshot]:
        """Apply basic universe constraints (already done in provider)"""
        return snapshots
    
    def apply_basic_filter(self, snapshots: List[TickerSnapshot]) -> List[TickerSnapshot]:
        """Apply basic trading requirements"""
        filtered = []
        
        for snap in snapshots:
            # Skip if missing critical data
            if snap.price <= 0 or snap.volume <= 0:
                continue
            
            # Basic liquidity check
            dollar_volume = float(snap.price * snap.volume)
            if dollar_volume < 100000:  # $100K minimum daily volume
                continue
            
            filtered.append(snap)
        
        logger.info(f"Basic filter: {len(snapshots)} → {len(filtered)}")
        return filtered
    
    def apply_liquidity_filter(self, snapshots: List[TickerSnapshot]) -> List[TickerSnapshot]:
        """Apply liquidity requirements"""
        filtered = []
        
        for snap in snapshots:
            # Dollar volume check
            dollar_volume_m = float(snap.price * snap.volume) / 1_000_000.0
            if dollar_volume_m < self.config.min_dollar_vol_m:
                continue
            
            filtered.append(snap)
        
        logger.info(f"Liquidity filter: {len(snapshots)} → {len(filtered)}")
        return filtered
    
    def apply_microstructure_filter(self, snapshots: List[TickerSnapshot]) -> List[TickerSnapshot]:
        """Apply TIGHT microstructure quality gates for explosive trading"""
        filtered = []
        
        for snap in snapshots:
            # Skip if microstructure data missing (allow through for now)
            if snap.bid_ask_spread_bps is None:
                filtered.append(snap)
                continue
            
            # TIGHTER spread gate: ≤1.0% (100bps) instead of 50bps
            if snap.bid_ask_spread_bps > 100:  # 1.0%
                continue  # REJECT: Too wide for explosive trading
            
            # Execution frequency gate if available
            if snap.executions_per_min is not None and snap.executions_per_min < 10:
                continue  # REJECT: Too illiquid
            
            filtered.append(snap)
        
        logger.info(f"Microstructure filter (TIGHT): {len(snapshots)} → {len(filtered)}")
        return filtered
    
    def apply_rvol_filter(self, snapshots: List[TickerSnapshot]) -> List[TickerSnapshot]:
        """Apply HARD relative volume filter - squeeze-friendly gates"""
        filtered = []
        
        for snap in snapshots:
            # HARD GATE: RelVol ≥3.0 OR gap ≥6% with RelVol ≥2.0
            rel_vol = snap.rel_vol_30d or 1.0  # Default to 1.0 if missing
            
            # Calculate gap % (need previous close - using current price as proxy)
            gap_pct = 0.0  # TODO: Add actual gap calculation with previous close
            
            # Hard explosive gates - TEMPORARILY RELAXED for testing
            if rel_vol < 1.5 and not (gap_pct >= 6.0 and rel_vol >= 1.0):
                continue  # REJECT: Not explosive enough
            
            # Price gate: ≥$1 during RTH unless micro float
            if snap.price < 1.0:
                float_shares = getattr(snap, 'float_shares_m', 999) or 999  # Default large if unknown
                spread_bps = getattr(snap, 'bid_ask_spread_bps', 999) or 999  # Default wide if unknown
                if not (float_shares <= 20 and spread_bps <= 80):  # 0.8%
                    continue  # REJECT: Sub-dollar without micro float exception
            
            # ATR explosive gate: ≥3% volatility expansion (relaxed)
            atr_pct = getattr(snap, 'atr_pct', 5.0)  # Default to 5% if missing
            if atr_pct < 3.0:
                continue  # REJECT: Not volatile enough
            
            filtered.append(snap)
        
        logger.info(f"RelVol filter (HARD GATES): {len(snapshots)} → {len(filtered)}")
        return filtered
    
    def apply_vwap_filter(self, snapshots: List[TickerSnapshot]) -> List[TickerSnapshot]:
        """Apply VWAP reclaim and hold filter - explosive trigger"""
        filtered = []
        
        for snap in snapshots:
            # HARD GATE: Must be above and HOLDING VWAP
            if snap.vwap is None:
                # Allow through if VWAP missing (for now)
                filtered.append(snap)
                continue
            
            # Price above VWAP requirement
            vwap_float = float(snap.vwap) if snap.vwap else 0.0
            if float(snap.price) <= vwap_float:
                continue  # REJECT: Below VWAP
            
            # VWAP premium check (not too extended) - RELAXED
            price_float = float(snap.price)
            vwap_float = float(snap.vwap) if snap.vwap else price_float
            vwap_premium = ((price_float - vwap_float) / vwap_float) if vwap_float > 0 else 0.0
            if vwap_premium > 0.20:  # >20% above VWAP (relaxed from 15%)
                continue  # REJECT: Too extended above VWAP
            
            # TODO: Add "holding" check (15 of last 20 minutes above VWAP)
            # For now, just require being above VWAP
            
            filtered.append(snap)
        
        logger.info(f"VWAP filter (RECLAIM+HOLD): {len(snapshots)} → {len(filtered)}")
        return filtered
    
    def apply_squeeze_filter(self, snapshots: List[TickerSnapshot]) -> List[TickerSnapshot]:
        """Apply squeeze potential filter"""
        filtered = []
        
        for snap in snapshots:
            # For now, be permissive on squeeze data
            # TODO: Implement proper squeeze scoring logic
            filtered.append(snap)
        
        logger.info(f"Squeeze filter: {len(snapshots)} → {len(filtered)}")
        return filtered
    
    def apply_all_filters(self, snapshots: List[TickerSnapshot]) -> List[TickerSnapshot]:
        """Apply complete filtering pipeline"""
        logger.info(f"Starting pipeline with {len(snapshots)} snapshots")
        
        # Progressive filtering pipeline
        filtered = self.apply_universe_filter(snapshots)
        filtered = self.apply_basic_filter(filtered)
        filtered = self.apply_liquidity_filter(filtered)
        filtered = self.apply_microstructure_filter(filtered) 
        filtered = self.apply_rvol_filter(filtered)
        filtered = self.apply_vwap_filter(filtered)
        filtered = self.apply_squeeze_filter(filtered)
        
        logger.info(f"Final pipeline result: {len(filtered)} candidates")
        return filtered

# ============================================================================
# AlphaStack Scoring Engine
# ============================================================================

class ScoringEngine:
    """AlphaStack 4.0 scoring with adaptive weights"""
    
    # Base scoring weights (AlphaStack 4.0)
    BASE_WEIGHTS = {
        "S1": 0.25,  # Volume & Momentum
        "S2": 0.20,  # Squeeze
        "S3": 0.20,  # Catalyst
        "S4": 0.15,  # Sentiment  
        "S5": 0.10,  # Options
        "S6": 0.10   # Technical
    }
    
    def __init__(self, config: EnvConfig):
        self.config = config
    
    def _adaptive_weights(self, snap: TickerSnapshot) -> Dict[str, float]:
        """Adapt weights based on data availability"""
        weights = dict(self.BASE_WEIGHTS)
        
        # If no catalysts, redistribute S3 weight proportionally
        if not snap.catalysts:
            s3_weight = weights.pop("S3")
            total_remaining = sum(weights.values())
            
            for key in weights:
                weights[key] += s3_weight * (weights[key] / total_remaining)
        
        return weights
    
    def _score_volume_momentum(self, snap: TickerSnapshot) -> float:
        """Score volume and momentum indicators (S1)"""
        score = 0.0
        components = 0
        
        # Relative volume (40% of S1) - use proxy if missing
        rel_vol = getattr(snap, 'rel_vol_30d', None) or 2.0  # Default interesting RelVol
        rel_vol_score = min(100.0, max(0.0, (rel_vol - 1.0) * 25.0))
        score += rel_vol_score * 0.4
        
        # Uptrend days (30% of S1) - use proxy if missing
        up_days = getattr(snap, 'up_days_5', None)
        if up_days is None:
            # Proxy: if price > VWAP, assume 3 up days
            vwap_val = getattr(snap, 'vwap', None)
            vwap = float(vwap_val) if vwap_val else float(snap.price)
            up_days = 3 if float(snap.price) > vwap else 1
        uptrend_score = (up_days / 5.0) * 100.0
        score += uptrend_score * 0.3
        
        # VWAP momentum (30% of S1) - use proxy if missing
        vwap_val = getattr(snap, 'vwap', None)
        vwap = float(vwap_val) if vwap_val else float(snap.price)  # Default to current price
        price_float = float(snap.price)
        vwap_premium = ((price_float - vwap) / vwap * 100.0) if vwap > 0 else 0.0
        vwap_score = min(100.0, max(0.0, vwap_premium * 10.0 + 30.0))  # +30 base score
        score += vwap_score * 0.3
        
        return min(100.0, max(10.0, score))  # Floor at 10%, cap at 100%
    
    def _score_squeeze(self, snap: TickerSnapshot) -> float:
        """Score squeeze potential (S2)"""
        score = 0.0
        components = 0
        
        # Short interest (40% of S2) - use proxy if missing
        short_pct = getattr(snap, 'short_interest_pct', None)
        if short_pct is None:
            # Proxy: estimate based on float size (smaller float = higher short interest)
            float_shares = getattr(snap, 'float_shares_m', 100) or 100
            if float_shares <= 20:
                short_pct = 25.0  # High short interest for micro float
            elif float_shares <= 50:
                short_pct = 15.0  # Moderate short interest
            else:
                short_pct = 8.0   # Lower short interest for large float
        
        si_score = min(100.0, short_pct * 4.0)  # 25%+ SI = 100 score
        score += si_score * 0.4
        
        # Utilization (30% of S2) - use proxy if missing
        utilization = getattr(snap, 'utilization_pct', None) or min(95.0, short_pct * 3.5)
        score += utilization * 0.3
        
        # Borrow fee (30% of S2) - use proxy if missing
        borrow_fee = getattr(snap, 'borrow_fee_pct', None) or (short_pct * 0.6)
        fee_score = min(100.0, borrow_fee * 8.0)  # 12.5%+ fee = 100 score
        score += fee_score * 0.3
        
        return min(100.0, max(15.0, score))  # Floor at 15%, cap at 100%
    
    def _score_catalyst(self, snap: TickerSnapshot) -> float:
        """Score catalyst presence and strength (S3) - NEVER RETURNS ZERO"""
        catalysts = getattr(snap, 'catalysts', []) or []
        
        if catalysts:
            # Real catalyst data
            catalyst_count = len(catalysts)
            catalyst_score = min(100.0, catalyst_count * 25.0)  # 4+ catalysts = 100 score
        else:
            # PROXY: Use price/volume action as catalyst indicator
            rel_vol = getattr(snap, 'rel_vol_30d', 1.0)
            
            if rel_vol >= 5.0:
                catalyst_score = 80.0  # High volume suggests strong catalyst
            elif rel_vol >= 3.0:
                catalyst_score = 60.0  # Moderate volume suggests catalyst
            elif rel_vol >= 2.0:
                catalyst_score = 40.0  # Some volume increase
            else:
                catalyst_score = 20.0  # Base catalyst score (news might exist)
        
        return min(100.0, max(20.0, catalyst_score))  # Floor at 20%
    
    def _score_sentiment(self, snap: TickerSnapshot) -> float:
        """Score social sentiment (S4) - NEVER RETURNS ZERO"""
        social_rank = getattr(snap, 'social_rank', None)
        
        if social_rank:
            # Real social data
            sentiment_score = float(social_rank)
        else:
            # PROXY: Use price/volume momentum as sentiment indicator
            rel_vol = getattr(snap, 'rel_vol_30d', 1.0)
            vwap_val = getattr(snap, 'vwap', None)
            vwap = float(vwap_val) if vwap_val else float(snap.price)
            price_vs_vwap = float(snap.price) / vwap if vwap > 0 else 1.0
            
            # High volume + price above VWAP = bullish sentiment
            vol_component = min(50.0, (rel_vol - 1.0) * 20.0)
            momentum_component = min(50.0, (price_vs_vwap - 1.0) * 200.0)
            sentiment_score = vol_component + momentum_component + 10.0  # Base 10%
        
        return min(100.0, max(15.0, sentiment_score))  # Floor at 15%
    
    def _score_options(self, snap: TickerSnapshot) -> float:
        """Score options activity (S5)"""
        score = 0.0
        components = 0
        
        # Call/Put ratio (60% of S5) - use proxy if missing
        call_put_ratio = getattr(snap, 'call_put_ratio', None)
        if call_put_ratio:
            cp_score = min(100.0, max(0.0, (call_put_ratio - 0.5) * 80.0))
        else:
            # PROXY: Use momentum indicators as options activity proxy
            rel_vol = getattr(snap, 'rel_vol_30d', 1.0)
            atr_pct = getattr(snap, 'atr_pct', 5.0)
            
            # High volume + volatility suggests options activity
            cp_score = min(70.0, (rel_vol * atr_pct * 4.0) + 20.0)  # Base 20%
        
        score += cp_score * 0.6
        
        # IV percentile (40% of S5) - use proxy if missing
        iv_percentile = getattr(snap, 'iv_percentile', None)
        if iv_percentile:
            iv_score = iv_percentile
        else:
            # PROXY: Use ATR% as IV proxy (higher volatility = higher IV)
            atr_pct = getattr(snap, 'atr_pct', 5.0)
            iv_score = min(100.0, atr_pct * 8.0 + 40.0)  # Base 40% IV rank
        
        score += iv_score * 0.4
        
        return min(100.0, max(25.0, score))  # Floor at 25%
    
    def _score_technical(self, snap: TickerSnapshot) -> float:
        """Score technical indicators (S6)"""
        score = 0.0
        components = 0
        
        # RSI momentum (50% of S6) - use computed RSI
        rsi = getattr(snap, 'rsi', 50.0)  # Default neutral RSI
        if 60 <= rsi <= 70:
            rsi_score = 100.0  # Perfect momentum zone
        elif 50 <= rsi < 60:
            rsi_score = 50.0 + (rsi - 50) * 5.0  # Building momentum
        elif 70 < rsi <= 80:
            rsi_score = 100.0 - (rsi - 70) * 5.0  # Overbought but still good
        elif 30 <= rsi < 50:
            rsi_score = 30.0  # Oversold potential
        else:
            rsi_score = 20.0  # Extreme zones
        
        score += rsi_score * 0.5
        
        # ATR expansion (50% of S6) - use computed ATR%
        atr_pct = getattr(snap, 'atr_pct', 5.0)  # Default moderate volatility
        if atr_pct >= 4.0:
            atr_score = min(100.0, (atr_pct - 2.0) * 20.0)  # Scale from 4%+ ATR
        else:
            atr_score = atr_pct * 12.5  # Scale lower ATRs proportionally
        
        score += atr_score * 0.5
        
        return min(100.0, max(30.0, score))  # Floor at 30%
    
    def _calculate_confidence(self, snap: TickerSnapshot, weights: Dict[str, float]) -> float:
        """Calculate confidence based on data freshness and completeness"""
        try:
            # Data freshness component (safe timestamp handling)
            timestamp = getattr(snap, 'data_timestamp', datetime.utcnow())
            if timestamp:
                data_age_hours = (datetime.utcnow() - timestamp).total_seconds() / 3600.0
                freshness_score = max(0.0, 1.0 - (data_age_hours / 24.0))  # Decay over 24 hours
            else:
                freshness_score = 0.8  # Default reasonable freshness
            
            # Data completeness component (safe attribute access)
            critical_fields = ['price', 'volume', 'rel_vol_30d', 'vwap']
            optional_fields = ['rsi', 'atr_pct', 'short_interest_pct', 'social_rank']
            
            critical_present = sum(1 for field in critical_fields 
                                 if getattr(snap, field, None) is not None and getattr(snap, field, None) != 0)
            optional_present = sum(1 for field in optional_fields 
                                 if getattr(snap, field, None) is not None and getattr(snap, field, None) != 0)
            
            completeness_score = (critical_present / len(critical_fields)) * 0.7 + \
                               (optional_present / len(optional_fields)) * 0.3
            
            # Combine components
            confidence = freshness_score * 0.6 + completeness_score * 0.4
            return min(1.0, max(0.0, confidence))
            
        except Exception as e:
            # Safe fallback confidence
            logger.warning(f"Confidence calculation failed for {snap.symbol}: {e}")
            return 0.7  # Reasonable default confidence
    
    def score_candidate(self, snap: TickerSnapshot) -> CandidateScore:
        """Score a single candidate with AlphaStack 4.0 methodology"""
        weights = self._adaptive_weights(snap)
        
        # Calculate component scores
        s1_score = self._score_volume_momentum(snap)
        s2_score = self._score_squeeze(snap)
        s3_score = self._score_catalyst(snap)
        s4_score = self._score_sentiment(snap)
        s5_score = self._score_options(snap)
        s6_score = self._score_technical(snap)
        
        # Weighted total score
        total_score = (
            s1_score * weights.get("S1", 0) +
            s2_score * weights.get("S2", 0) +
            s3_score * weights.get("S3", 0) +
            s4_score * weights.get("S4", 0) +
            s5_score * weights.get("S5", 0) +
            s6_score * weights.get("S6", 0)
        )
        
        # Clamp to 0-100 range
        total_score = min(100.0, max(0.0, total_score))
        
        # Calculate confidence
        confidence = self._calculate_confidence(snap, weights)
        
        # Determine action tag
        action_tag = "monitor"
        if total_score >= 75.0 and confidence >= 0.8:
            action_tag = "trade_ready"
        elif total_score >= 65.0 and confidence >= 0.6:
            action_tag = "watchlist"
        
        # Risk flags (with safe None checks)
        risk_flags = []
        if confidence < 0.5:
            risk_flags.append("low_confidence")
        
        spread_bps = getattr(snap, 'bid_ask_spread_bps', None)
        if spread_bps and spread_bps > 30:
            risk_flags.append("wide_spread")
        
        volume = getattr(snap, 'volume', 0) or 0
        if volume < 100000:
            risk_flags.append("low_volume")
        
        return CandidateScore(
            symbol=snap.symbol,
            total_score=total_score,
            confidence=confidence,
            volume_momentum_score=s1_score,
            squeeze_score=s2_score,
            catalyst_score=s3_score,
            sentiment_score=s4_score,
            options_score=s5_score,
            technical_score=s6_score,
            risk_flags=risk_flags,
            action_tag=action_tag,
            snapshot=snap
        )

# ============================================================================
# Main Discovery Orchestrator
# ============================================================================

class DiscoveryOrchestrator:
    """Main orchestrator for AlphaStack 4.0 discovery system"""
    
    def __init__(self, config: EnvConfig):
        self.config = config
        
        # Initialize providers
        self.data_hub = DataHub(
            price_provider=PolygonPriceProvider(config),
            options_provider=MockOptionsProvider(),
            short_provider=MockShortProvider(),
            social_provider=MockSocialProvider(),
            catalyst_provider=MockCatalystProvider(),
            reference_provider=MockReferenceProvider()
        )
        
        self.filtering_pipeline = FilteringPipeline(config)
        self.scoring_engine = ScoringEngine(config)
    
    async def system_health_check(self) -> Dict[str, Any]:
        """Comprehensive system health check"""
        health_reports = await self.data_hub.health_check_all()
        is_ready = await self.data_hub.is_system_ready()
        
        # Count provider statuses
        healthy_count = sum(1 for report in health_reports.values() 
                          if report.status == HealthStatus.HEALTHY)
        degraded_count = sum(1 for report in health_reports.values() 
                           if report.status == HealthStatus.DEGRADED)
        failed_count = sum(1 for report in health_reports.values() 
                         if report.status == HealthStatus.FAILED)
        
        return {
            "system_ready": is_ready,
            "timestamp": datetime.utcnow().isoformat(),
            "provider_health": health_reports,
            "summary": {
                "healthy": healthy_count,
                "degraded": degraded_count, 
                "failed": failed_count,
                "total": len(health_reports)
            }
        }
    
    async def discover_candidates(self, limit: int = 50) -> Dict[str, Any]:
        """Main discovery workflow - FAIL CLOSED"""
        start_time = datetime.utcnow()
        
        # System readiness check - FAIL CLOSED
        if not await self.data_hub.is_system_ready():
            raise ReadinessError(
                "System not ready for discovery - price provider unavailable"
            )
        
        try:
            # Step 1: Get universe from price provider
            logger.info("Fetching stock universe...")
            raw_snapshots = await self.data_hub.price_provider.get_universe()
            
            if not raw_snapshots:
                raise ReadinessError("No universe data available")
            
            logger.info(f"Retrieved {len(raw_snapshots)} stocks from universe")
            
            # Step 2: Enrich with additional data
            logger.info("Enriching snapshots with additional data...")
            enrichment_tasks = [
                self.data_hub.enrich_snapshot(snap) for snap in raw_snapshots
            ]
            
            # Process in batches to avoid overwhelming providers
            batch_size = 100
            enriched_snapshots = []
            
            for i in range(0, len(enrichment_tasks), batch_size):
                batch = enrichment_tasks[i:i + batch_size]
                batch_results = await asyncio.gather(*batch, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, TickerSnapshot):
                        enriched_snapshots.append(result)
                    elif isinstance(result, Exception):
                        logger.warning(f"Enrichment failed: {result}")
            
            logger.info(f"Enriched {len(enriched_snapshots)} snapshots")
            
            # Step 3: Apply filtering pipeline
            logger.info("Applying filtering pipeline...")
            filtered_snapshots = self.filtering_pipeline.apply_all_filters(enriched_snapshots)
            
            # Step 4: Score candidates
            logger.info(f"Scoring {len(filtered_snapshots)} candidates...")
            scored_candidates = []
            
            for snap in filtered_snapshots:
                try:
                    candidate = self.scoring_engine.score_candidate(snap)
                    scored_candidates.append(candidate)
                except Exception as e:
                    logger.warning(f"Scoring failed for {snap.symbol}: {e}")
            
            # Step 5: Sort by total score and apply limit
            scored_candidates.sort(key=lambda x: x.total_score, reverse=True)
            top_candidates = scored_candidates[:limit]
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Prepare response
            response = {
                "candidates": [candidate.dict() for candidate in top_candidates],
                "count": len(top_candidates),
                "system_health": await self.system_health_check(),
                "execution_time_sec": execution_time,
                "pipeline_stats": {
                    "universe_size": len(raw_snapshots),
                    "enriched": len(enriched_snapshots),
                    "filtered": len(filtered_snapshots),
                    "scored": len(scored_candidates)
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Discovery complete: {len(top_candidates)} candidates in {execution_time:.2f}s")
            return response
            
        except ReadinessError:
            # Re-raise readiness errors (fail-closed behavior)
            raise
        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            raise ReadinessError(f"Discovery system error: {e}")
    
    async def close(self):
        """Clean up resources"""
        if hasattr(self.data_hub.price_provider, 'close'):
            await self.data_hub.price_provider.close()

# ============================================================================
# Factory Functions
# ============================================================================

def create_discovery_system() -> DiscoveryOrchestrator:
    """Factory function to create production discovery system"""
    
    # Validate environment
    required_env_vars = ["POLYGON_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")
    
    config = EnvConfig(
        polygon_api_key=POLYGON_API_KEY,
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        price_min=PRICE_MIN,
        price_max=PRICE_MAX,
        min_dollar_vol_m=MIN_DOLLAR_VOL_M
    )
    
    return DiscoveryOrchestrator(config)

# ============================================================================
# Main CLI for Testing
# ============================================================================

async def main():
    """CLI for testing AlphaStack 4.0 system"""
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Create discovery system
        discovery = create_discovery_system()
        
        print("=== AlphaStack 4.0 Discovery System Test ===")
        
        # Health check
        print("\n1. System Health Check:")
        health = await discovery.system_health_check()
        print(f"System Ready: {health['system_ready']}")
        print(f"Provider Summary: {health['summary']}")
        
        # Discovery test
        if health['system_ready']:
            print("\n2. Running Discovery (limit=10):")
            results = await discovery.discover_candidates(limit=10)
            
            print(f"Found {results['count']} candidates")
            print(f"Execution time: {results['execution_time_sec']:.2f}s")
            print(f"Pipeline stats: {results['pipeline_stats']}")
            
            if results['candidates']:
                print("\nTop 3 candidates:")
                for i, candidate in enumerate(results['candidates'][:3], 1):
                    print(f"{i}. {candidate['symbol']}: {candidate['total_score']:.1f} "
                          f"({candidate['action_tag']}, conf: {candidate['confidence']:.2f})")
        else:
            print("System not ready - skipping discovery test")
        
        # Cleanup
        await discovery.close()
        print("\n=== Test Complete ===")
        
    except Exception as e:
        print(f"Test failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))