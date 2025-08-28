import React from "react";
import TopRecommendations from "./components/TopRecommendations";
import PortfolioTiles from "./components/PortfolioTiles";

export default function App() {
  return (
    <div style={{
      fontFamily: "ui-sans-serif, system-ui", 
      color: "#e7e7e7", 
      background: "#000",
      minHeight: "100vh",
      padding: "20px"
    }}>
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