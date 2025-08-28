import React, { useMemo } from "react";

type Holding = {
  symbol: string;
  qty: number;
  avg_entry_price: number;
  last_price: number;
  market_value: number;
  unrealized_pl: number;
  unrealized_pl_pct: number;
};

type PortfolioSummaryProps = {
  holdings: Holding[];
  isLoading?: boolean;
};

export default function PortfolioSummary({ holdings, isLoading }: PortfolioSummaryProps) {
  const stats = useMemo(() => {
    if (!holdings.length) return null;

    const totalValue = holdings.reduce((sum, h) => sum + h.market_value, 0);
    const totalPL = holdings.reduce((sum, h) => sum + h.unrealized_pl, 0);
    const totalInvested = totalValue - totalPL;
    const avgPLPct = totalInvested > 0 ? (totalPL / totalInvested) * 100 : 0;
    
    const winners = holdings.filter(h => h.unrealized_pl > 0);
    const losers = holdings.filter(h => h.unrealized_pl < 0);
    const winRate = holdings.length > 0 ? (winners.length / holdings.length) * 100 : 0;

    return {
      totalValue,
      totalPL,
      totalInvested,
      avgPLPct,
      winRate,
      positions: holdings.length,
      winners: winners.length,
      losers: losers.length,
    };
  }, [holdings]);

  if (isLoading) {
    return (
      <div style={containerStyle}>
        <div style={loadingStyle}>Loading portfolio...</div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div style={containerStyle}>
        <div style={emptyStyle}>No positions to display</div>
      </div>
    );
  }

  const isPositive = stats.totalPL >= 0;
  const plColor = isPositive ? "#22c55e" : "#ef4444";
  const plBg = isPositive ? "rgba(34, 197, 94, 0.1)" : "rgba(239, 68, 68, 0.1)";

  return (
    <div style={containerStyle}>
      {/* Main Performance Card */}
      <div style={{
        ...performanceCardStyle,
        background: `linear-gradient(135deg, ${plBg}, #111)`,
        borderColor: `${plColor}30`
      }}>
        <div style={headerStyle}>
          <span style={labelStyle}>Portfolio Value</span>
          <div style={valueStyle}>${stats.totalValue.toFixed(2)}</div>
        </div>
        
        <div style={plSectionStyle}>
          <div style={{ ...plValueStyle, color: plColor }}>
            {isPositive ? "+" : ""}${stats.totalPL.toFixed(2)}
          </div>
          <div style={{ ...plPctStyle, color: plColor }}>
            {isPositive ? "+" : ""}{stats.avgPLPct.toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="portfolio-stats-grid" style={statsGridStyle}>
        <div style={statItemStyle}>
          <div style={statValueStyle}>{stats.positions}</div>
          <div style={statLabelStyle}>Positions</div>
        </div>
        <div style={statItemStyle}>
          <div style={statValueStyle}>{stats.winRate.toFixed(0)}%</div>
          <div style={statLabelStyle}>Win Rate</div>
        </div>
        <div style={statItemStyle}>
          <div style={{...statValueStyle, color: "#22c55e"}}>{stats.winners}</div>
          <div style={statLabelStyle}>Winners</div>
        </div>
        <div style={statItemStyle}>
          <div style={{...statValueStyle, color: "#ef4444"}}>{stats.losers}</div>
          <div style={statLabelStyle}>Losers</div>
        </div>
      </div>
    </div>
  );
}

const containerStyle: React.CSSProperties = {
  marginBottom: 24,
  display: "flex",
  flexDirection: "column",
  gap: 12,
};

const loadingStyle: React.CSSProperties = {
  padding: 20,
  textAlign: "center",
  color: "#999",
  background: "#111",
  borderRadius: 12,
  border: "1px solid #333",
};

const emptyStyle: React.CSSProperties = {
  padding: 20,
  textAlign: "center", 
  color: "#999",
  background: "#111",
  borderRadius: 12,
  border: "1px solid #333",
};

const performanceCardStyle: React.CSSProperties = {
  border: "1px solid #333",
  borderRadius: 16,
  padding: 20,
  background: "#111",
  display: "flex",
  flexDirection: "column",
  gap: 12,
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
};

const labelStyle: React.CSSProperties = {
  fontSize: 14,
  color: "#999",
  fontWeight: 500,
};

const valueStyle: React.CSSProperties = {
  fontSize: 24,
  fontWeight: 700,
  color: "#eee",
  letterSpacing: "-0.02em",
};

const plSectionStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "baseline",
  gap: 12,
};

const plValueStyle: React.CSSProperties = {
  fontSize: 32,
  fontWeight: 800,
  letterSpacing: "-0.03em",
};

const plPctStyle: React.CSSProperties = {
  fontSize: 20,
  fontWeight: 600,
};

const statsGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(4, 1fr)",
  gap: 12,
};

const statItemStyle: React.CSSProperties = {
  background: "#111",
  border: "1px solid #333",
  borderRadius: 12,
  padding: 16,
  textAlign: "center",
  display: "flex",
  flexDirection: "column",
  gap: 4,
};

const statValueStyle: React.CSSProperties = {
  fontSize: 20,
  fontWeight: 700,
  color: "#eee",
};

const statLabelStyle: React.CSSProperties = {
  fontSize: 12,
  color: "#999",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
};

// Mobile breakpoints - will be handled by parent component responsive design
export const mobileBreakpoints = {
  small: "@media (max-width: 640px)",
  medium: "@media (max-width: 768px)",
  large: "@media (max-width: 1024px)",
};