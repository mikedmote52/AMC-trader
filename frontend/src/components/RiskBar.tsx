import { useMemo } from 'react';
import { usePolling } from '../hooks/usePolling';
import { API_ENDPOINTS } from '../config/api';
import './RiskBar.css';

export function RiskBar() {
  const { data: holdings } = usePolling<any>(API_ENDPOINTS.holdings);
  const { data: recommendations } = usePolling<any>(API_ENDPOINTS.recommendations);

  const riskMetrics = useMemo(() => {
    let totalValue = 0;
    let totalUnrealizedPL = 0;
    let highRiskPositions = 0;
    
    // Handle the API response format: { success: true, data: { positions: [...] } }
    const holdingsArray = holdings?.data?.positions || [];
    if (Array.isArray(holdingsArray)) {
      totalValue = holdingsArray.reduce((sum, holding) => sum + holding.market_value, 0);
      totalUnrealizedPL = holdingsArray.reduce((sum, holding) => sum + holding.unrealized_pl, 0);
    }

    // Handle recommendations (may be wrapped in data or direct array)
    const recsArray = recommendations?.data || recommendations || [];
    if (Array.isArray(recsArray)) {
      highRiskPositions = recsArray.filter(rec => 
        rec.risk_level === 'HIGH' && rec.action !== 'SELL'
      ).length;
    }

    const portfolioReturn = totalValue > 0 ? (totalUnrealizedPL / (totalValue - totalUnrealizedPL)) : 0;
    
    // Calculate risk score based on portfolio return and high-risk positions
    let riskScore = 0;
    
    // Portfolio performance factor (0-40 points)
    if (portfolioReturn < -0.25) riskScore += 40; // -25% or worse
    else if (portfolioReturn < -0.15) riskScore += 30; // -15% to -25%
    else if (portfolioReturn < -0.05) riskScore += 20; // -5% to -15%
    else if (portfolioReturn < 0) riskScore += 10; // 0% to -5%
    
    // High-risk positions factor (0-30 points)
    riskScore += Math.min(highRiskPositions * 10, 30);
    
    // Normalize to 0-100 scale
    riskScore = Math.min(riskScore, 100);
    
    let riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' = 'LOW';
    if (riskScore >= 60) riskLevel = 'HIGH';
    else if (riskScore >= 30) riskLevel = 'MEDIUM';
    
    return {
      score: riskScore,
      level: riskLevel,
      portfolioReturn,
      totalValue,
      totalUnrealizedPL,
      highRiskPositions
    };
  }, [holdings, recommendations]);

  const getRiskColor = () => {
    switch (riskMetrics.level) {
      case 'LOW': return '#22c55e'; // green
      case 'MEDIUM': return '#eab308'; // yellow
      case 'HIGH': return '#ef4444'; // red
      default: return '#6b7280'; // gray
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatPercent = (percent: number) => {
    return `${percent >= 0 ? '+' : ''}${(percent * 100).toFixed(1)}%`;
  };

  return (
    <div className="risk-bar">
      <h2>Risk Assessment</h2>
      
      <div className="risk-indicator">
        <div className="risk-level">
          <span className={`risk-label ${riskMetrics.level.toLowerCase()}`}>
            {riskMetrics.level} RISK
          </span>
          <span className="risk-score">{riskMetrics.score}/100</span>
        </div>
        
        <div className="risk-bar-container">
          <div 
            className="risk-bar-fill"
            style={{ 
              width: `${riskMetrics.score}%`,
              backgroundColor: getRiskColor()
            }}
          />
        </div>
      </div>
      
      <div className="risk-details">
        <div className="risk-metric">
          <span className="label">Portfolio Value:</span>
          <span className="value">{formatCurrency(riskMetrics.totalValue)}</span>
        </div>
        
        <div className="risk-metric">
          <span className="label">Unrealized P/L:</span>
          <span className={`value ${riskMetrics.totalUnrealizedPL >= 0 ? 'positive' : 'negative'}`}>
            {formatCurrency(riskMetrics.totalUnrealizedPL)} 
            ({formatPercent(riskMetrics.portfolioReturn)})
          </span>
        </div>
        
        {riskMetrics.highRiskPositions > 0 && (
          <div className="risk-metric">
            <span className="label">High-Risk Positions:</span>
            <span className="value warning">{riskMetrics.highRiskPositions}</span>
          </div>
        )}
      </div>
    </div>
  );
}