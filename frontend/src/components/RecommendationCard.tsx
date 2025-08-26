import React from 'react';

interface RecommendationCardProps {
  item: any;
  onOpenTradeModal: (candidate: any) => void;
}

export default function RecommendationCard({ item, onOpenTradeModal }: RecommendationCardProps) {
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

  const formatRelativeVolume = (relVol?: number) => {
    if (!relVol) return "—";
    return `${relVol.toFixed(1)}x`;
  };

  // Calculate integer score 0..100
  const integerScore = item.score ? Math.round(item.score * 100) : 0;
  
  // Calculate confidence percent
  const confidencePercent = Number.isFinite(item?.confidence) 
    ? (item.confidence * 100).toFixed(1) + "%" 
    : "—";

  return (
    <div className="bg-slate-800 rounded-2xl p-4 shadow-md">
      <div className="flex items-baseline justify-between mb-2">
        <div className="flex items-baseline gap-3">
          <h3 className="text-xl font-semibold">{item.symbol}</h3>
          <span className="text-lg font-bold text-green-400">{integerScore}</span>
          <span className="text-sm text-blue-400">{confidencePercent}</span>
        </div>
        <button 
          className="bg-blue-500 hover:bg-blue-600 text-white px-3 py-1 rounded-lg"
          onClick={() => onOpenTradeModal(item)}
        >
          Buy
        </button>
      </div>
      
      <div className="text-sm opacity-80 mb-3">
        {item.thesis || "No thesis available"}
      </div>
      
      <div className="grid grid-cols-3 gap-2 text-sm mb-3">
        <div>
          <span className="opacity-70">Price</span>
          <div>${formatPrice(item.price)}</div>
        </div>
        <div>
          <span className="opacity-70">Target</span>
          <div>${formatPrice(item.take_profit_price)}</div>
        </div>
        <div>
          <span className="opacity-70">Stop</span>
          <div>${formatPrice(item.stop_price)}</div>
        </div>
        <div>
          <span className="opacity-70">Rel Vol</span>
          <div>{formatRelativeVolume(item.relative_volume)}</div>
        </div>
        <div>
          <span className="opacity-70">ATR%</span>
          <div>{formatPercent(item.atr_pct)}</div>
        </div>
        <div>
          <span className="opacity-70">$ Vol</span>
          <div>{formatVolume(item.dollar_vol)}</div>
        </div>
      </div>
    </div>
  );
}