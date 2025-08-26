from fastapi import APIRouter
from typing import List, Dict

router = APIRouter()

def adapt_holding_for_frontend(raw_position: Dict) -> Dict:
    """Adapt backend position data to frontend expected format"""
    adapted = {
        # Frontend expected fields
        "symbol": raw_position.get("symbol", ""),
        "quantity": raw_position.get("qty", raw_position.get("quantity", 0)),
        "current_price": float(raw_position.get("market_value", 0)) / max(float(raw_position.get("qty", 1)), 1) if raw_position.get("market_value") else raw_position.get("current_price", 0),
        "avg_entry_price": raw_position.get("avg_entry_price", raw_position.get("cost_basis", 0)),
        "market_value": raw_position.get("market_value", 0),
        "unrealized_pl": raw_position.get("unrealized_pl", raw_position.get("unrealized_pnl", 0)),
        "unrealized_plpc": raw_position.get("unrealized_plpc", raw_position.get("unrealized_pnl_pct", 0)),
        # Keep original data for debugging
        "_raw": raw_position
    }
    return adapted

@router.get("/holdings")
async def get_holdings() -> Dict:
    try:
        positions = []
        
        # Try existing portfolio service
        try:
            from backend.src.services.portfolio import get_current_holdings_usd
            holdings_dict = await get_current_holdings_usd()
            # Convert dict to position format
            for symbol, value in holdings_dict.items():
                positions.append({
                    "symbol": symbol,
                    "quantity": 1,  # Default, may need to be fetched from broker
                    "market_value": value,
                    "current_price": value,
                    "avg_entry_price": value,
                    "unrealized_pl": 0,
                    "unrealized_plpc": 0
                })
        except ImportError:
            pass
            
        # Try alternative portfolio service
        if not positions:
            try:
                from backend.src.services.broker_alpaca import AlpacaBroker
                broker = AlpacaBroker()
                raw_positions = await broker.get_positions()
                if raw_positions:
                    positions = raw_positions
            except (ImportError, AttributeError):
                pass
        
        # Adapt positions for frontend
        adapted_positions = [adapt_holding_for_frontend(pos) for pos in positions]
        
        # Return in format expected by frontend: { data: { positions: [...] } }
        return {
            "success": True,
            "data": {
                "positions": adapted_positions
            }
        }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {
                "positions": []
            }
        }