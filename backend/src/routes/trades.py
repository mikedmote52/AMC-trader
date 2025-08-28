from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
import os, math, httpx, json
from prometheus_client import Counter
from typing import Literal, Optional
from backend.src.services.polygon_client import poly_singleton
from backend.src.shared.redis_client import get_redis_client

router = APIRouter()

# Price cap configuration
PRICE_CAP = float(os.getenv("AMC_PRICE_CAP", "100"))

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
        # --- deterministic mode decision ---
        live = int(os.getenv("LIVE_TRADING","0"))
        kill = int(os.getenv("KILL_SWITCH","1"))
        req_mode = (req.mode or "auto").lower()

        # If trading is enabled and killswitch is off, go live unless the client explicitly asks for shadow.
        if live == 1 and kill == 0:
            effective_mode = "shadow" if req_mode == "shadow" else "live"
        else:
            effective_mode = "shadow"
        # -----------------------------------

        # Fetch latest price for price cap validation
        latest_price = 0.0
        if req.price and req.price > 0:
            latest_price = float(req.price)
        else:
            try:
                m = await poly_singleton.agg_last_minute(req.symbol)
                latest_price = float(m.get("price") or 0.0)
            except Exception:
                try:
                    p = await poly_singleton.prev_day(req.symbol)
                    latest_price = float(p.get("price") or 0.0)
                except Exception:
                    pass

        # Price cap guards
        if latest_price > PRICE_CAP:
            guardrail_blocks.labels("price_cap_exceeded").inc()
            raise HTTPException(status_code=400, detail={
                "success": False,
                "error": "price_cap_exceeded",
                "price": latest_price,
                "cap": PRICE_CAP
            })
        
        if req.notional_usd and req.notional_usd > PRICE_CAP:
            guardrail_blocks.labels("price_cap_exceeded").inc()
            raise HTTPException(status_code=400, detail={
                "success": False,
                "error": "price_cap_exceeded",
                "price": req.notional_usd,
                "cap": PRICE_CAP
            })
        
        if req.qty and latest_price > 0 and (req.qty * latest_price) > PRICE_CAP:
            guardrail_blocks.labels("price_cap_exceeded").inc()
            raise HTTPException(status_code=400, detail={
                "success": False,
                "error": "qty_total",
                "price": req.qty * latest_price,
                "cap": PRICE_CAP
            })

        # derive qty (allow notional)
        qty = req.qty
        px  = float(req.price or latest_price or 0.0)
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
        if effective_mode != "live":
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
            tp_pct = req.take_profit_pct
            sl_pct = req.stop_loss_pct
            
            # If bracket True and no TP/SL provided, prefill from contenders
            if not any([tp_price, sl_price, tp_pct, sl_pct]):
                try:
                    redis_client = get_redis_client()
                    contenders_data = redis_client.get("amc:discovery:contenders.latest")
                    if contenders_data:
                        contenders = json.loads(contenders_data)
                        for contender in contenders:
                            if isinstance(contender, dict) and contender.get("symbol") == req.symbol:
                                if not sl_pct and contender.get("stop_loss_pct"):
                                    sl_pct = float(contender["stop_loss_pct"])
                                if not sl_price and contender.get("stop_price"):
                                    sl_price = float(contender["stop_price"])
                                if not tp_pct and contender.get("take_profit_pct"):
                                    tp_pct = float(contender["take_profit_pct"])
                                if not tp_price and contender.get("take_profit_price"):
                                    tp_price = float(contender["take_profit_price"])
                                break
                except Exception:
                    pass  # Continue with defaults if Redis lookup fails
            
            if tp_price is None and tp_pct:
                tp_price = round(ref_px * (1.0 + float(tp_pct)), 2)
            if sl_price is None and sl_pct:
                sl_price = round(ref_px * (1.0 - float(sl_pct)), 2)
            
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

# --- POSITION-SPECIFIC TRADE SCHEMAS ---

class PositionTradeReq(BaseModel):
    symbol: str = Field(..., description="Ticker symbol")
    action: Literal["TAKE_PROFITS", "TRIM_POSITION", "ADD_POSITION", "EXIT_POSITION"] = Field(..., description="Position-specific action")
    mode: Mode = Field("auto", description="live|shadow|auto") 
    percentage: Optional[float] = Field(None, ge=0.01, le=1.0, description="Percentage for trim/take profits (0.25 = 25%)")
    notional_usd: Optional[float] = Field(None, ge=1, description="Dollar amount for add position")
    time_in_force: TIF = Field("day")
    
    @field_validator("symbol")
    @classmethod
    def upcase(cls, v): return v.upper()

class PositionTradeResp(BaseModel):
    success: bool
    symbol: str
    action: str
    calculated_qty: Optional[int] = None
    current_position: Optional[dict] = None
    execution_result: Optional[ExecResult] = None
    error: Optional[dict] = None
    message: Optional[str] = None

# --- POSITION-SPECIFIC TRADE ROUTES ---

@router.post("/trades/position", response_model=PositionTradeResp, responses={
    400: {"description": "Invalid position or calculation error"},
    404: {"description": "Position not found"},
    502: {"description": "Broker error"},
})
async def execute_position_trade(req: PositionTradeReq):
    """Execute position-specific trades with smart quantity calculations"""
    try:
        # Get current position from broker
        try:
            from backend.src.services.broker_alpaca import AlpacaBroker
            broker = AlpacaBroker()
            positions = await broker.get_positions()
            current_position = next((p for p in positions if p.get("symbol") == req.symbol), None)
            
            if not current_position:
                raise HTTPException(status_code=404, detail={
                    "error": "position_not_found",
                    "symbol": req.symbol,
                    "message": f"No current position found for {req.symbol}"
                })
        except ImportError:
            raise HTTPException(status_code=500, detail={
                "error": "broker_unavailable",
                "message": "Alpaca broker service unavailable"
            })
        
        # Extract position data
        current_qty = int(float(current_position.get("qty", 0)))
        current_price = float(current_position.get("current_price", 0))
        
        if current_qty <= 0:
            raise HTTPException(status_code=400, detail={
                "error": "invalid_position", 
                "message": f"Invalid position quantity: {current_qty}"
            })
        
        # Calculate trade quantities based on action
        calculated_qty = 0
        trade_action = "SELL"  # Default for most position actions
        
        if req.action == "TAKE_PROFITS":
            # Sell 50% of position to lock in gains
            percentage = req.percentage or 0.5
            calculated_qty = max(1, int(current_qty * percentage))
            trade_action = "SELL"
            
        elif req.action == "TRIM_POSITION":
            # Sell 25% of position (or custom percentage)
            percentage = req.percentage or 0.25
            calculated_qty = max(1, int(current_qty * percentage))
            trade_action = "SELL"
            
        elif req.action == "EXIT_POSITION":
            # Sell entire position
            calculated_qty = current_qty
            trade_action = "SELL"
            
        elif req.action == "ADD_POSITION":
            # Buy more shares with dollar amount
            if req.notional_usd:
                calculated_qty = max(1, int(req.notional_usd / max(current_price, 0.01)))
            else:
                # Default to $500 if no amount specified
                calculated_qty = max(1, int(500 / max(current_price, 0.01)))
            trade_action = "BUY"
        
        # Create standard trade request
        trade_req = TradeReq(
            symbol=req.symbol,
            action=trade_action,
            mode=req.mode,
            qty=calculated_qty,
            time_in_force=req.time_in_force
        )
        
        # Execute the trade using existing logic
        trade_response = await execute(trade_req)
        
        return PositionTradeResp(
            success=trade_response.success,
            symbol=req.symbol,
            action=req.action,
            calculated_qty=calculated_qty,
            current_position={
                "qty": current_qty,
                "current_price": current_price,
                "market_value": float(current_position.get("market_value", 0)),
                "unrealized_pl": float(current_position.get("unrealized_pl", 0))
            },
            execution_result=trade_response.execution_result,
            error=trade_response.error,
            message=f"{req.action}: {trade_action} {calculated_qty} shares of {req.symbol}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": "execution_error",
            "message": str(e)
        })

@router.get("/trades/position/{symbol}/preview")
async def preview_position_trades(symbol: str):
    """Preview possible position trades for a symbol"""
    try:
        symbol = symbol.upper()
        
        # Get current position
        try:
            from backend.src.services.broker_alpaca import AlpacaBroker
            broker = AlpacaBroker()
            positions = await broker.get_positions()
            current_position = next((p for p in positions if p.get("symbol") == symbol), None)
            
            if not current_position:
                return {
                    "symbol": symbol,
                    "has_position": False,
                    "message": f"No current position found for {symbol}"
                }
                
        except ImportError:
            raise HTTPException(status_code=500, detail={
                "error": "broker_unavailable"
            })
        
        # Calculate preview data
        current_qty = int(float(current_position.get("qty", 0)))
        current_price = float(current_position.get("current_price", 0))
        market_value = float(current_position.get("market_value", 0))
        unrealized_pl = float(current_position.get("unrealized_pl", 0))
        
        # Calculate trade previews
        take_profits_qty = max(1, int(current_qty * 0.5))  # 50%
        trim_qty = max(1, int(current_qty * 0.25))  # 25%
        add_position_qty_500 = max(1, int(500 / max(current_price, 0.01)))
        add_position_qty_1000 = max(1, int(1000 / max(current_price, 0.01)))
        
        return {
            "symbol": symbol,
            "has_position": True,
            "current_position": {
                "qty": current_qty,
                "current_price": round(current_price, 2),
                "market_value": round(market_value, 2),
                "unrealized_pl": round(unrealized_pl, 2),
                "unrealized_pl_pct": round((unrealized_pl / max(market_value - unrealized_pl, 0.01)) * 100, 2)
            },
            "trade_options": {
                "take_profits": {
                    "action": "SELL",
                    "qty": take_profits_qty,
                    "percentage": 50,
                    "estimated_proceeds": round(take_profits_qty * current_price, 2),
                    "remaining_qty": current_qty - take_profits_qty
                },
                "trim_position": {
                    "action": "SELL", 
                    "qty": trim_qty,
                    "percentage": 25,
                    "estimated_proceeds": round(trim_qty * current_price, 2),
                    "remaining_qty": current_qty - trim_qty
                },
                "exit_position": {
                    "action": "SELL",
                    "qty": current_qty,
                    "percentage": 100,
                    "estimated_proceeds": round(market_value, 2),
                    "remaining_qty": 0
                },
                "add_position_500": {
                    "action": "BUY",
                    "qty": add_position_qty_500,
                    "notional": 500,
                    "new_total_qty": current_qty + add_position_qty_500
                },
                "add_position_1000": {
                    "action": "BUY", 
                    "qty": add_position_qty_1000,
                    "notional": 1000,
                    "new_total_qty": current_qty + add_position_qty_1000
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": "preview_error",
            "message": str(e)
        })

# Helper functions for polygon data
async def polygon_last_price(symbol: str) -> float:
    """Get latest price from polygon"""
    try:
        m = await poly_singleton.agg_last_minute(symbol)
        return float(m.get("price") or 0.0)
    except Exception:
        try:
            p = await poly_singleton.prev_day(symbol)
            return float(p.get("price") or 0.0)
        except Exception:
            return 0.0

async def polygon_atr_pct(symbol: str) -> Optional[float]:
    """Calculate ATR percentage from polygon bars"""
    try:
        bars_data = await poly_singleton.get_bars(symbol, timespan="day", limit=14)
        if not bars_data or len(bars_data) < 2:
            return None
        
        trs = []
        for i in range(1, len(bars_data)):
            prev_close = bars_data[i-1].get("c", 0)
            high = bars_data[i].get("h", 0)
            low = bars_data[i].get("l", 0)
            tr = max(
                high - low,
                abs(high - prev_close) if prev_close else 0,
                abs(low - prev_close) if prev_close else 0
            )
            trs.append(tr)
        
        if trs and bars_data[-1].get("c"):
            atr = sum(trs) / len(trs)
            return atr / float(bars_data[-1]["c"])
    except Exception:
        pass
    return None

@router.get("/defaults/{symbol}")
async def trade_defaults(symbol: str):
    sym = symbol.upper()
    r = get_redis_client()
    items = json.loads(r.get("amc:discovery:v2:contenders.latest") or r.get("amc:discovery:contenders.latest") or "[]")
    c = next((i for i in items if i.get("symbol")==sym), None)
    if c:
        return {
          "symbol": sym, "order_type":"market","time_in_force":"day","mode":"live","bracket": True,
          "stop_loss_pct": c.get("stop_loss_pct"), "take_profit_pct": c.get("take_profit_pct"),
          "stop_price": c.get("stop_price"), "take_profit_price": c.get("take_profit_price"),
          "r_multiple": c.get("r_multiple"), "last_price": c.get("price"),
          "price_cap": float(os.getenv("AMC_PRICE_CAP","100"))
        }
    # fallback: compute ATR based levels quickly
    # return a safe set if polygon fails
    last = await polygon_last_price(sym)
    atrp = await polygon_atr_pct(sym) or 0.04
    risk = max(last*float(os.getenv("AMC_MIN_STOP_PCT","0.02")), last*atrp*float(os.getenv("AMC_ATR_STOP_MULT","1.5")))
    return {
      "symbol": sym, "order_type":"market","time_in_force":"day","mode":"live","bracket": True,
      "stop_price": round(max(0.01, last-risk),2),
      "take_profit_price": round(last+float(os.getenv("AMC_R_MULT","2.0"))*risk,2),
      "last_price": last, "price_cap": float(os.getenv("AMC_PRICE_CAP","100"))
    }