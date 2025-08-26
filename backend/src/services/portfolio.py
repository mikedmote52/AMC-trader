import os
import httpx
from typing import Dict

ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
ALPACA_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET = os.getenv("ALPACA_API_SECRET", "")

async def get_portfolio_equity_usd() -> float:
    """Get total portfolio equity in USD"""
    try:
        headers = {
            "APCA-API-KEY-ID": ALPACA_KEY,
            "APCA-API-SECRET-KEY": ALPACA_SECRET,
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient(base_url=ALPACA_BASE_URL, headers=headers, timeout=10.0) as client:
            r = await client.get("/v2/account")
            r.raise_for_status()
            account = r.json()
            return float(account.get("portfolio_value", 0))
    except Exception:
        return 0.0

async def get_current_holdings_usd() -> Dict[str, float]:
    """Get current holdings by symbol in USD"""
    try:
        headers = {
            "APCA-API-KEY-ID": ALPACA_KEY,
            "APCA-API-SECRET-KEY": ALPACA_SECRET,
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient(base_url=ALPACA_BASE_URL, headers=headers, timeout=10.0) as client:
            r = await client.get("/v2/positions")
            r.raise_for_status()
            positions = r.json()
            
            holdings = {}
            for position in positions:
                symbol = position.get("symbol")
                market_value = float(position.get("market_value", 0))
                if symbol and market_value != 0:
                    holdings[symbol] = abs(market_value)  # Use absolute value
            
            return holdings
    except Exception:
        return {}