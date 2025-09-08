import React, { useEffect, useState } from "react";
import { API_BASE } from "../config";
import { getJSON } from "../lib/api";
import TradeModal from "./TradeModal";
import PortfolioSummary from "./PortfolioSummary";

type Holding = {
  symbol: string;
  qty: number;
  avg_entry_price: number;
  last_price: number;
  market_value: number;
  unrealized_pl: number;
  unrealized_pl_pct: number;
  thesis?: string;
  confidence?: number;
  suggestion?: string;
  [key: string]: any;
};

type Contender = {
  symbol: string;
  score?: number;
  thesis?: string;
};

export default function Holdings() {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [contenders, setContenders] = useState<Contender[]>([]);
  const [err, setErr] = useState<string>("");
  const [showTradeModal, setShowTradeModal] = useState(false);
  const [tradePreset, setTradePreset] = useState<{symbol: string; action: "BUY" | "SELL"; qty?: number} | null>(null);
  
  // New filtering and sorting state - default to highest P&L amount first
  const [sortBy, setSortBy] = useState<"pl_pct" | "pl_amount" | "confidence" | "value" | "symbol">("pl_amount");
  const [filterBy, setFilterBy] = useState<"all" | "winners" | "losers" | "action_needed">("all");
  const [groupBy, setGroupBy] = useState<"none" | "sector" | "recommendation">("none");

  async function fetchData() {
    try {
      setErr("");
      
      // Fetch holdings first (critical for portfolio display)
      const holdingsData = await getJSON<any>(`${API_BASE}/portfolio/holdings`);
      const positions = holdingsData?.data?.positions || holdingsData?.positions || [];
      setHoldings(Array.isArray(positions) ? positions : []);
      
      // Fetch contenders separately with timeout handling (non-critical)
      try {
        const contendersData = await getJSON<any>(`${API_BASE}/discovery/contenders`);
        setContenders(Array.isArray(contendersData) ? contendersData : []);
      } catch (contenderError) {
        console.warn('Failed to load contenders (non-critical):', contenderError);
        setContenders([]);
      }
    } catch (e: any) {
      setErr(e?.message || String(e));
    }
  }

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, 45_000); // Refresh every 45 seconds for real-time P&L updates
    return () => clearInterval(id);
  }, []);

  const handleTrade = (symbol: string, action: "BUY" | "SELL", qty?: number) => {
    setTradePreset({ symbol, action, qty });
    setShowTradeModal(true);
  };

  // Filter and sort holdings
  const getFilteredAndSortedHoldings = () => {
    let filtered = [...holdings];
    
    // Apply filters
    switch (filterBy) {
      case "winners":
        filtered = filtered.filter(h => h.unrealized_pl_pct >= 5);
        break;
      case "losers":
        filtered = filtered.filter(h => h.unrealized_pl_pct <= -2);
        break;
      case "action_needed":
        filtered = filtered.filter(h => {
          const rec = getRecommendation(h);
          return rec.action !== "HOLD";
        });
        break;
    }
    
    // Apply sorting
    filtered.sort((a, b) => {
      switch (sortBy) {
        case "pl_pct":
          return b.unrealized_pl_pct - a.unrealized_pl_pct;
        case "pl_amount":
          return b.unrealized_pl - a.unrealized_pl;
        case "confidence":
          return (b.confidence || 0) - (a.confidence || 0);
        case "value":
          return b.market_value - a.market_value;
        case "symbol":
          return a.symbol.localeCompare(b.symbol);
        default:
          return 0;
      }
    });
    
    // Group if needed
    if (groupBy === "none") {
      return { ungrouped: filtered };
    }
    
    return filtered.reduce((groups: {[key: string]: Holding[]}, holding) => {
      let key: string;
      if (groupBy === "sector") {
        key = holding.sector || "Unknown";
      } else if (groupBy === "recommendation") {
        key = getRecommendation(holding).action;
      } else {
        key = "All";
      }
      
      if (!groups[key]) groups[key] = [];
      groups[key].push(holding);
      return groups;
    }, {});
  };

  const getRecommendation = (holding: Holding) => {
    const plPct = holding.unrealized_pl_pct;
    const suggestion = holding.suggestion?.toLowerCase() || "";
    const confidence = holding.confidence || 0;
    const marketValue = holding.market_value;
    
    // Use API-provided suggestion when available and reliable
    if (confidence > 0.6 && suggestion) {
      const apiSuggestion = suggestion.toUpperCase();
      if (apiSuggestion === "INCREASE" || apiSuggestion === "BUY_MORE") {
        return { 
          action: "BUY MORE", 
          reason: `🎯 AI recommends adding (${(confidence * 100).toFixed(0)}% confidence)`, 
          color: "#16a34a",
          buttonText: "🎯 Add Position",
          buttonColor: "#16a34a"
        };
      } else if (apiSuggestion === "REDUCE" || apiSuggestion === "TRIM") {
        return { 
          action: "TRIM", 
          reason: `⚠️ AI recommends reducing (${(confidence * 100).toFixed(0)}% confidence)`, 
          color: "#f59e0b",
          buttonText: "⚠️ Reduce Position",
          buttonColor: "#f59e0b"
        };
      }
    }
    
    // Positions with VIGL thesis and confidence
    if (confidence > 0.55 && holding.thesis) {
      if (plPct > 2) {
        return { 
          action: "BUY MORE", 
          reason: `🎯 VIGL pattern developing (${(confidence * 100).toFixed(0)}% confidence)`, 
          color: "#16a34a",
          buttonText: "🎯 Add on Pattern",
          buttonColor: "#16a34a"
        };
      } else {
        return { 
          action: "HOLD", 
          reason: `⏳ VIGL thesis developing (${(confidence * 100).toFixed(0)}% confidence)`, 
          color: "#6b7280",
          buttonText: "⏳ Wait for Signal",
          buttonColor: "#6b7280"
        };
      }
    }
    
    // General P&L-based logic with more nuanced recommendations
    if (plPct >= 50) {
      return { 
        action: "TRIM", 
        reason: "💰 Strong gains - consider taking some profits", 
        color: "#f59e0b",
        buttonText: "💰 Take Profits",
        buttonColor: "#f59e0b"
      };
    }
    
    if (plPct >= 15) {
      return { 
        action: "HOLD", 
        reason: "📈 Good performance - let it run", 
        color: "#22c55e",
        buttonText: "📈 Let it Run",
        buttonColor: "#22c55e"
      };
    }
    
    if (plPct >= 5) {
      return { 
        action: "BUY MORE", 
        reason: "🚀 Building momentum - consider adding", 
        color: "#16a34a",
        buttonText: "🚀 Add on Strength",
        buttonColor: "#16a34a"
      };
    }
    
    if (plPct >= -2) {
      return { 
        action: "HOLD", 
        reason: "⚖️ Flat position - thesis intact", 
        color: "#6b7280",
        buttonText: "⚖️ Hold Position",
        buttonColor: "#6b7280"
      };
    }
    
    if (plPct >= -5) {
      return { 
        action: "HOLD", 
        reason: "⚠️ Small loss - monitor closely", 
        color: "#f59e0b",
        buttonText: "⚠️ Monitor Closely",
        buttonColor: "#f59e0b"
      };
    }
    
    if (plPct >= -15) {
      return { 
        action: "TRIM", 
        reason: "🔄 Moderate loss - consider reducing", 
        color: "#ef4444",
        buttonText: "🔄 Reduce Position",
        buttonColor: "#ef4444"
      };
    }
    
    // Heavy losses
    return { 
      action: "LIQUIDATE", 
      reason: "🚨 Heavy loss - exit position", 
      color: "#dc2626",
      buttonText: "🚨 Exit Position",
      buttonColor: "#dc2626"
    };
  };

  if (err) return <div style={{padding:12, color:"#c00"}}>Error loading holdings: {err}</div>;
  if (!holdings.length) return <div style={{padding:12, color:"#888"}}>No holdings found.</div>;

  const groupedHoldings = getFilteredAndSortedHoldings();

  return (
    <>
      <PortfolioSummary holdings={holdings} isLoading={!holdings.length && !err} />
      
      {/* Enhanced Controls with Toggle Buttons */}
      <div style={controlsStyle}>
        <div style={controlGroupStyle}>
          <label style={labelStyle}>Sort by:</label>
          <div style={toggleGroupStyle}>
            <button 
              onClick={() => setSortBy("pl_amount")} 
              style={sortBy === "pl_amount" ? activeToggleStyle : inactiveToggleStyle}
            >
              💰 $ P&L
            </button>
            <button 
              onClick={() => setSortBy("pl_pct")} 
              style={sortBy === "pl_pct" ? activeToggleStyle : inactiveToggleStyle}
            >
              📊 % P&L
            </button>
            <button 
              onClick={() => setSortBy("confidence")} 
              style={sortBy === "confidence" ? activeToggleStyle : inactiveToggleStyle}
            >
              🎯 AI Score
            </button>
            <button 
              onClick={() => setSortBy("value")} 
              style={sortBy === "value" ? activeToggleStyle : inactiveToggleStyle}
            >
              💵 Value
            </button>
            <button 
              onClick={() => setSortBy("symbol")} 
              style={sortBy === "symbol" ? activeToggleStyle : inactiveToggleStyle}
            >
              🔤 A-Z
            </button>
          </div>
        </div>
        
        <div style={controlGroupStyle}>
          <label style={labelStyle}>Filter:</label>
          <select value={filterBy} onChange={(e) => setFilterBy(e.target.value as any)} style={selectStyle}>
            <option value="all">🎯 All Positions ({holdings.length})</option>
            <option value="winners">📈 Winners ({holdings.filter(h => h.unrealized_pl_pct >= 5).length})</option>
            <option value="losers">📉 Losers ({holdings.filter(h => h.unrealized_pl_pct <= -2).length})</option>
            <option value="action_needed">⚡ Action Needed ({holdings.filter(h => getRecommendation(h).action !== "HOLD").length})</option>
          </select>
        </div>
        
        <div style={controlGroupStyle}>
          <label style={labelStyle}>Group by:</label>
          <select value={groupBy} onChange={(e) => setGroupBy(e.target.value as any)} style={selectStyle}>
            <option value="none">📋 No Grouping</option>
            <option value="sector">🏢 Sector</option>
            <option value="recommendation">⚡ Recommendation</option>
          </select>
        </div>
        
        <button onClick={fetchData} style={refreshButtonStyle}>
          🔄 Refresh Data
        </button>
      </div>

      {/* Render grouped holdings */}
      {Object.entries(groupedHoldings).map(([groupName, groupHoldings]) => (
        <div key={groupName}>
          {groupName !== "ungrouped" && (
            <div style={groupHeaderStyle}>
              <h3>{groupName} ({groupHoldings.length})</h3>
            </div>
          )}
          <div className="grid-responsive">
            {groupHoldings.map((holding) => {
              const plColor = holding.unrealized_pl >= 0 ? "#22c55e" : "#ef4444";
              const recommendation = getRecommendation(holding);
          
          return (
            <div key={holding.symbol} style={cardStyle}>
              <div>
                <div style={{display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:8}}>
                  <div style={{fontWeight:700, fontSize:18}}>{holding.symbol}</div>
                  <div style={{
                    background: recommendation.color,
                    color: "white",
                    padding: "4px 12px",
                    borderRadius: 8,
                    fontSize: 12,
                    fontWeight: 700,
                    textTransform: "uppercase"
                  }}>
                    {recommendation.action}
                  </div>
                </div>
                
                {/* Enhanced Action Recommendation */}
                <div style={{
                  background: `linear-gradient(135deg, ${recommendation.color}15, ${recommendation.color}05)`,
                  border: `1px solid ${recommendation.color}40`,
                  borderRadius: 10,
                  padding: 12,
                  marginBottom: 12
                }}>
                  <div style={{
                    fontSize: 14, 
                    fontWeight: 700, 
                    color: recommendation.color, 
                    marginBottom: 6,
                    textTransform: "uppercase",
                    letterSpacing: "0.5px"
                  }}>
                    {recommendation.action} • {holding.confidence ? (holding.confidence * 100).toFixed(0) : "0"}% Confidence
                  </div>
                  <div style={{fontSize: 13, color: "#ddd", lineHeight: 1.4}}>
                    {recommendation.reason}
                  </div>
                </div>
                
                {/* Position Details */}
                <div style={{fontSize:13, marginBottom:12, lineHeight:1.4}}>
                  <div>Position: {holding.qty} shares @ ${holding.avg_entry_price.toFixed(2)}</div>
                  <div>Current: ${holding.last_price.toFixed(2)} • Value: ${holding.market_value.toFixed(2)}</div>
                  <div style={{color: plColor, fontSize:15, fontWeight:600}}>
                    P&L: ${holding.unrealized_pl.toFixed(2)} ({holding.unrealized_pl_pct.toFixed(1)}%)
                  </div>
                  {holding.sector && (
                    <div style={{color: "#888", fontSize: 12, marginTop: 4}}>
                      Sector: {holding.sector} • Risk: {holding.risk_level || "Moderate"}
                    </div>
                  )}
                </div>
                
                {/* Enhanced Investment Thesis Display */}
                {holding.thesis && (
                  <div style={{
                    background: "#0f1419",
                    border: "1px solid #2a2a2a",
                    borderRadius: 8,
                    padding: 14,
                    marginBottom: 12,
                    fontSize: 12,
                    lineHeight: 1.5
                  }}>
                    <div style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color: "#888",
                      marginBottom: 8,
                      textTransform: "uppercase",
                      letterSpacing: "0.5px",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center"
                    }}>
                      <span>📊 Investment Analysis</span>
                      <span style={{color: holding.confidence > 0.7 ? "#22c55e" : holding.confidence > 0.4 ? "#f59e0b" : "#ef4444"}}>
                        {holding.thesis_source || "AI"}
                      </span>
                    </div>
                    <div style={{color: "#e5e7eb", marginBottom: 10}}>
                      {holding.thesis}
                    </div>
                    {holding.reasoning && (
                      <div style={{
                        borderTop: "1px solid #374151",
                        paddingTop: 8,
                        fontSize: 11,
                        color: "#9ca3af",
                        fontStyle: "italic"
                      }}>
                        <strong>Decision Logic:</strong> {holding.reasoning}
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              <div style={{display:"flex", gap:8, marginTop:"auto"}}>
                {recommendation.action === "LIQUIDATE" ? (
                  <button 
                    onClick={() => handleTrade(holding.symbol, "SELL", holding.qty)} 
                    style={{
                      ...actionBtn,
                      background: recommendation.buttonColor,
                      border: `1px solid ${recommendation.buttonColor}`,
                      flex: 1
                    }}
                  >
                    {recommendation.buttonText}
                  </button>
                ) : recommendation.action === "TRIM" ? (
                  <>
                    <button 
                      onClick={() => handleTrade(holding.symbol, "SELL", Math.floor(holding.qty * 0.5))} 
                      style={{
                        ...actionBtn,
                        background: recommendation.buttonColor,
                        border: `1px solid ${recommendation.buttonColor}`,
                        flex: 1
                      }}
                    >
                      {recommendation.buttonText}
                    </button>
                    <button 
                      onClick={() => handleTrade(holding.symbol, "SELL", Math.floor(holding.qty * 0.25))} 
                      style={{
                        ...actionBtn,
                        background: "#6b7280",
                        border: "1px solid #6b7280",
                        opacity: 0.7,
                        fontSize: 11
                      }}
                    >
                      Trim 25%
                    </button>
                  </>
                ) : recommendation.action === "BUY MORE" ? (
                  <>
                    <button 
                      onClick={() => handleTrade(holding.symbol, "BUY")} 
                      style={{
                        ...actionBtn,
                        background: recommendation.buttonColor,
                        border: `1px solid ${recommendation.buttonColor}`,
                        flex: 1
                      }}
                    >
                      {recommendation.buttonText}
                    </button>
                    <button 
                      onClick={() => handleTrade(holding.symbol, "SELL", Math.floor(holding.qty * 0.25))} 
                      style={{
                        ...actionBtn,
                        background: "#6b7280",
                        border: "1px solid #6b7280",
                        opacity: 0.5,
                        fontSize: 11
                      }}
                    >
                      Trim
                    </button>
                  </>
                ) : (
                  <>
                    <button 
                      onClick={() => handleTrade(holding.symbol, "BUY")} 
                      style={{
                        ...actionBtn,
                        background: "#374151",
                        border: "1px solid #4b5563",
                        opacity: 0.7,
                        fontSize: 11
                      }}
                    >
                      Add More
                    </button>
                    <button 
                      style={{
                        ...actionBtn,
                        background: recommendation.buttonColor,
                        border: `1px solid ${recommendation.buttonColor}`,
                        flex: 1,
                        cursor: "default"
                      }}
                    >
                      {recommendation.buttonText}
                    </button>
                    <button 
                      onClick={() => handleTrade(holding.symbol, "SELL", Math.floor(holding.qty * 0.25))} 
                      style={{
                        ...actionBtn,
                        background: "#374151",
                        border: "1px solid #4b5563",
                        opacity: 0.7,
                        fontSize: 11
                      }}
                    >
                      Trim
                    </button>
                  </>
                )}
              </div>
            </div>
          );
            })}
          </div>
        </div>
      ))}

      {showTradeModal && tradePreset && (
        <TradeModal
          presetSymbol={tradePreset.symbol}
          presetAction={tradePreset.action}
          presetQty={tradePreset.qty}
          onClose={() => {
            setShowTradeModal(false);
            setTradePreset(null);
          }}
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
  minHeight: "200px",
  display: "flex",
  flexDirection: "column"
};

const buyBtn: React.CSSProperties = {
  padding:"8px 12px",
  borderRadius:8,
  border:"1px solid #16a34a",
  background:"#16a34a",
  color:"white",
  cursor:"pointer",
  fontSize:12,
  fontWeight:600,
  flex:1
};

const sellBtn: React.CSSProperties = {
  padding:"8px 12px",
  borderRadius:8,
  border:"1px solid #ef4444",
  background:"#ef4444",
  color:"white",
  cursor:"pointer",
  fontSize:12,
  fontWeight:600,
  flex:1
};

const actionBtn: React.CSSProperties = {
  padding:"8px 12px",
  borderRadius:8,
  color:"white",
  cursor:"pointer",
  fontSize:12,
  fontWeight:600,
  transition: "all 0.2s ease",
  textAlign: "center",
  whiteSpace: "nowrap",
  overflow: "hidden",
  textOverflow: "ellipsis"
};

// New styles for enhanced controls
const controlsStyle: React.CSSProperties = {
  display: "flex",
  gap: "20px",
  marginBottom: "24px",
  padding: "20px",
  background: "linear-gradient(135deg, #22c55e15 0%, #16a34a10 100%)",
  borderRadius: "12px",
  border: "2px solid #22c55e40",
  boxShadow: "0 4px 12px rgba(34, 197, 94, 0.1)",
  flexWrap: "wrap",
  alignItems: "flex-start",
  minHeight: "80px",
  position: "relative",
  zIndex: 10
};

const controlGroupStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "6px",
  minWidth: "150px"
};

const labelStyle: React.CSSProperties = {
  fontSize: "12px",
  fontWeight: 600,
  color: "#888",
  textTransform: "uppercase",
  letterSpacing: "0.5px"
};

const selectStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderRadius: "8px",
  border: "1px solid #444",
  background: "#222",
  color: "#fff",
  fontSize: "14px",
  fontWeight: 500,
  cursor: "pointer",
  outline: "none"
};

const refreshButtonStyle: React.CSSProperties = {
  padding: "8px 16px",
  borderRadius: "8px",
  border: "1px solid #22c55e",
  background: "transparent",
  color: "#22c55e",
  fontSize: "14px",
  fontWeight: 600,
  cursor: "pointer",
  transition: "all 0.2s ease",
  marginTop: "20px"
};

const groupHeaderStyle: React.CSSProperties = {
  marginTop: "24px",
  marginBottom: "12px",
  padding: "12px 16px",
  background: "rgba(34, 197, 94, 0.1)",
  borderRadius: "8px",
  border: "1px solid rgba(34, 197, 94, 0.3)"
};

// Toggle button styles
const toggleGroupStyle: React.CSSProperties = {
  display: "flex",
  gap: "4px",
  flexWrap: "wrap"
};

const activeToggleStyle: React.CSSProperties = {
  padding: "10px 16px",
  borderRadius: "8px",
  border: "2px solid #22c55e",
  background: "#22c55e",
  color: "white",
  fontSize: "14px",
  fontWeight: 700,
  cursor: "pointer",
  transition: "all 0.2s ease",
  textTransform: "uppercase",
  letterSpacing: "0.5px",
  minWidth: "90px",
  textAlign: "center",
  boxShadow: "0 2px 8px rgba(34, 197, 94, 0.3)"
};

const inactiveToggleStyle: React.CSSProperties = {
  padding: "10px 16px",
  borderRadius: "8px",
  border: "2px solid #444",
  background: "#1a1a1a",
  color: "#ccc",
  fontSize: "14px",
  fontWeight: 500,
  cursor: "pointer",
  transition: "all 0.2s ease",
  textTransform: "uppercase",
  letterSpacing: "0.5px",
  minWidth: "90px",
  textAlign: "center",
  boxShadow: "0 1px 3px rgba(0, 0, 0, 0.3)"
};