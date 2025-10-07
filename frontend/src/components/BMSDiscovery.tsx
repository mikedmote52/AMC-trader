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
  const [showTradeModal, setShowTradeModal] = useState(false);
  const [tradingCandidate, setTradingCandidate] = useState<BMSCandidate | null>(null);

  const fetchCandidates = async () => {
    try {
      setLoading(true);
      setError(null);

      // V2 Explosive Stock Discovery - 11,644 stocks scanned in 1-2 seconds
      const endpoint = `/discovery/contenders-v2?limit=${maxResults}`;

      const response = await getJSON<any>(endpoint);

      // V2 returns simple format: { candidates: [...], count: N, stats: {...} }
      if (response.candidates && Array.isArray(response.candidates)) {
        // Map V2 data format to component's expected format
        const mappedCandidates = response.candidates.map((c: any) => ({
          symbol: c.symbol,
          price: c.price,
          bms_score: c.explosion_probability, // V2 explosion_probability → bms_score
          action: c.explosion_probability >= 60 ? 'TRADE_READY' : 'MONITOR',
          confidence: c.explosion_probability >= 65 ? 'HIGH' : 'MEDIUM',
          volume_surge: c.rvol, // V2 rvol → volume_surge
          dollar_volume: c.price * c.volume,
          momentum_1d: c.change_pct,
          thesis: `Explosive potential: ${c.explosion_probability.toFixed(1)}% probability, ${c.rvol.toFixed(1)}x volume surge`,
          ...c // Include all original V2 fields
        }));

        setCandidates(mappedCandidates);
        setLastUpdate(new Date().toLocaleTimeString());

        // Log V2 performance stats
        if (response.stats) {
          console.log('V2 Discovery Stats:', response.stats);
        }
      } else {
        console.warn('Unexpected V2 response format:', response);
        setError('Received unexpected response format. Please refresh the page.');
      }

    } catch (err) {
      console.error('Error fetching V2 explosive stocks:', err);
      setError('Failed to load explosive stocks. The system may be starting up.');
    } finally {
      setLoading(false);
    }
  };

  const pollForResults = async (taskId: string, maxAttempts = 12) => {
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds
        
        const pollResponse = await getJSON<any>(`/discovery/candidates?task=${taskId}`);
        
        if (pollResponse.status === 'ready') {
          setCandidates(pollResponse.candidates || []);
          setLastUpdate(new Date().toLocaleTimeString());
          setError(null);
          return;
          
        } else if (pollResponse.status === 'failed') {
          setError('Discovery failed. Please try again.');
          return;
          
        } else {
          // Still processing
          const progress = pollResponse.progress || 0;
          setError(`Discovery in progress... ${progress}% complete (attempt ${attempt}/${maxAttempts})`);
        }
        
      } catch (err) {
        console.error(`Polling attempt ${attempt} failed:`, err);
        setError(`Discovery in progress... (attempt ${attempt}/${maxAttempts})`);
      }
    }
    
    // Max attempts reached
    setError('Discovery is taking longer than expected. Please refresh the page.');
  };

  useEffect(() => {
    fetchCandidates();
    
    if (autoRefresh) {
      const interval = setInterval(fetchCandidates, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [maxResults, showOnlyTradeReady, autoRefresh, refreshInterval]);

  const triggerDiscovery = async () => {
    // V2 returns results immediately - just refresh candidates
    await fetchCandidates();
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
            🚀 V2 Explosive Stock Discovery (11,644 stocks scanned)
          </h2>
          <p className="text-gray-600">
            Real-time VIGL Pattern Detection • 50x Faster Than V1
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
              style={{
                background: 'white',
                border: '2px solid #e5e7eb',
                borderRadius: '12px',
                padding: '24px',
                marginBottom: '16px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                transition: 'box-shadow 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.1)';
              }}
            >
              {/* Header Row */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <span style={{ fontSize: '32px', fontWeight: '900', color: '#111' }}>
                    {candidate.symbol}
                  </span>
                  <span style={{ fontSize: '24px', fontWeight: 'bold', color: '#6b7280' }}>
                    ${candidate.price.toFixed(2)}
                  </span>
                  {getActionBadge(candidate.action, candidate.confidence || 'MEDIUM')}
                </div>
                <span style={{ fontSize: '14px', fontWeight: '500', color: '#9ca3af' }}>#{index + 1}</span>
              </div>

              {/* Key Metrics - Big & Bold */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '20px', marginBottom: '20px' }}>
                <div style={{
                  textAlign: 'center',
                  background: 'linear-gradient(to bottom right, #f0fdf4, #dcfce7)',
                  borderRadius: '8px',
                  padding: '16px'
                }}>
                  <div style={{ fontSize: '11px', fontWeight: '600', color: '#15803d', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>
                    Explosion Probability
                  </div>
                  <div style={{ fontSize: '36px', fontWeight: '900', color: '#16a34a' }}>
                    {candidate.bms_score.toFixed(1)}%
                  </div>
                </div>

                <div style={{
                  textAlign: 'center',
                  background: 'linear-gradient(to bottom right, #eff6ff, #dbeafe)',
                  borderRadius: '8px',
                  padding: '16px'
                }}>
                  <div style={{ fontSize: '11px', fontWeight: '600', color: '#1d4ed8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>
                    Volume Surge
                  </div>
                  <div style={{ fontSize: '36px', fontWeight: '900', color: '#2563eb' }}>
                    {candidate.volume_surge.toFixed(1)}x
                  </div>
                </div>

                <div style={{
                  textAlign: 'center',
                  background: 'linear-gradient(to bottom right, #faf5ff, #f3e8ff)',
                  borderRadius: '8px',
                  padding: '16px'
                }}>
                  <div style={{ fontSize: '11px', fontWeight: '600', color: '#7c3aed', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>
                    Price Change
                  </div>
                  <div style={{
                    fontSize: '36px',
                    fontWeight: '900',
                    color: candidate.momentum_1d >= 0 ? '#16a34a' : '#dc2626'
                  }}>
                    {candidate.momentum_1d >= 0 ? '+' : ''}{candidate.momentum_1d.toFixed(1)}%
                  </div>
                </div>
              </div>

              {/* Thesis */}
              {candidate.thesis && (
                <div style={{ background: '#f9fafb', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
                  <p style={{ color: '#374151', fontSize: '14px', lineHeight: '1.6', margin: 0 }}>{candidate.thesis}</p>
                </div>
              )}

              {/* Secondary Metrics */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
                {candidate.dollar_volume && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#f9fafb', borderRadius: '6px', padding: '8px 12px' }}>
                    <span style={{ color: '#4b5563', fontWeight: '500', fontSize: '14px' }}>Dollar Volume</span>
                    <span style={{ color: '#111', fontWeight: 'bold', fontSize: '14px' }}>
                      ${(candidate.dollar_volume / 1000000).toFixed(1)}M
                    </span>
                  </div>
                )}
                {candidate.volume && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#f9fafb', borderRadius: '6px', padding: '8px 12px' }}>
                    <span style={{ color: '#4b5563', fontWeight: '500', fontSize: '14px' }}>Volume</span>
                    <span style={{ color: '#111', fontWeight: 'bold', fontSize: '14px' }}>
                      {(candidate.volume / 1000000).toFixed(1)}M
                    </span>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: '12px', paddingTop: '16px', borderTop: '1px solid #e5e7eb' }}>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setTradingCandidate(candidate);
                    setShowTradeModal(true);
                  }}
                  style={{
                    flex: 2,
                    padding: '14px',
                    fontSize: '16px',
                    fontWeight: '700',
                    border: 'none',
                    borderRadius: '8px',
                    background: candidate.action === 'TRADE_READY' ? '#16a34a' : '#3b82f6',
                    color: 'white',
                    cursor: 'pointer',
                    transition: 'transform 0.1s',
                    ':hover': { transform: 'scale(1.02)' }
                  }}
                >
                  🚀 Buy Now
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    showAuditDetails(candidate);
                  }}
                  style={{
                    flex: 1,
                    padding: '14px',
                    fontSize: '14px',
                    fontWeight: '600',
                    border: '2px solid #e5e7eb',
                    borderRadius: '8px',
                    background: 'white',
                    color: '#6b7280',
                    cursor: 'pointer'
                  }}
                >
                  Details
                </button>
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

      {/* Trade Modal */}
      {showTradeModal && tradingCandidate && (
        <TradeModal
          candidate={tradingCandidate}
          onClose={() => {
            setShowTradeModal(false);
            setTradingCandidate(null);
          }}
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
                  {candidate.component_scores && Object.entries(candidate.component_scores).map(([key, score]) => (
                    <div key={key} className="bg-gray-50 p-3 rounded">
                      <div className="flex justify-between items-center">
                        <span className="text-sm font-medium capitalize">
                          {key.replace('_', ' ')}
                        </span>
                        <span className="font-bold">{(score as number).toFixed(1)}/100</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full"
                          style={{ width: `${score}%` }}
                        ></div>
                      </div>
                    </div>
                  ))}
                  {!candidate.component_scores && (
                    <div className="col-span-2 text-center text-gray-500 py-4">
                      Component scores not available
                    </div>
                  )}
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
                      <div className="text-lg font-bold">{candidate.atr_pct?.toFixed(1) || 'N/A'}%</div>
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

// Trade Modal Component
interface TradeModalProps {
  candidate: BMSCandidate;
  onClose: () => void;
}

const TradeModal: React.FC<TradeModalProps> = ({ candidate, onClose }) => {
  const [dollarAmount, setDollarAmount] = useState('100');
  const [stopLossPct, setStopLossPct] = useState(0);
  const [takeProfitPct, setTakeProfitPct] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<{success: boolean, message: string} | null>(null);

  // Calculate smart stop-loss based on stock characteristics
  useEffect(() => {
    // Stop-loss based on explosion probability and RVOL
    // High explosion prob + high RVOL = tighter stop (less risky)
    // Low explosion prob + high RVOL = wider stop (more volatile)

    const explosionProb = candidate.bms_score || 50;
    const rvol = candidate.volume_surge || 1.5;

    // Base stop-loss: 5-15%
    // Lower explosion prob = wider stop (more risk)
    // Higher RVOL = tighter stop (momentum stock, move fast)
    let baseStop = 10; // 10% default

    if (explosionProb >= 70) {
      baseStop = 5; // Tight stop for high-confidence trades
    } else if (explosionProb >= 60) {
      baseStop = 7; // Medium stop
    } else {
      baseStop = 10; // Wider stop for lower confidence
    }

    // Adjust for RVOL (high volume = tighter stops)
    if (rvol >= 10) {
      baseStop *= 0.8; // 20% tighter
    } else if (rvol >= 5) {
      baseStop *= 0.9; // 10% tighter
    }

    setStopLossPct(Math.round(baseStop * 10) / 10); // Round to 1 decimal

    // Take profit: 2x the stop-loss (risk/reward ratio of 1:2)
    setTakeProfitPct(Math.round(baseStop * 2 * 10) / 10);
  }, [candidate]);

  const handleBuy = async () => {
    setIsSubmitting(true);
    setResult(null);

    try {
      const amount = parseFloat(dollarAmount);
      if (isNaN(amount) || amount <= 0) {
        setResult({success: false, message: 'Invalid dollar amount'});
        setIsSubmitting(false);
        return;
      }

      const response = await fetch(
        `${window.location.hostname === 'localhost' ? '/api' : 'https://amc-trader.onrender.com'}/trades/execute`,
        {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            symbol: candidate.symbol,
            action: 'BUY',
            mode: 'live',
            notional_usd: amount,
            bracket: true,
            stop_loss_pct: stopLossPct / 100,
            take_profit_pct: takeProfitPct / 100
          })
        }
      );

      const data = await response.json();

      if (data.success) {
        setResult({
          success: true,
          message: `✅ Purchased ${candidate.symbol} for $${amount} with ${stopLossPct}% stop-loss`
        });
      } else {
        setResult({
          success: false,
          message: `❌ Trade failed: ${data.error?.message || 'Unknown error'}`
        });
      }
    } catch (err: any) {
      setResult({
        success: false,
        message: `❌ Error: ${err.message || 'Network error'}`
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const estimatedShares = Math.floor(parseFloat(dollarAmount || '0') / candidate.price);
  const stopLossPrice = (candidate.price * (1 - stopLossPct / 100)).toFixed(2);
  const takeProfitPrice = (candidate.price * (1 + takeProfitPct / 100)).toFixed(2);
  const potentialLoss = (parseFloat(dollarAmount || '0') * stopLossPct / 100).toFixed(2);
  const potentialGain = (parseFloat(dollarAmount || '0') * takeProfitPct / 100).toFixed(2);

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0,0,0,0.7)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        background: 'white',
        borderRadius: '16px',
        padding: '32px',
        maxWidth: '600px',
        width: '90%',
        maxHeight: '90vh',
        overflow: 'auto'
      }}>
        {/* Header */}
        <div style={{marginBottom: '24px'}}>
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px'}}>
            <h2 style={{fontSize: '28px', fontWeight: '900', color: '#111', margin: 0}}>
              Buy {candidate.symbol}
            </h2>
            <button
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                fontSize: '32px',
                cursor: 'pointer',
                color: '#9ca3af',
                padding: 0,
                lineHeight: 1
              }}
            >
              ×
            </button>
          </div>
          <p style={{fontSize: '18px', color: '#6b7280', margin: 0}}>
            ${candidate.price.toFixed(2)} | {candidate.bms_score.toFixed(1)}% explosion probability
          </p>
        </div>

        {/* Dollar Amount Input */}
        <div style={{marginBottom: '24px'}}>
          <label style={{display: 'block', fontSize: '14px', fontWeight: '600', color: '#374151', marginBottom: '8px'}}>
            Dollar Amount to Invest
          </label>
          <input
            type="number"
            value={dollarAmount}
            onChange={(e) => setDollarAmount(e.target.value)}
            style={{
              width: '100%',
              padding: '12px 16px',
              fontSize: '18px',
              fontWeight: '600',
              border: '2px solid #e5e7eb',
              borderRadius: '8px',
              outline: 'none'
            }}
            min="1"
            step="1"
          />
          <p style={{fontSize: '13px', color: '#6b7280', marginTop: '6px', marginBottom: 0}}>
            ≈ {estimatedShares} shares
          </p>
        </div>

        {/* Stop-Loss & Take-Profit */}
        <div style={{background: '#f9fafb', borderRadius: '12px', padding: '20px', marginBottom: '24px'}}>
          <h3 style={{fontSize: '16px', fontWeight: '700', color: '#111', marginTop: 0, marginBottom: '16px'}}>
            Automatic Risk Management
          </h3>

          <div style={{marginBottom: '16px'}}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px'}}>
              <label style={{fontSize: '14px', fontWeight: '600', color: '#374151'}}>
                Stop-Loss
              </label>
              <span style={{fontSize: '14px', fontWeight: '700', color: '#dc2626'}}>
                -{stopLossPct}%
              </span>
            </div>
            <input
              type="range"
              value={stopLossPct}
              onChange={(e) => setStopLossPct(parseFloat(e.target.value))}
              min="2"
              max="20"
              step="0.5"
              style={{width: '100%'}}
            />
            <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#6b7280'}}>
              <span>Exit at ${stopLossPrice}</span>
              <span>Max loss: ${potentialLoss}</span>
            </div>
          </div>

          <div>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px'}}>
              <label style={{fontSize: '14px', fontWeight: '600', color: '#374151'}}>
                Take-Profit
              </label>
              <span style={{fontSize: '14px', fontWeight: '700', color: '#16a34a'}}>
                +{takeProfitPct}%
              </span>
            </div>
            <input
              type="range"
              value={takeProfitPct}
              onChange={(e) => setTakeProfitPct(parseFloat(e.target.value))}
              min="5"
              max="50"
              step="1"
              style={{width: '100%'}}
            />
            <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#6b7280'}}>
              <span>Exit at ${takeProfitPrice}</span>
              <span>Potential gain: ${potentialGain}</span>
            </div>
          </div>

          <div style={{
            marginTop: '16px',
            padding: '12px',
            background: '#eff6ff',
            borderRadius: '8px',
            border: '1px solid #bfdbfe'
          }}>
            <p style={{fontSize: '13px', color: '#1e40af', margin: 0, lineHeight: '1.5'}}>
              <strong>Risk/Reward:</strong> 1:{(takeProfitPct / stopLossPct).toFixed(1)} -
              For every $1 risked, you could gain ${(takeProfitPct / stopLossPct).toFixed(2)}
            </p>
          </div>
        </div>

        {/* Result Message */}
        {result && (
          <div style={{
            padding: '16px',
            borderRadius: '8px',
            marginBottom: '20px',
            background: result.success ? '#f0fdf4' : '#fef2f2',
            border: result.success ? '1px solid #86efac' : '1px solid #fca5a5'
          }}>
            <p style={{
              margin: 0,
              color: result.success ? '#166534' : '#991b1b',
              fontSize: '14px',
              fontWeight: '600'
            }}>
              {result.message}
            </p>
          </div>
        )}

        {/* Action Buttons */}
        <div style={{display: 'flex', gap: '12px'}}>
          <button
            onClick={onClose}
            style={{
              flex: 1,
              padding: '14px',
              fontSize: '16px',
              fontWeight: '600',
              border: '2px solid #e5e7eb',
              borderRadius: '8px',
              background: 'white',
              color: '#374151',
              cursor: 'pointer'
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleBuy}
            disabled={isSubmitting || !dollarAmount || parseFloat(dollarAmount) <= 0}
            style={{
              flex: 2,
              padding: '14px',
              fontSize: '16px',
              fontWeight: '700',
              border: 'none',
              borderRadius: '8px',
              background: isSubmitting ? '#9ca3af' : '#16a34a',
              color: 'white',
              cursor: isSubmitting ? 'not-allowed' : 'pointer',
              opacity: isSubmitting ? 0.6 : 1
            }}
          >
            {isSubmitting ? 'Processing...' : `🚀 Buy $${dollarAmount} of ${candidate.symbol}`}
          </button>
        </div>

        {/* Fine Print */}
        <p style={{
          marginTop: '20px',
          fontSize: '11px',
          color: '#9ca3af',
          textAlign: 'center',
          lineHeight: '1.4'
        }}>
          Market order will execute at current price. Stop-loss and take-profit orders will be placed automatically.
          Trading involves risk of loss.
        </p>
      </div>
    </div>
  );
};

export default BMSDiscovery;