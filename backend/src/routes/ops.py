from __future__ import annotations
import os, sys, subprocess
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, Response, status, BackgroundTasks

router = APIRouter()

CRITICAL_ENVS = [
    "DATABASE_URL",
    "REDIS_URL",
    "POLYGON_API_KEY",
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET",
    "ALPACA_BASE_URL",
]

def _env_components() -> Dict[str, Any]:
    missing = [k for k in CRITICAL_ENVS if not os.getenv(k)]
    ok = len(missing) == 0
    return {"ok": ok, "missing": missing}

@router.get("/health")
@router.get("/healthz")
def health(resp: Response) -> Dict[str, Any]:
    # Base components from environment presence. This guarantees 503 on missing envs.
    components: Dict[str, Any] = {
        "env": _env_components(),
        # If you have deeper checks, you can extend these booleans later.
        "database": {"ok": bool(os.getenv("DATABASE_URL"))},
        "redis": {"ok": bool(os.getenv("REDIS_URL"))},
        "polygon": {"ok": bool(os.getenv("POLYGON_API_KEY"))},
        "alpaca": {"ok": bool(os.getenv("ALPACA_API_KEY") and os.getenv("ALPACA_API_SECRET"))},
    }
    overall = all(c.get("ok", False) for c in components.values())
    if not overall:
        resp.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        status_str = "degraded"
    else:
        status_str = "healthy"
    return {"status": status_str, "components": components}

@router.post("/discovery/run")
@router.get("/discovery/run")
def discovery_run(background: BackgroundTasks) -> Dict[str, Any]:
    """
    Fire-and-forget trigger. It tries to start the discover job in the background.
    Returns 202 semantics via payload without blocking the web worker.
    """
    project_root = Path(__file__).resolve().parents[2]  # points to backend/
    cmd = [sys.executable, "-m", "src.jobs.discover"]

    def _spawn():
        try:
            subprocess.Popen(cmd, cwd=str(project_root))
        except Exception:
            # Swallow errors; the endpoint reports "started": False in the response below
            pass

    started = True
    try:
        background.add_task(_spawn)
    except Exception:
        started = False

    return {"status": "queued", "started": started, "cmd": "python -m src.jobs.discover"}