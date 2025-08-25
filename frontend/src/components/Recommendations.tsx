import { usePolling } from '../hooks/usePolling';
import { API_ENDPOINTS } from '../config/api';
import type { Recommendation } from '../types/api';
import './Recommendations.css';

export function Recommendations() {
  const { data: recommendations, error, isLoading } = usePolling<Recommendation[]>(API_ENDPOINTS.recommendations);

  const getActionColor = (action: Recommendation['action']) => {
    switch (action) {
      case 'BUY_MORE': return 'green';
      case 'SELL': return 'red';
      case 'HOLD': return 'yellow';
      default: return 'gray';
    }
  };

  const getRiskColor = (risk: Recommendation['risk_level']) => {
    switch (risk) {
      case 'LOW': return 'green';
      case 'MEDIUM': return 'yellow';
      case 'HIGH': return 'red';
      default: return 'gray';
    }
  };

  const formatCurrency = (amount?: number) => {
    if (amount === undefined) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  if (isLoading && !recommendations) {
    return (
      <div className="recommendations">
        <h2>Recommendations</h2>
        <div className="loading">Loading recommendations...</div>
      </div>
    );
  }

  return (
    <div className="recommendations">
      <h2>Recommendations</h2>
      
      {error && (
        <div className="error-banner">
          ❌ Failed to fetch recommendations: {error.message}
        </div>
      )}
      
      {recommendations && recommendations.length > 0 ? (
        <div className="recommendations-grid">
          {recommendations.map((rec, index) => (
            <div key={`${rec.symbol}-${index}`} className="recommendation-card">
              <div className="recommendation-header">
                <span className="symbol">{rec.symbol}</span>
                <div className="badges">
                  <span className={`action-badge ${getActionColor(rec.action)}`}>
                    {rec.action}
                  </span>
                  <span className={`risk-badge ${getRiskColor(rec.risk_level)}`}>
                    {rec.risk_level}
                  </span>
                </div>
              </div>
              
              <div className="recommendation-metrics">
                <div className="metric">
                  <span className="label">Confidence:</span>
                  <span className="value">{(rec.confidence * 100).toFixed(1)}%</span>
                </div>
                {rec.vigl_score && (
                  <div className="metric">
                    <span className="label">VIGL Score:</span>
                    <span className="value">{rec.vigl_score.toFixed(2)}</span>
                  </div>
                )}
                {rec.price_target && (
                  <div className="metric">
                    <span className="label">Target:</span>
                    <span className="value">{formatCurrency(rec.price_target)}</span>
                  </div>
                )}
              </div>
              
              <div className="thesis">
                <p>{rec.thesis}</p>
              </div>
            </div>
          ))}
        </div>
      ) : !error && (
        <div className="no-recommendations">No recommendations available</div>
      )}
    </div>
  );
}