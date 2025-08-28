import React, { useEffect, useState } from "react";
import { API_BASE } from "../config";
import { getJSON } from "../lib/api";
import DailyBriefCard from "./DailyBriefCard";
import LiveRecommendationsPanel from "./LiveRecommendationsPanel";
import MarketPulseSection from "./MarketPulseSection";
import DailyTimelineView from "./DailyTimelineView";
import NotificationHistory from "./NotificationHistory";

// Mock data types - these would come from API endpoints
type DashboardData = {
  dailyBrief: {
    date: string;
    topOpportunities: number;
    portfolioChange: number;
    portfolioChangePct: number;
    riskLevel: "GREEN" | "YELLOW" | "RED";
    marketSentiment: string;
  };
  recommendations: Array<{
    symbol: string;
    confidence: number;
    pattern: string;
    volume: number;
    volumeMultiplier: number;
    entryPrice: number;
    targetPrice: number;
    potentialReturn: number;
    timestamp: string;
  }>;
  marketPulse: {
    preMarketMovers: number;
    volumeLeaders: string[];
    riskAlerts: string[];
    nextScanTime: string;
    marketStatus: "PRE_MARKET" | "MARKET_OPEN" | "AFTER_HOURS" | "CLOSED";
    lastUpdate: string;
  };
  timeline: Array<{
    time: string;
    status: "COMPLETED" | "IN_PROGRESS" | "PENDING" | "SCHEDULED";
    title: string;
    description: string;
    importance: "HIGH" | "MEDIUM" | "LOW";
  }>;
  notifications: Array<{
    id: string;
    time: string;
    type: "BRIEF" | "ALERT" | "SUMMARY" | "WARNING" | "INFO";
    title: string;
    message: string;
    status: "SENT" | "FAILED" | "PENDING";
    channel: "SMS" | "DASHBOARD" | "BOTH";
    importance: "HIGH" | "MEDIUM" | "LOW";
  }>;
};

export default function NotificationDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>("");

  const fetchDashboardData = async () => {
    try {
      setError("");
      
      // Fetch real data from actual API endpoints
      const [portfolioData, recommendationsData] = await Promise.all([
        getJSON(`${API_BASE}/portfolio/holdings`).catch(() => ({ data: { summary: {} } })),
        getJSON(`${API_BASE}/discovery/contenders`).catch(() => [])
      ]);

      // Use real portfolio data for daily brief
      const portfolioSummary = portfolioData?.data?.summary || {};
      const realData: DashboardData = {
        dailyBrief: {
          date: new Date().toLocaleDateString('en-US', { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
          }),
          topOpportunities: Array.isArray(recommendationsData) ? recommendationsData.length : 0,
          portfolioChange: portfolioSummary.total_unrealized_pl || 0,
          portfolioChangePct: portfolioSummary.total_unrealized_pl_pct || 0,
          riskLevel: portfolioSummary.total_unrealized_pl >= 0 ? "GREEN" : "RED",
          marketSentiment: portfolioSummary.total_unrealized_pl >= 0 ? "Bullish" : "Bearish"
        },
        recommendations: Array.isArray(recommendationsData) ? recommendationsData.map((rec: any) => ({
          symbol: rec.symbol || "N/A",
          confidence: Math.round((rec.score || rec.confidence || 0) * 100),
          pattern: rec.pattern || "Analysis",
          volume: rec.volume || 0,
          volumeMultiplier: rec.rel_vol_30m || 1,
          entryPrice: rec.price || 0,
          targetPrice: rec.target_price || rec.price || 0,
          potentialReturn: ((rec.target_price || rec.price || 0) - (rec.price || 0)) / (rec.price || 1) * 100,
          timestamp: new Date().toISOString()
        })) : [],
        marketPulse: {
          preMarketMovers: Array.isArray(recommendationsData) ? recommendationsData.length : 0,
          volumeLeaders: Array.isArray(recommendationsData) ? recommendationsData.slice(0, 3).map((rec: any) => rec.symbol || "N/A") : [],
          riskAlerts: portfolioSummary.total_unrealized_pl < -1000 ? ["High portfolio drawdown detected"] : [],
          nextScanTime: "Next scan scheduled",
          marketStatus: "MARKET_OPEN",
          lastUpdate: new Date().toISOString()
        },
        timeline: [
          {
            time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
            status: "COMPLETED" as const,
            title: "Data Updated",
            description: `Portfolio: ${portfolioSummary.total_positions || 0} positions, ${Array.isArray(recommendationsData) ? recommendationsData.length : 0} recommendations`,
            importance: "MEDIUM" as const
          }
        ],
        notifications: []
      };

      setData(realData);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return (
      <div style={errorContainerStyle}>
        <div style={errorStyle}>
          Error loading dashboard: {error}
        </div>
        <button onClick={fetchDashboardData} style={retryButtonStyle}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h1 style={titleStyle}>🖥️ Trading Intelligence Dashboard</h1>
        <div style={refreshInfoStyle}>
          Auto-refresh: 30s • Last updated: {new Date().toLocaleTimeString()}
        </div>
      </div>

      <div className="dashboard-grid" style={{...dashboardGridStyle, gridTemplateColumns: window.innerWidth >= 1024 ? "1fr 1fr" : "1fr"}}>
        {/* Daily Brief - Full Width */}
        <div style={fullWidthSectionStyle}>
          <DailyBriefCard 
            data={data?.dailyBrief || {} as any}
            isLoading={isLoading}
          />
        </div>

        {/* Two Column Layout */}
        <div style={leftColumnStyle}>
          <LiveRecommendationsPanel 
            recommendations={data?.recommendations || []}
            isLoading={isLoading}
          />
          
          <DailyTimelineView 
            events={data?.timeline || []}
            isLoading={isLoading}
          />
        </div>

        <div style={rightColumnStyle}>
          <MarketPulseSection 
            data={data?.marketPulse || {} as any}
            isLoading={isLoading}
          />
          
          <NotificationHistory 
            notifications={data?.notifications || []}
            isLoading={isLoading}
          />
        </div>
      </div>
    </div>
  );
}

const containerStyle: React.CSSProperties = {
  maxWidth: 1400,
  margin: "0 auto",
  padding: 24,
};

const errorContainerStyle: React.CSSProperties = {
  textAlign: "center",
  padding: 40,
};

const errorStyle: React.CSSProperties = {
  color: "#ef4444",
  fontSize: 16,
  marginBottom: 20,
};

const retryButtonStyle: React.CSSProperties = {
  background: "#3b82f6",
  color: "white",
  border: "none",
  borderRadius: 8,
  padding: "12px 24px",
  fontSize: 14,
  fontWeight: 600,
  cursor: "pointer",
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: 32,
  borderBottom: "1px solid #333",
  paddingBottom: 16,
};

const titleStyle: React.CSSProperties = {
  fontSize: 32,
  fontWeight: 700,
  color: "#eee",
  margin: 0,
};

const refreshInfoStyle: React.CSSProperties = {
  fontSize: 14,
  color: "#999",
  fontWeight: 500,
};

const dashboardGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr",
  gap: 24,
};

const fullWidthSectionStyle: React.CSSProperties = {
  gridColumn: "1 / -1",
};

const leftColumnStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 24,
};

const rightColumnStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 24,
};

// Responsive layout
const responsiveStyles = `
@media (min-width: 1024px) {
  .dashboard-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
  }
  
  .full-width-section {
    grid-column: 1 / -1;
  }
}
`;