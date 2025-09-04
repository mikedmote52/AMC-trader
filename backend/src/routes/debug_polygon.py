from fastapi import APIRouter, HTTPException
from backend.src.services.polygon_client_fixed import poly_fixed_singleton
router = APIRouter(prefix="/debug/polygon")

@router.get("/ping")
async def ping():
    try:
        p = await poly_fixed_singleton.prev_day("AAPL")
        s = await poly_fixed_singleton.get_snapshot("AAPL")
        return {"ok": True, "prev_sample": p, "snapshot_sample": s}
    except Exception as e:
        raise HTTPException(status_code=502, detail={"error":"polygon_probe_failed","message":str(e)})