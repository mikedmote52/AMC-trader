from fastapi import APIRouter
from typing import List, Dict
import json
from backend.src.shared.redis_client import get_redis_client

router = APIRouter()

def get_holding_recommendation(symbol: str, unrealized_pl_pct: float, contenders_dict: Dict) -> Dict:
    """Generate recommendation based on contenders and performance"""
    if symbol in contenders_dict:
        score = contenders_dict[symbol].get("score", 0)
        thesis = contenders_dict[symbol].get("thesis", "")
        
        if score >= 0.97:
            return {"suggestion": "increase", "thesis": thesis}
        elif score >= 0.94:
            return {"suggestion": "hold", "thesis": thesis}
    
    if symbol not in contenders_dict and unrealized_pl_pct < -0.05:
        return {"suggestion": "reduce", "thesis": "Position underperforming and not in current contenders"}
    
    return {"suggestion": "hold", "thesis": ""}

def build_holding_with_accurate_math(raw_position: Dict, contenders_dict: Dict) -> Dict:
    """Build holding with accurate math and recommendation"""
    symbol = raw_position.get("symbol", "")
    qty = float(raw_position.get("qty", raw_position.get("quantity", 0)))
    avg_entry_price = float(raw_position.get("avg_entry_price", raw_position.get("cost_basis", 0)))
    last_price = float(raw_position.get("last_price", raw_position.get("current_price", 0)))
    
    # Calculate accurate values
    market_value = qty * last_price
    unrealized_pl = (last_price - avg_entry_price) * qty
    unrealized_pl_pct = (last_price / avg_entry_price - 1) if avg_entry_price > 0 else 0
    
    # Get recommendation
    recommendation = get_holding_recommendation(symbol, unrealized_pl_pct, contenders_dict)
    
    return {
        "symbol": symbol,
        "qty": qty,
        "avg_entry_price": avg_entry_price,
        "last_price": last_price,
        "market_value": market_value,
        "unrealized_pl": unrealized_pl,
        "unrealized_pl_pct": unrealized_pl_pct,
        "suggestion": recommendation["suggestion"],
        "thesis": recommendation["thesis"],
        # Legacy frontend compatibility
        "quantity": qty,
        "current_price": last_price
    }

@router.get("/holdings")
async def get_holdings() -> Dict:
    try:
        positions = []
        
        # Get contenders data from Redis for recommendations
        contenders_dict = {}
        try:
            redis_client = get_redis_client()
            cached_data = redis_client.get("amc:discovery:contenders.latest")
            if cached_data:
                contenders_list = json.loads(cached_data)
                contenders_dict = {c.get("symbol", ""): c for c in contenders_list if isinstance(c, dict)}
        except Exception:
            pass
        
        # Try existing portfolio service
        try:
            from backend.src.services.portfolio import get_current_holdings_usd
            holdings_dict = await get_current_holdings_usd()
            # Convert dict to position format
            for symbol, value in holdings_dict.items():
                positions.append({
                    "symbol": symbol,
                    "qty": 1,  # Default, may need to be fetched from broker
                    "market_value": value,
                    "last_price": value,
                    "avg_entry_price": value,
                    "unrealized_pl": 0,
                    "unrealized_pl_pct": 0
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
        
        # Build holdings with accurate math and recommendations
        enriched_positions = []
        for pos in positions:
            try:
                enriched_pos = build_holding_with_accurate_math(pos, contenders_dict)
                enriched_positions.append(enriched_pos)
            except Exception:
                # Fallback to original position if enrichment fails
                enriched_positions.append(pos)
        
        # Return in format expected by frontend
        return {
            "success": True,
            "data": {
                "positions": enriched_positions
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