import React, { useState, useEffect } from "react";
import EnhancedHoldings from "../components/EnhancedHoldings";
import { API_BASE } from "../config";
import { getJSON } from "../lib/api";

export default function EnhancedPortfolioPage() {
  const [isPaused, setIsPaused] = useState(false);
  const [viewMode, setViewMode] = useState<"detailed" | "compact">("detailed");
  const [portfolioStats, setPortfolioStats] = useState({
    totalValue: 0,
    todayPL: 0,
    todayPLPercent: 0,
    activePositions: 0
  });

  useEffect(() => {
    const fetchPortfolioStats = async () => {
      try {
        const holdingsResponse = await getJSON(`${API_BASE}/portfolio/holdings`);
        const positions = holdingsResponse?.data?.positions || [];

        if (positions.length > 0) {
          const totalValue = positions.reduce((sum: number, pos: any) => sum + (pos.market_value || 0), 0);
          const totalUnrealizedPL = positions.reduce((sum: number, pos: any) => sum + (pos.unrealized_pl || 0), 0);
          const totalCostBasis = positions.reduce((sum: number, pos: any) => sum + (pos.cost_basis || 0), 0);
          const todayPLPercent = totalCostBasis > 0 ? (totalUnrealizedPL / totalCostBasis) * 100 : 0;

          setPortfolioStats({
            totalValue,
            todayPL: totalUnrealizedPL,
            todayPLPercent,
            activePositions: positions.length
          });
        }
      } catch (error) {
        console.error('Failed to fetch portfolio stats:', error);
      }
    };

    if (!isPaused) {
      fetchPortfolioStats();
      const interval = setInterval(fetchPortfolioStats, 30000);
      return () => clearInterval(interval);
    }
  }, [isPaused]);

  return (
    <div style={containerStyle}>
      {/* Enhanced Portfolio Header */}
      <div style={headerStyle}>
        <div style={titleContainerStyle}>
          <h1 style={titleStyle}>🚀 Enhanced Portfolio Manager</h1>
          <p style={subtitleStyle}>Advanced holdings analysis with learning intelligence and enhanced position management</p>
          <div style={experimentalBadgeStyle}>
            EXPERIMENTAL VERSION - Your current portfolio system remains unchanged
          </div>
        </div>

        <div style={controlsStyle}>
          <select
            value={viewMode}
            onChange={(e) => setViewMode(e.target.value as "detailed" | "compact")}
            style={selectStyle}
          >
            <option value="detailed">Detailed View</option>
            <option value="compact">Compact View</option>
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

      {/* Portfolio Stats */}
      <div style={statsContainerStyle}>
        <div style={statCardStyle}>
          <div style={statIconStyle}>💰</div>
          <div style={statValueStyle}>
            ${portfolioStats.totalValue.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}
          </div>
          <div style={statLabelStyle}>Total Portfolio Value</div>
        </div>
        <div style={statCardStyle}>
          <div style={statIconStyle}>📈</div>
          <div style={{
            ...statValueStyle,
            color: portfolioStats.todayPLPercent >= 0 ? "#22c55e" : "#ef4444"
          }}>
            {portfolioStats.todayPLPercent >= 0 ? "+" : ""}{portfolioStats.todayPLPercent.toFixed(2)}%
          </div>
          <div style={statLabelStyle}>Today's P&L</div>
        </div>
        <div style={statCardStyle}>
          <div style={statIconStyle}>🎯</div>
          <div style={statValueStyle}>{portfolioStats.activePositions}</div>
          <div style={statLabelStyle}>Active Positions</div>
        </div>
        <div style={statCardStyle}>
          <div style={statIconStyle}>🧠</div>
          <div style={statValueStyle}>Enhanced</div>
          <div style={statLabelStyle}>AI Analysis</div>
        </div>
      </div>

      {/* Holdings Component */}
      <div style={contentStyle}>
        {isPaused ? (
          <div style={pausedOverlayStyle}>
            <div style={pausedMessageStyle}>
              <div style={pausedIconStyle}>⏸️</div>
              <div>Portfolio Updates Paused</div>
              <div style={pausedSubtextStyle}>Click Resume to continue live position monitoring</div>
            </div>
          </div>
        ) : (
          <EnhancedHoldings />
        )}
      </div>

      {/* Portfolio Management Panel */}
      <div style={infoPanelStyle}>
        <h3 style={infoPanelTitleStyle}>🎯 Enhanced Portfolio Intelligence</h3>

        <div style={infoGridStyle}>
          <div style={infoSectionStyle}>
            <div style={infoSectionTitleStyle}>Enhanced Analysis</div>
            <div style={infoItemStyle}>
              <div style={infoLabelStyle}>Learning Integration</div>
              <div style={infoValueStyle}>AI learns from your trading patterns to improve recommendations</div>
            </div>
            <div style={infoItemStyle}>
              <div style={infoLabelStyle}>Unified Decisions</div>
              <div style={infoValueStyle}>Single, clear recommendation per position - no more conflicts</div>
            </div>
            <div style={infoItemStyle}>
              <div style={infoLabelStyle}>Thesis Evolution</div>
              <div style={infoValueStyle}>Dynamic thesis that evolves with market conditions</div>
            </div>
          </div>

          <div style={infoSectionStyle}>
            <div style={infoSectionTitleStyle}>Enhanced Features</div>
            <div style={infoItemStyle}>
              <div style={infoLabelStyle}>Pattern Recognition</div>
              <div style={infoValueStyle}>Identifies winning patterns from historical trades</div>
            </div>
            <div style={infoItemStyle}>
              <div style={infoLabelStyle}>Confidence Scoring</div>
              <div style={infoValueStyle}>Shows confidence levels based on historical accuracy</div>
            </div>
            <div style={infoItemStyle}>
              <div style={infoLabelStyle}>Performance Tracking</div>
              <div style={infoValueStyle}>Tracks outcomes to improve future recommendations</div>
            </div>
          </div>

          <div style={infoSectionStyle}>
            <div style={infoSectionTitleStyle}>Safety Features</div>
            <div style={infoItemStyle}>
              <div style={infoLabelStyle}>Fallback Protection</div>
              <div style={infoValueStyle}>Automatically falls back to proven methods if needed</div>
            </div>
            <div style={infoItemStyle}>
              <div style={infoLabelStyle}>Data Integrity</div>
              <div style={infoValueStyle}>All enhancements are additive - no data corruption risk</div>
            </div>
            <div style={infoItemStyle}>
              <div style={infoLabelStyle}>Current System Preserved</div>
              <div style={infoValueStyle}>Your working portfolio system remains completely unchanged</div>
            </div>
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
  fontWeight: 500,
  marginBottom: "8px"
};

const experimentalBadgeStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#f59e0b",
  fontWeight: 600,
  textTransform: "uppercase",
  letterSpacing: "0.5px",
  background: "rgba(245, 158, 11, 0.1)",
  border: "1px solid rgba(245, 158, 11, 0.3)",
  borderRadius: "6px",
  padding: "4px 8px",
  display: "inline-block"
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
  gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
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

const statIconStyle: React.CSSProperties = {
  fontSize: "24px",
  marginBottom: "8px",
  display: "block"
};

const statValueStyle: React.CSSProperties = {
  fontSize: "24px",
  fontWeight: 900,
  color: "#f59e0b",
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
  gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
  gap: "32px"
};

const infoSectionStyle: React.CSSProperties = {
  borderLeft: "3px solid #f59e0b",
  paddingLeft: "16px"
};

const infoSectionTitleStyle: React.CSSProperties = {
  fontSize: "16px",
  color: "#f59e0b",
  fontWeight: 700,
  marginBottom: "16px"
};

const infoItemStyle: React.CSSProperties = {
  marginBottom: "12px"
};

const infoLabelStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#ccc",
  fontWeight: 600,
  marginBottom: "4px"
};

const infoValueStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#999",
  lineHeight: "1.4"
};