import React, { useState } from "react";
import TopRecommendations from "./components/TopRecommendations";
import PortfolioTiles from "./components/PortfolioTiles";
import UpdatesPage from "./components/UpdatesPage";

export default function App() {
  const [currentPage, setCurrentPage] = useState<"trading" | "updates">("trading");

  if (currentPage === "updates") {
    return (
      <div>
        <div style={navStyle}>
          <button onClick={() => setCurrentPage("trading")} style={navButtonStyle}>
            ← Back to Trading
          </button>
        </div>
        <UpdatesPage />
      </div>
    );
  }

  return (
    <div style={{
      fontFamily: "ui-sans-serif, system-ui", 
      color: "#e7e7e7", 
      background: "#000",
      minHeight: "100vh",
      padding: "20px"
    }}>
      {/* Navigation */}
      <div style={navStyle}>
        <button onClick={() => setCurrentPage("updates")} style={updatesNavStyle}>
          📱 Daily Updates
        </button>
      </div>

      {/* Discovery Section */}
      <div style={{ marginBottom: "40px" }}>
        <h1 style={{ 
          fontSize: "24px", 
          fontWeight: 700, 
          marginBottom: "20px",
          color: "#fff"
        }}>
          🎯 Top Stock Recommendations
        </h1>
        <TopRecommendations />
      </div>

      {/* Portfolio Section */}
      <div>
        <h1 style={{ 
          fontSize: "24px", 
          fontWeight: 700, 
          marginBottom: "20px",
          color: "#fff"
        }}>
          📊 Current Holdings
        </h1>
        <PortfolioTiles />
      </div>
    </div>
  );
}

const navStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "flex-end",
  marginBottom: "20px",
  padding: "0 20px"
};

const navButtonStyle: React.CSSProperties = {
  background: "transparent",
  border: "1px solid #333",
  borderRadius: "8px",
  padding: "8px 16px",
  color: "#ccc",
  fontSize: "14px",
  fontWeight: 600,
  cursor: "pointer"
};

const updatesNavStyle: React.CSSProperties = {
  background: "linear-gradient(135deg, #22c55e, #16a34a)",
  border: "none",
  borderRadius: "8px",
  padding: "8px 16px",
  color: "#000",
  fontSize: "14px",
  fontWeight: 600,
  cursor: "pointer",
  boxShadow: "0 2px 8px rgba(34, 197, 94, 0.2)"
};