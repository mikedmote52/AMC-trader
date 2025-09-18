import React, { useState } from "react";
import { API_BASE } from "../config";
import { getJSON } from "../lib/api";

type TradeOutcome = {
  symbol: string;
  entry_price: number;
  exit_price: number;
  days_held: number;
  return_pct: number;
  entry_date?: string;
  exit_date?: string;
};

const isMobile = window.innerWidth < 768;

export default function InteractiveTradeTracker() {
  const [symbol, setSymbol] = useState("");
  const [entryPrice, setEntryPrice] = useState("");
  const [exitPrice, setExitPrice] = useState("");
  const [daysHeld, setDaysHeld] = useState("");
  const [entryDate, setEntryDate] = useState("");
  const [exitDate, setExitDate] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string; return_pct?: number } | null>(null);
  const [recentTrades, setRecentTrades] = useState<TradeOutcome[]>([]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setResult(null);

    try {
      const response = await getJSON(`${API_BASE}/learning-analytics/patterns/log-explosive-winner`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          symbol: symbol.toUpperCase(),
          entry_price: parseFloat(entryPrice),
          exit_price: parseFloat(exitPrice),
          days_held: parseInt(daysHeld)
        })
      });

      if (response?.success) {
        setResult({
          success: true,
          message: response.message,
          return_pct: response.return_pct
        });

        // Add to recent trades
        const newTrade: TradeOutcome = {
          symbol: symbol.toUpperCase(),
          entry_price: parseFloat(entryPrice),
          exit_price: parseFloat(exitPrice),
          days_held: parseInt(daysHeld),
          return_pct: response.return_pct,
          entry_date: entryDate,
          exit_date: exitDate
        };

        setRecentTrades(prev => [newTrade, ...prev.slice(0, 4)]);

        // Reset form
        setSymbol("");
        setEntryPrice("");
        setExitPrice("");
        setDaysHeld("");
        setEntryDate("");
        setExitDate("");
      } else {
        setResult({
          success: false,
          message: response?.error || "Failed to track trade outcome"
        });
      }
    } catch (error) {
      setResult({
        success: false,
        message: "Network error - trade outcome tracking may not be available yet"
      });
    } finally {
      setSubmitting(false);
    }
  };

  const calculateReturnPct = () => {
    if (!entryPrice || !exitPrice) return null;
    const entry = parseFloat(entryPrice);
    const exit = parseFloat(exitPrice);
    if (isNaN(entry) || isNaN(exit) || entry <= 0) return null;
    return ((exit - entry) / entry * 100).toFixed(2);
  };

  const previewReturn = calculateReturnPct();

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h3 style={titleStyle}>📊 Interactive Trade Outcome Tracker</h3>
        <div style={subtitleStyle}>
          Help the learning system improve by tracking your actual trade results
        </div>
      </div>

      <div style={contentStyle}>
        <div style={formSectionStyle}>
          <h4 style={formTitleStyle}>Track New Trade Outcome</h4>

          <form onSubmit={handleSubmit} style={formStyle}>
            <div style={formGridStyle}>
              <div style={inputGroupStyle}>
                <label style={labelStyle}>Symbol</label>
                <input
                  type="text"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                  placeholder="VIGL"
                  style={inputStyle}
                  required
                />
              </div>

              <div style={inputGroupStyle}>
                <label style={labelStyle}>Entry Price</label>
                <input
                  type="number"
                  step="0.01"
                  value={entryPrice}
                  onChange={(e) => setEntryPrice(e.target.value)}
                  placeholder="2.50"
                  style={inputStyle}
                  required
                />
              </div>

              <div style={inputGroupStyle}>
                <label style={labelStyle}>Exit Price</label>
                <input
                  type="number"
                  step="0.01"
                  value={exitPrice}
                  onChange={(e) => setExitPrice(e.target.value)}
                  placeholder="8.10"
                  style={inputStyle}
                  required
                />
              </div>

              <div style={inputGroupStyle}>
                <label style={labelStyle}>Days Held</label>
                <input
                  type="number"
                  min="1"
                  value={daysHeld}
                  onChange={(e) => setDaysHeld(e.target.value)}
                  placeholder="7"
                  style={inputStyle}
                  required
                />
              </div>

              <div style={inputGroupStyle}>
                <label style={labelStyle}>Entry Date (Optional)</label>
                <input
                  type="date"
                  value={entryDate}
                  onChange={(e) => setEntryDate(e.target.value)}
                  style={inputStyle}
                />
              </div>

              <div style={inputGroupStyle}>
                <label style={labelStyle}>Exit Date (Optional)</label>
                <input
                  type="date"
                  value={exitDate}
                  onChange={(e) => setExitDate(e.target.value)}
                  style={inputStyle}
                />
              </div>
            </div>

            {previewReturn && (
              <div style={previewStyle}>
                <div style={previewLabelStyle}>Preview Return:</div>
                <div style={{
                  ...previewValueStyle,
                  color: parseFloat(previewReturn) > 0 ? '#22c55e' : '#ef4444'
                }}>
                  {parseFloat(previewReturn) > 0 ? '+' : ''}{previewReturn}%
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={submitting || !symbol || !entryPrice || !exitPrice || !daysHeld}
              style={{
                ...submitButtonStyle,
                ...(submitting && disabledButtonStyle)
              }}
            >
              {submitting ? "Tracking..." : "Track Trade Outcome"}
            </button>
          </form>

          {result && (
            <div style={{
              ...resultStyle,
              ...(result.success ? successResultStyle : errorResultStyle)
            }}>
              <div style={resultMessageStyle}>
                {result.success ? '✅' : '❌'} {result.message}
              </div>
              {result.success && result.return_pct !== undefined && (
                <div style={resultReturnStyle}>
                  Return: {result.return_pct > 0 ? '+' : ''}{result.return_pct.toFixed(2)}%
                </div>
              )}
            </div>
          )}
        </div>

        {recentTrades.length > 0 && (
          <div style={recentTradesStyle}>
            <h4 style={recentTitleStyle}>Recent Tracked Trades</h4>
            <div style={tradesListStyle}>
              {recentTrades.map((trade, index) => (
                <div key={index} style={tradeItemStyle}>
                  <div style={tradeHeaderStyle}>
                    <span style={tradeSymbolStyle}>{trade.symbol}</span>
                    <span style={{
                      ...tradeReturnStyle,
                      color: trade.return_pct > 0 ? '#22c55e' : '#ef4444'
                    }}>
                      {trade.return_pct > 0 ? '+' : ''}{trade.return_pct.toFixed(2)}%
                    </span>
                  </div>
                  <div style={tradeDetailsStyle}>
                    ${trade.entry_price.toFixed(2)} → ${trade.exit_price.toFixed(2)} • {trade.days_held} days
                  </div>
                  {trade.entry_date && trade.exit_date && (
                    <div style={tradeDatesStyle}>
                      {new Date(trade.entry_date).toLocaleDateString()} → {new Date(trade.exit_date).toLocaleDateString()}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div style={infoSectionStyle}>
        <h4 style={infoTitleStyle}>🎯 How This Helps Learning</h4>
        <div style={infoBulletStyle}>
          <span style={bulletStyle}>•</span>
          <span>Tracks which discovery patterns led to successful trades</span>
        </div>
        <div style={infoBulletStyle}>
          <span style={bulletStyle}>•</span>
          <span>Improves confidence calibration for future recommendations</span>
        </div>
        <div style={infoBulletStyle}>
          <span style={bulletStyle}>•</span>
          <span>Optimizes discovery parameters based on actual outcomes</span>
        </div>
        <div style={infoBulletStyle}>
          <span style={bulletStyle}>•</span>
          <span>Builds pattern library of explosive winners for similarity matching</span>
        </div>
      </div>
    </div>
  );
}

// Styles
const containerStyle: React.CSSProperties = {
  background: '#111',
  border: '1px solid #333',
  borderRadius: '12px',
  padding: isMobile ? '16px' : '24px',
  marginBottom: '24px'
};

const headerStyle: React.CSSProperties = {
  marginBottom: '20px',
  textAlign: 'center'
};

const titleStyle: React.CSSProperties = {
  fontSize: '18px',
  fontWeight: 700,
  color: '#fff',
  marginBottom: '8px'
};

const subtitleStyle: React.CSSProperties = {
  fontSize: '14px',
  color: '#999',
  lineHeight: '1.4'
};

const contentStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: isMobile ? '1fr' : '2fr 1fr',
  gap: '24px',
  marginBottom: '20px'
};

const formSectionStyle: React.CSSProperties = {
  background: '#0a0a0a',
  border: '1px solid #333',
  borderRadius: '8px',
  padding: '20px'
};

const formTitleStyle: React.CSSProperties = {
  fontSize: '16px',
  fontWeight: 600,
  color: '#fff',
  marginBottom: '16px'
};

const formStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '16px'
};

const formGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: isMobile ? '1fr' : 'repeat(2, 1fr)',
  gap: '12px'
};

const inputGroupStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '4px'
};

const labelStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#999',
  fontWeight: 600
};

const inputStyle: React.CSSProperties = {
  background: '#111',
  border: '1px solid #333',
  borderRadius: '6px',
  padding: '8px 12px',
  color: '#fff',
  fontSize: '14px'
};

const previewStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '12px',
  background: '#111',
  border: '1px solid #333',
  borderRadius: '6px'
};

const previewLabelStyle: React.CSSProperties = {
  fontSize: '14px',
  color: '#999'
};

const previewValueStyle: React.CSSProperties = {
  fontSize: '16px',
  fontWeight: 700
};

const submitButtonStyle: React.CSSProperties = {
  background: '#22c55e',
  border: 'none',
  borderRadius: '8px',
  padding: '12px 20px',
  color: '#000',
  fontSize: '14px',
  fontWeight: 700,
  cursor: 'pointer',
  transition: 'all 0.2s ease'
};

const disabledButtonStyle: React.CSSProperties = {
  background: '#333',
  color: '#666',
  cursor: 'not-allowed'
};

const resultStyle: React.CSSProperties = {
  padding: '12px',
  borderRadius: '6px',
  border: '1px solid'
};

const successResultStyle: React.CSSProperties = {
  background: 'rgba(34, 197, 94, 0.1)',
  borderColor: '#22c55e'
};

const errorResultStyle: React.CSSProperties = {
  background: 'rgba(239, 68, 68, 0.1)',
  borderColor: '#ef4444'
};

const resultMessageStyle: React.CSSProperties = {
  fontSize: '14px',
  color: '#fff',
  marginBottom: '4px'
};

const resultReturnStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#22c55e',
  fontWeight: 600
};

const recentTradesStyle: React.CSSProperties = {
  background: '#0a0a0a',
  border: '1px solid #333',
  borderRadius: '8px',
  padding: '16px'
};

const recentTitleStyle: React.CSSProperties = {
  fontSize: '14px',
  fontWeight: 600,
  color: '#fff',
  marginBottom: '12px'
};

const tradesListStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '8px'
};

const tradeItemStyle: React.CSSProperties = {
  background: '#111',
  border: '1px solid #333',
  borderRadius: '6px',
  padding: '12px'
};

const tradeHeaderStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '4px'
};

const tradeSymbolStyle: React.CSSProperties = {
  fontSize: '14px',
  color: '#fff',
  fontWeight: 600
};

const tradeReturnStyle: React.CSSProperties = {
  fontSize: '14px',
  fontWeight: 700
};

const tradeDetailsStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#999',
  marginBottom: '2px'
};

const tradeDatesStyle: React.CSSProperties = {
  fontSize: '11px',
  color: '#666'
};

const infoSectionStyle: React.CSSProperties = {
  background: '#0a0a0a',
  border: '1px solid #333',
  borderRadius: '8px',
  padding: '16px'
};

const infoTitleStyle: React.CSSProperties = {
  fontSize: '14px',
  fontWeight: 600,
  color: '#22c55e',
  marginBottom: '12px'
};

const infoBulletStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  gap: '8px',
  marginBottom: '8px',
  fontSize: '12px',
  color: '#ccc',
  lineHeight: '1.4'
};

const bulletStyle: React.CSSProperties = {
  color: '#22c55e',
  fontWeight: 700,
  flexShrink: 0
};