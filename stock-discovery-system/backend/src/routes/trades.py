"""
Trades route - handles trade execution (shadow and live modes).
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Literal
from sqlalchemy.orm import Session
from datetime import datetime

from ..deps import get_db, get_http_client, HTTPClientWithRetry
from ..config import settings
from ..utils.logging import logger


router = APIRouter()


class Order(BaseModel):
    """Order model."""
    symbol: str
    side: Literal["buy", "sell"]
    qty: float
    order_type: Literal["market", "limit"] = "market"
    limit_price: Optional[float] = None


class ExecuteRequest(BaseModel):
    """Trade execution request."""
    mode: Literal["shadow", "live"]
    orders: Optional[List[Order]] = None


@router.post("/execute")
async def execute_trades(
    request: ExecuteRequest,
    db: Session = Depends(get_db),
    http_client: HTTPClientWithRetry = Depends(get_http_client)
) -> Dict[str, Any]:
    """
    Execute trades in shadow or live mode.
    Shadow mode: logs proposed trades without executing.
    Live mode: places actual orders through Alpaca.
    """
    logger.info(f"Trade execution requested in {request.mode} mode")
    
    results = []
    
    if request.mode == "shadow":
        # Shadow mode - just log the trades
        for order in (request.orders or []):
            trade_log = {
                "timestamp": datetime.utcnow().isoformat(),
                "symbol": order.symbol,
                "side": order.side,
                "qty": order.qty,
                "status": "shadow",
                "mode": "shadow",
                "reason": "Shadow mode execution"
            }
            results.append(trade_log)
            logger.info(f"Shadow trade logged: {trade_log}")
            
        return {
            "mode": "shadow",
            "trades": results,
            "message": "Shadow trades logged successfully"
        }
        
    else:
        # Live mode - would execute real trades
        # For safety, keeping this disabled initially
        return {
            "mode": "live",
            "trades": [],
            "message": "Live trading not yet enabled",
            "error": "Live trading requires additional setup and validation"
        }