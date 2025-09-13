"""
Health check route with real dependency validation.
Returns 200 only if all external dependencies are healthy.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
import httpx
from typing import Dict, Any

from ..config import settings
from ..deps import get_http_client, get_redis, get_db, HTTPClientWithRetry
from ..utils.logging import logger
import redis.asyncio as redis
from sqlalchemy.orm import Session


router = APIRouter()


async def check_database(db: Session) -> Dict[str, Any]:
    """Check database connectivity."""
    try:
        result = db.execute("SELECT 1")
        return {"status": "healthy", "message": "Database connection OK"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "message": str(e)}


async def check_redis(redis_client: redis.Redis) -> Dict[str, Any]:
    """Check Redis connectivity."""
    try:
        await redis_client.ping()
        return {"status": "healthy", "message": "Redis connection OK"}
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {"status": "unhealthy", "message": str(e)}


async def check_polygon(http_client: HTTPClientWithRetry) -> Dict[str, Any]:
    """Check Polygon API connectivity."""
    try:
        # Try to fetch last trade for AAPL as a health check
        url = f"https://api.polygon.io/v2/last/trade/AAPL"
        response = await http_client.get(
            url,
            params={"apiKey": settings.polygon_api_key}
        )
        data = response.json()
        
        if data.get("status") == "OK":
            return {"status": "healthy", "message": "Polygon API OK", "last_price": data.get("results", {}).get("p")}
        else:
            return {"status": "unhealthy", "message": f"Polygon API error: {data.get('message', 'Unknown error')}"}
            
    except httpx.TimeoutException:
        return {"status": "unhealthy", "message": "Polygon API timeout"}
    except Exception as e:
        logger.error(f"Polygon health check failed: {e}")
        return {"status": "unhealthy", "message": str(e)}


async def check_alpaca(http_client: HTTPClientWithRetry) -> Dict[str, Any]:
    """Check Alpaca API connectivity."""
    try:
        # Check account status
        url = f"{settings.alpaca_base_url}/v2/account"
        response = await http_client.get(
            url,
            headers={
                "APCA-API-KEY-ID": settings.alpaca_api_key,
                "APCA-API-SECRET-KEY": settings.alpaca_api_secret
            }
        )
        data = response.json()
        
        return {
            "status": "healthy",
            "message": "Alpaca API OK",
            "account_status": data.get("status"),
            "buying_power": float(data.get("buying_power", 0))
        }
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return {"status": "unhealthy", "message": "Alpaca API authentication failed"}
        return {"status": "unhealthy", "message": f"Alpaca API error: {e.response.status_code}"}
    except httpx.TimeoutException:
        return {"status": "unhealthy", "message": "Alpaca API timeout"}
    except Exception as e:
        logger.error(f"Alpaca health check failed: {e}")
        return {"status": "unhealthy", "message": str(e)}


@router.get("/health")
async def health_check(
    http_client: HTTPClientWithRetry = Depends(get_http_client),
    redis_client: redis.Redis = Depends(get_redis),
    db: Session = Depends(get_db)
) -> JSONResponse:
    """
    Comprehensive health check.
    Returns 200 only if ALL services are healthy.
    """
    checks = {
        "database": await check_database(db),
        "redis": await check_redis(redis_client),
        "polygon": await check_polygon(http_client),
        "alpaca": await check_alpaca(http_client)
    }
    
    # Determine overall health
    all_healthy = all(check["status"] == "healthy" for check in checks.values())
    
    response_data = {
        "status": "healthy" if all_healthy else "unhealthy",
        "checks": checks
    }
    
    if all_healthy:
        logger.info("Health check passed", extra={"extra_fields": checks})
        return JSONResponse(status_code=200, content=response_data)
    else:
        failed_checks = [name for name, check in checks.items() if check["status"] != "healthy"]
        logger.warning(f"Health check failed: {', '.join(failed_checks)}", extra={"extra_fields": checks})
        return JSONResponse(status_code=503, content=response_data)