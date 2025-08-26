import React, { useEffect, useState } from "react";
import { API_BASE } from "../config";
import { getJSON } from "../lib/api";
import TradeModal from "./TradeModal";

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

export default function RecommendationTile({ item }: { item: Candidate }) {
  const score = normScore(item.score ?? item.confidence ?? 0);
  const [hover, setHover] = useState(false);
  const [open, setOpen] = useState(false);
  const [audit, setAudit] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  function openModal() {
    setOpen(true);
    if (!audit) {
      setLoading(true);
      getJSON<any>(`${API_BASE}/discovery/audit/${item.symbol}`)
        .then(setAudit)
        .catch(err => console.error("audit error", err))
        .finally(()=>setLoading(false));
    }
  }

  const price = item.price ?? (audit?.price ?? null);
  const thesisRich = item.thesis_rich ?? audit?.thesis_rich ?? null;

  return (
    <div
      style={tile(score)}
      onMouseEnter={()=>setHover(true)}
      onMouseLeave={()=>setHover(false)}
    >
      <div style={{display:"flex", justifyContent:"space-between", alignItems:"center"}}>
        <div style={{fontWeight:700, letterSpacing:.2}}>{item.symbol}</div>
        <div style={badge(score)}>{score}</div>
      </div>

      <div style={{fontSize:13, opacity:.75, marginTop:6}}>
        {price ? `${price.toFixed(2)}` : "price n/a"} · ATR {(item.atr_pct ? (item.atr_pct*100).toFixed(1) : "n/a")}%
      </div>

      <div style={{fontSize:12, color:"#bbb", marginTop:8, minHeight:32}}>
        {item.thesis || "No thesis yet."}
      </div>

      <div style={{display:"flex", gap:8, marginTop:12}}>
        <button onClick={openModal} style={btn}>Details</button>
        <button onClick={()=>setOpen(true)} style={buyBtn}>Buy</button>
      </div>

      {hover && (
        <div style={hoverBox}>
          <div style={{fontSize:12, opacity:.9}}>
            Dollar vol {fmtNum(item.dollar_vol)} · RelVol {item.rel_vol_30m ? item.rel_vol_30m.toFixed(1) : "n/a"}×
          </div>
        </div>
      )}

      {open && (
        <TradeModal
          symbol={item.symbol}
          onClose={()=>setOpen(false)}
          price={price}
          thesisRich={thesisRich}
        />
      )}
    </div>
  );
}

const normScore = (n:any) => {
  const x = typeof n === "number" ? n : 0;
  return x > 1 ? Math.round(x) : Math.round(x * 100);
};
const fmtNum = (n:any) => n == null ? "n/a" : Intl.NumberFormat("en-US", { notation:"compact" }).format(n);

const tile = (score:number): React.CSSProperties => ({
  border:"1px solid #222",
  borderRadius:14,
  padding:14,
  background:"#0d0f12",
  color:"#e7e7e7",
  boxShadow:"0 6px 18px rgba(0,0,0,.35)",
  width:"min(320px, 100%)",
  position:"relative"
});

const badge = (score:number): React.CSSProperties => ({
  fontSize:12,
  padding:"2px 8px",
  borderRadius:999,
  background: score>=75 ? "#144d2a" : score>=70 ? "#5b4b17" : "#333",
  color: score>=75 ? "#50fa7b" : score>=70 ? "#ffd166" : "#aaa",
  border:"1px solid #333"
});

const hoverBox: React.CSSProperties = {
  position:"absolute",
  right:10,
  bottom:10,
  background:"#0a0c0f",
  border:"1px solid #222",
  padding:"8px 10px",
  borderRadius:10
};

const btn: React.CSSProperties = { padding:"8px 10px", borderRadius:10, border:"1px solid #333", background:"#0f1115", color:"#e7e7e7", cursor:"pointer" };
const buyBtn: React.CSSProperties = { padding:"8px 10px", borderRadius:10, border:"1px solid #1b4", background:"#134e25", color:"#e7e7e7", cursor:"pointer", fontWeight:700 };