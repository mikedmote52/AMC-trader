from backend.src.services.polygon_client import poly_singleton

async def get_price_volume(symbol: str):
    try:
        m = await poly_singleton.agg_last_minute(symbol)
        return m["price"], m["volume"], m["source"]
    except Exception:
        p = await poly_singleton.prev_day(symbol)
        return p["price"], p["volume"], p["source"]