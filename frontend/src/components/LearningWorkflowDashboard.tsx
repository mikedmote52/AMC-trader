import React, { useEffect, useState } from "react";
import { API_BASE } from "../config";
import { getJSON } from "../lib/api";

type WorkflowStep = {
  step: string;
  status: "completed" | "active" | "pending";
  description: string;
  data?: any;
  timestamp?: string;
};

type TrackedPosition = {
  symbol: string;
  entry_price: number;
  quantity: number;
  entry_time: string;
  current_return_pct?: number;
  days_held: number;
  discovery_source: boolean;
};

type LearningWorkflow = {
  discovery_to_trade: {
    recent_discoveries: number;
    trades_executed: number;
    success_rate: number;
  };
  position_tracking: {
    active_positions: TrackedPosition[];
    closed_positions_today: number;
    learning_data_collected: number;
  };
  pattern_learning: {
    patterns_analyzed: number;
    winning_patterns_identified: number;
    algorithm_improvements: number;
  };
  user_experience: {
    manual_entries_needed: number;
    automatic_data_collected: number;
    learning_accuracy: number;
  };
};

const isMobile = window.innerWidth < 768;

export default function LearningWorkflowDashboard() {
  const [workflow, setWorkflow] = useState<LearningWorkflow | null>(null);
  const [workflowSteps, setWorkflowSteps] = useState<WorkflowStep[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Get learning workflow data
      const [workflowResponse, stepsResponse] = await Promise.all([
        getJSON(`${API_BASE}/learning-analytics/workflow/overview`).catch((error) => {
          console.error("Failed to load workflow overview:", error);
          return null;
        }),
        getJSON(`${API_BASE}/learning-analytics/workflow/steps`).catch((error) => {
          console.error("Failed to load workflow steps:", error);
          return null;
        })
      ]);

      if (workflowResponse?.success) {
        setWorkflow(workflowResponse.data);
      } else {
        setWorkflow(null);
      }

      if (stepsResponse?.success) {
        setWorkflowSteps(stepsResponse.data);
      } else {
        setWorkflowSteps([]);
      }

    } catch (err) {
      setError("Failed to load learning workflow data");
      console.error("Learning workflow error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshData();
    const interval = setInterval(refreshData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div style={containerStyle}>
        <div style={headerStyle}>
          <h3 style={titleStyle}>🧠 Learning Workflow Dashboard</h3>
          <div style={subtitleStyle}>Loading learning system status...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={containerStyle}>
        <div style={headerStyle}>
          <h3 style={titleStyle}>🧠 Learning Workflow Dashboard</h3>
          <div style={{...subtitleStyle, color: '#ef4444'}}>{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h3 style={titleStyle}>🧠 Learning Workflow Dashboard</h3>
        <div style={subtitleStyle}>
          Complete learning cycle from discovery → trades → outcomes → improvements
        </div>
      </div>

      {/* Workflow Steps */}
      <div style={workflowSectionStyle}>
        <h4 style={sectionTitleStyle}>🔄 Current Workflow Status</h4>
        {workflowSteps.length > 0 ? (
          <div style={stepsContainerStyle}>
            {workflowSteps.map((step, index) => (
              <div key={index} style={{
                ...stepItemStyle,
                ...(step.status === 'active' && activeStepStyle),
                ...(step.status === 'completed' && completedStepStyle),
                ...(step.status === 'pending' && pendingStepStyle)
              }}>
                <div style={stepHeaderStyle}>
                  <span style={stepIndicatorStyle}>
                    {step.status === 'completed' ? '✅' :
                     step.status === 'active' ? '🔄' : '⏳'}
                  </span>
                  <span style={stepNameStyle}>{step.step}</span>
                </div>
                <div style={stepDescriptionStyle}>{step.description}</div>
                {step.timestamp && (
                  <div style={stepTimestampStyle}>
                    {new Date(step.timestamp).toLocaleTimeString()}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div style={emptyStateStyle}>
            No workflow data available yet. Learning system is initializing.
          </div>
        )}
      </div>

      {/* Live Data Overview */}
      {workflow ? (
        <div style={contentGridStyle}>
          {/* Discovery to Trade */}
          <div style={metricCardStyle}>
            <h4 style={cardTitleStyle}>🎯 Discovery → Trades</h4>
            <div style={metricRowStyle}>
              <span style={metricLabelStyle}>Discoveries:</span>
              <span style={metricValueStyle}>{workflow.discovery_to_trade.recent_discoveries}</span>
            </div>
            <div style={metricRowStyle}>
              <span style={metricLabelStyle}>Executed:</span>
              <span style={metricValueStyle}>{workflow.discovery_to_trade.trades_executed}</span>
            </div>
            <div style={metricRowStyle}>
              <span style={metricLabelStyle}>Success Rate:</span>
              <span style={{
                ...metricValueStyle,
                color: workflow.discovery_to_trade.success_rate > 60 ? '#22c55e' : '#ef4444'
              }}>
                {workflow.discovery_to_trade.success_rate}%
              </span>
            </div>
          </div>

          {/* Position Tracking */}
          <div style={metricCardStyle}>
            <h4 style={cardTitleStyle}>📊 Position Tracking</h4>
            <div style={metricRowStyle}>
              <span style={metricLabelStyle}>Active Positions:</span>
              <span style={metricValueStyle}>{workflow.position_tracking.active_positions.length}</span>
            </div>
            <div style={metricRowStyle}>
              <span style={metricLabelStyle}>Closed Today:</span>
              <span style={metricValueStyle}>{workflow.position_tracking.closed_positions_today}</span>
            </div>
            <div style={metricRowStyle}>
              <span style={metricLabelStyle}>Data Collected:</span>
              <span style={metricValueStyle}>{workflow.position_tracking.learning_data_collected}</span>
            </div>
          </div>

          {/* Pattern Learning */}
          <div style={metricCardStyle}>
            <h4 style={cardTitleStyle}>🔍 Pattern Learning</h4>
            <div style={metricRowStyle}>
              <span style={metricLabelStyle}>Patterns Analyzed:</span>
              <span style={metricValueStyle}>{workflow.pattern_learning.patterns_analyzed}</span>
            </div>
            <div style={metricRowStyle}>
              <span style={metricLabelStyle}>Winners Identified:</span>
              <span style={metricValueStyle}>{workflow.pattern_learning.winning_patterns_identified}</span>
            </div>
            <div style={metricRowStyle}>
              <span style={metricLabelStyle}>Improvements:</span>
              <span style={metricValueStyle}>{workflow.pattern_learning.algorithm_improvements}</span>
            </div>
          </div>

          {/* User Experience */}
          <div style={metricCardStyle}>
            <h4 style={cardTitleStyle}>👤 User Experience</h4>
            <div style={metricRowStyle}>
              <span style={metricLabelStyle}>Manual Entries:</span>
              <span style={metricValueStyle}>{workflow.user_experience.manual_entries_needed}</span>
            </div>
            <div style={metricRowStyle}>
              <span style={metricLabelStyle}>Auto Collected:</span>
              <span style={metricValueStyle}>{workflow.user_experience.automatic_data_collected}</span>
            </div>
            <div style={metricRowStyle}>
              <span style={metricLabelStyle}>Accuracy:</span>
              <span style={{
                ...metricValueStyle,
                color: workflow.user_experience.learning_accuracy > 80 ? '#22c55e' : '#f59e0b'
              }}>
                {workflow.user_experience.learning_accuracy}%
              </span>
            </div>
          </div>
        </div>
      ) : (
        <div style={emptyStateStyle}>
          No workflow metrics available. Learning system may not be deployed or is still collecting data.
        </div>
      )}

      {/* Active Positions */}
      {workflow && workflow.position_tracking.active_positions.length > 0 && (
        <div style={positionsTableStyle}>
          <h4 style={sectionTitleStyle}>📈 Active Learning Positions</h4>
          <div style={tableHeaderStyle}>
            <span style={tableHeaderCellStyle}>Symbol</span>
            <span style={tableHeaderCellStyle}>Entry Price</span>
            <span style={tableHeaderCellStyle}>Return</span>
            <span style={tableHeaderCellStyle}>Days</span>
            <span style={tableHeaderCellStyle}>Discovery</span>
          </div>
          {workflow.position_tracking.active_positions.map((position, index) => (
            <div key={index} style={tableRowStyle}>
              <span style={tableCellStyle}>{position.symbol}</span>
              <span style={tableCellStyle}>${position.entry_price.toFixed(2)}</span>
              <span style={{
                ...tableCellStyle,
                color: (position.current_return_pct || 0) > 0 ? '#22c55e' : '#ef4444'
              }}>
                {position.current_return_pct ? `${position.current_return_pct > 0 ? '+' : ''}${position.current_return_pct.toFixed(1)}%` : 'N/A'}
              </span>
              <span style={tableCellStyle}>{position.days_held}</span>
              <span style={tableCellStyle}>{position.discovery_source ? '✅' : '❌'}</span>
            </div>
          ))}
        </div>
      )}

      {/* Learning Impact */}
      <div style={impactSectionStyle}>
        <h4 style={sectionTitleStyle}>🎯 Learning Impact</h4>
        <div style={impactContentStyle}>
          <div style={impactItemStyle}>
            <span style={impactIconStyle}>🤖</span>
            <div>
              <div style={impactTitleStyle}>Automatic Data Collection</div>
              <div style={impactDescStyle}>
                System automatically tracks all discovery → trade → outcome cycles without manual input
              </div>
            </div>
          </div>
          <div style={impactItemStyle}>
            <span style={impactIconStyle}>📊</span>
            <div>
              <div style={impactTitleStyle}>Real-time Learning</div>
              <div style={impactDescStyle}>
                Algorithm improves discovery quality based on actual trading results
              </div>
            </div>
          </div>
          <div style={impactItemStyle}>
            <span style={impactIconStyle}>🎯</span>
            <div>
              <div style={impactTitleStyle}>Pattern Recognition</div>
              <div style={impactDescStyle}>
                Identifies winning patterns and adjusts scoring weights for better recommendations
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Styles
const containerStyle: React.CSSProperties = {
  background: '#111',
  border: '1px solid #333',
  borderRadius: '12px',
  padding: isMobile ? '16px' : '24px',
  marginBottom: '24px'
};

const headerStyle: React.CSSProperties = {
  marginBottom: '24px',
  textAlign: 'center'
};

const titleStyle: React.CSSProperties = {
  fontSize: '20px',
  fontWeight: 700,
  color: '#fff',
  marginBottom: '8px'
};

const subtitleStyle: React.CSSProperties = {
  fontSize: '14px',
  color: '#999',
  lineHeight: '1.4'
};

const workflowSectionStyle: React.CSSProperties = {
  marginBottom: '24px'
};

const sectionTitleStyle: React.CSSProperties = {
  fontSize: '16px',
  fontWeight: 600,
  color: '#22c55e',
  marginBottom: '16px'
};

const stepsContainerStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: isMobile ? 'column' : 'row',
  gap: '12px',
  overflowX: isMobile ? 'visible' : 'auto'
};

const stepItemStyle: React.CSSProperties = {
  background: '#0a0a0a',
  border: '1px solid #333',
  borderRadius: '8px',
  padding: '16px',
  minWidth: isMobile ? 'auto' : '200px',
  flexShrink: 0
};

const activeStepStyle: React.CSSProperties = {
  borderColor: '#3b82f6',
  background: 'rgba(59, 130, 246, 0.1)'
};

const completedStepStyle: React.CSSProperties = {
  borderColor: '#22c55e',
  background: 'rgba(34, 197, 94, 0.1)'
};

const pendingStepStyle: React.CSSProperties = {
  borderColor: '#6b7280',
  background: 'rgba(107, 114, 128, 0.1)'
};

const stepHeaderStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  marginBottom: '8px'
};

const stepIndicatorStyle: React.CSSProperties = {
  fontSize: '16px'
};

const stepNameStyle: React.CSSProperties = {
  fontSize: '14px',
  fontWeight: 600,
  color: '#fff'
};

const stepDescriptionStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#ccc',
  lineHeight: '1.4',
  marginBottom: '8px'
};

const stepTimestampStyle: React.CSSProperties = {
  fontSize: '11px',
  color: '#666'
};

const contentGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(250px, 1fr))',
  gap: '16px',
  marginBottom: '24px'
};

const metricCardStyle: React.CSSProperties = {
  background: '#0a0a0a',
  border: '1px solid #333',
  borderRadius: '8px',
  padding: '16px'
};

const cardTitleStyle: React.CSSProperties = {
  fontSize: '14px',
  fontWeight: 600,
  color: '#fff',
  marginBottom: '12px'
};

const metricRowStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '8px'
};

const metricLabelStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#999'
};

const metricValueStyle: React.CSSProperties = {
  fontSize: '14px',
  fontWeight: 600,
  color: '#fff'
};

const positionsTableStyle: React.CSSProperties = {
  marginBottom: '24px'
};

const tableHeaderStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr',
  gap: '8px',
  padding: '12px',
  background: '#0a0a0a',
  border: '1px solid #333',
  borderRadius: '6px 6px 0 0',
  borderBottom: 'none'
};

const tableHeaderCellStyle: React.CSSProperties = {
  fontSize: '12px',
  fontWeight: 600,
  color: '#999',
  textAlign: 'center'
};

const tableRowStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr',
  gap: '8px',
  padding: '12px',
  background: '#111',
  border: '1px solid #333',
  borderTop: 'none'
};

const tableCellStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#ccc',
  textAlign: 'center'
};

const impactSectionStyle: React.CSSProperties = {
  background: '#0a0a0a',
  border: '1px solid #333',
  borderRadius: '8px',
  padding: '20px'
};

const impactContentStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '16px'
};

const impactItemStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  gap: '12px'
};

const impactIconStyle: React.CSSProperties = {
  fontSize: '20px',
  flexShrink: 0,
  marginTop: '2px'
};

const impactTitleStyle: React.CSSProperties = {
  fontSize: '14px',
  fontWeight: 600,
  color: '#22c55e',
  marginBottom: '4px'
};

const impactDescStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#ccc',
  lineHeight: '1.4'
};

const emptyStateStyle: React.CSSProperties = {
  padding: '24px',
  textAlign: 'center',
  color: '#666',
  fontSize: '14px',
  background: '#0a0a0a',
  border: '1px solid #333',
  borderRadius: '8px'
};