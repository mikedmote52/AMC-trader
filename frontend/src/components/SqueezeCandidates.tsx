import { useEffect, useState, useMemo, useCallback } from 'react';
import './SqueezeCandidates.css';

interface SqueezeCandidate {
  symbol: string;
  price: number;
  price_1d_ago: number;
  volatility: number;
  volatility_1d_ago: number;
  volume: number;
  volume_1d_ago: number;
  momentum: number;
  risk_score: number;
}

const API_BASE = import.meta.env.VITE_API_URL || '';

export function SqueezeCandidates() {
  const [candidates, setCandidates] = useState<SqueezeCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [buying, setBuying] = useState<Set<string>>(new Set());
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const fetchCandidates = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/squeeze-candidates`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      
      setCandidates(prev => {
        const hasChanges = JSON.stringify(prev) !== JSON.stringify(data);
        if (hasChanges) setLastUpdate(new Date());
        return data;
      });
      setError(null);
      setLoading(false);
    } catch (err: any) {
      setError(err.message || 'Failed to load candidates');
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCandidates();
    const interval = setInterval(fetchCandidates, 30000);
    return () => clearInterval(interval);
  }, [fetchCandidates]);

  const executeBuy = useCallback(async (symbol: string, notional: number = 100) => {
    setBuying(prev => new Set(prev).add(symbol));
    try {
      const response = await fetch(`${API_BASE}/trades/execute`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ 
          symbol, 
          action: 'BUY', 
          notional_usd: notional, 
          mode: 'live' 
        })
      });
      const result = await response.json();
      if (!response.ok) throw result;
      
      setCandidates(prev => prev.map(c => 
        c.symbol === symbol 
          ? { ...c, momentum: Math.min(c.momentum + 0.1, 1) }
          : c
      ));
      
      return { success: true, mode: result.mode };
    } catch (err: any) {
      return { success: false, error: err.error || 'Order failed' };
    } finally {
      setBuying(prev => {
        const next = new Set(prev);
        next.delete(symbol);
        return next;
      });
    }
  }, []);

  const sortedCandidates = useMemo(() => {
    return [...candidates].sort((a, b) => {
      const scoreA = (a.momentum * 2 + (1 - a.risk_score)) / 3;
      const scoreB = (b.momentum * 2 + (1 - b.risk_score)) / 3;
      return scoreB - scoreA;
    });
  }, [candidates]);

  const topPicks = sortedCandidates.slice(0, 3);
  const others = sortedCandidates.slice(3);

  const formatChange = (current: number, previous: number) => {
    const change = ((current - previous) / previous) * 100;
    return {
      value: change,
      display: `${change >= 0 ? '+' : ''}${change.toFixed(1)}%`,
      color: change >= 0 ? 'green' : 'red'
    };
  };

  const formatVolume = (volume: number) => {
    if (volume >= 1e9) return `${(volume / 1e9).toFixed(2)}B`;
    if (volume >= 1e6) return `${(volume / 1e6).toFixed(2)}M`;
    if (volume >= 1e3) return `${(volume / 1e3).toFixed(2)}K`;
    return volume.toString();
  };

  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey) {
        const num = parseInt(e.key);
        if (num >= 1 && num <= 9) {
          e.preventDefault();
          const candidate = sortedCandidates[num - 1];
          if (candidate && !buying.has(candidate.symbol)) {
            executeBuy(candidate.symbol);
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [sortedCandidates, buying, executeBuy]);

  if (loading && candidates.length === 0) {
    return (
      <div className="squeeze-container">
        <h2>Squeeze Candidates</h2>
        <div className="skeleton-grid">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="skeleton-card" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="squeeze-container">
      <div className="squeeze-header">
        <h2>Squeeze Candidates</h2>
        {lastUpdate && (
          <span className="update-indicator">
            Updated {Math.floor((Date.now() - lastUpdate.getTime()) / 1000)}s ago
          </span>
        )}
      </div>

      {error && (
        <div className="error-banner">
          ⚠️ {error}
        </div>
      )}

      {topPicks.length > 0 && (
        <div className="top-picks">
          <h3>🔥 Top Opportunities</h3>
          <div className="hero-grid">
            {topPicks.map((candidate, index) => {
              const priceChange = formatChange(candidate.price, candidate.price_1d_ago);
              const volumeChange = formatChange(candidate.volume, candidate.volume_1d_ago);
              const score = (candidate.momentum * 2 + (1 - candidate.risk_score)) / 3;
              
              return (
                <div 
                  key={candidate.symbol} 
                  className={`hero-card rank-${index + 1}`}
                  data-momentum={candidate.momentum > 0.7 ? 'high' : 'normal'}
                >
                  <div className="hero-header">
                    <div className="hero-symbol">
                      <span className="symbol">{candidate.symbol}</span>
                      <span className="rank">#{index + 1}</span>
                    </div>
                    <div className="hero-score">
                      <div className="score-ring" style={{ '--score': score }}>
                        {Math.round(score * 100)}
                      </div>
                    </div>
                  </div>

                  <div className="hero-price">
                    <span className="current">${candidate.price.toFixed(2)}</span>
                    <span className={`change ${priceChange.color}`}>
                      {priceChange.display}
                    </span>
                  </div>

                  <div className="hero-metrics">
                    <div className="metric">
                      <label>Volume</label>
                      <span>{formatVolume(candidate.volume)}</span>
                      <span className={`sub ${volumeChange.color}`}>
                        {volumeChange.display}
                      </span>
                    </div>
                    <div className="metric">
                      <label>Volatility</label>
                      <span>{(candidate.volatility * 100).toFixed(1)}%</span>
                      <span className="sub">
                        {candidate.volatility > candidate.volatility_1d_ago ? '↑' : '↓'}
                      </span>
                    </div>
                  </div>

                  <div className="hero-actions">
                    <button
                      className="buy-primary"
                      disabled={buying.has(candidate.symbol)}
                      onClick={() => executeBuy(candidate.symbol)}
                    >
                      {buying.has(candidate.symbol) ? 'Executing...' : 'Buy'}
                    </button>
                    <button className="details-secondary">
                      Details
                    </button>
                  </div>

                  <div className="keyboard-hint">
                    ⌘{index + 1}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {others.length > 0 && (
        <div className="other-candidates">
          <h3>Your Holdings</h3>
          <div className="compact-grid">
            {others.map((candidate, index) => {
              const globalIndex = index + 3;
              const priceChange = formatChange(candidate.price, candidate.price_1d_ago);
              
              return (
                <div key={candidate.symbol} className="compact-card">
                  <div className="compact-main">
                    <span className="symbol">{candidate.symbol}</span>
                    <span className="price">${candidate.price.toFixed(2)}</span>
                    <span className={`change ${priceChange.color}`}>
                      {priceChange.display}
                    </span>
                  </div>
                  <div className="compact-actions">
                    <button
                      className="buy-compact"
                      disabled={buying.has(candidate.symbol)}
                      onClick={() => executeBuy(candidate.symbol)}
                      title={`Buy ${candidate.symbol} (⌘${globalIndex + 1})`}
                    >
                      Buy
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {candidates.length === 0 && !error && (
        <div className="no-candidates">
          No squeeze candidates found. Scanning market...
        </div>
      )}
    </div>
  );
}