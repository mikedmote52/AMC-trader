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

  // Determine if this is a top pick (score >= 75)
  const isTopPick = score >= 75;
  const cardStyleEnhanced = {
    ...cardStyle,
    ...(isTopPick && {
      background: "linear-gradient(135deg, rgba(34, 197, 94, 0.1), #111)",
      borderColor: "rgba(34, 197, 94, 0.3)",
      boxShadow: "0 0 20px rgba(34, 197, 94, 0.15)"
    })
  };

  return (
    <>
      <div style={cardStyleEnhanced} className="recommendation-card">
        {/* Header with priority indicator */}
        {isTopPick && (
          <div style={priorityBannerStyle}>
            ⚡ HIGH PRIORITY
          </div>
        )}
        
        <div style={{display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:12}}>
          <div style={{flex: 1}}>
            <div style={{display:"flex", alignItems:"center", gap:8, marginBottom:4}}>
              <div style={{fontWeight:700, fontSize:20, letterSpacing:"-0.02em"}}>
                {item.symbol}
              </div>
              {item.confidence && (
                <div style={{
                  fontSize: 11,
                  color: "#999",
                  background: "rgba(255,255,255,0.05)",
                  padding: "2px 6px",
                  borderRadius: 4,
                }}>
                  {Math.round(item.confidence * 100)}% confidence
                </div>
              )}
            </div>
            <div style={{fontSize:24, fontWeight:700, color:score >= 75 ? "#22c55e" : "#fff"}}>
              ${item.price?.toFixed(2) || "N/A"}
            </div>
            
            {/* Quick metrics row */}
            <div style={{display:"flex", gap:8, marginTop:4, fontSize:11, color:"#666"}}>
              {item.rel_vol_30m && (
                <span>Vol: {item.rel_vol_30m.toFixed(1)}x</span>
              )}
              {item.atr_pct && (
                <span>ATR: {(item.atr_pct * 100).toFixed(1)}%</span>
              )}
              {item.dollar_vol && (
                <span>${(item.dollar_vol / 1e6).toFixed(1)}M</span>
              )}
            </div>
          </div>
          
          <div style={{
            background: score >= 75 ? "#22c55e" : score >= 70 ? "#eab308" : "#6b7280",
            color: score >= 75 ? "#000" : "#fff",
            padding: "8px 12px",
            borderRadius: 12,
            fontSize: 16,
            fontWeight: 700,
            minWidth: 48,
            textAlign: "center",
            boxShadow: score >= 75 ? "0 0 16px rgba(34, 197, 94, 0.3)" : "none"
          }}>
            {score}
          </div>
        </div>
        
        {/* Thesis with better typography */}
        <div style={{
          fontSize:13, 
          color: isTopPick ? "#ccc" : "#999", 
          marginBottom:16, 
          minHeight:36, 
          lineHeight:1.4,
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
          overflow: "hidden"
        }}>
          {item.thesis || "Analyzing opportunity..."}
        </div>
        
        {/* Enhanced action buttons */}
        <div style={{display:"flex", gap:8}}>
          <button onClick={handleDetailsClick} style={{
            ...detailsBtn,
            flex: 1
          }}>
            📊 Details
          </button>
          <button onClick={() => setShowTradeModal(true)} style={{
            ...buyBtn,
            flex: 2,
            ...(isTopPick && {
              background: "linear-gradient(135deg, #22c55e, #16a34a)",
              borderColor: "#22c55e",
              fontWeight: 700,
              boxShadow: "0 4px 12px rgba(34, 197, 94, 0.2)"
            })
          }}>
            {isTopPick ? "🚀 BUY NOW" : "📈 Buy"}
          </button>
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
  background:"linear-gradient(135deg, #1a1a1a 0%, #111 100%)",
  color:"#eee",
  width:"100%",
  minWidth:280,
  transition:"all 0.2s ease",
  position:"relative"
};

const detailsBtn: React.CSSProperties = {
  padding:"10px 16px",
  borderRadius:8,
  border:"1px solid #444",
  background:"rgba(255,255,255,0.05)",
  color:"#aaa",
  cursor:"pointer",
  fontSize:13,
  fontWeight:600,
  flex:1,
  transition:"all 0.2s ease"
};

const buyBtn: React.CSSProperties = {
  padding:"10px 16px",
  borderRadius:8,
  border:"1px solid #16a34a",
  background:"#16a34a",
  color:"white",
  cursor:"pointer",
  transition:"all 0.2s ease",
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

const priorityBannerStyle: React.CSSProperties = {
  position: "absolute",
  top: -1,
  left: -1,
  right: -1,
  background: "linear-gradient(90deg, #22c55e, #16a34a)",
  color: "#000",
  fontSize: 10,
  fontWeight: 800,
  padding: "4px 8px",
  textAlign: "center",
  letterSpacing: "0.05em",
  borderTopLeftRadius: 12,
  borderTopRightRadius: 12,
};