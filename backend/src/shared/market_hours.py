from datetime import datetime, time
import pytz

def is_market_hours():
    """
    Check if current time is during market hours (9:30 AM - 4:00 PM ET)
    
    Returns:
        bool: True if market is open, False otherwise
    """
    et = pytz.timezone('US/Eastern')
    now = datetime.now(et)
    
    # Market is closed on weekends
    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    market_open = time(9, 30)  # 9:30 AM
    market_close = time(16, 0)  # 4:00 PM
    current_time = now.time()
    
    return market_open <= current_time <= market_close

def get_market_status():
    """
    Get detailed market status information
    
    Returns:
        dict: Market status details
    """
    et = pytz.timezone('US/Eastern')
    now = datetime.now(et)
    
    return {
        'is_open': is_market_hours(),
        'current_time_et': now.strftime('%Y-%m-%d %H:%M:%S %Z'),
        'is_weekend': now.weekday() >= 5,
        'day_of_week': now.strftime('%A')
    }