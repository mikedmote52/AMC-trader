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

  async function fetchData() {
    try {
      setErr("");
      
      // Fetch holdings and contenders in parallel
      const [holdingsData, contendersData] = await Promise.all([
        getJSON<any>(`${API_BASE}/portfolio/holdings`),
        getJSON<any>(`${API_BASE}/discovery/contenders`)
      ]);
      
      // Extract positions from the holdings response structure
      const positions = holdingsData?.data?.positions || holdingsData?.positions || [];
      setHoldings(Array.isArray(positions) ? positions : []);
      setContenders(Array.isArray(contendersData) ? contendersData : []);
    } catch (e: any) {
      setErr(e?.message || String(e));
    }
  }

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, 15_000);
    return () => clearInterval(id);
  }, []);

  const handleTrade = (symbol: string, action: "BUY" | "SELL", qty?: number) => {
    setTradePreset({ symbol, action, qty });
    setShowTradeModal(true);
  };

  const getRecommendation = (holding: Holding) => {
    const plPct = holding.unrealized_pl_pct;
    const suggestion = holding.suggestion || "";
    
    if (plPct <= -80) return { action: "SELL", reason: "Heavy loss - cut losses", color: "#ef4444" };
    if (plPct <= -50) return { action: "HOLD", reason: "Monitor closely", color: "#f59e0b" };
    if (plPct >= 20) return { action: "HOLD", reason: "Strong performer", color: "#22c55e" };
    if (suggestion.includes("reduce")) return { action: "SELL", reason: "Reduce position", color: "#ef4444" };
    return { action: "HOLD", reason: "Monitor", color: "#6b7280" };
  };

  if (err) return <div style={{padding:12, color:"#c00"}}>Error loading holdings: {err}</div>;
  if (!holdings.length) return <div style={{padding:12, color:"#888"}}>No holdings found.</div>;

  return (
    <>
      <PortfolioSummary holdings={holdings} isLoading={!holdings.length && !err} />
      <div className="grid-responsive">
        {holdings.map((holding) => {
          const plColor = holding.unrealized_pl >= 0 ? "#22c55e" : "#ef4444";
          const recommendation = getRecommendation(holding);
          
          return (
            <div key={holding.symbol} style={cardStyle}>
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
              
              <div style={{fontSize:14, marginBottom:12, color: recommendation.color, fontWeight:600}}>
                {recommendation.reason}
              </div>
              
              <div style={{fontSize:13, marginBottom:12, lineHeight:1.4}}>
                <div>Position: {holding.qty} shares @ ${holding.avg_entry_price.toFixed(2)}</div>
                <div>Current: ${holding.last_price.toFixed(2)} • Value: ${holding.market_value.toFixed(2)}</div>
                <div style={{color: plColor, fontSize:15, fontWeight:600}}>
                  P&L: ${holding.unrealized_pl.toFixed(2)} ({holding.unrealized_pl_pct.toFixed(1)}%)
                </div>
              </div>
              
              <div style={{display:"flex", gap:8}}>
                {recommendation.action === "SELL" ? (
                  <button 
                    onClick={() => handleTrade(holding.symbol, "SELL", holding.qty)} 
                    style={{...sellBtn, flex: 1}}
                  >
                    Sell Position
                  </button>
                ) : (
                  <>
                    <button 
                      onClick={() => handleTrade(holding.symbol, "BUY")} 
                      style={{...buyBtn, opacity: 0.7}}
                    >
                      Buy More
                    </button>
                    <button 
                      onClick={() => handleTrade(holding.symbol, "SELL", Math.floor(holding.qty / 2))} 
                      style={{...sellBtn, opacity: 0.7}}
                    >
                      Reduce
                    </button>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>

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
  color:"#eee"
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