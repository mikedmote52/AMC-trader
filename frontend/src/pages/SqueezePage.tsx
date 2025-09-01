import React, { useState } from "react";
import SqueezeMonitor from "../components/SqueezeMonitor";

export default function SqueezePage() {
  const [isPaused, setIsPaused] = useState(false);

  return (
    <div style={containerStyle}>
      {/* Page Header */}
      <div style={headerStyle}>
        <div style={titleContainerStyle}>
          <h1 style={titleStyle}>🔍 Squeeze Monitor</h1>
          <p style={subtitleStyle}>Real-time ANTE alerts and pattern detection</p>
        </div>
        
        <div style={controlsStyle}>
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

      {/* Squeeze Monitor Component */}
      <div style={contentStyle}>
        {isPaused ? (
          <div style={pausedOverlayStyle}>
            <div style={pausedMessageStyle}>
              <div style={pausedIconStyle}>⏸️</div>
              <div>Monitoring Paused</div>
              <div style={pausedSubtextStyle}>Click Resume to continue real-time alerts</div>
            </div>
          </div>
        ) : (
          <SqueezeMonitor 
            watchedSymbols={[]}
            showPatternHistory={true}
          />
        )}
      </div>

      {/* Info Panel */}
      <div style={infoPanelStyle}>
        <div style={infoItemStyle}>
          <div style={infoLabelStyle}>Alert Type</div>
          <div style={infoValueStyle}>ANTE Squeeze Patterns</div>
        </div>
        <div style={infoItemStyle}>
          <div style={infoLabelStyle}>Refresh Rate</div>
          <div style={infoValueStyle}>Every 30 seconds</div>
        </div>
        <div style={infoItemStyle}>
          <div style={infoLabelStyle}>Pattern History</div>
          <div style={infoValueStyle}>Full tracking enabled</div>
        </div>
        <div style={infoItemStyle}>
          <div style={infoLabelStyle}>Auto-Execution</div>
          <div style={infoValueStyle}>Manual approval required</div>
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
  padding: "24px",
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
  gap: "24px"
};

const infoItemStyle: React.CSSProperties = {
  textAlign: "center"
};

const infoLabelStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#999",
  fontWeight: 600,
  textTransform: "uppercase",
  letterSpacing: "0.5px",
  marginBottom: "8px"
};

const infoValueStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#fff",
  fontWeight: 600
};