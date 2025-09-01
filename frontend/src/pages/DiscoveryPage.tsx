import React, { useState } from "react";
import TopRecommendations from "../components/TopRecommendations";

export default function DiscoveryPage() {
  const [isPaused, setIsPaused] = useState(false);
  const [refreshRate, setRefreshRate] = useState(30);

  return (
    <div style={containerStyle}>
      {/* Page Header */}
      <div style={headerStyle}>
        <div style={titleContainerStyle}>
          <h1 style={titleStyle}>🎯 Discovery Engine</h1>
          <p style={subtitleStyle}>AI-powered stock recommendations with VIGL pattern analysis</p>
        </div>
        
        <div style={controlsStyle}>
          <select 
            value={refreshRate}
            onChange={(e) => setRefreshRate(Number(e.target.value))}
            style={selectStyle}
          >
            <option value={15}>15s refresh</option>
            <option value={30}>30s refresh</option>
            <option value={60}>60s refresh</option>
            <option value={300}>5m refresh</option>
          </select>
          
          <button 
            onClick={() => setIsPaused(!isPaused)}
            style={{
              ...controlButtonStyle,
              ...(isPaused ? pausedButtonStyle : activeButtonStyle)
            }}
          >
            {isPaused ? "▶️ Resume" : "⏸️ Pause"}
          </button>
        </div>
      </div>

      {/* Discovery Stats */}
      <div style={statsContainerStyle}>
        <div style={statCardStyle}>
          <div style={statValueStyle}>324%</div>
          <div style={statLabelStyle}>VIGL Pattern Winner</div>
        </div>
        <div style={statCardStyle}>
          <div style={statValueStyle}>Real-time</div>
          <div style={statLabelStyle}>Market Scanning</div>
        </div>
        <div style={statCardStyle}>
          <div style={statValueStyle}>AI-Powered</div>
          <div style={statLabelStyle}>Recommendation Engine</div>
        </div>
        <div style={statCardStyle}>
          <div style={statValueStyle}>Live</div>
          <div style={statLabelStyle}>Trade Execution</div>
        </div>
      </div>

      {/* Top Recommendations Component */}
      <div style={contentStyle}>
        {isPaused ? (
          <div style={pausedOverlayStyle}>
            <div style={pausedMessageStyle}>
              <div style={pausedIconStyle}>⏸️</div>
              <div>Discovery Engine Paused</div>
              <div style={pausedSubtextStyle}>Click Resume to continue scanning for opportunities</div>
            </div>
          </div>
        ) : (
          <TopRecommendations />
        )}
      </div>

      {/* Discovery Info Panel */}
      <div style={infoPanelStyle}>
        <h3 style={infoPanelTitleStyle}>🧠 Discovery Intelligence</h3>
        
        <div style={infoGridStyle}>
          <div style={infoItemStyle}>
            <div style={infoLabelStyle}>Pattern Detection</div>
            <div style={infoValueStyle}>VIGL squeeze patterns with 85%+ similarity</div>
          </div>
          <div style={infoItemStyle}>
            <div style={infoLabelStyle}>Volume Analysis</div>
            <div style={infoValueStyle}>20.9x average volume spike threshold</div>
          </div>
          <div style={infoItemStyle}>
            <div style={infoLabelStyle}>Price Range</div>
            <div style={infoValueStyle}>$2.94-$4.66 optimal entry zone</div>
          </div>
          <div style={infoItemStyle}>
            <div style={infoLabelStyle}>Risk Management</div>
            <div style={infoValueStyle}>WOLF pattern detection for downside protection</div>
          </div>
          <div style={infoItemStyle}>
            <div style={infoLabelStyle}>Momentum Threshold</div>
            <div style={infoValueStyle}>0.7 minimum momentum requirement</div>
          </div>
          <div style={infoItemStyle}>
            <div style={infoLabelStyle}>Execution Mode</div>
            <div style={infoValueStyle}>Live trading with manual approval</div>
          </div>
        </div>
      </div>
    </div>
  );
}

const containerStyle: React.CSSProperties = {
  fontFamily: "ui-sans-serif, system-ui",
  color: "#e7e7e7",
  background: "#000",
  minHeight: "calc(100vh - 60px)",
  padding: "20px 16px",
  maxWidth: "1400px",
  margin: "0 auto"
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  marginBottom: "32px",
  flexWrap: "wrap",
  gap: "16px"
};

const titleContainerStyle: React.CSSProperties = {
  flex: 1
};

const titleStyle: React.CSSProperties = {
  fontSize: "32px",
  fontWeight: 700,
  color: "#fff",
  marginBottom: "8px"
};

const subtitleStyle: React.CSSProperties = {
  fontSize: "16px",
  color: "#ccc",
  fontWeight: 500
};

const controlsStyle: React.CSSProperties = {
  display: "flex",
  gap: "12px",
  alignItems: "center"
};

const selectStyle: React.CSSProperties = {
  background: "#222",
  border: "1px solid #333",
  borderRadius: "8px",
  padding: "8px 12px",
  color: "#ccc",
  fontSize: "14px",
  fontWeight: 600
};

const controlButtonStyle: React.CSSProperties = {
  padding: "8px 16px",
  borderRadius: "8px",
  fontSize: "14px",
  fontWeight: 600,
  cursor: "pointer",
  border: "none",
  transition: "all 0.2s ease"
};

const activeButtonStyle: React.CSSProperties = {
  background: "linear-gradient(135deg, #22c55e, #16a34a)",
  color: "#000"
};

const pausedButtonStyle: React.CSSProperties = {
  background: "linear-gradient(135deg, #f59e0b, #d97706)",
  color: "#000"
};

const statsContainerStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
  gap: "16px",
  marginBottom: "32px"
};

const statCardStyle: React.CSSProperties = {
  background: "#111",
  border: "1px solid #333",
  borderRadius: "12px",
  padding: "20px",
  textAlign: "center"
};

const statValueStyle: React.CSSProperties = {
  fontSize: "24px",
  fontWeight: 900,
  color: "#22c55e",
  marginBottom: "8px"
};

const statLabelStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#999",
  fontWeight: 600,
  textTransform: "uppercase"
};

const contentStyle: React.CSSProperties = {
  marginBottom: "40px",
  position: "relative"
};

const pausedOverlayStyle: React.CSSProperties = {
  position: "absolute",
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  background: "rgba(0, 0, 0, 0.8)",
  backdropFilter: "blur(4px)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  minHeight: "400px",
  borderRadius: "12px",
  border: "1px solid #333",
  zIndex: 10
};

const pausedMessageStyle: React.CSSProperties = {
  textAlign: "center",
  color: "#ccc"
};

const pausedIconStyle: React.CSSProperties = {
  fontSize: "48px",
  marginBottom: "16px"
};

const pausedSubtextStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#999",
  marginTop: "8px"
};

const infoPanelStyle: React.CSSProperties = {
  background: "#111",
  border: "1px solid #333",
  borderRadius: "12px",
  padding: "24px"
};

const infoPanelTitleStyle: React.CSSProperties = {
  fontSize: "20px",
  fontWeight: 700,
  color: "#fff",
  marginBottom: "24px",
  textAlign: "center"
};

const infoGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
  gap: "20px"
};

const infoItemStyle: React.CSSProperties = {
  borderLeft: "3px solid #22c55e",
  paddingLeft: "16px"
};

const infoLabelStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#22c55e",
  fontWeight: 600,
  textTransform: "uppercase",
  letterSpacing: "0.5px",
  marginBottom: "8px"
};

const infoValueStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#ccc",
  lineHeight: "1.5"
};