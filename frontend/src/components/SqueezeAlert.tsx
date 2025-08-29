import React, { useState } from "react";
import { API_BASE } from "../config";
import { postJSON } from "../lib/api";
import "./SqueezeAlert.css";

interface SqueezeMetrics {
  squeeze_score: number;
  volume_spike: number;
  short_interest: number;
  price: number;
  pattern_type?: string;
  confidence?: number;
}

interface SqueezeAlertProps {
  symbol: string;
  metrics: SqueezeMetrics;
  onTradeExecuted?: (result: any) => void;
}

export default function SqueezeAlert({ symbol, metrics, onTradeExecuted }: SqueezeAlertProps) {
  const [executing, setExecuting] = useState(false);
  const [lastExecuted, setLastExecuted] = useState<Date | null>(null);

  // Only show alerts for high-confidence squeeze patterns
  if (metrics.squeeze_score < 0.70) return null;

  const calculatePositionSize = () => {
    const maxPosition = 100; // $100 max position
    const currentPrice = metrics.price;
    if (!currentPrice || currentPrice <= 0) return { shares: 0, amount: 0 };
    
    const maxShares = Math.floor(maxPosition / currentPrice);
    const actualAmount = maxShares * currentPrice;
    return { shares: maxShares, amount: actualAmount };
  };

  const executeQuickTrade = async (tradeType: 'bracket' | 'market') => {
    if (executing) return;
    
    try {
      setExecuting(true);
      
      const { shares, amount } = calculatePositionSize();
      if (shares === 0) {
        alert(`❌ Position size too small - ${symbol} at $${metrics.price.toFixed(2)}`);
        return;
      }

      // Show quick confirmation
      const confirmed = confirm(
        `🚨 SQUEEZE TRADE CONFIRMATION\n\n` +
        `Symbol: ${symbol}\n` +
        `Squeeze Score: ${(metrics.squeeze_score * 100).toFixed(0)}%\n` +
        `Volume Spike: ${metrics.volume_spike}x\n` +
        `Short Interest: ${metrics.short_interest}%\n\n` +
        `Position: ${shares} shares (~$${amount.toFixed(2)})\n` +
        `Type: ${tradeType === 'bracket' ? 'Bracket Order with Stops' : 'Market Order'}\n\n` +
        `Execute trade?`
      );

      if (!confirmed) return;

      // Execute the trade based on type
      let result;
      if (tradeType === 'bracket') {
        // Bracket order with stops (3% stop loss, 10% take profit)
        const stopPrice = metrics.price * 0.97; // 3% stop loss
        const takeProfitPrice = metrics.price * 1.10; // 10% take profit
        
        result = await postJSON(`${API_BASE}/trades/bracket`, {
          symbol,
          action: "BUY",
          qty: shares,
          limit_price: metrics.price * 1.01, // Slight premium for execution
          stop_price: stopPrice,
          take_profit_price: takeProfitPrice,
          mode: "live",
          squeeze_context: {
            squeeze_score: metrics.squeeze_score,
            volume_spike: metrics.volume_spike,
            short_interest: metrics.short_interest
          }
        });
      } else {
        // Simple market order
        result = await postJSON(`${API_BASE}/trades/execute`, {
          symbol,
          action: "BUY",
          qty: shares,
          mode: "live",
          squeeze_context: {
            squeeze_score: metrics.squeeze_score,
            volume_spike: metrics.volume_spike
          }
        });
      }

      if (result.success) {
        alert(`✅ Squeeze trade executed: ${result.message}`);
        setLastExecuted(new Date());
        onTradeExecuted?.(result);
      } else {
        alert(`❌ Trade failed: ${result.error?.message || "Unknown error"}`);
      }

    } catch (error: any) {
      console.error("Squeeze trade error:", error);
      alert(`❌ Trade error: ${error?.message || "Failed to execute squeeze trade"}`);
    } finally {
      setExecuting(false);
    }
  };

  const { shares, amount } = calculatePositionSize();
  const riskAmount = amount * 0.03; // 3% risk
  const rewardAmount = amount * 0.10; // 10% reward
  const riskRewardRatio = rewardAmount / riskAmount;

  const alertLevel = metrics.squeeze_score >= 0.90 ? 'critical' : metrics.squeeze_score >= 0.80 ? 'high' : 'medium';

  return (
    <div style={{
      ...squeezeAlertStyle,
      borderColor: alertLevel === 'critical' ? '#ef4444' : alertLevel === 'high' ? '#f59e0b' : '#22c55e',
      backgroundColor: alertLevel === 'critical' ? 'rgba(239, 68, 68, 0.1)' : alertLevel === 'high' ? 'rgba(245, 158, 11, 0.1)' : 'rgba(34, 197, 94, 0.1)'
    }}>
      
      {/* Pulse Animation Header */}
      <div style={pulseHeaderStyle}>
        <div style={pulseStyle}>
          🚨 SQUEEZE DETECTED: {symbol}
        </div>
        <div style={scoreStyle}>
          {(metrics.squeeze_score * 100).toFixed(0)}% CONFIDENCE
        </div>
      </div>

      {/* Metrics Grid */}
      <div style={metricsGridStyle}>
        <div style={metricItemStyle}>
          <span style={metricLabelStyle}>Volume</span>
          <span style={metricValueStyle}>{metrics.volume_spike.toFixed(1)}x</span>
        </div>
        <div style={metricItemStyle}>
          <span style={metricLabelStyle}>Short Int.</span>
          <span style={metricValueStyle}>{metrics.short_interest.toFixed(1)}%</span>
        </div>
        <div style={metricItemStyle}>
          <span style={metricLabelStyle}>Price</span>
          <span style={metricValueStyle}>${metrics.price.toFixed(2)}</span>
        </div>
        {metrics.pattern_type && (
          <div style={metricItemStyle}>
            <span style={metricLabelStyle}>Pattern</span>
            <span style={metricValueStyle}>{metrics.pattern_type}</span>
          </div>
        )}
      </div>

      {/* Position Sizing */}
      <div style={positionSizeStyle}>
        <div style={sizeHeaderStyle}>📊 Position Calculator</div>
        <div style={sizeDetailsStyle}>
          <span>Size: {shares} shares (~${amount.toFixed(2)})</span>
          <span style={{color: '#ef4444'}}>Risk: ${riskAmount.toFixed(2)}</span>
          <span style={{color: '#22c55e'}}>Reward: ${rewardAmount.toFixed(2)}</span>
          <span>R/R: {riskRewardRatio.toFixed(1)}:1</span>
        </div>
      </div>

      {/* Action Buttons */}
      <div style={actionButtonsStyle}>
        <button 
          onClick={() => executeQuickTrade('bracket')}
          disabled={executing || shares === 0}
          style={{
            ...primaryButtonStyle,
            opacity: executing || shares === 0 ? 0.5 : 1,
            cursor: executing || shares === 0 ? 'not-allowed' : 'pointer'
          }}
        >
          {executing ? '⏳ Executing...' : '⚡ Quick Entry with Stops'}
        </button>
        
        <button 
          onClick={() => executeQuickTrade('market')}
          disabled={executing || shares === 0}
          style={{
            ...secondaryButtonStyle,
            opacity: executing || shares === 0 ? 0.5 : 1,
            cursor: executing || shares === 0 ? 'not-allowed' : 'pointer'
          }}
        >
          {executing ? '⏳ Wait...' : '🎯 Market Order'}
        </button>
      </div>

      {/* Last Executed */}
      {lastExecuted && (
        <div style={lastExecutedStyle}>
          ✅ Last trade: {lastExecuted.toLocaleTimeString()}
        </div>
      )}

      {/* Risk Warning */}
      {shares === 0 && (
        <div style={warningStyle}>
          ⚠️ Price too high for $100 max position
        </div>
      )}
    </div>
  );
}

// Styles
const squeezeAlertStyle: React.CSSProperties = {
  border: '2px solid',
  borderRadius: '16px',
  padding: '20px',
  margin: '16px 0',
  position: 'relative',
  overflow: 'hidden',
  backdropFilter: 'blur(10px)'
};

const pulseHeaderStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '16px'
};

const pulseStyle: React.CSSProperties = {
  fontSize: '18px',
  fontWeight: 800,
  color: '#fff',
  animation: 'pulse 1.5s infinite',
  textShadow: '0 0 10px rgba(255, 255, 255, 0.5)'
};

const scoreStyle: React.CSSProperties = {
  fontSize: '14px',
  fontWeight: 700,
  color: '#f59e0b',
  textTransform: 'uppercase',
  letterSpacing: '1px'
};

const metricsGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
  gap: '12px',
  marginBottom: '16px',
  padding: '16px',
  background: 'rgba(0, 0, 0, 0.3)',
  borderRadius: '12px'
};

const metricItemStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  gap: '4px'
};

const metricLabelStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#999',
  textTransform: 'uppercase',
  fontWeight: 600
};

const metricValueStyle: React.CSSProperties = {
  fontSize: '16px',
  color: '#fff',
  fontWeight: 700
};

const positionSizeStyle: React.CSSProperties = {
  background: 'rgba(0, 0, 0, 0.2)',
  borderRadius: '12px',
  padding: '12px',
  marginBottom: '16px'
};

const sizeHeaderStyle: React.CSSProperties = {
  fontSize: '14px',
  fontWeight: 700,
  color: '#22c55e',
  marginBottom: '8px',
  textTransform: 'uppercase'
};

const sizeDetailsStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))',
  gap: '8px',
  fontSize: '13px',
  fontWeight: 600
};

const actionButtonsStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '1fr 1fr',
  gap: '12px',
  marginBottom: '12px'
};

const primaryButtonStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, #ef4444, #dc2626)',
  border: 'none',
  borderRadius: '12px',
  padding: '14px',
  color: '#fff',
  fontSize: '14px',
  fontWeight: 700,
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  cursor: 'pointer',
  transition: 'all 0.2s ease',
  boxShadow: '0 4px 12px rgba(239, 68, 68, 0.3)'
};

const secondaryButtonStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, #374151, #1f2937)',
  border: '1px solid #6b7280',
  borderRadius: '12px',
  padding: '14px',
  color: '#fff',
  fontSize: '14px',
  fontWeight: 700,
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  cursor: 'pointer',
  transition: 'all 0.2s ease'
};

const lastExecutedStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#22c55e',
  textAlign: 'center',
  fontWeight: 600,
  marginTop: '8px'
};

const warningStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#f59e0b',
  textAlign: 'center',
  fontWeight: 600,
  marginTop: '8px',
  padding: '8px',
  background: 'rgba(245, 158, 11, 0.1)',
  borderRadius: '8px'
};