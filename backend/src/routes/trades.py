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
    order_type: Literal["market","limit"] = Field("market", description="Order type")
    bracket: Optional[bool] = Field(False, description="Enable bracket order")
    take_profit_pct: Optional[float] = Field(None, description="Take profit as % gain, e.g. 0.05 for +5%")
    stop_loss_pct: Optional[float] = Field(None, description="Stop loss as % loss, e.g. 0.03 for -3%")
    take_profit_price: Optional[float] = Field(None, description="Absolute take profit price")
    stop_loss_price: Optional[float] = Field(None, description="Absolute stop loss price")

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
    handler_tag: Optional[str] = None

# --- ROUTE ---

@router.post("/trades/execute", response_model=TradeResp, responses={
    400: {"description":"Guardrail or validation block"},
    502: {"description":"Broker error"},
})
async def execute(req: TradeReq):
    try:
        # env + mode decision
        live = int(os.getenv("LIVE_TRADING","0"))
        kill = int(os.getenv("KILL_SWITCH","1"))
        _EFFECTIVE = "shadow" if not (live==1 and kill==0) else ("shadow" if req.mode=="shadow" else "live")

        # derive qty (allow notional)
        qty = req.qty
        px  = float(req.price or 0.0)
        if qty is None:
            if req.notional_usd is None:
                raise HTTPException(status_code=400, detail={
                    "error":"missing_qty_or_notional",
                    "handler_tag": "trace_v1"
                })
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
            raise HTTPException(status_code=400, detail={
                "error":"max_position_exceeded",
                "proposed":notional,
                "cap":max_pos,
                "handler_tag": "trace_v1"
            })

        # shadow path
        if _EFFECTIVE != "live":
            trade_submissions.labels(mode="shadow", result="accepted").inc()
            return TradeResp(
                success=True, 
                mode="shadow",
                execution_result=ExecResult(
                    status="shadow_logged", 
                    execution_mode="shadow", 
                    message="Shadow trade recorded."
                ),
                handler_tag="trace_v1"
            )

        # build Alpaca payload
        side = "buy" if req.action=="BUY" else "sell"
        type_ = req.order_type if req.order_type in ("market","limit") else ("limit" if px>0 else "market")
        payload = {
            "symbol": req.symbol,
            "qty": int(qty),
            "side": side,
            "type": type_,
            "time_in_force": req.time_in_force,
        }
        
        if type_ == "limit":
            payload["limit_price"] = float(px)
        
        # bracket computation
        if req.bracket:
            # ensure we have a reference price for pct math
            ref_px = float(px) if px and px > 0 else float(px or 0.0)
            if ref_px <= 0:
                try:
                    m = await poly_singleton.agg_last_minute(req.symbol)
                    ref_px = float(m.get("price") or 0.0)
                except Exception:
                    p = await poly_singleton.prev_day(req.symbol)
                    ref_px = float(p.get("price") or 0.0)
            
            tp_price = req.take_profit_price
            sl_price = req.stop_loss_price
            if tp_price is None and req.take_profit_pct:
                tp_price = round(ref_px * (1.0 + float(req.take_profit_pct)), 2)
            if sl_price is None and req.stop_loss_pct:
                sl_price = round(ref_px * (1.0 - float(req.stop_loss_pct)), 2)
            
            # build Alpaca bracket
            payload["order_class"] = "bracket"
            if tp_price:
                payload["take_profit"] = {"limit_price": float(tp_price)}
            if sl_price:
                # use stop_price, optional limit for stop-limit; start with stop only
                payload["stop_loss"] = {"stop_price": float(sl_price)}
        
        # live broker call
        headers = {
            "APCA-API-KEY-ID": os.getenv("ALPACA_API_KEY",""),
            "APCA-API-SECRET-KEY": os.getenv("ALPACA_API_SECRET",""),
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(base_url=os.getenv("ALPACA_BASE_URL","https://paper-api.alpaca.markets"), headers=headers, timeout=10.0) as c:
            r = await c.post("/v2/orders", json=payload)
        if r.status_code >= 400:
            trade_submissions.labels(mode="live", result="error").inc()
            body = r.json() if "json" in r.headers.get("content-type","") else {"text": r.text}
            raise HTTPException(status_code=502, detail={
                "error":"broker_reject",
                "status":r.status_code,
                "body":body,
                "handler_tag": "trace_v1"
            })
        j = r.json()
        trade_submissions.labels(mode="live", result="ok").inc()
        return TradeResp(
            success=True, 
            mode="live",
            execution_result=ExecResult(
                status=j.get("status","submitted"), 
                alpaca_order_id=j.get("id"), 
                execution_mode="live", 
                raw=j
            ),
            handler_tag="trace_v1"
        )
        
    except HTTPException:
        # if we already raised with detail above, let it propagate
        raise
    except Exception as e:
        # anything unexpected becomes a 500 with a visible message and tag
        raise HTTPException(status_code=500, detail={
            "error": "unhandled_exception",
            "message": str(e),
            "handler_tag": "trace_v1"
        })

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
example_bracket = {
 "summary":"Bracket order with stop loss and take profit",
 "value":{"symbol":"QUBT","action":"BUY","mode":"live","qty":10,"bracket":True,"take_profit_pct":0.05,"stop_loss_pct":0.03}
}
execute.__dict__["__docs_examples__"]= [example_market, example_limit, example_notional, example_bracket]  # Fast hack to carry examples