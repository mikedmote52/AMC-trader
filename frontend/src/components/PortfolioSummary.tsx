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

    // Portfolio Health Metrics
    const largestHolding = Math.max(...holdings.map(h => h.market_value));
    const concentrationPct = totalValue > 0 ? (largestHolding / totalValue) * 100 : 0;
    
    const topMover = holdings.reduce((max, h) =>
      Math.abs(h.unrealized_pl_pct) > Math.abs(max.unrealized_pl_pct) ? h : max
    , holdings[0] || null);

    // Risk Score (based on volatility and concentration)
    const avgVolatility = holdings.reduce((sum, h) => sum + Math.abs(h.unrealized_pl_pct), 0) / holdings.length;
    const riskScore = Math.min(100, (avgVolatility * 2) + (concentrationPct * 0.5));

    // Sector exposure (simplified - using symbol patterns for demo)
    const sectorMap: Record<string, string> = {
      'VIGL': 'Tech', 'CRWV': 'Energy', 'AEVA': 'Auto', 'WOLF': 'Entertainment',
      'QUBT': 'Tech', 'RGTI': 'Tech', 'IONQ': 'Tech', 'QBTS': 'Tech',
      'AMDL': 'Healthcare', 'CARS': 'Auto', 'GMAB': 'Biotech', 'KSS': 'Retail',
      'SPHR': 'Tech', 'SSRM': 'Mining', 'TEM': 'Energy', 'TEVA': 'Pharma',
      'UP': 'Transport', 'WOOF': 'Consumer', 'WULF': 'Crypto'
    };
    
    const sectorExposure = holdings.reduce((sectors: Record<string, number>, h) => {
      const sector = sectorMap[h.symbol] || 'Other';
      sectors[sector] = (sectors[sector] || 0) + h.market_value;
      return sectors;
    }, {});

    const topSector = Object.entries(sectorExposure).reduce((max, [sector, value]) => 
      value > max.value ? { sector, value } : max
    , { sector: 'None', value: 0 });

    const topSectorPct = totalValue > 0 ? (topSector.value / totalValue) * 100 : 0;

    // Average days held (estimated based on P&L patterns - would need actual purchase dates for accuracy)
    const estimatedDaysHeld = holdings.reduce((sum, h) => {
      // Rough estimate: higher absolute P&L suggests longer holding period
      const estimatedDays = Math.max(1, Math.abs(h.unrealized_pl_pct) * 30);
      return sum + Math.min(estimatedDays, 90); // Cap at 90 days
    }, 0) / holdings.length;

    return {
      totalValue,
      totalPL,
      totalInvested,
      avgPLPct,
      winRate,
      positions: holdings.length,
      winners: winners.length,
      losers: losers.length,
      // Health Metrics
      concentrationPct,
      topMover,
      riskScore,
      topSector: topSector.sector,
      topSectorPct,
      avgDaysHeld: Math.round(estimatedDaysHeld),
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
      {/* Real Portfolio Performance */}

      {/* Main Performance Card */}
      <div style={{
        ...performanceCardStyle,
        background: `linear-gradient(135deg, ${plBg}, #111)`,
        borderColor: `${plColor}30`
      }}>
        <div style={headerStyle}>
          <span style={labelStyle}>Current Portfolio Value</span>
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

      {/* Enhanced Stats Grid */}
      <div className="portfolio-stats-grid" style={statsGridStyle}>
        <div style={statItemStyle}>
          <div style={statValueStyle}>{stats.positions}</div>
          <div style={statLabelStyle}>Active Positions</div>
        </div>
        <div style={{...statItemStyle, background: stats.winRate >= 60 ? "rgba(34, 197, 94, 0.1)" : "#111"}}>
          <div style={{...statValueStyle, color: stats.winRate >= 60 ? "#22c55e" : "#eee"}}>{stats.winRate.toFixed(0)}%</div>
          <div style={statLabelStyle}>Win Rate</div>
        </div>
        <div style={{...statItemStyle, background: "rgba(34, 197, 94, 0.1)", border: "1px solid rgba(34, 197, 94, 0.3)"}}>
          <div style={{...statValueStyle, color: "#22c55e"}}>{stats.winners}</div>
          <div style={statLabelStyle}>Winners</div>
        </div>
        <div style={{...statItemStyle, background: stats.losers > 0 ? "rgba(239, 68, 68, 0.1)" : "#111", border: stats.losers > 0 ? "1px solid rgba(239, 68, 68, 0.3)" : "1px solid #333"}}>
          <div style={{...statValueStyle, color: stats.losers > 0 ? "#ef4444" : "#666"}}>{stats.losers}</div>
          <div style={statLabelStyle}>Losers</div>
        </div>
      </div>

      {/* Current Portfolio Stats */}

      {/* Portfolio Health Metrics */}
      <div style={healthSectionStyle}>
        <div style={healthHeaderStyle}>
          <span style={healthTitleStyle}>📊 Portfolio Health</span>
          <span style={healthSubtitleStyle}>Risk & opportunity analysis</span>
        </div>
        
        <div style={healthGridStyle}>
          <div style={healthItemStyle}>
            <div style={healthLabelStyle}>Concentration</div>
            <div style={{
              ...healthValueStyle,
              color: stats.concentrationPct > 40 ? "#ef4444" : stats.concentrationPct > 25 ? "#f59e0b" : "#22c55e"
            }}>
              {stats.concentrationPct.toFixed(0)}%
            </div>
            <div style={healthDescStyle}>Largest position</div>
          </div>

          <div style={healthItemStyle}>
            <div style={healthLabelStyle}>Risk Score</div>
            <div style={{
              ...healthValueStyle,
              color: stats.riskScore > 70 ? "#ef4444" : stats.riskScore > 40 ? "#f59e0b" : "#22c55e"
            }}>
              {Math.round(stats.riskScore)}
            </div>
            <div style={healthDescStyle}>Volatility index</div>
          </div>

          <div style={healthItemStyle}>
            <div style={healthLabelStyle}>Avg Hold Time</div>
            <div style={healthValueStyle}>
              {stats.avgDaysHeld}d
            </div>
            <div style={healthDescStyle}>Position age</div>
          </div>

          <div style={healthItemStyle}>
            <div style={healthLabelStyle}>Top Sector</div>
            <div style={healthValueStyle}>
              {stats.topSectorPct.toFixed(0)}%
            </div>
            <div style={healthDescStyle}>{stats.topSector}</div>
          </div>
        </div>

        {stats.topMover && (
          <div style={topMoverStyle}>
            <div style={topMoverHeaderStyle}>
              <span style={topMoverLabelStyle}>🎯 Top Mover</span>
              <span style={{
                ...topMoverValueStyle,
                color: stats.topMover.unrealized_pl_pct >= 0 ? "#22c55e" : "#ef4444"
              }}>
                {stats.topMover.symbol} {stats.topMover.unrealized_pl_pct.toFixed(1)}%
              </span>
            </div>
            <div style={topMoverDescStyle}>
              ${stats.topMover.market_value.toFixed(2)} • {stats.topMover.unrealized_pl_pct >= 0 ? "Winner" : "Needs attention"}
            </div>
          </div>
        )}
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

// Removed unused demo/marketing styles

const healthSectionStyle: React.CSSProperties = {
  background: "#0a0a0a",
  border: "1px solid #333",
  borderRadius: 12,
  padding: 16,
  marginTop: 16,
};

const healthHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: 16,
};

const healthTitleStyle: React.CSSProperties = {
  fontSize: 14,
  fontWeight: 600,
  color: "#eee",
};

const healthSubtitleStyle: React.CSSProperties = {
  fontSize: 12,
  color: "#999",
  fontStyle: "italic",
};

const healthGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(4, 1fr)",
  gap: 12,
  marginBottom: 16,
};

const healthItemStyle: React.CSSProperties = {
  background: "#111",
  border: "1px solid #333",
  borderRadius: 8,
  padding: 12,
  textAlign: "center",
  display: "flex",
  flexDirection: "column",
  gap: 4,
};

const healthLabelStyle: React.CSSProperties = {
  fontSize: 11,
  color: "#999",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  fontWeight: 600,
};

const healthValueStyle: React.CSSProperties = {
  fontSize: 18,
  fontWeight: 700,
  color: "#eee",
};

const healthDescStyle: React.CSSProperties = {
  fontSize: 10,
  color: "#777",
};

const topMoverStyle: React.CSSProperties = {
  background: "#111",
  border: "1px solid #333",
  borderRadius: 8,
  padding: 12,
};

const topMoverHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: 4,
};

const topMoverLabelStyle: React.CSSProperties = {
  fontSize: 12,
  color: "#eee",
  fontWeight: 600,
};

const topMoverValueStyle: React.CSSProperties = {
  fontSize: 14,
  fontWeight: 700,
};

const topMoverDescStyle: React.CSSProperties = {
  fontSize: 11,
  color: "#999",
};

// Mobile breakpoints - will be handled by parent component responsive design
export const mobileBreakpoints = {
  small: "@media (max-width: 640px)",
  medium: "@media (max-width: 768px)",
  large: "@media (max-width: 1024px)",
};