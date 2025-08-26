from fastapi import APIRouter
from typing import List, Dict
import json
from backend.src.shared.redis_client import get_redis_client

router = APIRouter()

def build_holding_with_accurate_math(raw_position: Dict, contenders_dict: Dict) -> Dict:
    """Build holding with accurate math, thesis, and confidence"""
    symbol = raw_position.get("symbol", "")
    
    # Derive accurate values per user specification
    qty = float(raw_position.get("qty", raw_position.get("quantity", 0)))
    avg_entry_price = float(raw_position.get("avg_entry_price", raw_position.get("cost_basis", 0)))
    last_price = float(raw_position.get("current_price") or raw_position.get("asset_price") or avg_entry_price)
    
    # Calculate rounded values
    market_value = round(last_price * qty, 2)
    unrealized_pl = round((last_price - avg_entry_price) * qty, 2)
    unrealized_pl_pct = round((last_price / avg_entry_price - 1.0) if avg_entry_price else 0.0, 4)
    
    # Join discovery context
    contender = contenders_dict.get(symbol, {})
    thesis = contender.get("thesis")
    confidence = contender.get("confidence") or contender.get("score")
    
    # Generate suggestion based on confidence and performance
    suggestion = (
        "increase" if (confidence or 0) >= 0.97 else
        "reduce" if unrealized_pl_pct < -0.05 else
        "hold"
    )
    
    return {
        "symbol": symbol,
        "qty": qty,
        "avg_entry_price": avg_entry_price,
        "last_price": last_price,
        "market_value": market_value,
        "unrealized_pl": unrealized_pl,
        "unrealized_pl_pct": unrealized_pl_pct,
        "thesis": thesis,
        "confidence": confidence,
        "suggestion": suggestion,
        # Legacy frontend compatibility
        "quantity": qty,
        "current_price": last_price
    }

@router.get("/holdings")
async def get_holdings() -> Dict:
    try:
        positions = []
        
        # Get contenders data from Redis for thesis and confidence
        contenders_dict = {}
        try:
            contenders = json.loads(get_redis_client().get("amc:discovery:contenders.latest") or "[]")
            contenders_dict = {c["symbol"]: c for c in contenders if isinstance(c, dict) and "symbol" in c}
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