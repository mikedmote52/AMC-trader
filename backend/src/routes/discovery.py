from fastapi import APIRouter, Query
from typing import List, Dict
import json
import importlib
import math
import os
from backend.src.shared.redis_client import get_redis_client

router = APIRouter()

def _sigmoid(x):
    """Sigmoid function for normalization"""
    return 1 / (1 + math.exp(-x))

def _compute_confidence(item: Dict) -> float:
    """Compute confidence based on tightness, RS, and ATR"""
    w_score = float(os.getenv("AMC_W_SCORE", "0.6"))
    w_rs = float(os.getenv("AMC_W_RS", "0.3"))
    w_atr = float(os.getenv("AMC_W_ATR", "0.1"))
    
    tight = float(item.get("score", 0.0))  # already 0..1
    rsn = _sigmoid((float(item.get("rs_5d", 0.0))) / 0.05)  # ±5% maps to ~0.27..0.73
    atrn = max(0.0, 1.0 - min(1.0, float(item.get("atr_pct", 0.0)) / 0.05))  # ≤5% ATR preferred
    
    confidence = w_score * tight + w_rs * rsn + w_atr * atrn
    return max(0.0, min(1.0, confidence))

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
    """Return contenders data with computed confidence to prevent NaN in UI"""
    try:
        redis_client = get_redis_client()
        cached_data = redis_client.get("amc:discovery:contenders.latest")
        if cached_data:
            raw_items = json.loads(cached_data)
            # Inject confidence for each item if missing
            for item in raw_items:
                if isinstance(item, dict):
                    item["confidence"] = item.get("confidence") or _compute_confidence(item)
            return raw_items
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
async def get_audit() -> List[Dict]:
    """Read-only audit endpoint for inspecting contender data"""
    try:
        redis_client = get_redis_client()
        cached_data = redis_client.get("amc:discovery:contenders.latest")
        if cached_data:
            raw_items = json.loads(cached_data)
            audit_items = []
            for item in raw_items:
                if isinstance(item, dict):
                    confidence = item.get("confidence") or _compute_confidence(item)
                    audit_items.append({
                        "symbol": item.get("symbol", ""),
                        "price": item.get("price", 0),
                        "dollar_vol": item.get("dollar_vol", 0),
                        "compression_pct": item.get("compression_pct", 0),
                        "score": item.get("score", 0),
                        "rs_5d": item.get("rs_5d", 0),
                        "atr_pct": item.get("atr_pct", 0),
                        "confidence": confidence,
                        "thesis": item.get("thesis", "")
                    })
            return audit_items
        return []
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