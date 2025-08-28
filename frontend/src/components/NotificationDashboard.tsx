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
      
      // For now, use mock data. In production, these would be separate API calls
      // const [briefData, recommendationsData, pulseData, timelineData, notificationsData] = await Promise.all([
      //   getJSON(`${API_BASE}/notifications/daily-brief`),
      //   getJSON(`${API_BASE}/discovery/contenders`),
      //   getJSON(`${API_BASE}/notifications/market-pulse`),
      //   getJSON(`${API_BASE}/notifications/timeline`),
      //   getJSON(`${API_BASE}/notifications/history`)
      // ]);

      // Mock data for demonstration
      const mockData: DashboardData = {
        dailyBrief: {
          date: new Date().toLocaleDateString('en-US', { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
          }),
          topOpportunities: 3,
          portfolioChange: 412,
          portfolioChangePct: 3.2,
          riskLevel: "GREEN",
          marketSentiment: "Bullish"
        },
        recommendations: [
          {
            symbol: "VIGL",
            confidence: 87,
            pattern: "VIGL",
            volume: 2400000,
            volumeMultiplier: 12.3,
            entryPrice: 3.24,
            targetPrice: 4.50,
            potentialReturn: 38.9,
            timestamp: new Date().toISOString()
          },
          {
            symbol: "QUBT",
            confidence: 82,
            pattern: "Volume Breakout",
            volume: 1800000,
            volumeMultiplier: 8.7,
            entryPrice: 2.15,
            targetPrice: 2.85,
            potentialReturn: 32.6,
            timestamp: new Date().toISOString()
          },
          {
            symbol: "RGTI",
            confidence: 75,
            pattern: "Momentum",
            volume: 950000,
            volumeMultiplier: 5.2,
            entryPrice: 1.89,
            targetPrice: 2.35,
            potentialReturn: 24.3,
            timestamp: new Date().toISOString()
          }
        ],
        marketPulse: {
          preMarketMovers: 3,
          volumeLeaders: ["VIGL", "QUBT", "RGTI"],
          riskAlerts: [],
          nextScanTime: "2:15 PM EST",
          marketStatus: "MARKET_OPEN",
          lastUpdate: new Date().toISOString()
        },
        timeline: [
          {
            time: "08:00 AM",
            status: "COMPLETED",
            title: "Morning scan complete",
            description: "3 opportunities identified with high confidence scores",
            importance: "HIGH"
          },
          {
            time: "12:30 PM",
            status: "COMPLETED",
            title: "Mid-day update",
            description: "2 positions up, 1 down - portfolio +$284",
            importance: "MEDIUM"
          },
          {
            time: "16:00 PM",
            status: "IN_PROGRESS",
            title: "End-of-day analysis",
            description: "Analyzing final market moves and position performance",
            importance: "HIGH"
          },
          {
            time: "18:00 PM",
            status: "SCHEDULED",
            title: "Tomorrow's prep",
            description: "Generate watch list and strategy for next trading day",
            importance: "MEDIUM"
          }
        ],
        notifications: [
          {
            id: "1",
            time: "08:00 AM",
            type: "BRIEF",
            title: "Morning brief sent",
            message: "Daily trading brief delivered with 3 top opportunities",
            status: "SENT",
            channel: "BOTH",
            importance: "HIGH"
          },
          {
            id: "2",
            time: "02:00 PM",
            type: "ALERT",
            title: "VIGL alert: +8.2% move",
            message: "VIGL up 8.2% on volume spike - target approaching",
            status: "SENT",
            channel: "SMS",
            importance: "HIGH"
          },
          {
            id: "3",
            time: "06:00 PM",
            type: "SUMMARY",
            title: "Portfolio summary (+$284)",
            message: "Daily portfolio update: +$284 (+2.1%) across 11 positions",
            status: "SENT",
            channel: "DASHBOARD",
            importance: "MEDIUM"
          }
        ]
      };

      setData(mockData);
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