import os, httpx, asyncio

ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
ALPACA_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET = os.getenv("ALPACA_API_SECRET", "")

class AlpacaBroker:
    def __init__(self):
        headers = {
            "APCA-API-KEY-ID": ALPACA_KEY,
            "APCA-API-SECRET-KEY": ALPACA_SECRET,
            "Content-Type": "application/json",
        }
        self.client = httpx.AsyncClient(base_url=ALPACA_BASE_URL, headers=headers, timeout=10.0)

    async def get_account(self):
        r = await self.client.get("/v2/account")
        r.raise_for_status()
        return r.json()

    async def place_order(self, symbol: str, qty: int, side: str, type_: str, tif: str, limit_price=None):
        payload = {"symbol": symbol, "qty": qty, "side": side, "type": type_, "time_in_force": tif}
        if limit_price is not None:
            payload["limit_price"] = limit_price
        r = await self.client.post("/v2/orders", json=payload)
        if r.status_code >= 400:
            return {"status": "error", "broker_status": r.status_code, "broker_body": r.text}
        return r.json()

    async def close(self):
        await self.client.aclose()

broker_singleton = AlpacaBroker()