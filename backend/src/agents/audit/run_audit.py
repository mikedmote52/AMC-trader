#!/usr/bin/env python3
"""
AlphaStack 4.0 Audit Runner - One command to see exactly how the system finds stocks
"""
import json
import time
import asyncio
import sys
import os
from datetime import datetime
from typing import Dict, List, Any

# Add agents to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from audit.hooks import (
    snapshot_config, coverage_report, explain_filter_stage, 
    score_breakdown, analyze_etf_leakage, scoring_variance_analysis, 
    quick_health_check
)

async def run_comprehensive_audit(limit: int = 25) -> Dict[str, Any]:
    """Run comprehensive audit of the AlphaStack discovery system"""
    
    print("🔍 Starting AlphaStack 4.0 Comprehensive Audit...")
    print("=" * 80)
    
    start_time = time.time()
    audit_report = {
        "audit_meta": {
            "timestamp": datetime.now().isoformat(),
            "system_version": "alphastack_v4_corrected",
            "audit_version": "1.0"
        }
    }
    
    try:
        # Import and setup systems
        from alphastack_v4 import create_discovery_system
        from alphastack_v4_corrected import CorrectedFilteringPipeline, CorrectedScoringEngine
        
        print("📊 Initializing discovery system...")
        discovery = create_discovery_system()
        
        # Replace with corrected components
        corrected_filter = CorrectedFilteringPipeline() 
        corrected_scorer = CorrectedScoringEngine()
        discovery.filtering_pipeline = corrected_filter
        discovery.scoring_engine = corrected_scorer
        
        # 1. Configuration Snapshot
        print("🎛️  Capturing configuration snapshot...")
        audit_report["config"] = snapshot_config(discovery)
        
        # 2. Get Universe and Apply Filters Step-by-Step
        print("📡 Getting universe from Polygon...")
        universe = await discovery.data_hub.price_provider.get_universe()
        print(f"   Raw universe: {len(universe):,} stocks")
        
        audit_report["stage_1_universe"] = {
            "input_count": len(universe),
            "output_count": len(universe),
            "stage_name": "Universe Acquisition"
        }
        
        # 3. Technical Enrichment
        print("🧮 Enriching with technical indicators...")
        enriched = []
        sample_size = min(100, len(universe))  # Sample for speed in audit
        for snap in universe[:sample_size]:
            enriched_snap = await discovery.data_hub.enrich_snapshot(snap)
            enriched.append(enriched_snap)
        
        print(f"   Enriched sample: {len(enriched)} stocks")
        audit_report["stage_2_enrichment"] = {
            "input_count": len(universe),
            "output_count": len(enriched),
            "stage_name": "Technical Enrichment",
            "sample_note": f"Using sample of {sample_size} for audit speed"
        }
        
        # 4. Coverage Analysis
        print("📋 Analyzing feature coverage...")
        audit_report["coverage"] = coverage_report(enriched)
        
        # 5. Step-by-step Filter Analysis
        print("🔧 Analyzing filtration pipeline...")
        
        current_stocks = enriched
        filter_stages = []
        
        # ETF Exclusion
        before_etf = current_stocks
        after_etf = corrected_filter._apply_etf_exclusion(current_stocks)
        stage_analysis = explain_filter_stage(before_etf, after_etf, "ETF Exclusion")
        filter_stages.append(stage_analysis)
        current_stocks = after_etf
        
        # Basic Filters
        before_basic = current_stocks
        after_basic = corrected_filter._apply_basic_filters(current_stocks)
        stage_analysis = explain_filter_stage(before_basic, after_basic, "Basic Filters")
        filter_stages.append(stage_analysis)
        current_stocks = after_basic
        
        # Liquidity Filters
        before_liquidity = current_stocks
        after_liquidity = corrected_filter._apply_liquidity_filter(current_stocks)
        stage_analysis = explain_filter_stage(before_liquidity, after_liquidity, "Liquidity Filters")
        filter_stages.append(stage_analysis)
        current_stocks = after_liquidity
        
        # Microstructure Filters
        before_micro = current_stocks
        after_micro = corrected_filter._apply_microstructure_filter(current_stocks)
        stage_analysis = explain_filter_stage(before_micro, after_micro, "Microstructure Filters")
        filter_stages.append(stage_analysis)
        current_stocks = after_micro
        
        # RelVol Filters
        before_relvol = current_stocks
        after_relvol = corrected_filter._apply_relvol_filter(current_stocks)
        stage_analysis = explain_filter_stage(before_relvol, after_relvol, "RelVol Filters")
        filter_stages.append(stage_analysis)
        current_stocks = after_relvol
        
        # VWAP Filters
        before_vwap = current_stocks
        after_vwap = corrected_filter._apply_vwap_filter(current_stocks)
        stage_analysis = explain_filter_stage(before_vwap, after_vwap, "VWAP Filters")
        filter_stages.append(stage_analysis)
        current_stocks = after_vwap
        
        # Squeeze Filters
        before_squeeze = current_stocks
        after_squeeze = corrected_filter._apply_squeeze_filter(current_stocks)
        stage_analysis = explain_filter_stage(before_squeeze, after_squeeze, "Squeeze Filters")
        filter_stages.append(stage_analysis)
        current_stocks = after_squeeze
        
        audit_report["filter_stages"] = filter_stages
        
        # 6. Scoring Analysis
        print("🎯 Analyzing scoring system...")
        if current_stocks:
            scored_candidates = corrected_scorer.score_candidates(current_stocks)
            
            # Convert to candidate dictionaries for analysis
            candidates_for_analysis = []
            for score_obj in scored_candidates[:limit]:
                candidate_dict = {
                    'symbol': score_obj.symbol,
                    'total_score': score_obj.total_score,
                    'volume_momentum_score': score_obj.volume_momentum_score,
                    'squeeze_score': score_obj.squeeze_score,
                    'catalyst_score': score_obj.catalyst_score,
                    'sentiment_score': score_obj.sentiment_score,
                    'options_score': score_obj.options_score,
                    'technical_score': score_obj.technical_score,
                    'confidence': score_obj.confidence,
                    'action_tag': score_obj.action_tag,
                    'snapshot': score_obj.snapshot
                }
                candidates_for_analysis.append(candidate_dict)
            
            # Detailed scoring breakdown for top candidates
            audit_report["scoring_breakdown"] = [
                score_breakdown(candidate) for candidate in candidates_for_analysis[:10]
            ]
            
            # Scoring variance analysis
            audit_report["scoring_analysis"] = scoring_variance_analysis(candidates_for_analysis)
            
            # ETF leakage analysis
            audit_report["etf_analysis"] = analyze_etf_leakage(candidates_for_analysis)
            
            print(f"   Scored candidates: {len(scored_candidates)}")
            print(f"   Top {limit} selected for analysis")
        
        else:
            print("   ⚠️ No stocks survived filtration!")
            audit_report["scoring_breakdown"] = []
            audit_report["scoring_analysis"] = {"note": "No candidates to score"}
            audit_report["etf_analysis"] = {"note": "No candidates to analyze"}
        
        # 7. Health Check
        print("🏥 Running health check...")
        audit_report["health_check"] = quick_health_check(audit_report)
        
        # 8. Full System Comparison
        print("🔄 Running full system for comparison...")
        full_results = await discovery.discover_candidates(limit=limit)
        audit_report["full_system_results"] = {
            "execution_time_sec": full_results['execution_time_sec'],
            "pipeline_stats": full_results['pipeline_stats'],
            "candidate_count": len(full_results['candidates']),
            "top_symbols": [c['symbol'] for c in full_results['candidates'][:10]]
        }
        
        execution_time = time.time() - start_time
        audit_report["audit_meta"]["execution_time_sec"] = round(execution_time, 2)
        
        await discovery.close()
        
        print(f"✅ Audit complete in {execution_time:.2f} seconds")
        return audit_report
        
    except Exception as e:
        print(f"❌ Audit failed: {e}")
        import traceback
        traceback.print_exc()
        
        audit_report["error"] = {
            "message": str(e),
            "type": type(e).__name__
        }
        return audit_report

def print_audit_summary(audit_report: Dict[str, Any]):
    """Print a human-readable summary of the audit results"""
    
    print("\n" + "=" * 100)
    print("📊 ALPHASTACK 4.0 AUDIT SUMMARY")
    print("=" * 100)
    
    # Configuration
    config = audit_report.get("config", {})
    print(f"🎛️  Configuration:")
    print(f"   Price Range: ${config.get('price_bounds', {}).get('min', 'N/A')} - ${config.get('price_bounds', {}).get('max', 'N/A')}")
    print(f"   Min Dollar Volume: ${config.get('min_dollar_vol_m', 'N/A')}M")
    print(f"   ETF Patterns: {config.get('etf_exclusion', {}).get('pattern_count', 'N/A')} patterns, {config.get('etf_exclusion', {}).get('symbol_count', 'N/A')} symbols")
    
    # Coverage
    coverage = audit_report.get("coverage", {})
    print(f"\n📋 Feature Coverage:")
    for feature, pct in coverage.get("feature_coverage_pct", {}).items():
        status = "✅" if pct >= 90 else "⚠️" if pct >= 70 else "❌"
        print(f"   {status} {feature}: {pct}%")
    
    # Filter Stages
    print(f"\n🔧 Filter Pipeline:")
    for stage in audit_report.get("filter_stages", []):
        removed = stage.get("removed_count", 0)
        rate = stage.get("removal_rate_pct", 0)
        print(f"   {stage.get('stage_name', 'Unknown')}: {stage.get('input_count', 0)} → {stage.get('output_count', 0)} ({removed} removed, {rate}%)")
    
    # ETF Analysis
    etf_analysis = audit_report.get("etf_analysis", {})
    etf_count = etf_analysis.get("etf_leakage_count", 0)
    print(f"\n🚫 ETF Leakage Analysis:")
    if etf_count > 0:
        print(f"   ❌ {etf_count} potential ETFs found in results:")
        for etf in etf_analysis.get("leaked_etfs", [])[:5]:
            print(f"      • {etf.get('symbol', 'N/A')} (Score: {etf.get('score', 'N/A')})")
    else:
        print(f"   ✅ No ETF leakage detected")
    
    # Scoring Analysis
    scoring = audit_report.get("scoring_analysis", {})
    print(f"\n🎯 Scoring Analysis:")
    print(f"   Variance: {scoring.get('variance', 'N/A')} ({'Good' if scoring.get('variance', 0) > 5 else 'Poor differentiation'})")
    print(f"   Unique Scores: {scoring.get('unique_scores', 'N/A')}/{scoring.get('total_candidates', 'N/A')}")
    print(f"   Score Range: {scoring.get('min_score', 'N/A')} - {scoring.get('max_score', 'N/A')}")
    
    # Health Check
    health = audit_report.get("health_check", {})
    status = health.get("health_status", "UNKNOWN")
    print(f"\n🏥 Health Check: {status}")
    
    for issue in health.get("critical_issues", []):
        print(f"   ❌ {issue}")
    
    for warning in health.get("warnings", []):
        print(f"   ⚠️ {warning}")
    
    if health.get("recommendations"):
        print(f"\n💡 Recommendations:")
        for rec in health.get("recommendations", []):
            print(f"   • {rec}")
    
    print("\n" + "=" * 100)

async def main():
    """Main audit runner"""
    
    # Run the audit
    audit_report = await run_comprehensive_audit(limit=25)
    
    # Print summary to console
    print_audit_summary(audit_report)
    
    # Save detailed report to file
    output_file = f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(audit_report, f, indent=2, default=str)
    
    print(f"\n📄 Detailed audit report saved to: {output_file}")
    
    return audit_report

if __name__ == "__main__":
    result = asyncio.run(main())