import React from "react";

type MarketPulseData = {
  preMarketMovers: number;
  volumeLeaders: string[];
  riskAlerts: string[];
  nextScanTime: string;
  marketStatus: "PRE_MARKET" | "MARKET_OPEN" | "AFTER_HOURS" | "CLOSED";
  lastUpdate: string;
};

type MarketPulseSectionProps = {
  data: MarketPulseData;
  isLoading?: boolean;
};

export default function MarketPulseSection({ data, isLoading }: MarketPulseSectionProps) {
  if (isLoading) {
    return (
      <div style={containerStyle}>
        <div style={headerStyle}>
          <span style={titleStyle}>📊 MARKET PULSE</span>
          <div style={loadingBadgeStyle}>Loading...</div>
        </div>
        <div style={loadingContentStyle}>
          Fetching live market data...
        </div>
      </div>
    );
  }

  const getMarketStatusInfo = () => {
    switch (data.marketStatus) {
      case "PRE_MARKET":
        return { label: "Pre-Market", color: "#f59e0b" };
      case "MARKET_OPEN":
        return { label: "Market Open", color: "#22c55e" };
      case "AFTER_HOURS":
        return { label: "After Hours", color: "#3b82f6" };
      case "CLOSED":
        return { label: "Market Closed", color: "#ef4444" };
      default:
        return { label: "Unknown", color: "#999" };
    }
  };

  const marketStatusInfo = getMarketStatusInfo();

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <span style={titleStyle}>📊 MARKET PULSE</span>
        <div style={statusBadgeStyle(marketStatusInfo.color)}>
          {marketStatusInfo.label}
        </div>
      </div>

      <div style={contentGridStyle}>
        <div style={pulseItemStyle}>
          <div style={pulseIconStyle}>🎯</div>
          <div style={pulseContentStyle}>
            <div style={pulseLabelStyle}>Pre-market movers</div>
            <div style={pulseValueStyle}>
              {data.preMarketMovers > 0 ? `+${data.preMarketMovers} new candidates` : "No new movers"}
            </div>
          </div>
        </div>

        <div style={pulseItemStyle}>
          <div style={pulseIconStyle}>📈</div>
          <div style={pulseContentStyle}>
            <div style={pulseLabelStyle}>Volume leaders</div>
            <div style={pulseValueStyle}>
              {data.volumeLeaders.length > 0 ? data.volumeLeaders.join(", ") : "No volume leaders"}
            </div>
          </div>
        </div>

        <div style={pulseItemStyle}>
          <div style={pulseIconStyle}>⚠️</div>
          <div style={pulseContentStyle}>
            <div style={pulseLabelStyle}>Risk alerts</div>
            <div style={{
              ...pulseValueStyle,
              color: data.riskAlerts.length > 0 ? "#ef4444" : "#22c55e"
            }}>
              {data.riskAlerts.length > 0 ? data.riskAlerts.join(", ") : "None ✅"}
            </div>
          </div>
        </div>

        <div style={pulseItemStyle}>
          <div style={pulseIconStyle}>⏰</div>
          <div style={pulseContentStyle}>
            <div style={pulseLabelStyle}>Next scan</div>
            <div style={pulseValueStyle}>{data.nextScanTime}</div>
          </div>
        </div>
      </div>

      <div style={footerStyle}>
        <div style={lastUpdateStyle}>
          Last updated: {new Date(data.lastUpdate).toLocaleTimeString()}
        </div>
        <div style={liveIndicatorStyle}>
          <div style={liveIconStyle}></div>
          Live Updates
        </div>
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

const statusBadgeStyle = (color: string): React.CSSProperties => ({
  background: `${color}20`,
  border: `1px solid ${color}50`,
  borderRadius: 8,
  padding: "4px 8px",
  fontSize: 11,
  fontWeight: 600,
  color: color,
});

const loadingContentStyle: React.CSSProperties = {
  textAlign: "center",
  color: "#999",
  fontSize: 14,
  padding: 20,
};

const contentGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(2, 1fr)",
  gap: 16,
  marginBottom: 16,
};

const pulseItemStyle: React.CSSProperties = {
  display: "flex",
  gap: 12,
  padding: 12,
  background: "#111",
  border: "1px solid #333",
  borderRadius: 8,
};

const pulseIconStyle: React.CSSProperties = {
  fontSize: 20,
  alignSelf: "flex-start",
};

const pulseContentStyle: React.CSSProperties = {
  flex: 1,
};

const pulseLabelStyle: React.CSSProperties = {
  fontSize: 12,
  color: "#999",
  marginBottom: 4,
  textTransform: "capitalize",
};

const pulseValueStyle: React.CSSProperties = {
  fontSize: 14,
  fontWeight: 600,
  color: "#eee",
  lineHeight: 1.3,
};

const footerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  paddingTop: 12,
  borderTop: "1px solid #333",
};

const lastUpdateStyle: React.CSSProperties = {
  fontSize: 11,
  color: "#666",
};

const liveIndicatorStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 6,
  fontSize: 11,
  color: "#22c55e",
  fontWeight: 600,
};

const liveIconStyle: React.CSSProperties = {
  width: 8,
  height: 8,
  background: "#22c55e",
  borderRadius: "50%",
  animation: "pulse 2s infinite",
};