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
    """Ensure each item has confidence, return as-is for UI"""
    try:
        redis_client = get_redis_client()
        cached_data = redis_client.get("amc:discovery:contenders.latest")
        if cached_data:
            items = json.loads(cached_data)
            # Ensure each item has confidence
            for item in items:
                if isinstance(item, dict) and not item.get("confidence"):
                    item["confidence"] = (item.get("score", 0) or 0) / 100.0
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
    """Compact view of latest contenders with factor fields"""
    try:
        raw = get_redis_client().get("amc:discovery:contenders.latest") or b"[]"
        items = json.loads(raw)
        keep = ["symbol", "price", "dollar_vol", "score", "confidence", "rel_vol_30m", 
                "atr_pct", "float", "si", "borrow", "util", "pcr", "iv_pctl", 
                "call_oi_up", "sent_score", "trending", "ema_cross", "rsi_zone_ok", "thesis"]
        result = []
        for item in items:
            if isinstance(item, dict):
                audit_item = {k: item.get(k) for k in keep}
                # Ensure confidence
                if not audit_item.get("confidence"):
                    audit_item["confidence"] = (item.get("score", 0) or 0) / 100.0
                result.append(audit_item)
        return result
    except Exception:
        return []

@router.get("/audit/{symbol}")
async def discovery_audit_symbol(symbol: str):
    """Full record for symbol plus factor weights and env policy"""
    try:
        raw = get_redis_client().get("amc:discovery:contenders.latest") or b"[]"
        items = json.loads(raw)
        
        # Find the symbol
        item = None
        for i in items:
            if isinstance(i, dict) and i.get("symbol") == symbol:
                item = i
                break
        
        if not item:
            return {"symbol": symbol, "item": None, "weights": {}, "gates": {}}
        
        # Ensure confidence
        if not item.get("confidence"):
            item["confidence"] = (item.get("score", 0) or 0) / 100.0
        
        # Factor weights from environment
        weights = {
            "volume": float(os.getenv("W_VOLUME", "0.2")),
            "momentum": float(os.getenv("W_MOMENTUM", "0.15")),
            "technicals": float(os.getenv("W_TECHNICALS", "0.15")),
            "options": float(os.getenv("W_OPTIONS", "0.2")),
            "sentiment": float(os.getenv("W_SENTIMENT", "0.15")),
            "fundamentals": float(os.getenv("W_FUNDAMENTALS", "0.15"))
        }
        
        # Policy gates from environment
        gates = {
            "REL_VOL_MIN": float(os.getenv("REL_VOL_MIN", "2.0")),
            "PRICE_MIN": float(os.getenv("PRICE_MIN", "1.0")),
            "PRICE_MAX": float(os.getenv("PRICE_MAX", "50.0")),
            "DOLLAR_VOL_MIN": float(os.getenv("DOLLAR_VOL_MIN", "5000000")),
            "ATR_PCT_MAX": float(os.getenv("ATR_PCT_MAX", "0.08")),
            "FLOAT_MIN": float(os.getenv("FLOAT_MIN", "10000000"))
        }
        
        return {
            "symbol": symbol,
            "item": item,
            "weights": weights,
            "gates": gates
        }
    except Exception:
        return {"symbol": symbol, "item": None, "weights": {}, "gates": {}}

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