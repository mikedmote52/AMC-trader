import { usePolling } from '../hooks/usePolling';
import { API_ENDPOINTS } from '../config/api';
import type { Holding } from '../types/api';
import './Holdings.css';

export function Holdings() {
  const { data: holdings, error, isLoading } = usePolling<Holding[]>(API_ENDPOINTS.holdings);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatPercent = (percent: number) => {
    return `${percent >= 0 ? '+' : ''}${(percent * 100).toFixed(2)}%`;
  };

  if (isLoading && !holdings) {
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
      
      {holdings && holdings.length > 0 ? (
        <div className="holdings-grid">
          {holdings.map((holding) => (
            <div key={holding.symbol} className="holding-card">
              <div className="holding-header">
                <span className="symbol">{holding.symbol}</span>
                <span className="qty">{holding.qty} shares</span>
              </div>
              
              <div className="holding-details">
                <div className="price-info">
                  <span className="current-price">{formatCurrency(holding.current_price)}</span>
                  <span className="avg-price">Avg: {formatCurrency(holding.avg_entry_price)}</span>
                </div>
                
                <div className="value-info">
                  <span className="market-value">{formatCurrency(holding.market_value)}</span>
                  <span className={`unrealized-pl ${holding.unrealized_pl >= 0 ? 'positive' : 'negative'}`}>
                    {formatCurrency(holding.unrealized_pl)} ({formatPercent(holding.unrealized_plpc)})
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : !error && (
        <div className="no-holdings">No holdings found</div>
      )}
    </div>
  );
}