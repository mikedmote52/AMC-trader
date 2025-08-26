import React, { useEffect, useState } from "react";
import { API_BASE } from "../config";
import { getJSON } from "../lib/api";
import RecommendationTile from "./RecommendationTile";

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
        list.sort((a,b) => (b.score ?? b.confidence ?? 0) - (a.score ?? a.confidence ?? 0));
        if (alive) setItems(list);
      } catch (e:any) {
        if (alive) setErr(e?.message || String(e));
      } finally {
        if (alive) setLoading(false);
      }
    }
    run();
    const id = setInterval(run, 30_000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  if (loading) return <div style={{padding:12}}>Loading recommendations…</div>;
  if (err) return <div style={{padding:12, color:"#c00"}}>Error: {err}</div>;
  if (!items.length) return <div style={{padding:12}}>No recommendations yet. The discovery job may still be running.</div>;

  return (
    <div style={{display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(320px, 1fr))", gap:12}}>
      {items.map((it) => (
        <RecommendationTile key={it.symbol} item={it} />
      ))}
    </div>
  );
}