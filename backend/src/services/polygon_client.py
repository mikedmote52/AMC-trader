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

    async def get_bars(self, symbol: str, timespan: str = "day", limit: int = 20):
        """
        Fetch historical bars from Polygon API

        NO MOCK DATA - Returns None if data unavailable

        Args:
            symbol: Stock ticker
            timespan: 'day', 'hour', 'minute'
            limit: Number of bars to fetch

        Returns:
            List of bars with {c: close, v: volume, t: timestamp} or None
        """
        try:
            from datetime import datetime, timedelta

            # Calculate date range (add buffer for weekends/holidays)
            to_date = datetime.now()
            from_date = to_date - timedelta(days=limit + 10)

            from_ts = int(from_date.timestamp() * 1000)
            to_ts = int(to_date.timestamp() * 1000)

            url = f"/v2/aggs/ticker/{symbol.upper()}/range/1/{timespan}/{from_ts}/{to_ts}"
            r = await self.c.get(url, params={"adjusted": "true", "sort": "asc", "limit": limit + 5})
            r.raise_for_status()

            js = r.json()
            results = js.get("results") or []

            if not results:
                return None  # NO FAKE DATA - return None if no data

            return results

        except Exception:
            return None  # NO FAKE DATA - return None on error

    async def close(self): await self.c.aclose()

poly_singleton = Polygon()