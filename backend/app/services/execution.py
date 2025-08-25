import alpaca_trade_api as tradeapi
from typing import Dict, Optional
import structlog
from app.config import settings
from app.models import Trade
from app.deps import get_db
from datetime import datetime

logger = structlog.get_logger()

class ExecutionService:
    def __init__(self):
        self.alpaca_api = tradeapi.REST(
            settings.alpaca_api_key,
            settings.alpaca_secret_key,
            settings.alpaca_base_url
        )
    
    async def execute_trade(self, trade_data: Dict, mode: str = "shadow") -> Dict:
        """Execute a trade order"""
        try:
            symbol = trade_data["symbol"]
            side = trade_data["side"]  # buy or sell
            quantity = trade_data["quantity"]
            order_type = trade_data.get("order_type", "market")
            
            logger.info("Processing trade order",
                       symbol=symbol,
                       side=side,
                       quantity=quantity,
                       mode=mode,
                       order_type=order_type)
            
            # Log the trade regardless of mode
            trade_record = await self._log_trade(trade_data, mode)
            
            if mode == "shadow":
                # Shadow mode - only log the trade, don't execute
                result = {
                    "status": "shadow_logged",
                    "trade_id": trade_record.id if trade_record else None,
                    "message": f"Shadow trade logged: {side} {quantity} {symbol}",
                    "execution_mode": mode
                }
                logger.info("Shadow trade logged", **result)
                return result
            
            elif mode == "live":
                # Live mode - execute the actual trade
                result = await self._execute_live_trade(trade_data, trade_record)
                logger.info("Live trade executed", **result)
                return result
            
            else:
                error_msg = f"Invalid execution mode: {mode}"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "message": error_msg
                }
                
        except Exception as e:
            logger.error("Trade execution error", error=str(e))
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def _execute_live_trade(self, trade_data: Dict, trade_record: Optional[Trade]) -> Dict:
        """Execute live trade through Alpaca"""
        try:
            symbol = trade_data["symbol"]
            side = trade_data["side"]
            quantity = trade_data["quantity"]
            order_type = trade_data.get("order_type", "market")
            
            # Prepare order parameters
            order_params = {
                "symbol": symbol,
                "qty": quantity,
                "side": side,
                "type": order_type,
                "time_in_force": "day"
            }
            
            # Add limit price if specified
            if order_type == "limit" and "limit_price" in trade_data:
                order_params["limit_price"] = trade_data["limit_price"]
            
            # Submit order to Alpaca
            order = self.alpaca_api.submit_order(**order_params)
            
            # Update trade record with Alpaca order ID
            if trade_record:
                db = next(get_db())
                trade_record.alpaca_order_id = order.id
                trade_record.status = "submitted"
                db.commit()
            
            return {
                "status": "submitted",
                "trade_id": trade_record.id if trade_record else None,
                "alpaca_order_id": order.id,
                "message": f"Live order submitted: {side} {quantity} {symbol}",
                "execution_mode": "live",
                "order_details": {
                    "symbol": order.symbol,
                    "qty": order.qty,
                    "side": order.side,
                    "status": order.status,
                    "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None
                }
            }
            
        except Exception as e:
            logger.error("Live trade execution failed", error=str(e))
            
            # Update trade record status
            if trade_record:
                db = next(get_db())
                trade_record.status = "failed"
                db.commit()
            
            return {
                "status": "failed",
                "trade_id": trade_record.id if trade_record else None,
                "message": f"Live trade failed: {str(e)}",
                "execution_mode": "live"
            }
    
    async def _log_trade(self, trade_data: Dict, mode: str) -> Optional[Trade]:
        """Log trade to database"""
        try:
            db = next(get_db())
            
            trade = Trade(
                symbol=trade_data["symbol"],
                side=trade_data["side"],
                quantity=trade_data["quantity"],
                price=trade_data.get("price"),
                order_type=trade_data.get("order_type", "market"),
                execution_mode=mode,
                status="pending" if mode == "live" else "shadow_logged"
            )
            
            db.add(trade)
            db.commit()
            db.refresh(trade)
            
            logger.info("Trade logged to database", trade_id=trade.id)
            return trade
            
        except Exception as e:
            logger.error("Failed to log trade", error=str(e))
            return None
    
    async def get_order_status(self, alpaca_order_id: str) -> Optional[Dict]:
        """Get order status from Alpaca"""
        try:
            order = self.alpaca_api.get_order(alpaca_order_id)
            return {
                "order_id": order.id,
                "symbol": order.symbol,
                "qty": order.qty,
                "side": order.side,
                "status": order.status,
                "filled_qty": order.filled_qty,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                "filled_at": order.filled_at.isoformat() if order.filled_at else None
            }
        except Exception as e:
            logger.error("Failed to get order status", error=str(e), order_id=alpaca_order_id)
            return None
    
    async def cancel_order(self, alpaca_order_id: str) -> Dict:
        """Cancel an order"""
        try:
            self.alpaca_api.cancel_order(alpaca_order_id)
            logger.info("Order cancelled", order_id=alpaca_order_id)
            return {
                "status": "cancelled",
                "order_id": alpaca_order_id,
                "message": "Order successfully cancelled"
            }
        except Exception as e:
            logger.error("Failed to cancel order", error=str(e), order_id=alpaca_order_id)
            return {
                "status": "error",
                "message": str(e)
            }