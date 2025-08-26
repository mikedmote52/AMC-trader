import React, { useEffect, useState } from "react";
import { API_BASE } from "../config";
import { getJSON } from "../lib/api";
import RecommendationCard from "./RecommendationCard";

interface Contender {
  symbol: string; 
  price?: number; 
  thesis?: string;
  score: number; 
  confidence?: number;
  factors?: Record<string, any>;
}

export default function Recommendations() {
  const [items, setItems] = useState<Contender[]>([]);
  const [err, setErr] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    async function run() {
      try {
        setLoading(true);
        setErr("");
        const data = await getJSON<any>(`${API_BASE}/discovery/contenders`);
        const list: Contender[] = Array.isArray(data) ? data : [];
        list.sort((a,b) => b.score - a.score);
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

  if (loading) return <div style={{padding:12}}>Loading recommendations…</div>;
  if (err) return <div style={{padding:12, color:"#c00"}}>Error: {err}</div>;
  if (!items.length) return <div style={{padding:12}}>No recommendations yet. The discovery job may still be running.</div>;

  return (
    <div style={{display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(320px, 1fr))", gap:12}}>
      {items.map((it) => (
        <RecommendationCard key={it.symbol} item={it} />
      ))}
    </div>
  );
}