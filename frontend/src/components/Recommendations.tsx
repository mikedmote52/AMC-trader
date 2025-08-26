import React, { useCallback } from 'react';
import { API_BASE } from '../config';
import { usePolling } from '../hooks/usePolling';

export function Recommendations() {
  const { data, error, isLoading } = usePolling<any>(`${API_BASE}/discovery/contenders`);
  
  // Handle both array and {items: [...]} response formats
  const items = Array.isArray(data) ? data : (data?.items || []);

  const handleBuy = useCallback(async (symbol: string) => {
    try {
      await fetch(`${API_BASE}/trades/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol,
          action: 'BUY',
          mode: 'live',
          order_type: 'market',
          time_in_force: 'day',
          notional_usd: 100
        })
      });
    } catch (error) {
      console.error('Buy failed:', error);
    }
  }, []);

  const formatPrice = (x?: number) => {
    if (x == null) return "—";
    return Math.abs(x) >= 1 ? x.toFixed(2) : x.toFixed(3);
  };

  const formatPercent = (x?: number) => {
    if (x == null) return "—";
    return `${(x * 100).toFixed(1)}%`;
  };

  const formatVolume = (vol?: number) => {
    if (!vol) return "—";
    return `$${Math.round(vol / 1_000_000)}M`;
  };

  if (isLoading && !items.length) {
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
      
      {items.length > 0 ? (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {items.map((item: any) => {
            const conf = Number.isFinite(item?.confidence) ? (item.confidence * 100).toFixed(1) + "%" :
                        Number.isFinite(item?.score) ? (item.score * 100).toFixed(1) + "%" : "—";
            
            return (
              <div key={item.symbol} className="bg-slate-800 rounded-2xl p-4 shadow-md">
                <div className="flex items-baseline justify-between mb-2">
                  <h3 className="text-xl font-semibold">{item.symbol}</h3>
                  <button 
                    className="bg-blue-500 hover:bg-blue-600 text-white px-3 py-1 rounded-lg"
                    onClick={() => handleBuy(item.symbol)}
                  >
                    Buy
                  </button>
                </div>
                
                <div className="text-sm opacity-80 mb-3">
                  {item.thesis || "No thesis available"}
                </div>
                
                <div className="grid grid-cols-3 gap-2 text-sm">
                  <div>
                    <span className="opacity-70">Confidence</span>
                    <div>{conf}</div>
                  </div>
                  <div>
                    <span className="opacity-70">Price</span>
                    <div>${formatPrice(item.price)}</div>
                  </div>
                  <div>
                    <span className="opacity-70">$ Vol</span>
                    <div>{formatVolume(item.dollar_vol)}</div>
                  </div>
                  <div>
                    <span className="opacity-70">5d RS</span>
                    <div>{formatPercent(item.rs_5d)}</div>
                  </div>
                  <div>
                    <span className="opacity-70">ATR%</span>
                    <div>{formatPercent(item.atr_pct)}</div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : !error && (
        <div className="opacity-70 italic">No recommendations available</div>
      )}
    </div>
  );
}