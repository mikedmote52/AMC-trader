import { useState } from "react";
import { API_BASE } from '../config';

export function TradeModal({ symbol, onClose }: { symbol: string; onClose: () => void }) {
  const [amount, setAmount] = useState(100);        // dollar notional
  const [shares, setShares] = useState<string>(""); // optional share override
  const [orderType, setOrderType] = useState<"market"|"limit">("market");
  const [limitPrice, setLimitPrice] = useState<string>("");
  const [useBracket, setUseBracket] = useState(false);
  const [tpPct, setTpPct] = useState<string>("");   // e.g. 5 for 5%
  const [slPct, setSlPct] = useState<string>("");   // e.g. 3 for 3%
  const [tpAbs, setTpAbs] = useState<string>("");
  const [slAbs, setSlAbs] = useState<string>("");
  const [msg, setMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit() {
    setLoading(true); setMsg(null);
    try {
      const body:any = {
        symbol: symbol.toUpperCase(),
        action: "BUY",
        mode: "live",
        order_type: orderType,
        time_in_force: "day",
      };
      if (shares && Number(shares) > 0) body.qty = Number(shares);
      else body.notional_usd = Number(amount);
      if (orderType === "limit" && limitPrice) body.price = Number(limitPrice);
      if (useBracket) {
        body.bracket = true;
        if (tpPct) body.take_profit_pct = Number(tpPct) / 100.0;
        if (slPct) body.stop_loss_pct = Number(slPct) / 100.0;
        if (tpAbs) body.take_profit_price = Number(tpAbs);
        if (slAbs) body.stop_loss_price = Number(slAbs);
      }
      const r = await fetch(`${API_BASE}/trades/execute`, {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify(body)
      });
      const json = await r.json();
      if (!r.ok) throw json;
      
      // Extract order_id from response and display it
      const orderId = json?.execution_result?.alpaca_order_id || json?.order_id || json?.id;
      const baseMsg = json?.execution_result?.alpaca_order_id ? "Live order submitted" : "Order accepted";
      setMsg(orderId ? `${baseMsg} (Order ID: ${orderId})` : baseMsg);
      
      // Trigger a holdings refresh by dispatching a custom event
      window.dispatchEvent(new CustomEvent('holdingsRefresh'));
    } catch (e:any) {
      const err = e?.error || e?.detail || e;
      setMsg(typeof err === "string" ? err : JSON.stringify(err));
    } finally { setLoading(false); }
  }

  return (
    <div className="p-4 rounded-xl border bg-white/5 space-y-3">
      <div className="text-lg font-semibold">Buy {symbol.toUpperCase()}</div>
      <div className="flex flex-wrap gap-2">
        <input className="px-3 py-2 rounded border bg-white/10 w-32" type="number" min="1"
               value={amount} onChange={(e)=>setAmount(Number(e.target.value||0))} placeholder="$ Notional"/>
        <span>or</span>
        <input className="px-3 py-2 rounded border bg-white/10 w-24" type="number" min="1"
               value={shares} onChange={(e)=>setShares(e.target.value)} placeholder="# shares"/>
      </div>
      <div className="flex gap-2 items-center">
        <select className="px-3 py-2 rounded border bg-white/10" value={orderType} onChange={(e)=>setOrderType(e.target.value as any)}>
          <option value="market">Market</option>
          <option value="limit">Limit</option>
        </select>
        {orderType === "limit" && (
          <input className="px-3 py-2 rounded border bg-white/10 w-28" type="number" min="0"
                 value={limitPrice} onChange={(e)=>setLimitPrice(e.target.value)} placeholder="Limit"/>
        )}
      </div>
      <label className="flex items-center gap-2">
        <input type="checkbox" checked={useBracket} onChange={(e)=>setUseBracket(e.target.checked)} />
        Add take-profit / stop-loss
      </label>
      {useBracket && (
        <div className="grid grid-cols-2 gap-2">
          <input className="px-3 py-2 rounded border bg-white/10" type="number" min="0"
                 value={tpPct} onChange={(e)=>setTpPct(e.target.value)} placeholder="TP % (e.g. 5)"/>
          <input className="px-3 py-2 rounded border bg-white/10" type="number" min="0"
                 value={slPct} onChange={(e)=>setSlPct(e.target.value)} placeholder="SL % (e.g. 3)"/>
          <input className="px-3 py-2 rounded border bg-white/10" type="number" min="0"
                 value={tpAbs} onChange={(e)=>setTpAbs(e.target.value)} placeholder="TP price (optional)"/>
          <input className="px-3 py-2 rounded border bg-white/10" type="number" min="0"
                 value={slAbs} onChange={(e)=>setSlAbs(e.target.value)} placeholder="SL price (optional)"/>
        </div>
      )}
      <div className="flex gap-2">
        <button onClick={submit} disabled={loading}
                className="px-3 py-2 rounded bg-black text-white disabled:opacity-50">
          {loading ? "Submitting..." : "Submit order"}
        </button>
        <button onClick={onClose} className="px-3 py-2 rounded border">Close</button>
      </div>
      {msg && <div className="text-sm break-all">{msg}</div>}
    </div>
  );
}