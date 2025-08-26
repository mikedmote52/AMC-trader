import React, { useState, useEffect } from 'react';
import { API_BASE } from '../config';

interface AuditModalProps {
  symbol: string;
  onClose: () => void;
}

interface AuditData {
  volume?: {
    score: number;
    rel_vol_30m: number;
    float: number;
  };
  short?: {
    score: number;
    si: number;
  };
  catalyst?: {
    score: number;
  };
  sentiment?: {
    score: number;
  };
  options?: {
    score: number;
    pcr: number;
    iv_pctl: number;
  };
  technicals?: {
    score: number;
    ema_cross: boolean;
    rsi: number;
    above_vwap: boolean;
    atr_pct: number;
  };
  sector?: {
    score: number;
    rs_20d: number;
    rs_5d: number;
    ema_20: number;
    ema_50: number;
    sector_etf: string;
  };
}

export default function AuditModal({ symbol, onClose }: AuditModalProps) {
  const [auditData, setAuditData] = useState<AuditData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAuditData = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${API_BASE}/discovery/audit/${symbol}`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const data = await response.json();
        setAuditData(data);
      } catch (err) {
        console.error('Failed to fetch audit data:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch audit data');
      } finally {
        setLoading(false);
      }
    };

    fetchAuditData();
  }, [symbol]);

  const formatPercent = (x?: number) => {
    if (x == null) return "—";
    return `${(x * 100).toFixed(1)}%`;
  };

  const formatNumber = (x?: number, decimals = 1) => {
    if (x == null) return "—";
    return x.toFixed(decimals);
  };

  const ScoreBar = ({ score, maxScore = 100 }: { score: number; maxScore?: number }) => {
    const percentage = Math.min((score / maxScore) * 100, 100);
    const color = percentage >= 80 ? 'bg-green-500' : 
                  percentage >= 60 ? 'bg-yellow-500' : 'bg-red-500';
    
    return (
      <div className="flex items-center gap-2">
        <div className="w-16 bg-slate-700 rounded-full h-2">
          <div 
            className={`h-2 rounded-full ${color}`}
            style={{ width: `${percentage}%` }}
          />
        </div>
        <span className="text-sm font-medium">{score.toFixed(0)}</span>
      </div>
    );
  };

  const AuditRow = ({ 
    title, 
    score, 
    children 
  }: { 
    title: string; 
    score: number; 
    children: React.ReactNode 
  }) => (
    <tr className="border-b border-slate-700">
      <td className="py-3 px-4 font-medium">{title}</td>
      <td className="py-3 px-4">
        <ScoreBar score={score} />
      </td>
      <td className="py-3 px-4 text-sm opacity-80">
        {children}
      </td>
    </tr>
  );

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-slate-800 p-6 rounded-xl max-w-2xl w-full mx-4">
          <div className="text-white text-center">Loading audit data for {symbol}...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-slate-800 p-6 rounded-xl max-w-2xl w-full mx-4 space-y-4">
          <div className="text-red-400">Error loading audit data: {error}</div>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-slate-800 p-6 rounded-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-white">Audit: {symbol}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-2xl"
          >
            ×
          </button>
        </div>

        <div className="bg-slate-900 rounded-lg overflow-hidden">
          <table className="w-full text-white">
            <thead className="bg-slate-700">
              <tr>
                <th className="py-3 px-4 text-left">Category</th>
                <th className="py-3 px-4 text-left">Score</th>
                <th className="py-3 px-4 text-left">Details</th>
              </tr>
            </thead>
            <tbody>
              {auditData?.volume && (
                <AuditRow title="Volume" score={auditData.volume.score}>
                  <div className="space-y-1">
                    <div>30m Rel Vol: {formatNumber(auditData.volume.rel_vol_30m)}x</div>
                    <div>Float: {formatNumber(auditData.volume.float / 1_000_000)}M</div>
                  </div>
                </AuditRow>
              )}
              
              {auditData?.short && (
                <AuditRow title="Short" score={auditData.short.score}>
                  <div>Short Interest: {formatPercent(auditData.short.si)}</div>
                </AuditRow>
              )}
              
              {auditData?.catalyst && (
                <AuditRow title="Catalyst" score={auditData.catalyst.score}>
                  <div>—</div>
                </AuditRow>
              )}
              
              {auditData?.sentiment && (
                <AuditRow title="Sentiment" score={auditData.sentiment.score}>
                  <div>—</div>
                </AuditRow>
              )}
              
              {auditData?.options && (
                <AuditRow title="Options" score={auditData.options.score}>
                  <div className="space-y-1">
                    <div>P/C Ratio: {formatNumber(auditData.options.pcr, 2)}</div>
                    <div>IV Percentile: {formatNumber(auditData.options.iv_pctl)}%</div>
                  </div>
                </AuditRow>
              )}
              
              {auditData?.technicals && (
                <AuditRow title="Technicals" score={auditData.technicals.score}>
                  <div className="space-y-1">
                    <div>EMA Cross: {auditData.technicals.ema_cross ? '✓' : '✗'}</div>
                    <div>RSI: {formatNumber(auditData.technicals.rsi)}</div>
                    <div>Above VWAP: {auditData.technicals.above_vwap ? '✓' : '✗'}</div>
                    <div>ATR: {formatPercent(auditData.technicals.atr_pct)}</div>
                  </div>
                </AuditRow>
              )}
              
              {auditData?.sector && (
                <AuditRow title="Sector" score={auditData.sector.score}>
                  <div className="space-y-1">
                    <div>ETF: {auditData.sector.sector_etf}</div>
                    <div>RS 20d: {formatPercent(auditData.sector.rs_20d)}</div>
                    <div>RS 5d: {formatPercent(auditData.sector.rs_5d)}</div>
                    <div>EMA 20: {formatNumber(auditData.sector.ema_20, 2)}</div>
                    <div>EMA 50: {formatNumber(auditData.sector.ema_50, 2)}</div>
                  </div>
                </AuditRow>
              )}
            </tbody>
          </table>
        </div>

        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}