#!/usr/bin/env python3
"""
Score normalization using z-scores for better differentiation
"""
import numpy as np
from typing import List, Dict, Any

# Scoring modules/components
MODULES = ('momentum', 'squeeze', 'catalyst', 'sentiment', 'options', 'technical')

def classify_stock(stock: Dict[str, Any]) -> tuple[str, str]:
    """
    Classify stock by sector and float bucket for peer comparison
    
    Returns:
        (sector, float_bucket) tuple for grouping
    """
    # Extract sector information
    sector = 'UNK'
    if hasattr(stock, 'sector'):
        sector = stock.sector or 'UNK'
    elif isinstance(stock, dict):
        sector = stock.get('sector', 'UNK')
        # Try to get from metadata
        meta = stock.get('meta', {})
        if not sector or sector == 'UNK':
            sector = meta.get('sector', meta.get('gics_sector', 'UNK'))
    
    # Extract float size for bucketing
    shares_outstanding = 0
    if hasattr(stock, 'shares_outstanding'):
        shares_outstanding = stock.shares_outstanding or 0
    elif isinstance(stock, dict):
        meta = stock.get('meta', {})
        shares_outstanding = meta.get('sharesOutstanding', meta.get('shares_outstanding', 0))
    
    # Float size buckets
    if shares_outstanding < 50_000_000:
        float_bucket = 'small'
    elif shares_outstanding < 200_000_000:
        float_bucket = 'medium'
    elif shares_outstanding < 1_000_000_000:
        float_bucket = 'large'
    else:
        float_bucket = 'mega'
    
    return (sector, float_bucket)

def group_zscores(stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculate z-scores for each scoring component within peer groups
    
    Args:
        stocks: List of stock dictionaries with 'feats' containing raw scores
        
    Returns:
        Same list with added z-score fields (z_momentum, z_squeeze, etc.)
    """
    if not stocks:
        return stocks
    
    # Group stocks by sector and float size
    buckets = {}
    for stock in stocks:
        group_key = classify_stock(stock)
        if group_key not in buckets:
            buckets[group_key] = []
        buckets[group_key].append(stock)
    
    # Calculate z-scores within each group
    for group_key, group_stocks in buckets.items():
        if len(group_stocks) < 2:
            # Not enough stocks for meaningful z-score, use raw values
            for stock in group_stocks:
                feats = stock.get('feats', {})
                for module in MODULES:
                    stock[f'z_{module}'] = feats.get(module, 0.0)
            continue
        
        # Calculate z-scores for each module
        for module in MODULES:
            # Extract raw values for this module
            values = []
            valid_count = 0
            for stock in group_stocks:
                feats = stock.get('feats', {})
                value = feats.get(module)
                if value is not None and value != 0:
                    values.append(value)
                    valid_count += 1
                else:
                    values.append(None)  # Mark as missing data
            
            # Check if we have enough valid data for meaningful z-scores
            if valid_count < max(3, len(group_stocks) * 0.3):  # Need at least 3 or 30% coverage
                # Insufficient data - mark all as None for down-weighting
                for stock in group_stocks:
                    stock[f'z_{module}'] = None
                continue
            
            # Calculate mean and standard deviation from valid values only
            valid_values = [v for v in values if v is not None]
            values_array = np.array(valid_values)
            mean_val = float(np.mean(values_array))
            std_val = float(np.std(values_array))
            
            # Avoid division by zero
            if std_val == 0 or np.isnan(std_val):
                std_val = 1.0
            
            # Assign z-scores - keep float precision, return None for missing data
            for i, stock in enumerate(group_stocks):
                raw_value = values[i]
                if raw_value is not None:
                    z_score = (raw_value - mean_val) / std_val
                    # Keep one decimal precision instead of rounding to int
                    stock[f'z_{module}'] = round(z_score, 1)
                else:
                    stock[f'z_{module}'] = None  # Missing data - let score.py down-weight
    
    return stocks

def calculate_coverage_multiplier(stock: Dict[str, Any]) -> float:
    """
    Calculate coverage multiplier based on data availability
    
    Stocks with more complete data get higher multipliers
    """
    feats = stock.get('feats', {})
    meta = stock.get('meta', {})
    
    # Track data availability
    data_points = 0
    total_possible = 0
    
    # Technical indicators (weight: 40%)
    tech_indicators = ['rsi', 'vwap', 'atr_pct', 'ema9', 'ema20']
    tech_available = sum(1 for indicator in tech_indicators if feats.get(indicator) is not None)
    data_points += tech_available * 0.4 / len(tech_indicators)
    total_possible += 0.4
    
    # Volume metrics (weight: 30%)
    volume_metrics = ['volume', 'rel_vol_30d', 'dollar_volume']
    volume_available = sum(1 for metric in volume_metrics 
                          if (feats.get(metric) is not None or meta.get(metric) is not None))
    data_points += volume_available * 0.3 / len(volume_metrics)
    total_possible += 0.3
    
    # Fundamental data (weight: 20%)
    fundamental_data = ['sharesOutstanding', 'marketCap', 'float']
    fundamental_available = sum(1 for item in fundamental_data if meta.get(item) is not None)
    data_points += fundamental_available * 0.2 / len(fundamental_data)
    total_possible += 0.2
    
    # Options/sentiment data (weight: 10%)
    options_data = ['call_put_ratio', 'iv_percentile', 'unusual_options']
    options_available = sum(1 for item in options_data if meta.get(item) is not None)
    data_points += options_available * 0.1 / len(options_data)
    total_possible += 0.1
    
    # Calculate coverage ratio
    if total_possible > 0:
        coverage_ratio = data_points / total_possible
    else:
        coverage_ratio = 0.5  # Default for stocks with no data
    
    # Convert to multiplier (0.7 to 1.3 range)
    multiplier = 0.7 + (coverage_ratio * 0.6)
    
    # Bonus for complete data
    if coverage_ratio >= 0.9:
        multiplier += 0.1
    
    return min(multiplier, 1.3)  # Cap at 1.3x

def add_sector_momentum_boost(stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Add sector momentum boost to stocks in hot sectors
    
    Identifies sectors with multiple strong performers and boosts all stocks in those sectors
    """
    if len(stocks) < 10:
        return stocks  # Not enough stocks for sector analysis
    
    # Group by sector and calculate average scores
    sector_scores = {}
    sector_counts = {}
    
    for stock in stocks:
        sector, _ = classify_stock(stock)
        
        # Calculate preliminary score for sector analysis
        feats = stock.get('feats', {})
        momentum_score = feats.get('momentum', 0.0)
        volume_score = feats.get('volume_momentum', 0.0)
        
        sector_score = (momentum_score + volume_score) / 2.0
        
        if sector not in sector_scores:
            sector_scores[sector] = []
            sector_counts[sector] = 0
        
        sector_scores[sector].append(sector_score)
        sector_counts[sector] += 1
    
    # Calculate sector averages and identify hot sectors
    hot_sectors = set()
    for sector, scores in sector_scores.items():
        if len(scores) >= 3:  # Need at least 3 stocks for reliable sector signal
            avg_score = np.mean(scores)
            if avg_score > np.percentile(list(np.concatenate(list(sector_scores.values()))), 75):
                hot_sectors.add(sector)
    
    # Apply sector momentum boost
    for stock in stocks:
        sector, _ = classify_stock(stock)
        if sector in hot_sectors:
            stock['sector_momentum_boost'] = 0.05  # 5% boost for hot sectors
        else:
            stock['sector_momentum_boost'] = 0.0
    
    return stocks

def normalize_scores(stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Complete normalization pipeline: z-scores + coverage + sector momentum
    """
    # Step 1: Calculate z-scores within peer groups
    stocks = group_zscores(stocks)
    
    # Step 2: Calculate coverage multipliers
    for stock in stocks:
        stock['coverage_mult'] = calculate_coverage_multiplier(stock)
    
    # Step 3: Add sector momentum boosts
    stocks = add_sector_momentum_boost(stocks)
    
    return stocks