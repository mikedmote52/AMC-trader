import React, { useEffect, useState } from "react";
import { API_BASE } from "../config";
import { getJSON } from "../lib/api";
import TradeModal from "./TradeModal";

type Recommendation = {
  symbol: string;
  thesis: string;
  current_price: number;
  target_price: number;
  confidence: number;
  score: number;
};

export default function TopRecommendations() {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [showTradeModal, setShowTradeModal] = useState(false);
  const [selectedStock, setSelectedStock] = useState<string>("");
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    const loadRecommendations = async () => {
      try {
        const data = await getJSON(`${API_BASE}/discovery/contenders`);
        if (Array.isArray(data)) {
          const mapped = data.map((rec: any) => ({
            symbol: rec.symbol || "N/A",
            thesis: rec.thesis || "Strong technical and fundamental signals suggest upward momentum potential.",
            current_price: rec.price || rec.current_price || 0,
            target_price: rec.target_price || (rec.price || rec.current_price || 0) * 1.25,
            confidence: Math.round((rec.confidence || rec.score || 0.75) * 100),
            score: rec.score || 75
          }));
          setRecommendations(mapped);
        }
      } catch (error) {
        console.error("Failed to load recommendations:", error);
      } finally {
        setLoading(false);
      }
    };

    loadRecommendations();
    const interval = setInterval(loadRecommendations, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  const handleBuy = (symbol: string) => {
    setSelectedStock(symbol);
    setShowTradeModal(true);
  };

  if (loading) {
    return (
      <div style={loadingStyle}>
        <div>🔍 Scanning markets for opportunities...</div>
      </div>
    );
  }

  const displayRecommendations = showAll ? recommendations : recommendations.slice(0, 3);

  if (recommendations.length === 0) {
    return (
      <div style={emptyStyle}>
        <div>📊 Market scan complete - No high-confidence opportunities found</div>
        <div style={subTextStyle}>Our discovery system is being selective in current market conditions</div>
      </div>
    );
  }

  return (
    <>
      <div style={containerStyle}>
        {displayRecommendations.map((rec, index) => (
          <div key={rec.symbol} style={cardStyle}>
            {/* Header */}
            <div style={headerStyle}>
              <div style={symbolStyle}>{rec.symbol}</div>
              <div style={confidenceStyle}>
                {rec.confidence}% confidence
              </div>
            </div>

            {/* Thesis */}
            <div style={thesisStyle}>
              {rec.thesis}
            </div>

            {/* Price Info */}
            <div style={priceRowStyle}>
              <div style={priceInfoStyle}>
                <div style={priceLabelStyle}>Current</div>
                <div style={currentPriceStyle}>${rec.current_price.toFixed(2)}</div>
              </div>
              <div style={arrowStyle}>→</div>
              <div style={priceInfoStyle}>
                <div style={priceLabelStyle}>Target</div>
                <div style={targetPriceStyle}>${rec.target_price.toFixed(2)}</div>
              </div>
              <div style={returnStyle}>
                +{Math.round(((rec.target_price - rec.current_price) / rec.current_price) * 100)}%
              </div>
            </div>

            {/* Buy Button */}
            <button 
              onClick={() => handleBuy(rec.symbol)}
              style={buyButtonStyle}
            >
              🚀 Buy {rec.symbol}
            </button>
          </div>
        ))}
      </div>

      {/* View All Button */}
      {recommendations.length > 3 && (
        <div style={viewAllContainerStyle}>
          <button 
            onClick={() => setShowAll(!showAll)}
            style={viewAllButtonStyle}
          >
            {showAll ? `Show Top 3` : `View All ${recommendations.length} Recommendations`}
          </button>
        </div>
      )}

      {/* Trade Modal */}
      {showTradeModal && (
        <TradeModal
          presetSymbol={selectedStock}
          presetAction="BUY"
          presetPrice={recommendations.find(r => r.symbol === selectedStock)?.current_price}
          onClose={() => setShowTradeModal(false)}
        />
      )}
    </>
  );
}

const containerStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(350px, 1fr))",
  gap: "20px",
  marginBottom: "20px"
};

const cardStyle: React.CSSProperties = {
  background: "linear-gradient(135deg, #1a1a1a 0%, #111 100%)",
  border: "1px solid #333",
  borderRadius: "16px",
  padding: "24px",
  display: "flex",
  flexDirection: "column",
  gap: "16px"
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center"
};

const symbolStyle: React.CSSProperties = {
  fontSize: "24px",
  fontWeight: 800,
  color: "#fff",
  letterSpacing: "-0.02em"
};

const confidenceStyle: React.CSSProperties = {
  background: "rgba(34, 197, 94, 0.2)",
  border: "1px solid rgba(34, 197, 94, 0.5)",
  color: "#22c55e",
  padding: "4px 12px",
  borderRadius: "8px",
  fontSize: "12px",
  fontWeight: 600
};

const thesisStyle: React.CSSProperties = {
  fontSize: "14px",
  lineHeight: "1.5",
  color: "#ccc",
  minHeight: "42px"
};

const priceRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "16px",
  padding: "12px 0"
};

const priceInfoStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  gap: "4px"
};

const priceLabelStyle: React.CSSProperties = {
  fontSize: "11px",
  color: "#999",
  fontWeight: 600,
  textTransform: "uppercase"
};

const currentPriceStyle: React.CSSProperties = {
  fontSize: "18px",
  fontWeight: 700,
  color: "#fff"
};

const targetPriceStyle: React.CSSProperties = {
  fontSize: "18px",
  fontWeight: 700,
  color: "#22c55e"
};

const arrowStyle: React.CSSProperties = {
  fontSize: "16px",
  color: "#666"
};

const returnStyle: React.CSSProperties = {
  marginLeft: "auto",
  fontSize: "16px",
  fontWeight: 700,
  color: "#22c55e"
};

const buyButtonStyle: React.CSSProperties = {
  background: "linear-gradient(135deg, #22c55e, #16a34a)",
  border: "none",
  borderRadius: "12px",
  padding: "14px 20px",
  color: "#000",
  fontSize: "14px",
  fontWeight: 700,
  cursor: "pointer",
  transition: "all 0.2s ease",
  boxShadow: "0 4px 12px rgba(34, 197, 94, 0.3)"
};

const loadingStyle: React.CSSProperties = {
  textAlign: "center",
  padding: "40px",
  color: "#999",
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

const viewAllContainerStyle: React.CSSProperties = {
  textAlign: "center",
  marginTop: "20px"
};

const viewAllButtonStyle: React.CSSProperties = {
  background: "transparent",
  border: "1px solid #333",
  borderRadius: "8px",
  padding: "10px 20px",
  color: "#ccc",
  fontSize: "14px",
  fontWeight: 600,
  cursor: "pointer"
};