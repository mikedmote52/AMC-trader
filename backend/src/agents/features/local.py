#!/usr/bin/env python3
"""
Local feature computation for technical indicators and signal detection
"""
from math import isnan, sqrt
from typing import List, Dict, Optional, Union

def typical_price(bar: Dict[str, float]) -> float:
    """Calculate typical price from OHLC bar"""
    return (bar['h'] + bar['l'] + bar['c']) / 3.0

def vwap(minute_bars: List[Dict[str, float]]) -> Optional[float]:
    """
    Calculate Volume Weighted Average Price from minute bars
    minute_bars: List of dicts with keys 'h', 'l', 'c', 'v'
    """
    if not minute_bars:
        return None
    
    total_pv = 0.0
    total_volume = 0.0
    
    for bar in minute_bars:
        volume = bar.get('v', 0) or 0
        if volume > 0:
            price = typical_price(bar)
            total_pv += price * volume
            total_volume += volume
    
    return total_pv / total_volume if total_volume > 0 else None

def ema(series: List[float], period: int) -> Optional[float]:
    """Calculate Exponential Moving Average"""
    if not series or len(series) < period:
        return None
    
    # Filter out None values
    clean_series = [x for x in series if x is not None and not isnan(x)]
    if len(clean_series) < period:
        return None
    
    k = 2.0 / (period + 1)
    ema_value = clean_series[0]
    
    for price in clean_series[1:]:
        ema_value = price * k + ema_value * (1 - k)
    
    return ema_value

def rsi_wilder(closes: List[float], period: int = 14) -> Optional[float]:
    """
    Calculate RSI using Wilder's smoothing method
    """
    if not closes or len(closes) < period + 1:
        return None
    
    # Filter out None values
    clean_closes = [x for x in closes if x is not None and not isnan(x)]
    if len(clean_closes) < period + 1:
        return None
    
    gains = []
    losses = []
    
    # Calculate initial gains and losses
    for i in range(1, period + 1):
        change = clean_closes[i] - clean_closes[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
    
    # Initial averages
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    # Smooth subsequent periods
    for i in range(period + 1, len(clean_closes)):
        change = clean_closes[i] - clean_closes[i - 1]
        gain = max(change, 0)
        loss = max(-change, 0)
        
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def atr_percent(daily_bars: List[Dict[str, float]], period: int = 14) -> Optional[float]:
    """
    Calculate Average True Range as percentage of closing price
    daily_bars: List of dicts with keys 'h', 'l', 'c' (most recent last)
    """
    if not daily_bars or len(daily_bars) < period + 1:
        return None
    
    true_ranges = []
    prev_close = daily_bars[0]['c']
    
    for bar in daily_bars[1:]:
        high = bar['h']
        low = bar['l']
        close = bar['c']
        
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        
        true_range = max(tr1, tr2, tr3)
        true_ranges.append(true_range)
        prev_close = close
    
    if len(true_ranges) < period:
        return None
    
    # Calculate Wilder's smoothed ATR
    atr = sum(true_ranges[:period]) / period
    alpha = 1.0 / period
    
    for tr in true_ranges[period:]:
        atr = (1 - alpha) * atr + alpha * tr
    
    last_close = daily_bars[-1]['c']
    if last_close <= 0:
        return None
    
    return (atr / last_close) * 100.0

def sustained(mask: List[bool], window: int = 20, min_frac: float = 0.75) -> bool:
    """
    Check if a boolean condition is sustained over a time window
    
    Args:
        mask: List of boolean values (True/False conditions)
        window: Number of periods to check
        min_frac: Minimum fraction of periods that must be True
    """
    if len(mask) < window:
        return False
    
    # Check the most recent window
    recent_slice = mask[-window:]
    true_count = sum(recent_slice)
    
    return (true_count / window) >= min_frac

def relvol_series(cum_today: List[float], cum_ref: List[float]) -> List[float]:
    """
    Calculate time-aligned relative volume series
    
    Args:
        cum_today: Today's cumulative volume by minute
        cum_ref: Reference period cumulative volume by minute (30-day average)
    
    Returns:
        List of relative volume ratios
    """
    if not cum_today or not cum_ref:
        return []
    
    min_length = min(len(cum_today), len(cum_ref))
    relvol_ratios = []
    
    for i in range(min_length):
        today_vol = cum_today[i]
        ref_vol = cum_ref[i]
        
        if ref_vol > 0:
            ratio = today_vol / ref_vol
        else:
            ratio = 0.0
        
        relvol_ratios.append(ratio)
    
    return relvol_ratios

def bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Dict[str, Optional[float]]:
    """
    Calculate Bollinger Bands
    
    Returns:
        Dict with 'upper', 'middle', 'lower' bands
    """
    if not prices or len(prices) < period:
        return {'upper': None, 'middle': None, 'lower': None}
    
    # Calculate SMA (middle band)
    recent_prices = prices[-period:]
    sma = sum(recent_prices) / period
    
    # Calculate standard deviation
    variance = sum((p - sma) ** 2 for p in recent_prices) / period
    std = sqrt(variance)
    
    return {
        'upper': sma + (std_dev * std),
        'middle': sma,
        'lower': sma - (std_dev * std)
    }

def macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, Optional[float]]:
    """
    Calculate MACD (Moving Average Convergence Divergence)
    
    Returns:
        Dict with 'macd', 'signal', 'histogram' values
    """
    if not prices or len(prices) < slow:
        return {'macd': None, 'signal': None, 'histogram': None}
    
    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)
    
    if ema_fast is None or ema_slow is None:
        return {'macd': None, 'signal': None, 'histogram': None}
    
    macd_line = ema_fast - ema_slow
    
    # For signal line, we'd need to calculate EMA of MACD values
    # Simplified version returns just the MACD line
    return {
        'macd': macd_line,
        'signal': None,  # Would need historical MACD values
        'histogram': None
    }

def volume_profile(minute_bars: List[Dict[str, float]], price_levels: int = 20) -> Dict[float, float]:
    """
    Calculate volume profile - volume distribution by price level
    
    Returns:
        Dict mapping price levels to volume
    """
    if not minute_bars:
        return {}
    
    # Get price range
    all_prices = []
    for bar in minute_bars:
        all_prices.extend([bar['h'], bar['l'], bar['c']])
    
    if not all_prices:
        return {}
    
    min_price = min(all_prices)
    max_price = max(all_prices)
    
    if max_price == min_price:
        return {min_price: sum(bar.get('v', 0) for bar in minute_bars)}
    
    # Create price levels
    price_step = (max_price - min_price) / price_levels
    volume_by_level = {}
    
    for i in range(price_levels):
        level_price = min_price + (i * price_step)
        volume_by_level[level_price] = 0.0
    
    # Distribute volume to price levels
    for bar in minute_bars:
        volume = bar.get('v', 0)
        if volume > 0:
            # Use typical price to assign volume
            price = typical_price(bar)
            
            # Find closest level
            level_index = min(int((price - min_price) / price_step), price_levels - 1)
            level_price = min_price + (level_index * price_step)
            
            volume_by_level[level_price] += volume
    
    return volume_by_level

def momentum_oscillator(prices: List[float], period: int = 10) -> Optional[float]:
    """
    Calculate momentum oscillator (rate of change)
    """
    if not prices or len(prices) < period + 1:
        return None
    
    current_price = prices[-1]
    past_price = prices[-period - 1]
    
    if past_price == 0:
        return None
    
    return ((current_price - past_price) / past_price) * 100.0