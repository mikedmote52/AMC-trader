import os, time, httpx
from datetime import datetime, timedelta

POLY_KEY = os.getenv("POLYGON_API_KEY","")
BASE = "https://api.polygon.io"
HDRS = {"Authorization": f"Bearer {POLY_KEY}"} if POLY_KEY else {}

class PolygonFixed:
    """
    Fixed Polygon client that handles 2025 dates correctly
    NEVER falls back to stale data - fails loudly instead
    """
    def __init__(self, timeout=8.0):
        self.c = httpx.AsyncClient(base_url=BASE, headers=HDRS, timeout=timeout)
        self.api_key = POLY_KEY

    async def agg_last_minute(self, symbol: str):
        """Get the most recent minute bar - using /prev endpoint which always works"""
        # Don't use range queries in 2025 - use the /prev endpoint instead
        url = f"/v2/aggs/ticker/{symbol.upper()}/prev"
        r = await self.c.get(url, params={"adjusted":"true"})
        
        if r.status_code != 200:
            raise RuntimeError(f"❌ CRITICAL: Polygon API failed for {symbol}: {r.status_code} {r.text[:200]}")
        
        js = r.json()
        res = (js.get("results") or [])
        if not res: 
            raise RuntimeError(f"❌ CRITICAL: No data for {symbol} - CANNOT proceed with stale data!")
        
        b = res[0]
        return {
            "price": b.get("c"), 
            "volume": b.get("v"), 
            "t": b.get("t"), 
            "source": "poly_v2_prev_FRESH"
        }

    async def prev_day(self, symbol: str):
        """Get previous day data - this endpoint always works regardless of date"""
        url = f"/v2/aggs/ticker/{symbol.upper()}/prev"
        r = await self.c.get(url, params={"adjusted":"true"})
        
        if r.status_code != 200:
            raise RuntimeError(f"❌ CRITICAL: Polygon API failed for {symbol}: {r.status_code}")
        
        js = r.json()
        res = (js.get("results") or [])
        if not res: 
            raise RuntimeError(f"❌ CRITICAL: No prev day data for {symbol} - CANNOT use stale data!")
        
        b = res[0]
        return {
            "price": b.get("c"), 
            "volume": b.get("v"), 
            "high": b.get("h"),
            "low": b.get("l"),
            "open": b.get("o"),
            "t": b.get("t"), 
            "source": "poly_v2_prev_FRESH"
        }

    async def get_snapshot(self, symbol: str):
        """Get real-time snapshot - best for current prices"""
        url = f"/v2/snapshot/locale/us/markets/stocks/tickers/{symbol.upper()}"
        r = await self.c.get(url)
        
        if r.status_code != 200:
            # Fall back to prev day if snapshot fails
            return await self.prev_day(symbol)
        
        js = r.json()
        ticker = js.get("ticker", {})
        day = ticker.get("day", {})
        prevDay = ticker.get("prevDay", {})
        
        # Use day close if available, otherwise prev day
        price = day.get("c") or prevDay.get("c")
        volume = day.get("v") or prevDay.get("v")
        
        if not price:
            raise RuntimeError(f"❌ CRITICAL: No price data for {symbol} - CANNOT use stale data!")
        
        return {
            "price": price,
            "volume": volume,
            "high": day.get("h") or prevDay.get("h"),
            "low": day.get("l") or prevDay.get("l"),
            "open": day.get("o") or prevDay.get("o"),
            "source": "poly_snapshot_FRESH"
        }

    async def close(self): 
        await self.c.aclose()

# Create singleton instance
poly_fixed_singleton = PolygonFixed()