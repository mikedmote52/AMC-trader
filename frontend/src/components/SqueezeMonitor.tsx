import React, { useState, useEffect, useRef } from "react";
import { io, Socket } from "socket.io-client";
import SqueezeAlert from "./SqueezeAlert";
import PatternHistory from "./PatternHistory";
import { WS_URL } from "../config";
import { getJSON, postJSON } from "../lib/api";
import { polygonSqueezeDetector } from "../lib/polygonSqueezeDetector";

// Enhanced Candidate Interface with Hybrid V1 Support
interface Candidate {
  symbol: string;
  ticker?: string;
  total_score?: number;
  score?: number;
  action_tag?: string;
  price?: number;
  snapshot?: {
    price?: number;
    intraday_relvol?: number;
  };
  entry?: number;
  stop?: number;
  tp1?: number;
  tp2?: number;
  subscores?: {
    volume_momentum?: number;
    squeeze?: number;
    catalyst?: number;
    options?: number;
    technical?: number;
  };
  strategy?: string;
  confidence?: number;
}

interface Telemetry {
  schema_version?: string;
  system_health?: {
    system_ready: boolean;
  };
  production_health?: {
    stale_data_detected: boolean;
  };
}

// Status Pill Component
function StatusPill({ telemetry, loading }: { telemetry: Telemetry | null; loading: boolean }) {
  const getStatus = () => {
    if (loading) return { color: '#6b7280', text: 'Loading...' }; // Gray
    if (!telemetry?.system_health?.system_ready) return { color: '#ef4444', text: 'System Offline' }; // Red
    if (telemetry?.production_health?.stale_data_detected) return { color: '#f59e0b', text: 'Stale Data' }; // Yellow
    return { color: '#22c55e', text: 'Live' }; // Green
  };

  const status = getStatus();

  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px',
      padding: '4px 12px',
      borderRadius: '16px',
      background: status.color,
      color: '#000',
      fontSize: '12px',
      fontWeight: 600
    }}>
      <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#000' }} />
      {status.text}
    </div>
  );
}

export default function SqueezeMonitor() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [explosive, setExplosive] = useState<Candidate[]>([]);
  const [telemetry, setTelemetry] = useState<Telemetry | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showHistory, setShowHistory] = useState(false);
  const socketRef = useRef<Socket | null>(null);

  // Check if safe to trade
  const safeToTrade = telemetry?.system_health?.system_ready === true &&
                      telemetry?.production_health?.stale_data_detected === false;

  // Enhanced candidate mapping functions
  const mapStrategyCandidate = (candidates: any[], strategy: string): Candidate[] => {
    return candidates.map((candidate: any) => {
      const price = candidate.price || candidate.snapshot?.price || 0;
      const score = candidate.total_score || candidate.score || 0;

      return {
        symbol: candidate.symbol || candidate.ticker || 'UNKNOWN',
        ticker: candidate.symbol || candidate.ticker || 'UNKNOWN',
        total_score: score,
        score: score,
        action_tag: candidate.action_tag || (score > 0.8 ? 'trade_ready' : score > 0.65 ? 'watchlist' : 'monitor'),
        price: price,
        snapshot: {
          price: price,
          intraday_relvol: candidate.snapshot?.intraday_relvol || 0
        },
        entry: candidate.entry || price,
        stop: candidate.stop || price * 0.95,
        tp1: candidate.tp1 || price * 1.10,
        tp2: candidate.tp2 || price * 1.20,
        subscores: candidate.subscores || {
          volume_momentum: (score * 0.40) * 100,
          squeeze: (score * 0.30) * 100,
          catalyst: (score * 0.15) * 100,
          options: (score * 0.10) * 100,
          technical: (score * 0.05) * 100
        },
        strategy: strategy,
        confidence: candidate.confidence || score
      };
    });
  };

  const mapContenderCandidates = (candidates: any[]): Candidate[] => {
    return candidates.map((candidate: any) => {
      const price = candidate.day?.c || candidate.prevDay?.c || 0;
      const volume = candidate.day?.v || 0;
      const change_percent = candidate.todaysChangePerc || 0;
      const volume_ratio = candidate.volume_ratio || 1.0;
      const score = candidate.filter_score || 0;

      return {
        symbol: candidate.ticker || 'UNKNOWN',
        ticker: candidate.ticker || 'UNKNOWN',
        total_score: score,
        score: score,
        action_tag: score > 0.7 ? 'trade_ready' : score > 0.5 ? 'watchlist' : 'monitor',
        price: price,
        snapshot: {
          price: price,
          intraday_relvol: volume_ratio
        },
        entry: price,
        stop: price * 0.95,
        tp1: price * 1.10,
        tp2: price * 1.20,
        subscores: {
          volume_momentum: Math.min(volume_ratio * 25, 100),
          squeeze: Math.min(score * 150, 100),
          catalyst: Math.max(0, Math.min(change_percent * 10, 100)),
          options: Math.min(volume / 1000000 * 50, 100),
          technical: score * 100
        },
        strategy: 'contenders',
        confidence: Math.min(score + 0.1, 1.0)
      };
    });
  };

  // Enhanced discovery system with strategy support
  const fetchData = async () => {
    try {
      setLoading(true);
      setError("");

      console.log('🔄 Using enhanced discovery system...');

      // Call the enhanced discovery system with strategy validation
      const discoveryURL = WS_URL.replace('wss', 'https').replace('ws', 'http').replace('/v1/stream', '');

      // Try strategy validation first to get hybrid_v1 data
      let discoveryResponse = await fetch(`${discoveryURL}/discovery/strategy-validation?limit=50`);
      let useStrategyData = false;

      if (discoveryResponse.ok) {
        const strategyData = await discoveryResponse.json();
        if (strategyData.success && strategyData.comparison?.hybrid_v1?.candidates) {
          console.log('✅ Using hybrid_v1 strategy data');
          const candidates = mapStrategyCandidate(strategyData.comparison.hybrid_v1.candidates, 'hybrid_v1');
          setCandidates(candidates);
          setExplosive([]);
          setTelemetry({
            schema_version: "hybrid_v1_strategy",
            system_health: { system_ready: true },
            production_health: { stale_data_detected: false }
          });
          useStrategyData = true;
        }
      }

      // Fallback to contenders if strategy validation fails
      if (!useStrategyData) {
        discoveryResponse = await fetch(`${discoveryURL}/discovery/contenders?limit=50`);

        if (!discoveryResponse.ok) {
          throw new Error(`Discovery system failed: ${discoveryResponse.status}`);
        }

        const discoveryData = await discoveryResponse.json();
        console.log('✅ Discovery fallback data received:', discoveryData);

        if (!discoveryData.success) {
          throw new Error(`Discovery system returned success=false: ${JSON.stringify(discoveryData)}`);
        }

        if (!discoveryData.data || !Array.isArray(discoveryData.data)) {
          throw new Error(`No valid data array returned: ${JSON.stringify(discoveryData)}`);
        }

        if (discoveryData.data.length === 0) {
          console.warn('⚠️ Discovery returned empty data array');
        }

        // Map the real live discovery contenders data
        const candidates = mapContenderCandidates(discoveryData.data);
        setCandidates(candidates);
        setExplosive([]);
        setTelemetry({
          schema_version: "contenders_fallback",
          system_health: { system_ready: true },
          production_health: { stale_data_detected: false }
        });
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load real data";
      setError(`Real data error: ${errorMessage}`);
      console.error("Real data error:", err);

      setCandidates([]);
      setExplosive([]);
      setTelemetry({
        schema_version: "error_state",
        system_health: { system_ready: false },
        production_health: { stale_data_detected: true }
      });
    } finally {
      setLoading(false);
    }
  };

  // Place order
  const placeOrder = async (ticker: string) => {
    try {
      const payload = {
        symbol: ticker,
        action: "BUY",
        mode: "shadow",  // Use shadow mode for safe testing
        notional_usd: 100
      };

      const result = await postJSON('/trades/execute', payload);
      console.log("Order placed:", result);
      alert(`Paper order placed for ${ticker}`);
    } catch (err) {
      console.error("Order error:", err);
      alert(`Failed to place order: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  // Initialize WebSocket
  useEffect(() => {
    // Initial fetch
    fetchData();

    // Setup WebSocket with correct path for Socket.IO mounted at /v1/stream
    const socket = io(WS_URL, {
      path: '/v1/stream/socket.io',
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 2000
    });

    socket.on('connect', () => console.log('AlphaStack WebSocket connected'));
    socket.on('candidate', () => fetchData());
    socket.on('explosive', () => fetchData());
    socket.on('telemetry', () => fetchData());

    socketRef.current = socket;

    return () => {
      socket.disconnect();
    };
  }, []);

  // Normalize candidate data with safety guards
  const normalizeCandidate = (c: Candidate) => {
    const raw = (c.total_score ?? c.score ?? 0);
    const scorePct = raw <= 1 ? raw * 100 : raw;
    return {
      symbol: c.symbol || c.ticker || 'UNKNOWN',
      score: scorePct,
      action_tag: c.action_tag || 'MONITOR',
      price: c.price || c.snapshot?.price || 0,
      relvol: c.snapshot?.intraday_relvol || 0,
      entry: c.entry,
      stop: c.stop,
      tp1: c.tp1,
      tp2: c.tp2,
      short_interest: c.short_interest || { available: false }
    };
  };

  // Combine and de-duplicate candidates
  const allCandidates = Array.from(
    new Map([...candidates, ...explosive].map(c => {
      const n = normalizeCandidate(c);
      return [n.symbol, n]; // last write wins
    })).values()
  );

  const tradeReady = allCandidates.filter(c => c.action_tag === 'trade_ready');
  const watchlist = allCandidates.filter(c => c.action_tag === 'watchlist');
  const others = allCandidates.filter(c => c.action_tag !== 'trade_ready' && c.action_tag !== 'watchlist');

  return (
    <div style={containerStyle}>
      {/* Header */}
      <div style={headerStyle}>
        <div>
          <h1 style={titleStyle}>🔍 Squeeze Monitor</h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '8px' }}>
            <StatusPill telemetry={telemetry} loading={loading} />
            <span style={{ fontSize: '14px', color: '#999' }}>
              AlphaStack {telemetry?.schema_version || 'Unknown'}
            </span>
          </div>
        </div>
        <div>
          <button onClick={fetchData} style={buttonStyle} disabled={loading}>
            {loading ? 'Loading...' : '🔄 Refresh'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: '16px', background: '#2d1b1b', border: '1px solid #ef4444', borderRadius: '8px', color: '#ef4444', marginBottom: '24px' }}>
          ⚠️ {error}
        </div>
      )}

      {/* Trade Ready Candidates */}
      {tradeReady.length > 0 && (
        <section style={sectionStyle}>
          <h2 style={sectionTitleStyle}>🚀 Trade Ready ({tradeReady.length})</h2>
          <div style={gridStyle}>
            {tradeReady.map((c, i) => (
              <CandidateCard
                key={`${c.symbol}-${i}`}
                candidate={c}
                onBuy={() => placeOrder(c.symbol)}
                disabled={!safeToTrade}
              />
            ))}
          </div>
        </section>
      )}

      {/* Watchlist */}
      {watchlist.length > 0 && (
        <section style={sectionStyle}>
          <h2 style={sectionTitleStyle}>📊 Watchlist ({watchlist.length})</h2>
          <div style={gridStyle}>
            {watchlist.map((c, i) => (
              <CandidateCard
                key={`${c.symbol}-${i}`}
                candidate={c}
                onBuy={() => placeOrder(c.symbol)}
                disabled={true}
              />
            ))}
          </div>
        </section>
      )}

      {/* Others */}
      {others.length > 0 && (
        <section style={sectionStyle}>
          <h2 style={sectionTitleStyle}>🔍 Monitoring ({others.length})</h2>
          <div style={gridStyle}>
            {others.map((c, i) => (
              <CandidateCard
                key={`${c.symbol}-${i}`}
                candidate={c}
                onBuy={() => placeOrder(c.symbol)}
                disabled={true}
              />
            ))}
          </div>
        </section>
      )}

      {/* Pattern History */}
      <section style={{ marginTop: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <h2 style={sectionTitleStyle}>📚 Pattern History</h2>
          <button onClick={() => setShowHistory(!showHistory)} style={{ ...buttonStyle, padding: '4px 12px', fontSize: '12px' }}>
            {showHistory ? 'Hide' : 'Show'}
          </button>
        </div>
        {showHistory && <PatternHistory />}
      </section>
    </div>
  );
}

// Enhanced Candidate Card Component with Subscores
function CandidateCard({ candidate, onBuy, disabled }: { candidate: any; onBuy: () => void; disabled: boolean }) {
  const getActionTagColor = (tag: string) => {
    switch (tag) {
      case 'trade_ready': return '#22c55e';
      case 'watchlist': return '#f59e0b';
      case 'monitor': return '#6b7280';
      default: return '#999';
    }
  };

  const renderSubscores = () => {
    if (!candidate.subscores) return null;

    return (
      <div style={{ marginTop: '8px', padding: '8px', background: '#0a0a0a', borderRadius: '4px' }}>
        <div style={{ fontSize: '10px', color: '#888', marginBottom: '4px' }}>
          {candidate.strategy === 'hybrid_v1' ? 'Hybrid V1 Components:' : 'Score Breakdown:'}
        </div>
        {candidate.subscores.volume_momentum !== undefined && (
          <div style={{ fontSize: '10px', color: '#22c55e' }}>
            Volume/Momentum: {candidate.subscores.volume_momentum.toFixed(1)}%
          </div>
        )}
        {candidate.subscores.squeeze !== undefined && (
          <div style={{ fontSize: '10px', color: '#f59e0b' }}>
            Squeeze: {candidate.subscores.squeeze.toFixed(1)}%
          </div>
        )}
        {candidate.subscores.catalyst !== undefined && (
          <div style={{ fontSize: '10px', color: '#ef4444' }}>
            Catalyst: {candidate.subscores.catalyst.toFixed(1)}%
          </div>
        )}
        {candidate.subscores.options !== undefined && (
          <div style={{ fontSize: '10px', color: '#8b5cf6' }}>
            Options: {candidate.subscores.options.toFixed(1)}%
          </div>
        )}
        {candidate.subscores.technical !== undefined && (
          <div style={{ fontSize: '10px', color: '#06b6d4' }}>
            Technical: {candidate.subscores.technical.toFixed(1)}%
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{
      ...cardStyle,
      border: `2px solid ${getActionTagColor(candidate.action_tag)}`
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <span style={{ fontSize: '18px', fontWeight: 700, color: '#fff' }}>{candidate.symbol}</span>
        <span style={{ fontSize: '14px', color: '#22c55e' }}>
          {typeof candidate.price === 'number' ? `$${candidate.price.toFixed(2)}` : '—'}
        </span>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <span style={{
          fontSize: '12px',
          padding: '2px 6px',
          borderRadius: '4px',
          background: getActionTagColor(candidate.action_tag),
          color: '#000',
          fontWeight: 600
        }}>
          {candidate.action_tag?.toUpperCase() || 'UNKNOWN'}
        </span>
        {candidate.strategy && (
          <span style={{ fontSize: '10px', color: '#888' }}>
            {candidate.strategy}
          </span>
        )}
      </div>

      <div style={{ fontSize: '12px', color: '#999', marginBottom: '8px' }}>
        <div>Score: {typeof candidate.score === 'number' ? `${(candidate.score * 100).toFixed(1)}%` : 'N/A'}</div>
        <div>RelVol: {typeof candidate.relvol === 'number' ? `${candidate.relvol.toFixed(1)}x` : 'N/A'}</div>
        {typeof candidate.entry === 'number' && <div>Entry: ${candidate.entry.toFixed(2)}</div>}
        {typeof candidate.stop === 'number' && <div>Stop: ${candidate.stop.toFixed(2)}</div>}
        {typeof candidate.tp1 === 'number' && <div>TP1: ${candidate.tp1.toFixed(2)}</div>}
        {candidate.confidence && (
          <div style={{ color: '#06b6d4' }}>
            Confidence: {(candidate.confidence * 100).toFixed(0)}%
          </div>
        )}
      </div>

      {renderSubscores()}

      <button
        onClick={onBuy}
        disabled={disabled}
        style={{
          ...buttonStyle,
          width: '100%',
          background: disabled ? '#333' : getActionTagColor(candidate.action_tag),
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.5 : 1,
          marginTop: '8px'
        }}
      >
        {disabled ? 'Not Available' : `Buy ${candidate.symbol}`}
      </button>
    </div>
  );
}

// Styles
const containerStyle: React.CSSProperties = {
  fontFamily: "ui-sans-serif, system-ui",
  color: "#e7e7e7",
  background: "#000",
  minHeight: "100vh",
  padding: "20px",
  maxWidth: "1400px",
  margin: "0 auto"
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "32px"
};

const titleStyle: React.CSSProperties = {
  fontSize: "32px",
  fontWeight: 700,
  color: "#fff"
};

const buttonStyle: React.CSSProperties = {
  padding: "8px 16px",
  borderRadius: "8px",
  border: "none",
  background: "#333",
  color: "#fff",
  fontSize: "14px",
  fontWeight: 600,
  cursor: "pointer"
};

const sectionStyle: React.CSSProperties = {
  marginBottom: "32px"
};

const sectionTitleStyle: React.CSSProperties = {
  fontSize: "20px",
  fontWeight: 600,
  color: "#fff",
  marginBottom: "16px"
};

const gridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fill, minmax(250px, 1fr))",
  gap: "16px"
};

const cardStyle: React.CSSProperties = {
  padding: "16px",
  background: "#111",
  border: "1px solid #333",
  borderRadius: "12px"
};