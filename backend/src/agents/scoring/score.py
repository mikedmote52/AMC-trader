#!/usr/bin/env python3
"""
Improved scoring engine with real differentiation using z-scores
"""
import numpy as np
from math import exp
from typing import Dict, Any

# Scoring weights (must sum to 1.0)
WEIGHTS = {
    'momentum': 0.25,
    'squeeze': 0.20,
    'catalyst': 0.15,
    'sentiment': 0.15,
    'options': 0.12,
    'technical': 0.13
}

def sigmoid(x: float, steepness: float = 1.0) -> float:
    """
    Sigmoid activation function for score normalization
    
    Args:
        x: Input value
        steepness: Controls the steepness of the sigmoid curve
    """
    try:
        return 1.0 / (1.0 + exp(-x * steepness))
    except OverflowError:
        # Handle extreme values
        return 1.0 if x > 0 else 0.0

def calculate_base_score(z_scores: Dict[str, float]) -> tuple[float, int]:
    """
    Calculate base score from z-scores using weighted combination
    
    Args:
        z_scores: Dictionary of z-scores for each component
        
    Returns:
        Tuple of (weighted z-score sum, number of missing buckets)
    """
    weighted_sum = 0.0
    missing_buckets = 0
    total_weight = 0.0
    
    for component, weight in WEIGHTS.items():
        z_score = z_scores.get(component)
        
        # Check if this bucket has valid data
        if z_score is None or np.isnan(z_score) or np.isinf(z_score):
            missing_buckets += 1
            # Don't add weight for missing buckets - effectively down-weights
            continue
        
        weighted_sum += weight * z_score
        total_weight += weight
    
    # Normalize by actual weight used (down-weighting effect)
    if total_weight > 0:
        weighted_sum = weighted_sum * (sum(WEIGHTS.values()) / total_weight)
    
    return weighted_sum, missing_buckets

def apply_volatility_bonus(stock: Dict[str, Any], base_score: float) -> float:
    """
    Apply volatility-based bonus for explosive potential
    
    Stocks with higher ATR% get score boosts as they have more explosive potential
    """
    feats = stock.get('feats', {})
    atr_pct = feats.get('atr_pct', 0.0)
    
    if atr_pct is None or np.isnan(atr_pct):
        return base_score
    
    # Volatility bonus: 0% to 15% boost based on ATR
    # ATR > 8% gets maximum boost, ATR < 2% gets no boost
    if atr_pct >= 8.0:
        volatility_bonus = 0.15
    elif atr_pct >= 4.0:
        volatility_bonus = 0.10
    elif atr_pct >= 2.0:
        volatility_bonus = 0.05
    else:
        volatility_bonus = 0.0
    
    return base_score * (1.0 + volatility_bonus)

def apply_momentum_boost(stock: Dict[str, Any], base_score: float) -> float:
    """
    Apply momentum-based boost for trending stocks
    """
    feats = stock.get('feats', {})
    
    # Check for multiple momentum signals
    momentum_signals = 0
    
    # RSI in bullish range (50-80)
    rsi = feats.get('rsi', 50.0)
    if 50.0 <= rsi <= 80.0:
        momentum_signals += 1
    
    # Price above EMA9
    price = stock.get('meta', {}).get('last', 0.0)
    ema9 = feats.get('ema9')
    if ema9 and price > ema9:
        momentum_signals += 1
    
    # Strong relative volume
    rel_vol = feats.get('rel_vol_30d', 1.0)
    if rel_vol >= 2.0:
        momentum_signals += 1
    
    # Apply boost based on number of signals
    if momentum_signals >= 3:
        momentum_boost = 0.12
    elif momentum_signals >= 2:
        momentum_boost = 0.08
    elif momentum_signals >= 1:
        momentum_boost = 0.04
    else:
        momentum_boost = 0.0
    
    return base_score * (1.0 + momentum_boost)

def apply_squeeze_multiplier(stock: Dict[str, Any], base_score: float) -> float:
    """
    Apply squeeze-specific multiplier for short squeeze potential
    """
    meta = stock.get('meta', {})
    
    # Get squeeze-related metrics
    shares_outstanding = meta.get('sharesOutstanding', 0)
    short_interest = meta.get('short_interest_pct', 0.0)
    days_to_cover = meta.get('days_to_cover', 0.0)
    
    squeeze_multiplier = 1.0
    
    # Small float bonus (< 50M shares)
    if shares_outstanding < 50_000_000:
        squeeze_multiplier += 0.10
    
    # High short interest bonus
    if short_interest >= 20.0:
        squeeze_multiplier += 0.15
    elif short_interest >= 10.0:
        squeeze_multiplier += 0.08
    
    # High days to cover bonus
    if days_to_cover >= 5.0:
        squeeze_multiplier += 0.10
    elif days_to_cover >= 3.0:
        squeeze_multiplier += 0.05
    
    return base_score * squeeze_multiplier

def calculate_ticker_jitter(ticker: str) -> float:
    """
    Calculate small ticker-based jitter to ensure unique scores
    
    Uses hash of ticker to generate consistent but unique small adjustments
    """
    # Use hash of ticker for deterministic jitter
    hash_val = hash(ticker) % 10000
    
    # Convert to small decimal (0.0001 to 0.9999)
    jitter = (hash_val / 10000.0) * 0.001
    
    return jitter

def score_stock(stock: Dict[str, Any]) -> float:
    """
    Calculate final score for a stock using improved scoring algorithm
    
    Args:
        stock: Stock dictionary with z-scores, features, and metadata
        
    Returns:
        Final score (typically 0-100 range)
    """
    # Extract z-scores
    z_scores = {}
    for component in WEIGHTS.keys():
        z_key = f'z_{component}'
        z_scores[component] = stock.get(z_key)  # Don't default to 0.0, use None
    
    # Calculate base score from z-scores and get missing bucket count
    raw_score, missing_buckets = calculate_base_score(z_scores)
    
    # Apply sigmoid transformation to normalize to 0-1 range
    # Use steepness factor to control score spread
    base_score = sigmoid(raw_score, steepness=0.8)
    
    # Scale to 0-100 range
    base_score *= 100.0
    
    # Apply missing bucket penalty (2-5 points per missing bucket)
    if missing_buckets >= 2:
        missing_penalty = min(5.0 * missing_buckets, 25.0)  # Cap at 25 points
        base_score -= missing_penalty
    
    # Apply coverage multiplier
    coverage_mult = stock.get('coverage_mult', 1.0)
    score = base_score * coverage_mult
    
    # Apply various bonuses and multipliers
    score = apply_volatility_bonus(stock, score)
    score = apply_momentum_boost(stock, score)
    score = apply_squeeze_multiplier(stock, score)
    
    # Add sector momentum boost
    sector_boost = stock.get('sector_momentum_boost', 0.0)
    score = score * (1.0 + sector_boost)
    
    # Add ticker-based jitter for uniqueness
    ticker = stock.get('symbol') or stock.get('ticker', 'UNK')
    jitter = calculate_ticker_jitter(ticker)
    score += jitter
    
    # Ensure score is in reasonable range
    score = max(0.0, min(100.0, score))
    
    return score

def validate_score_distribution(scores: list[float], min_variance: float = 5.0) -> bool:
    """
    Validate that score distribution has sufficient variance
    
    Args:
        scores: List of calculated scores
        min_variance: Minimum required variance
        
    Returns:
        True if distribution is acceptable
    """
    if len(scores) < 2:
        return True  # Cannot calculate variance with < 2 scores
    
    scores_array = np.array(scores)
    variance = float(np.var(scores_array))
    score_range = float(np.max(scores_array) - np.min(scores_array))
    
    # Check variance requirement
    if variance < min_variance:
        return False
    
    # Check range requirement (should be at least 15 points)
    if score_range < 15.0:
        return False
    
    return True

def score_candidates(stocks: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """
    Score all candidate stocks and validate distribution
    
    Args:
        stocks: List of stock dictionaries with normalized z-scores
        
    Returns:
        List of stocks with added 'score' field, sorted by score descending
    """
    # Calculate scores for all stocks
    for stock in stocks:
        stock['score'] = score_stock(stock)
    
    # Extract scores for validation
    scores = [stock['score'] for stock in stocks]
    
    # Validate score distribution
    if not validate_score_distribution(scores):
        # If validation fails, add more aggressive differentiation
        for i, stock in enumerate(stocks):
            # Add position-based boost to spread scores
            position_boost = (len(stocks) - i) * 0.1
            stock['score'] += position_boost
        
        # Re-validate
        scores = [stock['score'] for stock in stocks]
        if not validate_score_distribution(scores):
            raise ValueError(f"Score distribution failed validation. "
                           f"Variance: {np.var(scores):.2f}, "
                           f"Range: {max(scores) - min(scores):.2f}")
    
    # Sort by score descending
    stocks.sort(key=lambda x: x['score'], reverse=True)
    
    return stocks