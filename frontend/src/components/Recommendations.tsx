import React, { useEffect, useState, useCallback } from "react";
import RecommendationCard from "./RecommendationCard";
import { API_BASE } from "../config";

export default function Recommendations() {
  const [items, setItems] = useState<any[]>([]);
  const fetchData = useCallback(async ()=>{
    const r = await fetch(`${API_BASE}/discovery/contenders`);
    const j = await r.json();
    setItems(Array.isArray(j)? j : []);
  }, []);
  useEffect(()=>{ fetchData(); const t=setInterval(fetchData, 15000); return ()=>clearInterval(t);},[fetchData]);

  const handleBuy = async (sym:string)=>{
    await fetch(`${API_BASE}/trades/execute`, {method:"POST", headers:{ "content-type":"application/json"},
      body: JSON.stringify({ symbol: sym, action: "BUY", mode: "live", order_type:"market", time_in_force:"day", notional_usd: 100 })
    });
  };

  if (!items.length) return <div className="opacity-70 italic">No recommendations available</div>;

  return (
    <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
      {items.map((it)=> <RecommendationCard key={it.symbol} item={it} onBuy={handleBuy} />)}
    </div>
  );
}