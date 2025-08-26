from fastapi import APIRouter
from typing import List, Dict

router = APIRouter()

@router.get("/holdings")
async def get_holdings() -> List[Dict]:
    try:
        # Try existing portfolio service
        try:
            from backend.src.services.portfolio import get_current_holdings_usd
            holdings_dict = await get_current_holdings_usd()
            # Convert dict to list format for frontend
            return [{"symbol": symbol, "value": value} for symbol, value in holdings_dict.items()]
        except ImportError:
            pass
            
        # Try alternative portfolio service
        try:
            from backend.src.services.broker_alpaca import AlpacaBroker
            broker = AlpacaBroker()
            positions = await broker.get_positions()
            return positions or []
        except (ImportError, AttributeError):
            pass
            
        # Final fallback: empty list  
        return []
    except Exception:
        return []