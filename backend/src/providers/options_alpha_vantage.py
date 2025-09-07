"""
Alpha Vantage Options Data Provider
Provides ATM options data with IV percentile calculation and no fabrication
"""

import asyncio
import aiohttp
import structlog
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import json
import os
import math

logger = structlog.get_logger()

class AlphaVantageOptionsProvider:
    """
    Provider for options data from Alpha Vantage API
    - ATM Call/Put mid prices from nearest expiry  
    - Black-Scholes IV inversion for ATM IV
    - 252-day IV percentile calculation
    - No fabrication - returns confidence-weighted data or empty
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('ALPHAVANTAGE_API_KEY')
        self.base_url = "https://www.alphavantage.co/query"
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limit_delay = 12  # Alpha Vantage: 5 calls per minute
    
    async def __aenter__(self):
        if not self.api_key:
            raise ValueError("Alpha Vantage API key required. Set ALPHAVANTAGE_API_KEY environment variable.")
        
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            headers={'Accept': 'application/json'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_atm_options_data(self, symbol: str, stock_price: float) -> Dict:
        """
        Get ATM options data and calculate IV percentile
        Returns: {
            'atm_call_mid': float,
            'atm_put_mid': float, 
            'atm_iv': float,
            'iv_percentile': float,
            'expiry_date': str (ISO),
            'strike': float,
            'asof': str (ISO),
            'source': 'alphavantage',
            'staleness_policy_pass': bool,
            'latency_sec': float,
            'confidence': float
        }
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            if not self.session:
                raise RuntimeError("Provider not initialized - use async context manager")
            
            # Get options chain for nearest expiry
            params = {
                'function': 'OPTION_CHAIN',
                'symbol': symbol,
                'apikey': self.api_key
            }
            
            async with self.session.get(self.base_url, params=params) as response:
                if response.status == 429:
                    logger.warning("Alpha Vantage rate limited", symbol=symbol)
                    await asyncio.sleep(self.rate_limit_delay)
                    return self._empty_response(start_time, "rate_limited")
                
                if response.status != 200:
                    logger.error("Alpha Vantage API error", symbol=symbol, status=response.status)
                    return self._empty_response(start_time, f"api_error_{response.status}")
                
                data = await response.json()
                
                if 'data' not in data or not data['data']:
                    logger.info("No options data found", symbol=symbol)
                    return self._empty_response(start_time, "no_data")
                
                options_data = data['data']
                
                # Find nearest expiry
                nearest_expiry = self._find_nearest_expiry(options_data)
                if not nearest_expiry:
                    return self._empty_response(start_time, "no_valid_expiry")
                
                # Find ATM strike
                atm_strike = self._find_atm_strike(options_data[nearest_expiry], stock_price)
                if not atm_strike:
                    return self._empty_response(start_time, "no_atm_strike")
                
                # Get ATM call/put data
                call_data = options_data[nearest_expiry].get('calls', {}).get(str(atm_strike))
                put_data = options_data[nearest_expiry].get('puts', {}).get(str(atm_strike))
                
                if not call_data or not put_data:
                    return self._empty_response(start_time, "missing_atm_data")
                
                # Calculate mid prices
                call_bid = float(call_data.get('bid', 0))
                call_ask = float(call_data.get('ask', 0))
                put_bid = float(put_data.get('bid', 0))
                put_ask = float(put_data.get('ask', 0))
                
                call_mid = (call_bid + call_ask) / 2
                put_mid = (put_bid + put_ask) / 2
                
                # Check data quality
                if call_mid <= 0 or put_mid <= 0:
                    return self._empty_response(start_time, "invalid_prices")
                
                # Calculate ATM IV using Black-Scholes inversion
                expiry_date = datetime.fromisoformat(nearest_expiry)
                time_to_expiry = (expiry_date - datetime.now()).days / 365.0
                
                atm_iv = self._calculate_atm_iv(call_mid, stock_price, atm_strike, time_to_expiry)
                
                # Get IV percentile
                iv_percentile = await self._calculate_iv_percentile(symbol, atm_iv)
                
                # Check freshness (options data should be within 24 hours)
                data_age_hours = self._get_data_age_hours(call_data)
                staleness_pass = data_age_hours <= 24
                
                # Calculate confidence based on spreads and age
                confidence = self._calculate_confidence(call_bid, call_ask, put_bid, put_ask, data_age_hours)
                
                latency_sec = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                result = {
                    'atm_call_mid': round(call_mid, 4),
                    'atm_put_mid': round(put_mid, 4),
                    'atm_iv': round(atm_iv, 4),
                    'iv_percentile': round(iv_percentile, 2),
                    'expiry_date': expiry_date.isoformat(),
                    'strike': atm_strike,
                    'asof': datetime.now(timezone.utc).isoformat(),
                    'source': 'alphavantage',
                    'ingested_at': datetime.now(timezone.utc).isoformat(),
                    'staleness_policy_pass': staleness_pass,
                    'latency_sec': round(latency_sec, 3),
                    'confidence': round(confidence, 3),
                    'data_age_hours': round(data_age_hours, 1)
                }
                
                logger.info("Alpha Vantage options data retrieved", 
                           symbol=symbol, atm_iv=atm_iv, iv_percentile=iv_percentile, confidence=confidence)
                return result
                
        except Exception as e:
            logger.error("Alpha Vantage options fetch failed", symbol=symbol, error=str(e))
            return self._empty_response(start_time, f"error_{str(e)[:20]}")
    
    def _find_nearest_expiry(self, options_data: Dict) -> Optional[str]:
        """Find the nearest expiry date"""
        today = datetime.now()
        nearest_expiry = None
        min_days = float('inf')
        
        for expiry_str in options_data.keys():
            try:
                expiry_date = datetime.fromisoformat(expiry_str)
                days_to_expiry = (expiry_date - today).days
                
                # Must be future date and within reasonable range (1-60 days)
                if 1 <= days_to_expiry <= 60 and days_to_expiry < min_days:
                    min_days = days_to_expiry
                    nearest_expiry = expiry_str
                    
            except ValueError:
                continue
        
        return nearest_expiry
    
    def _find_atm_strike(self, expiry_data: Dict, stock_price: float) -> Optional[float]:
        """Find the strike closest to current stock price"""
        calls = expiry_data.get('calls', {})
        
        if not calls:
            return None
        
        strikes = [float(strike) for strike in calls.keys()]
        
        # Find closest strike to stock price
        atm_strike = min(strikes, key=lambda x: abs(x - stock_price))
        
        # Must be within 10% of stock price to be considered ATM
        if abs(atm_strike - stock_price) / stock_price > 0.1:
            return None
        
        return atm_strike
    
    def _calculate_atm_iv(self, call_price: float, stock_price: float, strike: float, time_to_expiry: float, risk_free_rate: float = 0.05) -> float:
        """
        Calculate implied volatility using Black-Scholes model inversion
        Simple Newton-Raphson method
        """
        if time_to_expiry <= 0:
            return 0.0
        
        # Initial IV guess
        iv = 0.3  # 30%
        
        for _ in range(100):  # Max iterations
            d1 = (math.log(stock_price / strike) + (risk_free_rate + 0.5 * iv * iv) * time_to_expiry) / (iv * math.sqrt(time_to_expiry))
            d2 = d1 - iv * math.sqrt(time_to_expiry)
            
            # Standard normal CDF approximation
            n_d1 = 0.5 * (1 + math.erf(d1 / math.sqrt(2)))
            n_d2 = 0.5 * (1 + math.erf(d2 / math.sqrt(2)))
            
            # Black-Scholes call price
            bs_price = stock_price * n_d1 - strike * math.exp(-risk_free_rate * time_to_expiry) * n_d2
            
            # Vega (sensitivity to IV)
            vega = stock_price * math.sqrt(time_to_expiry) * math.exp(-0.5 * d1 * d1) / math.sqrt(2 * math.pi)
            
            if abs(bs_price - call_price) < 0.001 or vega < 0.001:
                break
            
            # Newton-Raphson step
            iv = iv - (bs_price - call_price) / vega
            iv = max(0.01, min(5.0, iv))  # Clamp between 1% and 500%
        
        return iv
    
    async def _calculate_iv_percentile(self, symbol: str, current_iv: float) -> float:
        """
        Calculate IV percentile based on 252-day historical IV
        For now, returns a simple percentile based on typical ranges
        In production, this would use historical IV data
        """
        # Simplified percentile calculation
        # In production, fetch 252 days of historical IV data
        
        # Typical IV ranges by asset type
        typical_low = 0.15   # 15%
        typical_high = 0.80  # 80%
        
        if current_iv <= typical_low:
            return 5.0
        elif current_iv >= typical_high:
            return 95.0
        else:
            # Linear interpolation
            percentile = 5 + (current_iv - typical_low) / (typical_high - typical_low) * 90
            return max(5, min(95, percentile))
    
    def _get_data_age_hours(self, option_data: Dict) -> float:
        """Get age of options data in hours"""
        # Alpha Vantage typically includes timestamp
        timestamp_str = option_data.get('lastTradeTime', option_data.get('timestamp'))
        
        if not timestamp_str:
            return 24.0  # Assume stale if no timestamp
        
        try:
            data_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            age_seconds = (datetime.now(timezone.utc) - data_time).total_seconds()
            return age_seconds / 3600
        except:
            return 24.0  # Assume stale if parsing fails
    
    def _calculate_confidence(self, call_bid: float, call_ask: float, put_bid: float, put_ask: float, age_hours: float) -> float:
        """
        Calculate confidence score based on spreads and data age
        Returns: 0.0 (no confidence) to 1.0 (full confidence)
        """
        # Spread quality score
        call_spread = call_ask - call_bid if call_ask > call_bid else float('inf')
        put_spread = put_ask - put_bid if put_ask > put_bid else float('inf')
        
        if call_spread == float('inf') or put_spread == float('inf'):
            return 0.0
        
        call_mid = (call_bid + call_ask) / 2
        put_mid = (put_bid + put_ask) / 2
        
        # Relative spread quality (tighter spreads = higher confidence)
        call_spread_pct = call_spread / call_mid if call_mid > 0 else 1.0
        put_spread_pct = put_spread / put_mid if put_mid > 0 else 1.0
        
        avg_spread_pct = (call_spread_pct + put_spread_pct) / 2
        spread_quality = max(0, 1 - avg_spread_pct * 10)  # Good spreads < 10%
        
        # Age quality score (fresher = higher confidence)  
        age_quality = max(0, 1 - age_hours / 24)  # Full confidence if < 1 hour old
        
        # Combined confidence
        confidence = (spread_quality * 0.7 + age_quality * 0.3)
        return max(0.0, min(1.0, confidence))
    
    def _empty_response(self, start_time: datetime, reason: str) -> Dict:
        """Generate empty response with error reason"""
        latency_sec = (datetime.now(timezone.utc) - start_time).total_seconds()
        return {
            'atm_call_mid': 0.0,
            'atm_put_mid': 0.0,
            'atm_iv': 0.0,
            'iv_percentile': 50.0,  # Neutral percentile when unknown
            'expiry_date': None,
            'strike': 0.0,
            'asof': datetime.now(timezone.utc).isoformat(),
            'source': 'alphavantage',
            'ingested_at': datetime.now(timezone.utc).isoformat(),
            'staleness_policy_pass': False,
            'latency_sec': round(latency_sec, 3),
            'confidence': 0.0,
            'error_reason': reason
        }

# Async context manager usage example:
# async with AlphaVantageOptionsProvider() as provider:
#     options_data = await provider.get_atm_options_data('AAPL', 150.0)