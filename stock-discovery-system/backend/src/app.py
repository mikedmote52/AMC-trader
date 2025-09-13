"""
Main FastAPI application with structured logging and health checks.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app, Counter, Histogram
import time
import traceback

from .config import settings
from .deps import init_resources, cleanup_resources
from .utils.logging import logger
from .utils.errors import BaseAPIError
from .routes import health, holdings, recommendations, trades


# Prometheus metrics
http_request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint", "status"]
)
http_request_total = Counter(
    "http_request_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)
api_errors_total = Counter(
    "api_errors_total",
    "Total API errors",
    ["error_type"]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    logger.info("Starting application...")
    
    # Initialize resources
    await init_resources()
    
    logger.info("Application started successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down application...")
    await cleanup_resources()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Stock Discovery System",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_public_api_base],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with duration."""
    start_time = time.time()
    
    # Skip metrics endpoint
    if request.url.path == "/metrics":
        return await call_next(request)
    
    # Process request
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Log and record metrics
        logger.info(
            f"{request.method} {request.url.path}",
            extra={
                "duration_ms": duration * 1000,
                "extra_fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code
                }
            }
        )
        
        http_request_duration.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).observe(duration)
        
        http_request_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"{request.method} {request.url.path} failed",
            extra={
                "duration_ms": duration * 1000,
                "error": str(e),
                "extra_fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "traceback": traceback.format_exc()
                }
            }
        )
        api_errors_total.labels(error_type=type(e).__name__).inc()
        raise


@app.exception_handler(BaseAPIError)
async def handle_api_error(request: Request, exc: BaseAPIError):
    """Handle custom API errors."""
    api_errors_total.labels(error_type=type(exc).__name__).inc()
    return JSONResponse(
        status_code=getattr(exc, "status_code", 500),
        content={
            "error": exc.message,
            "details": exc.details
        }
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.error(
        f"Unexpected error: {exc}",
        extra={
            "extra_fields": {
                "path": request.url.path,
                "traceback": traceback.format_exc()
            }
        }
    )
    api_errors_total.labels(error_type="unexpected").inc()
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "details": {"message": str(exc)}
        }
    )


# Mount routes
app.include_router(health.router, tags=["health"])
app.include_router(holdings.router, prefix="/holdings", tags=["holdings"])
app.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
app.include_router(trades.router, prefix="/trades", tags=["trades"])

# Mount Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Stock Discovery System",
        "version": "0.1.0",
        "status": "running"
    }