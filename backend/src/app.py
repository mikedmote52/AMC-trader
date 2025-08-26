import structlog
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.src.routes.trades import router as trades_router
from backend.src.routes.debug_polygon import router as polygon_debug

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

@app.get("/_whoami")
def whoami():
    return {
        "commit": os.getenv("RENDER_GIT_COMMIT","unknown"),
        "build": os.getenv("RENDER_SERVICE_BUILD_ID","unknown"),
        "handler_tag": "trace_v1"
    }

@app.exception_handler(StarletteHTTPException)
async def http_exc_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}, "handler_tag": "trace_v1"},
    )

@app.middleware("http")
async def add_trace_header(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["x-amc-trades-handler"] = "trace_v1"
    return resp

# CORS middleware - allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(trades_router)
app.include_router(polygon_debug)

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