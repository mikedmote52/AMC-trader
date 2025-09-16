import React, { useState } from "react";
import SqueezeAlert from "./SqueezeAlert";
import PatternHistory from "./PatternHistory";
import { useAlphaStackLive } from "../hooks/useAlphaStackLive";
import { mapList, filterByAction, sortByScore, SqueezeOpportunity } from "../lib/alphastack-adapter";

interface SqueezeMonitorProps {
  watchedSymbols?: string[];
  showPatternHistory?: boolean;
}

interface PortfolioAction {
  type: 'immediate' | 'trim' | 'add' | 'stop_loss';
  symbol?: string;
  action: string;
  priority?: number;
  urgency?: string;
}

// System Status Pill Component
function SystemStatusPill({ telemetry, safeToTrade }: { telemetry: any; safeToTrade: boolean }) {
  const getStatusColor = () => {
    if (!telemetry?.system_health?.system_ready) return '#ef4444'; // Red
    if (telemetry?.production_health?.stale_data_detected) return '#f59e0b'; // Yellow
    return '#22c55e'; // Green
  };

  const getStatusText = () => {
    if (!telemetry?.system_health?.system_ready) return 'System Offline';
    if (telemetry?.production_health?.stale_data_detected) return 'Stale Data';
    return 'System Ready';
  };

  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px',
      padding: '4px 12px',
      borderRadius: '16px',
      background: getStatusColor(),
      color: '#000',
      fontSize: '12px',
      fontWeight: 600,
      textTransform: 'uppercase',
      letterSpacing: '0.5px'
    }}>
      <div style={{
        width: '6px',
        height: '6px',
        borderRadius: '50%',
        background: '#000'
      }} />
      {getStatusText()}
    </div>
  );
}

export default function SqueezeMonitor({
  watchedSymbols = [],
  showPatternHistory = true
}: SqueezeMonitorProps) {
  const { top, explosive, telemetry, safeToTrade, loading, error } = useAlphaStackLive();

  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [portfolioActions] = useState<PortfolioAction[]>([]);

  // Convert AlphaStack data to UI format
  const uiTop = sortByScore(mapList(top?.items ?? []));
  const uiExplosive = sortByScore(mapList(explosive?.explosive_top ?? []));

  // Filter by watched symbols if specified
  const filteredTop = watchedSymbols.length > 0
    ? uiTop.filter(opp => watchedSymbols.includes(opp.symbol))
    : uiTop;

  const filteredExplosive = watchedSymbols.length > 0
    ? uiExplosive.filter(opp => watchedSymbols.includes(opp.symbol))
    : uiExplosive;

  // Categorize opportunities by action
  const allOpportunities = [...filteredTop, ...filteredExplosive];
  const critical = filterByAction(allOpportunities, 'trade_ready');
  const developing = filterByAction(allOpportunities, 'watchlist');
  const early = allOpportunities.filter(opp =>
    opp.action !== 'trade_ready' && opp.action !== 'watchlist'
  );

  const handleSignificantMove = (symbol: string, changePercent: number) => {
    console.log(`Significant move detected: ${symbol} ${changePercent.toFixed(2)}%`);

    if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
      new Notification(`${symbol} Alert`, {
        body: `Significant move: ${changePercent.toFixed(2)}%`,
        icon: '/favicon.ico'
      });
    }
  };

  if (error) {
    return (
      <div style={containerStyle}>
        <div style={{
          padding: '24px',
          background: '#2d1b1b',
          border: '1px solid #ef4444',
          borderRadius: '12px',
          color: '#ef4444',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '18px', fontWeight: 600, marginBottom: '8px' }}>
            ⚠️ AlphaStack Connection Error
          </div>
          <div style={{ fontSize: '14px', color: '#ccc' }}>
            {error}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      {/* Header with Status */}
      <div style={headerStyle}>
        <div style={titleContainerStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <h1 style={titleStyle}>🔍 Squeeze Monitor</h1>
            <SystemStatusPill telemetry={telemetry} safeToTrade={safeToTrade} />
          </div>
          <p style={subtitleStyle}>
            AlphaStack 4.1 Discovery • Schema: {telemetry?.schema_version || 'Unknown'}
          </p>
        </div>

        {loading && (
          <div style={{
            padding: '8px 16px',
            background: '#1a1a1a',
            border: '1px solid #333',
            borderRadius: '8px',
            color: '#ccc',
            fontSize: '14px'
          }}>
            Loading...
          </div>
        )}
      </div>

      {/* Critical Opportunities (Trade Ready) */}
      {critical.length > 0 && (
        <div style={sectionStyle}>
          <div style={sectionTitleStyle}>🚀 Critical Opportunities ({critical.length})</div>
          <div style={alertsContainerStyle}>
            {critical.slice(0, 6).map((opportunity, index) => (
              <SqueezeAlert
                key={`critical-${opportunity.symbol}-${index}`}
                symbol={opportunity.symbol}
                score={opportunity.squeeze_score * 100} // Convert to percentage
                pattern={opportunity.pattern_type || 'STRONG_BUY'}
                price={opportunity.price || 0}
                volume={opportunity.volume_spike || 0}
                onTrade={() => handleSignificantMove(opportunity.symbol, 5.0)}
                disabled={!safeToTrade || opportunity.action !== 'trade_ready'}
              />
            ))}
          </div>
        </div>
      )}

      {/* Developing Opportunities (Watchlist) */}
      {developing.length > 0 && (
        <div style={sectionStyle}>
          <div style={sectionTitleStyle}>📈 Developing Opportunities ({developing.length})</div>
          <div style={alertsContainerStyle}>
            {developing.slice(0, 6).map((opportunity, index) => (
              <SqueezeAlert
                key={`developing-${opportunity.symbol}-${index}`}
                symbol={opportunity.symbol}
                score={opportunity.squeeze_score * 100}
                pattern={opportunity.pattern_type || 'WATCH'}
                price={opportunity.price || 0}
                volume={opportunity.volume_spike || 0}
                onTrade={() => handleSignificantMove(opportunity.symbol, 3.0)}
                disabled={!safeToTrade || opportunity.action !== 'trade_ready'}
              />
            ))}
          </div>
        </div>
      )}

      {/* Early Stage Opportunities */}
      {early.length > 0 && (
        <div style={sectionStyle}>
          <div style={sectionTitleStyle}>🔍 Early Stage ({early.length})</div>
          <div style={alertsContainerStyle}>
            {early.slice(0, 6).map((opportunity, index) => (
              <SqueezeAlert
                key={`early-${opportunity.symbol}-${index}`}
                symbol={opportunity.symbol}
                score={opportunity.squeeze_score * 100}
                pattern={opportunity.pattern_type || 'MONITOR'}
                price={opportunity.price || 0}
                volume={opportunity.volume_spike || 0}
                onTrade={() => handleSignificantMove(opportunity.symbol, 2.0)}
                disabled={true} // Early stage always disabled
              />
            ))}
          </div>
        </div>
      )}

      {/* Active Monitoring Summary */}
      <div style={sectionStyle}>
        <div style={sectionTitleStyle}>📊 Active Monitoring ({allOpportunities.length} symbols)</div>
        <div style={summaryContainerStyle}>
          {allOpportunities.slice(0, 6).map((opportunity, index) => (
            <div key={`summary-${opportunity.symbol}-${index}`} style={summaryCardStyle}>
              <div style={symbolHeaderStyle}>
                <span style={symbolTextStyle}>{opportunity.symbol}</span>
                <span style={{
                  fontSize: '12px',
                  color: opportunity.action === 'trade_ready' ? '#22c55e' : '#f59e0b',
                  fontWeight: 600
                }}>
                  {opportunity.action?.toUpperCase() || 'MONITOR'}
                </span>
              </div>
              <span style={scoreTextStyle}>
                Score: {(opportunity.squeeze_score * 100).toFixed(0)}% | {opportunity.action || 'EVAL'}
              </span>
            </div>
          ))}
          {allOpportunities.length > 6 && (
            <div style={{
              ...summaryCardStyle,
              justifyContent: 'center',
              alignItems: 'center',
              color: '#999',
              fontStyle: 'italic'
            }}>
              +{allOpportunities.length - 6} more symbols being monitored
            </div>
          )}
        </div>
      </div>

      {/* Portfolio Actions */}
      {portfolioActions.length > 0 && (
        <div style={sectionStyle}>
          <div style={sectionTitleStyle}>⚡ Portfolio Actions Required</div>
          <div style={alertsContainerStyle}>
            {portfolioActions.map((action, index) => (
              <div key={`action-${index}`} style={{
                padding: '16px',
                background: action.type === 'immediate' ? '#2d1b1b' : '#1a1a1a',
                border: `1px solid ${action.type === 'immediate' ? '#ef4444' : '#333'}`,
                borderRadius: '8px',
                color: '#e7e7e7'
              }}>
                <div style={{ fontWeight: 600, marginBottom: '8px' }}>
                  {action.symbol || 'Portfolio'}: {action.action}
                </div>
                {action.urgency && (
                  <div style={{ fontSize: '12px', color: '#ccc' }}>
                    Urgency: {action.urgency}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pattern History */}
      {showPatternHistory && (
        <div style={sectionStyle}>
          <div style={sectionTitleStyle}>
            📚 Pattern History
            <button
              onClick={() => setShowHistory(!showHistory)}
              style={{
                marginLeft: '16px',
                padding: '4px 12px',
                background: '#333',
                border: 'none',
                borderRadius: '6px',
                color: '#ccc',
                fontSize: '12px',
                cursor: 'pointer'
              }}
            >
              {showHistory ? 'Hide' : 'Show'}
            </button>
          </div>
          {showHistory && (
            <PatternHistory
              currentSymbol={selectedSymbol || undefined}
              onSymbolSelect={(pattern: any) => {
                setSelectedSymbol(pattern.symbol);
              }}
            />
          )}
        </div>
      )}

      {/* System Info Footer */}
      <div style={footerStyle}>
        <div style={footerItemStyle}>
          <div>AlphaStack 4.1 Integration</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            {safeToTrade ? '✅ Safe to Trade' : '⚠️ Trading Restricted'}
          </div>
        </div>
        <div style={footerItemStyle}>
          <div>Total Candidates: {allOpportunities.length}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            Trade Ready: {critical.length} • Watchlist: {developing.length}
          </div>
        </div>
        <div style={footerItemStyle}>
          <div>Monitoring Scope</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            {watchedSymbols.length > 0 ? `${watchedSymbols.length} symbols` : "All symbols"}
          </div>
        </div>
      </div>
    </div>
  );
}

// Styles (keeping existing styles from original component)
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
  fontWeight: 500
};

const sectionStyle: React.CSSProperties = {
  marginBottom: "32px"
};

const sectionTitleStyle: React.CSSProperties = {
  fontSize: "18px",
  fontWeight: 600,
  color: "#fff",
  marginBottom: "16px",
  display: "flex",
  alignItems: "center"
};

const alertsContainerStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
  gap: "16px"
};

const summaryContainerStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
  gap: "12px"
};

const summaryCardStyle: React.CSSProperties = {
  padding: "12px",
  background: "#111",
  border: "1px solid #333",
  borderRadius: "8px",
  display: "flex",
  flexDirection: "column",
  gap: "8px"
};

const symbolHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center"
};

const symbolTextStyle: React.CSSProperties = {
  fontWeight: 600,
  color: "#fff"
};

const scoreTextStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#ccc"
};

const footerStyle: React.CSSProperties = {
  marginTop: "40px",
  padding: "24px",
  background: "#111",
  border: "1px solid #333",
  borderRadius: "12px",
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
  gap: "24px"
};

const footerItemStyle: React.CSSProperties = {
  textAlign: "center"
};