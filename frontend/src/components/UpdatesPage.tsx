import React, { useEffect, useState } from "react";
import { API_BASE } from "../config";
import { getJSON } from "../lib/api";

type Update = {
  time: string;
  type: string;
  title: string;
  summary: string;
  details: any;
  sms_text: string;
  action_items: string[];
};

type LearningMetrics = {
  overall_health_score: number;
  pattern_learning: {
    success_rate: number;
    total_patterns_tracked: number;
    avg_success_return: number;
    max_winner_return: number;
  };
  discovery_optimization: {
    avg_success_rate: number;
    parameter_effectiveness: number;
    explosion_rate: number;
  };
  thesis_accuracy: {
    avg_accuracy_score: number;
    total_predictions: number;
  };
};

type DiscoveryCandidate = {
  symbol: string;
  price: number;
  squeeze_score: number;
  confidence: number;
  thesis: string;
  explosive_potential: string;
  is_vigl_class: boolean;
};

type PerformanceMetrics = {
  current: {
    average_return: number;
    win_rate: number;
    explosive_growth_rate: number;
    portfolio_value: number;
    best_performer?: { symbol: string; return: string };
  };
  recovery: {
    recovery_progress_pct: number;
    recovery_status: string;
    performance_gap: number;
    projected_recovery_date: string | null;
  };
  squeeze_analysis: {
    total_candidates_found: number;
    high_probability_count: number;
    vigl_similarity_found: boolean;
  };
};

export default function UpdatesPage() {
  const [updates, setUpdates] = useState<Update[]>([]);
  const [currentUpdate, setCurrentUpdate] = useState<Update | null>(null);
  const [loading, setLoading] = useState(true);
  const [smsStatus, setSmsStatus] = useState<string>("");
  const [learningMetrics, setLearningMetrics] = useState<LearningMetrics | null>(null);
  const [liveOpportunities, setLiveOpportunities] = useState<DiscoveryCandidate[]>([]);
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  useEffect(() => {
    const loadAllData = async () => {
      try {
        const [currentResponse, allResponse, learningResponse, opportunitiesResponse, performanceResponse] = await Promise.all([
          getJSON(`${API_BASE}/daily-updates/current`),
          getJSON(`${API_BASE}/daily-updates/all`),
          getJSON(`${API_BASE}/learning-analytics/learning/performance-summary?days_back=7`),
          getJSON(`${API_BASE}/discovery/squeeze-candidates?min_score=0.5`),
          getJSON(`${API_BASE}/analytics/performance`)
        ]);

        if (currentResponse?.success) {
          setCurrentUpdate(currentResponse.data);
        }

        if (allResponse?.success) {
          setUpdates(allResponse.data);
        }

        if (learningResponse?.success) {
          setLearningMetrics(learningResponse.learning_performance_summary);
        }

        if (opportunitiesResponse?.success) {
          setLiveOpportunities(opportunitiesResponse.candidates || []);
        }

        if (performanceResponse?.success) {
          setPerformanceMetrics(performanceResponse);
        }

        setLastRefresh(new Date());
      } catch (error) {
        console.error("Failed to load dashboard data:", error);
      } finally {
        setLoading(false);
      }
    };

    loadAllData();
    const interval = setInterval(loadAllData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const sendSMSUpdate = async (updateType: string = "current") => {
    try {
      setSmsStatus("Sending...");
      const response = await getJSON(`${API_BASE}/daily-updates/send-sms?update_type=${updateType}`);
      
      if (response?.success) {
        setSmsStatus(`✅ SMS sent to ...${response.phone_number}`);
      } else {
        setSmsStatus(`❌ Failed: ${response?.error || "Unknown error"}`);
      }
      
      setTimeout(() => setSmsStatus(""), 3000);
    } catch (error) {
      setSmsStatus("❌ SMS failed");
      setTimeout(() => setSmsStatus(""), 3000);
    }
  };

  if (loading) {
    return (
      <div style={pageStyle}>
        <div style={loadingStyle}>📱 Loading daily updates...</div>
      </div>
    );
  }

  return (
    <div style={pageStyle}>
      {/* Header */}
      <div style={headerStyle}>
        <h1 style={titleStyle}>📱 Daily Trading Updates</h1>
        <div style={subtitleStyle}>
          Real-time learning system monitoring and actionable insights • Last update: {lastRefresh.toLocaleTimeString()}
        </div>
      </div>

      {/* Learning System Status Dashboard */}
      {learningMetrics && (
        <div style={learningDashboardStyle}>
          <div style={dashboardHeaderStyle}>
            <h2 style={dashboardTitleStyle}>🧠 Learning System Performance</h2>
            <div style={healthScoreStyle}>
              <span style={healthLabelStyle}>Health Score:</span>
              <span style={{
                ...healthValueStyle,
                color: learningMetrics.overall_health_score > 0.8 ? '#22c55e' : 
                       learningMetrics.overall_health_score > 0.6 ? '#f59e0b' : '#ef4444'
              }}>
                {(learningMetrics.overall_health_score * 100).toFixed(1)}%
              </span>
            </div>
          </div>
          
          <div style={metricsGridStyle}>
            <div style={metricCardStyle}>
              <div style={metricLabelStyle}>Pattern Learning</div>
              <div style={metricValueStyle}>{(learningMetrics.pattern_learning.success_rate * 100).toFixed(1)}%</div>
              <div style={metricSubtextStyle}>
                {learningMetrics.pattern_learning.total_patterns_tracked} patterns • 
                Max winner: {learningMetrics.pattern_learning.max_winner_return.toFixed(1)}%
              </div>
            </div>
            
            <div style={metricCardStyle}>
              <div style={metricLabelStyle}>Discovery Engine</div>
              <div style={metricValueStyle}>{(learningMetrics.discovery_optimization.parameter_effectiveness * 100).toFixed(1)}%</div>
              <div style={metricSubtextStyle}>
                {(learningMetrics.discovery_optimization.explosion_rate * 100).toFixed(1)}% explosion rate
              </div>
            </div>
            
            <div style={metricCardStyle}>
              <div style={metricLabelStyle}>Thesis Accuracy</div>
              <div style={metricValueStyle}>{(learningMetrics.thesis_accuracy.avg_accuracy_score * 100).toFixed(1)}%</div>
              <div style={metricSubtextStyle}>
                {learningMetrics.thesis_accuracy.total_predictions} predictions
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Real-Time Opportunities */}
      {liveOpportunities.length > 0 && (
        <div style={opportunitiesStyle}>
          <h2 style={opportunitiesTitleStyle}>⚡ Live Opportunities - Early Detection</h2>
          <div style={opportunitiesGridStyle}>
            {liveOpportunities.slice(0, 3).map((opportunity, index) => (
              <div key={opportunity.symbol} style={{
                ...opportunityCardStyle,
                ...(opportunity.is_vigl_class && viglClassStyle)
              }}>
                <div style={opportunityHeaderStyle}>
                  <span style={symbolStyle}>{opportunity.symbol}</span>
                  <span style={priceStyle}>${opportunity.price.toFixed(2)}</span>
                </div>
                <div style={scoreStyle}>
                  Squeeze Score: {(opportunity.squeeze_score * 100).toFixed(1)}%
                </div>
                <div style={potentialStyle}>
                  {opportunity.explosive_potential} Potential
                  {opportunity.is_vigl_class && <span style={viglBadgeStyle}>VIGL-CLASS</span>}
                </div>
                <div style={thesisStyle}>
                  {opportunity.thesis.slice(0, 80)}...
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Performance Recovery Tracking */}
      {performanceMetrics && (
        <div style={recoveryTrackingStyle}>
          <h2 style={recoveryTitleStyle}>📈 Recovery Progress Tracking</h2>
          <div style={recoveryGridStyle}>
            <div style={recoveryCardStyle}>
              <div style={recoveryLabelStyle}>Recovery Status</div>
              <div style={{
                ...recoveryStatusStyle,
                color: performanceMetrics.recovery.recovery_status === 'ON_TRACK' ? '#22c55e' : 
                       performanceMetrics.recovery.recovery_status === 'BEHIND_SCHEDULE' ? '#ef4444' : '#f59e0b'
              }}>
                {performanceMetrics.recovery.recovery_status.replace('_', ' ')}
              </div>
              <div style={recoveryProgressStyle}>
                <div style={{
                  ...progressBarStyle,
                  width: `${Math.min(performanceMetrics.recovery.recovery_progress_pct, 100)}%`
                }}></div>
              </div>
              <div style={recoveryPercentStyle}>
                {performanceMetrics.recovery.recovery_progress_pct.toFixed(1)}% to +152% target
              </div>
            </div>
            
            <div style={recoveryCardStyle}>
              <div style={recoveryLabelStyle}>Current Performance</div>
              <div style={recoveryValueStyle}>
                {performanceMetrics.current.average_return > 0 ? '+' : ''}{performanceMetrics.current.average_return.toFixed(1)}%
              </div>
              <div style={recoverySubtextStyle}>
                Gap: {performanceMetrics.recovery.performance_gap > 0 ? '+' : ''}{performanceMetrics.recovery.performance_gap.toFixed(1)}%
              </div>
            </div>
            
            <div style={recoveryCardStyle}>
              <div style={recoveryLabelStyle}>Squeeze Detection</div>
              <div style={recoveryValueStyle}>
                {performanceMetrics.squeeze_analysis.total_candidates_found} found
              </div>
              <div style={recoverySubtextStyle}>
                {performanceMetrics.squeeze_analysis.high_probability_count} high-confidence
                {performanceMetrics.squeeze_analysis.vigl_similarity_found && 
                  <span style={viglDetectedStyle}>• VIGL-like detected</span>
                }
              </div>
            </div>
          </div>
          
          {performanceMetrics.recovery.projected_recovery_date && (
            <div style={projectionStyle}>
              🎯 Projected full recovery: {new Date(performanceMetrics.recovery.projected_recovery_date).toLocaleDateString()}
            </div>
          )}
        </div>
      )}

      {/* Current Update - Prominent */}
      {currentUpdate && (
        <div style={currentUpdateStyle}>
          <div style={currentHeaderStyle}>
            <div>
              <div style={currentTitleStyle}>{currentUpdate.title}</div>
              <div style={currentTimeStyle}>{currentUpdate.time}</div>
            </div>
            <button 
              onClick={() => sendSMSUpdate("current")}
              style={smsButtonStyle}
              disabled={smsStatus.includes("Sending")}
            >
              📱 Text Me Now
            </button>
          </div>
          
          <div style={currentSummaryStyle}>{currentUpdate.summary}</div>
          
          <div style={smsPreviewStyle}>
            <div style={smsLabelStyle}>SMS Preview:</div>
            <div style={smsTextStyle}>"{currentUpdate.sms_text}"</div>
          </div>

          {smsStatus && (
            <div style={smsStatusStyle}>{smsStatus}</div>
          )}
        </div>
      )}

      {/* All Updates Timeline */}
      <div style={timelineStyle}>
        <h2 style={timelineHeaderStyle}>📊 Today's Market Schedule</h2>
        
        <div style={timelineGridStyle}>
          {updates.map((update, index) => {
            const isActive = currentUpdate?.type === update.type;
            
            return (
              <div 
                key={update.type} 
                style={{
                  ...updateCardStyle,
                  ...(isActive && activeCardStyle)
                }}
              >
                <div style={cardHeaderStyle}>
                  <div style={cardTitleStyle}>{update.title}</div>
                  <div style={cardTimeStyle}>{update.time}</div>
                </div>
                
                <div style={cardSummaryStyle}>{update.summary}</div>
                
                {/* Key Details */}
                {update.details && (
                  <div style={detailsStyle}>
                    {Object.entries(update.details).slice(0, 2).map(([key, value]) => (
                      <div key={key} style={detailItemStyle}>
                        <span style={detailKeyStyle}>{key.replace('_', ' ')}:</span>
                        <span style={detailValueStyle}>{String(value)}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Action Items */}
                {update.action_items && update.action_items.length > 0 && (
                  <div style={actionItemsStyle}>
                    {update.action_items.slice(0, 2).map((item, i) => (
                      <div key={i} style={actionItemStyle}>• {item}</div>
                    ))}
                  </div>
                )}

                <button 
                  onClick={() => sendSMSUpdate(update.type)}
                  style={cardSmsButtonStyle}
                >
                  📱 Send This Update
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* System Intelligence Summary */}
      <div style={intelligenceSummaryStyle}>
        <h3 style={intelligenceTitleStyle}>🎯 What My System Learned Today</h3>
        <div style={intelligenceContentStyle}>
          <div style={intelligenceItemStyle}>
            <span style={intelligenceBulletStyle}>•</span>
            <span>Early detection threshold optimized: 2.5x volume vs 20x (catching opportunities faster)</span>
          </div>
          <div style={intelligenceItemStyle}>
            <span style={intelligenceBulletStyle}>•</span>
            <span>VIGL-pattern similarity tracking: {performanceMetrics?.squeeze_analysis?.vigl_similarity_found ? 'Active matches found' : 'Scanning for patterns'}</span>
          </div>
          <div style={intelligenceItemStyle}>
            <span style={intelligenceBulletStyle}>•</span>
            <span>Market regime: {learningMetrics ? 'Adaptive parameters active' : 'Baseline parameters'}</span>
          </div>
          <div style={intelligenceItemStyle}>
            <span style={intelligenceBulletStyle}>•</span>
            <span>Win/loss learning: {learningMetrics ? `${(learningMetrics.pattern_learning.success_rate * 100).toFixed(0)}% pattern success rate` : 'Building database'}</span>
          </div>
        </div>
        
        <div style={nextStepsStyle}>
          <div style={nextStepsHeaderStyle}>🚀 Next Actions</div>
          <div style={actionGridStyle}>
            {liveOpportunities.length > 0 && (
              <div style={actionItemStyle}>
                Monitor {liveOpportunities[0].symbol} for entry (${liveOpportunities[0].price.toFixed(2)})
              </div>
            )}
            <div style={actionItemStyle}>
              System learning from {learningMetrics?.pattern_learning?.total_patterns_tracked || 0} historical patterns
            </div>
            {performanceMetrics?.recovery?.recovery_status === 'BEHIND_SCHEDULE' && (
              <div style={{...actionItemStyle, color: '#f59e0b'}}>
                Focus: Accelerate discovery to match June-July performance
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

const pageStyle: React.CSSProperties = {
  padding: "16px",
  maxWidth: "1200px",
  margin: "0 auto",
  fontFamily: "ui-sans-serif, system-ui",
  color: "#e7e7e7",
  background: "#000",
  minHeight: "100vh"
};

// Mobile responsive breakpoints
const isMobile = window.innerWidth < 768;

const headerStyle: React.CSSProperties = {
  marginBottom: "30px",
  textAlign: "center"
};

const titleStyle: React.CSSProperties = {
  fontSize: isMobile ? "22px" : "28px",
  fontWeight: 800,
  margin: "0 0 8px 0",
  color: "#fff"
};

const subtitleStyle: React.CSSProperties = {
  fontSize: isMobile ? "14px" : "16px",
  color: "#999",
  lineHeight: "1.4"
};

const currentUpdateStyle: React.CSSProperties = {
  background: "linear-gradient(135deg, #1a1a1a 0%, #111 100%)",
  border: "2px solid #22c55e",
  borderRadius: "16px",
  padding: "24px",
  marginBottom: "40px",
  boxShadow: "0 0 20px rgba(34, 197, 94, 0.1)"
};

const currentHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  marginBottom: "16px"
};

const currentTitleStyle: React.CSSProperties = {
  fontSize: "20px",
  fontWeight: 700,
  color: "#22c55e",
  margin: "0 0 4px 0"
};

const currentTimeStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#22c55e",
  opacity: 0.8
};

const currentSummaryStyle: React.CSSProperties = {
  fontSize: "16px",
  color: "#fff",
  marginBottom: "16px",
  lineHeight: "1.4"
};

const smsButtonStyle: React.CSSProperties = {
  background: "#22c55e",
  border: "none",
  borderRadius: "8px",
  padding: "12px 16px",
  color: "#000",
  fontSize: "14px",
  fontWeight: 700,
  cursor: "pointer",
  whiteSpace: "nowrap"
};

const smsPreviewStyle: React.CSSProperties = {
  background: "#0a0a0a",
  border: "1px solid #333",
  borderRadius: "8px",
  padding: "12px",
  marginBottom: "12px"
};

const smsLabelStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#22c55e",
  marginBottom: "4px"
};

const smsTextStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#ccc",
  fontStyle: "italic"
};

const smsStatusStyle: React.CSSProperties = {
  fontSize: "14px",
  padding: "8px",
  borderRadius: "4px",
  background: "#0a0a0a"
};

const timelineStyle: React.CSSProperties = {
  marginBottom: "40px"
};

const timelineHeaderStyle: React.CSSProperties = {
  fontSize: "20px",
  fontWeight: 700,
  color: "#fff",
  marginBottom: "20px"
};

const timelineGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: isMobile ? "1fr" : "repeat(auto-fit, minmax(280px, 1fr))",
  gap: "12px"
};

const updateCardStyle: React.CSSProperties = {
  background: "#111",
  border: "1px solid #333",
  borderRadius: "12px",
  padding: "16px",
  transition: "all 0.2s ease"
};

const activeCardStyle: React.CSSProperties = {
  borderColor: "#22c55e",
  boxShadow: "0 0 16px rgba(34, 197, 94, 0.1)"
};

const cardHeaderStyle: React.CSSProperties = {
  marginBottom: "8px"
};

const cardTitleStyle: React.CSSProperties = {
  fontSize: "16px",
  fontWeight: 600,
  color: "#fff",
  marginBottom: "2px"
};

const cardTimeStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#999"
};

const cardSummaryStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#ccc",
  marginBottom: "12px",
  lineHeight: "1.3"
};

const detailsStyle: React.CSSProperties = {
  marginBottom: "12px"
};

const detailItemStyle: React.CSSProperties = {
  fontSize: "12px",
  marginBottom: "2px",
  display: "flex",
  gap: "8px"
};

const detailKeyStyle: React.CSSProperties = {
  color: "#999",
  minWidth: "80px"
};

const detailValueStyle: React.CSSProperties = {
  color: "#ccc"
};

const actionItemsStyle: React.CSSProperties = {
  marginBottom: "12px"
};

const actionItemStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#999",
  marginBottom: "2px"
};

const cardSmsButtonStyle: React.CSSProperties = {
  background: "transparent",
  border: "1px solid #333",
  borderRadius: "6px",
  padding: "8px 12px",
  color: "#ccc",
  fontSize: "12px",
  fontWeight: 600,
  cursor: "pointer",
  width: "100%"
};

const learningInfoStyle: React.CSSProperties = {
  background: "#0a0a0a",
  border: "1px solid #333",
  borderRadius: "12px",
  padding: "20px"
};

const learningTitleStyle: React.CSSProperties = {
  fontSize: "18px",
  fontWeight: 700,
  color: "#22c55e",
  marginBottom: "12px"
};

const learningDescStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#ccc",
  lineHeight: "1.4",
  marginBottom: "12px"
};

const learningStatsStyle: React.CSSProperties = {
  fontSize: "13px",
  color: "#999",
  lineHeight: "1.4"
};

const loadingStyle: React.CSSProperties = {
  textAlign: "center",
  padding: "40px",
  color: "#999",
  fontSize: "16px"
};

// Learning Dashboard Styles
const learningDashboardStyle: React.CSSProperties = {
  background: "linear-gradient(135deg, #1a1a1a 0%, #0a0a0a 100%)",
  border: "1px solid #333",
  borderRadius: "12px",
  padding: isMobile ? "16px" : "24px",
  marginBottom: "24px"
};

const dashboardHeaderStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: isMobile ? "column" : "row",
  justifyContent: "space-between",
  alignItems: isMobile ? "flex-start" : "center",
  gap: isMobile ? "12px" : "0",
  marginBottom: "20px"
};

const dashboardTitleStyle: React.CSSProperties = {
  fontSize: "20px",
  fontWeight: 700,
  color: "#fff",
  margin: 0
};

const healthScoreStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "8px"
};

const healthLabelStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#999"
};

const healthValueStyle: React.CSSProperties = {
  fontSize: "24px",
  fontWeight: 800
};

const metricsGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: isMobile ? "1fr" : "repeat(auto-fit, minmax(200px, 1fr))",
  gap: "12px"
};

const metricCardStyle: React.CSSProperties = {
  background: "#111",
  border: "1px solid #333",
  borderRadius: "12px",
  padding: "16px",
  textAlign: "center"
};

const metricLabelStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#999",
  marginBottom: "8px"
};

const metricValueStyle: React.CSSProperties = {
  fontSize: "24px",
  fontWeight: 800,
  color: "#22c55e",
  marginBottom: "4px"
};

const metricSubtextStyle: React.CSSProperties = {
  fontSize: "11px",
  color: "#666",
  lineHeight: "1.3"
};

// Opportunities Styles
const opportunitiesStyle: React.CSSProperties = {
  marginBottom: "32px"
};

const opportunitiesTitleStyle: React.CSSProperties = {
  fontSize: "20px",
  fontWeight: 700,
  color: "#fff",
  marginBottom: "16px",
  display: "flex",
  alignItems: "center",
  gap: "8px"
};

const opportunitiesGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: isMobile ? "1fr" : "repeat(auto-fit, minmax(300px, 1fr))",
  gap: "12px"
};

const opportunityCardStyle: React.CSSProperties = {
  background: "#111",
  border: "1px solid #333",
  borderRadius: "8px",
  padding: isMobile ? "12px" : "16px",
  transition: "all 0.2s ease"
};

const viglClassStyle: React.CSSProperties = {
  borderColor: "#f59e0b",
  boxShadow: "0 0 16px rgba(245, 158, 11, 0.1)"
};

const opportunityHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "8px"
};

const symbolStyle: React.CSSProperties = {
  fontSize: "18px",
  fontWeight: 700,
  color: "#fff"
};

const priceStyle: React.CSSProperties = {
  fontSize: "16px",
  color: "#22c55e",
  fontWeight: 600
};

const scoreStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#f59e0b",
  fontWeight: 600,
  marginBottom: "4px"
};

const potentialStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#999",
  marginBottom: "8px",
  display: "flex",
  alignItems: "center",
  gap: "8px"
};

const viglBadgeStyle: React.CSSProperties = {
  background: "#f59e0b",
  color: "#000",
  padding: "2px 6px",
  borderRadius: "4px",
  fontSize: "10px",
  fontWeight: 700
};

const thesisStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#ccc",
  lineHeight: "1.4"
};

// Recovery Tracking Styles
const recoveryTrackingStyle: React.CSSProperties = {
  marginBottom: "32px"
};

const recoveryTitleStyle: React.CSSProperties = {
  fontSize: "20px",
  fontWeight: 700,
  color: "#fff",
  marginBottom: "16px"
};

const recoveryGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: isMobile ? "1fr" : "repeat(auto-fit, minmax(250px, 1fr))",
  gap: "12px",
  marginBottom: "16px"
};

const recoveryCardStyle: React.CSSProperties = {
  background: "#111",
  border: "1px solid #333",
  borderRadius: "12px",
  padding: "16px"
};

const recoveryLabelStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#999",
  marginBottom: "8px"
};

const recoveryStatusStyle: React.CSSProperties = {
  fontSize: "16px",
  fontWeight: 700,
  marginBottom: "8px"
};

const recoveryProgressStyle: React.CSSProperties = {
  width: "100%",
  height: "6px",
  background: "#333",
  borderRadius: "3px",
  marginBottom: "8px",
  overflow: "hidden"
};

const progressBarStyle: React.CSSProperties = {
  height: "100%",
  background: "linear-gradient(90deg, #22c55e, #16a34a)",
  borderRadius: "3px",
  transition: "width 0.5s ease"
};

const recoveryPercentStyle: React.CSSProperties = {
  fontSize: "11px",
  color: "#666"
};

const recoveryValueStyle: React.CSSProperties = {
  fontSize: "20px",
  fontWeight: 800,
  color: "#22c55e",
  marginBottom: "4px"
};

const recoverySubtextStyle: React.CSSProperties = {
  fontSize: "11px",
  color: "#666"
};

const viglDetectedStyle: React.CSSProperties = {
  color: "#f59e0b",
  fontWeight: 600
};

const projectionStyle: React.CSSProperties = {
  background: "#0a0a0a",
  border: "1px solid #333",
  borderRadius: "8px",
  padding: "12px",
  fontSize: "14px",
  color: "#22c55e",
  textAlign: "center"
};

// Intelligence Summary Styles
const intelligenceSummaryStyle: React.CSSProperties = {
  background: "#0a0a0a",
  border: "1px solid #333",
  borderRadius: "12px",
  padding: "20px"
};

const intelligenceTitleStyle: React.CSSProperties = {
  fontSize: "18px",
  fontWeight: 700,
  color: "#22c55e",
  marginBottom: "16px"
};

const intelligenceContentStyle: React.CSSProperties = {
  marginBottom: "20px"
};

const intelligenceItemStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#ccc",
  marginBottom: "8px",
  display: "flex",
  alignItems: "flex-start",
  gap: "8px",
  lineHeight: "1.4"
};

const intelligenceBulletStyle: React.CSSProperties = {
  color: "#22c55e",
  fontWeight: 700,
  flexShrink: 0
};

const nextStepsStyle: React.CSSProperties = {
  borderTop: "1px solid #333",
  paddingTop: "16px"
};

const nextStepsHeaderStyle: React.CSSProperties = {
  fontSize: "16px",
  fontWeight: 700,
  color: "#f59e0b",
  marginBottom: "12px"
};

const actionGridStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "8px"
};