from fastapi import APIRouter, Query
from typing import List, Dict
import json
import importlib
import math
import os
from backend.src.shared.redis_client import get_redis_client

router = APIRouter()

# Confidence computation functions
w_score = float(os.getenv("AMC_W_SCORE", "0.6"))
w_rs    = float(os.getenv("AMC_W_RS",    "0.3"))
w_atr   = float(os.getenv("AMC_W_ATR",   "0.1"))

def _sigmoid(x): 
    return 1/(1+math.exp(-x))

def _conf(it):
    tight = float(it.get("score") or 0.0)
    rsn   = _sigmoid((float(it.get("rs_5d") or 0.0))/0.05)
    atrn  = max(0.0, 1.0 - min(1.0, float(it.get("atr_pct") or 0.0)/0.05))
    return max(0.0, min(1.0, w_score*tight + w_rs*rsn + w_atr*atrn))

def _load_selector():
    """Load select_candidates function from available jobs modules"""
    for mod in ("src.jobs.discovery", "src.jobs.discover"):
        try:
            m = importlib.import_module(mod)
            f = getattr(m, "select_candidates", None)
            if callable(f):
                return f, mod
        except Exception:
            continue
    return None, None

@router.get("/contenders")
async def get_contenders() -> List[Dict]:
    """Ensure each item has confidence to prevent NaN in UI"""
    try:
        redis_client = get_redis_client()
        cached_data = redis_client.get("amc:discovery:contenders.latest")
        if cached_data:
            items = json.loads(cached_data)
            # Ensure each item has confidence
            for it in items:
                if isinstance(it, dict):
                    it["confidence"] = it.get("confidence") or _conf(it)
            return items
        return []
    except Exception:
        return []

@router.get("/status")
async def get_discovery_status() -> Dict:
    try:
        redis_client = get_redis_client()
        status_data = redis_client.get("amc:discovery:status")
        if status_data:
            return json.loads(status_data)
        else:
            return {"count": 0, "ts": None}
    except Exception:
        return {"count": 0, "ts": None}

@router.get("/explain")
async def discovery_explain():
    try:
        redis_client = get_redis_client()
        raw = redis_client.get("amc:discovery:explain.latest")
        if not raw:
            return {"ts": None, "count": 0, "trace": {"stages":[], "counts_in":{}, "counts_out":{}, "rejections":{}, "samples":{}}}
        return json.loads(raw)
    except Exception:
        return {"ts": None, "count": 0, "trace": {"stages":[], "counts_in":{}, "counts_out":{}, "rejections":{}, "samples":{}}}

@router.get("/audit")
async def discovery_audit():
    """Returns what the UI sees for contender inspection"""
    try:
        raw = get_redis_client().get("amc:discovery:contenders.latest") or b"[]"
        items = json.loads(raw)
        keep = ["symbol","price","dollar_vol","compression_pct","score","rs_5d","atr_pct","confidence","thesis"]
        return [{k:i.get(k) for k in keep} for i in items]
    except Exception:
        return []

@router.get("/test")
async def discovery_test(relaxed: bool = Query(True), limit: int = Query(10)):
    f, mod = _load_selector()
    if not f:
        return {"items": [], "trace": {}, "error": "select_candidates not found in src.jobs.discovery or src.jobs.discover"}
    try:
        res = await f(relaxed=relaxed, limit=limit, with_trace=True)  # type: ignore
        if isinstance(res, tuple) and len(res) == 2:
            items, trace = res
        else:
            items, trace = res, {}
        return {"items": items, "trace": trace, "module": mod, "relaxed": relaxed, "limit": limit}
    except Exception as e:
        return {"items": [], "trace": {}, "module": mod, "error": str(e)}