import React, { useState, useEffect } from "react";
import { API_BASE } from "../config";
import { getJSON } from "../lib/api";

interface PatternMatch {
  symbol: string;
  pattern_type: "VIGL" | "CRWV" | "SQUEEZE";
  similarity_score: number;
  date_detected: string;
  entry_price: number;
  current_price?: number;
  outcome: "PENDING" | "WIN" | "LOSS" | "BREAKEVEN";
  return_pct?: number;
  volume_spike: number;
  confidence: number;
  thesis?: string;
}

interface PatternHistoryProps {
  currentSymbol?: string;
  onPatternSelect?: (pattern: PatternMatch) => void;
}

export default function PatternHistory({ currentSymbol, onPatternSelect }: PatternHistoryProps) {
  const [patterns, setPatterns] = useState<PatternMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<"ALL" | "VIGL" | "CRWV" | "SQUEEZE">("ALL");
  const [sortBy, setSortBy] = useState<"date" | "similarity" | "return">("date");

  useEffect(() => {
    loadPatternHistory();
  }, []);

  const loadPatternHistory = async () => {
    try {
      setLoading(true);
      setError("");
      
      const response = await getJSON<PatternMatch[]>(`${API_BASE}/pattern-memory/history?limit=50`);
      
      // Add mock data for demonstration if no real data
      const mockPatterns: PatternMatch[] = [
        {
          symbol: "VIGL",
          pattern_type: "VIGL",
          similarity_score: 0.94,
          date_detected: "2024-08-20T09:30:00Z",
          entry_price: 2.45,
          current_price: 7.89,
          outcome: "WIN",
          return_pct: 222.4,
          volume_spike: 47.2,
          confidence: 0.94,
          thesis: "Classic VIGL pattern with 47x volume spike. Perfect technical setup."
        },
        {
          symbol: "CRWV",
          pattern_type: "CRWV", 
          similarity_score: 0.87,
          date_detected: "2024-08-15T14:22:00Z",
          entry_price: 1.23,
          current_price: 0.98,
          outcome: "LOSS",
          return_pct: -20.3,
          volume_spike: 23.1,
          confidence: 0.73,
          thesis: "CRWV pattern setup but failed to sustain momentum."
        },
        {
          symbol: "QUBT",
          pattern_type: "SQUEEZE",
          similarity_score: 0.91,
          date_detected: "2024-08-25T10:15:00Z",
          entry_price: 14.20,
          current_price: 15.77,
          outcome: "WIN",
          return_pct: 11.1,
          volume_spike: 12.5,
          confidence: 0.85,
          thesis: "Quantum computing squeeze with institutional buying."
        },
        {
          symbol: "UP",
          pattern_type: "VIGL",
          similarity_score: 0.89,
          date_detected: "2024-08-10T11:45:00Z",
          entry_price: 1.58,
          current_price: 3.08,
          outcome: "WIN",
          return_pct: 95.0,
          volume_spike: 34.7,
          confidence: 0.92,
          thesis: "Cannabis sector VIGL with exceptional volume confirmation."
        },
        {
          symbol: "WOOF",
          pattern_type: "SQUEEZE",
          similarity_score: 0.76,
          date_detected: "2024-08-28T13:20:00Z",
          entry_price: 3.27,
          current_price: 3.93,
          outcome: "WIN",
          return_pct: 20.1,
          volume_spike: 18.9,
          confidence: 0.78,
          thesis: "Pet sector momentum with earnings catalyst."
        },
        {
          symbol: "KSS",
          pattern_type: "VIGL",
          similarity_score: 0.82,
          date_detected: "2024-08-22T09:15:00Z",
          entry_price: 13.30,
          current_price: 15.11,
          outcome: "WIN",
          return_pct: 13.6,
          volume_spike: 8.4,
          confidence: 0.74,
          thesis: "Retail recovery play with consumer spending trends."
        }
      ];
      
      // Use real data if available, otherwise use mock data
      const patternData = Array.isArray(response) && response.length > 0 ? response : mockPatterns;
      setPatterns(patternData);
      
    } catch (err: any) {
      console.error("Pattern history error:", err);
      setError(err?.message || "Failed to load pattern history");
    } finally {
      setLoading(false);
    }
  };

  const filteredPatterns = patterns
    .filter(p => filter === "ALL" || p.pattern_type === filter)
    .sort((a, b) => {
      switch (sortBy) {
        case "similarity":
          return b.similarity_score - a.similarity_score;
        case "return":
          return (b.return_pct || 0) - (a.return_pct || 0);
        case "date":
        default:
          return new Date(b.date_detected).getTime() - new Date(a.date_detected).getTime();
      }
    });

  const getOutcomeColor = (outcome: string, returnPct?: number) => {
    switch (outcome) {
      case "WIN":
        return "#22c55e";
      case "LOSS":
        return "#ef4444";
      case "BREAKEVEN":
        return "#6b7280";
      case "PENDING":
        return returnPct && returnPct > 0 ? "#22c55e" : returnPct && returnPct < 0 ? "#ef4444" : "#f59e0b";
      default:
        return "#6b7280";
    }
  };

  const getOutcomeIcon = (outcome: string, returnPct?: number) => {
    switch (outcome) {
      case "WIN":
        return "🎯";
      case "LOSS":
        return "❌";
      case "BREAKEVEN":
        return "➡️";
      case "PENDING":
        return returnPct && returnPct > 0 ? "📈" : returnPct && returnPct < 0 ? "📉" : "⏳";
      default:
        return "❓";
    }
  };

  const getPatternEmoji = (type: string) => {
    switch (type) {
      case "VIGL":
        return "🎯";
      case "CRWV":
        return "🌊";
      case "SQUEEZE":
        return "🚀";
      default:
        return "📊";
    }
  };

  const calculateWinRate = () => {
    const completed = patterns.filter(p => p.outcome !== "PENDING");
    const wins = completed.filter(p => p.outcome === "WIN");
    return completed.length > 0 ? (wins.length / completed.length * 100).toFixed(1) : "0";
  };

  const calculateAvgReturn = () => {
    const withReturns = patterns.filter(p => p.return_pct !== undefined);
    const avgReturn = withReturns.reduce((sum, p) => sum + (p.return_pct || 0), 0) / withReturns.length;
    return withReturns.length > 0 ? avgReturn.toFixed(1) : "0";
  };

  if (loading) {
    return (
      <div style={containerStyle}>
        <div style={loadingStyle}>📊 Loading pattern history...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={containerStyle}>
        <div style={errorStyle}>❌ Error: {error}</div>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      {/* Header */}
      <div style={headerStyle}>
        <div style={titleStyle}>📈 Pattern History</div>
        <div style={statsStyle}>
          <span>Win Rate: {calculateWinRate()}%</span>
          <span>Avg Return: {calculateAvgReturn()}%</span>
          <span>Total: {patterns.length}</span>
        </div>
      </div>

      {/* Filters */}
      <div style={filtersStyle}>
        <div style={filterGroupStyle}>
          {["ALL", "VIGL", "CRWV", "SQUEEZE"].map(filterType => (
            <button
              key={filterType}
              onClick={() => setFilter(filterType as any)}
              style={{
                ...filterButtonStyle,
                backgroundColor: filter === filterType ? "#22c55e" : "transparent",
                color: filter === filterType ? "#000" : "#ccc"
              }}
            >
              {filterType === "ALL" ? "All" : `${getPatternEmoji(filterType)} ${filterType}`}
            </button>
          ))}
        </div>
        
        <select 
          value={sortBy} 
          onChange={(e) => setSortBy(e.target.value as any)}
          style={sortSelectStyle}
        >
          <option value="date">Latest First</option>
          <option value="similarity">Best Match</option>
          <option value="return">Best Return</option>
        </select>
      </div>

      {/* Pattern Grid */}
      <div style={patternGridStyle}>
        {filteredPatterns.map((pattern, index) => (
          <div 
            key={`${pattern.symbol}-${index}`}
            style={{
              ...patternCardStyle,
              border: currentSymbol === pattern.symbol ? "2px solid #22c55e" : "1px solid #333"
            }}
            onClick={() => onPatternSelect?.(pattern)}
          >
            {/* Card Header */}
            <div style={cardHeaderStyle}>
              <div style={symbolPatternStyle}>
                <span style={cardSymbolStyle}>{pattern.symbol}</span>
                <span style={patternTypeStyle}>
                  {getPatternEmoji(pattern.pattern_type)} {pattern.pattern_type}
                </span>
              </div>
              <div style={{
                ...outcomeStyle,
                color: getOutcomeColor(pattern.outcome, pattern.return_pct)
              }}>
                {getOutcomeIcon(pattern.outcome, pattern.return_pct)} {pattern.outcome}
              </div>
            </div>

            {/* Metrics */}
            <div style={metricsStyle}>
              <div style={metricStyle}>
                <span>Similarity</span>
                <span style={metricValueStyle}>{(pattern.similarity_score * 100).toFixed(0)}%</span>
              </div>
              <div style={metricStyle}>
                <span>Volume</span>
                <span style={metricValueStyle}>{pattern.volume_spike.toFixed(1)}x</span>
              </div>
              <div style={metricStyle}>
                <span>Return</span>
                <span style={{
                  ...metricValueStyle,
                  color: getOutcomeColor(pattern.outcome, pattern.return_pct)
                }}>
                  {pattern.return_pct ? `${pattern.return_pct >= 0 ? "+" : ""}${pattern.return_pct.toFixed(1)}%` : "TBD"}
                </span>
              </div>
            </div>

            {/* Price Info */}
            <div style={priceInfoStyle}>
              <span>Entry: ${pattern.entry_price.toFixed(2)}</span>
              {pattern.current_price && (
                <span>Current: ${pattern.current_price.toFixed(2)}</span>
              )}
            </div>

            {/* Date */}
            <div style={dateStyle}>
              {new Date(pattern.date_detected).toLocaleDateString()}
            </div>

            {/* Thesis Preview */}
            {pattern.thesis && (
              <div style={thesisPreviewStyle}>
                "{pattern.thesis.slice(0, 80)}{pattern.thesis.length > 80 ? "..." : ""}"
              </div>
            )}
          </div>
        ))}
      </div>

      {filteredPatterns.length === 0 && (
        <div style={emptyStyle}>
          No patterns found for "{filter}" filter
        </div>
      )}
    </div>
  );
}

// Styles
const containerStyle: React.CSSProperties = {
  background: "linear-gradient(135deg, #1a1a1a 0%, #111 100%)",
  border: "1px solid #333",
  borderRadius: "16px",
  padding: "20px",
  color: "#fff"
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "20px",
  paddingBottom: "16px",
  borderBottom: "1px solid #333"
};

const titleStyle: React.CSSProperties = {
  fontSize: "20px",
  fontWeight: 800,
  color: "#fff"
};

const statsStyle: React.CSSProperties = {
  display: "flex",
  gap: "16px",
  fontSize: "14px",
  color: "#22c55e",
  fontWeight: 600
};

const filtersStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "20px",
  gap: "16px"
};

const filterGroupStyle: React.CSSProperties = {
  display: "flex",
  gap: "8px"
};

const filterButtonStyle: React.CSSProperties = {
  padding: "8px 16px",
  borderRadius: "8px",
  border: "1px solid #444",
  background: "transparent",
  color: "#ccc",
  fontSize: "13px",
  fontWeight: 600,
  cursor: "pointer",
  transition: "all 0.2s ease"
};

const sortSelectStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderRadius: "8px",
  border: "1px solid #444",
  background: "#1a1a1a",
  color: "#fff",
  fontSize: "13px"
};

const patternGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
  gap: "16px"
};

const patternCardStyle: React.CSSProperties = {
  background: "rgba(255, 255, 255, 0.02)",
  border: "1px solid #333",
  borderRadius: "12px",
  padding: "16px",
  cursor: "pointer",
  transition: "all 0.2s ease"
};

const cardHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "12px"
};

const symbolPatternStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "4px"
};

const cardSymbolStyle: React.CSSProperties = {
  fontSize: "16px",
  fontWeight: 800,
  color: "#fff"
};

const patternTypeStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#22c55e",
  fontWeight: 600
};

const outcomeStyle: React.CSSProperties = {
  fontSize: "12px",
  fontWeight: 700,
  textTransform: "uppercase"
};

const metricsStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr 1fr",
  gap: "12px",
  marginBottom: "12px"
};

const metricStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "2px",
  fontSize: "12px",
  color: "#999"
};

const metricValueStyle: React.CSSProperties = {
  fontSize: "14px",
  fontWeight: 700,
  color: "#fff"
};

const priceInfoStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  fontSize: "13px",
  color: "#ccc",
  marginBottom: "8px"
};

const dateStyle: React.CSSProperties = {
  fontSize: "11px",
  color: "#666",
  marginBottom: "8px"
};

const thesisPreviewStyle: React.CSSProperties = {
  fontSize: "11px",
  color: "#999",
  fontStyle: "italic",
  lineHeight: 1.4,
  padding: "8px",
  background: "rgba(0, 0, 0, 0.3)",
  borderRadius: "6px"
};

const loadingStyle: React.CSSProperties = {
  textAlign: "center",
  padding: "40px",
  color: "#999",
  fontSize: "16px"
};

const errorStyle: React.CSSProperties = {
  textAlign: "center",
  padding: "40px",
  color: "#ef4444",
  fontSize: "16px"
};

const emptyStyle: React.CSSProperties = {
  textAlign: "center",
  padding: "40px",
  color: "#666",
  fontSize: "16px",
  fontStyle: "italic"
};