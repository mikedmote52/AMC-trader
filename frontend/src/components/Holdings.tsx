import React, { useEffect, useState } from "react";
import { API_BASE } from "../config";
import { getJSON } from "../lib/api";
import TradeModal from "./TradeModal";

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


export default function Holdings({ onDebugUpdate }: { onDebugUpdate?: (info: any) => void }) {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [err, setErr] = useState<string>("");
  const [showTradeModal, setShowTradeModal] = useState(false);
  const [tradePreset, setTradePreset] = useState<{symbol: string; action: "BUY" | "SELL"} | null>(null);
  const [debugInfo, setDebugInfo] = useState<{holdingsStatus: string, holdingsCount: number, lastUpdated: string}>({
    holdingsStatus: "loading", holdingsCount: 0, lastUpdated: new Date().toLocaleTimeString()
  });

  function normalizeHoldings(x: any): any[] {
    console.log("normalizeHoldings input:", x);
    
    // Precedence order as specified
    if (Array.isArray(x)) {
      console.log("Found direct array:", x);
      return x;
    }
    
    if (x?.data && Array.isArray(x.data)) {
      console.log("Found data array:", x.data);
      return x.data;
    }
    
    if (x?.items && Array.isArray(x.items)) {
      console.log("Found items array:", x.items);
      return x.items;
    }
    
    if (x?.positions && Array.isArray(x.positions)) {
      console.log("Found positions array:", x.positions);
      return x.positions;
    }
    
    if (x?.data?.positions && Array.isArray(x.data.positions)) {
      console.log("Found data.positions:", x.data.positions);
      return x.data.positions;
    }
    
    console.log("No valid holdings structure found, returning empty array");
    return [];
  }

  async function fetchData() {
    try {
      setErr("");
      const holdingsData = await getJSON<any>(`${API_BASE}/portfolio/holdings`);
      console.log("Raw holdings API response:", holdingsData);
      
      const normalized = normalizeHoldings(holdingsData);
      console.log("Normalized holdings array:", normalized);
      
      if (!normalized || normalized.length === 0) {
        console.log("Holdings array is empty — nothing to render");
        console.log("API response structure:", JSON.stringify(holdingsData, null, 2));
      } else {
        console.log(`Found ${normalized.length} holdings to render:`, normalized);
      }
      
      setHoldings(normalized);
      const debugUpdate = {
        holdingsStatus: "success", 
        holdingsCount: normalized.length, 
        lastUpdated: new Date().toLocaleTimeString()
      };
      setDebugInfo(debugUpdate);
      onDebugUpdate?.(debugUpdate);
    } catch (e: any) {
      console.error("Holdings fetch error:", e);
      setErr(e?.message || String(e));
      const debugUpdate = {
        holdingsStatus: "error", 
        holdingsCount: 0, 
        lastUpdated: new Date().toLocaleTimeString()
      };
      setDebugInfo(debugUpdate);
      onDebugUpdate?.(debugUpdate);
    }
  }

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, 15_000);
    return () => clearInterval(id);
  }, []);

  const handleTrade = (symbol: string, action: "BUY" | "SELL") => {
    setTradePreset({ symbol, action });
    setShowTradeModal(true);
  };

  console.log("Holdings state:", { holdings, length: holdings.length, err });
  
  if (err) return <div style={{padding:12, color:"#c00"}}>Error loading holdings: {err}</div>;
  if (!holdings.length) return <div style={{padding:12, color:"#888"}}>No holdings found.</div>;

  return (
    <>
      <div style={{display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(280px, 1fr))", gap:12}}>
        {holdings.map((holding) => {
          const plColor = (holding.unrealized_pl ?? 0) >= 0 ? "#22c55e" : "#ef4444";
          
          return (
            <div key={holding.symbol} style={cardStyle}>
              <div style={{fontSize:16, fontWeight:700, marginBottom:8}}>
                {holding.symbol} • {holding.qty ?? 0}
              </div>
              
              <div style={{fontSize:14, marginBottom:8, lineHeight:1.4}}>
                <div>Last: ${(holding.last_price ?? 0).toFixed(2)} | Avg: ${(holding.avg_entry_price ?? 0).toFixed(2)}</div>
                <div>Value: ${(holding.market_value ?? 0).toFixed(2)}</div>
                <div style={{color: plColor}}>
                  P&L: ${(holding.unrealized_pl ?? 0).toFixed(2)} ({((holding.unrealized_pl_pct ?? 0) * 100).toFixed(1)}%)
                </div>
              </div>
              
              {(holding.thesis || holding.confidence != null || holding.suggestion) && (
                <div style={{fontSize:12, color:"#bbb", marginBottom:8, lineHeight:1.3}}>
                  {holding.suggestion && <div><strong>Action:</strong> {holding.suggestion}</div>}
                  {holding.confidence != null && <div><strong>Confidence:</strong> {holding.confidence}</div>}
                  {holding.thesis && <div><strong>Thesis:</strong> {holding.thesis}</div>}
                </div>
              )}
              
              <div style={{display:"flex", gap:8}}>
                <button 
                  onClick={() => handleTrade(holding.symbol, "BUY")} 
                  style={buyBtn}
                >
                  Buy/Increase
                </button>
                <button 
                  onClick={() => handleTrade(holding.symbol, "SELL")} 
                  style={sellBtn}
                >
                  Reduce/Sell
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {showTradeModal && tradePreset && (
        <TradeModal
          presetSymbol={tradePreset.symbol}
          presetAction={tradePreset.action}
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