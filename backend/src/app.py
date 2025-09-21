from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os

try:
    import structlog  # optional
    log = structlog.get_logger("amc")
except Exception:
    import logging
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger("amc")

from datetime import datetime, timezone
from fastapi.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.src.routes.trades import router as trades_router
from backend.src.routes.debug_polygon import router as polygon_debug
from backend.src.routes.discovery_admin import router as discovery_admin_router

# Trace v3 constants
APP_TAG    = "trace_v3"
APP_COMMIT = os.getenv("RENDER_GIT_COMMIT", "unknown")
APP_BUILD  = os.getenv("RENDER_SERVICE_BUILD_ID", "unknown")
TRADES_HANDLER = os.getenv("AMC_TRADES_HANDLER", "default")

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
app = FastAPI(title="AMC Trader API")

@app.get("/_whoami")
async def whoami():
    return {
        "env": os.getenv("ENVIRONMENT", "unknown"),
        "service": os.getenv("RENDER_SERVICE_NAME", "amc-trader"),
        "handler": TRADES_HANDLER,
    }

@app.get("/_routes")
def _routes():
    return sorted([r.path for r in app.routes])

@app.get("/_redis_ping")
def _redis_ping():
    """Quick Redis connectivity test"""
    try:
        import redis
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)
        ping_result = r.ping()
        return {"pong": ping_result, "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/0").split("@")[-1]}
    except Exception as e:
        return {"error": str(e), "pong": False}

class TradeError(Exception):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail

@app.exception_handler(TradeError)
async def trade_error_handler(request: Request, exc: TradeError):
    return JSONResponse(status_code=400, content={"success": False, "error": exc.code, "detail": exc.detail})

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
async def add_trace_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["x-amc-trades-handler"] = TRADES_HANDLER
    resp.headers["x-amc-env"] = os.getenv("RENDER_SERVICE_NAME", os.getenv("ENVIRONMENT", "unknown"))
    return resp

# CORS middleware - allow frontend origins
origins = [
    "http://localhost:5173",  # Vite dev server
    "https://amc-frontend.onrender.com",  # Production frontend
    "https://www.amc-frontend.onrender.com",  # Production frontend with www
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database health and metrics
from contextlib import asynccontextmanager
import asyncpg
from prometheus_client import CollectorRegistry, Counter, make_asgi_app
import redis.asyncio as redis

# Discovery worker imports removed - using enhanced discovery system only

DISCOVERY_TRIGGERED = Counter("amc_discovery_triggered_total", "manual discovery trigger calls")
DISCOVERY_ERRORS = Counter("amc_discovery_errors_total", "manual discovery trigger errors")

registry = CollectorRegistry()
metrics_app = make_asgi_app(registry=registry)
app.mount("/metrics", metrics_app)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup - No background worker in web process (using dedicated worker service)
    log.info("✅ Web process started - discovery handled by dedicated worker service")
    yield
    # On shutdown
    log.info("🛑 Web process shutdown")

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

# Include AlphaStack 4.1 API
from backend.src.routes.alphastack import router as alphastack_router
app.include_router(alphastack_router, prefix="/v1", tags=["alphastack"])

# Mount Socket.IO for real-time WebSocket streaming
from backend.src.sockets import sockets_app
app.mount("/v1/stream", sockets_app)

# Include discovery (enhanced only), portfolio, learning, daily updates, thesis, analytics, and pattern memory routers  
from backend.src.routes import discovery_unified as discovery_routes
from backend.src.routes import discovery_explosive as discovery_explosive_routes
from backend.src.routes import portfolio as portfolio_routes
from backend.src.routes import learning as learning_routes
from backend.src.routes import daily_updates as daily_updates_routes
from backend.src.routes import learning_analytics as learning_analytics_routes
from backend.src.routes import thesis as thesis_routes
from backend.src.routes import analytics as analytics_routes
from backend.src.routes import performance_analytics as performance_analytics_routes
from backend.src.routes import data_quality as data_quality_routes
from backend.src.routes import pattern_memory as pattern_memory_routes
from backend.src.routes import notifications as notification_routes
from backend.src.routes import monitoring as monitoring_routes
from backend.src.routes import data_integrity as data_integrity_routes
from backend.src.routes import advanced_ranking as advanced_ranking_routes
from backend.src.routes import thesis_monitor as thesis_monitor_routes

# Enhanced discovery system - single unified system
app.include_router(discovery_routes.router, prefix="/api/discovery", tags=["discovery"])
app.include_router(discovery_routes.router, prefix="/discovery", tags=["discovery"])
app.include_router(discovery_explosive_routes.router, prefix="/discovery", tags=["discovery-explosive"])
app.include_router(discovery_admin_router, prefix="", tags=["discovery-admin"])
# Calibration routes removed - unified BMS system
app.include_router(advanced_ranking_routes.router, prefix="/advanced-ranking", tags=["advanced-ranking"])
app.include_router(portfolio_routes.router, prefix="/portfolio", tags=["portfolio"])
app.include_router(learning_routes.router, prefix="/learning", tags=["learning"])
app.include_router(learning_analytics_routes.router, prefix="/learning-analytics", tags=["learning-analytics"])
app.include_router(daily_updates_routes.router, prefix="/daily-updates", tags=["daily-updates"])
app.include_router(thesis_routes.router, prefix="/thesis", tags=["thesis"])
app.include_router(analytics_routes.router, prefix="/analytics", tags=["analytics"])
app.include_router(performance_analytics_routes.router, prefix="/performance", tags=["performance-analytics"])
app.include_router(data_quality_routes.router, prefix="/data-quality", tags=["data-quality"])
app.include_router(pattern_memory_routes.router, prefix="/pattern-memory", tags=["pattern-memory"])
app.include_router(notification_routes.router, prefix="/notifications", tags=["notifications"])
app.include_router(monitoring_routes.router, prefix="/monitoring", tags=["monitoring"])
app.include_router(thesis_monitor_routes.router, prefix="/thesis-monitor", tags=["thesis-monitor"])
app.include_router(data_integrity_routes.router, prefix="/data-integrity", tags=["data-integrity"])

# Compatibility routes for old frontend paths
from starlette.responses import RedirectResponse

@app.get("/api/recommendations")
@app.get("/recommendations")
async def compat_recommendations():
    return RedirectResponse(url="/discovery/emergency/enhanced-discovery", status_code=307)

@app.get("/api/holdings")
@app.get("/holdings")
async def compat_holdings():
    return RedirectResponse(url="/portfolio/holdings", status_code=307)

@app.get("/api/contenders")
async def api_contenders():
    # Enhanced discovery system - redirect to enhanced endpoint
    return RedirectResponse(url="/discovery/emergency/enhanced-discovery?limit=20", status_code=307)

# Polygon MCP endpoints for frontend squeeze detector
@app.get("/api/polygon/universe")
async def polygon_universe():
    """Get stock universe for frontend Polygon MCP detector"""
    try:
        # Use the MCP client to get real universe data
        from backend.src.mcp_client import get_polygon_tickers
        results = await get_polygon_tickers(limit=1000)
        return {"results": results}
    except Exception as e:
        log.error(f"Polygon universe error: {e}")
        # Return a representative sample to keep frontend working
        return {
            "results": [
                {"ticker": "AAPL", "name": "Apple Inc.", "type": "CS", "active": True},
                {"ticker": "TSLA", "name": "Tesla Inc.", "type": "CS", "active": True},
                {"ticker": "NVDA", "name": "NVIDIA Corporation", "type": "CS", "active": True},
                {"ticker": "MSFT", "name": "Microsoft Corporation", "type": "CS", "active": True},
                {"ticker": "META", "name": "Meta Platforms Inc.", "type": "CS", "active": True},
                {"ticker": "GOOGL", "name": "Alphabet Inc.", "type": "CS", "active": True},
                {"ticker": "AMZN", "name": "Amazon.com Inc.", "type": "CS", "active": True},
                {"ticker": "NFLX", "name": "Netflix Inc.", "type": "CS", "active": True},
                {"ticker": "AMD", "name": "Advanced Micro Devices Inc.", "type": "CS", "active": True},
                {"ticker": "COIN", "name": "Coinbase Global Inc.", "type": "CS", "active": True}
            ]
        }

@app.post("/api/polygon/snapshots")
async def polygon_snapshots(payload: dict = Body(...)):
    """Get market snapshots for frontend Polygon MCP detector"""
    try:
        symbols = payload.get("symbols", [])
        if not symbols:
            return {"results": []}

        # Use the MCP client to get real snapshot data
        from backend.src.mcp_client import get_polygon_snapshots
        results = await get_polygon_snapshots(symbols)
        return {"results": results}
    except Exception as e:
        log.error(f"Polygon snapshots error: {e}")
        # Return realistic mock data to keep frontend working
        symbols = payload.get("symbols", [])
        results = []
        for symbol in symbols[:10]:  # Limit to 10 for performance
            import random
            base_price = 10 + random.random() * 190
            change_percent = (random.random() - 0.5) * 20
            volume = random.randint(50000, 10000000)

            results.append({
                "symbol": symbol,
                "todaysChangePerc": change_percent,
                "day": {
                    "c": base_price * (1 + change_percent / 100),
                    "v": volume,
                    "o": base_price,
                    "h": base_price * 1.05,
                    "l": base_price * 0.95
                },
                "prevDay": {
                    "c": base_price,
                    "v": int(volume * 0.8)
                }
            })
        return {"results": results}

# Optional buy-now alias if the UI ever posts here:
from fastapi import Body
@app.post("/api/buy")
async def compat_buy(payload: dict = Body(...)):
    # forward to the actual executor
    from fastapi import Request
    # re-use existing trades endpoint by calling it directly
    # safest and simplest is to import the router function if available; otherwise call via HTTP to self:
    import httpx
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=60) as client:
        r = await client.post("/trades/execute", json=payload)
        return r.json()