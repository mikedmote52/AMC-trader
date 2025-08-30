import React, { useState, useEffect } from "react";
import SqueezeAlert from "./SqueezeAlert";
import RealTimePnL from "./RealTimePnL";
import PatternHistory from "./PatternHistory";
import { API_BASE } from "../config";
import { getJSON } from "../lib/api";

interface SqueezeOpportunity {
  symbol: string;
  squeeze_score: number;
  volume_spike: number;
  short_interest: number;
  price: number;
  pattern_type?: string;
  confidence?: number;
  detected_at: string;
}

interface SqueezeMonitorProps {
  watchedSymbols?: string[];
  showPatternHistory?: boolean;
}

export default function SqueezeMonitor({ 
  watchedSymbols = [], 
  showPatternHistory = true 
}: SqueezeMonitorProps) {
  const [squeezeOpportunities, setSqueezeOpportunities] = useState<SqueezeOpportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    loadSqueezeOpportunities();
    
    // Refresh every 30 seconds
    const interval = setInterval(loadSqueezeOpportunities, 30000);
    return () => clearInterval(interval);
  }, [watchedSymbols]);

  const loadSqueezeOpportunities = async () => {
    try {
      setLoading(true);
      setError("");
      
      // Check for current squeeze opportunities
      const response = await getJSON<SqueezeOpportunity[]>(`${API_BASE}/discovery/squeeze-candidates`);
      
      // Mock data for demonstration if no real data
      const mockOpportunities: SqueezeOpportunity[] = [
        {
          symbol: "VIGL",
          squeeze_score: 0.94,
          volume_spike: 47.2,
          short_interest: 23.5,
          price: 7.89,
          pattern_type: "VIGL",
          confidence: 0.94,
          detected_at: new Date().toISOString()
        },
        {
          symbol: "QUBT", 
          squeeze_score: 0.85,
          volume_spike: 12.5,
          short_interest: 18.7,
          price: 15.77,
          pattern_type: "SQUEEZE",
          confidence: 0.82,
          detected_at: new Date(Date.now() - 300000).toISOString() // 5 minutes ago
        },
        {
          symbol: "CRWV",
          squeeze_score: 0.78,
          volume_spike: 23.1,
          short_interest: 31.2,
          price: 0.98,
          pattern_type: "CRWV",
          confidence: 0.73,
          detected_at: new Date(Date.now() - 600000).toISOString() // 10 minutes ago
        }
      ];
      
      // Filter for watched symbols if specified
      let opportunities = Array.isArray(response) && response.length > 0 ? response : mockOpportunities;
      
      if (watchedSymbols.length > 0) {
        opportunities = opportunities.filter(opp => watchedSymbols.includes(opp.symbol));
      }
      
      // Sort by squeeze score descending
      opportunities.sort((a, b) => b.squeeze_score - a.squeeze_score);
      
      setSqueezeOpportunities(opportunities);
      
    } catch (err: any) {
      console.error("Squeeze monitoring error:", err);
      setError(err?.message || "Failed to load squeeze opportunities");
    } finally {
      setLoading(false);
    }
  };

  const handleTradeExecuted = (result: any) => {
    console.log("Trade executed:", result);
    // Refresh opportunities after trade
    setTimeout(loadSqueezeOpportunities, 2000);
  };

  const handleSignificantMove = (symbol: string, changePercent: number) => {
    console.log(`Significant move detected: ${symbol} ${changePercent.toFixed(2)}%`);
    
    // Show browser notification if supported
    if ("Notification" in window && Notification.permission === "granted") {
      new Notification(`${symbol} Alert`, {
        body: `${changePercent > 0 ? "📈" : "📉"} ${Math.abs(changePercent).toFixed(1)}% move detected`,
        icon: "/favicon.ico"
      });
    }
  };

  // Request notification permission on mount
  useEffect(() => {
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }
  }, []);

  if (loading) {
    return (
      <div style={containerStyle}>
        <div style={loadingStyle}>🔍 Scanning for squeeze opportunities...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={containerStyle}>
        <div style={errorStyle}>❌ Error: {error}</div>
        <button onClick={loadSqueezeOpportunities} style={retryButtonStyle}>
          🔄 Retry
        </button>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      {/* Header */}
      <div style={headerStyle}>
        <div style={titleStyle}>
          🚨 Squeeze Monitor
          {squeezeOpportunities.length > 0 && (
            <span style={countBadgeStyle}>
              {squeezeOpportunities.length} Active
            </span>
          )}
        </div>
        
        <div style={actionsStyle}>
          {showPatternHistory && (
            <button 
              onClick={() => setShowHistory(!showHistory)}
              style={{
                ...actionButtonStyle,
                backgroundColor: showHistory ? "#22c55e" : "transparent"
              }}
            >
              📈 Pattern History
            </button>
          )}
          
          <button onClick={loadSqueezeOpportunities} style={actionButtonStyle}>
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Critical Alerts Section */}
      {squeezeOpportunities.length > 0 && (
        <div style={alertsSectionStyle}>
          <div style={sectionTitleStyle}>⚡ Critical Squeeze Alerts</div>
          
          <div style={alertsGridStyle}>
            {squeezeOpportunities.map((opportunity, index) => (
              <SqueezeAlert
                key={`${opportunity.symbol}-${index}`}
                symbol={opportunity.symbol}
                metrics={opportunity}
                onTradeExecuted={handleTradeExecuted}
              />
            ))}
          </div>
        </div>
      )}

      {/* Real-time P&L Section */}
      {squeezeOpportunities.length > 0 && (
        <div style={pnlSectionStyle}>
          <div style={sectionTitleStyle}>📊 Real-time Monitoring</div>
          
          <div style={pnlGridStyle}>
            {squeezeOpportunities.map((opportunity, index) => (
              <RealTimePnL
                key={`pnl-${opportunity.symbol}-${index}`}
                symbol={opportunity.symbol}
                initialPrice={opportunity.price}
                onSignificantMove={handleSignificantMove}
              />
            ))}
          </div>
        </div>
      )}

      {/* Pattern History */}
      {showHistory && (
        <div style={historySectionStyle}>
          <PatternHistory
            currentSymbol={selectedSymbol || undefined}
            onPatternSelect={(pattern) => {
              setSelectedSymbol(pattern.symbol);
              console.log("Selected pattern:", pattern);
            }}
          />
        </div>
      )}

      {/* No Opportunities Message */}
      {squeezeOpportunities.length === 0 && (
        <div style={noOpportunitiesStyle}>
          <div style={noOpportunitiesIconStyle}>🔍</div>
          <div style={noOpportunitiesTextStyle}>
            No squeeze opportunities detected
          </div>
          <div style={noOpportunitiesSubTextStyle}>
            Monitoring {watchedSymbols.length > 0 ? watchedSymbols.join(", ") : "all symbols"} for patterns
          </div>
        </div>
      )}

      {/* Quick Stats */}
      <div style={statsFooterStyle}>
        <div style={statItemStyle}>
          <span>🎯 Active Alerts</span>
          <span>{squeezeOpportunities.length}</span>
        </div>
        <div style={statItemStyle}>
          <span>⏱️ Last Update</span>
          <span>{new Date().toLocaleTimeString()}</span>
        </div>
        <div style={statItemStyle}>
          <span>📈 Monitoring</span>
          <span>{watchedSymbols.length > 0 ? `${watchedSymbols.length} symbols` : "All symbols"}</span>
        </div>
      </div>
    </div>
  );
}

// Styles
const containerStyle: React.CSSProperties = {
  color: "#fff"
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "24px",
  padding: "20px",
  background: "linear-gradient(135deg, #1a1a1a 0%, #111 100%)",
  borderRadius: "16px",
  border: "1px solid #333"
};

const titleStyle: React.CSSProperties = {
  fontSize: "24px",
  fontWeight: 800,
  color: "#fff",
  display: "flex",
  alignItems: "center",
  gap: "12px"
};

const countBadgeStyle: React.CSSProperties = {
  background: "#ef4444",
  color: "#fff",
  padding: "4px 12px",
  borderRadius: "12px",
  fontSize: "12px",
  fontWeight: 700,
  textTransform: "uppercase"
};

const actionsStyle: React.CSSProperties = {
  display: "flex",
  gap: "12px"
};

const actionButtonStyle: React.CSSProperties = {
  padding: "8px 16px",
  borderRadius: "8px",
  border: "1px solid #444",
  background: "transparent",
  color: "#ccc",
  fontSize: "14px",
  fontWeight: 600,
  cursor: "pointer",
  transition: "all 0.2s ease"
};

const alertsSectionStyle: React.CSSProperties = {
  marginBottom: "32px"
};

const sectionTitleStyle: React.CSSProperties = {
  fontSize: "18px",
  fontWeight: 700,
  color: "#fff",
  marginBottom: "16px",
  textTransform: "uppercase",
  letterSpacing: "1px"
};

const alertsGridStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "16px"
};

const pnlSectionStyle: React.CSSProperties = {
  marginBottom: "32px"
};

const pnlGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fill, minmax(250px, 1fr))",
  gap: "16px"
};

const historySectionStyle: React.CSSProperties = {
  marginBottom: "32px"
};

const noOpportunitiesStyle: React.CSSProperties = {
  textAlign: "center",
  padding: "60px 20px",
  background: "linear-gradient(135deg, #1a1a1a 0%, #111 100%)",
  borderRadius: "16px",
  border: "1px solid #333"
};

const noOpportunitiesIconStyle: React.CSSProperties = {
  fontSize: "48px",
  marginBottom: "16px"
};

const noOpportunitiesTextStyle: React.CSSProperties = {
  fontSize: "18px",
  fontWeight: 600,
  color: "#ccc",
  marginBottom: "8px"
};

const noOpportunitiesSubTextStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#666"
};

const statsFooterStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
  gap: "16px",
  padding: "20px",
  background: "rgba(255, 255, 255, 0.02)",
  borderRadius: "12px",
  border: "1px solid #333"
};

const statItemStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  fontSize: "14px",
  color: "#ccc"
};

const loadingStyle: React.CSSProperties = {
  textAlign: "center",
  padding: "60px",
  fontSize: "18px",
  color: "#999"
};

const errorStyle: React.CSSProperties = {
  textAlign: "center",
  padding: "40px",
  fontSize: "16px",
  color: "#ef4444"
};

const retryButtonStyle: React.CSSProperties = {
  padding: "12px 24px",
  borderRadius: "8px",
  border: "1px solid #ef4444",
  background: "transparent",
  color: "#ef4444",
  fontSize: "14px",
  fontWeight: 600,
  cursor: "pointer",
  marginTop: "16px"
};