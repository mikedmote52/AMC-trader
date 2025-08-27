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
        console.log("Raw discovery contenders:", data);
        
        const list: Contender[] = Array.isArray(data) ? data : [];
        console.log("Candidates before filtering:", list);
        
        // Check for any filtering/dropping logic that might be removing items
        const filteredList = list.filter(item => item && item.symbol); // Basic validation
        console.log("Filtered candidates after ETF/fund drop:", filteredList);
        
        filteredList.sort((a,b) => b.score - a.score);
        console.log("Final sorted candidates:", filteredList);
        
        if (alive) setItems(filteredList);
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

  console.log("Rendering", items.length, "recommendations");
  
  return (
    <div style={{display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(320px, 1fr))", gap:12}}>
      {items.map((it) => (
        <RecommendationCard key={it.symbol} item={it} />
      ))}
    </div>
  );
}