import redis
import httpx
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
import structlog
from app.config import settings

logger = structlog.get_logger()

# Database setup
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Redis client
redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

def get_redis() -> redis.Redis:
    """Get Redis client"""
    return redis_client

# HTTPx client for external API calls
@contextmanager
def get_httpx_client():
    """Get HTTPx client with proper timeout settings"""
    client = httpx.Client(timeout=30.0)
    try:
        yield client
    finally:
        client.close()

async def get_async_httpx_client():
    """Get async HTTPx client"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client

# Health check functions
def check_database_health() -> bool:
    """Check if database is accessible"""
    try:
        with SessionLocal() as db:
            db.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return False

def check_redis_health() -> bool:
    """Check if Redis is accessible"""
    try:
        return redis_client.ping()
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return False

def check_polygon_health() -> bool:
    """Check if Polygon API is accessible"""
    try:
        with get_httpx_client() as client:
            response = client.get(
                f"https://api.polygon.io/v1/meta/symbols/AAPL/company",
                params={"apikey": settings.polygon_api_key}
            )
            return response.status_code == 200
    except Exception as e:
        logger.error("Polygon health check failed", error=str(e))
        return False

def check_alpaca_health() -> bool:
    """Check if Alpaca API is accessible"""
    try:
        import alpaca_trade_api as tradeapi
        api = tradeapi.REST(
            settings.alpaca_api_key,
            settings.alpaca_secret_key,
            settings.alpaca_base_url
        )
        account = api.get_account()
        return account is not None
    except Exception as e:
        logger.error("Alpaca health check failed", error=str(e))
        return False