"""
Holdings route - retrieves current positions from Alpaca.
"""
from fastapi import APIRouter, Depends
from typing import List, Dict, Any

from ..deps import get_http_client, HTTPClientWithRetry
from ..config import settings
from ..utils.logging import logger
from ..utils.errors import HTTPError, TimeoutError


router = APIRouter()


@router.get("/")
async def get_holdings(
    http_client: HTTPClientWithRetry = Depends(get_http_client)
) -> Dict[str, Any]:
    """Get current holdings from Alpaca."""
    try:
        # Get account info
        account_url = f"{settings.alpaca_base_url}/v2/account"
        headers = {
            "APCA-API-KEY-ID": settings.alpaca_api_key,
            "APCA-API-SECRET-KEY": settings.alpaca_api_secret
        }
        
        account_response = await http_client.get(account_url, headers=headers)
        account_data = account_response.json()
        
        # Get positions
        positions_url = f"{settings.alpaca_base_url}/v2/positions"
        positions_response = await http_client.get(positions_url, headers=headers)
        positions_data = positions_response.json()
        
        # Format response
        holdings = {
            "cash": float(account_data.get("cash", 0)),
            "buying_power": float(account_data.get("buying_power", 0)),
            "portfolio_value": float(account_data.get("portfolio_value", 0)),
            "positions": [
                {
                    "symbol": pos.get("symbol"),
                    "qty": float(pos.get("qty", 0)),
                    "market_value": float(pos.get("market_value", 0)),
                    "cost_basis": float(pos.get("cost_basis", 0)),
                    "unrealized_pl": float(pos.get("unrealized_pl", 0)),
                    "unrealized_plpc": float(pos.get("unrealized_plpc", 0)),
                    "current_price": float(pos.get("current_price", 0))
                }
                for pos in positions_data
            ]
        }
        
        logger.info(f"Retrieved {len(holdings['positions'])} positions")
        return holdings
        
    except Exception as e:
        logger.error(f"Failed to get holdings: {e}")
        raise HTTPError(f"Failed to retrieve holdings: {str(e)}")