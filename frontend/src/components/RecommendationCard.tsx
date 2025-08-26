import React, { useState } from "react";
import { API_BASE } from "../config";
import { getJSON } from "../lib/api";
import TradeModal from "./TradeModal";

type Candidate = {
  symbol: string;
  price?: number | null;
  score?: number | null;
  thesis?: string | null;
  [key: string]: any;
};

type AuditData = {
  volume?: { rel_vol_30m?: number };
  short?: { si?: number; borrow?: number; util?: number };
  catalyst?: { news_score?: number; tag?: string };
  sentiment?: { score?: number; trending?: string };
  options?: { pcr?: number; iv_pctl?: number; call_oi_up?: number };
  technicals?: { ema9_above_ema20?: boolean; rsi?: number; vwap_reclaim?: boolean };
  atr_pct?: number;
  dollar_vol?: number;
};

export default function RecommendationCard({ item }: { item: Candidate }) {
  const [showAuditModal, setShowAuditModal] = useState(false);
  const [showTradeModal, setShowTradeModal] = useState(false);
  const [auditData, setAuditData] = useState<AuditData | null>(null);
  const [loading, setLoading] = useState(false);

  // Use item.score directly, not compression percentile
  const score = Math.round(item.score ?? 0);
  
  const getScoreClass = (score: number) => {
    if (score >= 75) return "bg-green-600 text-white";
    if (score >= 70) return "bg-yellow-600 text-white"; 
    return "bg-gray-600 text-white";
  };

  const handleDetailsClick = async () => {
    setShowAuditModal(true);
    if (!auditData) {
      setLoading(true);
      try {
        const data = await getJSON<AuditData>(`${API_BASE}/discovery/audit/${item.symbol}`);
        setAuditData(data);
      } catch (err) {
        console.error("Audit error:", err);
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <>
      <div style={cardStyle}>
        <div style={{display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:8}}>
          <div>
            <div style={{fontWeight:700, fontSize:18, marginBottom:4}}>{item.symbol}</div>
            <div style={{fontSize:14, opacity:0.8}}>
              ${item.price?.toFixed(2) || "N/A"}
            </div>
          </div>
          <div className={`px-2 py-1 text-xs rounded-full font-bold ${getScoreClass(score)}`}>
            {score}
          </div>
        </div>
        
        <div style={{fontSize:12, color:"#bbb", marginBottom:12, minHeight:20}}>
          {item.thesis || "No thesis available"}
        </div>
        
        <div style={{display:"flex", gap:8}}>
          <button onClick={handleDetailsClick} style={detailsBtn}>Details</button>
          <button onClick={() => setShowTradeModal(true)} style={buyBtn}>Buy</button>
        </div>
      </div>

      {showAuditModal && (
        <div style={modalOverlay} onClick={() => setShowAuditModal(false)}>
          <div style={modalContent} onClick={e => e.stopPropagation()}>
            <div style={{display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:16}}>
              <h3 style={{margin:0, fontSize:18}}>Audit: {item.symbol}</h3>
              <button onClick={() => setShowAuditModal(false)} style={{background:"none", border:"none", color:"#aaa", fontSize:20, cursor:"pointer"}}>×</button>
            </div>
            
            {loading ? (
              <div>Loading audit data...</div>
            ) : auditData ? (
              <table style={tableStyle}>
                <tbody>
                  <tr>
                    <td style={cellStyle}>Volume</td>
                    <td style={cellStyle}>{auditData.volume?.rel_vol_30m?.toFixed(1) || "N/A"}x rel_vol_30m</td>
                  </tr>
                  <tr>
                    <td style={cellStyle}>Short</td>
                    <td style={cellStyle}>
                      SI: {auditData.short?.si?.toFixed(1) || "N/A"}%
                      {auditData.short?.borrow && ` • Borrow: ${auditData.short.borrow.toFixed(1)}%`}
                      {auditData.short?.util && ` • Util: ${auditData.short.util.toFixed(1)}%`}
                    </td>
                  </tr>
                  <tr>
                    <td style={cellStyle}>Catalyst</td>
                    <td style={cellStyle}>
                      {auditData.catalyst?.news_score ? `News: ${auditData.catalyst.news_score.toFixed(1)}` : "N/A"}
                      {auditData.catalyst?.tag && ` • ${auditData.catalyst.tag}`}
                    </td>
                  </tr>
                  <tr>
                    <td style={cellStyle}>Sentiment</td>
                    <td style={cellStyle}>
                      Score: {auditData.sentiment?.score?.toFixed(1) || "N/A"}
                      {auditData.sentiment?.trending && ` • ${auditData.sentiment.trending}`}
                    </td>
                  </tr>
                  <tr>
                    <td style={cellStyle}>Options</td>
                    <td style={cellStyle}>
                      PCR: {auditData.options?.pcr?.toFixed(2) || "N/A"}
                      {auditData.options?.iv_pctl && ` • IV: ${auditData.options.iv_pctl.toFixed(0)}%ile`}
                      {auditData.options?.call_oi_up && ` • Call OI: ${auditData.options.call_oi_up.toFixed(0)}`}
                    </td>
                  </tr>
                  <tr>
                    <td style={cellStyle}>Technicals</td>
                    <td style={cellStyle}>
                      EMA9&gt;EMA20: {auditData.technicals?.ema9_above_ema20 ? "✓" : "✗"}
                      {auditData.technicals?.rsi && ` • RSI: ${auditData.technicals.rsi.toFixed(0)}`}
                      {auditData.technicals?.vwap_reclaim !== undefined && ` • VWAP: ${auditData.technicals.vwap_reclaim ? "✓" : "✗"}`}
                    </td>
                  </tr>
                  <tr>
                    <td style={cellStyle}>ATR & Vol</td>
                    <td style={cellStyle}>
                      ATR: {auditData.atr_pct ? `${(auditData.atr_pct * 100).toFixed(1)}%` : "N/A"}
                      {auditData.dollar_vol && ` • $Vol: ${(auditData.dollar_vol / 1e6).toFixed(1)}M`}
                    </td>
                  </tr>
                </tbody>
              </table>
            ) : (
              <div>No audit data available</div>
            )}
          </div>
        </div>
      )}

      {showTradeModal && (
        <TradeModal
          presetSymbol={item.symbol}
          presetAction="BUY"
          presetPrice={item.price}
          onClose={() => setShowTradeModal(false)}
        />
      )}
    </>
  );
}

const cardStyle: React.CSSProperties = {
  border:"1px solid #333",
  borderRadius:12,
  padding:16,
  background:"#111",
  color:"#eee",
  width:"100%",
  minWidth:280
};

const detailsBtn: React.CSSProperties = {
  padding:"8px 12px",
  borderRadius:8,
  border:"1px solid #444",
  background:"#222",
  color:"#eee",
  cursor:"pointer",
  fontSize:12
};

const buyBtn: React.CSSProperties = {
  padding:"8px 12px",
  borderRadius:8,
  border:"1px solid #16a34a",
  background:"#16a34a",
  color:"white",
  cursor:"pointer",
  fontSize:12,
  fontWeight:600
};

const modalOverlay: React.CSSProperties = {
  position:"fixed",
  inset:0,
  background:"rgba(0,0,0,0.5)",
  display:"flex",
  alignItems:"center",
  justifyContent:"center",
  zIndex:1000
};

const modalContent: React.CSSProperties = {
  background:"#111",
  color:"#eee",
  padding:20,
  borderRadius:12,
  width:"90%",
  maxWidth:600,
  maxHeight:"80vh",
  overflow:"auto"
};

const tableStyle: React.CSSProperties = {
  width:"100%",
  borderSpacing:0
};

const cellStyle: React.CSSProperties = {
  padding:"8px 12px",
  borderBottom:"1px solid #333",
  fontSize:13
};