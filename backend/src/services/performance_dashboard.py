import asyncio
import asyncpg
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
import statistics
import os

from .performance_analytics import PerformanceAnalytics, BaselineMetrics
from .discovery_tracker import DiscoveryPerformanceTracker
from .thesis_accuracy_tracker import ThesisAccuracyTracker
from .market_timing_analyzer import MarketTimingAnalyzer
from .risk_management_tracker import RiskManagementTracker
from .system_health_monitor import SystemHealthMonitor

@dataclass
class DashboardSummary:
    """Executive dashboard summary"""
    timestamp: datetime
    
    # Critical Performance Indicators
    overall_performance_grade: str  # A, B, C, D, F
    vs_baseline_status: str  # AHEAD, BEHIND, CRITICAL
    restoration_progress: float  # % progress toward June-July levels
    
    # Key Metrics Summary
    current_win_rate: float
    current_avg_return: float
    explosive_growth_rate: float
    total_positions: int
    
    # System Health Summary
    system_health_score: float
    critical_alerts: int
    components_down: int
    
    # Priority Actions
    top_priority_action: str
    days_to_baseline_restoration: Optional[int]
    immediate_actions_required: int
    
    # Performance Gaps
    win_rate_gap: float  # vs baseline
    return_gap: float    # vs baseline
    explosive_gap: float # vs baseline

@dataclass
class PerformanceReport:
    """Comprehensive performance report"""
    report_id: str
    generated_at: datetime
    period_days: int
    
    # Executive Summary
    executive_summary: DashboardSummary
    
    # Detailed Analytics
    performance_metrics: Dict
    discovery_analysis: Dict
    thesis_accuracy: Dict
    market_timing: Dict
    risk_management: Dict
    system_health: Dict
    
    # Comparative Analysis
    baseline_comparison: Dict
    vigl_analysis: Dict
    trend_analysis: Dict
    
    # Action Plans
    restoration_roadmap: List[Dict]
    immediate_actions: List[str]
    weekly_goals: List[str]
    success_metrics: Dict
    
    # Insights
    key_findings: List[str]
    root_cause_analysis: Dict
    improvement_opportunities: List[Dict]

class PerformanceDashboard:
    """Comprehensive performance analytics dashboard"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv('DATABASE_URL', 'postgresql://localhost/amc_trader')
        
        # Initialize analytics components
        self.performance_analytics = PerformanceAnalytics()
        self.discovery_tracker = DiscoveryPerformanceTracker()
        self.thesis_tracker = ThesisAccuracyTracker()
        self.timing_analyzer = MarketTimingAnalyzer()
        self.risk_tracker = RiskManagementTracker()
        self.health_monitor = SystemHealthMonitor()
        
        # Baseline for comparison
        self.baseline = BaselineMetrics()
    
    async def generate_comprehensive_dashboard(self, period_days: int = 30) -> DashboardSummary:
        """Generate executive dashboard summary"""
        
        # Collect metrics from all systems
        performance_metrics = await self.performance_analytics.calculate_comprehensive_metrics(period_days)
        discovery_report = await self.discovery_tracker.generate_discovery_report(7)  # Last week
        thesis_report = await self.thesis_tracker.generate_thesis_accuracy_report(period_days)
        timing_report = await self.timing_analyzer.generate_timing_report(period_days)
        risk_report = await self.risk_tracker.generate_risk_management_report()
        health_report = await self.health_monitor.generate_health_report()
        
        # Calculate overall performance grade
        overall_grade = self._calculate_overall_grade(
            performance_metrics, discovery_report, thesis_report, timing_report, risk_report, health_report
        )
        
        # Determine baseline status
        baseline_status = self._determine_baseline_status(performance_metrics)
        
        # Calculate restoration progress
        restoration_progress = self._calculate_restoration_progress(performance_metrics)
        
        # Identify top priority action
        top_priority = self._identify_top_priority_action(
            performance_metrics, discovery_report, thesis_report, timing_report, risk_report, health_report
        )
        
        # Calculate gaps
        win_rate_gap = performance_metrics.win_rate - self.baseline.win_rate
        return_gap = performance_metrics.average_return - self.baseline.average_return
        explosive_gap = performance_metrics.explosive_growth_rate - self.baseline.explosive_growth_rate
        
        summary = DashboardSummary(
            timestamp=datetime.utcnow(),
            overall_performance_grade=overall_grade,
            vs_baseline_status=baseline_status,
            restoration_progress=restoration_progress,
            
            current_win_rate=performance_metrics.win_rate,
            current_avg_return=performance_metrics.average_return,
            explosive_growth_rate=performance_metrics.explosive_growth_rate,
            total_positions=performance_metrics.total_positions,
            
            system_health_score=health_report['executive_summary']['overall_health_score'],
            critical_alerts=len(health_report['critical_actions']),
            components_down=len(health_report['executive_summary']['critical_components']),
            
            top_priority_action=top_priority,
            days_to_baseline_restoration=self._estimate_restoration_days(restoration_progress),
            immediate_actions_required=len(health_report['critical_actions']),
            
            win_rate_gap=win_rate_gap,
            return_gap=return_gap,
            explosive_gap=explosive_gap
        )
        
        # Store dashboard summary
        await self._store_dashboard_summary(summary)
        
        return summary
    
    async def generate_comprehensive_report(self, period_days: int = 30) -> PerformanceReport:
        """Generate comprehensive performance analysis report"""
        
        report_id = f"perf_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Generate dashboard summary
        executive_summary = await self.generate_comprehensive_dashboard(period_days)
        
        # Collect detailed analytics
        performance_metrics = await self.performance_analytics.calculate_comprehensive_metrics(period_days)
        performance_report = await self.performance_analytics.generate_performance_report(performance_metrics)
        
        discovery_report = await self.discovery_tracker.generate_discovery_report(7)
        thesis_report = await self.thesis_tracker.generate_thesis_accuracy_report(period_days)
        timing_report = await self.timing_analyzer.generate_timing_report(period_days)
        risk_report = await self.risk_tracker.generate_risk_management_report()
        health_report = await self.health_monitor.generate_health_report()
        
        # Baseline comparison analysis
        baseline_comparison = self._generate_baseline_comparison(performance_metrics)
        
        # VIGL analysis
        vigl_analysis = self._generate_vigl_analysis(
            performance_metrics, discovery_report, timing_report, risk_report
        )
        
        # Trend analysis
        trend_analysis = await self._generate_trend_analysis(period_days)
        
        # Restoration roadmap
        restoration_roadmap = self._generate_restoration_roadmap(
            performance_metrics, discovery_report, thesis_report, timing_report, risk_report
        )
        
        # Key findings and root cause analysis
        key_findings = self._generate_key_findings(
            performance_metrics, discovery_report, thesis_report, timing_report, risk_report, health_report
        )
        
        root_cause_analysis = self._perform_root_cause_analysis(
            performance_metrics, discovery_report, thesis_report, timing_report
        )
        
        # Improvement opportunities
        improvement_opportunities = self._identify_improvement_opportunities(
            performance_metrics, discovery_report, thesis_report, timing_report, risk_report
        )
        
        report = PerformanceReport(
            report_id=report_id,
            generated_at=datetime.utcnow(),
            period_days=period_days,
            
            executive_summary=executive_summary,
            
            performance_metrics=asdict(performance_metrics),
            discovery_analysis=discovery_report,
            thesis_accuracy=thesis_report,
            market_timing=timing_report,
            risk_management=risk_report,
            system_health=health_report,
            
            baseline_comparison=baseline_comparison,
            vigl_analysis=vigl_analysis,
            trend_analysis=trend_analysis,
            
            restoration_roadmap=restoration_roadmap,
            immediate_actions=self._collect_immediate_actions([discovery_report, thesis_report, timing_report, risk_report, health_report]),
            weekly_goals=self._generate_weekly_goals(restoration_roadmap),
            success_metrics=self._define_success_metrics(),
            
            key_findings=key_findings,
            root_cause_analysis=root_cause_analysis,
            improvement_opportunities=improvement_opportunities
        )
        
        # Store comprehensive report
        await self._store_performance_report(report)
        
        return report
    
    def _calculate_overall_grade(self, performance_metrics, discovery_report, thesis_report, 
                               timing_report, risk_report, health_report) -> str:
        """Calculate overall performance grade A-F"""
        
        # Component scores (0-100)
        scores = {}
        
        # Performance score (40% weight)
        if performance_metrics.average_return > 50:
            scores['performance'] = 95
        elif performance_metrics.average_return > 20:
            scores['performance'] = 85
        elif performance_metrics.average_return > 0:
            scores['performance'] = 70
        elif performance_metrics.average_return > -10:
            scores['performance'] = 50
        else:
            scores['performance'] = 20
        
        # Discovery score (25% weight)
        discovery_status = discovery_report['summary']['status']
        scores['discovery'] = 90 if discovery_status == 'GOOD' else \
                             70 if discovery_status == 'WARNING' else 30
        
        # Thesis accuracy score (15% weight)
        thesis_accuracy = thesis_report['period_summary']['overall_accuracy']
        scores['thesis'] = max(0, min(100, thesis_accuracy))
        
        # Timing score (10% weight)
        timing_status = timing_report['summary']['status']
        scores['timing'] = 90 if timing_status == 'EXCELLENT' else \
                          80 if timing_status == 'GOOD' else \
                          60 if timing_status == 'FAIR' else 30
        
        # Risk score (10% weight)
        risk_grade = risk_report['executive_summary']['portfolio_risk_grade']
        risk_score = {'A': 95, 'B': 85, 'C': 70, 'D': 50, 'F': 20}.get(risk_grade, 50)
        scores['risk'] = risk_score
        
        # Calculate weighted average
        weights = {'performance': 0.4, 'discovery': 0.25, 'thesis': 0.15, 'timing': 0.1, 'risk': 0.1}
        overall_score = sum(scores[component] * weight for component, weight in weights.items())
        
        # Convert to letter grade
        if overall_score >= 90:
            return 'A'
        elif overall_score >= 80:
            return 'B'
        elif overall_score >= 70:
            return 'C'
        elif overall_score >= 60:
            return 'D'
        else:
            return 'F'
    
    def _determine_baseline_status(self, performance_metrics) -> str:
        """Determine status vs June-July baseline"""
        return_gap = performance_metrics.average_return - self.baseline.average_return
        
        if return_gap > -10:
            return 'AHEAD'
        elif return_gap > -30:
            return 'BEHIND'
        else:
            return 'CRITICAL'
    
    def _calculate_restoration_progress(self, performance_metrics) -> float:
        """Calculate progress toward baseline restoration"""
        
        # Key metrics to track
        current_return = performance_metrics.average_return
        current_win_rate = performance_metrics.win_rate
        current_explosive = performance_metrics.explosive_growth_rate
        
        # Calculate progress for each metric (assuming starting from -20%)
        starting_return = -20.0  # Assumed current poor performance
        target_return = self.baseline.average_return
        
        if current_return <= starting_return:
            return_progress = 0.0
        elif current_return >= target_return:
            return_progress = 100.0
        else:
            return_progress = ((current_return - starting_return) / (target_return - starting_return)) * 100
        
        # Similar for other metrics
        starting_win_rate = 30.0
        target_win_rate = self.baseline.win_rate
        win_rate_progress = max(0, min(100, ((current_win_rate - starting_win_rate) / (target_win_rate - starting_win_rate)) * 100))
        
        starting_explosive = 5.0
        target_explosive = self.baseline.explosive_growth_rate
        explosive_progress = max(0, min(100, ((current_explosive - starting_explosive) / (target_explosive - starting_explosive)) * 100))
        
        # Weighted average
        overall_progress = (return_progress * 0.4 + win_rate_progress * 0.3 + explosive_progress * 0.3)
        return max(0.0, min(100.0, overall_progress))
    
    def _identify_top_priority_action(self, performance_metrics, discovery_report, thesis_report,
                                    timing_report, risk_report, health_report) -> str:
        """Identify the single most critical action needed"""
        
        # Critical system issues first
        if health_report['executive_summary']['critical_components']:
            critical_components = health_report['executive_summary']['critical_components']
            if 'discovery' in critical_components:
                return "URGENT: Restore discovery system - no new opportunities being found"
            return f"URGENT: Fix critical system component - {critical_components[0]}"
        
        # Performance issues
        if performance_metrics.average_return < -15:
            return "URGENT: Stop losses - implement emergency position management"
        
        # Discovery quality issues
        if discovery_report['summary']['explosive_rate'] < 10:
            return "URGENT: Restore VIGL pattern detection - no explosive growth candidates"
        
        # Thesis accuracy issues
        if thesis_report['period_summary']['overall_accuracy'] < 50:
            return "URGENT: Fix thesis generation - predictions worse than random"
        
        # Timing issues
        if timing_report['summary']['vigl_gap'] > 15:
            return "HIGH: Restore immediate entry system like VIGL approach"
        
        # Risk management issues
        if risk_report['executive_summary']['critical_positions'] > 0:
            return "HIGH: Liquidate critical loss positions to preserve capital"
        
        return "Continue monitoring - system performance within acceptable range"
    
    def _estimate_restoration_days(self, restoration_progress: float) -> Optional[int]:
        """Estimate days to complete baseline restoration"""
        if restoration_progress >= 90:
            return 0  # Already there
        
        if restoration_progress < 10:
            return None  # Too early to estimate
        
        # Assume linear progress improvement (optimistic)
        # If at 50% progress, estimate 30 more days to reach 90%
        remaining_progress = 90 - restoration_progress
        days_per_percent = 0.75  # Estimated days per percent of progress
        
        return int(remaining_progress * days_per_percent)
    
    def _generate_baseline_comparison(self, performance_metrics) -> Dict:
        """Generate detailed baseline comparison"""
        return {
            'baseline_period': self.baseline.benchmark_period,
            'baseline_metrics': asdict(self.baseline),
            'current_metrics': {
                'win_rate': performance_metrics.win_rate,
                'average_return': performance_metrics.average_return,
                'explosive_growth_rate': performance_metrics.explosive_growth_rate
            },
            'gaps': {
                'win_rate_gap': performance_metrics.win_rate - self.baseline.win_rate,
                'return_gap': performance_metrics.average_return - self.baseline.average_return,
                'explosive_gap': performance_metrics.explosive_growth_rate - self.baseline.explosive_growth_rate
            },
            'gap_severity': {
                'win_rate': 'CRITICAL' if performance_metrics.win_rate - self.baseline.win_rate < -30 else 'WARNING',
                'returns': 'CRITICAL' if performance_metrics.average_return - self.baseline.average_return < -40 else 'WARNING',
                'explosive': 'CRITICAL' if performance_metrics.explosive_growth_rate - self.baseline.explosive_growth_rate < -30 else 'WARNING'
            }
        }
    
    def _generate_vigl_analysis(self, performance_metrics, discovery_report, timing_report, risk_report) -> Dict:
        """Generate VIGL pattern analysis"""
        return {
            'vigl_characteristics': {
                'return': '324% explosive growth',
                'timing': 'Immediate entry upon discovery',
                'risk': 'Conservative position sizing',
                'pattern': 'Volume spike >20x, price $2.94-$4.66',
                'hold_duration': '45 days to peak'
            },
            'current_vs_vigl': {
                'discovery_vigl_rate': discovery_report.get('vigl_analysis', {}).get('vigl_detection_rate', 0),
                'timing_gap': timing_report['summary']['vigl_gap'],
                'risk_gap': risk_report.get('vigl_comparison', {}).get('risk_gaps', {}).get('position_risk', 0)
            },
            'vigl_restoration_steps': [
                'Restore volume threshold to 20.9x average',
                'Focus on $2.94-$4.66 price range',
                'Implement immediate entry system',
                'Conservative position sizing (10% max)',
                'High conviction, low risk approach'
            ]
        }
    
    async def _generate_trend_analysis(self, period_days: int) -> Dict:
        """Generate trend analysis over time"""
        # Get historical data for trend analysis
        pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=10)
        
        try:
            async with pool.acquire() as conn:
                # Get performance trends
                trend_query = """
                SELECT calculated_at, metrics_json
                FROM performance_metrics
                WHERE calculated_at >= $1
                ORDER BY calculated_at ASC
                """
                
                start_date = datetime.utcnow() - timedelta(days=period_days * 2)  # Double period for trend
                rows = await conn.fetch(trend_query, start_date)
                
                trends = []
                for row in rows:
                    try:
                        metrics = json.loads(row['metrics_json'])
                        trends.append({
                            'date': row['calculated_at'],
                            'avg_return': metrics.get('average_return', 0),
                            'win_rate': metrics.get('win_rate', 0),
                            'explosive_rate': metrics.get('explosive_growth_rate', 0)
                        })
                    except:
                        continue
                
                if len(trends) < 3:
                    return {'status': 'insufficient_data', 'trends': trends}
                
                # Analyze trends
                recent_returns = [t['avg_return'] for t in trends[-3:]]
                older_returns = [t['avg_return'] for t in trends[:3]]
                
                return_trend = statistics.mean(recent_returns) - statistics.mean(older_returns)
                
                return {
                    'status': 'improving' if return_trend > 5 else 'declining' if return_trend < -5 else 'stable',
                    'return_trend': return_trend,
                    'data_points': len(trends),
                    'trends': trends
                }
                
        except Exception as e:
            print(f"Error generating trend analysis: {e}")
            return {'status': 'error', 'trends': []}
        finally:
            await pool.close()
    
    def _generate_restoration_roadmap(self, performance_metrics, discovery_report, thesis_report,
                                    timing_report, risk_report) -> List[Dict]:
        """Generate comprehensive restoration roadmap"""
        roadmap = []
        
        # Phase 1: Stop the bleeding (Week 1)
        phase1_actions = []
        if risk_report['executive_summary']['critical_positions'] > 0:
            phase1_actions.append('Liquidate critical loss positions')
        if performance_metrics.average_return < -15:
            phase1_actions.append('Implement emergency position sizing limits')
        
        if phase1_actions:
            roadmap.append({
                'phase': 1,
                'title': 'Emergency Stabilization',
                'duration': '1 week',
                'priority': 'CRITICAL',
                'actions': phase1_actions,
                'success_metrics': ['Stop major losses', 'Reduce risk exposure', 'Stabilize portfolio']
            })
        
        # Phase 2: Restore discovery system (Week 2-3)
        discovery_actions = []
        if discovery_report['summary']['explosive_rate'] < 20:
            discovery_actions.append('Restore VIGL pattern detection algorithm')
            discovery_actions.append('Calibrate volume threshold to 20.9x average')
            discovery_actions.append('Focus price range $2.94-$4.66')
        
        if discovery_actions:
            roadmap.append({
                'phase': 2,
                'title': 'Discovery System Restoration',
                'duration': '2 weeks',
                'priority': 'URGENT',
                'actions': discovery_actions,
                'success_metrics': ['20%+ explosive candidates', 'Average composite score >6.0', 'Daily candidate count >5']
            })
        
        # Phase 3: Improve execution (Week 4-5)
        execution_actions = []
        if timing_report['summary']['vigl_gap'] > 10:
            execution_actions.append('Implement same-day entry system')
        if thesis_report['period_summary']['overall_accuracy'] < 70:
            execution_actions.append('Retrain thesis generation algorithm')
        
        if execution_actions:
            roadmap.append({
                'phase': 3,
                'title': 'Execution Enhancement',
                'duration': '2 weeks',
                'priority': 'HIGH',
                'actions': execution_actions,
                'success_metrics': ['<1 day entry delay', '>70% thesis accuracy', 'Improved timing scores']
            })
        
        # Phase 4: Performance optimization (Week 6-8)
        roadmap.append({
            'phase': 4,
            'title': 'Performance Optimization',
            'duration': '3 weeks',
            'priority': 'MEDIUM',
            'actions': [
                'Fine-tune all system parameters',
                'Optimize position sizing strategy',
                'Implement advanced analytics',
                'Monitor progress vs baseline'
            ],
            'success_metrics': ['Approach baseline metrics', '>60% win rate', '>30% avg returns']
        })
        
        return roadmap
    
    def _generate_key_findings(self, performance_metrics, discovery_report, thesis_report,
                             timing_report, risk_report, health_report) -> List[str]:
        """Generate key analytical findings"""
        findings = []
        
        # Performance findings
        if performance_metrics.average_return < -10:
            findings.append(f"Performance severely degraded at {performance_metrics.average_return:.1f}% vs {self.baseline.average_return:.1f}% baseline")
        
        # Discovery findings
        if discovery_report['summary']['explosive_rate'] < 10:
            findings.append(f"Discovery system missing explosive candidates - only {discovery_report['summary']['explosive_rate']:.1f}% vs 46.7% baseline")
        
        # Thesis findings
        if thesis_report['period_summary']['overall_accuracy'] < 60:
            findings.append(f"Thesis accuracy critically low at {thesis_report['period_summary']['overall_accuracy']:.1f}%")
        
        # Timing findings
        if timing_report['summary']['avg_entry_delay'] > 2:
            findings.append(f"Entry delays averaging {timing_report['summary']['avg_entry_delay']:.1f} days vs VIGL's immediate entry")
        
        # Risk findings
        if risk_report['executive_summary']['portfolio_risk_grade'] in ['D', 'F']:
            findings.append(f"Risk management grade {risk_report['executive_summary']['portfolio_risk_grade']} indicates poor risk control")
        
        # System health findings
        if health_report['executive_summary']['overall_health_score'] < 60:
            findings.append(f"System health critically low at {health_report['executive_summary']['overall_health_score']:.1f}%")
        
        return findings
    
    def _perform_root_cause_analysis(self, performance_metrics, discovery_report, thesis_report, timing_report) -> Dict:
        """Perform root cause analysis of performance issues"""
        
        root_causes = {}
        
        # Discovery root causes
        if discovery_report['summary']['explosive_rate'] < 20:
            root_causes['discovery'] = {
                'primary_cause': 'VIGL pattern detection algorithm degraded',
                'contributing_factors': [
                    'Volume threshold may have been changed from 20.9x',
                    'Price range filter not focused on $2.94-$4.66',
                    'Composite scoring algorithm modified',
                    'Market data quality issues affecting pattern recognition'
                ],
                'impact': 'Missing 324% explosive growth opportunities like VIGL',
                'solution': 'Restore June-July discovery algorithm parameters exactly'
            }
        
        # Thesis root causes
        if thesis_report['period_summary']['overall_accuracy'] < 65:
            root_causes['thesis'] = {
                'primary_cause': 'Thesis generation algorithm producing poor predictions',
                'contributing_factors': [
                    'Training data may not include successful patterns',
                    'Confidence scoring miscalibrated',
                    'Market context analysis degraded',
                    'Sector analysis not reflecting current conditions'
                ],
                'impact': 'Poor buy/sell/hold decisions reducing win rate',
                'solution': 'Retrain using June-July successful thesis patterns'
            }
        
        # Timing root causes
        if timing_report['summary']['avg_entry_delay'] > 1:
            root_causes['timing'] = {
                'primary_cause': 'Entry execution system not immediate like VIGL',
                'contributing_factors': [
                    'Manual approval processes causing delays',
                    'Hesitation on high-conviction opportunities',
                    'System latency in processing discoveries',
                    'Risk aversion preventing quick entry'
                ],
                'impact': 'Missing optimal entry prices, reducing returns',
                'solution': 'Implement VIGL-style immediate entry system'
            }
        
        return root_causes
    
    def _identify_improvement_opportunities(self, performance_metrics, discovery_report, thesis_report,
                                          timing_report, risk_report) -> List[Dict]:
        """Identify specific improvement opportunities"""
        opportunities = []
        
        # Discovery improvements
        if discovery_report['summary']['explosive_rate'] < 30:
            opportunities.append({
                'area': 'Discovery System',
                'opportunity': 'Restore VIGL-style pattern detection',
                'current_state': f"{discovery_report['summary']['explosive_rate']:.1f}% explosive rate",
                'target_state': '46.7% explosive rate (baseline)',
                'potential_impact': 'Could restore 324% explosive growth opportunities',
                'implementation_effort': 'Medium - algorithm parameter restoration',
                'timeline': '2-3 weeks'
            })
        
        # Timing improvements
        if timing_report['summary']['avg_entry_delay'] > 0.5:
            opportunities.append({
                'area': 'Market Timing',
                'opportunity': 'Implement same-day entry system',
                'current_state': f"{timing_report['summary']['avg_entry_delay']:.1f} day average delay",
                'target_state': '0 day delay (VIGL baseline)',
                'potential_impact': f"Could improve returns by {timing_report['summary']['potential_improvement']:.1f}%",
                'implementation_effort': 'Low - process automation',
                'timeline': '1 week'
            })
        
        # Risk management improvements
        if risk_report['executive_summary']['portfolio_risk_grade'] in ['C', 'D', 'F']:
            opportunities.append({
                'area': 'Risk Management',
                'opportunity': 'Adopt VIGL-style conservative approach',
                'current_state': f"Grade {risk_report['executive_summary']['portfolio_risk_grade']}",
                'target_state': 'Grade A risk management',
                'potential_impact': 'Reduce losses, improve risk-adjusted returns',
                'implementation_effort': 'Medium - position sizing rules',
                'timeline': '1-2 weeks'
            })
        
        return opportunities
    
    def _collect_immediate_actions(self, reports: List[Dict]) -> List[str]:
        """Collect all immediate actions from reports"""
        actions = []
        
        for report in reports:
            if 'recommendations' in report:
                for rec in report['recommendations']:
                    if isinstance(rec, str) and ('IMMEDIATE' in rec or 'URGENT' in rec):
                        actions.append(rec)
            if 'critical_actions' in report:
                actions.extend(report['critical_actions'])
            if 'next_actions' in report:
                urgent_actions = [a for a in report['next_actions'] if 'IMMEDIATE' in a or 'URGENT' in a]
                actions.extend(urgent_actions)
        
        return list(set(actions))  # Remove duplicates
    
    def _generate_weekly_goals(self, roadmap: List[Dict]) -> List[str]:
        """Generate weekly goals from roadmap"""
        goals = []
        
        for phase in roadmap[:2]:  # Next 2 phases
            phase_goals = [f"Phase {phase['phase']}: {phase['title']}"]
            phase_goals.extend([f"- {action}" for action in phase['actions'][:3]])  # Top 3 actions
            goals.extend(phase_goals)
        
        return goals
    
    def _define_success_metrics(self) -> Dict:
        """Define key success metrics for tracking"""
        return {
            'primary_metrics': {
                'win_rate_target': self.baseline.win_rate,
                'avg_return_target': self.baseline.average_return,
                'explosive_growth_target': self.baseline.explosive_growth_rate
            },
            'system_metrics': {
                'discovery_candidates_per_day': 8,
                'thesis_accuracy_target': 73.0,
                'entry_delay_target': 0,
                'system_health_target': 90.0
            },
            'milestone_targets': {
                '30_day': {'win_rate': 50, 'avg_return': 10, 'explosive_rate': 20},
                '60_day': {'win_rate': 60, 'avg_return': 25, 'explosive_rate': 30},
                '90_day': {'win_rate': 70, 'avg_return': 50, 'explosive_rate': 40}
            }
        }
    
    async def _store_dashboard_summary(self, summary: DashboardSummary):
        """Store dashboard summary in database"""
        pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=10)
        
        try:
            async with pool.acquire() as conn:
                query = """
                INSERT INTO dashboard_summaries
                (timestamp, summary_json, overall_grade, baseline_status, restoration_progress)
                VALUES ($1, $2, $3, $4, $5)
                """
                
                summary_json = json.dumps(asdict(summary), default=str)
                
                await conn.execute(query,
                                 summary.timestamp,
                                 summary_json,
                                 summary.overall_performance_grade,
                                 summary.vs_baseline_status,
                                 summary.restoration_progress)
                                 
        except Exception as e:
            print(f"Error storing dashboard summary: {e}")
        finally:
            await pool.close()
    
    async def _store_performance_report(self, report: PerformanceReport):
        """Store comprehensive performance report"""
        pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=10)
        
        try:
            async with pool.acquire() as conn:
                query = """
                INSERT INTO performance_reports
                (report_id, generated_at, period_days, report_json)
                VALUES ($1, $2, $3, $4)
                """
                
                report_json = json.dumps(asdict(report), default=str)
                
                await conn.execute(query,
                                 report.report_id,
                                 report.generated_at,
                                 report.period_days,
                                 report_json)
                                 
        except Exception as e:
            print(f"Error storing performance report: {e}")
        finally:
            await pool.close()

# Database tables for dashboard
CREATE_DASHBOARD_TABLES = """
CREATE TABLE IF NOT EXISTS dashboard_summaries (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    summary_json JSONB NOT NULL,
    overall_grade CHAR(1) NOT NULL,
    baseline_status VARCHAR(20) NOT NULL,
    restoration_progress FLOAT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS performance_reports (
    id SERIAL PRIMARY KEY,
    report_id VARCHAR(100) NOT NULL UNIQUE,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    period_days INTEGER NOT NULL,
    report_json JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dashboard_timestamp ON dashboard_summaries(timestamp);
CREATE INDEX IF NOT EXISTS idx_dashboard_grade ON dashboard_summaries(overall_grade);
CREATE INDEX IF NOT EXISTS idx_reports_generated_at ON performance_reports(generated_at);
CREATE INDEX IF NOT EXISTS idx_reports_report_id ON performance_reports(report_id);
"""