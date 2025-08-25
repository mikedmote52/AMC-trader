import { useEffect, useMemo, useRef, useState } from "react";
type Rec = { symbol?: string; ticker?: string; action?: string; decision?: string; recommendation?: string; score?: number; confidence?: number; signal?: number; risk?: number; risk_score?: number; reason?: string; notes?: string; rationale?: string; };
const API_BASE = (typeof window !== "undefined" && (window as any).API_BASE) || import.meta.env.VITE_API_BASE || "";
export default function BuyNow() {
  const [recs, setRecs] = useState<Rec[]>([]), [error, setError] = useState<string|null>(null);
  const timer = useRef<number|null>(null);
  async function load(){ try{ const r=await fetch(`${API_BASE}/recommendations`); if(!r.ok) throw new Error(`HTTP ${r.status}`); const data=await r.json(); setRecs(Array.isArray(data)?data:[]); setError(null);} catch(e:any){ setError(e?.message||"Failed to load");}}
  useEffect(()=>{ load(); timer.current=window.setInterval(load,15000); return()=>{ if(timer.current) window.clearInterval(timer.current);};},[]);
  const buys = useMemo(()=>{ const minScore=0.6, maxRisk=0.5; return recs.filter(r=>{ const action=(r.action||r.decision||r.recommendation||"").toString().toUpperCase(); const score=Number(r.score??r.confidence??r.signal??0); const risk=Number(r.risk??r.risk_score??0); return action.includes("BUY") && score>=minScore && (isNaN(risk) || risk<=maxRisk);}).sort((a,b)=>(Number(b.score??b.confidence??b.signal??0))-(Number(a.score??a.confidence??a.signal??0))).slice(0,5); },[recs]);
  return (
    <div className="rounded-2xl shadow p-4 bg-white/80 dark:bg-zinc-900/60 border border-black/10">
      <div className="text-xl font-semibold mb-2">Buy Now</div>
      {error && <div className="text-red-600 text-sm mb-2">Error: {error}</div>}
      {buys.length===0 ? <div className="text-sm opacity-70">No qualifying buys right now. This updates every ~15s.</div> : (
        <ul className="divide-y divide-black/5">
          {buys.map((r,i)=>{ const ticker=r.symbol||r.ticker||"—"; const score=Number(r.score??r.confidence??r.signal??0); const note=r.reason||r.notes||r.rationale||""; return (
            <li key={i} className="py-2 flex items-center justify-between">
              <div className="flex flex-col"><span className="font-medium">{ticker}</span><span className="text-xs opacity-70">{note}</span></div>
              <div className="text-right"><span className="inline-block text-xs px-2 py-1 rounded-full bg-green-600/10 text-green-700 dark:text-green-300 border border-green-600/20">BUY • {(score*100).toFixed(0)}%</span></div>
            </li>
          );})}
        </ul>
      )}
    </div>
  );
}