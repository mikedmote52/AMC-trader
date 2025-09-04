import os, time, httpx

POLY_KEY = os.getenv("POLYGON_API_KEY","")
BASE = "https://api.polygon.io"
HDRS = {"Authorization": f"Bearer {POLY_KEY}"} if POLY_KEY else {}

class Polygon:
    def __init__(self, timeout=8.0):
        self.c = httpx.AsyncClient(base_url=BASE, headers=HDRS, timeout=timeout)

    async def agg_last_minute(self, symbol: str):
        # v2 aggregates, last closed 1-min bar
        now_sec = int(time.time())
        day_ago = now_sec - 24*3600
        url = f"/v2/aggs/ticker/{symbol.upper()}/range/1/min/{day_ago}/{now_sec}"
        r = await self.c.get(url, params={"adjusted":"true","sort":"desc","limit":"1"})
        r.raise_for_status()
        js = r.json()
        res = (js.get("results") or [])
        if not res: raise RuntimeError(f"no minute bars for {symbol}")
        b = res[0]
        return {"price": b.get("c"), "volume": b.get("v"), "t": b.get("t"), "source": "poly_v2_min"}

    async def prev_day(self, symbol: str):
        # v2 previous-day aggregate (stable and fast)
        url = f"/v2/aggs/ticker/{symbol.upper()}/prev"
        r = await self.c.get(url, params={"adjusted":"true"})
        r.raise_for_status()
        js = r.json()
        res = (js.get("results") or [])
        if not res: raise RuntimeError(f"no prev for {symbol}")
        b = res[0]
        return {"price": b.get("c"), "volume": b.get("v"), "t": js.get("queryCount"), "source": "poly_v2_prev"}

    async def close(self): await self.c.aclose()

poly_singleton = Polygon()