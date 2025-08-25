import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import time
from app.config import settings
from app.routes import health, holdings, recommendations, trades
from app.deps import Base, engine

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency')

# Create FastAPI app
app = FastAPI(
    title="AMC Trading API",
    description="Trading intelligence and execution API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
Base.metadata.create_all(bind=engine)

# Middleware for logging and metrics
@app.middleware("http")
async def log_requests(request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    # Log request
    logger.info(
        "HTTP request processed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        process_time=process_time
    )
    
    # Update metrics
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_LATENCY.observe(process_time)
    
    return response

# Include routers
app.include_router(health.router)
app.include_router(holdings.router)
app.include_router(recommendations.router)
app.include_router(trades.router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AMC Trading API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting AMC Trading API", 
               environment=settings.environment,
               log_level=settings.log_level)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development"
    )