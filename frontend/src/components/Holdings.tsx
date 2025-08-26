import React, { useEffect, useState } from "react";
import { API_BASE } from "../config";
import { getJSON } from "../lib/api";

type Holding = {
  symbol: string;
  qty?: number;
  quantity?: number;
  last_price?: number;
  market_value?: number;
  unrealized_pl?: number;
  unrealized_pl_pct?: number;
  thesis?: string | null;
  suggestion?: string | null;
};

export default function Holdings() {
  const [items, setItems] = useState<Holding[]>([]);
  const [err, setErr] = useState<string>("");

  async function run() {
    try {
      setErr("");
      const data = await getJSON<any>(`${API_BASE}/portfolio/holdings`);
      setItems(Array.isArray(data) ? data : []);
    } catch (e:any) {
      setErr(e?.message || String(e));
    }
  }

  useEffect(() => { run(); const id = setInterval(run, 30000); return ()=>clearInterval(id); }, []);

  if (err) return <div style={{padding:12, color:"#c00"}}>Error loading holdings: {err}</div>;
  if (!items.length) return <div style={{padding:12}}>No holdings found.</div>;

  return (
    <div style={{display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(320px, 1fr))", gap:12}}>
      {items.map((h) => {
        const shares = h.qty ?? h.quantity ?? 0;
        const px = h.last_price ?? 0;
        const mv = h.market_value ?? 0;
        const pl = h.unrealized_pl ?? 0;
        const plPct = h.unrealized_pl_pct ?? 0;
        return (
          <div key={h.symbol} style={{border:"1px solid #222", borderRadius:14, padding:14, background:"#0d0f12", color:"#e7e7e7"}}>
            <div style={{display:"flex", justifyContent:"space-between"}}>
              <div style={{fontWeight:700}}>{h.symbol}</div>
              <div style={{fontSize:12, opacity:.8}}>{shares} sh</div>
            </div>
            <div style={{marginTop:6, fontSize:13, opacity:.8}}>
              Price ${px.toFixed(2)} · Value ${mv.toFixed(2)}
            </div>
            <div style={{marginTop:6, fontSize:13, color: pl>=0 ? "#22c55e" : "#ef4444"}}>
              P/L ${pl.toFixed(2)} ({(plPct*100).toFixed(1)}%)
            </div>
            {h.suggestion || h.thesis ? (
              <div style={{marginTop:8, fontSize:12, color:"#bbb"}}>
                {h.suggestion ? <div>Suggestion: {h.suggestion}</div> : null}
                {h.thesis ? <div>Thesis: {h.thesis}</div> : null}
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}