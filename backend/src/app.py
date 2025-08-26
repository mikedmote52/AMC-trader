try:
    import structlog  # optional
    log = structlog.get_logger("amc")
except Exception:
    import logging
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger("amc")

import os
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.src.routes.trades import router as trades_router
from backend.src.routes.debug_polygon import router as polygon_debug

# Trace v3 constants
APP_TAG    = "trace_v3"
APP_COMMIT = os.getenv("RENDER_GIT_COMMIT", "unknown")
APP_BUILD  = os.getenv("RENDER_SERVICE_BUILD_ID", "unknown")

# Configure structured logging if available
try:
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
except NameError:
    # structlog not available, already configured logging fallback above
    pass

# Create FastAPI app
app = FastAPI(
    title="AMC Paper Trading API",
    description="Paper trading execution API with risk guardrails",
    version="1.0.0"
)

@app.get("/_whoami")
def whoami():
    return {
        "tag": APP_TAG,
        "commit": APP_COMMIT,
        "build": APP_BUILD,
        "ts": datetime.now(timezone.utc).isoformat()
    }

@app.exception_handler(StarletteHTTPException)
async def http_exc_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)},
            "tag": APP_TAG,
        },
    )

@app.middleware("http")
async def add_trace_header(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["x-amc-trades-handler"] = APP_TAG
    resp.headers["x-amc-commit"] = APP_COMMIT
    return resp

# CORS middleware - allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database health and metrics
from contextlib import asynccontextmanager
import asyncpg
from prometheus_client import CollectorRegistry, Counter, make_asgi_app
import redis.asyncio as redis

DISCOVERY_TRIGGERED = Counter("amc_discovery_triggered_total", "manual discovery trigger calls")
DISCOVERY_ERRORS = Counter("amc_discovery_errors_total", "manual discovery trigger errors")

registry = CollectorRegistry()
metrics_app = make_asgi_app(registry=registry)
app.mount("/metrics", metrics_app)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup - you could initialize DB pools here
    yield
    # On shutdown

app.lifespan = lifespan

@app.get("/")
def root():
    return {"status": "AMC Trading API v1.0.0", "docs": "/docs"}

@app.get("/health")
@app.get("/healthz")
async def health():
    """Health check endpoint"""
    try:
        components = {}
        
        # Check environment
        required_vars = [
            "DATABASE_URL", "REDIS_URL", "POLYGON_API_KEY", 
            "ALPACA_API_KEY", "ALPACA_API_SECRET", "ALPACA_BASE_URL"
        ]
        missing = [var for var in required_vars if not os.getenv(var)]
        components["env"] = {"ok": len(missing) == 0, "missing": missing}
        
        # Check database
        try:
            async with asyncpg.create_pool(os.getenv("DATABASE_URL"), min_size=1, max_size=1) as pool:
                async with pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
            components["database"] = {"ok": True}
        except Exception:
            components["database"] = {"ok": False}
        
        # Check Redis
        try:
            r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
            await r.ping()
            await r.close()
            components["redis"] = {"ok": True}
        except Exception:
            components["redis"] = {"ok": False}
        
        # Check external APIs (simple connectivity)
        components["polygon"] = {"ok": bool(os.getenv("POLYGON_API_KEY"))}
        components["alpaca"] = {"ok": bool(os.getenv("ALPACA_API_KEY")) and bool(os.getenv("ALPACA_API_SECRET"))}
        
        # Overall health
        all_ok = all(comp.get("ok", False) for comp in components.values())
        status_code = 200 if all_ok else 503
        
        # Add version fields
        resp = {
            "status": "healthy" if all_ok else "degraded",
            "components": components,
            "tag": APP_TAG,
            "commit": APP_COMMIT,
            "build": APP_BUILD
        }
        
        from fastapi import Response
        import json
        return Response(
            content=json.dumps(resp),
            status_code=status_code,
            media_type="application/json"
        )
        
    except Exception:
        from fastapi import Response
        return Response(
            content='{"status":"error","components":{}}',
            status_code=503,
            media_type="application/json"
        )

# Include routers
app.include_router(trades_router)
app.include_router(polygon_debug, prefix="/debug")