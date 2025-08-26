import React, { useMemo, useState } from "react";
import { API_BASE } from "../config";
import { postJSON } from "../lib/api";

type Props = {
  symbol: string;
  onClose: () => void;
  price?: number | null;
  thesisRich?: {
    entry_zone?: [number, number];
    stop_loss?: number;
    tp1?: number;
    tp2?: number;
    swing?: string;
    trade_note?: string;
  } | null;
};

export default function TradeModal({ symbol, onClose, price, thesisRich }: Props) {
  const [mode, setMode] = useState<"notional"|"shares">("notional");
  const [amount, setAmount] = useState<number>(100);
  const [shares, setShares] = useState<number>(1);
  const [useBracket, setUseBracket] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState(false);
  const [resp, setResp] = useState<any>(null);
  const [error, setError] = useState<string>("");

  const defaults = useMemo(() => {
    return {
      stop: thesisRich?.stop_loss ?? undefined,
      tp: thesisRich?.tp1 ?? undefined,
    };
  }, [thesisRich]);

  async function submit() {
    setSubmitting(true);
    setError("");
    setResp(null);
    try {
      const body: any = {
        symbol: symbol.toUpperCase(),
        action: "BUY",
        mode: "live",
        order_type: "market",
        time_in_force: "day",
      };
      if (mode === "notional") body.notional_usd = amount;
      else body.qty = shares;
      if (useBracket && (defaults.stop || defaults.tp)) {
        body.bracket = true;
        if (defaults.tp) body.take_profit_price = defaults.tp;
        if (defaults.stop) body.stop_loss_price = defaults.stop;
      }
      const r = await postJSON<any>(`${API_BASE}/trades/execute`, body);
      setResp(r);
    } catch (e:any) {
      setError(e?.message || String(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={overlay}>
      <div style={card}>
        <div style={rowBetween}>
          <h3 style={{margin:0}}>Buy {symbol.toUpperCase()}</h3>
          <button onClick={onClose} style={xbtn}>×</button>
        </div>
        <div style={{fontSize:13, opacity:.7, marginBottom:8}}>
          {thesisRich?.swing || "No thesis available yet."}
        </div>

        <div style={{display:"flex", gap:12, marginTop:4, marginBottom:8}}>
          <button onClick={()=>setMode("notional")} style={modeBtn(mode==="notional")}>Notional</button>
          <button onClick={()=>setMode("shares")} style={modeBtn(mode==="shares")}>Shares</button>
        </div>

        {mode==="notional" ? (
          <label style={label}>
            Amount (USD)
            <input type="number" min={1} value={amount} onChange={e=>setAmount(Number(e.target.value))} style={input} />
          </label>
        ) : (
          <label style={label}>
            Shares
            <input type="number" min={1} value={shares} onChange={e=>setShares(Number(e.target.value))} style={input} />
          </label>
        )}

        <label style={{...label, flexDirection:"row", alignItems:"center", gap:8}}>
          <input type="checkbox" checked={useBracket} onChange={e=>setUseBracket(e.target.checked)} />
          Use bracket with suggested stop/TP
          <span style={{fontSize:12, opacity:.7}}>
            {defaults.stop ? `Stop ${defaults.stop}` : ""}{defaults.stop && defaults.tp ? " • " : ""}{defaults.tp ? `TP1 ${defaults.tp}` : ""}
          </span>
        </label>

        <button disabled={submitting} onClick={submit} style={buybtn}>
          {submitting ? "Submitting..." : "Buy"}
        </button>

        {error ? <div style={{color:"#b00", marginTop:8, whiteSpace:"pre-wrap"}}>{error}</div> : null}
        {resp ? <pre style={pre}>{JSON.stringify(resp, null, 2)}</pre> : null}
      </div>
    </div>
  );
}

const overlay: React.CSSProperties = { position:"fixed", inset:0, background:"rgba(0,0,0,.45)", display:"flex", alignItems:"center", justifyContent:"center", zIndex:1000 };
const card: React.CSSProperties = { width:560, maxWidth:"95vw", background:"#111", color:"#eee", borderRadius:12, padding:16, boxShadow:"0 10px 30px rgba(0,0,0,.5)", fontFamily:"ui-sans-serif, system-ui" };
const rowBetween: React.CSSProperties = { display:"flex", justifyContent:"space-between", alignItems:"center" };
const xbtn: React.CSSProperties = { background:"transparent", border:"none", color:"#aaa", fontSize:24, cursor:"pointer" };
const label: React.CSSProperties = { display:"flex", flexDirection:"column", gap:6, margin:"8px 0" };
const input: React.CSSProperties = { padding:"8px 10px", borderRadius:8, border:"1px solid #333", background:"#0d0d0d", color:"#eee", outline:"none" };
const buybtn: React.CSSProperties = { marginTop:8, padding:"10px 14px", borderRadius:10, background:"#16a34a", color:"#fff", border:"none", cursor:"pointer", fontWeight:600 };
const pre: React.CSSProperties = { marginTop:10, background:"#0a0a0a", padding:10, borderRadius:8, maxHeight:280, overflow:"auto", border:"1px solid #222" };
const modeBtn = (active:boolean) => ({ padding:"6px 10px", borderRadius:999, border:"1px solid "+(active?"#999":"#333"), background: active? "#1a1a1a" : "#0e0e0e", color:"#eee", cursor:"pointer" });