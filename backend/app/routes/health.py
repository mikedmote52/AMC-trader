from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
import structlog
from app.deps import (
    check_database_health,
    check_redis_health,
    check_polygon_health,
    check_alpaca_health
)

logger = structlog.get_logger()
router = APIRouter()

# @router.get("/health")  # disabled in favor of spec-compliant ops.health
async def health_check():
    """
    Health check endpoint - returns 200 only if all services are healthy,
    otherwise returns 503 with boolean status for each service
    """
    try:
        # Check all services
        db_healthy = check_database_health()
        redis_healthy = check_redis_health()
        polygon_healthy = check_polygon_health()
        alpaca_healthy = check_alpaca_health()
        
        health_status = {
            "database": db_healthy,
            "redis": redis_healthy,
            "polygon": polygon_healthy,
            "alpaca": alpaca_healthy,
            "overall": db_healthy and redis_healthy and polygon_healthy and alpaca_healthy
        }
        
        logger.info("Health check performed", **health_status)
        
        if health_status["overall"]:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=health_status
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=health_status
            )
            
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "database": False,
                "redis": False,
                "polygon": False,
                "alpaca": False,
                "overall": False,
                "error": str(e)
            }
        )