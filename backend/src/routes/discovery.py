from fastapi import APIRouter, Query
from typing import List, Dict
import json
import importlib
from backend.src.shared.redis_client import get_redis_client

router = APIRouter()

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
    """Return raw contenders data from Redis with all enriched fields"""
    try:
        redis_client = get_redis_client()
        cached_data = redis_client.get("amc:discovery:contenders.latest")
        if cached_data:
            return json.loads(cached_data)
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