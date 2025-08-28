import React, { useState, useEffect } from "react";

type MarketSession = "pre-market" | "market-open" | "after-hours" | "closed";

type MarketStatusProps = {
  className?: string;
};

export default function MarketStatus({ className }: MarketStatusProps) {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [session, setSession] = useState<MarketSession>("closed");

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(now);
      setSession(determineMarketSession(now));
    };

    updateTime();
    const interval = setInterval(updateTime, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  function determineMarketSession(date: Date): MarketSession {
    // Convert to ET (assuming user timezone, would need proper timezone handling for production)
    const et = new Date(date.toLocaleString("en-US", {timeZone: "America/New_York"}));
    const hour = et.getHours();
    const minute = et.getMinutes();
    const day = et.getDay(); // 0 = Sunday, 6 = Saturday
    
    // Weekend
    if (day === 0 || day === 6) return "closed";
    
    const currentMinutes = hour * 60 + minute;
    const preMarketStart = 4 * 60; // 4:00 AM
    const marketOpen = 9 * 60 + 30; // 9:30 AM
    const marketClose = 16 * 60; // 4:00 PM
    const afterHoursEnd = 20 * 60; // 8:00 PM
    
    if (currentMinutes >= preMarketStart && currentMinutes < marketOpen) {
      return "pre-market";
    } else if (currentMinutes >= marketOpen && currentMinutes < marketClose) {
      return "market-open";
    } else if (currentMinutes >= marketClose && currentMinutes < afterHoursEnd) {
      return "after-hours";
    } else {
      return "closed";
    }
  }

  const getSessionInfo = () => {
    switch (session) {
      case "pre-market":
        return {
          label: "Pre-Market",
          color: "#eab308",
          bg: "rgba(234, 179, 8, 0.1)",
          icon: "🌅",
          description: "Extended trading active"
        };
      case "market-open":
        return {
          label: "Market Open",
          color: "#22c55e",
          bg: "rgba(34, 197, 94, 0.1)",
          icon: "🟢",
          description: "Regular trading hours"
        };
      case "after-hours":
        return {
          label: "After Hours",
          color: "#f97316",
          bg: "rgba(249, 115, 22, 0.1)",
          icon: "🌆",
          description: "Extended trading active"
        };
      case "closed":
        return {
          label: "Market Closed",
          color: "#6b7280",
          bg: "rgba(107, 114, 128, 0.1)",
          icon: "🔴",
          description: "Trading suspended"
        };
    }
  };

  const sessionInfo = getSessionInfo();
  const timeString = currentTime.toLocaleTimeString("en-US", {
    hour12: true,
    hour: "numeric",
    minute: "2-digit",
    timeZone: "America/New_York"
  });

  return (
    <div className={className} style={{
      ...containerStyle,
      background: sessionInfo.bg,
      borderColor: `${sessionInfo.color}30`
    }}>
      <div style={contentStyle}>
        <div style={mainInfoStyle}>
          <div style={sessionHeaderStyle}>
            <span style={{fontSize: 16}}>{sessionInfo.icon}</span>
            <span style={{
              color: sessionInfo.color,
              fontWeight: 700,
              fontSize: 14
            }}>
              {sessionInfo.label}
            </span>
          </div>
          <div style={{
            fontSize: 12,
            color: "#999",
            marginTop: 2
          }}>
            {sessionInfo.description}
          </div>
        </div>
        
        <div style={timeStyle}>
          <div style={{
            fontSize: 18,
            fontWeight: 700,
            color: "#eee"
          }}>
            {timeString}
          </div>
          <div style={{
            fontSize: 10,
            color: "#666",
            textAlign: "center",
            marginTop: 1
          }}>
            ET
          </div>
        </div>
      </div>
      
      {/* Next session indicator */}
      {session !== "market-open" && (
        <div style={nextSessionStyle}>
          {getNextSessionInfo()}
        </div>
      )}
    </div>
  );

  function getNextSessionInfo(): string {
    const now = new Date();
    const et = new Date(now.toLocaleString("en-US", {timeZone: "America/New_York"}));
    
    switch (session) {
      case "pre-market":
        return "🔔 Market opens at 9:30 AM ET";
      case "after-hours":
        return "🔔 Next session: Tomorrow 4:00 AM ET";
      case "closed":
        const tomorrow = new Date(et);
        tomorrow.setDate(tomorrow.getDate() + 1);
        const day = tomorrow.getDay();
        if (day === 0) { // Sunday, next is Monday
          return "🔔 Pre-market opens Monday 4:00 AM ET";
        } else if (day === 6) { // Saturday, next is Monday
          return "🔔 Pre-market opens Monday 4:00 AM ET";
        } else {
          return "🔔 Pre-market opens at 4:00 AM ET";
        }
      default:
        return "";
    }
  }
}

const containerStyle: React.CSSProperties = {
  border: "1px solid #333",
  borderRadius: 12,
  padding: 16,
  background: "#111",
  marginBottom: 16,
  position: "relative",
};

const contentStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
};

const mainInfoStyle: React.CSSProperties = {
  flex: 1,
};

const sessionHeaderStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 8,
};

const timeStyle: React.CSSProperties = {
  textAlign: "right",
};

const nextSessionStyle: React.CSSProperties = {
  fontSize: 11,
  color: "#666",
  marginTop: 8,
  paddingTop: 8,
  borderTop: "1px solid #333",
  textAlign: "center",
};