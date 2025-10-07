"""
AMC-TRADER Risk Management Module
Centralized stop-loss and risk calculation
Single source of truth for frontend and backend
"""
from typing import Dict, Optional


def compute_stop_loss(
    price: float,
    explosion_probability: float,
    rvol: float,
    atr_pct: Optional[float] = None
) -> Dict[str, float]:
    """
    Calculate smart stop-loss based on stock characteristics.

    Logic:
    - High explosion probability + high RVOL = tighter stop (less risk)
    - Low explosion probability + high RVOL = wider stop (more volatile)

    Args:
        price: Current stock price
        explosion_probability: V2 explosion probability score (0-100)
        rvol: Relative volume (e.g., 1.5 = 1.5x average)
        atr_pct: Optional ATR percentage for additional context

    Returns:
        {
            'stop_loss_pct': percentage stop (e.g., 0.05 = 5%),
            'stop_price': absolute stop price,
            'take_profit_pct': percentage target (2x the stop),
            'take_profit_price': absolute target price,
            'risk_reward_ratio': ratio (typically 1:2)
        }
    """
    # Base stop-loss: 5-15% depending on confidence
    # Lower explosion prob = wider stop (more risk)
    # Higher RVOL = tighter stop (momentum stock, move fast)

    base_stop_pct = 10.0  # 10% default

    # Adjust for explosion probability
    if explosion_probability >= 70:
        base_stop_pct = 5.0  # Tight stop for high-confidence trades
    elif explosion_probability >= 60:
        base_stop_pct = 7.0  # Medium stop
    elif explosion_probability >= 50:
        base_stop_pct = 10.0  # Standard stop
    else:
        base_stop_pct = 12.0  # Wider stop for lower confidence

    # Adjust for RVOL (high volume = tighter stops)
    if rvol >= 10:
        base_stop_pct *= 0.8  # 20% tighter
    elif rvol >= 5:
        base_stop_pct *= 0.9  # 10% tighter
    elif rvol >= 3:
        base_stop_pct *= 0.95  # 5% tighter

    # Optional ATR adjustment (if volatility is abnormally high)
    if atr_pct and atr_pct > 0.15:  # 15%+ daily volatility
        base_stop_pct *= 1.1  # Widen stop by 10%

    # Round to 1 decimal
    stop_loss_pct = round(base_stop_pct / 100, 3)  # Convert to decimal (e.g., 0.05)

    # Calculate absolute prices
    stop_price = round(price * (1 - stop_loss_pct), 2)

    # Take profit: 2x the stop-loss (risk/reward ratio of 1:2)
    take_profit_pct = round(stop_loss_pct * 2, 3)
    take_profit_price = round(price * (1 + take_profit_pct), 2)

    # Calculate potential gain/loss
    potential_loss = round(price * stop_loss_pct, 2)
    potential_gain = round(price * take_profit_pct, 2)

    return {
        'stop_loss_pct': stop_loss_pct,
        'stop_price': stop_price,
        'take_profit_pct': take_profit_pct,
        'take_profit_price': take_profit_price,
        'risk_reward_ratio': round(take_profit_pct / stop_loss_pct, 1),
        'potential_loss': potential_loss,
        'potential_gain': potential_gain
    }


def validate_bracket_order(
    price: float,
    stop_price: float,
    take_profit_price: float
) -> Dict[str, bool]:
    """
    Validate bracket order parameters to prevent invalid orders.

    Returns:
        {
            'valid': True/False,
            'errors': ['error message 1', ...],
            'warnings': ['warning message 1', ...]
        }
    """
    errors = []
    warnings = []

    # Stop-loss must be below current price
    if stop_price >= price:
        errors.append(f"Stop price ${stop_price} must be below current price ${price}")

    # Take-profit must be above current price
    if take_profit_price <= price:
        errors.append(f"Take profit ${take_profit_price} must be above current price ${price}")

    # Sanity checks
    stop_loss_pct = (price - stop_price) / price
    take_profit_pct = (take_profit_price - price) / price

    if stop_loss_pct > 0.25:  # 25% stop is very wide
        warnings.append(f"Stop-loss of {stop_loss_pct*100:.1f}% is unusually wide")

    if stop_loss_pct < 0.02:  # 2% stop is very tight
        warnings.append(f"Stop-loss of {stop_loss_pct*100:.1f}% is very tight")

    if take_profit_pct > 0.50:  # 50% target is ambitious
        warnings.append(f"Take-profit of {take_profit_pct*100:.1f}% is ambitious")

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }
