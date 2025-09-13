"""
Custom error types for explicit error handling.
"""
from typing import Optional, Dict, Any


class BaseAPIError(Exception):
    """Base class for API errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigError(BaseAPIError):
    """Configuration or environment error."""
    pass


class TimeoutError(BaseAPIError):
    """External service timeout."""
    pass


class HTTPError(BaseAPIError):
    """HTTP request error."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, **kwargs):
        super().__init__(message, kwargs)
        self.status_code = status_code


class BadResponseError(BaseAPIError):
    """Invalid or unexpected response from external service."""
    pass


class RateLimitError(BaseAPIError):
    """Rate limit exceeded."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, kwargs)
        self.retry_after = retry_after


class DataError(BaseAPIError):
    """Data validation or processing error."""
    pass


class TradingError(BaseAPIError):
    """Trading operation error."""
    pass