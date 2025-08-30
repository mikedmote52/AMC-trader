import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Progress } from './ui/progress';
import { TrendingUp, TrendingDown, Target, AlertTriangle, Activity, BarChart3 } from 'lucide-react';

interface PerformanceMetrics {
  baseline: {
    period: string;
    best_performer: {
      symbol: string;
      return: string;
      entry_price: number;
      peak_price: number;
      pattern: string;
    };
    portfolio_metrics: {
      average_return: string;
      win_rate: string;
      total_positions: number;
      explosive_growth_rate: string;
    };
  };
  current: {
    total_positions: number;
    average_return: number;
    win_rate: number;
    explosive_growth_rate: number;
    portfolio_value: number;
    best_performer?: {
      symbol: string;
      return: string;
      value: number;
    };
    worst_performer?: {
      symbol: string;
      return: string;
      value: number;
    };
  };
  recovery: {
    days_since_baseline: number;
    performance_gap: number;
    recovery_progress_pct: number;
    recovery_status: string;
    projected_recovery_date?: string;
    key_metrics_status: {
      average_return: string;
      win_rate: string;
      explosive_growth: string;
    };
  };
  squeeze_analysis: {
    current_squeeze_candidates: Array<{
      symbol: string;
      pattern_score: number;
      composite_score: number;
      price: number;
    }>;
    total_candidates_found: number;
    high_probability_count: number;
    vigl_similarity_found: boolean;
    pattern_detection_status: string;
  };
  system_health: {
    overall_health_score: number;
    system_status: string;
    active_alerts_count: number;
  };
}

const PerformanceAnalyticsDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      const response = await fetch('/analytics/performance');
      if (!response.ok) {
        throw new Error('Failed to fetch performance metrics');
      }
      const data = await response.json();
      setMetrics(data);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 60000); // Update every minute
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status.toUpperCase()) {
      case 'CRITICAL': return 'bg-red-500';
      case 'WARNING': return 'bg-yellow-500';
      case 'GOOD': return 'bg-green-500';
      case 'HEALTHY': return 'bg-green-500';
      case 'DEGRADED': return 'bg-yellow-500';
      default: return 'bg-gray-500';
    }
  };

  const getRecoveryStatusIcon = (status: string) => {
    switch (status.toUpperCase()) {
      case 'ACHIEVED': return <Target className="w-4 h-4 text-green-500" />;
      case 'ON_TRACK': return <TrendingUp className="w-4 h-4 text-blue-500" />;
      case 'BEHIND_SCHEDULE': return <TrendingDown className="w-4 h-4 text-red-500" />;
      default: return <Activity className="w-4 h-4 text-gray-500" />;
    }
  };

  if (loading && !metrics) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <Card className="border-red-200">
        <CardContent className="p-6">
          <div className="flex items-center text-red-600">
            <AlertTriangle className="w-5 h-5 mr-2" />
            Error loading performance analytics: {error}
          </div>
          <Button onClick={fetchMetrics} className="mt-4">
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!metrics) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Performance Analytics</h2>
          <p className="text-muted-foreground">
            Tracking recovery to June-July 2024 explosive growth baseline
          </p>
        </div>
        <div className="text-sm text-muted-foreground">
          Last updated: {lastUpdated.toLocaleTimeString()}
        </div>
      </div>

      {/* Recovery Progress Card */}
      <Card className="border-l-4 border-l-blue-500">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                {getRecoveryStatusIcon(metrics.recovery.recovery_status)}
                Recovery Progress
              </CardTitle>
              <CardDescription>
                Progress toward June-July baseline performance
              </CardDescription>
            </div>
            <Badge className={getStatusColor(metrics.recovery.recovery_status)}>
              {metrics.recovery.recovery_status.replace('_', ' ')}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Overall Progress</span>
                <span className="text-sm">{metrics.recovery.recovery_progress_pct.toFixed(1)}%</span>
              </div>
              <Progress value={metrics.recovery.recovery_progress_pct} className="w-full" />
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="text-muted-foreground">Days Since Baseline</div>
                <div className="font-semibold">{metrics.recovery.days_since_baseline}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Performance Gap</div>
                <div className={`font-semibold ${metrics.recovery.performance_gap < 0 ? 'text-red-500' : 'text-green-500'}`}>
                  {metrics.recovery.performance_gap > 0 ? '+' : ''}{metrics.recovery.performance_gap.toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-muted-foreground">Recovery Target</div>
                <div className="font-semibold">{metrics.recovery.projected_recovery_date || 'TBD'}</div>
              </div>
              <div>
                <div className="text-muted-foreground">System Health</div>
                <div className="font-semibold">{metrics.system_health.overall_health_score.toFixed(0)}%</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Current Performance */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Portfolio Performance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm">Current Return</span>
                <span className={`font-semibold ${metrics.current.average_return >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {metrics.current.average_return >= 0 ? '+' : ''}{metrics.current.average_return.toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm">Target Return</span>
                <span className="font-semibold text-blue-500">+152%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm">Win Rate</span>
                <span className="font-semibold">{metrics.current.win_rate.toFixed(1)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm">Portfolio Value</span>
                <span className="font-semibold">${metrics.current.portfolio_value.toLocaleString()}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Baseline Comparison */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Baseline Comparison</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm">Best Historical</span>
                <span className="font-semibold text-green-500">
                  {metrics.baseline.best_performer.symbol} {metrics.baseline.best_performer.return}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm">Baseline Win Rate</span>
                <span className="font-semibold">{metrics.baseline.portfolio_metrics.win_rate}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm">Explosive Growth</span>
                <span className="font-semibold">{metrics.baseline.portfolio_metrics.explosive_growth_rate}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm">Current Explosive</span>
                <span className="font-semibold">{metrics.current.explosive_growth_rate.toFixed(1)}%</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Squeeze Detection */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Squeeze Detection</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm">Candidates Found</span>
                <span className="font-semibold">{metrics.squeeze_analysis.total_candidates_found}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm">High Probability</span>
                <span className="font-semibold text-orange-500">{metrics.squeeze_analysis.high_probability_count}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm">VIGL-like Found</span>
                <span className={`font-semibold ${metrics.squeeze_analysis.vigl_similarity_found ? 'text-green-500' : 'text-gray-500'}`}>
                  {metrics.squeeze_analysis.vigl_similarity_found ? 'YES' : 'NO'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm">Detection Status</span>
                <Badge className={getStatusColor(metrics.squeeze_analysis.pattern_detection_status)}>
                  {metrics.squeeze_analysis.pattern_detection_status}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* System Health */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">System Health</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm">Overall Health</span>
                <span className="font-semibold">{metrics.system_health.overall_health_score.toFixed(0)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm">System Status</span>
                <Badge className={getStatusColor(metrics.system_health.system_status)}>
                  {metrics.system_health.system_status}
                </Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-sm">Active Alerts</span>
                <span className={`font-semibold ${metrics.system_health.active_alerts_count > 0 ? 'text-red-500' : 'text-green-500'}`}>
                  {metrics.system_health.active_alerts_count}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm">Positions</span>
                <span className="font-semibold">{metrics.current.total_positions}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Current Squeeze Candidates */}
      {metrics.squeeze_analysis.current_squeeze_candidates.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              Current Squeeze Candidates
            </CardTitle>
            <CardDescription>
              Stocks showing VIGL-like squeeze patterns
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {metrics.squeeze_analysis.current_squeeze_candidates.map((candidate) => (
                <div key={candidate.symbol} className="border rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-lg">{candidate.symbol}</span>
                    <Badge className={candidate.pattern_score >= 75 ? 'bg-green-500' : 'bg-yellow-500'}>
                      {candidate.pattern_score >= 75 ? 'HIGH' : 'MEDIUM'}
                    </Badge>
                  </div>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span>Pattern Score</span>
                      <span className="font-semibold">{candidate.pattern_score.toFixed(0)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Composite Score</span>
                      <span className="font-semibold">{candidate.composite_score.toFixed(1)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Price</span>
                      <span className="font-semibold">${candidate.price.toFixed(2)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Performance Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className={`border-l-4 border-l-${metrics.recovery.key_metrics_status.average_return === 'GOOD' ? 'green' : metrics.recovery.key_metrics_status.average_return === 'WARNING' ? 'yellow' : 'red'}-500`}>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Average Return</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {metrics.current.average_return >= 0 ? '+' : ''}{metrics.current.average_return.toFixed(1)}%
            </div>
            <div className="text-sm text-muted-foreground">
              Target: +152% | Gap: {metrics.recovery.performance_gap.toFixed(1)}%
            </div>
            <Badge className={getStatusColor(metrics.recovery.key_metrics_status.average_return)}>
              {metrics.recovery.key_metrics_status.average_return}
            </Badge>
          </CardContent>
        </Card>

        <Card className={`border-l-4 border-l-${metrics.recovery.key_metrics_status.win_rate === 'GOOD' ? 'green' : metrics.recovery.key_metrics_status.win_rate === 'WARNING' ? 'yellow' : 'red'}-500`}>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Win Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.current.win_rate.toFixed(1)}%</div>
            <div className="text-sm text-muted-foreground">
              Target: 73% | Current Status
            </div>
            <Badge className={getStatusColor(metrics.recovery.key_metrics_status.win_rate)}>
              {metrics.recovery.key_metrics_status.win_rate}
            </Badge>
          </CardContent>
        </Card>

        <Card className={`border-l-4 border-l-${metrics.recovery.key_metrics_status.explosive_growth === 'GOOD' ? 'green' : metrics.recovery.key_metrics_status.explosive_growth === 'WARNING' ? 'yellow' : 'red'}-500`}>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Explosive Growth</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.current.explosive_growth_rate.toFixed(1)}%</div>
            <div className="text-sm text-muted-foreground">
              Target: 46.7% | >50% returns
            </div>
            <Badge className={getStatusColor(metrics.recovery.key_metrics_status.explosive_growth)}>
              {metrics.recovery.key_metrics_status.explosive_growth}
            </Badge>
          </CardContent>
        </Card>
      </div>

      {/* Action Items */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>Analytics and monitoring tools</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 flex-wrap">
            <Button onClick={() => window.open('/analytics/comprehensive-report', '_blank')}>
              📊 Full Report
            </Button>
            <Button onClick={() => window.open('/analytics/backtesting/squeeze-detector', '_blank')}>
              🔬 Backtest Results  
            </Button>
            <Button onClick={() => window.open('/analytics/dashboard/executive', '_blank')}>
              👔 Executive Dashboard
            </Button>
            <Button onClick={fetchMetrics} variant="outline">
              🔄 Refresh Data
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default PerformanceAnalyticsDashboard;