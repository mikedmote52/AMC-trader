"""
Structured JSON logging utilities.
"""
import json
import logging
import sys
import time
from datetime import datetime
from typing import Any, Dict, Optional
from contextlib import contextmanager


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
            "component": record.name,
        }
        
        # Add extra fields if present
        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms
        if hasattr(record, "error"):
            log_obj["error"] = str(record.error)
        if hasattr(record, "extra_fields"):
            log_obj.update(record.extra_fields)
            
        return json.dumps(log_obj)


def setup_logger(name: str = "stock-discovery", level: str = "INFO") -> logging.Logger:
    """Set up JSON logger."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


@contextmanager
def log_duration(logger: logging.Logger, event: str, **extra_fields):
    """Context manager to log operation duration."""
    start = time.time()
    try:
        yield
        duration_ms = (time.time() - start) * 1000
        logger.info(
            event,
            extra={
                "duration_ms": duration_ms,
                "extra_fields": extra_fields
            }
        )
    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        logger.error(
            f"{event} failed",
            extra={
                "duration_ms": duration_ms,
                "error": str(e),
                "extra_fields": extra_fields
            }
        )
        raise


# Global logger instance
logger = setup_logger()