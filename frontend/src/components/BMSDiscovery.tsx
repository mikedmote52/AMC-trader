/**
 * BMS Discovery Component
 * Clean unified discovery system based on June-July winner patterns
 * Replaces: TopRecommendations, SqueezeMonitor, Recommendations
 */

import React, { useState, useEffect } from 'react';
import { getJSON } from '../lib/api';

interface BMSCandidate {
  symbol: string;
  bms_score: number;
  action: 'TRADE_READY' | 'MONITOR' | 'REJECT';
  price: number;
  volume_surge: number;
  dollar_volume?: number;
  momentum_1d?: number;
  atr_pct?: number;
  confidence?: 'HIGH' | 'MEDIUM' | 'LOW';
  risk_level?: 'LOW' | 'MEDIUM' | 'HIGH';
  thesis?: string;
  component_scores?: {
    volume_surge: number;
    price_momentum: number;
    volatility_expansion: number;
    risk_filter: number;
  };
}

interface BMSResponse {
  candidates: BMSCandidate[];
  count: number;
  timestamp: string;
  engine: string;
}

interface BMSDiscoveryProps {
  maxResults?: number;
  showOnlyTradeReady?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export const BMSDiscovery: React.FC<BMSDiscoveryProps> = ({
  maxResults = 20,
  showOnlyTradeReady = false,
  autoRefresh = true,
  refreshInterval = 30000 // 30 seconds
}) => {
  const [candidates, setCandidates] = useState<BMSCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<string>('');
  const [selectedCandidate, setSelectedCandidate] = useState<BMSCandidate | null>(null);
  const [showAuditModal, setShowAuditModal] = useState(false);

  const fetchCandidates = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const endpoint = showOnlyTradeReady 
        ? `/discovery/candidates/trade-ready?limit=${maxResults}`
        : `/discovery/candidates?limit=${maxResults}`;
      
      const response: BMSResponse = await getJSON(endpoint);
      setCandidates(response.candidates);
      setLastUpdate(new Date(response.timestamp).toLocaleTimeString());
      
    } catch (err) {
      console.error('Error fetching BMS candidates:', err);
      setError('Failed to load discovery candidates');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCandidates();
    
    if (autoRefresh) {
      const interval = setInterval(fetchCandidates, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [maxResults, showOnlyTradeReady, autoRefresh, refreshInterval]);

  const triggerDiscovery = async () => {
    try {
      setLoading(true);
      await getJSON(`/discovery/trigger?limit=${maxResults}`);
      await fetchCandidates();
    } catch (err) {
      console.error('Error triggering discovery:', err);
      setError('Failed to trigger discovery scan');
    }
  };

  const getScoreColor = (score: number): string => {
    if (score >= 75) return 'text-green-600 font-bold';
    if (score >= 60) return 'text-blue-600 font-semibold';
    return 'text-gray-600';
  };

  const getActionBadge = (action: string, confidence?: string): JSX.Element => {
    const baseClasses = 'px-2 py-1 rounded-full text-xs font-medium';
    
    if (action === 'TRADE_READY') {
      return (
        <span className={`${baseClasses} bg-green-100 text-green-800`}>
          🚀 TRADE READY
        </span>
      );
    } else if (action === 'MONITOR') {
      return (
        <span className={`${baseClasses} bg-blue-100 text-blue-800`}>
          👁️ MONITOR
        </span>
      );
    }
    return <span className={`${baseClasses} bg-gray-100 text-gray-800`}>REJECT</span>;
  };

  const showAuditDetails = async (candidate: BMSCandidate) => {
    setSelectedCandidate(candidate);
    setShowAuditModal(true);
  };

  if (loading && candidates.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-2 text-gray-600">Scanning for BMS opportunities...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <h3 className="text-red-800 font-medium">Discovery Error</h3>
        <p className="text-red-600">{error}</p>
        <button 
          onClick={fetchCandidates}
          className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">
            BMS Discovery System
          </h2>
          <p className="text-gray-600">
            Breakout Momentum Score • Based on June-July 2025 Winners
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <span className="text-sm text-gray-500">
            Last Update: {lastUpdate}
          </span>
          <button
            onClick={triggerDiscovery}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Scanning...' : 'Trigger Scan'}
          </button>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg border">
          <div className="text-2xl font-bold text-gray-900">{candidates.length}</div>
          <div className="text-gray-600">Total Candidates</div>
        </div>
        <div className="bg-white p-4 rounded-lg border">
          <div className="text-2xl font-bold text-green-600">
            {candidates.filter(c => c.action === 'TRADE_READY').length}
          </div>
          <div className="text-gray-600">Trade Ready</div>
        </div>
        <div className="bg-white p-4 rounded-lg border">
          <div className="text-2xl font-bold text-blue-600">
            {candidates.filter(c => c.action === 'MONITOR').length}
          </div>
          <div className="text-gray-600">Monitor</div>
        </div>
        <div className="bg-white p-4 rounded-lg border">
          <div className="text-2xl font-bold text-purple-600">
            {candidates.length > 0 
              ? Math.round(candidates.reduce((sum, c) => sum + c.bms_score, 0) / candidates.length)
              : 0
            }
          </div>
          <div className="text-gray-600">Avg BMS Score</div>
        </div>
      </div>

      {/* Candidates List */}
      <div className="space-y-3">
        {candidates.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No candidates found matching criteria
          </div>
        ) : (
          candidates.map((candidate, index) => (
            <div
              key={candidate.symbol}
              className="bg-white border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => showAuditDetails(candidate)}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <span className="text-xl font-bold text-gray-900">
                      #{index + 1} {candidate.symbol}
                    </span>
                    <span className={`text-lg ${getScoreColor(candidate.bms_score)}`}>
                      {candidate.bms_score.toFixed(1)}
                    </span>
                    {getActionBadge(candidate.action, candidate.confidence || 'MEDIUM')}
                    <span className="text-sm text-gray-500">
                      ${candidate.price.toFixed(2)}
                    </span>
                  </div>
                  
                  {candidate.thesis && <p className="text-gray-700 mb-3">{candidate.thesis}</p>}
                  
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">Volume Surge:</span>
                      <span className="ml-1 font-medium">{candidate.volume_surge.toFixed(1)}x</span>
                    </div>
                    {candidate.dollar_volume && (
                      <div>
                        <span className="text-gray-500">Dollar Vol:</span>
                        <span className="ml-1 font-medium">${(candidate.dollar_volume / 1000000).toFixed(0)}M</span>
                      </div>
                    )}
                    {candidate.momentum_1d !== undefined && (
                      <div>
                        <span className="text-gray-500">Momentum 1D:</span>
                        <span className={`ml-1 font-medium ${candidate.momentum_1d >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {candidate.momentum_1d.toFixed(1)}%
                        </span>
                      </div>
                    )}
                    {candidate.atr_pct !== undefined && (
                      <div>
                        <span className="text-gray-500">ATR:</span>
                        <span className="ml-1 font-medium">{candidate.atr_pct.toFixed(1)}%</span>
                      </div>
                    )}
                    {candidate.risk_level && (
                      <div>
                        <span className="text-gray-500">Risk:</span>
                        <span className={`ml-1 font-medium ${
                          candidate.risk_level === 'LOW' ? 'text-green-600' :
                          candidate.risk_level === 'MEDIUM' ? 'text-yellow-600' : 'text-red-600'
                        }`}>
                          {candidate.risk_level}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="ml-4 text-right">
                  <button className="px-3 py-1 bg-blue-100 text-blue-800 rounded text-sm hover:bg-blue-200">
                    Details
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Audit Modal */}
      {showAuditModal && selectedCandidate && (
        <BMSAuditModal
          candidate={selectedCandidate}
          onClose={() => setShowAuditModal(false)}
        />
      )}
    </div>
  );
};

// Audit Modal Component
interface BMSAuditModalProps {
  candidate: BMSCandidate;
  onClose: () => void;
}

const BMSAuditModal: React.FC<BMSAuditModalProps> = ({ candidate, onClose }) => {
  const [auditData, setAuditData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAuditData = async () => {
      try {
        const data = await getJSON(`/discovery/audit/${candidate.symbol}`);
        setAuditData(data);
      } catch (err) {
        console.error('Error fetching audit data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchAuditData();
  }, [candidate.symbol]);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full m-4 max-h-[80vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-2xl font-bold">{candidate.symbol} - BMS Analysis</h3>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 text-xl"
            >
              ✕
            </button>
          </div>

          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
              <p className="mt-2">Loading detailed analysis...</p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Component Scores Breakdown */}
              <div>
                <h4 className="text-lg font-semibold mb-3">BMS Component Breakdown</h4>
                <div className="grid grid-cols-2 gap-4">
                  {Object.entries(candidate.component_scores).map(([key, score]) => (
                    <div key={key} className="bg-gray-50 p-3 rounded">
                      <div className="flex justify-between items-center">
                        <span className="text-sm font-medium capitalize">
                          {key.replace('_', ' ')}
                        </span>
                        <span className="font-bold">{score.toFixed(1)}/100</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full"
                          style={{ width: `${score}%` }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Market Data */}
              {auditData && (
                <div>
                  <h4 className="text-lg font-semibold mb-3">Market Data</h4>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-gray-50 p-3 rounded">
                      <div className="text-sm text-gray-600">Price</div>
                      <div className="text-lg font-bold">${candidate.price.toFixed(2)}</div>
                    </div>
                    <div className="bg-gray-50 p-3 rounded">
                      <div className="text-sm text-gray-600">Volume Surge</div>
                      <div className="text-lg font-bold">{candidate.volume_surge.toFixed(1)}x</div>
                    </div>
                    <div className="bg-gray-50 p-3 rounded">
                      <div className="text-sm text-gray-600">ATR %</div>
                      <div className="text-lg font-bold">{candidate.atr_pct.toFixed(1)}%</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Thesis */}
              <div>
                <h4 className="text-lg font-semibold mb-2">Investment Thesis</h4>
                <p className="bg-gray-50 p-3 rounded">{candidate.thesis}</p>
              </div>

              {/* Action Buttons */}
              <div className="flex space-x-3 pt-4 border-t">
                <button
                  onClick={onClose}
                  className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
                >
                  Close
                </button>
                {candidate.action === 'TRADE_READY' && (
                  <button className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
                    Add to Portfolio
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default BMSDiscovery;