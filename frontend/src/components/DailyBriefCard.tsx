import React from "react";

type DailyBriefData = {
  date: string;
  topOpportunities: number;
  portfolioChange: number;
  portfolioChangePct: number;
  riskLevel: "GREEN" | "YELLOW" | "RED";
  marketSentiment: string;
};

type DailyBriefCardProps = {
  data: DailyBriefData;
  isLoading?: boolean;
};

export default function DailyBriefCard({ data, isLoading }: DailyBriefCardProps) {
  if (isLoading) {
    return (
      <div style={containerStyle}>
        <div style={loadingStyle}>Loading daily brief...</div>
      </div>
    );
  }

  const riskColor = {
    GREEN: "#22c55e",
    YELLOW: "#f59e0b", 
    RED: "#ef4444"
  }[data.riskLevel];

  const changeColor = data.portfolioChange >= 0 ? "#22c55e" : "#ef4444";

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <div>
          <div style={titleStyle}>📈 Today's Trading Brief</div>
          <div style={dateStyle}>{data.date}</div>
        </div>
        <div style={riskBadgeStyle(riskColor)}>
          Risk: {data.riskLevel} {data.riskLevel === "GREEN" ? "✅" : data.riskLevel === "YELLOW" ? "⚠️" : "🚨"}
        </div>
      </div>

      <div style={metricsRowStyle}>
        <div style={metricStyle}>
          <div style={metricLabelStyle}>🎯 Top Opportunities</div>
          <div style={metricValueStyle}>{data.topOpportunities}</div>
        </div>
        
        <div style={metricStyle}>
          <div style={metricLabelStyle}>📊 Portfolio Today</div>
          <div style={{...metricValueStyle, color: changeColor}}>
            {data.portfolioChange >= 0 ? "+" : ""}${data.portfolioChange.toFixed(0)} ({data.portfolioChangePct >= 0 ? "+" : ""}{data.portfolioChangePct.toFixed(1)}%)
          </div>
        </div>

        <div style={metricStyle}>
          <div style={metricLabelStyle}>🌊 Market Pulse</div>
          <div style={metricValueStyle}>{data.marketSentiment}</div>
        </div>
      </div>
    </div>
  );
}

const containerStyle: React.CSSProperties = {
  background: "linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(16, 185, 129, 0.1))",
  border: "1px solid rgba(59, 130, 246, 0.3)",
  borderRadius: 16,
  padding: 20,
  marginBottom: 24,
};

const loadingStyle: React.CSSProperties = {
  textAlign: "center",
  color: "#999",
  fontSize: 14,
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  marginBottom: 20,
};

const titleStyle: React.CSSProperties = {
  fontSize: 18,
  fontWeight: 700,
  color: "#eee",
  marginBottom: 4,
};

const dateStyle: React.CSSProperties = {
  fontSize: 14,
  color: "#999",
  fontWeight: 500,
};

const riskBadgeStyle = (color: string): React.CSSProperties => ({
  background: `${color}20`,
  border: `1px solid ${color}50`,
  borderRadius: 8,
  padding: "6px 12px",
  fontSize: 12,
  fontWeight: 600,
  color: color,
});

const metricsRowStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(3, 1fr)",
  gap: 20,
};

const metricStyle: React.CSSProperties = {
  textAlign: "center",
};

const metricLabelStyle: React.CSSProperties = {
  fontSize: 12,
  color: "#999",
  marginBottom: 4,
  fontWeight: 500,
};

const metricValueStyle: React.CSSProperties = {
  fontSize: 16,
  fontWeight: 700,
  color: "#eee",
};