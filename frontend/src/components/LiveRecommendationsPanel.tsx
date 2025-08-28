import React from "react";

type Recommendation = {
  symbol: string;
  confidence: number;
  pattern: string;
  volume: number;
  volumeMultiplier: number;
  entryPrice: number;
  targetPrice: number;
  potentialReturn: number;
  timestamp: string;
};

type LiveRecommendationsPanelProps = {
  recommendations: Recommendation[];
  isLoading?: boolean;
};

export default function LiveRecommendationsPanel({ recommendations, isLoading }: LiveRecommendationsPanelProps) {
  if (isLoading) {
    return (
      <div style={containerStyle}>
        <div style={headerStyle}>
          <span style={titleStyle}>🌟 CURRENT TOP RECOMMENDATIONS</span>
          <div style={loadingBadgeStyle}>Scanning...</div>
        </div>
        <div style={loadingContentStyle}>
          <div>Loading live recommendations...</div>
        </div>
      </div>
    );
  }

  if (!recommendations.length) {
    return (
      <div style={containerStyle}>
        <div style={headerStyle}>
          <span style={titleStyle}>🌟 CURRENT TOP RECOMMENDATIONS</span>
          <div style={emptyBadgeStyle}>Market Quiet</div>
        </div>
        <div style={emptyContentStyle}>
          <div>No high-confidence opportunities found</div>
          <div style={emptySubtextStyle}>Next scan in progress...</div>
        </div>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <span style={titleStyle}>🌟 CURRENT TOP RECOMMENDATIONS</span>
        <div style={countBadgeStyle}>{recommendations.length} Active</div>
      </div>

      <div style={recommendationsListStyle}>
        {recommendations.map((rec, index) => (
          <div key={rec.symbol} style={recommendationCardStyle}>
            <div style={rankBadgeStyle(index + 1)}>
              {index === 0 ? "🥇" : index === 1 ? "🥈" : index === 2 ? "🥉" : `#${index + 1}`}
            </div>
            
            <div style={recommendationContentStyle}>
              <div style={symbolRowStyle}>
                <span style={symbolStyle}>{rec.symbol}</span>
                <span style={confidenceStyle(rec.confidence)}>
                  {rec.confidence}% confidence
                </span>
              </div>

              <div style={metricsRowStyle}>
                <div style={metricStyle}>
                  <span style={metricLabelStyle}>Volume:</span>
                  <span style={metricValueStyle}>{rec.volumeMultiplier.toFixed(1)}x</span>
                </div>
                <div style={metricStyle}>
                  <span style={metricLabelStyle}>Pattern:</span>
                  <span style={metricValueStyle}>{rec.pattern}</span>
                </div>
              </div>

              <div style={priceRowStyle}>
                <div style={priceStyle}>
                  <span style={priceLabelStyle}>Entry:</span>
                  <span style={priceValueStyle}>${rec.entryPrice.toFixed(2)}</span>
                </div>
                <div style={priceStyle}>
                  <span style={priceLabelStyle}>Target:</span>
                  <span style={targetPriceStyle}>${rec.targetPrice.toFixed(2)}</span>
                </div>
                <div style={returnStyle}>
                  <span style={returnValueStyle}>+{rec.potentialReturn.toFixed(0)}%</span>
                </div>
              </div>

              <div style={timestampStyle}>
                Updated: {new Date(rec.timestamp).toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const containerStyle: React.CSSProperties = {
  background: "#0a0a0a",
  border: "1px solid #333",
  borderRadius: 16,
  padding: 20,
  marginBottom: 24,
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: 16,
};

const titleStyle: React.CSSProperties = {
  fontSize: 16,
  fontWeight: 700,
  color: "#eee",
};

const loadingBadgeStyle: React.CSSProperties = {
  background: "rgba(59, 130, 246, 0.2)",
  border: "1px solid rgba(59, 130, 246, 0.5)",
  borderRadius: 8,
  padding: "4px 8px",
  fontSize: 11,
  fontWeight: 600,
  color: "#3b82f6",
};

const emptyBadgeStyle: React.CSSProperties = {
  background: "rgba(156, 163, 175, 0.2)",
  border: "1px solid rgba(156, 163, 175, 0.5)",
  borderRadius: 8,
  padding: "4px 8px",
  fontSize: 11,
  fontWeight: 600,
  color: "#9ca3af",
};

const countBadgeStyle: React.CSSProperties = {
  background: "rgba(34, 197, 94, 0.2)",
  border: "1px solid rgba(34, 197, 94, 0.5)",
  borderRadius: 8,
  padding: "4px 8px",
  fontSize: 11,
  fontWeight: 600,
  color: "#22c55e",
};

const loadingContentStyle: React.CSSProperties = {
  textAlign: "center",
  color: "#999",
  fontSize: 14,
  padding: 20,
};

const emptyContentStyle: React.CSSProperties = {
  textAlign: "center",
  color: "#999",
  fontSize: 14,
  padding: 20,
};

const emptySubtextStyle: React.CSSProperties = {
  fontSize: 12,
  color: "#666",
  marginTop: 4,
};

const recommendationsListStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 12,
};

const recommendationCardStyle: React.CSSProperties = {
  background: "#111",
  border: "1px solid #333",
  borderRadius: 12,
  padding: 16,
  display: "flex",
  gap: 12,
};

const rankBadgeStyle = (rank: number): React.CSSProperties => ({
  background: rank <= 3 ? "rgba(251, 191, 36, 0.2)" : "rgba(156, 163, 175, 0.2)",
  border: rank <= 3 ? "1px solid rgba(251, 191, 36, 0.5)" : "1px solid rgba(156, 163, 175, 0.5)",
  borderRadius: 8,
  padding: "4px 8px",
  fontSize: 12,
  fontWeight: 600,
  color: rank <= 3 ? "#fbbf24" : "#9ca3af",
  alignSelf: "flex-start",
  minWidth: 40,
  textAlign: "center",
});

const recommendationContentStyle: React.CSSProperties = {
  flex: 1,
  display: "flex",
  flexDirection: "column",
  gap: 8,
};

const symbolRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
};

const symbolStyle: React.CSSProperties = {
  fontSize: 18,
  fontWeight: 700,
  color: "#eee",
};

const confidenceStyle = (confidence: number): React.CSSProperties => ({
  fontSize: 12,
  fontWeight: 600,
  color: confidence >= 85 ? "#22c55e" : confidence >= 75 ? "#f59e0b" : "#ef4444",
  background: confidence >= 85 ? "rgba(34, 197, 94, 0.1)" : confidence >= 75 ? "rgba(245, 158, 11, 0.1)" : "rgba(239, 68, 68, 0.1)",
  border: confidence >= 85 ? "1px solid rgba(34, 197, 94, 0.3)" : confidence >= 75 ? "1px solid rgba(245, 158, 11, 0.3)" : "1px solid rgba(239, 68, 68, 0.3)",
  borderRadius: 6,
  padding: "2px 6px",
});

const metricsRowStyle: React.CSSProperties = {
  display: "flex",
  gap: 20,
};

const metricStyle: React.CSSProperties = {
  display: "flex",
  gap: 4,
};

const metricLabelStyle: React.CSSProperties = {
  fontSize: 12,
  color: "#999",
};

const metricValueStyle: React.CSSProperties = {
  fontSize: 12,
  fontWeight: 600,
  color: "#eee",
};

const priceRowStyle: React.CSSProperties = {
  display: "flex",
  gap: 16,
  alignItems: "center",
};

const priceStyle: React.CSSProperties = {
  display: "flex",
  gap: 4,
  alignItems: "center",
};

const priceLabelStyle: React.CSSProperties = {
  fontSize: 12,
  color: "#999",
};

const priceValueStyle: React.CSSProperties = {
  fontSize: 14,
  fontWeight: 600,
  color: "#eee",
};

const targetPriceStyle: React.CSSProperties = {
  fontSize: 14,
  fontWeight: 600,
  color: "#22c55e",
};

const returnStyle: React.CSSProperties = {
  marginLeft: "auto",
};

const returnValueStyle: React.CSSProperties = {
  fontSize: 14,
  fontWeight: 700,
  color: "#22c55e",
};

const timestampStyle: React.CSSProperties = {
  fontSize: 10,
  color: "#666",
  alignSelf: "flex-end",
};