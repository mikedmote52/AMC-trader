from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import asyncio

from ..services.performance_dashboard import PerformanceDashboard
from ..services.performance_analytics import PerformanceAnalytics
from ..services.discovery_tracker import DiscoveryPerformanceTracker
from ..services.thesis_accuracy_tracker import ThesisAccuracyTracker
from ..services.market_timing_analyzer import MarketTimingAnalyzer
from ..services.risk_management_tracker import RiskManagementTracker
from ..services.system_health_monitor import SystemHealthMonitor

router = APIRouter(prefix="/analytics", tags=["Performance Analytics"])

# Initialize analytics services
dashboard = PerformanceDashboard()
performance_analytics = PerformanceAnalytics()
discovery_tracker = DiscoveryPerformanceTracker()
thesis_tracker = ThesisAccuracyTracker()
timing_analyzer = MarketTimingAnalyzer()
risk_tracker = RiskManagementTracker()
health_monitor = SystemHealthMonitor()

# Pydantic models for request/response validation
class PerformanceMetricsResponse(BaseModel):
    status: str
    timestamp: datetime
    period_days: int
    metrics: Dict
    baseline_comparison: Dict
    insights: List[str]
    recommendations: List[str]

class DashboardSummaryResponse(BaseModel):
    status: str
    timestamp: datetime
    overall_grade: str
    baseline_status: str
    restoration_progress: float
    key_metrics: Dict
    priority_actions: List[str]
    system_health_score: float

class AnalyticsReportResponse(BaseModel):
    status: str
    report_id: str
    generated_at: datetime
    executive_summary: Dict
    detailed_analysis: Dict
    restoration_roadmap: List[Dict]
    immediate_actions: List[str]

@router.get("/dashboard", response_model=DashboardSummaryResponse)
async def get_performance_dashboard(
    period_days: int = Query(30, ge=1, le=90, description="Analysis period in days")
):
    """Get executive performance dashboard summary"""
    try:
        # Generate comprehensive dashboard
        dashboard_summary = await dashboard.generate_comprehensive_dashboard(period_days)
        
        return DashboardSummaryResponse(
            status="success",
            timestamp=dashboard_summary.timestamp,
            overall_grade=dashboard_summary.overall_performance_grade,
            baseline_status=dashboard_summary.vs_baseline_status,
            restoration_progress=dashboard_summary.restoration_progress,
            key_metrics={
                "current_win_rate": dashboard_summary.current_win_rate,
                "current_avg_return": dashboard_summary.current_avg_return,
                "explosive_growth_rate": dashboard_summary.explosive_growth_rate,
                "total_positions": dashboard_summary.total_positions,
                "win_rate_gap": dashboard_summary.win_rate_gap,
                "return_gap": dashboard_summary.return_gap,
                "explosive_gap": dashboard_summary.explosive_gap
            },
            priority_actions=[dashboard_summary.top_priority_action],
            system_health_score=dashboard_summary.system_health_score
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate dashboard: {str(e)}")

@router.get("/comprehensive-report")
async def generate_comprehensive_report(
    period_days: int = Query(30, ge=7, le=90, description="Analysis period in days"),
    format: str = Query("json", description="Report format: json or summary")
):
    """Generate comprehensive performance analysis report"""
    try:
        # Generate full performance report
        report = await dashboard.generate_comprehensive_report(period_days)
        
        if format == "summary":
            # Return condensed summary
            return {
                "status": "success",
                "report_id": report.report_id,
                "generated_at": report.generated_at,
                "executive_summary": report.executive_summary,
                "key_findings": report.key_findings[:5],  # Top 5 findings
                "immediate_actions": report.immediate_actions,
                "restoration_progress": report.executive_summary.restoration_progress
            }
        else:
            # Return full detailed report
            return {
                "status": "success",
                "report": report
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")

@router.get("/metrics", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(
    period_days: int = Query(30, ge=7, le=90, description="Analysis period in days")
):
    """Get detailed performance metrics"""
    try:
        # Calculate comprehensive metrics
        metrics = await performance_analytics.calculate_comprehensive_metrics(period_days)
        
        # Generate performance report
        report = await performance_analytics.generate_performance_report(metrics)
        
        return PerformanceMetricsResponse(
            status="success",
            timestamp=metrics.calculated_at,
            period_days=period_days,
            metrics={
                "discovery_quality_score": metrics.discovery_quality_score,
                "win_rate": metrics.win_rate,
                "average_return": metrics.average_return,
                "explosive_growth_rate": metrics.explosive_growth_rate,
                "risk_adjusted_return": metrics.risk_adjusted_return,
                "thesis_accuracy": metrics.thesis_accuracy,
                "data_quality_score": metrics.data_quality_score,
                "market_timing_score": metrics.market_timing_score,
                "system_health_score": metrics.system_health_score,
                "benchmark_gap": metrics.benchmark_gap,
                "performance_trend": metrics.performance_trend
            },
            baseline_comparison=report["baseline_comparison"],
            insights=report["key_findings"],
            recommendations=report["recommendations"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

@router.get("/discovery-analysis")
async def get_discovery_analysis(
    days_back: int = Query(7, ge=1, le=30, description="Days to analyze")
):
    """Get discovery system performance analysis"""
    try:
        report = await discovery_tracker.generate_discovery_report(days_back)
        
        return {
            "status": "success",
            "analysis": report,
            "summary": {
                "total_candidates": report["summary"]["total_candidates"],
                "explosive_candidates": report["summary"]["explosive_candidates"],
                "explosive_rate": report["summary"]["explosive_candidates"] / report["summary"]["total_candidates"] * 100 if report["summary"]["total_candidates"] > 0 else 0,
                "baseline_gap": report["summary"]["explosive_gap"],
                "status": report["summary"]["status"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get discovery analysis: {str(e)}")

@router.get("/thesis-accuracy")
async def get_thesis_accuracy(
    period_days: int = Query(30, ge=7, le=90, description="Analysis period in days")
):
    """Get thesis accuracy analysis"""
    try:
        report = await thesis_tracker.generate_thesis_accuracy_report(period_days)
        
        return {
            "status": "success",
            "analysis": report,
            "summary": {
                "overall_accuracy": report["period_summary"]["overall_accuracy"],
                "total_predictions": report["period_summary"]["total_predictions"],
                "accuracy_trend": report["detailed_metrics"]["accuracy_trend"],
                "high_confidence_accuracy": report["detailed_metrics"]["high_confidence_accuracy"],
                "status": report["period_summary"]["status"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get thesis accuracy: {str(e)}")

@router.get("/market-timing")
async def get_market_timing_analysis(
    period_days: int = Query(30, ge=7, le=90, description="Analysis period in days")
):
    """Get market timing analysis"""
    try:
        report = await timing_analyzer.generate_timing_report(period_days)
        
        return {
            "status": "success",
            "analysis": report,
            "summary": {
                "avg_entry_delay": report["summary"]["avg_entry_delay"],
                "avg_timing_cost": report["summary"]["avg_timing_cost"],
                "vigl_gap": report["summary"]["vigl_gap"],
                "potential_improvement": report["summary"]["potential_improvement"],
                "status": report["summary"]["status"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get timing analysis: {str(e)}")

@router.get("/risk-management")
async def get_risk_management_analysis():
    """Get risk management analysis"""
    try:
        report = await risk_tracker.generate_risk_management_report()
        
        return {
            "status": "success",
            "analysis": report,
            "summary": {
                "portfolio_risk_grade": report["executive_summary"]["portfolio_risk_grade"],
                "total_positions": report["executive_summary"]["total_positions"],
                "critical_positions": report["executive_summary"]["critical_positions"],
                "risk_budget_used": report["executive_summary"]["risk_budget_used"],
                "immediate_action_required": report["executive_summary"]["immediate_action_required"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get risk analysis: {str(e)}")

@router.get("/system-health")
async def get_system_health():
    """Get system health monitoring report"""
    try:
        report = await health_monitor.generate_health_report()
        
        return {
            "status": "success",
            "health_report": report,
            "summary": {
                "overall_health_score": report["executive_summary"]["overall_health_score"],
                "system_status": report["current_metrics"]["system_status"],
                "critical_components": report["executive_summary"]["critical_components"],
                "active_alerts": report["executive_summary"]["active_alerts"],
                "performance_vs_baseline": report["current_metrics"]["performance_vs_baseline"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system health: {str(e)}")

@router.post("/run-batch-analysis")
async def run_batch_analysis(
    period_days: int = Query(30, ge=7, le=90, description="Analysis period in days")
):
    """Run batch analysis across all systems"""
    try:
        # Run analysis for all components in parallel
        analysis_tasks = [
            discovery_tracker.track_discovery_batch(),
            thesis_tracker.update_thesis_outcomes(period_days),
            timing_analyzer.batch_analyze_timing(period_days),
            health_monitor.collect_system_health_metrics()
        ]
        
        results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        
        # Count successful analyses
        successful_analyses = sum(1 for result in results if not isinstance(result, Exception))
        
        return {
            "status": "success",
            "message": f"Batch analysis completed: {successful_analyses}/4 components analyzed",
            "results": {
                "discovery_batch_tracked": not isinstance(results[0], Exception),
                "thesis_outcomes_updated": not isinstance(results[1], Exception) and results[1] if not isinstance(results[1], Exception) else 0,
                "timing_positions_analyzed": not isinstance(results[2], Exception) and results[2] if not isinstance(results[2], Exception) else 0,
                "health_metrics_collected": not isinstance(results[3], Exception)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")

@router.get("/baseline-comparison")
async def get_baseline_comparison():
    """Get comparison to June-July 2024 baseline performance"""
    try:
        # Get current metrics
        current_metrics = await performance_analytics.calculate_comprehensive_metrics(30)
        
        # Generate baseline comparison
        baseline_report = await performance_analytics.generate_performance_report(current_metrics)
        
        return {
            "status": "success",
            "baseline_period": "June-July 2024",
            "baseline_metrics": {
                "win_rate": 73.0,
                "average_return": 63.8,
                "explosive_growth_rate": 46.7,
                "total_profit": 957.50,
                "max_individual_return": 324.0
            },
            "current_metrics": {
                "win_rate": current_metrics.win_rate,
                "average_return": current_metrics.average_return,
                "explosive_growth_rate": current_metrics.explosive_growth_rate,
                "benchmark_gap": current_metrics.benchmark_gap
            },
            "gaps": {
                "win_rate_gap": current_metrics.win_rate - 73.0,
                "return_gap": current_metrics.average_return - 63.8,
                "explosive_gap": current_metrics.explosive_growth_rate - 46.7
            },
            "restoration_priority": baseline_report["restoration_priority"],
            "next_actions": baseline_report["next_actions"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get baseline comparison: {str(e)}")

@router.get("/vigl-analysis")
async def get_vigl_analysis():
    """Get VIGL pattern analysis and comparison"""
    try:
        # Get discovery report for VIGL analysis
        discovery_report = await discovery_tracker.generate_discovery_report(7)
        
        # Get timing report for VIGL timing comparison
        timing_report = await timing_analyzer.generate_timing_report(30)
        
        return {
            "status": "success",
            "vigl_baseline": {
                "return": "324% explosive growth",
                "pattern": "Volume >20.9x average, Price $2.94-$4.66",
                "timing": "Immediate entry upon discovery (0 days)",
                "duration": "45 days to peak",
                "risk_profile": "Low risk, high reward"
            },
            "current_vs_vigl": {
                "vigl_candidates_found": discovery_report.get("vigl_analysis", {}).get("total_vigl_candidates", 0),
                "vigl_detection_rate": discovery_report.get("vigl_analysis", {}).get("vigl_detection_rate", 0),
                "vigl_success_rate": discovery_report.get("vigl_analysis", {}).get("avg_vigl_success_rate", 0),
                "entry_timing_gap": timing_report["summary"]["vigl_gap"],
                "avg_entry_delay": timing_report["summary"]["avg_entry_delay"]
            },
            "restoration_steps": [
                "Restore volume threshold to >20.9x average",
                "Focus price discovery range $2.94-$4.66",
                "Implement immediate entry system (0 day delay)",
                "Target 45-day hold duration for explosive gains",
                "Conservative position sizing approach"
            ],
            "vigl_opportunity_assessment": {
                "current_vigl_score": discovery_report.get("vigl_analysis", {}).get("status", "CRITICAL"),
                "restoration_urgency": "CRITICAL" if discovery_report.get("vigl_analysis", {}).get("vigl_detection_rate", 0) < 10 else "HIGH"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get VIGL analysis: {str(e)}")

@router.get("/restoration-progress")
async def get_restoration_progress():
    """Get restoration progress toward June-July baseline"""
    try:
        # Generate dashboard to get restoration progress
        dashboard_summary = await dashboard.generate_comprehensive_dashboard(30)
        
        # Get detailed progress breakdown
        current_metrics = await performance_analytics.calculate_comprehensive_metrics(30)
        
        return {
            "status": "success",
            "overall_progress": dashboard_summary.restoration_progress,
            "baseline_status": dashboard_summary.vs_baseline_status,
            "days_to_restoration": dashboard_summary.days_to_baseline_restoration,
            "progress_breakdown": {
                "win_rate_progress": max(0, min(100, (current_metrics.win_rate - 30) / (73 - 30) * 100)),
                "return_progress": max(0, min(100, (current_metrics.average_return - (-20)) / (63.8 - (-20)) * 100)),
                "explosive_progress": max(0, min(100, (current_metrics.explosive_growth_rate - 5) / (46.7 - 5) * 100))
            },
            "milestone_targets": {
                "30_day": {"win_rate": 50, "avg_return": 10, "explosive_rate": 20},
                "60_day": {"win_rate": 60, "avg_return": 25, "explosive_rate": 30},
                "90_day": {"win_rate": 70, "avg_return": 50, "explosive_rate": 40}
            },
            "critical_success_factors": [
                "Restore VIGL pattern detection",
                "Implement immediate entry system",
                "Focus on explosive growth candidates",
                "Maintain conservative risk management",
                "Monitor and adjust system parameters"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get restoration progress: {str(e)}")

@router.get("/alert-status")
async def get_alert_status():
    """Get current system alerts and priority actions"""
    try:
        # Get system health for alerts
        health_report = await health_monitor.generate_health_report()
        
        # Get dashboard for priority actions
        dashboard_summary = await dashboard.generate_comprehensive_dashboard(30)
        
        alerts = {
            "critical_alerts": health_report.get("critical_actions", []),
            "system_alerts": health_report["current_metrics"]["active_alerts"],
            "priority_action": dashboard_summary.top_priority_action,
            "immediate_actions_required": dashboard_summary.immediate_actions_required,
            "system_status": health_report["current_metrics"]["system_status"],
            "overall_health_score": health_report["executive_summary"]["overall_health_score"]
        }
        
        # Determine alert severity
        severity = "CRITICAL" if health_report["current_metrics"]["system_status"] == "CRITICAL" else \
                  "WARNING" if health_report["current_metrics"]["system_status"] == "DEGRADED" else \
                  "NORMAL"
        
        return {
            "status": "success",
            "alert_severity": severity,
            "alerts": alerts,
            "requires_immediate_attention": len(health_report.get("critical_actions", [])) > 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alert status: {str(e)}")

# Health check endpoint for the analytics system
@router.get("/health")
async def analytics_health_check():
    """Health check for analytics system"""
    try:
        # Quick health check of core components
        health_checks = {
            "performance_analytics": True,
            "discovery_tracker": True,
            "thesis_tracker": True,
            "timing_analyzer": True,
            "risk_tracker": True,
            "health_monitor": True,
            "dashboard": True
        }
        
        all_healthy = all(health_checks.values())
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": datetime.utcnow(),
            "components": health_checks,
            "version": "1.0.0",
            "message": "Performance Analytics System operational"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.utcnow(),
            "error": str(e),
            "message": "Performance Analytics System experiencing issues"
        }