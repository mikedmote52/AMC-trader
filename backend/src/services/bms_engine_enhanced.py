"""
Enhanced BMS Engine - Advanced Momentum Scanner with $100 Price Cap
Implements sustained RVOL, microstructure gates, directional gating, and multi-component scoring
"""

import logging
import asyncio
import json
import os
import time
import math
from typing import Dict, List, Optional, Tuple, NamedTuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import requests
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration constants
CONFIG = {
    'PRICE': {'MIN': 0.50, 'MAX': 100.00},  # NON-NEGOTIABLE: $100 hard cap preserved
    'MICRO': {'DVOL_MIN': 20_000_000, 'SPREAD_BPS_MAX': 15, 'EXEC_MIN': 200},
    'RVOL': {'WINDOW_MIN': 15, 'THRESHOLD': 3.0},
    'VOL': {'ATR_PCT_MIN': 4},
    'TECH': {'RSI_MIN': 55},
    'CLASSIFY': {'TRADE_READY': 75, 'BUILDER': 70, 'MONITOR': 60}
}

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
    volCurve30dMedian: Dict[int, float]  # minute -> median volume
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
    ssr: bool = False  # Short Sale Restriction
    
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

def clamp(value: float, min_val: float, max_val: float) -> int:
    """Clamp value to range and return as integer"""
    return int(max(min_val, min(max_val, value)))

def scale(value: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    """Scale value from input range to output range"""
    if in_max == in_min:
        return out_min
    ratio = (value - in_min) / (in_max - in_min)
    return out_min + ratio * (out_max - out_min)

class EnhancedBMSEngine:
    """Enhanced BMS Engine with $100 cap and advanced features"""
    
    def __init__(self, polygon_api_key: str):
        self.polygon_api_key = polygon_api_key
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'AMC-TRADER-Enhanced/1.0'})
        
        # Rolling windows for sustained RVOL tracking
        self.rvol_windows = {}  # symbol -> list of (timestamp, rvol) tuples
        self.vwap_reclaim_cache = {}  # symbol -> reclaim status
        
        logger.info("🚀 Enhanced BMS Engine initialized with $100 hard cap")
        logger.info(f"   Price range: ${CONFIG['PRICE']['MIN']}-${CONFIG['PRICE']['MAX']}")
        logger.info(f"   Min dollar volume: ${CONFIG['MICRO']['DVOL_MIN']:,}")
        logger.info(f"   Sustained RVOL: {CONFIG['RVOL']['THRESHOLD']}x for {CONFIG['RVOL']['WINDOW_MIN']}+ minutes")
    
    def passes_price_preference(self, price: float) -> bool:
        """Global preference gate - NON-NEGOTIABLE $100 cap"""
        return CONFIG['PRICE']['MIN'] <= price <= CONFIG['PRICE']['MAX']
    
    def is_listed_on_nyse_or_nasdaq(self, ticker: TickerState) -> bool:
        """Check if ticker is on major exchanges"""
        return ticker.exchange in {'XNYS', 'XNAS', 'ARCX', 'BATS'}
    
    def is_fund_etf_reit_spac_preferred(self, ticker: TickerState) -> bool:
        """Identify funds, ETFs, REITs, SPACs, preferred stocks - COMPREHENSIVE DETECTION"""
        fund_keywords = ['ETF', 'ETN', 'TRUST', 'FUND', 'SPDR', 'INDEX', 'BDC', 
                        'CLOSED-END', 'PREFERRED', 'PFD', 'UNIT', 'WARRANT', 'SPAC', 'REIT']
        
        # Check symbol patterns
        symbol_upper = ticker.symbol.upper()
        if any(keyword in symbol_upper for keyword in fund_keywords):
            return True
        
        # Specific ETF symbols that don't contain "ETF" in name
        known_etfs = {
            'SOXL', 'SOXS', 'TQQQ', 'SQQQ', 'UPRO', 'SPXU', 'TNA', 'TZA',
            'LABU', 'LABD', 'TECL', 'TECS', 'CURE', 'RWM', 'PSQ', 'QID',
            'DXD', 'DOG', 'SDS', 'QQQ', 'SPY', 'IWM', 'DIA', 'VTI', 'VOO',
            'ARKK', 'ARKQ', 'ARKG', 'ARKW', 'GDXJ', 'GDX', 'SLV', 'GLD',
            'XLE', 'XLF', 'XLK', 'XLV', 'XLI', 'XLP', 'XLU', 'XLY', 'XLB',
            'UVXY', 'VXX', 'SVXY', 'TMF', 'TMV', 'FAZ', 'FAS', 'ERX', 'ERY'
        }
        
        if ticker.symbol.upper() in known_etfs:
            return True
        
        # Pattern-based detection for leveraged/inverse funds
        if (ticker.symbol.endswith('L') or ticker.symbol.endswith('S') or 
            ticker.symbol.endswith('X') or ticker.symbol.endswith('U')):
            # Additional check for 3-4 character leveraged symbols
            if len(ticker.symbol) <= 4 and ticker.symbol.upper() in known_etfs:
                return True
        
        return False
    
    def stage1_universe_filter(self, t: TickerState) -> bool:
        """Stage 1: Universe filtering with preference + tradability gates"""
        if not self.passes_price_preference(t.price):
            return False  # $100 hard cap enforced
        
        if t.dollarVolume < CONFIG['MICRO']['DVOL_MIN']:
            return False  # $20M+ dollar volume
        
        if t.medianSpreadBps > CONFIG['MICRO']['SPREAD_BPS_MAX']:
            return False  # spread ≤ 15 bps
        
        if t.executionsPerMin < CONFIG['MICRO']['EXEC_MIN']:
            return False  # prints ≥ 200/min
        
        if not self.is_listed_on_nyse_or_nasdaq(t):
            return False  # NYSE/NASDAQ only
        
        if self.is_fund_etf_reit_spac_preferred(t):
            return False  # no funds/ETFs/etc
        
        return True
    
    def minute_rvol(self, t: TickerState) -> float:
        """Calculate minute-based RVOL"""
        current_minute = datetime.now().hour * 60 + datetime.now().minute
        base_volume = t.volCurve30dMedian.get(current_minute, 1.0)
        return max(1.0, t.volMinute / max(1.0, base_volume))
    
    def sustained_rvol(self, t: TickerState) -> bool:
        """Check if RVOL has been sustained for 15+ minutes"""
        current_time = time.time()
        threshold = CONFIG['RVOL']['THRESHOLD']
        window_minutes = CONFIG['RVOL']['WINDOW_MIN']
        
        # Get or create window for this symbol
        if t.symbol not in self.rvol_windows:
            self.rvol_windows[t.symbol] = []
        
        window = self.rvol_windows[t.symbol]
        
        # Add current reading
        current_rvol = self.minute_rvol(t)
        window.append((current_time, current_rvol))
        
        # Clean old readings (older than 30 minutes)
        cutoff_time = current_time - (30 * 60)
        window[:] = [(ts, rvol) for ts, rvol in window if ts > cutoff_time]
        
        # Check if we have sustained RVOL for the required window
        window_start = current_time - (window_minutes * 60)
        sustained_readings = [rvol for ts, rvol in window if ts >= window_start and rvol >= threshold]
        
        return len(sustained_readings) >= window_minutes  # At least one reading per minute
    
    def reclaimed_vwap_within(self, symbol: str, minutes: int) -> bool:
        """Check if price reclaimed VWAP within specified minutes"""
        # Simplified implementation - in production would track VWAP crosses
        return self.vwap_reclaim_cache.get(symbol, False)
    
    def stage2_intraday_filter(self, t: TickerState) -> bool:
        """Stage 2: Intraday filter with sustained RVOL + VWAP logic"""
        if not self.passes_price_preference(t.price):
            return False  # Recheck $100 cap
        
        if not self.sustained_rvol(t):
            return False  # Sustained RVOL required
        
        if t.atrPct < CONFIG['VOL']['ATR_PCT_MIN']:
            return False  # ATR ≥ 4%
        
        if t.halted or t.offeringFiled:
            return False  # No halts or offerings
        
        return True
    
    def multi_day_up_volume_bonus(self, t: TickerState) -> float:
        """Bonus for multi-day volume pattern"""
        # Simplified - would analyze 2-5 day volume trend
        return 2.0 if t.rvolCurrent > 4.0 else 0.0
    
    def short_squeeze_score(self, t: TickerState) -> float:
        """Calculate short squeeze potential"""
        if not all([t.floatShares, t.shortPercent, t.borrowFee, t.utilization]):
            return 5.0  # Default neutral score
        
        score = 0.0
        
        # Float tightness (smaller float = higher squeeze potential)
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
            'analyst_upgrade': 5.0
        }
        
        base = base_scores.get(catalyst_type, 3.0)
        return min(20.0, base * strength)
    
    def social_z_score(self, t: TickerState) -> float:
        """Calculate social media buzz score"""
        if t.socialScore is None:
            return 1.0
        
        # Normalize social score to 0-15 range
        return min(15.0, max(0.0, t.socialScore * 3.0))
    
    def options_flow_score(self, t: TickerState) -> float:
        """Score options flow and gamma potential"""
        if not all([t.callOI, t.putOI, t.ivPercentile]):
            return 1.0
        
        score = 0.0
        
        # Call/Put ratio
        call_put_ratio = t.callOI / max(1.0, t.putOI)
        if call_put_ratio > 2.0:
            score += 4.0
        elif call_put_ratio > 1.5:
            score += 2.0
        
        # IV percentile (high IV = more potential)
        if t.ivPercentile > 80:
            score += 4.0
        elif t.ivPercentile > 60:
            score += 2.0
        
        # Gamma exposure alignment
        if t.gammaExposure and t.gammaExposure > 0:
            score += 2.0
        
        return min(10.0, score)
    
    def tech_setup_score(self, t: TickerState) -> float:
        """Technical setup scoring"""
        score = 0.0
        
        # EMA cross (9 > 20)
        if t.ema9 > t.ema20:
            score += 3.0
        
        # RSI in momentum zone (60-70)
        if 60 <= t.rsi <= 70:
            score += 3.0
        elif 55 <= t.rsi < 75:
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
    
    def score_ticker(self, t: TickerState) -> Score:
        """Enhanced scoring with new weights and directional gates"""
        rvol = t.rvolSustained15min
        above_vwap = t.price >= t.vwap or self.reclaimed_vwap_within(t.symbol, 10)
        
        # Component scores (0-max values as specified)
        early_volume_and_trend = clamp(
            scale(rvol, 3, 8, 15, 25) + self.multi_day_up_volume_bonus(t), 0, 25
        )
        
        squeeze_potential = clamp(self.short_squeeze_score(t), 0, 20)
        catalyst_strength = clamp(self.catalyst_score(t.catalyst), 0, 20)
        social_buzz = clamp(self.social_z_score(t), 0, 15)
        options_gamma = clamp(self.options_flow_score(t), 0, 10)
        technical_setup = clamp(self.tech_setup_score(t), 0, 10)
        
        # Base subtotal
        subtotal = (early_volume_and_trend + squeeze_potential + catalyst_strength + 
                   social_buzz + options_gamma + technical_setup)
        
        # Directional gates & anti-chase multipliers
        multiplier = 1.0
        
        if not above_vwap or t.rsi < CONFIG['TECH']['RSI_MIN']:
            multiplier *= 0.7  # Prevent 100s under VWAP
        
        if self.intraday_extension_atrs(t) > 3:
            multiplier *= 0.8  # Overextended decay
        
        if t.ssr:
            multiplier *= 0.9  # SSR headwind for longs
        
        total = clamp(subtotal * multiplier, 0, 100)
        
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
        """Classification with clearer tags"""
        if total >= CONFIG['CLASSIFY']['TRADE_READY']:
            return 'TRADE_READY'
        elif total >= CONFIG['CLASSIFY']['BUILDER']:
            return 'BUILDER'
        elif total >= CONFIG['CLASSIFY']['MONITOR']:
            return 'MONITOR'
        else:
            return 'IGNORE'
    
    def entry_signal(self, t: TickerState) -> bool:
        """Entry signal logic compatible with ≤$100"""
        if not self.passes_price_preference(t.price):
            return False  # Final price check
        
        # Simplified entry signals
        orb_break = (t.priceChangeIntraday > 2.0 and 
                    self.sustained_rvol(t))
        
        vwap_reclaim = (self.reclaimed_vwap_within(t.symbol, 10) and 
                       self.sustained_rvol(t))
        
        return orb_break or vwap_reclaim
    
    def get_status_message(self) -> str:
        """Status message for UI display"""
        return (f"**Cap enforced**: scanning only stocks **${CONFIG['PRICE']['MIN']}-"
                f"${CONFIG['PRICE']['MAX']}**; **sustained RVOL ≥ {CONFIG['RVOL']['THRESHOLD']}×** "
                f"for ≥{CONFIG['RVOL']['WINDOW_MIN']}m; **above VWAP or active reclaim** "
                f"required for full momentum credit.")

# Acceptance tests
def run_acceptance_tests():
    """Run acceptance tests to verify implementation"""
    engine = EnhancedBMSEngine("test_key")
    
    # Test data
    ok_microstructure = TickerState(
        symbol="TEST", price=50.0, volume=1000000, dollarVolume=50_000_000,
        medianSpreadBps=10, executionsPerMin=250, exchange="XNYS", securityType="CS",
        volCurve30dMedian={570: 1000}, volMinute=3000, rvolCurrent=3.0, rvolSustained15min=3.5,
        vwap=49.0, atrPct=5.0, rsi=65, ema9=50.5, ema20=49.0, priceChangeIntraday=1.0,
        extensionATRs=1.5
    )
    
    # Test 1: Price cap enforced
    from dataclasses import replace
    high_price = replace(ok_microstructure, price=101.0)
    assert not engine.stage1_universe_filter(high_price), "Price cap test failed"
    
    valid_price = replace(ok_microstructure, price=99.99)
    assert engine.stage1_universe_filter(valid_price), "Valid price test failed"
    
    # Test 2: Microstructure guard
    wide_spread = replace(ok_microstructure, medianSpreadBps=35)
    assert not engine.stage1_universe_filter(wide_spread), "Spread test failed"
    
    # Test 3: Classification boundaries
    assert engine.classify(75) == 'TRADE_READY', "Trade ready classification failed"
    assert engine.classify(72) == 'BUILDER', "Builder classification failed"
    assert engine.classify(63) == 'MONITOR', "Monitor classification failed"
    assert engine.classify(59) == 'IGNORE', "Ignore classification failed"
    
    logger.info("✅ All acceptance tests passed!")

if __name__ == "__main__":
    run_acceptance_tests()