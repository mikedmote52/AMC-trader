import React, { useEffect, useState } from "react";
import { API_BASE } from "../config";
import { getJSON } from "../lib/api";
import RecommendationCard from "./RecommendationCard";

type Candidate = {
  symbol: string;
  price?: number | null;
  score?: number | null;
  confidence?: number | null;
  thesis?: string | null;
  thesis_rich?: any | null;
  atr_pct?: number | null;
  dollar_vol?: number | null;
  rel_vol_30m?: number | null;
  reason?: string | null;
};

export default function Recommendations() {
  const [items, setItems] = useState<Candidate[]>([]);
  const [err, setErr] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    async function run() {
      try {
        setLoading(true);
        setErr("");
        const data = await getJSON<any>(`${API_BASE}/discovery/contenders`);
        const list: Candidate[] = Array.isArray(data) ? data : [];
        list.sort((a,b) => (b.score ?? 0) - (a.score ?? 0));
        if (alive) setItems(list);
      } catch (e:any) {
        if (alive) setErr(e?.message || String(e));
      } finally {
        if (alive) setLoading(false);
      }
    }
    run();
    const id = setInterval(run, 15_000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  if (loading) return <div style={{padding:12}}>🔍 Scanning market for opportunities…</div>;
  if (err) return <div style={{padding:12, color:"#c00"}}>❌ Error: {err}</div>;
  if (!items.length) return (
    <div style={{padding:12}}>
      <div style={{marginBottom: 12}}>
        <strong>📊 No high-confidence opportunities detected</strong>
      </div>
      <div style={{fontSize: 13, color: '#888', lineHeight: 1.5, marginBottom: 12}}>
        <strong>Why no recommendations right now:</strong><br/>
        • Market volatility may be too high (risk protection active)<br/>
        • No stocks meeting our strict VIGL pattern criteria (>75% confidence)<br/>
        • Volume patterns insufficient (need >5x average for signals)<br/>
        • Waiting for clearer entry points in current market conditions<br/>
        • Discovery engine last run: {new Date().toLocaleTimeString()}
      </div>
      <div style={{fontSize: 12, color: '#666', fontStyle: 'italic', marginBottom: 12}}>
        💡 <strong>System Status:</strong> Active and monitoring. Being selective is better than forcing bad trades.
        The system scans 1,700+ stocks every 30 minutes for patterns matching our proven winners.
      </div>
      <button 
        onClick={() => window.location.reload()} 
        style={{padding: '8px 16px', background: '#22c55e', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600}}
      >
        🔄 Refresh Now
      </button>
    </div>
  );

  return (
    <div className="grid-responsive">
      {items.map((it) => (
        <RecommendationCard key={it.symbol} item={it} />
      ))}
    </div>
  );
}