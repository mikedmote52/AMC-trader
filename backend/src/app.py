import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.src.routes import trades

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

# Create FastAPI app
app = FastAPI(
    title="AMC Paper Trading API",
    description="Paper trading execution API with risk guardrails",
    version="1.0.0"
)

# CORS middleware - allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(trades.router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AMC Paper Trading API",
        "version": "1.0.0",
        "status": "running"
    }

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting AMC Paper Trading API")
    
    uvicorn.run(
        "backend.src.app:app",
        host="0.0.0.0",
        port=8001,  # Use different port from main API
        reload=True
    )