import { useState, useEffect } from 'react';
import { usePolling } from '../hooks/usePolling';
import { API_ENDPOINTS } from '../config/api';
import { API_BASE } from '../config';
import TradeModal from './TradeModal';
import './Holdings.css';

export function Holdings() {
  const { data: holdingsResponse, error, isLoading, refresh } = usePolling<any>(API_ENDPOINTS.holdings);
  const { data: contendersData } = usePolling<any>(`${API_BASE}/discovery/contenders`, 15000);
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

  // Score pill styling based on thresholds
  const getScorePillClass = (score: number) => {
    if (score >= 75) return 'bg-green-600 text-white';
    if (score >= 70) return 'bg-yellow-600 text-white';
    return 'bg-gray-600 text-white';
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
  
  // Extract contenders for score matching
  const contenders = Array.isArray(contendersData) ? contendersData : (contendersData?.items || []);
  const contendersBySymbol = new Map(contenders.map((c: any) => [c.symbol, c]));

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
            // Display backend fields verbatim as specified
            const symbol = holding.symbol || "—";
            const qty = holding.qty;
            const lastPrice = holding.last_price;
            const marketValue = holding.market_value;
            const avgEntryPrice = holding.avg_entry_price;
            const unrealizedPL = holding.unrealized_pl;
            const unrealizedPLPct = holding.unrealized_pl_pct;
            const thesis = holding.thesis;
            const suggestion = holding.suggestion;
            
            // Check if this holding appears in contenders for score
            const contender = contendersBySymbol.get(symbol);
            const contenderScore = contender?.score;
            
            return (
              <div key={symbol} className="holding-card">
                <div className="holding-header">
                  <span className="symbol">{symbol}</span>
                  <span className="qty">{qty} shares</span>
                  <div className="flex gap-2">
                    {contenderScore !== undefined && (
                      <div className={`px-2 py-0.5 text-xs rounded-full ${getScorePillClass(Math.round(contenderScore))}`}>
                        Score {Math.round(contenderScore)}
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="holding-details">
                  <div className="price-info">
                    <span className="current-price">{formatCurrency(lastPrice)}</span>
                    <span className="avg-price">Avg: {formatCurrency(avgEntryPrice)}</span>
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
                        onClick={() => handleAdjustPosition(holding, 'SELL', qty)}
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