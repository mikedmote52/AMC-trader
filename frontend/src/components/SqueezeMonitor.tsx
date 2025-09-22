import React, { useState, useEffect, useRef } from "react";
import { io, Socket } from "socket.io-client";
import SqueezeAlert from "./SqueezeAlert";
import PatternHistory from "./PatternHistory";
import { WS_URL } from "../config";
import { getJSON, postJSON } from "../lib/api";
import { polygonSqueezeDetector } from "../lib/polygonSqueezeDetector";

// AlphaStack 4.1 Candidate Interface
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

  // Use the existing working discovery system
  const fetchData = async () => {
    try {
      setLoading(true);
      setError("");

      console.log('🔄 Using existing discovery system...');

      // Call the explosive discovery system that has MCP-enhanced data
      const discoveryURL = WS_URL.replace('wss', 'https').replace('ws', 'http').replace('/v1/stream', '');
      const discoveryResponse = await fetch(`${discoveryURL}/discovery/discovery/explosive?limit=50`);

      if (!discoveryResponse.ok) {
        throw new Error(`Discovery system failed: ${discoveryResponse.status}`);
      }

      const discoveryData = await discoveryResponse.json();
      console.log('✅ Discovery data received:', discoveryData);
      console.log('Discovery success:', discoveryData.success);
      console.log('Discovery data array:', discoveryData.data);
      console.log('Discovery count:', discoveryData.count || 0, 'candidates');

      if (!discoveryData.success) {
        throw new Error(`Discovery system returned success=false: ${JSON.stringify(discoveryData)}`);
      }

      if (!discoveryData.data || !Array.isArray(discoveryData.data)) {
        throw new Error(`No valid data array returned: ${JSON.stringify(discoveryData)}`);
      }

      if (discoveryData.data.length === 0) {
        console.warn('⚠️ Discovery returned empty data array');
      }

      // Map the MCP-enhanced explosive discovery data
      const candidates = discoveryData.data.map((candidate: any, index: number) => {
        console.log(`Mapping candidate ${index}:`, candidate);

        const mapped = {
          symbol: candidate.symbol || 'UNKNOWN',
          ticker: candidate.symbol || 'UNKNOWN',
          total_score: (candidate.score || 0) / 100, // Convert to 0-1 range
          score: (candidate.score || 0) / 100,
          action_tag: candidate.action_tag || 'monitor',
          price: candidate.price || 0,
          snapshot: {
            price: candidate.price || 0,
            intraday_relvol: candidate.volume_surge_ratio || 1.0,
            volume: candidate.volume || 0,
            change_percent: candidate.price_change_pct || 0
          },
          entry: candidate.price || 0,
          stop: (candidate.price || 0) * 0.95, // 5% stop loss
          tp1: (candidate.price || 0) * 1.10,  // 10% target
          tp2: (candidate.price || 0) * 1.20,  // 20% target
          // Include MCP-enhanced subscores
          subscores: candidate.subscores || {},
          confidence: candidate.confidence || 0,
          news_count: candidate.news_count_24h || 0
        };

        console.log(`Mapped candidate ${index}:`, mapped);
        return mapped;
      });

      console.log('✅ Using real discovery candidates:', candidates.slice(0, 5).map(c => `${c.symbol}: ${(c.score * 100).toFixed(1)}%`));

      setCandidates(candidates);
      setExplosive([]);
      setTelemetry({
        schema_version: "alphastack_v4_discovery",
        system_health: { system_ready: true },
        production_health: { stale_data_detected: false }
      });

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
        mode: "paper",
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
      tp2: c.tp2
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

// Candidate Card Component with safety guards
function CandidateCard({ candidate, onBuy, disabled }: { candidate: any; onBuy: () => void; disabled: boolean }) {
  return (
    <div style={cardStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <span style={{ fontSize: '18px', fontWeight: 700, color: '#fff' }}>{candidate.symbol}</span>
        <span style={{ fontSize: '14px', color: '#22c55e' }}>
          {typeof candidate.price === 'number' ? `$${candidate.price.toFixed(2)}` : '—'}
        </span>
      </div>
      <div style={{ fontSize: '12px', color: '#999', marginBottom: '12px' }}>
        <div>Score: {typeof candidate.score === 'number' ? `${candidate.score.toFixed(1)}%` : 'N/A'}</div>
        <div>RelVol: {typeof candidate.relvol === 'number' ? `${candidate.relvol.toFixed(1)}x` : 'N/A'}</div>
        {typeof candidate.entry === 'number' && <div>Entry: ${candidate.entry.toFixed(2)}</div>}
        {typeof candidate.stop === 'number' && <div>Stop: ${candidate.stop.toFixed(2)}</div>}
        {typeof candidate.tp1 === 'number' && <div>TP1: ${candidate.tp1.toFixed(2)}</div>}
      </div>
      <button
        onClick={onBuy}
        disabled={disabled}
        style={{
          ...buttonStyle,
          width: '100%',
          background: disabled ? '#333' : '#22c55e',
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.5 : 1
        }}
      >
        {disabled ? 'Not Available' : 'Buy Paper'}
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