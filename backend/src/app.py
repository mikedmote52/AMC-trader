import structlog
import os, json
from fastapi import FastAPI, Request
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

@app.get("/_version")
def version():
    # Render exposes these; fall back to git SHA you set later
    return {
        "render_commit": os.getenv("RENDER_GIT_COMMIT", "unknown"),
        "render_build_id": os.getenv("RENDER_SERVICE_BUILD_ID", "unknown")
    }

@app.get("/_routes")
def routes(request: Request):
    return {"routes": [r.path for r in request.app.routes]}

# Include routers
app.include_router(trades.router)
app.include_router(trades.diag)

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