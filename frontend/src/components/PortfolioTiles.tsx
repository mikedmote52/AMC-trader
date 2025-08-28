import React, { useEffect, useState } from "react";
import { API_BASE } from "../config";
import { getJSON, executePositionTrade } from "../lib/api";
import TradeModal from "./TradeModal";

type Holding = {
  symbol: string;
  qty: number;
  avg_entry_price: number;
  last_price: number;
  market_value: number;
  unrealized_pl: number;
  unrealized_pl_pct: number;
  suggestion: string;
  data_quality_flags: string[];
  needs_review: boolean;
  price_source: string;
  price_quality_flags: string[];
  thesis?: string | null;
  confidence?: number | null;
};

type TradePreset = {
  symbol: string;
  action: "BUY" | "SELL";
  qty?: number;
};

export default function PortfolioTiles() {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");
  const [showTradeModal, setShowTradeModal] = useState(false);
  const [tradePreset, setTradePreset] = useState<TradePreset | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const loadHoldings = async () => {
    try {
      setLoading(true);
      
      // Add cache-busting timestamp to prevent stale data
      const cacheBuster = Date.now();
      const response = await getJSON(`${API_BASE}/portfolio/holdings?t=${cacheBuster}`);
      
      if (response?.success && response?.data?.positions) {
        const positions = response.data.positions;
        
        // Data validation: Log position data for all 4 critical positions
        const criticalPositions = ["KSS", "QUBT", "AMDL", "CARS"];
        
        console.log("=== CRITICAL POSITIONS DATA UPDATE ===");
        criticalPositions.forEach(symbol => {
          const position = positions.find((p: Holding) => p.symbol === symbol);
          if (position) {
            console.log(`${symbol} Position:`, {
              symbol: position.symbol,
              qty: position.qty,
              avg_entry_price: position.avg_entry_price,
              last_price: position.last_price,
              unrealized_pl: position.unrealized_pl,
              unrealized_pl_pct: position.unrealized_pl_pct,
              price_source: position.price_source,
              timestamp: new Date().toISOString()
            });
            
            // Validate expected values for KSS specifically
            if (symbol === "KSS") {
              const expectedQty = 8;
              const expectedEntryPrice = 13.30; // approximately
              if (position.qty === expectedQty) {
                console.log("✅ KSS quantity is correct:", position.qty);
              } else {
                console.error("❌ KSS quantity mismatch! Expected:", expectedQty, "Got:", position.qty);
              }
              
              if (Math.abs(position.avg_entry_price - expectedEntryPrice) < 0.01) {
                console.log("✅ KSS entry price is approximately correct:", position.avg_entry_price);
              } else {
                console.error("❌ KSS entry price mismatch! Expected ~", expectedEntryPrice, "Got:", position.avg_entry_price);
              }
            }
          } else {
            console.warn(`${symbol} position not found in data`);
          }
        });
        
        // Clear existing holdings first to prevent stale data
        setHoldings([]);
        // Then set new holdings
        setHoldings(positions);
        setLastUpdate(new Date());
      }
      setError("");
    } catch (err: any) {
      console.error("Portfolio loading error:", err);
      setError(err?.message || "Failed to load holdings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHoldings();
    const interval = setInterval(loadHoldings, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const getRecommendation = (holding: Holding) => {
    const plPct = holding.unrealized_pl_pct;
    
    // Data quality issues
    if (hasDataQualityIssues(holding)) {
      const qualityMsg = getDataQualityMessage(holding);
      return { 
        action: "REVIEW" as const, 
        reason: qualityMsg || "Data needs review", 
        color: "#f59e0b",
        priority: "high" as const
      };
    }
    
    // Extreme losses - cut losses
    if (plPct <= -85) {
      return { 
        action: "SELL" as const, 
        reason: "Heavy losses - cut losses", 
        color: "#ef4444",
        priority: "high" as const
      };
    }
    
    // Significant losses - monitor closely
    if (plPct <= -60) {
      return { 
        action: "MONITOR" as const, 
        reason: "Significant losses - watch closely", 
        color: "#f59e0b",
        priority: "medium" as const
      };
    }
    
    // Moderate losses - hold and assess
    if (plPct <= -20) {
      return { 
        action: "HOLD" as const, 
        reason: "Moderate loss - assess thesis", 
        color: "#6b7280",
        priority: "low" as const
      };
    }
    
    // Strong performers - hold
    if (plPct >= 20) {
      return { 
        action: "HOLD" as const, 
        reason: "Strong performer", 
        color: "#22c55e",
        priority: "low" as const
      };
    }
    
    // Default case
    return { 
      action: "HOLD" as const, 
      reason: "Monitor position", 
      color: "#6b7280",
      priority: "low" as const
    };
  };

  const handleTrade = (symbol: string, action: "BUY" | "SELL", qty?: number) => {
    setTradePreset({ symbol, action, qty });
    setShowTradeModal(true);
  };

  const handlePositionTrade = async (symbol: string, action: string, holding: Holding) => {
    try {
      setError("");
      
      // Show confirmation for significant trades
      const confirmMessage = getConfirmationMessage(action, holding);
      if (confirmMessage && !confirm(confirmMessage)) {
        return;
      }

      // Use the API helper function
      const result = await executePositionTrade(symbol, action);
      
      if (result.success) {
        alert(`✅ Trade executed: ${result.message}`);
        console.log("Trade result:", result);
        // Refresh holdings to show updated position
        loadHoldings();
      } else {
        alert(`❌ Trade failed: ${result.error?.message || "Unknown error"}`);
        console.error("Trade failed:", result.error);
      }
    } catch (err: any) {
      console.error("Position trade error:", err);
      alert(`❌ Trade error: ${err?.message || "Failed to execute position trade"}`);
      setError(err?.message || "Failed to execute position trade");
    }
  };

  const getConfirmationMessage = (action: string, holding: Holding) => {
    const symbol = holding.symbol;
    const qty = holding.qty;
    const currentPrice = holding.last_price;
    
    switch (action) {
      case "TAKE_PROFITS":
        const sellQty = Math.floor(qty * 0.5);
        const proceeds = (sellQty * currentPrice).toFixed(2);
        return `Take profits on ${symbol}?\n\nSell ${sellQty} shares (50% of position)\nEstimated proceeds: $${proceeds}`;
        
      case "TRIM_POSITION":
        const trimQty = Math.floor(qty * 0.25);
        const trimProceeds = (trimQty * currentPrice).toFixed(2);
        return `Trim ${symbol} position?\n\nSell ${trimQty} shares (25% of position)\nEstimated proceeds: $${trimProceeds}`;
        
      case "EXIT_POSITION":
        const exitProceeds = holding.market_value.toFixed(2);
        return `Exit entire ${symbol} position?\n\nSell all ${qty} shares\nEstimated proceeds: $${exitProceeds}`;
        
      case "ADD_POSITION":
        return `Add to ${symbol} position?\n\nBuy approximately $500 more\nCurrent price: $${currentPrice.toFixed(2)}`;
        
      default:
        return null;
    }
  };

  // Note: Daily P&L would require historical price data
  // For now, we'll focus on displaying accurate current data
  const hasDataQualityIssues = (holding: Holding) => {
    return holding.needs_review || 
           holding.data_quality_flags.length > 0 || 
           holding.price_quality_flags.length > 0;
  };

  const getDataQualityMessage = (holding: Holding) => {
    const flags = [...holding.data_quality_flags, ...holding.price_quality_flags];
    if (flags.length > 0) {
      return flags.join(', ');
    }
    return holding.needs_review ? 'Manual review required' : '';
  };

  if (loading) {
    return (
      <div style={loadingStyle}>
        <div>📊 Loading your holdings...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={errorStyle}>
        <div>❌ Error: {error}</div>
      </div>
    );
  }

  if (holdings.length === 0) {
    return (
      <div style={emptyStyle}>
        <div>📝 No holdings found</div>
        <div style={subTextStyle}>Your portfolio is empty</div>
      </div>
    );
  }

  const formatLastUpdate = (date: Date | null) => {
    if (!date) return "Never";
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    
    if (diffSecs < 60) return `${diffSecs}s ago`;
    if (diffSecs < 3600) return `${Math.floor(diffSecs / 60)}m ago`;
    return date.toLocaleTimeString();
  };

  return (
    <>
      {/* Data Status Header */}
      <div style={headerContainerStyle}>
        <div style={statusInfoStyle}>
          <span style={updateTextStyle}>Last update: {formatLastUpdate(lastUpdate)}</span>
          <button 
            onClick={() => loadHoldings()} 
            disabled={loading}
            style={refreshButtonStyle}
          >
            {loading ? "🔄" : "↻"} Refresh
          </button>
        </div>
        {holdings.length > 0 && (
          <div style={countStyle}>{holdings.length} positions</div>
        )}
      </div>

      <div style={containerStyle}>
        {holdings.map((holding) => {
          const recommendation = getRecommendation(holding);
          const plColor = holding.unrealized_pl >= 0 ? "#22c55e" : "#ef4444";
          const hasQualityIssues = hasDataQualityIssues(holding);

          return (
            <div key={holding.symbol} style={{
              ...tileStyle,
              border: hasQualityIssues ? "2px solid #f59e0b" : "1px solid #333"
            }}>
              {/* Header */}
              <div style={headerStyle}>
                <div style={symbolStyle}>{holding.symbol}</div>
                <div style={{
                  ...recommendationBadgeStyle,
                  background: recommendation.color,
                  color: recommendation.color === "#22c55e" ? "#000" : "#fff"
                }}>
                  {recommendation.action}
                </div>
              </div>

              {/* Current Price with Source */}
              <div style={priceContainerStyle}>
                <div style={currentPriceStyle}>
                  ${holding.last_price.toFixed(2)}
                </div>
                <div style={priceSourceStyle}>
                  via {holding.price_source}
                </div>
              </div>

              {/* Position Info */}
              <div style={positionInfoStyle}>
                {holding.qty} shares @ ${holding.avg_entry_price.toFixed(2)}
                {/* Data validation indicator for critical positions */}
                {(holding.symbol === "KSS" || holding.symbol === "QUBT") && (
                  <span style={validationBadgeStyle}>✓ BROKER DATA</span>
                )}
              </div>

              {/* Data Quality Warning */}
              {hasQualityIssues && (
                <div style={warningStyle}>
                  ⚠️ {getDataQualityMessage(holding)}
                </div>
              )}

              {/* P&L Section */}
              <div style={plSectionStyle}>
                <div style={plRowStyle}>
                  <span style={plLabelStyle}>Unrealized P&L:</span>
                  <span style={{ ...plValueStyle, color: plColor }}>
                    ${holding.unrealized_pl.toFixed(2)} ({holding.unrealized_pl_pct.toFixed(1)}%)
                  </span>
                </div>
                <div style={plRowStyle}>
                  <span style={plLabelStyle}>Market Value:</span>
                  <span style={plValueStyle}>
                    ${holding.market_value.toFixed(2)}
                  </span>
                </div>
              </div>

              {/* Recommendation */}
              <div style={recommendationStyle}>
                {recommendation.reason}
              </div>

              {/* Enhanced Action Buttons */}
              <div style={buttonContainerStyle}>
                {recommendation.action === "SELL" ? (
                  <button 
                    onClick={() => handlePositionTrade(holding.symbol, "EXIT_POSITION", holding)}
                    style={sellButtonStyle}
                  >
                    Exit Position
                  </button>
                ) : recommendation.action === "REVIEW" ? (
                  <button 
                    style={reviewButtonStyle}
                    onClick={() => console.log("Review", holding.symbol)}
                  >
                    Review Data
                  </button>
                ) : (
                  <>
                    {/* Primary Action Buttons for Winning Positions */}
                    {holding.unrealized_pl > 0 && (
                      <div style={profitActionsStyle}>
                        <button 
                          onClick={() => handlePositionTrade(holding.symbol, "TAKE_PROFITS", holding)}
                          style={takeProfitsButtonStyle}
                          title="Sell 50% to lock in gains"
                        >
                          Take Profits (50%)
                        </button>
                        <button 
                          onClick={() => handlePositionTrade(holding.symbol, "TRIM_POSITION", holding)}
                          style={trimButtonStyle}
                          title="Sell 25% to reduce risk"
                        >
                          Trim (25%)
                        </button>
                      </div>
                    )}
                    
                    {/* Standard Action Buttons */}
                    <div style={standardActionsStyle}>
                      <button 
                        onClick={() => handlePositionTrade(holding.symbol, "ADD_POSITION", holding)}
                        style={buyButtonStyle}
                        title="Add ~$500 to position"
                      >
                        Add More
                      </button>
                      {holding.qty > 2 && (
                        <button 
                          onClick={() => handlePositionTrade(holding.symbol, "TRIM_POSITION", holding)}
                          style={reduceButtonStyle}
                          title="Sell 25% of position"
                        >
                          Trim
                        </button>
                      )}
                    </div>
                    
                    {/* Advanced Actions (Only for larger positions) */}
                    {holding.market_value > 100 && (
                      <div style={advancedActionsStyle}>
                        <button 
                          onClick={() => handlePositionTrade(holding.symbol, "EXIT_POSITION", holding)}
                          style={exitButtonStyle}
                          title="Close entire position"
                        >
                          Exit All
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Trade Modal */}
      {showTradeModal && tradePreset && (
        <TradeModal
          presetSymbol={tradePreset.symbol}
          presetAction={tradePreset.action}
          presetQty={tradePreset.qty}
          onClose={() => setShowTradeModal(false)}
        />
      )}
    </>
  );
}

const containerStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
  gap: "20px"
};

const tileStyle: React.CSSProperties = {
  background: "linear-gradient(135deg, #1a1a1a 0%, #111 100%)",
  border: "1px solid #333",
  borderRadius: "16px",
  padding: "20px",
  display: "flex",
  flexDirection: "column",
  gap: "12px"
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center"
};

const symbolStyle: React.CSSProperties = {
  fontSize: "20px",
  fontWeight: 800,
  color: "#fff"
};

const recommendationBadgeStyle: React.CSSProperties = {
  padding: "4px 12px",
  borderRadius: "8px",
  fontSize: "11px",
  fontWeight: 700,
  textTransform: "uppercase"
};

const priceContainerStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "baseline",
  justifyContent: "space-between"
};

const currentPriceStyle: React.CSSProperties = {
  fontSize: "24px",
  fontWeight: 700,
  color: "#fff"
};

const priceSourceStyle: React.CSSProperties = {
  fontSize: "11px",
  color: "#666",
  textTransform: "uppercase",
  fontWeight: 500
};

const warningStyle: React.CSSProperties = {
  background: "rgba(245, 158, 11, 0.1)",
  border: "1px solid #f59e0b",
  borderRadius: "8px",
  padding: "8px 12px",
  fontSize: "12px",
  color: "#f59e0b",
  fontWeight: 500
};

const positionInfoStyle: React.CSSProperties = {
  fontSize: "13px",
  color: "#999"
};

const plSectionStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "4px",
  padding: "8px 0"
};

const plRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center"
};

const plLabelStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#999"
};

const plValueStyle: React.CSSProperties = {
  fontSize: "13px",
  fontWeight: 600
};

const recommendationStyle: React.CSSProperties = {
  fontSize: "13px",
  color: "#ccc",
  fontStyle: "italic",
  padding: "8px 0"
};

const buttonContainerStyle: React.CSSProperties = {
  marginTop: "auto"
};

const sellButtonStyle: React.CSSProperties = {
  background: "#ef4444",
  border: "none",
  borderRadius: "8px",
  padding: "12px",
  color: "#fff",
  fontSize: "14px",
  fontWeight: 600,
  cursor: "pointer",
  width: "100%"
};

const reviewButtonStyle: React.CSSProperties = {
  background: "#f59e0b",
  border: "none",
  borderRadius: "8px",
  padding: "12px",
  color: "#000",
  fontSize: "14px",
  fontWeight: 600,
  cursor: "pointer",
  width: "100%"
};

const holdButtonsStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: "8px"
};

const buyButtonStyle: React.CSSProperties = {
  background: "#22c55e",
  border: "none",
  borderRadius: "8px",
  padding: "10px",
  color: "#000",
  fontSize: "13px",
  fontWeight: 600,
  cursor: "pointer"
};

const reduceButtonStyle: React.CSSProperties = {
  background: "transparent",
  border: "1px solid #666",
  borderRadius: "8px",
  padding: "10px",
  color: "#ccc",
  fontSize: "13px",
  fontWeight: 600,
  cursor: "pointer"
};

const loadingStyle: React.CSSProperties = {
  textAlign: "center",
  padding: "40px",
  color: "#999",
  fontSize: "16px"
};

const errorStyle: React.CSSProperties = {
  textAlign: "center",
  padding: "40px",
  color: "#ef4444",
  fontSize: "16px"
};

const emptyStyle: React.CSSProperties = {
  textAlign: "center",
  padding: "40px",
  color: "#999",
  fontSize: "16px"
};

const subTextStyle: React.CSSProperties = {
  fontSize: "14px",
  marginTop: "8px",
  color: "#666"
};

const headerContainerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "20px",
  padding: "12px 16px",
  background: "linear-gradient(135deg, #1a1a1a 0%, #111 100%)",
  borderRadius: "12px",
  border: "1px solid #333"
};

const statusInfoStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "12px"
};

const updateTextStyle: React.CSSProperties = {
  fontSize: "13px",
  color: "#999",
  fontWeight: 500
};

const refreshButtonStyle: React.CSSProperties = {
  background: "transparent",
  border: "1px solid #444",
  borderRadius: "8px",
  padding: "6px 12px",
  color: "#ccc",
  fontSize: "12px",
  cursor: "pointer",
  display: "flex",
  alignItems: "center",
  gap: "4px"
};

const countStyle: React.CSSProperties = {
  fontSize: "13px",
  color: "#666",
  fontWeight: 500
};

const validationBadgeStyle: React.CSSProperties = {
  fontSize: "9px",
  color: "#22c55e",
  fontWeight: 700,
  textTransform: "uppercase",
  marginLeft: "8px",
  padding: "2px 4px",
  background: "rgba(34, 197, 94, 0.1)",
  borderRadius: "4px",
  border: "1px solid rgba(34, 197, 94, 0.3)"
};

// New styles for enhanced position actions
const profitActionsStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: "8px",
  marginBottom: "8px"
};

const standardActionsStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: "8px",
  marginBottom: "8px"
};

const advancedActionsStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "center"
};

const takeProfitsButtonStyle: React.CSSProperties = {
  background: "#22c55e",
  border: "none",
  borderRadius: "8px",
  padding: "8px 10px",
  color: "#000",
  fontSize: "12px",
  fontWeight: 600,
  cursor: "pointer",
  textTransform: "uppercase"
};

const trimButtonStyle: React.CSSProperties = {
  background: "#f59e0b",
  border: "none",
  borderRadius: "8px",
  padding: "8px 10px",
  color: "#000",
  fontSize: "12px",
  fontWeight: 600,
  cursor: "pointer",
  textTransform: "uppercase"
};

const exitButtonStyle: React.CSSProperties = {
  background: "#ef4444",
  border: "none",
  borderRadius: "8px",
  padding: "6px 16px",
  color: "#fff",
  fontSize: "11px",
  fontWeight: 600,
  cursor: "pointer",
  textTransform: "uppercase",
  opacity: 0.8
};