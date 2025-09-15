"""
AlphaStack 4.0 Audit Framework
Ask-your-system-first approach to understanding stock discovery
"""

from .hooks import (
    snapshot_config,
    coverage_report, 
    explain_filter_stage,
    score_breakdown,
    analyze_etf_leakage,
    scoring_variance_analysis,
    quick_health_check
)

from .run_audit import run_comprehensive_audit, print_audit_summary

__version__ = "1.0.0"
__all__ = [
    "snapshot_config",
    "coverage_report", 
    "explain_filter_stage",
    "score_breakdown",
    "analyze_etf_leakage", 
    "scoring_variance_analysis",
    "quick_health_check",
    "run_comprehensive_audit",
    "print_audit_summary"
]