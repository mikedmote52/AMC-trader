import React from "react";
import { Link } from "react-router-dom";

export default function HomePage() {
  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h1 style={titleStyle}>AMC-TRADER</h1>
        <p style={subtitleStyle}>Professional Trading Intelligence System</p>
      </div>

      <div style={cardsContainerStyle}>
        <Link to="/squeeze" style={cardLinkStyle}>
          <div data-card style={{ ...cardStyle, ...squeezeCardStyle }}>
            <div style={cardIconStyle}>🔍</div>
            <h2 style={cardTitleStyle}>Squeeze Monitor</h2>
            <p style={cardDescriptionStyle}>
              Real-time ANTE alerts and squeeze pattern detection
            </p>
            <div style={cardFeatureStyle}>
              • Live price monitoring
            </div>
            <div style={cardFeatureStyle}>
              • Pattern history tracking
            </div>
            <div style={cardFeatureStyle}>
              • Auto-refresh alerts
            </div>
          </div>
        </Link>

        <Link to="/discovery" style={cardLinkStyle}>
          <div data-card style={{ ...cardStyle, ...discoveryCardStyle }}>
            <div style={cardIconStyle}>🎯</div>
            <h2 style={cardTitleStyle}>Discovery Engine</h2>
            <p style={cardDescriptionStyle}>
              Top stock recommendations with AI-powered analysis
            </p>
            <div style={cardFeatureStyle}>
              • VIGL pattern scoring
            </div>
            <div style={cardFeatureStyle}>
              • Real-time recommendations
            </div>
            <div style={cardFeatureStyle}>
              • Trade execution ready
            </div>
          </div>
        </Link>

        <Link to="/portfolio" style={cardLinkStyle}>
          <div data-card style={{ ...cardStyle, ...portfolioCardStyle }}>
            <div style={cardIconStyle}>📊</div>
            <h2 style={cardTitleStyle}>Portfolio Manager</h2>
            <p style={cardDescriptionStyle}>
              Holdings analysis with AI thesis and position management
            </p>
            <div style={cardFeatureStyle}>
              • Position analysis
            </div>
            <div style={cardFeatureStyle}>
              • AI-generated thesis
            </div>
            <div style={cardFeatureStyle}>
              • Sortable holdings view
            </div>
          </div>
        </Link>

        <Link to="/updates" style={cardLinkStyle}>
          <div data-card style={{ ...cardStyle, ...updatesCardStyle }}>
            <div style={cardIconStyle}>📱</div>
            <h2 style={cardTitleStyle}>Daily Updates</h2>
            <p style={cardDescriptionStyle}>
              Comprehensive market analysis and trading insights
            </p>
            <div style={cardFeatureStyle}>
              • Market overview
            </div>
            <div style={cardFeatureStyle}>
              • Trading performance
            </div>
            <div style={cardFeatureStyle}>
              • Strategic insights
            </div>
          </div>
        </Link>
      </div>

      <div style={statsStyle}>
        <div style={statItemStyle}>
          <div style={statValueStyle}>324%</div>
          <div style={statLabelStyle}>VIGL Pattern Winner</div>
        </div>
        <div style={statItemStyle}>
          <div style={statValueStyle}>Real-time</div>
          <div style={statLabelStyle}>Market Data</div>
        </div>
        <div style={statItemStyle}>
          <div style={statValueStyle}>AI-Powered</div>
          <div style={statLabelStyle}>Analysis Engine</div>
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
  padding: "40px 16px",
  maxWidth: "1400px",
  margin: "0 auto"
};

const headerStyle: React.CSSProperties = {
  textAlign: "center",
  marginBottom: "60px"
};

const titleStyle: React.CSSProperties = {
  fontSize: "48px",
  fontWeight: 900,
  color: "#fff",
  marginBottom: "16px",
  background: "linear-gradient(135deg, #22c55e, #16a34a)",
  backgroundClip: "text",
  WebkitBackgroundClip: "text",
  WebkitTextFillColor: "transparent"
};

const subtitleStyle: React.CSSProperties = {
  fontSize: "18px",
  color: "#ccc",
  fontWeight: 500
};

const cardsContainerStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
  gap: "24px",
  marginBottom: "60px"
};

const cardLinkStyle: React.CSSProperties = {
  textDecoration: "none"
};

const cardStyle: React.CSSProperties = {
  background: "#111",
  border: "1px solid #333",
  borderRadius: "16px",
  padding: "32px",
  transition: "all 0.3s ease",
  cursor: "pointer",
  minHeight: "280px"
};

const squeezeCardStyle: React.CSSProperties = {
  borderColor: "#3b82f6"
};

const discoveryCardStyle: React.CSSProperties = {
  borderColor: "#22c55e"
};

const portfolioCardStyle: React.CSSProperties = {
  borderColor: "#f59e0b"
};

const updatesCardStyle: React.CSSProperties = {
  borderColor: "#8b5cf6"
};

const cardIconStyle: React.CSSProperties = {
  fontSize: "48px",
  marginBottom: "16px"
};

const cardTitleStyle: React.CSSProperties = {
  fontSize: "24px",
  fontWeight: 700,
  color: "#fff",
  marginBottom: "12px"
};

const cardDescriptionStyle: React.CSSProperties = {
  fontSize: "16px",
  color: "#ccc",
  marginBottom: "24px",
  lineHeight: "1.5"
};

const cardFeatureStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#999",
  marginBottom: "8px"
};

const statsStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "center",
  gap: "60px",
  flexWrap: "wrap"
};

const statItemStyle: React.CSSProperties = {
  textAlign: "center"
};

const statValueStyle: React.CSSProperties = {
  fontSize: "32px",
  fontWeight: 900,
  color: "#22c55e",
  marginBottom: "8px"
};

const statLabelStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#999",
  fontWeight: 600
};

// Add hover effects
const hoverStyle = document.createElement('style');
hoverStyle.textContent = `
[data-card]:hover {
  transform: translateY(-4px);
  border-color: #555 !important;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}
`;
document.head.appendChild(hoverStyle);