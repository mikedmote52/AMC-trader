import React, { useEffect, useState } from "react";
import { API_BASE } from "../config";
import { getJSON } from "../lib/api";

type MarketRegime = {
  current_regime: string;
  regime_changed: boolean;
  previous_regime?: string;
  change_date: string;
};

type PatternAnalysis = {
  pattern_count: {
    winners: number;
    losers: number;
  };
  feature_effectiveness: Record<string, {
    winner_avg: number;
    loser_avg: number;
    effectiveness_score: number;
    predictive_power: string;
  }>;
  optimal_ranges: Record<string, {
    optimal_min: number;
    optimal_target: number;
    exceptional: number;
    median: number;
  }>;
  weight_recommendations: {
    current_weights: Record<string, number>;
    recommended_weights: Record<string, number>;
    weight_changes: Record<string, number>;
    rationale: string;
  };
  top_performing_patterns: Array<{
    symbol: string;
    return_7d: number;
    score: number;
    regime: string;
    key_features: Record<string, string>;
  }>;
};

type ConfidenceCalibration = {
  calibration_table: Array<{
    confidence_range: string;
    avg_return_7d: number;
    success_rate: number;
    sample_size: number;
  }>;
  calibration_quality: string;
};

type LearningSystemSummary = {
  system_stats: {
    discovery_events_tracked: number;
    candidates_analyzed: number;
    trade_outcomes_recorded: number;
    avg_7d_return: number;
    last_discovery: string | null;
  };
  recent_activity: Array<{
    date: string;
    discoveries: number;
    avg_candidates: number;
  }>;
  learning_status: string;
};

type DiscoveryParameters = {
  current_regime: string;
  regime_changed: boolean;
  optimized_parameters: Record<string, number>;
  last_updated: string;
  confidence: number;
};

const isMobile = window.innerWidth < 768;

export default function EnhancedLearningDashboard() {
  const [marketRegime, setMarketRegime] = useState<MarketRegime | null>(null);
  const [patternAnalysis, setPatternAnalysis] = useState<PatternAnalysis | null>(null);
  const [confidenceCalibration, setConfidenceCalibration] = useState<ConfidenceCalibration | null>(null);
  const [learningSystemSummary, setLearningSystemSummary] = useState<LearningSystemSummary | null>(null);
  const [discoveryParameters, setDiscoveryParameters] = useState<DiscoveryParameters | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadEnhancedLearningData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Load all enhanced learning data in parallel
        const [
          regimeResponse,
          patternResponse,
          calibrationResponse,
          summaryResponse,
          parametersResponse
        ] = await Promise.all([
          getJSON(`${API_BASE}/learning/intelligence/market-regime`).catch(() => null),
          getJSON(`${API_BASE}/learning/intelligence/pattern-analysis`).catch(() => null),
          getJSON(`${API_BASE}/learning/intelligence/confidence-calibration`).catch(() => null),
          getJSON(`${API_BASE}/learning/intelligence/learning-summary`).catch(() => null),
          getJSON(`${API_BASE}/learning/intelligence/discovery-parameters`).catch(() => null)
        ]);

        if (regimeResponse?.success) {
          setMarketRegime(regimeResponse.data.regime_info);
        }

        if (patternResponse?.success) {
          setPatternAnalysis(patternResponse.data);
        }

        if (calibrationResponse?.success) {
          setConfidenceCalibration(calibrationResponse.data);
        }

        if (summaryResponse?.success) {
          setLearningSystemSummary(summaryResponse.data);
        }

        if (parametersResponse?.success) {
          setDiscoveryParameters(parametersResponse.data);
        }

      } catch (err) {
        console.error("Failed to load enhanced learning data:", err);
        setError("Failed to load enhanced learning data");
      } finally {
        setLoading(false);
      }
    };

    loadEnhancedLearningData();

    // Refresh every 60 seconds
    const interval = setInterval(loadEnhancedLearningData, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div style={loadingContainerStyle}>
        <div style={loadingTextStyle}>🧠 Loading Enhanced Learning Intelligence...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={errorContainerStyle}>
        <div style={errorTextStyle}>⚠️ {error}</div>
        <div style={errorSubtextStyle}>Enhanced learning features may not be deployed yet</div>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      {/* Enhanced Learning System Header */}
      <div style={headerStyle}>
        <h2 style={titleStyle}>🤖 Enhanced Learning Intelligence System</h2>
        <div style={subtitleStyle}>
          Self-improving pattern recognition • Advanced market adaptation • Real-time optimization
        </div>
      </div>

      {/* Market Regime Detection */}
      {marketRegime && (
        <div style={sectionStyle}>
          <h3 style={sectionTitleStyle}>🌊 Market Regime Detection</h3>
          <div style={regimeCardStyle}>
            <div style={regimeHeaderStyle}>
              <div style={regimeCurrentStyle}>
                Current Regime: <span style={regimeValueStyle}>{formatRegimeName(marketRegime.current_regime)}</span>
              </div>
              {marketRegime.regime_changed && (
                <div style={regimeChangeStyle}>
                  🔄 Recently changed from {formatRegimeName(marketRegime.previous_regime || "unknown")}
                </div>
              )}
            </div>
            <div style={regimeRecommendationStyle}>
              {getRegimeRecommendation(marketRegime.current_regime)}
            </div>
          </div>
        </div>
      )}

      {/* Discovery Parameter Optimization */}
      {discoveryParameters && (
        <div style={sectionStyle}>
          <h3 style={sectionTitleStyle}>⚙️ Adaptive Discovery Parameters</h3>
          <div style={parametersCardStyle}>
            <div style={parametersHeaderStyle}>
              <span>Optimized for: {formatRegimeName(discoveryParameters.current_regime)}</span>
              <span style={confidenceStyle}>Confidence: {(discoveryParameters.confidence * 100).toFixed(0)}%</span>
            </div>
            <div style={parametersGridStyle}>
              {Object.entries(discoveryParameters.optimized_parameters).slice(0, 6).map(([param, value]) => (
                <div key={param} style={parameterItemStyle}>
                  <div style={parameterNameStyle}>{formatParameterName(param)}</div>
                  <div style={parameterValueStyle}>{formatParameterValue(param, value)}</div>
                </div>
              ))}
            </div>
            <div style={parameterUpdateStyle}>
              Last updated: {new Date(discoveryParameters.last_updated).toLocaleTimeString()}
            </div>
          </div>
        </div>
      )}

      {/* Pattern Analysis */}
      {patternAnalysis && (
        <div style={sectionStyle}>
          <h3 style={sectionTitleStyle}>📊 Pattern Analysis Intelligence</h3>

          {/* Learning Statistics */}
          <div style={patternStatsStyle}>
            <div style={statCardStyle}>
              <div style={statLabelStyle}>Winning Patterns</div>
              <div style={statValueStyle}>{patternAnalysis.pattern_count.winners}</div>
              <div style={statSubtextStyle}>Analyzed for success factors</div>
            </div>
            <div style={statCardStyle}>
              <div style={statLabelStyle}>Losing Patterns</div>
              <div style={statValueStyle}>{patternAnalysis.pattern_count.losers}</div>
              <div style={statSubtextStyle}>Identified failure modes</div>
            </div>
            <div style={statCardStyle}>
              <div style={statLabelStyle}>Top Features</div>
              <div style={statValueStyle}>
                {Object.values(patternAnalysis.feature_effectiveness).filter(f => f.predictive_power === 'high').length}
              </div>
              <div style={statSubtextStyle}>High predictive power</div>
            </div>
          </div>

          {/* Feature Effectiveness */}
          <div style={featureEffectivenessStyle}>
            <h4 style={subsectionTitleStyle}>🎯 Feature Effectiveness Analysis</h4>
            <div style={featuresGridStyle}>
              {Object.entries(patternAnalysis.feature_effectiveness).map(([feature, data]) => (
                <div key={feature} style={featureCardStyle}>
                  <div style={featureNameStyle}>{formatFeatureName(feature)}</div>
                  <div style={featureScoreStyle}>
                    <span style={effectivenessScoreStyle(data.effectiveness_score)}>
                      {data.effectiveness_score > 0 ? '+' : ''}{data.effectiveness_score.toFixed(3)}
                    </span>
                    <span style={powerLabelStyle}>{data.predictive_power.toUpperCase()}</span>
                  </div>
                  <div style={featureDetailsStyle}>
                    Winners: {data.winner_avg.toFixed(3)} • Losers: {data.loser_avg.toFixed(3)}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Weight Recommendations */}
          {patternAnalysis.weight_recommendations && (
            <div style={weightRecommendationsStyle}>
              <h4 style={subsectionTitleStyle}>⚖️ Scoring Weight Optimization</h4>
              <div style={weightsGridStyle}>
                {Object.entries(patternAnalysis.weight_recommendations.current_weights).map(([component, currentWeight]) => {
                  const recommendedWeight = patternAnalysis.weight_recommendations.recommended_weights[component];
                  const change = patternAnalysis.weight_recommendations.weight_changes[component];

                  return (
                    <div key={component} style={weightCardStyle}>
                      <div style={weightComponentStyle}>{formatComponentName(component)}</div>
                      <div style={weightValuesStyle}>
                        <span style={currentWeightStyle}>{(currentWeight * 100).toFixed(1)}%</span>
                        <span style={arrowStyle}>→</span>
                        <span style={recommendedWeightStyle}>{(recommendedWeight * 100).toFixed(1)}%</span>
                      </div>
                      <div style={weightChangeStyle(change)}>
                        {change > 0 ? '+' : ''}{(change * 100).toFixed(1)}%
                      </div>
                    </div>
                  );
                })}
              </div>
              <div style={rationaleStyle}>
                💡 {patternAnalysis.weight_recommendations.rationale}
              </div>
            </div>
          )}

          {/* Top Performing Patterns */}
          {patternAnalysis.top_performing_patterns && patternAnalysis.top_performing_patterns.length > 0 && (
            <div style={topPatternsStyle}>
              <h4 style={subsectionTitleStyle}>🏆 Top Performing Patterns</h4>
              <div style={topPatternsGridStyle}>
                {patternAnalysis.top_performing_patterns.slice(0, 3).map((pattern, index) => (
                  <div key={pattern.symbol} style={topPatternCardStyle}>
                    <div style={patternHeaderStyle}>
                      <span style={symbolStyle}>{pattern.symbol}</span>
                      <span style={returnStyle}>+{pattern.return_7d.toFixed(1)}%</span>
                    </div>
                    <div style={patternScoreStyle}>Score: {pattern.score.toFixed(3)}</div>
                    <div style={patternRegimeStyle}>Regime: {formatRegimeName(pattern.regime)}</div>
                    <div style={keyFeaturesStyle}>
                      {Object.entries(pattern.key_features).slice(0, 2).map(([feature, value]) => (
                        <div key={feature} style={keyFeatureStyle}>
                          <span style={featureKeyStyle}>{feature}:</span> {value}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Confidence Calibration */}
      {confidenceCalibration && (
        <div style={sectionStyle}>
          <h3 style={sectionTitleStyle}>🎯 Confidence Calibration Analysis</h3>
          <div style={calibrationCardStyle}>
            <div style={calibrationHeaderStyle}>
              Quality: <span style={calibrationQualityStyle}>{confidenceCalibration.calibration_quality.toUpperCase()}</span>
            </div>
            <div style={calibrationGridStyle}>
              {confidenceCalibration.calibration_table.map((bucket, index) => (
                <div key={bucket.confidence_range} style={calibrationBucketStyle}>
                  <div style={bucketRangeStyle}>{bucket.confidence_range}</div>
                  <div style={bucketMetricsStyle}>
                    <div style={bucketReturnStyle}>
                      {bucket.avg_return_7d > 0 ? '+' : ''}{bucket.avg_return_7d.toFixed(1)}% avg
                    </div>
                    <div style={bucketSuccessStyle}>{bucket.success_rate.toFixed(1)}% success</div>
                    <div style={bucketSampleStyle}>{bucket.sample_size} samples</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* System Summary */}
      {learningSystemSummary && (
        <div style={sectionStyle}>
          <h3 style={sectionTitleStyle}>📈 Learning System Activity</h3>
          <div style={summaryCardStyle}>
            <div style={summaryStatsStyle}>
              <div style={summaryStatStyle}>
                <div style={summaryStatLabelStyle}>Discovery Events</div>
                <div style={summaryStatValueStyle}>{learningSystemSummary.system_stats.discovery_events_tracked}</div>
              </div>
              <div style={summaryStatStyle}>
                <div style={summaryStatLabelStyle}>Candidates Analyzed</div>
                <div style={summaryStatValueStyle}>{learningSystemSummary.system_stats.candidates_analyzed}</div>
              </div>
              <div style={summaryStatStyle}>
                <div style={summaryStatLabelStyle}>Trade Outcomes</div>
                <div style={summaryStatValueStyle}>{learningSystemSummary.system_stats.trade_outcomes_recorded}</div>
              </div>
              <div style={summaryStatStyle}>
                <div style={summaryStatLabelStyle}>Avg 7D Return</div>
                <div style={summaryStatValueStyle}>
                  {learningSystemSummary.system_stats.avg_7d_return > 0 ? '+' : ''}
                  {learningSystemSummary.system_stats.avg_7d_return.toFixed(1)}%
                </div>
              </div>
            </div>

            <div style={learningStatusStyle}>
              Status: <span style={statusValueStyle(learningSystemSummary.learning_status)}>
                {learningSystemSummary.learning_status.toUpperCase()}
              </span>
            </div>

            {learningSystemSummary.recent_activity.length > 0 && (
              <div style={recentActivityStyle}>
                <h4 style={activityTitleStyle}>Recent Activity (7 days)</h4>
                <div style={activityGridStyle}>
                  {learningSystemSummary.recent_activity.slice(0, 7).map((activity, index) => (
                    <div key={activity.date} style={activityItemStyle}>
                      <div style={activityDateStyle}>{new Date(activity.date).toLocaleDateString()}</div>
                      <div style={activityMetricsStyle}>
                        {activity.discoveries} discoveries • {activity.avg_candidates.toFixed(1)} avg candidates
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Helper functions
function formatRegimeName(regime: string): string {
  return regime.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function formatParameterName(param: string): string {
  return param.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function formatParameterValue(param: string, value: number): string {
  if (param.includes('threshold') || param.includes('min') || param.includes('max')) {
    return value.toFixed(3);
  }
  if (param.includes('pct') || param.includes('percent')) {
    return `${(value * 100).toFixed(1)}%`;
  }
  return value.toFixed(2);
}

function formatFeatureName(feature: string): string {
  return feature.replace(/_score|_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function formatComponentName(component: string): string {
  return component.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function getRegimeRecommendation(regime: string): string {
  const recommendations: Record<string, string> = {
    'explosive_bull': '🚀 Aggressive momentum plays - High scores + volume required',
    'squeeze_setup': '🎯 Focus on squeeze catalyst combinations - Verify authenticity',
    'low_opportunity': '🛡️ Defensive approach - High conviction only, reduce position sizes',
    'high_volatility': '⚡ Rapid trades - Quick entries/exits with tight stops',
    'normal_market': '📊 Balanced approach - Standard discovery parameters active',
    'insufficient_data': '📈 Building learning database - Standard parameters in use'
  };

  return recommendations[regime] || '📊 Standard discovery approach recommended';
}

// Styling functions
function effectivenessScoreStyle(score: number): React.CSSProperties {
  return {
    color: score > 0.2 ? '#22c55e' : score > 0.1 ? '#f59e0b' : '#ef4444',
    fontWeight: 700,
    fontSize: '16px'
  };
}

function weightChangeStyle(change: number): React.CSSProperties {
  return {
    color: change > 0 ? '#22c55e' : change < 0 ? '#ef4444' : '#999',
    fontSize: '12px',
    fontWeight: 600
  };
}

function statusValueStyle(status: string): React.CSSProperties {
  return {
    color: status === 'active' ? '#22c55e' : status === 'initializing' ? '#f59e0b' : '#999',
    fontWeight: 700
  };
}

// Styles
const containerStyle: React.CSSProperties = {
  padding: isMobile ? '12px' : '16px',
  maxWidth: '1400px',
  margin: '0 auto'
};

const loadingContainerStyle: React.CSSProperties = {
  padding: '40px',
  textAlign: 'center'
};

const loadingTextStyle: React.CSSProperties = {
  fontSize: '16px',
  color: '#999'
};

const errorContainerStyle: React.CSSProperties = {
  padding: '24px',
  background: '#1a1a1a',
  border: '1px solid #ef4444',
  borderRadius: '8px',
  textAlign: 'center'
};

const errorTextStyle: React.CSSProperties = {
  fontSize: '16px',
  color: '#ef4444',
  marginBottom: '8px'
};

const errorSubtextStyle: React.CSSProperties = {
  fontSize: '14px',
  color: '#999'
};

const headerStyle: React.CSSProperties = {
  marginBottom: '24px',
  textAlign: 'center'
};

const titleStyle: React.CSSProperties = {
  fontSize: isMobile ? '20px' : '24px',
  fontWeight: 800,
  color: '#fff',
  marginBottom: '8px'
};

const subtitleStyle: React.CSSProperties = {
  fontSize: isMobile ? '12px' : '14px',
  color: '#999',
  lineHeight: '1.4'
};

const sectionStyle: React.CSSProperties = {
  marginBottom: '32px'
};

const sectionTitleStyle: React.CSSProperties = {
  fontSize: '18px',
  fontWeight: 700,
  color: '#fff',
  marginBottom: '16px'
};

const regimeCardStyle: React.CSSProperties = {
  background: '#111',
  border: '1px solid #333',
  borderRadius: '12px',
  padding: '20px'
};

const regimeHeaderStyle: React.CSSProperties = {
  marginBottom: '12px'
};

const regimeCurrentStyle: React.CSSProperties = {
  fontSize: '16px',
  color: '#ccc',
  marginBottom: '8px'
};

const regimeValueStyle: React.CSSProperties = {
  color: '#22c55e',
  fontWeight: 700
};

const regimeChangeStyle: React.CSSProperties = {
  fontSize: '14px',
  color: '#f59e0b',
  fontWeight: 600
};

const regimeRecommendationStyle: React.CSSProperties = {
  fontSize: '14px',
  color: '#ccc',
  padding: '12px',
  background: '#0a0a0a',
  borderRadius: '8px',
  border: '1px solid #333'
};

const parametersCardStyle: React.CSSProperties = {
  background: '#111',
  border: '1px solid #333',
  borderRadius: '12px',
  padding: '20px'
};

const parametersHeaderStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '16px',
  fontSize: '14px',
  color: '#ccc'
};

const confidenceStyle: React.CSSProperties = {
  color: '#22c55e',
  fontWeight: 600
};

const parametersGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: isMobile ? '1fr 1fr' : 'repeat(auto-fit, minmax(200px, 1fr))',
  gap: '12px',
  marginBottom: '16px'
};

const parameterItemStyle: React.CSSProperties = {
  background: '#0a0a0a',
  border: '1px solid #333',
  borderRadius: '8px',
  padding: '12px',
  textAlign: 'center'
};

const parameterNameStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#999',
  marginBottom: '4px'
};

const parameterValueStyle: React.CSSProperties = {
  fontSize: '16px',
  color: '#22c55e',
  fontWeight: 700
};

const parameterUpdateStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#666',
  textAlign: 'center'
};

const patternStatsStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)',
  gap: '12px',
  marginBottom: '20px'
};

const statCardStyle: React.CSSProperties = {
  background: '#111',
  border: '1px solid #333',
  borderRadius: '8px',
  padding: '16px',
  textAlign: 'center'
};

const statLabelStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#999',
  marginBottom: '4px'
};

const statValueStyle: React.CSSProperties = {
  fontSize: '24px',
  color: '#22c55e',
  fontWeight: 800,
  marginBottom: '4px'
};

const statSubtextStyle: React.CSSProperties = {
  fontSize: '11px',
  color: '#666'
};

const featureEffectivenessStyle: React.CSSProperties = {
  marginBottom: '24px'
};

const subsectionTitleStyle: React.CSSProperties = {
  fontSize: '16px',
  fontWeight: 600,
  color: '#fff',
  marginBottom: '12px'
};

const featuresGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(250px, 1fr))',
  gap: '12px'
};

const featureCardStyle: React.CSSProperties = {
  background: '#111',
  border: '1px solid #333',
  borderRadius: '8px',
  padding: '16px'
};

const featureNameStyle: React.CSSProperties = {
  fontSize: '14px',
  color: '#fff',
  fontWeight: 600,
  marginBottom: '8px'
};

const featureScoreStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '8px'
};

const powerLabelStyle: React.CSSProperties = {
  fontSize: '10px',
  color: '#999',
  fontWeight: 600
};

const featureDetailsStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#666'
};

const weightRecommendationsStyle: React.CSSProperties = {
  marginBottom: '24px'
};

const weightsGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(200px, 1fr))',
  gap: '12px',
  marginBottom: '16px'
};

const weightCardStyle: React.CSSProperties = {
  background: '#111',
  border: '1px solid #333',
  borderRadius: '8px',
  padding: '16px',
  textAlign: 'center'
};

const weightComponentStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#999',
  marginBottom: '8px'
};

const weightValuesStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '8px',
  marginBottom: '4px'
};

const currentWeightStyle: React.CSSProperties = {
  fontSize: '14px',
  color: '#ccc'
};

const arrowStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#22c55e'
};

const recommendedWeightStyle: React.CSSProperties = {
  fontSize: '14px',
  color: '#22c55e',
  fontWeight: 700
};

const rationaleStyle: React.CSSProperties = {
  fontSize: '14px',
  color: '#999',
  fontStyle: 'italic',
  textAlign: 'center',
  padding: '12px',
  background: '#0a0a0a',
  borderRadius: '8px'
};

const topPatternsStyle: React.CSSProperties = {
  marginBottom: '24px'
};

const topPatternsGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(300px, 1fr))',
  gap: '12px'
};

const topPatternCardStyle: React.CSSProperties = {
  background: '#111',
  border: '1px solid #333',
  borderRadius: '8px',
  padding: '16px'
};

const patternHeaderStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '8px'
};

const symbolStyle: React.CSSProperties = {
  fontSize: '16px',
  color: '#fff',
  fontWeight: 700
};

const returnStyle: React.CSSProperties = {
  fontSize: '16px',
  color: '#22c55e',
  fontWeight: 700
};

const patternScoreStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#999',
  marginBottom: '4px'
};

const patternRegimeStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#f59e0b',
  marginBottom: '8px'
};

const keyFeaturesStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '2px'
};

const keyFeatureStyle: React.CSSProperties = {
  fontSize: '11px',
  color: '#666'
};

const featureKeyStyle: React.CSSProperties = {
  color: '#999'
};

const calibrationCardStyle: React.CSSProperties = {
  background: '#111',
  border: '1px solid #333',
  borderRadius: '12px',
  padding: '20px'
};

const calibrationHeaderStyle: React.CSSProperties = {
  fontSize: '14px',
  color: '#ccc',
  marginBottom: '16px'
};

const calibrationQualityStyle: React.CSSProperties = {
  color: '#22c55e',
  fontWeight: 700
};

const calibrationGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(150px, 1fr))',
  gap: '12px'
};

const calibrationBucketStyle: React.CSSProperties = {
  background: '#0a0a0a',
  border: '1px solid #333',
  borderRadius: '8px',
  padding: '12px',
  textAlign: 'center'
};

const bucketRangeStyle: React.CSSProperties = {
  fontSize: '14px',
  color: '#fff',
  fontWeight: 600,
  marginBottom: '8px'
};

const bucketMetricsStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '2px'
};

const bucketReturnStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#22c55e'
};

const bucketSuccessStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#f59e0b'
};

const bucketSampleStyle: React.CSSProperties = {
  fontSize: '11px',
  color: '#666'
};

const summaryCardStyle: React.CSSProperties = {
  background: '#111',
  border: '1px solid #333',
  borderRadius: '12px',
  padding: '20px'
};

const summaryStatsStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(4, 1fr)',
  gap: '16px',
  marginBottom: '20px'
};

const summaryStatStyle: React.CSSProperties = {
  textAlign: 'center'
};

const summaryStatLabelStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#999',
  marginBottom: '4px'
};

const summaryStatValueStyle: React.CSSProperties = {
  fontSize: '20px',
  color: '#22c55e',
  fontWeight: 700
};

const learningStatusStyle: React.CSSProperties = {
  fontSize: '14px',
  color: '#ccc',
  textAlign: 'center',
  marginBottom: '20px'
};

const recentActivityStyle: React.CSSProperties = {
  borderTop: '1px solid #333',
  paddingTop: '16px'
};

const activityTitleStyle: React.CSSProperties = {
  fontSize: '14px',
  color: '#fff',
  fontWeight: 600,
  marginBottom: '12px'
};

const activityGridStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '8px'
};

const activityItemStyle: React.CSSProperties = {
  background: '#0a0a0a',
  border: '1px solid #333',
  borderRadius: '6px',
  padding: '8px 12px',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center'
};

const activityDateStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#22c55e',
  fontWeight: 600
};

const activityMetricsStyle: React.CSSProperties = {
  fontSize: '11px',
  color: '#999'
};