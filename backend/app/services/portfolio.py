import alpaca_trade_api as tradeapi
from typing import Dict, List, Optional
import structlog
from app.config import settings
from app.models import Portfolio
from app.deps import get_db

logger = structlog.get_logger()

class PortfolioService:
    def __init__(self):
        self.alpaca_api = tradeapi.REST(
            settings.alpaca_api_key,
            settings.alpaca_secret_key,
            settings.alpaca_base_url
        )
    
    async def get_account_info(self) -> Optional[Dict]:
        """Get Alpaca account information"""
        try:
            account = self.alpaca_api.get_account()
            return {
                "cash": float(account.cash),
                "buying_power": float(account.buying_power),
                "portfolio_value": float(account.portfolio_value),
                "day_trade_count": int(account.daytrade_buying_power) if hasattr(account, 'daytrade_buying_power') else 0,
                "status": account.status
            }
        except Exception as e:
            logger.error("Failed to get account info", error=str(e))
            return None
    
    async def get_positions(self) -> List[Dict]:
        """Get current positions from Alpaca"""
        try:
            positions = self.alpaca_api.list_positions()
            position_list = []
            
            for position in positions:
                position_data = {
                    "symbol": position.symbol,
                    "quantity": int(position.qty),
                    "market_value": float(position.market_value),
                    "cost_basis": float(position.cost_basis),
                    "current_price": float(position.current_price),
                    "unrealized_pl": float(position.unrealized_pl),
                    "unrealized_plpc": float(position.unrealized_plpc),
                    "side": position.side
                }
                position_list.append(position_data)
            
            return position_list
            
        except Exception as e:
            logger.error("Failed to get positions", error=str(e))
            return []
    
    async def get_holdings(self) -> Dict:
        """Get complete holdings information"""
        try:
            account_info = await self.get_account_info()
            positions = await self.get_positions()
            
            if account_info is None:
                return {"error": "Failed to retrieve account information"}
            
            holdings = {
                "account": account_info,
                "positions": positions,
                "total_positions": len(positions)
            }
            
            # Calculate additional metrics
            total_unrealized_pl = sum(pos.get("unrealized_pl", 0) for pos in positions)
            holdings["total_unrealized_pl"] = total_unrealized_pl
            
            return holdings
            
        except Exception as e:
            logger.error("Failed to get holdings", error=str(e))
            return {"error": str(e)}
    
    async def save_portfolio_snapshot(self, holdings: Dict) -> Optional[int]:
        """Save portfolio snapshot to database"""
        try:
            db = next(get_db())
            
            account = holdings.get("account", {})
            positions = holdings.get("positions", [])
            
            snapshot = Portfolio(
                cash=account.get("cash", 0),
                buying_power=account.get("buying_power", 0),
                portfolio_value=account.get("portfolio_value", 0),
                day_trade_count=account.get("day_trade_count", 0),
                positions=positions
            )
            
            db.add(snapshot)
            db.commit()
            db.refresh(snapshot)
            
            logger.info("Saved portfolio snapshot", snapshot_id=snapshot.id)
            return snapshot.id
            
        except Exception as e:
            logger.error("Failed to save portfolio snapshot", error=str(e))
            return None
    
    async def get_position_performance(self, symbol: str) -> Optional[Dict]:
        """Get performance metrics for a specific position"""
        try:
            positions = await self.get_positions()
            position = next((p for p in positions if p["symbol"] == symbol), None)
            
            if not position:
                return None
            
            # Calculate additional performance metrics
            cost_basis = position["cost_basis"]
            market_value = position["market_value"]
            
            performance = {
                **position,
                "total_return_pct": ((market_value - cost_basis) / cost_basis * 100) if cost_basis != 0 else 0,
                "daily_return_pct": position["unrealized_plpc"] * 100
            }
            
            return performance
            
        except Exception as e:
            logger.error("Failed to get position performance", error=str(e), symbol=symbol)
            return None