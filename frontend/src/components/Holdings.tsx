import { useState, useEffect } from 'react';
import { usePolling } from '../hooks/usePolling';
import { API_ENDPOINTS } from '../config/api';
import TradeModal from './TradeModal';
import './Holdings.css';

export function Holdings() {
  const { data: holdingsResponse, error, isLoading, refresh } = usePolling<any>(API_ENDPOINTS.holdings);
  const [showTradeModal, setShowTradeModal] = useState(false);
  const [selectedHolding, setSelectedHolding] = useState<any>(null);
  const [tradeAction, setTradeAction] = useState<'BUY' | 'SELL'>('BUY');
  const [tradeQty, setTradeQty] = useState<number | undefined>(undefined);
  
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

  const handleAdjustPosition = (holding: any, action: 'BUY' | 'SELL', qty?: number) => {
    setSelectedHolding(holding);
    setTradeAction(action);
    setTradeQty(qty);
    setShowTradeModal(true);
  };

  const handleCloseTradeModal = () => {
    setShowTradeModal(false);
    setSelectedHolding(null);
    setTradeAction('BUY');
    setTradeQty(undefined);
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
            // Use backend fields directly - no client-side derivations
            const symbol = holding.symbol || "—";
            const quantity = holding.quantity || 0;
            const avgPrice = holding.avg_price || 0;
            const lastPrice = holding.last_price || 0;
            const marketValue = holding.market_value || 0;
            const unrealizedPL = holding.unrealized_pl || 0;
            const unrealizedPLPct = holding.unrealized_pl_pct || 0;
            const suggestion = holding.suggestion;
            const thesis = holding.thesis;
            const confidence = holding.confidence;
            const score = holding.score;
            const targetPrice = holding.target_price;
            const stopPrice = holding.stop_price;
            
            return (
              <div key={symbol} className="holding-card">
                <div className="holding-header">
                  <span className="symbol">{symbol}</span>
                  <span className="qty">{quantity} shares</span>
                  <div className="flex gap-2">
                    {score !== undefined && (
                      <span className="score text-sm text-green-400">
                        {Math.round(score * 100)}
                      </span>
                    )}
                    {confidence !== undefined && (
                      <span className="confidence text-sm text-blue-400">
                        {(confidence * 100).toFixed(1)}%
                      </span>
                    )}
                  </div>
                </div>
                
                <div className="holding-details">
                  <div className="price-info">
                    <span className="current-price">{formatCurrency(lastPrice)}</span>
                    <span className="avg-price">Avg: {formatCurrency(avgPrice)}</span>
                  </div>
                  
                  <div className="value-info">
                    <span className="market-value">Value: {formatCurrency(marketValue)}</span>
                    <span className={`unrealized-pl ${unrealizedPL >= 0 ? 'positive' : 'negative'}`}>
                      {formatCurrency(unrealizedPL)} ({formatPercent(unrealizedPLPct)})
                    </span>
                  </div>
                  
                  {suggestion && (
                    <div className="suggestion">
                      <strong>Suggestion:</strong> {suggestion}
                    </div>
                  )}
                  
                  {thesis && (
                    <div className="thesis text-sm opacity-80 mt-2">
                      {thesis}
                    </div>
                  )}
                  
                  {/* Show targets if available */}
                  {(targetPrice || stopPrice) && (
                    <div className="targets border-t border-gray-700 pt-2 mt-2">
                      <div className="text-xs opacity-70 mb-1">Targets</div>
                      <div className="grid grid-cols-2 gap-3 text-sm">
                        {targetPrice && (
                          <div>
                            <span className="opacity-70">Target</span>
                            <div className="text-green-400">{formatCurrency(targetPrice)}</div>
                          </div>
                        )}
                        {stopPrice && (
                          <div>
                            <span className="opacity-70">Stop</span>
                            <div className="text-red-400">{formatCurrency(stopPrice)}</div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  
                  <div className="actions mt-3">
                    <div className="flex gap-2">
                      <button
                        className="px-3 py-1 text-sm bg-green-600 hover:bg-green-700 text-white rounded"
                        onClick={() => handleAdjustPosition(holding, 'BUY')}
                      >
                        Buy More
                      </button>
                      <button
                        className="px-3 py-1 text-sm bg-red-600 hover:bg-red-700 text-white rounded"
                        onClick={() => handleAdjustPosition(holding, 'SELL', quantity)}
                      >
                        Sell All
                      </button>
                      <button
                        className="px-3 py-1 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded"
                        onClick={() => handleAdjustPosition(holding, 'SELL')}
                      >
                        Adjust
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : !error && (
        <div className="no-holdings">No holdings found</div>
      )}

      {showTradeModal && selectedHolding && (
        <TradeModal
          symbol={selectedHolding.symbol}
          action={tradeAction}
          qty={tradeQty}
          onClose={handleCloseTradeModal}
        />
      )}
    </div>
  );
}