"""
Configuration management with strict environment validation.
Fails fast if any required environment variable is missing.
"""
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings with strict validation."""
    
    # API Keys - REQUIRED
    polygon_api_key: str = Field(..., description="Polygon.io API key for market data")
    alpaca_api_key: str = Field(..., description="Alpaca API key for trading")
    alpaca_api_secret: str = Field(..., description="Alpaca API secret")
    alpaca_base_url: str = Field(default="https://paper-api.alpaca.markets", description="Alpaca API base URL")
    
    # Database - REQUIRED
    database_url: str = Field(..., description="PostgreSQL connection URL")
    redis_url: str = Field(..., description="Redis connection URL")
    
    # Optional
    slack_webhook_url: Optional[str] = Field(default=None, description="Slack webhook for notifications")
    frontend_public_api_base: str = Field(default="http://localhost:8000", description="API base URL for frontend")
    
    # Timeouts and retries
    http_timeout: float = Field(default=5.0, description="HTTP request timeout in seconds")
    http_retries: int = Field(default=2, description="Number of HTTP retries")
    
    # Rate limits
    polygon_rate_limit: int = Field(default=5, description="Polygon API calls per second")
    alpaca_rate_limit: int = Field(default=200, description="Alpaca API calls per minute")
    
    # Trading constraints
    max_position_pct: float = Field(default=0.02, description="Max position size as % of portfolio")
    max_sector_pct: float = Field(default=0.20, description="Max sector exposure as % of portfolio")
    min_price: float = Field(default=1.0, description="Minimum stock price for trading")
    min_volume: int = Field(default=100000, description="Minimum daily volume for trading")
    max_daily_trades: int = Field(default=10, description="Maximum trades per day")
    
    # Discovery parameters
    discovery_top_n: int = Field(default=20, description="Number of top recommendations to generate")
    sentiment_min_posts: int = Field(default=5, description="Minimum posts for valid sentiment")
    
    @validator("polygon_api_key", "alpaca_api_key", "alpaca_api_secret")
    def validate_api_keys(cls, v: str, field):
        """Ensure API keys are not placeholder values."""
        if not v or v.startswith("your_") or v == "":
            raise ValueError(f"{field.name} must be set to a valid API key, not '{v}'")
        return v
    
    @validator("database_url")
    def validate_database_url(cls, v: str):
        """Ensure database URL is properly formatted."""
        if not v.startswith("postgresql"):
            raise ValueError(f"DATABASE_URL must be a PostgreSQL URL, got: {v}")
        return v
    
    @validator("redis_url")
    def validate_redis_url(cls, v: str):
        """Ensure Redis URL is properly formatted."""
        if not v.startswith("redis://"):
            raise ValueError(f"REDIS_URL must start with 'redis://', got: {v}")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        validate_assignment = True


# Global settings instance - will fail fast on import if env vars are missing
try:
    settings = Settings()
except Exception as e:
    import sys
    print(f"FATAL: Failed to load configuration: {e}", file=sys.stderr)
    print("Ensure all required environment variables are set:", file=sys.stderr)
    print("  - POLYGON_API_KEY", file=sys.stderr)
    print("  - ALPACA_API_KEY", file=sys.stderr)
    print("  - ALPACA_API_SECRET", file=sys.stderr)
    print("  - DATABASE_URL", file=sys.stderr)
    print("  - REDIS_URL", file=sys.stderr)
    sys.exit(1)