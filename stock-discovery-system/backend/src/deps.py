"""
Dependency injection for FastAPI routes.
Creates and manages shared resources like HTTP clients, database connections, etc.
"""
import httpx
import redis.asyncio as redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import AsyncGenerator, Generator
from contextlib import asynccontextmanager

from .config import settings
from .utils.logging import logger


# Global HTTP client with timeout and retry
class HTTPClientWithRetry:
    """HTTP client with built-in retry logic."""
    
    def __init__(self, timeout: float = 5.0, retries: int = 2):
        self.timeout = timeout
        self.retries = retries
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))
    
    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make HTTP request with retry logic."""
        last_error = None
        for attempt in range(self.retries + 1):
            try:
                response = await self.client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"HTTP timeout on attempt {attempt + 1}/{self.retries + 1}: {url}")
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:  # Retry on server errors
                    last_error = e
                    logger.warning(f"HTTP {e.response.status_code} on attempt {attempt + 1}/{self.retries + 1}: {url}")
                else:
                    raise  # Don't retry client errors
            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error on attempt {attempt + 1}/{self.retries + 1}: {e}")
                
        raise last_error
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("POST", url, **kwargs)
    
    async def close(self):
        await self.client.aclose()


# Global instances
http_client: HTTPClientWithRetry = None
redis_client: redis.Redis = None
db_engine = None
SessionLocal = None


async def init_resources():
    """Initialize all shared resources."""
    global http_client, redis_client, db_engine, SessionLocal
    
    # HTTP client
    http_client = HTTPClientWithRetry(
        timeout=settings.http_timeout,
        retries=settings.http_retries
    )
    logger.info("HTTP client initialized")
    
    # Redis
    try:
        redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise
    
    # Database
    try:
        db_engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
        # Test connection
        with db_engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


async def cleanup_resources():
    """Clean up all shared resources."""
    global http_client, redis_client
    
    if http_client:
        await http_client.close()
        logger.info("HTTP client closed")
    
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")
    
    if db_engine:
        db_engine.dispose()
        logger.info("Database connections closed")


# Dependency providers for FastAPI
async def get_http_client() -> HTTPClientWithRetry:
    """Get HTTP client dependency."""
    return http_client


async def get_redis() -> redis.Redis:
    """Get Redis client dependency."""
    return redis_client


def get_db() -> Generator[Session, None, None]:
    """Get database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()