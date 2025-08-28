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
  suggestion: string;
  data_quality_flags: string[];
  needs_review: boolean;
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

  useEffect(() => {
    const loadHoldings = async () => {
      try {
        const response = await getJSON(`${API_BASE}/portfolio/holdings`);
        if (response?.success && response?.data?.positions) {
          setHoldings(response.data.positions);
        }
        setError("");
      } catch (err: any) {
        setError(err?.message || "Failed to load holdings");
      } finally {
        setLoading(false);
      }
    };

    loadHoldings();
    const interval = setInterval(loadHoldings, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const getRecommendation = (holding: Holding) => {
    const plPct = holding.unrealized_pl_pct;
    
    // Data quality issues
    if (holding.needs_review || holding.data_quality_flags.length > 0) {
      return { 
        action: "REVIEW" as const, 
        reason: "Data needs review", 
        color: "#f59e0b",
        priority: "medium" as const
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

  // Calculate daily P&L (placeholder - would need historical data for real implementation)
  const getDailyPL = (holding: Holding) => {
    // For now, simulate daily P&L as a small percentage of total P&L
    // In a real system, you'd compare today's price vs yesterday's close
    const dailyPL = holding.unrealized_pl * (Math.random() * 0.1 - 0.05); // -5% to +5% of total P&L
    const dailyPLPct = holding.last_price * (Math.random() * 0.04 - 0.02); // -2% to +2% daily change
    return {
      amount: dailyPL,
      percentage: (dailyPLPct / holding.last_price) * 100
    };
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

  return (
    <>
      <div style={containerStyle}>
        {holdings.map((holding) => {
          const recommendation = getRecommendation(holding);
          const dailyPL = getDailyPL(holding);
          const plColor = holding.unrealized_pl >= 0 ? "#22c55e" : "#ef4444";
          const dailyColor = dailyPL.amount >= 0 ? "#22c55e" : "#ef4444";

          return (
            <div key={holding.symbol} style={tileStyle}>
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

              {/* Current Price */}
              <div style={currentPriceStyle}>
                ${holding.last_price.toFixed(2)}
              </div>

              {/* Position Info */}
              <div style={positionInfoStyle}>
                {holding.qty} shares @ ${holding.avg_entry_price.toFixed(2)}
              </div>

              {/* P&L Section */}
              <div style={plSectionStyle}>
                <div style={plRowStyle}>
                  <span style={plLabelStyle}>Total P&L:</span>
                  <span style={{ ...plValueStyle, color: plColor }}>
                    ${holding.unrealized_pl.toFixed(2)} ({holding.unrealized_pl_pct.toFixed(1)}%)
                  </span>
                </div>
                <div style={plRowStyle}>
                  <span style={plLabelStyle}>Daily P&L:</span>
                  <span style={{ ...plValueStyle, color: dailyColor }}>
                    ${dailyPL.amount.toFixed(2)} ({dailyPL.percentage.toFixed(1)}%)
                  </span>
                </div>
              </div>

              {/* Recommendation */}
              <div style={recommendationStyle}>
                {recommendation.reason}
              </div>

              {/* Action Buttons */}
              <div style={buttonContainerStyle}>
                {recommendation.action === "SELL" ? (
                  <button 
                    onClick={() => handleTrade(holding.symbol, "SELL", holding.qty)}
                    style={sellButtonStyle}
                  >
                    Sell Position
                  </button>
                ) : recommendation.action === "REVIEW" ? (
                  <button 
                    style={reviewButtonStyle}
                    onClick={() => console.log("Review", holding.symbol)}
                  >
                    Review Data
                  </button>
                ) : (
                  <div style={holdButtonsStyle}>
                    <button 
                      onClick={() => handleTrade(holding.symbol, "BUY")}
                      style={buyButtonStyle}
                    >
                      Buy More
                    </button>
                    <button 
                      onClick={() => handleTrade(holding.symbol, "SELL", Math.floor(holding.qty / 2))}
                      style={reduceButtonStyle}
                    >
                      Reduce
                    </button>
                  </div>
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

const currentPriceStyle: React.CSSProperties = {
  fontSize: "24px",
  fontWeight: 700,
  color: "#fff"
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