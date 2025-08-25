from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import structlog
from app.services.execution import ExecutionService

logger = structlog.get_logger()
router = APIRouter()

class TradeRequest(BaseModel):
    mode: str  # "shadow" or "live"
    symbol: Optional[str] = None
    side: Optional[str] = None  # "buy" or "sell"
    quantity: Optional[int] = None
    order_type: Optional[str] = "market"
    limit_price: Optional[float] = None

class TradeExecuteRequest(BaseModel):
    mode: str  # "shadow" or "live"

@router.post("/trades/execute")
async def execute_trades(request: TradeExecuteRequest):
    """
    Execute trades - accepts {"mode":"shadow"|"live"} and logs orders
    """
    try:
        execution_service = ExecutionService()
        
        # Validate mode
        if request.mode not in ["shadow", "live"]:
            logger.error("Invalid execution mode", mode=request.mode)
            return {
                "success": False,
                "error": f"Invalid mode: {request.mode}. Must be 'shadow' or 'live'."
            }
        
        # For this endpoint, we'll execute sample trades based on top recommendations
        # In production, this might take specific trade orders as input
        
        logger.info("Trade execution requested", mode=request.mode)
        
        # Sample trade execution - in production this would be based on actual signals
        sample_trade = {
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 10,
            "order_type": "market"
        }
        
        result = await execution_service.execute_trade(sample_trade, request.mode)
        
        return {
            "success": True,
            "mode": request.mode,
            "execution_result": result
        }
        
    except Exception as e:
        logger.error("Trade execution endpoint error", error=str(e))
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/trades/custom")
async def execute_custom_trade(trade_request: TradeRequest):
    """
    Execute a custom trade with specific parameters
    """
    try:
        execution_service = ExecutionService()
        
        # Validate required fields
        if not all([trade_request.symbol, trade_request.side, trade_request.quantity]):
            return {
                "success": False,
                "error": "Missing required fields: symbol, side, quantity"
            }
        
        trade_data = {
            "symbol": trade_request.symbol,
            "side": trade_request.side,
            "quantity": trade_request.quantity,
            "order_type": trade_request.order_type
        }
        
        if trade_request.limit_price:
            trade_data["limit_price"] = trade_request.limit_price
        
        result = await execution_service.execute_trade(trade_data, trade_request.mode)
        
        return {
            "success": True,
            "mode": trade_request.mode,
            "execution_result": result
        }
        
    except Exception as e:
        logger.error("Custom trade execution error", error=str(e))
        return {
            "success": False,
            "error": str(e)
        }