import React, { useState } from 'react';
import AuditModal from './AuditModal';

interface RecommendationCardProps {
  item: any;
  onOpenTradeModal: (candidate: any) => void;
}

// Environment variables for ATR calculations (fallback to reasonable defaults)
const R_MULT = parseFloat(process.env.REACT_APP_R_MULT || '2.0');
const MIN_STOP_PCT = parseFloat(process.env.REACT_APP_MIN_STOP_PCT || '0.05');
const ATR_STOP_MULT = parseFloat(process.env.REACT_APP_ATR_STOP_MULT || '1.0');

export default function RecommendationCard({ item, onOpenTradeModal }: RecommendationCardProps) {
  const [showAuditModal, setShowAuditModal] = useState(false);

  const formatPrice = (x?: number) => {
    if (x == null) return "—";
    return Math.abs(x) >= 1 ? x.toFixed(2) : x.toFixed(3);
  };

  const formatPercent = (x?: number) => {
    if (x == null) return "—";
    return `${(x * 100).toFixed(1)}%`;
  };

  const formatRelativeVolume = (relVol?: number) => {
    if (!relVol) return "—";
    return `${relVol.toFixed(1)}x`;
  };

  // Calculate integer score 0..100
  const integerScore = item.score ? Math.round(item.score * 100) : 0;

  // Calculate ATR-based targets if not provided by backend
  const lastPrice = item.last_price || item.price || 0;
  const atrAbs = item.atr_abs || (lastPrice * (item.atr_pct || 0));
  
  const targetPrice = item.target_price || (lastPrice > 0 && atrAbs > 0 
    ? lastPrice + R_MULT * atrAbs 
    : null);
  
  const stopPrice = item.stop_price || (lastPrice > 0 && atrAbs > 0
    ? Math.max(lastPrice * (1 - MIN_STOP_PCT), lastPrice - ATR_STOP_MULT * atrAbs)
    : null);

  // Prepare enhanced item with calculated targets for trade modal
  const enhancedItem = {
    ...item,
    target_price: targetPrice,
    stop_price: stopPrice
  };

  return (
    <>
      <div className="bg-slate-800 rounded-2xl p-4 shadow-md">
        <div className="flex items-start justify-between mb-2">
          <div className="flex-1">
            <div className="flex items-baseline gap-2 mb-1">
              <h3 className="text-xl font-semibold">{item.symbol}</h3>
              <span className="text-lg font-bold text-green-400">{integerScore}</span>
              {/* Sector pill with tooltip */}
              <div 
                className="px-2 py-0.5 bg-purple-600 text-white text-xs rounded-full cursor-help"
                title={`${item.sector_etf || 'N/A'} • RS20: ${formatPercent(item.rs_20d)} • RS5d: ${formatPercent(item.rs_5d)}`}
              >
                {item.sector || "—"}
              </div>
            </div>
            
            <div className="text-sm opacity-80 mb-3">
              {item.thesis || "No thesis available"}
            </div>
          </div>
          
          <div className="flex flex-col gap-1">
            <button 
              className="bg-blue-500 hover:bg-blue-600 text-white px-3 py-1 rounded-lg text-sm"
              onClick={() => onOpenTradeModal(enhancedItem)}
            >
              Buy
            </button>
            <button 
              className="bg-gray-600 hover:bg-gray-700 text-white px-3 py-1 rounded-lg text-xs"
              onClick={() => setShowAuditModal(true)}
            >
              Details
            </button>
          </div>
        </div>
        
        {/* Compact metrics: rel_vol_30m and atr_pct */}
        <div className="grid grid-cols-2 gap-3 text-sm mb-3">
          <div>
            <span className="opacity-70">30m Vol</span>
            <div>{formatRelativeVolume(item.rel_vol_30m)}</div>
          </div>
          <div>
            <span className="opacity-70">ATR%</span>
            <div>{formatPercent(item.atr_pct)}</div>
          </div>
        </div>
        
        {/* Projected targets */}
        {(targetPrice || stopPrice) && (
          <div className="border-t border-slate-700 pt-2 mt-2">
            <div className="text-xs opacity-70 mb-1">Projected</div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="opacity-70">Target</span>
                <div className="text-green-400">${formatPrice(targetPrice)}</div>
              </div>
              <div>
                <span className="opacity-70">Stop</span>
                <div className="text-red-400">${formatPrice(stopPrice)}</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {showAuditModal && (
        <AuditModal
          symbol={item.symbol}
          onClose={() => setShowAuditModal(false)}
        />
      )}
    </>
  );
}