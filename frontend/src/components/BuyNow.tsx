import { useEffect, useMemo, useRef, useState } from "react";
import { TradeModal } from "./TradeModal";
import { API_BASE } from '../config';

type Rec = { 
  symbol?: string; 
  ticker?: string; 
  action?: string; 
  decision?: string; 
  recommendation?: string; 
  score?: number; 
  confidence?: number; 
  signal?: number; 
  risk?: number; 
  risk_score?: number; 
  reason?: string; 
  notes?: string; 
  rationale?: string;
  price?: number;
  last?: number;
};


function QuickBuy() {
  const [symbol, setSymbol] = useState("");
  const [open, setOpen] = useState(false);

  return (
    <div className="flex items-center gap-2 mb-3">
      <input
        value={symbol}
        onChange={(e) => setSymbol(e.target.value)}
        placeholder="Symbol e.g. AAPL"
        className="px-3 py-2 rounded border bg-white/10"
      />
      <button
        onClick={() => symbol.trim() && setOpen(true)}
        disabled={!symbol.trim()}
        className="px-3 py-2 rounded bg-black text-white disabled:opacity-50"
      >
        Buy
      </button>
      {open && <TradeModal symbol={symbol.trim()} onClose={() => setOpen(false)} />}
    </div>
  );
}

export function BuyNowRow({ rec }: { rec: Rec }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="flex items-center gap-3">
      <span className="font-medium">{rec.symbol}</span>
      <button className="px-3 py-1 rounded bg-black text-white" onClick={()=>setOpen(true)}>Buy</button>
      {open && <TradeModal symbol={rec.symbol || rec.ticker || ""} onClose={()=>setOpen(false)} />}
    </div>
  );
}

export default function BuyNow() {
  const [recs, setRecs] = useState<Rec[]>([]);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<number | null>(null);

  async function load() { 
    try { 
      const r = await fetch(`${API_BASE}/discovery/contenders`); 
      if (!r.ok) throw new Error(`HTTP ${r.status}`); 
      const data = await r.json(); 
      setRecs(Array.isArray(data) ? data : []); 
      setError(null);
    } catch (e: any) { 
      setError(e?.message || "Failed to load");
    }
  }

  useEffect(() => { 
    load(); 
    timer.current = window.setInterval(load, 15000); 
    return () => { 
      if (timer.current) window.clearInterval(timer.current);
    };
  }, []);

  const buys = useMemo(() => { 
    return recs.filter(r => { 
      // before: rec.action === "BUY" && rec.score >= 0.6 && rec.risk <= 0.5
      const qualifies = (r.action ?? r.decision ?? "BUY") === "BUY";
      return qualifies;
    }).sort((a, b) => (Number(b.score ?? b.confidence ?? b.signal ?? 0)) - (Number(a.score ?? a.confidence ?? a.signal ?? 0))).slice(0, 10); 
  }, [recs]);

  return (
    <div className="rounded-2xl shadow p-4 bg-white/80 dark:bg-zinc-900/60 border border-black/10">
      <div className="text-xl font-semibold mb-2">Buy Now</div>
      <QuickBuy />
      {error && <div className="text-red-600 text-sm mb-2">Error: {error}</div>}
      {buys.length === 0 ? (
        <div className="text-sm opacity-70">No qualifying buys right now. This updates every ~15s.</div>
      ) : (
        <ul className="divide-y divide-black/5">
          {buys.map((r, i) => { 
            const ticker = r.symbol || r.ticker || "—"; 
            const score = Number(r.score ?? r.confidence ?? r.signal ?? 0); 
            const note = r.reason || r.notes || r.rationale || ""; 
            return (
              <li key={i} className="py-2">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex flex-col">
                    <span className="font-medium">{ticker}</span>
                    <span className="text-xs opacity-70">{note}</span>
                  </div>
                  <div className="text-right">
                    <span className="inline-block text-xs px-2 py-1 rounded-full bg-green-600/10 text-green-700 dark:text-green-300 border border-green-600/20">
                      BUY • {(score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <BuyNowRow rec={r} />
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}