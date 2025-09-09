"""
AMC-TRADER Discovery System Constants
Single source of truth for filters, cache keys, and configuration
"""
import os

# Coverage invariant - system must scan at least this many stocks
UNIVERSE_MIN_EXPECTED = int(os.getenv("BMS_UNIVERSE_MIN_EXPECTED", "4500"))

# Business filters for stock selection
PRICE_MIN = float(os.getenv("BMS_PRICE_MIN", "0.50"))
PRICE_MAX = float(os.getenv("BMS_PRICE_MAX", "100.0"))     # Critical: <$100 rule
MIN_DOLLAR_VOL_M = float(os.getenv("BMS_MIN_DOLLAR_VOLUME_M", "5.0"))  # $5M minimum liquidity

# Exclusions - funds, leveraged products, preferred shares
EXCLUDE_TYPES = {"ETF", "ETN", "FUND", "MUTUAL_FUND", "PREFERRED", "RIGHT", "WARRANT", "TRUST", "INDEX"}
EXCLUDE_SYMBOL_PATTERNS = [
    # Leveraged ETFs
    "SQQQ", "TQQQ", "UVXY", "SVIX", "TSLQ", "LABD", "DRIP", "QID",
    # Common fund patterns
    "BKLN", "PGX", "EWH", "SPY", "QQQ", "IWM", "VTI", "VOO",
    # Options-related
    "SPXL", "SPXS", "TLT", "GLD", "SLV"
]

# Cache and queue configuration
DISCOVERY_QUEUE = os.getenv("DISCOVERY_QUEUE", "amc_discovery")
CACHE_KEY_CONTENDERS = os.getenv("CACHE_KEY_CONTENDERS", "amc:discovery:candidates:v2")
CACHE_KEY_STATUS = os.getenv("CACHE_KEY_STATUS", "amc:discovery:status:v2")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "600"))  # 10 minutes

# Job processing configuration
JOB_TIMEOUT_SECONDS = int(os.getenv("JOB_TIMEOUT_SECONDS", "900"))  # 15 minutes max
RESULT_TTL_SECONDS = int(os.getenv("RESULT_TTL_SECONDS", "3600"))  # Keep results 1 hour

# Performance configuration
CONCURRENCY = int(os.getenv("BMS_CONCURRENCY", "8"))
RATE_LIMIT_PER_SEC = int(os.getenv("BMS_RATE_LIMIT_PER_SEC", "5"))
EARLY_STOP_SCAN = int(os.getenv("BMS_EARLY_STOP_SCAN", "100000"))  # Effectively disabled

# Scoring thresholds (from existing system)
TRADE_READY_THRESHOLD = float(os.getenv("BMS_TRADE_READY_THRESHOLD", "65.0"))
MONITOR_THRESHOLD = float(os.getenv("BMS_MONITOR_THRESHOLD", "45.0"))

# API configuration
DEFAULT_LIMIT = int(os.getenv("BMS_DEFAULT_LIMIT", "50"))
MAX_LIMIT = int(os.getenv("BMS_MAX_LIMIT", "500"))

# Polygon API configuration  
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
POLYGON_TIMEOUT_SECONDS = int(os.getenv("POLYGON_TIMEOUT_SECONDS", "30"))
POLYGON_MAX_RETRIES = int(os.getenv("POLYGON_MAX_RETRIES", "3"))

def get_trading_date():
    """Get the most recent trading date for data requests"""
    from datetime import datetime, timedelta
    today = datetime.now()
    
    # For weekends and Monday, go back to previous Friday
    if today.weekday() == 6:  # Sunday
        days_back = 2
    elif today.weekday() == 0:  # Monday  
        days_back = 3
    else:
        days_back = 1  # Use previous day
    
    return (today - timedelta(days=days_back)).strftime('%Y-%m-%d')

def is_fund_symbol(symbol: str) -> bool:
    """Check if symbol appears to be a fund/ETF"""
    symbol_upper = symbol.upper()
    return any(pattern in symbol_upper for pattern in EXCLUDE_SYMBOL_PATTERNS)

def validate_environment():
    """Validate required environment variables"""
    required_vars = ['POLYGON_API_KEY', 'REDIS_URL']
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing required environment variables: {missing}")
    return True