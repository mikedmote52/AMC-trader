import React, { useState, useEffect } from "react";
// Portfolio Actions Integration v2
import SqueezeAlert from "./SqueezeAlert";
import PatternHistory from "./PatternHistory";
import { API_BASE } from "../config";
import { getJSON } from "../lib/api";

interface SqueezeOpportunity {
  symbol: string;
  squeeze_score: number;
  volume_spike: number;
  short_interest: number;
  price: number;
  pattern_type?: string;
  confidence?: number;
  detected_at: string;
  advanced_score?: number;
  success_probability?: number;
  action?: string;
  vigl_similarity?: number;
  position_size_pct?: number;
}

interface SqueezeMonitorProps {
  watchedSymbols?: string[];
  showPatternHistory?: boolean;
  strategy?: 'legacy_v0' | 'hybrid_v1';
  minScore?: number;
}

interface PortfolioAction {
  type: 'immediate' | 'trim' | 'add' | 'stop_loss';
  symbol?: string;
  action: string;
  priority?: number;
  urgency?: string;
}

export default function SqueezeMonitor({ 
  watchedSymbols = [], 
  showPatternHistory = true,
  strategy = 'hybrid_v1',
  minScore = 40
}: SqueezeMonitorProps) {
  const [squeezeOpportunities, setSqueezeOpportunities] = useState<SqueezeOpportunity[]>([]);
  const [portfolioActions, setPortfolioActions] = useState<PortfolioAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [systemState, setSystemState] = useState("UNKNOWN");
  const [debugInfo, setDebugInfo] = useState<any>(null);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [lastApiCall, setLastApiCall] = useState<{url: string, candidateCount: number, timestamp: string, strategy: string} | null>(null);
  const [currentStrategy, setCurrentStrategy] = useState<'legacy_v0' | 'hybrid_v1'>(strategy);
  const [currentMinScore, setCurrentMinScore] = useState(minScore);

  const getRefreshInterval = () => {
    const now = new Date();
    const currentHour = now.getHours();
    const isWeekend = now.getDay() === 0 || now.getDay() === 6; // Sunday = 0, Saturday = 6
    
    // Convert to ET (approximate - for more precision, use a timezone library)
    const etHour = currentHour - 5; // Rough EST conversion (ignoring DST)
    
    if (isWeekend) {
      return 15 * 60 * 1000; // 15 minutes on weekends
    } else if (etHour >= 9.5 && etHour < 16) { // 9:30am - 4pm ET (market hours)
      return 5 * 60 * 1000; // 5 minutes during trading hours
    } else if ((etHour >= 4 && etHour < 9.5) || (etHour >= 16 && etHour < 20)) { // Extended hours
      return 10 * 60 * 1000; // 10 minutes during extended hours
    } else {
      return 20 * 60 * 1000; // 20 minutes overnight
    }
  };

  useEffect(() => {
    loadSqueezeOpportunities();
    
    // Set interval based on market hours
    const refreshInterval = getRefreshInterval();
    const interval = setInterval(loadSqueezeOpportunities, refreshInterval);
    
    // Log the refresh rate for transparency
    const minutes = refreshInterval / 60000;
    console.log(`Scanner refresh rate: ${minutes} minutes`);
    
    return () => clearInterval(interval);
  }, [watchedSymbols, currentStrategy, currentMinScore]);

  const loadSqueezeOpportunities = async () => {
    try {
      setLoading(true);
      setError("");
      
      // PRODUCTION: Use only contenders endpoint (never test endpoint)
      const useTestEndpoint = import.meta.env.VITE_USE_TEST_ENDPOINT === 'true' && import.meta.env.DEV;
      
      let discoveryResponse: any;
      let systemState = "UNKNOWN";
      let reasonStats = {};
      
      if (useTestEndpoint) {
        discoveryResponse = await getJSON<any>(`${API_BASE}/discovery/test?strategy=${currentStrategy}&limit=20`);
      } else {
        // FIXED: Use correct endpoint with strategy parameter and integer scale (0-100)
        const apiUrl = `${API_BASE}/discovery/squeeze-candidates?strategy=${currentStrategy}&min_score=${currentMinScore}&cache=${Date.now()}`;
        const response = await fetch(apiUrl, {
          cache: 'no-store'
        });
        
        // Read system state headers
        systemState = response.headers.get('X-System-State') || 'UNKNOWN';
        const reasonStatsHeader = response.headers.get('X-Reason-Stats');
        reasonStats = reasonStatsHeader ? JSON.parse(reasonStatsHeader) : {};
        
        discoveryResponse = await response.json();
        
        // FIXED: Track API call details for debugging with strategy
        setLastApiCall({
          url: apiUrl,
          candidateCount: discoveryResponse?.candidates?.length || 0,
          timestamp: new Date().toLocaleTimeString(),
          strategy: currentStrategy
        });
      }
      
      // Also get portfolio optimization actions
      const portfolioResponse = await getJSON<any>(`${API_BASE}/portfolio/immediate-actions`).catch(() => ({ success: false }));
      
      // Transform discovery candidates to squeeze opportunities format (test endpoint uses .items)
      const candidates = Array.isArray(discoveryResponse?.items) ? discoveryResponse.items :
                         Array.isArray(discoveryResponse?.candidates) ? discoveryResponse.candidates :
                         Array.isArray(discoveryResponse?.squeeze_candidates) ? discoveryResponse.squeeze_candidates :
                         Array.isArray(discoveryResponse) ? discoveryResponse : [];
      
      // FIXED: Handle both 0-1 and 0-100 scales from API response
      const normalizeScore = (score: number) => {
        if (!score) return 0;
        return score > 1 ? score / 100 : score; // Convert 0-100 to 0-1 if needed
      };
      
      const response: SqueezeOpportunity[] = candidates.map((candidate: any) => ({
            symbol: candidate.symbol,
            squeeze_score: normalizeScore(candidate.squeeze_score || candidate.score || 0),
            volume_spike: candidate.factors?.volume_spike_ratio || candidate.volume_spike || 0,
            short_interest: candidate.short_interest_data?.percent * 100 || candidate.short_interest || 0,
            price: candidate.price || 0,
            pattern_type: candidate.action_tag || candidate.pattern_match || 'WATCH',
            confidence: normalizeScore(candidate.confidence || candidate.score || 0),
            detected_at: new Date().toISOString(),
            advanced_score: normalizeScore(candidate.score || 0),
            success_probability: normalizeScore(candidate.confidence || candidate.score || 0),
            action: candidate.action_tag || 'WATCH',
            vigl_similarity: candidate.vigl_similarity || 0,
            position_size_pct: candidate.position_size_pct || 0
          }));
      
      // Only use real advanced ranking data
      let opportunities: SqueezeOpportunity[] = [];
      if (Array.isArray(response) && response.length > 0) {
        opportunities = response.map(item => ({
          symbol: item.symbol,
          squeeze_score: item.advanced_score || item.squeeze_score || 0,
          volume_spike: item.volume_spike || 0,
          short_interest: item.short_interest || 0,
          price: item.price || 0,
          pattern_type: item.action || item.pattern_type || 'BUY',
          confidence: item.success_probability || item.confidence || 0,
          detected_at: new Date().toISOString(),
          advanced_score: item.advanced_score,
          success_probability: item.success_probability,
          action: item.action,
          vigl_similarity: item.vigl_similarity,
          position_size_pct: item.position_size_pct
        // FIXED: Remove redundant client-side filtering since API already filters by min_score
        })); // API already filtered by min_score parameter
      }
      
      if (watchedSymbols.length > 0) {
        opportunities = opportunities.filter(opp => watchedSymbols.includes(opp.symbol));
      }
      
      // Update system state
      setSystemState(systemState);
      
      // If healthy system but no candidates, get debug info
      let debugInfo = null;
      if (!useTestEndpoint && systemState === "HEALTHY" && opportunities.length === 0) {
        try {
          debugInfo = await getJSON<any>(`${API_BASE}/discovery/contenders/debug?strategy=${currentStrategy}`);
          console.log("Debug info:", debugInfo);
          setDebugInfo(debugInfo);
        } catch (e) {
          console.warn("Debug endpoint not available:", e);
        }
      }

      // Sort by advanced score descending (1.0 = strongest)
      opportunities.sort((a, b) => (b.advanced_score || b.squeeze_score) - (a.advanced_score || a.squeeze_score));
      
      setSqueezeOpportunities(opportunities);
      
      // Process portfolio actions
      const actions: PortfolioAction[] = [];
      if (portfolioResponse.success && portfolioResponse.data?.immediate_actions) {
        portfolioResponse.data.immediate_actions.forEach((actionText: string, index: number) => {
          actions.push({
            type: actionText.includes('stop-loss') ? 'stop_loss' : 
                  actionText.includes('Trim') ? 'trim' :
                  actionText.includes('adding') ? 'add' : 'immediate',
            action: actionText,
            priority: index + 1,
            urgency: actionText.includes('URGENT') ? 'HIGH' : 
                    actionText.includes('Monitor') ? 'MEDIUM' : 'LOW'
          });
        });
      }
      setPortfolioActions(actions);
      
    } catch (err: any) {
      console.error("Squeeze monitoring error:", err);
      
      // Enhanced error messaging for common integration issues
      let errorMessage = "Failed to load squeeze opportunities";
      if (err?.message?.includes('timeout')) {
        errorMessage = "Discovery system timeout - this may indicate heavy load or system startup";
      } else if (err?.message?.includes('404') || err?.message?.includes('Not Found')) {
        errorMessage = "Discovery endpoint not available - check API deployment";
      } else if (err?.message?.includes('500')) {
        errorMessage = "Discovery system error - backend processing issue";
      } else if (err?.message) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleTradeExecuted = (result: any) => {
    console.log("Trade executed:", result);
    // Refresh opportunities after trade
    setTimeout(loadSqueezeOpportunities, 2000);
  };

  // Categorize opportunities by advanced score tiers (SAFE THRESHOLDS)
  const categorizeOpportunities = (opportunities: SqueezeOpportunity[]) => {
    const critical = opportunities.filter(opp => (opp.advanced_score || opp.squeeze_score) >= 0.70); // STRONG_BUY (70%+)
    const developing = opportunities.filter(opp => (opp.advanced_score || opp.squeeze_score) >= 0.50 && (opp.advanced_score || opp.squeeze_score) < 0.70); // BUY (50-70%)
    const early = opportunities.filter(opp => (opp.advanced_score || opp.squeeze_score) >= 0.30 && (opp.advanced_score || opp.squeeze_score) < 0.50); // WATCH (30-50%)
    
    return { critical, developing, early };
  };

  const handleSignificantMove = (symbol: string, changePercent: number) => {
    console.log(`Significant move detected: ${symbol} ${changePercent.toFixed(2)}%`);
    
    // Show browser notification if supported
    if ("Notification" in window && Notification.permission === "granted") {
      new Notification(`${symbol} Alert`, {
        body: `${changePercent > 0 ? "📈" : "📉"} ${Math.abs(changePercent).toFixed(1)}% move detected`,
        icon: "/favicon.ico"
      });
    }
  };

  // Request notification permission on mount
  useEffect(() => {
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }
  }, []);

  if (loading) {
    return (
      <div style={containerStyle}>
        <div style={loadingStyle}>🔍 Scanning for squeeze opportunities...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={containerStyle}>
        <div style={errorStyle}>❌ Error: {error}</div>
        <button onClick={loadSqueezeOpportunities} style={retryButtonStyle}>
          🔄 Retry
        </button>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      {/* Test Mode Banner */}
      {import.meta.env.VITE_USE_TEST_ENDPOINT === 'true' && import.meta.env.DEV && (
        <div style={{
          backgroundColor: 'rgba(234, 179, 8, 0.1)',
          border: '1px solid rgba(234, 179, 8, 0.3)',
          borderRadius: '8px',
          padding: '12px',
          marginBottom: '16px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <div style={{
            width: '8px',
            height: '8px',
            backgroundColor: '#facc15',
            borderRadius: '50%',
            animation: 'pulse 2s infinite'
          }}></div>
          <span style={{ color: '#fcd34d', fontWeight: '500' }}>
            TEST MODE - Using development endpoint
          </span>
        </div>
      )}

      {/* Debug Overlay - Show API call details */}
      {import.meta.env.DEV && lastApiCall && (
        <div style={{
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          border: '1px solid rgba(59, 130, 246, 0.3)',
          borderRadius: '8px',
          padding: '12px',
          marginBottom: '16px',
          fontSize: '14px'
        }}>
          <div style={{ color: '#93c5fd', fontWeight: '500', marginBottom: '8px' }}>
            🔍 API Debug Info
          </div>
          <div style={{ color: '#e5e7eb', fontSize: '13px', lineHeight: '1.4' }}>
            <div>Endpoint: {lastApiCall.url}</div>
            <div>Strategy: {lastApiCall.strategy}</div>
            <div>Min Score: {currentMinScore}% (threshold)</div>
            <div>Candidates received: {lastApiCall.candidateCount}</div>
            <div>Candidates displayed: {squeezeOpportunities.length}</div>
            <div>Last call: {lastApiCall.timestamp}</div>
            <div style={{ marginTop: '4px', color: '#9ca3af', fontSize: '12px' }}>
              System State: {systemState}
            </div>
          </div>
        </div>
      )}

      {/* System Status Bar */}
      {!import.meta.env.DEV && (
        <div style={{
          backgroundColor: systemState === 'HEALTHY' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
          border: `1px solid ${systemState === 'HEALTHY' ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
          borderRadius: '8px',
          padding: '8px 12px',
          marginBottom: '16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '14px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              width: '8px',
              height: '8px',
              backgroundColor: systemState === 'HEALTHY' ? '#22c55e' : '#ef4444',
              borderRadius: '50%'
            }}></div>
            <span style={{ color: systemState === 'HEALTHY' ? '#86efac' : '#fca5a5' }}>
              {systemState === 'HEALTHY' ? 'System Healthy' : 'Live market data degraded — signals paused'}
            </span>
          </div>
          <span style={{ color: '#9ca3af', fontSize: '12px' }}>
            {squeezeOpportunities.length} candidates
          </span>
        </div>
      )}

      {/* Header */}
      <div style={headerStyle}>
        <div style={titleStyle}>
          🚨 Squeeze Monitor
          {squeezeOpportunities.length > 0 && (
            <span style={countBadgeStyle}>
              {squeezeOpportunities.length} Active
            </span>
          )}
        </div>
        
        <div style={actionsStyle}>
          {/* Strategy Selector */}
          <select 
            value={currentStrategy}
            onChange={(e) => setCurrentStrategy(e.target.value as 'legacy_v0' | 'hybrid_v1')}
            style={{
              ...actionButtonStyle,
              backgroundColor: "#1a1a1a",
              color: "#fff",
              padding: "6px 12px",
              minWidth: "120px"
            }}
          >
            <option value="legacy_v0">Legacy V0</option>
            <option value="hybrid_v1">Hybrid V1</option>
          </select>
          
          {/* Min Score Slider */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: '#ccc', fontSize: '12px' }}>Min Score:</span>
            <input
              type="range"
              min="10"
              max="80"
              step="5"
              value={currentMinScore}
              onChange={(e) => setCurrentMinScore(Number(e.target.value))}
              style={{ width: '60px' }}
            />
            <span style={{ color: '#ccc', fontSize: '12px', minWidth: '30px' }}>{currentMinScore}%</span>
          </div>
          
          {showPatternHistory && (
            <button 
              onClick={() => setShowHistory(!showHistory)}
              style={{
                ...actionButtonStyle,
                backgroundColor: showHistory ? "#22c55e" : "transparent"
              }}
            >
              📈 Pattern History
            </button>
          )}
          
          <button onClick={loadSqueezeOpportunities} style={actionButtonStyle}>
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Tiered Alerts Section */}
      {squeezeOpportunities.length > 0 && (() => {
        const { critical, developing, early } = categorizeOpportunities(squeezeOpportunities);
        
        return (
          <div style={alertsSectionStyle}>
            {/* Critical Alerts */}
            {critical.length > 0 && (
              <div style={{ marginBottom: '24px' }}>
                <div style={{ ...sectionTitleStyle, color: '#dc2626' }}>🚨 STRONG BUY SIGNALS ({critical.length})</div>
                <div style={alertsGridStyle}>
                  {critical.map((opportunity, index) => (
                    <SqueezeAlert
                      key={`critical-${opportunity.symbol}-${index}`}
                      symbol={opportunity.symbol}
                      metrics={opportunity}
                      onTradeExecuted={handleTradeExecuted}
                      alertTier="CRITICAL"
                    />
                  ))}
                </div>
              </div>
            )}
            
            {/* Developing Alerts */}
            {developing.length > 0 && (
              <div style={{ marginBottom: '24px' }}>
                <div style={{ ...sectionTitleStyle, color: '#f59e0b' }}>⚡ BUY OPPORTUNITIES ({developing.length})</div>
                <div style={alertsGridStyle}>
                  {developing.map((opportunity, index) => (
                    <SqueezeAlert
                      key={`developing-${opportunity.symbol}-${index}`}
                      symbol={opportunity.symbol}
                      metrics={opportunity}
                      onTradeExecuted={handleTradeExecuted}
                      alertTier="DEVELOPING"
                    />
                  ))}
                </div>
              </div>
            )}
            
            {/* Early Signals */}
            {early.length > 0 && (
              <div style={{ marginBottom: '24px' }}>
                <div style={{ ...sectionTitleStyle, color: '#eab308' }}>📊 WATCH CANDIDATES ({early.length})</div>
                <div style={alertsGridStyle}>
                  {early.map((opportunity, index) => (
                    <SqueezeAlert
                      key={`early-${opportunity.symbol}-${index}`}
                      symbol={opportunity.symbol}
                      metrics={opportunity}
                      onTradeExecuted={handleTradeExecuted}
                      alertTier="EARLY"
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })()}

      {/* Quick Summary Section */}
      {squeezeOpportunities.length > 0 && (
        <div style={pnlSectionStyle}>
          <div style={sectionTitleStyle}>📊 Active Monitoring ({squeezeOpportunities.length} symbols)</div>
          
          <div style={summaryGridStyle}>
            {squeezeOpportunities.slice(0, 6).map((opportunity, index) => (
              <div key={`summary-${opportunity.symbol}-${index}`} style={summaryCardStyle}>
                <div style={symbolHeaderStyle}>
                  <span style={symbolTextStyle}>{opportunity.symbol}</span>
                  <span style={priceTextStyle}>${opportunity.price.toFixed(2)}</span>
                </div>
                <div style={scoreRowStyle}>
                  <span style={scoreTextStyle}>Score: {((opportunity.advanced_score || opportunity.squeeze_score) * 100).toFixed(0)}% | {opportunity.action || 'EVAL'}</span>
                  <span style={{
                    ...confidenceTextStyle,
                    color: (opportunity.success_probability || opportunity.confidence) >= 0.7 ? '#22c55e' : (opportunity.success_probability || opportunity.confidence) >= 0.5 ? '#f59e0b' : '#ef4444'
                  }}>
                    {Math.round((opportunity.success_probability || opportunity.confidence) * 100)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
          
          {squeezeOpportunities.length > 6 && (
            <div style={moreCountStyle}>
              +{squeezeOpportunities.length - 6} more symbols being monitored
            </div>
          )}
        </div>
      )}

      {/* Pattern History */}
      {showHistory && (
        <div style={historySectionStyle}>
          <PatternHistory
            currentSymbol={selectedSymbol || undefined}
            onPatternSelect={(pattern) => {
              setSelectedSymbol(pattern.symbol);
              console.log("Selected pattern:", pattern);
            }}
          />
        </div>
      )}

      {/* No Opportunities Message + Portfolio Actions */}
      {squeezeOpportunities.length === 0 && (
        <div style={noOpportunitiesStyle}>
          <div style={noOpportunitiesIconStyle}>🔍</div>
          <div style={noOpportunitiesTextStyle}>
            No squeeze opportunities detected
          </div>

          {/* Debug Information for HEALTHY system with no candidates */}
          {systemState === 'HEALTHY' && debugInfo && (
            <div style={{
              backgroundColor: 'rgba(59, 130, 246, 0.1)',
              border: '1px solid rgba(59, 130, 246, 0.3)',
              borderRadius: '8px',
              padding: '12px',
              marginTop: '16px',
              fontSize: '14px'
            }}>
              <div style={{ color: '#93c5fd', fontWeight: '500', marginBottom: '8px' }}>
                🔍 System Diagnostics
              </div>
              <div style={{ color: '#e5e7eb', fontSize: '13px', lineHeight: '1.4' }}>
                <div>Symbols processed: {debugInfo.summary?.symbols_in || 0}</div>
                <div>After filtering: {debugInfo.summary?.after_freshness || 0}</div>
                <div>Watchlist eligible: {debugInfo.summary?.watchlist || 0}</div>
                <div>Trade ready: {debugInfo.summary?.trade_ready || 0}</div>
                {debugInfo.drop_reasons?.length > 0 && (
                  <div style={{ marginTop: '8px' }}>
                    <div style={{ color: '#93c5fd', fontSize: '12px' }}>Top drop reasons:</div>
                    {debugInfo.drop_reasons.slice(0, 3).map((reason: any, i: number) => (
                      <div key={i} style={{ fontSize: '12px', color: '#9ca3af' }}>
                        • {reason.reason}: {reason.count}
                      </div>
                    ))}
                  </div>
                )}
                <div style={{ marginTop: '8px', fontSize: '12px', color: '#6b7280' }}>
                  Thresholds: {debugInfo.config_snapshot?.gates?.watchlist_min}% watchlist, {debugInfo.config_snapshot?.gates?.trade_ready_min}% trade ready
                </div>
              </div>
            </div>
          )}
          
          {/* Portfolio Management Actions */}
          {portfolioActions.length > 0 && (
            <div style={{...noOpportunitiesSubTextStyle, marginBottom: 16, backgroundColor: '#1f2937', padding: 16, borderRadius: 8, border: '1px solid #374151'}}>
              <div style={{color: '#10b981', fontWeight: 'bold', marginBottom: 8}}>
                📈 Portfolio Management Actions Required:
              </div>
              {portfolioActions.map((action, index) => (
                <div key={index} style={{
                  marginBottom: 6,
                  padding: '6px 10px',
                  backgroundColor: action.urgency === 'HIGH' ? '#ef44441a' : 
                                  action.urgency === 'MEDIUM' ? '#f59e0b1a' : '#10b9811a',
                  borderRadius: 4,
                  fontSize: 13,
                  color: action.urgency === 'HIGH' ? '#fca5a5' : 
                         action.urgency === 'MEDIUM' ? '#fcd34d' : '#86efac',
                  border: `1px solid ${action.urgency === 'HIGH' ? '#ef4444' : 
                                      action.urgency === 'MEDIUM' ? '#f59e0b' : '#10b981'}33`
                }}>
                  {action.urgency === 'HIGH' && '🚨 '}
                  {action.urgency === 'MEDIUM' && '⚠️ '}
                  {action.urgency === 'LOW' && '💡 '}
                  {action.action}
                </div>
              ))}
            </div>
          )}
          
          <div style={{...noOpportunitiesSubTextStyle, marginBottom: 16}}>
            <strong>Why no squeezes right now:</strong><br/>
            • Advanced scores below 0.10 threshold (need 10%+ probability)<br/>
            • Volume patterns not meeting discovery criteria<br/>
            • Current market conditions limiting squeeze setups<br/>
            • System recently updated - scanning for new opportunities<br/>
            • Discovery pipeline processing 7,000+ stocks
          </div>
          <div style={{fontSize: 12, color: '#555', fontStyle: 'italic', marginBottom: 12}}>
            💡 <strong>Advanced Discovery Active:</strong> Monitoring {watchedSymbols.length > 0 ? watchedSymbols.join(", ") : "7,000+ symbols"} for:<br/>
            - High short interest (&gt;20%)<br/>
            - Low float (&lt;50M shares)<br/>
            - Volume surges (&gt;10x average)<br/>
            - Price compression patterns
          </div>
          <div style={{fontSize: 11, color: '#777', textAlign: 'center'}}>
            Last scan: {new Date().toLocaleTimeString()} • Next scan: {new Date(Date.now() + 300000).toLocaleTimeString()}
          </div>
        </div>
      )}

      {/* Quick Stats */}
      <div style={statsFooterStyle}>
        <div style={statItemStyle}>
          <span>🎯 Active Alerts</span>
          <span>{squeezeOpportunities.length}</span>
        </div>
        <div style={statItemStyle}>
          <span>💼 Portfolio Actions</span>
          <span>{portfolioActions.length}</span>
        </div>
        <div style={statItemStyle}>
          <span>⏱️ Last Update</span>
          <span>{new Date().toLocaleTimeString()}</span>
        </div>
        <div style={statItemStyle}>
          <span>📈 Monitoring</span>
          <span>{watchedSymbols.length > 0 ? `${watchedSymbols.length} symbols` : "All symbols"}</span>
        </div>
      </div>
    </div>
  );
}

// Styles
const containerStyle: React.CSSProperties = {
  color: "#fff"
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "24px",
  padding: "20px",
  background: "linear-gradient(135deg, #1a1a1a 0%, #111 100%)",
  borderRadius: "16px",
  border: "1px solid #333"
};

const titleStyle: React.CSSProperties = {
  fontSize: "24px",
  fontWeight: 800,
  color: "#fff",
  display: "flex",
  alignItems: "center",
  gap: "12px"
};

const countBadgeStyle: React.CSSProperties = {
  background: "#ef4444",
  color: "#fff",
  padding: "4px 12px",
  borderRadius: "12px",
  fontSize: "12px",
  fontWeight: 700,
  textTransform: "uppercase"
};

const actionsStyle: React.CSSProperties = {
  display: "flex",
  gap: "12px"
};

const actionButtonStyle: React.CSSProperties = {
  padding: "8px 16px",
  borderRadius: "8px",
  border: "1px solid #444",
  background: "transparent",
  color: "#ccc",
  fontSize: "14px",
  fontWeight: 600,
  cursor: "pointer",
  transition: "all 0.2s ease"
};

const alertsSectionStyle: React.CSSProperties = {
  marginBottom: "32px"
};

const sectionTitleStyle: React.CSSProperties = {
  fontSize: "18px",
  fontWeight: 700,
  color: "#fff",
  marginBottom: "16px",
  textTransform: "uppercase",
  letterSpacing: "1px"
};

const alertsGridStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "16px"
};

const pnlSectionStyle: React.CSSProperties = {
  marginBottom: "32px"
};

const summaryGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
  gap: "12px",
  marginBottom: "16px"
};

const summaryCardStyle: React.CSSProperties = {
  background: "#111",
  border: "1px solid #333",
  borderRadius: "8px",
  padding: "12px"
};

const symbolHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "8px"
};

const symbolTextStyle: React.CSSProperties = {
  fontSize: "16px",
  fontWeight: 700,
  color: "#fff"
};

const priceTextStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#22c55e",
  fontWeight: 600
};

const scoreRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center"
};

const scoreTextStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#ccc"
};

const confidenceTextStyle: React.CSSProperties = {
  fontSize: "12px",
  fontWeight: 700,
  padding: "2px 6px",
  borderRadius: "4px",
  backgroundColor: "rgba(255,255,255,0.1)"
};

const moreCountStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#999",
  textAlign: "center",
  fontStyle: "italic"
};

const historySectionStyle: React.CSSProperties = {
  marginBottom: "32px"
};

const noOpportunitiesStyle: React.CSSProperties = {
  textAlign: "center",
  padding: "60px 20px",
  background: "linear-gradient(135deg, #1a1a1a 0%, #111 100%)",
  borderRadius: "16px",
  border: "1px solid #333"
};

const noOpportunitiesIconStyle: React.CSSProperties = {
  fontSize: "48px",
  marginBottom: "16px"
};

const noOpportunitiesTextStyle: React.CSSProperties = {
  fontSize: "18px",
  fontWeight: 600,
  color: "#ccc",
  marginBottom: "8px"
};

const noOpportunitiesSubTextStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#666"
};

const statsFooterStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
  gap: "16px",
  padding: "20px",
  background: "rgba(255, 255, 255, 0.02)",
  borderRadius: "12px",
  border: "1px solid #333"
};

const statItemStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  fontSize: "14px",
  color: "#ccc"
};

const loadingStyle: React.CSSProperties = {
  textAlign: "center",
  padding: "60px",
  fontSize: "18px",
  color: "#999"
};

const errorStyle: React.CSSProperties = {
  textAlign: "center",
  padding: "40px",
  fontSize: "16px",
  color: "#ef4444"
};

const retryButtonStyle: React.CSSProperties = {
  padding: "12px 24px",
  borderRadius: "8px",
  border: "1px solid #ef4444",
  background: "transparent",
  color: "#ef4444",
  fontSize: "14px",
  fontWeight: 600,
  cursor: "pointer",
  marginTop: "16px"
};