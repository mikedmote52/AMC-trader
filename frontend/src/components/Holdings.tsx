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

  function normalizeHoldings(resp: any) {
    console.log("normalizeHoldings input:", resp);
    
    if (Array.isArray(resp)) {
      console.log("Found direct array:", resp);
      return resp;
    }
    
    const d = resp?.data ?? resp;
    console.log("Extracted data object:", d);
    
    if (Array.isArray(d)) {
      console.log("Found data as array:", d);
      return d;
    }
    
    if (Array.isArray(d?.positions)) {
      console.log("Found d.positions:", d.positions);
      return d.positions;
    }
    
    if (Array.isArray(resp?.positions)) {
      console.log("Found resp.positions:", resp.positions);
      return resp.positions;
    }
    
    if (Array.isArray(d?.items)) {
      console.log("Found d.items:", d.items);
      return d.items;
    }
    
    if (Array.isArray(d?.data)) {
      console.log("Found d.data:", d.data);
      return d.data;
    }
    
    console.log("No valid holdings structure found, returning empty array");
    return [];
  }

  async function fetchData() {
    try {
      setErr("");
      const apiResponse = await getJSON<any>(`${API_BASE}/portfolio/holdings`);
      console.log("=== HOLDINGS DEBUG ===");
      console.log("Raw holdings API response:", apiResponse);
      console.log("apiResponse.success:", apiResponse?.success);
      console.log("apiResponse.data:", apiResponse?.data);
      console.log("apiResponse.data.positions:", apiResponse?.data?.positions);
      console.log("Is apiResponse.data.positions an array?", Array.isArray(apiResponse?.data?.positions));
      
      const rows = normalizeHoldings(apiResponse);
      console.log("Normalized holdings rows:", rows);
      console.log("rows.length:", rows.length);
      
      if (rows.length === 0) {
        console.log("❌ Holdings array is empty — nothing to render");
        console.log("Full API response structure:", JSON.stringify(apiResponse, null, 2));
      } else {
        console.log(`✅ Found ${rows.length} holdings to render:`, rows);
      }
      
      setHoldings(rows);
      const debugUpdate = {
        holdingsStatus: "success", 
        holdingsCount: rows.length, 
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
    // Test API call manually
    console.log("🔍 Testing API call manually...");
    fetch(`${API_BASE}/portfolio/holdings`)
      .then(r => r.json())
      .then(data => {
        console.log("🔥 MANUAL API TEST RESULT:", data);
        console.log("🔥 Type:", typeof data);
        console.log("🔥 Keys:", Object.keys(data || {}));
        console.log("🔥 data.success:", data?.success);
        console.log("🔥 data.data:", data?.data);
        console.log("🔥 data.data?.positions:", data?.data?.positions);
      })
      .catch(err => console.log("🔥 MANUAL API ERROR:", err));

    fetchData();
    const id = setInterval(fetchData, 15_000);
    return () => clearInterval(id);
  }, []);

  const handleTrade = (symbol: string, action: "BUY" | "SELL") => {
    setTradePreset({ symbol, action });
    setShowTradeModal(true);
  };

  console.log("Holdings render state:", { holdings, length: holdings.length, err });
  
  // Add visual debug info on page
  const debugText = `Holdings: ${holdings.length} items, Status: ${err ? 'ERROR' : 'OK'}`;
  
  if (err) return (
    <div>
      <div style={{padding:12, color:"#c00"}}>Error loading holdings: {err}</div>
      <div style={{fontSize:10, color:"#666", padding:8}}>Debug: {debugText}</div>
    </div>
  );
  
  if (holdings.length === 0) return (
    <div>
      <div style={{padding:12, color:"#888"}}>No holdings found.</div>
      <div style={{fontSize:10, color:"#666", padding:8}}>Debug: {debugText} - Check console for API response</div>
    </div>
  );

  return (
    <>
      <div style={{display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(280px, 1fr))", gap:12}}>
        {holdings.map((holding, index) => {
          console.log(`Rendering holding ${index}:`, holding);
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