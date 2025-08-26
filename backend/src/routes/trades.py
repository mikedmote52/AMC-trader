from fastapi import APIRouter, HTTPException
import os, math
from backend.src.services.portfolio import get_portfolio_equity_usd, get_current_holdings_usd
from backend.src.services.broker_alpaca import broker_singleton
from prometheus_client import Counter

router = APIRouter()
guardrail_blocks = Counter("amc_guardrail_blocks_total","Blocked trade requests",["reason"])
trade_submissions = Counter("amc_trade_submissions_total","Submitted trades",["mode","result"])

def env_i(name, default): 
    try: return int(os.getenv(name, str(default)))
    except: return int(default)
def env_f(name, default):
    try: return float(os.getenv(name, str(default)))
    except: return float(default)

@router.post("/trades/execute")
async def execute(order: dict):
    # parse input
    symbol = str(order.get("symbol","")).upper()
    action = order.get("action","BUY").upper()
    qty = float(order.get("qty") or 0)
    price = float(order.get("price") or order.get("limit_price") or 0)
    mode = order.get("mode","auto")  # "shadow" | "live" | "auto"

    # guardrails
    live = env_i("LIVE_TRADING", 0)
    kill = env_i("KILL_SWITCH", 1)
    max_pos = env_f("MAX_POSITION_USD", 100.0)
    max_alloc = env_f("MAX_PORTFOLIO_ALLOCATION_PCT", 15.0)

    if live == 1 and kill == 1:
        guardrail_blocks.labels("killswitch").inc()
        raise HTTPException(status_code=400, detail={"error":"killswitch_engaged"})

    notional = qty * price
    if notional > max_pos:
        guardrail_blocks.labels("max_position").inc()
        raise HTTPException(status_code=400, detail={"error":"max_position_exceeded","proposed":notional,"cap":max_pos})

    equity = await get_portfolio_equity_usd()
    holdings = await get_current_holdings_usd()
    cur = holdings.get(symbol, 0.0)
    prop_pct = (cur + notional) / max(equity, 1e-6) * 100.0
    if prop_pct > max_alloc:
        guardrail_blocks.labels("max_allocation").inc()
        raise HTTPException(status_code=400, detail={"error":"max_allocation_exceeded","symbol":symbol,"proposed_pct":prop_pct,"cap_pct":max_alloc})

    # decide execution mode
    effective_live = (live == 1 and kill == 0 and mode != "shadow")

    # always log to trades_log (shadow record)
    # assume you have a helper function log_shadow_trade(...)
    # await log_shadow_trade(symbol, action, qty, price, effective_live)

    if not effective_live:
        trade_submissions.labels(mode="shadow", result="accepted").inc()
        return {"mode":"shadow","accepted":True,"symbol":symbol,"qty":qty,"price":price}

    # live paper execution via Alpaca
    side = "buy" if action == "BUY" else "sell"
    tif = order.get("time_in_force","day")
    type_ = "limit" if price > 0 else "market"
    limit_price = price if type_ == "limit" else None
    result = await broker_singleton.place_order(symbol, int(math.floor(qty)), side, type_, tif, limit_price)
    ok = isinstance(result, dict) and result.get("id") is not None and result.get("status") not in ("rejected","error")
    trade_submissions.labels(mode="live", result="ok" if ok else "error").inc()
    if not ok:
        raise HTTPException(status_code=502, detail={"error":"broker_reject","broker":result})
    return {"mode":"live","accepted":True,"broker_order":result}