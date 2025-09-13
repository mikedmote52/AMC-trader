"""
SPY constituent universe for discovery.
Top 100 S&P 500 stocks by market cap as of 2024.
Real symbols only - no mock data.
"""

SPY_UNIVERSE = [
    # Technology
    "AAPL", "MSFT", "NVDA", "GOOGL", "GOOG", "META", "TSM", "AVGO", "ORCL", "ADBE",
    "CRM", "ACN", "CSCO", "AMD", "INTC", "IBM", "QCOM", "TXN", "INTU", "NOW",
    
    # Healthcare
    "UNH", "JNJ", "LLY", "PFE", "ABBV", "MRK", "TMO", "ABT", "CVS", "DHR",
    "AMGN", "BMY", "GILD", "MDT", "ISRG", "VRTX", "REGN", "SYK", "ZTS", "BSX",
    
    # Financials
    "BRK.B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "AXP", "BLK",
    "SPGI", "C", "SCHW", "CB", "PGR", "CME", "AON", "ICE", "MMC", "USB",
    
    # Consumer
    "AMZN", "TSLA", "WMT", "HD", "DIS", "MCD", "NKE", "COST", "PEP", "KO",
    "PG", "VZ", "CMCSA", "T", "NFLX", "SBUX", "TGT", "LOW", "BKNG", "MDLZ",
    
    # Industrials
    "BA", "CAT", "GE", "HON", "UNP", "UPS", "RTX", "LMT", "DE", "MMM",
    "FDX", "NOC", "GD", "EMR", "ETN", "ITW", "CSX", "NSC", "WM", "PH",
    
    # Energy
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PXD", "VLO", "PSX", "OXY",
    
    # Materials & Others
    "LIN", "APD", "SHW", "FCX", "ECL", "NEM", "DD", "DOW", "PPG", "ALB"
]


def get_universe() -> list[str]:
    """Get the current trading universe."""
    return SPY_UNIVERSE.copy()


def get_sectors() -> dict[str, list[str]]:
    """Get symbols grouped by sector."""
    return {
        "Technology": SPY_UNIVERSE[0:20],
        "Healthcare": SPY_UNIVERSE[20:40],
        "Financials": SPY_UNIVERSE[40:60],
        "Consumer": SPY_UNIVERSE[60:80],
        "Industrials": SPY_UNIVERSE[80:100],
        "Energy": SPY_UNIVERSE[100:110],
        "Materials": SPY_UNIVERSE[110:120]
    }