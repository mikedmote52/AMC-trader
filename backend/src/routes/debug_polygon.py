from fastapi import APIRouter, HTTPException
from backend.src.services.polygon_client import poly_singleton
router = APIRouter(prefix="/debug/polygon")

@router.get("/ping")
async def ping():
    try:
        p = await poly_singleton.prev_day("AAPL")
        m = await poly_singleton.agg_last_minute("AAPL")
        return {"ok": True, "prev_sample": p, "min_sample": m}
    except Exception as e:
        raise HTTPException(status_code=502, detail={"error":"polygon_probe_failed","message":str(e)})