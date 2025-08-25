import os
import sys
from typing import Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings
import structlog

logger = structlog.get_logger()

class Settings(BaseSettings):
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    
    # Redis
    redis_url: str = Field(..., env="REDIS_URL")
    
    # Alpaca Trading API
    alpaca_api_key: str = Field(..., env="ALPACA_API_KEY")
    alpaca_secret_key: str = Field(..., env="ALPACA_SECRET_KEY")
    alpaca_base_url: str = Field(..., env="ALPACA_BASE_URL")
    
    # Polygon API for market data
    polygon_api_key: str = Field(..., env="POLYGON_API_KEY")
    
    # Application settings
    environment: str = Field(default="development", env="ENVIRONMENT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    @validator("*", pre=True)
    def validate_required_env_vars(cls, v, field):
        if v is None and field.field_info.default is ...:
            logger.error(f"Missing required environment variable: {field.field_info.env}")
            sys.exit(1)
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False

def validate_environment():
    """Validate all required environment variables on import - fail fast"""
    try:
        settings = Settings()
        logger.info("Environment validation successful", 
                   environment=settings.environment)
        return settings
    except Exception as e:
        logger.error("Environment validation failed", error=str(e))
        sys.exit(1)

# Validate environment on import
settings = validate_environment()