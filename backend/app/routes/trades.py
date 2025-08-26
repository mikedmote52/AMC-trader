from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import structlog
import os
from prometheus_client import Counter
from app.services.execution import ExecutionService
from app.services.portfolio import PortfolioService

logger = structlog.get_logger()
router = APIRouter()

# Prometheus counter for guardrail blocks
GUARDRAIL_BLOCKS = Counter("amc_guardrail_blocks_total", "Trade blocks by guardrails", ["reason"])

def get_risk_settings():
    """Get risk management environment variables"""
    return {
        "live_trading": os.getenv("LIVE_TRADING", "0") == "1",
        "kill_switch": os.getenv("KILL_SWITCH", "1") == "1",
        "max_position_usd": float(os.getenv("MAX_POSITION_USD", "100")),
        "max_portfolio_allocation_pct": float(os.getenv("MAX_PORTFOLIO_ALLOCATION_PCT", "15"))
    }

async def check_risk_guardrails(symbol: str, side: str, quantity: int, price: float = None):
    """Check all risk guardrails before trade execution"""
    settings = get_risk_settings()
    
    # Kill switch check
    if settings["live_trading"] and settings["kill_switch"]:
        GUARDRAIL_BLOCKS.labels(reason="killswitch_engaged").inc()
        return {
            "blocked": True,
            "error": "killswitch_engaged",
            "message": "Trades disabled by KILL_SWITCH"
        }
    
    # Calculate notional value - use current market price if not provided
    if price is None:
        # For now, use a placeholder price - in production would fetch from market data
        price = 150.0  # Placeholder price
    
    notional = quantity * price
    
    # Position size check
    if notional > settings["max_position_usd"]:
        GUARDRAIL_BLOCKS.labels(reason="max_position_exceeded").inc()
        return {
            "blocked": True,
            "error": "max_position_exceeded", 
            "message": f"Position size ${notional:.2f} exceeds limit ${settings['max_position_usd']:.2f}"
        }
    
    # Portfolio allocation check (only for buy orders)
    if side.lower() == "buy":
        try:
            portfolio_service = PortfolioService()
            holdings = await portfolio_service.get_holdings()
            
            if "error" not in holdings:
                account = holdings.get("account", {})
                positions = holdings.get("positions", [])
                portfolio_value = account.get("portfolio_value", 0)
                
                # Find current position in this symbol
                current_position_value = 0
                for position in positions:
                    if position.get("symbol") == symbol:
                        current_position_value = abs(float(position.get("market_value", 0)))
                        break
                
                if portfolio_value > 0:
                    current_alloc = (current_position_value / portfolio_value) * 100
                    proposed_alloc = ((current_position_value + notional) / portfolio_value) * 100
                    
                    if proposed_alloc > settings["max_portfolio_allocation_pct"]:
                        GUARDRAIL_BLOCKS.labels(reason="max_allocation_exceeded").inc()
                        return {
                            "blocked": True,
                            "error": "max_allocation_exceeded",
                            "message": f"Proposed allocation {proposed_alloc:.1f}% exceeds limit {settings['max_portfolio_allocation_pct']:.1f}%"
                        }
        except Exception as e:
            logger.warning("Portfolio allocation check failed", error=str(e))
            # Don't block trade if allocation check fails
    
    return {"blocked": False}

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
        
        # Check risk guardrails
        risk_check = await check_risk_guardrails(
            sample_trade["symbol"], 
            sample_trade["side"], 
            sample_trade["quantity"]
        )
        
        if risk_check["blocked"]:
            logger.warning("Trade blocked by guardrails", 
                          symbol=sample_trade["symbol"],
                          reason=risk_check["error"])
            raise HTTPException(
                status_code=400,
                detail={
                    "error": risk_check["error"],
                    "message": risk_check["message"]
                }
            )
        
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
        
        # Check risk guardrails
        risk_check = await check_risk_guardrails(
            trade_request.symbol,
            trade_request.side, 
            trade_request.quantity,
            trade_request.limit_price
        )
        
        if risk_check["blocked"]:
            logger.warning("Custom trade blocked by guardrails",
                          symbol=trade_request.symbol,
                          reason=risk_check["error"])
            raise HTTPException(
                status_code=400,
                detail={
                    "error": risk_check["error"],
                    "message": risk_check["message"]
                }
            )
        
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