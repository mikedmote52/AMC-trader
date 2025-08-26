from fastapi import APIRouter, Query
from typing import List, Dict
import json
import importlib
import math
import os
from backend.src.shared.redis_client import get_redis_client

router = APIRouter()

# Redis keys
V2_CONT = "amc:discovery:v2:contenders.latest"
V2_TRACE = "amc:discovery:v2:explain.latest"
V1_CONT = "amc:discovery:contenders.latest"
V1_TRACE = "amc:discovery:explain.latest"
STATUS = "amc:discovery:status"

def _get_json(r, key):
    raw = r.get(key)
    return json.loads(raw) if raw else None

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
async def get_contenders():
    r = get_redis_client()
    items = _get_json(r, V2_CONT) or _get_json(r, V1_CONT) or []
    for it in items:
        if isinstance(it, dict):
            it["confidence"] = it.get("confidence") or ((it.get("score") or 0)/100.0)
    return items

@router.get("/explain")
async def explain():
    r = get_redis_client()
    return _get_json(r, V2_TRACE) or _get_json(r, V1_TRACE) or {"stages":[], "counts_in":{}, "counts_out":{}}

@router.get("/status")
async def status():
    r = get_redis_client()
    s = _get_json(r, STATUS)
    if s: return s
    tr = _get_json(r, V2_TRACE) or _get_json(r, V1_TRACE)
    return {"count": (tr or {}).get("count", 0), "ts": (tr or {}).get("ts")}

@router.get("/policy")
async def policy():
    # echo live env gates/weights so you can see what the job used
    env = {
      "PRICE_CAP": float(os.getenv("AMC_PRICE_CAP","100")),
      "REL_VOL_MIN": float(os.getenv("AMC_REL_VOL_MIN","3")),
      "ATR_PCT_MIN": float(os.getenv("AMC_ATR_PCT_MIN","0.04")),
      "FLOAT_MAX": float(os.getenv("AMC_FLOAT_MAX","50000000")),
      "BIG_FLOAT_MIN": float(os.getenv("AMC_BIG_FLOAT_MIN","150000000")),
      "SI_MIN": float(os.getenv("AMC_SI_MIN","0.20")),
      "BORROW_MIN": float(os.getenv("AMC_BORROW_MIN","0.20")),
      "UTIL_MIN": float(os.getenv("AMC_UTIL_MIN","0.85")),
      "IV_PCTL_MIN": float(os.getenv("AMC_IV_PCTL_MIN","0.80")),
      "PCR_MIN": float(os.getenv("AMC_PCR_MIN","2.0")),
      "W": {
        "volume": float(os.getenv("AMC_W_VOLUME","0.25")),
        "short":  float(os.getenv("AMC_W_SHORT","0.20")),
        "catalyst":float(os.getenv("AMC_W_CATALYST","0.20")),
        "sent":   float(os.getenv("AMC_W_SENT","0.15")),
        "options":float(os.getenv("AMC_W_OPTIONS","0.10")),
        "tech":   float(os.getenv("AMC_W_TECH","0.10")),
      },
      "INTRADAY": int(os.getenv("AMC_INTRADAY","0")),
      "LOOKBACK_DAYS": int(os.getenv("LOOKBACK_DAYS","60")),
      "R_MULT": float(os.getenv("AMC_R_MULT","2.0")),
      "ATR_STOP_MULT": float(os.getenv("AMC_ATR_STOP_MULT","1.5")),
      "MIN_STOP_PCT": float(os.getenv("AMC_MIN_STOP_PCT","0.02")),
    }
    return env

@router.get("/audit")
async def discovery_audit():
    """Compact view of latest contenders with factor fields"""
    try:
        r = get_redis_client()
        items = _get_json(r, V2_CONT) or _get_json(r, V1_CONT) or []
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
        r = get_redis_client()
        items = _get_json(r, V2_CONT) or _get_json(r, V1_CONT) or []
        
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