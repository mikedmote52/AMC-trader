from fastapi import APIRouter
from typing import List, Dict
import json
from backend.src.shared.redis_client import get_redis_client

router = APIRouter()

def build_normalized_holding(pos: Dict, by_sym: Dict) -> Dict:
    """Build normalized fields using broker position data"""
    symbol = pos.get("symbol", "")
    
    # Ensure holdings map 1:1 from broker (no client recompute)
    qty = int(pos["qty"])
    last_price = float(pos.get("current_price") or pos.get("asset_price"))
    market_value = round(qty * last_price, 2)
    avg_entry_price = float(pos["avg_entry_price"])
    unrealized_pl = round((last_price - avg_entry_price) * qty, 2)
    unrealized_pl_pct = round((last_price / avg_entry_price - 1.0) if avg_entry_price else 0.0, 4)
    
    # Join discovery context from Redis
    holding = {
        "symbol": symbol,
        "qty": qty,
        "avg_entry_price": avg_entry_price,
        "last_price": last_price,
        "market_value": market_value,
        "unrealized_pl": unrealized_pl,
        "unrealized_pl_pct": unrealized_pl_pct
    }
    
    holding["thesis"] = by_sym.get(symbol, {}).get("thesis")
    holding["confidence"] = by_sym.get(symbol, {}).get("confidence") or by_sym.get(symbol, {}).get("score")
    holding["suggestion"] = (
        "increase" if (holding.get("confidence") or 0) >= 0.97
        else "reduce" if holding["unrealized_pl_pct"] < -0.05
        else "hold"
    )
    
    return holding

@router.get("/holdings")
async def get_holdings() -> Dict:
    try:
        positions = []
        
        # Join discovery context from Redis
        contenders = json.loads(get_redis_client().get("amc:discovery:contenders.latest") or "[]")
        by_sym = {c["symbol"]: c for c in contenders if isinstance(c, dict)}
        
        # Try existing portfolio service
        try:
            from backend.src.services.portfolio import get_current_holdings_usd
            holdings_dict = await get_current_holdings_usd()
            # Convert dict to position format
            for symbol, value in holdings_dict.items():
                positions.append({
                    "symbol": symbol,
                    "qty": 1,  # Default, may need to be fetched from broker
                    "avg_entry_price": value,
                    "current_price": value,
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
        
        # Build normalized holdings
        normalized_positions = []
        for pos in positions:
            try:
                normalized_pos = build_normalized_holding(pos, by_sym)
                normalized_positions.append(normalized_pos)
            except Exception:
                # Skip positions that can't be normalized
                continue
        
        # Return in format expected by frontend
        return {
            "success": True,
            "data": {
                "positions": normalized_positions
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

@router.get("/holdings/sanity")
async def holdings_sanity() -> Dict:
    """Per-symbol recompute and diff for holdings sanity check"""
    try:
        positions = []
        
        # Get broker positions
        try:
            from backend.src.services.broker_alpaca import AlpacaBroker
            broker = AlpacaBroker()
            raw_positions = await broker.get_positions()
            if raw_positions:
                positions = raw_positions
        except (ImportError, AttributeError):
            # Fallback to portfolio service
            try:
                from backend.src.services.portfolio import get_current_holdings_usd
                holdings_dict = await get_current_holdings_usd()
                for symbol, value in holdings_dict.items():
                    positions.append({
                        "symbol": symbol,
                        "qty": 1,
                        "avg_entry_price": value,
                        "current_price": value,
                    })
            except ImportError:
                pass
        
        # Sanity check: recompute vs broker values
        sanity_results = []
        for pos in positions:
            try:
                symbol = pos.get("symbol", "")
                broker_qty = int(pos["qty"])
                broker_price = float(pos.get("current_price") or pos.get("asset_price"))
                broker_avg_entry = float(pos["avg_entry_price"])
                broker_market_value = float(pos.get("market_value", 0))
                broker_unrealized_pl = float(pos.get("unrealized_pl", 0))
                
                # Recompute
                recomputed_market_value = round(broker_qty * broker_price, 2)
                recomputed_unrealized_pl = round((broker_price - broker_avg_entry) * broker_qty, 2)
                
                # Calculate differences
                market_value_diff = abs(broker_market_value - recomputed_market_value)
                unrealized_pl_diff = abs(broker_unrealized_pl - recomputed_unrealized_pl)
                
                sanity_results.append({
                    "symbol": symbol,
                    "broker": {
                        "market_value": broker_market_value,
                        "unrealized_pl": broker_unrealized_pl
                    },
                    "recomputed": {
                        "market_value": recomputed_market_value,
                        "unrealized_pl": recomputed_unrealized_pl
                    },
                    "diff": {
                        "market_value": market_value_diff,
                        "unrealized_pl": unrealized_pl_diff
                    },
                    "sanity_ok": market_value_diff < 0.01 and unrealized_pl_diff < 0.01
                })
                
            except Exception as e:
                sanity_results.append({
                    "symbol": pos.get("symbol", "unknown"),
                    "error": str(e)
                })
        
        return {
            "success": True,
            "data": {
                "sanity_checks": sanity_results
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {
                "sanity_checks": []
            }
        }