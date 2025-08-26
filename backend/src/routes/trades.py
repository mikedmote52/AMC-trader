from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
import os, math, httpx
from prometheus_client import Counter
from typing import Literal, Optional
from backend.src.services.polygon_client import poly_singleton

router = APIRouter()

# Prometheus
guardrail_blocks = Counter("amc_guardrail_blocks_total","Trade blocks by guardrails",["reason"])
trade_submissions = Counter("amc_trade_submissions_total","Submitted trades",["mode","result"])

# --- SCHEMA ---

Mode = Literal["live","shadow","auto"]
Action = Literal["BUY","SELL"]
TIF = Literal["day","gtc","opg","cls","ioc","fok"]  # common Alpaca TIFs

class TradeReq(BaseModel):
    symbol: str = Field(..., description="Ticker symbol, e.g. NVDA")
    action: Action = Field("BUY", description="BUY or SELL")
    mode: Mode = Field("auto", description="live|shadow|auto")
    qty: Optional[int] = Field(None, ge=1, description="Whole shares to trade")
    price: Optional[float] = Field(None, ge=0, description="Limit price; omit for market")
    notional_usd: Optional[float] = Field(None, ge=1, description="Dollar sizing if qty omitted")
    time_in_force: TIF = Field("day")

    @field_validator("symbol")
    @classmethod
    def upcase(cls, v): return v.upper()

class ExecResult(BaseModel):
    status: str
    alpaca_order_id: Optional[str] = None
    execution_mode: Literal["live","shadow"]
    message: Optional[str] = None
    raw: Optional[dict] = None

class TradeResp(BaseModel):
    success: bool
    mode: Literal["live","shadow"]
    execution_result: Optional[ExecResult] = None
    error: Optional[dict] = None

# --- ROUTE ---

@router.post("/trades/execute", response_model=TradeResp, responses={
    400: {"description":"Guardrail or validation block"},
    502: {"description":"Broker error"},
})
async def execute(req: TradeReq):
    # env + mode decision
    live = int(os.getenv("LIVE_TRADING","0"))
    kill = int(os.getenv("KILL_SWITCH","1"))
    _EFFECTIVE = "shadow" if not (live==1 and kill==0) else ("shadow" if req.mode=="shadow" else "live")

    # derive qty (allow notional)
    qty = req.qty
    px  = float(req.price or 0.0)
    if qty is None:
        if req.notional_usd is None:
            raise HTTPException(status_code=400, detail={"error":"missing_qty_or_notional"})
        if px <= 0:
            try:
                m = await poly_singleton.agg_last_minute(req.symbol)
                px = float(m.get("price") or 0.0)
            except Exception:
                p = await poly_singleton.prev_day(req.symbol)
                px = float(p.get("price") or 0.0)
        qty = max(1, int(req.notional_usd // max(px, 1e-6)))

    # guardrails (keep simple notional cap; allocation optional)
    max_pos = float(os.getenv("MAX_POSITION_USD","100"))
    notional = (px if px>0 else 0.0) * qty
    if notional > 0 and notional > max_pos:
        guardrail_blocks.labels("max_position").inc()
        raise HTTPException(status_code=400, detail={"error":"max_position_exceeded","proposed":notional,"cap":max_pos})

    # shadow path
    if _EFFECTIVE != "live":
        trade_submissions.labels(mode="shadow", result="accepted").inc()
        return TradeResp(success=True, mode="shadow",
            execution_result=ExecResult(status="shadow_logged", execution_mode="shadow", message="Shadow trade recorded."),
        )

    # live broker call
    headers = {
        "APCA-API-KEY-ID": os.getenv("ALPACA_API_KEY",""),
        "APCA-API-SECRET-KEY": os.getenv("ALPACA_API_SECRET",""),
        "content-type": "application/json",
    }
    side = "buy" if req.action=="BUY" else "sell"
    type_ = "limit" if px > 0 else "market"
    payload = {"symbol": req.symbol, "qty": int(qty), "side": side, "type": type_, "time_in_force": req.time_in_force}
    if px > 0: payload["limit_price"] = px

    try:
        async with httpx.AsyncClient(base_url=os.getenv("ALPACA_BASE_URL","https://paper-api.alpaca.markets"), headers=headers, timeout=10.0) as c:
            r = await c.post("/v2/orders", json=payload)
        if r.status_code >= 400:
            trade_submissions.labels(mode="live", result="error").inc()
            body = r.json() if "json" in r.headers.get("content-type","") else {"text": r.text}
            raise HTTPException(status_code=502, detail={"error":"broker_reject","status":r.status_code,"body":body})
        j = r.json()
        trade_submissions.labels(mode="live", result="ok").inc()
        return TradeResp(success=True, mode="live",
            execution_result=ExecResult(status=j.get("status","submitted"), alpaca_order_id=j.get("id"), execution_mode="live", raw=j)
        )
    except httpx.HTTPError as e:
        trade_submissions.labels(mode="live", result="error").inc()
        raise HTTPException(status_code=502, detail={"error":"broker_http_error","message":str(e)})

# OpenAPI examples
example_market = {
 "summary":"Market buy by shares",
 "value":{"symbol":"QUBT","action":"BUY","mode":"live","qty":1}
}
example_limit = {
 "summary":"Limit buy by shares",
 "value":{"symbol":"QUBT","action":"BUY","mode":"live","qty":1,"price":1.00,"time_in_force":"day"}
}
example_notional = {
 "summary":"Dollar-sized buy",
 "value":{"symbol":"QUBT","action":"BUY","mode":"live","notional_usd":25}
}
execute.__dict__["__docs_examples__"]= [example_market, example_limit, example_notional]  # Fast hack to carry examples