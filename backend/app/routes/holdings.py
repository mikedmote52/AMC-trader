from fastapi import APIRouter
import structlog
from app.services.portfolio import PortfolioService

logger = structlog.get_logger()
router = APIRouter()

@router.get("/holdings")
async def get_holdings():
    """
    Get Alpaca cash and positions
    """
    try:
        portfolio_service = PortfolioService()
        holdings = await portfolio_service.get_holdings()
        
        if "error" in holdings:
            logger.error("Failed to retrieve holdings", error=holdings["error"])
            return {
                "success": False,
                "error": holdings["error"]
            }
        
        logger.info("Holdings retrieved successfully", 
                   total_positions=holdings.get("total_positions", 0),
                   portfolio_value=holdings.get("account", {}).get("portfolio_value", 0))
        
        return {
            "success": True,
            "data": holdings
        }
        
    except Exception as e:
        logger.error("Holdings endpoint error", error=str(e))
        return {
            "success": False,
            "error": str(e)
        }