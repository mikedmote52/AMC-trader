import { usePolling } from '../hooks/usePolling';
import { API_ENDPOINTS } from '../config/api';
import { useEffect } from 'react';
import './Holdings.css';

export function Holdings() {
  const { data: holdingsResponse, error, isLoading, refresh } = usePolling<any>(API_ENDPOINTS.holdings);
  
  // Listen for holdings refresh events from trade executions
  useEffect(() => {
    const handleRefresh = () => {
      refresh();
    };
    
    window.addEventListener('holdingsRefresh', handleRefresh);
    return () => window.removeEventListener('holdingsRefresh', handleRefresh);
  }, [refresh]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatPercent = (percent: number) => {
    return `${percent >= 0 ? '+' : ''}${(percent * 100).toFixed(2)}%`;
  };

  // Extract positions from API response: handle various response structures
  const holdings = holdingsResponse?.data?.positions || holdingsResponse?.positions || holdingsResponse || [];

  if (isLoading && !holdingsResponse) {
    return (
      <div className="holdings">
        <h2>Holdings</h2>
        <div className="loading">Loading holdings...</div>
      </div>
    );
  }

  return (
    <div className="holdings">
      <h2>Holdings</h2>
      
      {error && (
        <div className="error-banner">
          ❌ Failed to fetch holdings: {error.message}
        </div>
      )}
      
      {Array.isArray(holdings) && holdings.length > 0 ? (
        <div className="holdings-grid">
          {holdings.map((holding) => {
            // Use canonical keys with fallbacks to _raw fields
            const symbol = holding.symbol || holding._raw?.symbol || "—";
            const quantity = holding.quantity || holding.qty || holding._raw?.qty || 0;
            const avgPrice = holding.avg_price || holding.avg_entry_price || holding._raw?.avg_entry_price || 0;
            const lastPrice = holding.last_price || holding.current_price || holding.price || holding._raw?.last_price || holding._raw?.current_price || 0;
            const marketValue = holding.market_value || holding._raw?.market_value || 0;
            const unrealizedPL = holding.unrealized_pl || holding._raw?.unrealized_pl || 0;
            const unrealizedPLPC = holding.unrealized_plpc || holding._raw?.unrealized_plpc || 0;
            const suggestion = holding.suggestion || holding._raw?.suggestion;
            const thesis = holding.thesis || holding._raw?.thesis;
            
            return (
              <div key={symbol} className="holding-card">
                <div className="holding-header">
                  <span className="symbol">{symbol}</span>
                  <span className="qty">{quantity} shares</span>
                </div>
                
                <div className="holding-details">
                  <div className="price-info">
                    <span className="current-price">{formatCurrency(lastPrice)}</span>
                    <span className="avg-price">Avg: {formatCurrency(avgPrice)}</span>
                  </div>
                  
                  <div className="value-info">
                    <span className="market-value">Value: {formatCurrency(marketValue)}</span>
                    <span className={`unrealized-pl ${unrealizedPL >= 0 ? 'positive' : 'negative'}`}>
                      {formatCurrency(unrealizedPL)} ({formatPercent(unrealizedPLPC)})
                    </span>
                  </div>
                  
                  {suggestion && (
                    <div className="suggestion">
                      <strong>Suggestion:</strong> {suggestion}
                    </div>
                  )}
                  
                  {thesis && (
                    <div className="thesis">
                      {thesis}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : !error && (
        <div className="no-holdings">No holdings found</div>
      )}
    </div>
  );
}