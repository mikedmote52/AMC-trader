import React, { useEffect, useState } from "react";
import { API_BASE } from "../config";
import { getJSON } from "../lib/api";
import RecommendationCard from "./RecommendationCard";

type Candidate = {
  symbol: string;
  price?: number | null;
  score?: number | null;
  confidence?: number | null;
  thesis?: string | null;
  thesis_rich?: any | null;
  atr_pct?: number | null;
  dollar_vol?: number | null;
  rel_vol_30m?: number | null;
  reason?: string | null;
};

type DiagnosticData = {
  discovery_status: {
    last_run: string;
    status: string;
    total_stocks_scanned: number;
    candidates_found: number;
    processing_time: string;
    error?: string;
  };
  filtering_breakdown: {
    initial_universe: number;
    after_price_filter: number;
    after_volume_filter: number;
    after_momentum_filter: number;
    after_pattern_matching: number;
    after_confidence_filter: number;
    final_candidates: number;
  };
  current_thresholds: {
    min_price: number;
    max_price: number;
    min_volume: number;
    min_confidence: number;
    min_score: number;
  };
  reasons_for_no_results: string[];
};

export default function Recommendations() {
  const [items, setItems] = useState<Candidate[]>([]);
  const [err, setErr] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [diagnostics, setDiagnostics] = useState<DiagnosticData | null>(null);

  useEffect(() => {
    let alive = true;
    async function run() {
      try {
        setLoading(true);
        setErr("");
        
        // Fetch both contenders and diagnostics
        const [contendersData, diagnosticsData] = await Promise.all([
          getJSON<any>(`${API_BASE}/discovery/contenders`),
          getJSON<DiagnosticData>(`${API_BASE}/discovery/diagnostics`)
        ]);
        
        const list: Candidate[] = Array.isArray(contendersData) ? contendersData : [];
        list.sort((a,b) => (b.score ?? 0) - (a.score ?? 0));
        
        if (alive) {
          setItems(list);
          setDiagnostics(diagnosticsData);
        }
      } catch (e:any) {
        if (alive) setErr(e?.message || String(e));
      } finally {
        if (alive) setLoading(false);
      }
    }
    run();
    const id = setInterval(run, 15_000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  if (loading) return <div style={{padding:12}}>🔍 Scanning market for opportunities…</div>;
  if (err) return <div style={{padding:12, color:"#c00"}}>❌ Error: {err}</div>;
  if (!items.length) return (
    <div style={{padding:12}}>
      <div style={{marginBottom: 12}}>
        <strong>📊 No high-confidence opportunities detected</strong>
      </div>
      
      {diagnostics && (
        <>
          <div style={{fontSize: 13, color: '#888', lineHeight: 1.5, marginBottom: 12}}>
            <strong>Discovery Pipeline Status:</strong><br/>
            • Last run: {diagnostics.discovery_status.last_run || 'Unknown'}<br/>
            • Status: {diagnostics.discovery_status.status}<br/>
            • Stocks scanned: {diagnostics.discovery_status.total_stocks_scanned?.toLocaleString() || 'Unknown'}<br/>
            • Processing time: {diagnostics.discovery_status.processing_time || 'Unknown'}
            {diagnostics.discovery_status.error && <span style={{color: '#ef4444'}}><br/>• Error: {diagnostics.discovery_status.error}</span>}
          </div>
          
          <div style={{fontSize: 13, color: '#888', lineHeight: 1.5, marginBottom: 12}}>
            <strong>Filtering Breakdown:</strong><br/>
            • Initial universe: {diagnostics.filtering_breakdown.initial_universe?.toLocaleString() || 0} stocks<br/>
            • After price filter (${diagnostics.current_thresholds.min_price}-${diagnostics.current_thresholds.max_price}): {diagnostics.filtering_breakdown.after_price_filter?.toLocaleString() || 0}<br/>
            • After volume filter (>{diagnostics.current_thresholds.min_volume?.toLocaleString()}): {diagnostics.filtering_breakdown.after_volume_filter?.toLocaleString() || 0}<br/>
            • After momentum filter: {diagnostics.filtering_breakdown.after_momentum_filter?.toLocaleString() || 0}<br/>
            • After pattern matching: {diagnostics.filtering_breakdown.after_pattern_matching?.toLocaleString() || 0}<br/>
            • After confidence filter (>{Math.round((diagnostics.current_thresholds.min_confidence || 0.75) * 100)}%): {diagnostics.filtering_breakdown.after_confidence_filter?.toLocaleString() || 0}<br/>
            • <strong>Final candidates: {diagnostics.filtering_breakdown.final_candidates}</strong>
          </div>
          
          {diagnostics.reasons_for_no_results && diagnostics.reasons_for_no_results.length > 0 && (
            <div style={{fontSize: 13, color: '#f59e0b', lineHeight: 1.5, marginBottom: 12}}>
              <strong>Why no results:</strong><br/>
              {diagnostics.reasons_for_no_results.map((reason, i) => (
                <span key={i}>• {reason}<br/></span>
              ))}
            </div>
          )}
        </>
      )}
      
      <button 
        onClick={() => window.location.reload()} 
        style={{padding: '8px 16px', background: '#22c55e', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600}}
      >
        🔄 Refresh Now
      </button>
    </div>
  );

  return (
    <div className="grid-responsive">
      {items.map((it) => (
        <RecommendationCard key={it.symbol} item={it} />
      ))}
    </div>
  );
}