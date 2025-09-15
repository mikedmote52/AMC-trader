#!/usr/bin/env python3
"""
AlphaStack 4.0 Audit Hooks - See exactly how the system finds stocks
"""
import statistics
from collections import Counter
from typing import Dict, List, Any, Tuple

def snapshot_config(discovery_system) -> Dict[str, Any]:
    """Snapshot the brain - what thresholds is the system actually using?"""
    
    # Extract config from the discovery system
    config = discovery_system.data_hub.price_provider.config
    
    return {
        "version": "alphastack_v4_corrected",
        "price_bounds": {
            "min": config.price_min,
            "max": config.price_max
        },
        "min_dollar_vol_m": config.min_dollar_vol_m,
        "volume_thresholds": {
            "basic_filter": 250000,  # From corrected system
            "liquidity_filter": 5000000,  # $5M dollar volume
            "relvol_filter": 100000,  # From corrected system
        },
        "relvol_rules": {
            "min_surge": 1.2,  # From corrected system
        },
        "vwap_rules": {
            "allowed_below_pct": 2,  # 2% below VWAP allowed
        },
        "etf_exclusion": {
            "pattern_count": len(discovery_system.filtering_pipeline.ETF_PATTERNS),
            "symbol_count": len(discovery_system.filtering_pipeline.ETF_SYMBOLS),
        },
        "scoring_weights": {
            "volume_momentum": 0.25,
            "squeeze": 0.20,
            "catalyst": 0.15,
            "sentiment": 0.15,
            "options": 0.12,
            "technical": 0.13
        }
    }

def coverage_report(enriched_snapshots: List) -> Dict[str, Any]:
    """Coverage report - what data do we actually have?"""
    
    if not enriched_snapshots:
        return {"feature_coverage_pct": {}, "total_stocks": 0}
    
    # Key features we expect
    features = ["rsi", "vwap", "atr_pct", "rel_vol_30d", "volume", "shares_outstanding"]
    
    coverage = {}
    total = len(enriched_snapshots)
    
    for feature in features:
        count_with_feature = 0
        for snap in enriched_snapshots:
            value = getattr(snap, feature, None)
            if value is not None and value != 0:
                count_with_feature += 1
        
        coverage[feature] = round(100 * count_with_feature / total, 1)
    
    # Special checks
    price_coverage = sum(1 for snap in enriched_snapshots if snap.price > 0)
    coverage["price"] = round(100 * price_coverage / total, 1)
    
    return {
        "feature_coverage_pct": coverage,
        "total_stocks": total,
        "samples_checked": min(10, total),
        "sample_data": [
            {
                "symbol": snap.symbol,
                "price": float(snap.price),
                "has_rsi": getattr(snap, 'rsi', None) is not None,
                "has_vwap": getattr(snap, 'vwap', None) is not None,
                "has_relvol": getattr(snap, 'rel_vol_30d', None) is not None,
            }
            for snap in enriched_snapshots[:10]
        ]
    }

def explain_filter_stage(before_stocks: List, after_stocks: List, stage_name: str) -> Dict[str, Any]:
    """Explain what happened in a filter stage"""
    
    before_symbols = {getattr(stock, 'symbol', str(stock)) for stock in before_stocks}
    after_symbols = {getattr(stock, 'symbol', str(stock)) for stock in after_stocks}
    
    removed_symbols = before_symbols - after_symbols
    
    return {
        "stage_name": stage_name,
        "input_count": len(before_stocks),
        "output_count": len(after_stocks),
        "removed_count": len(removed_symbols),
        "removal_rate_pct": round(100 * len(removed_symbols) / len(before_stocks), 1) if before_stocks else 0,
        "removed_samples": sorted(list(removed_symbols))[:20],  # First 20 removed
        "passed_samples": sorted(list(after_symbols))[:20]      # First 20 that passed
    }

def score_breakdown(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Show the exact math behind a candidate's score"""
    
    components = {
        "volume_momentum": candidate.get('volume_momentum_score', 0),
        "squeeze": candidate.get('squeeze_score', 0),
        "catalyst": candidate.get('catalyst_score', 0),
        "sentiment": candidate.get('sentiment_score', 0),
        "options": candidate.get('options_score', 0),
        "technical": candidate.get('technical_score', 0)
    }
    
    weights = {
        "volume_momentum": 0.25,
        "squeeze": 0.20,
        "catalyst": 0.15,
        "sentiment": 0.15,
        "options": 0.12,
        "technical": 0.13
    }
    
    # Calculate weighted components
    weighted_parts = {k: components[k] * weights[k] for k in components}
    raw_score = sum(weighted_parts.values())
    final_score = candidate.get('total_score', raw_score * 100)
    
    return {
        "symbol": candidate['symbol'],
        "raw_components": components,
        "weights": weights,
        "weighted_parts": weighted_parts,
        "raw_sum": round(raw_score, 4),
        "final_score": round(final_score, 2),
        "confidence": candidate.get('confidence', 0),
        "action_tag": candidate.get('action_tag', 'unknown')
    }

def analyze_etf_leakage(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Check for ETFs that leaked through the filters"""
    
    # Known ETF patterns
    etf_patterns = ['ETF', 'SPDR', 'ISHARES', 'VANGUARD', 'DIREXION']
    common_etfs = ['SPY', 'QQQ', 'KRE', 'XRT', 'XBI', 'EMB', 'TMF', 'SDS', 'IWM']
    
    potential_etfs = []
    
    for candidate in candidates:
        symbol = candidate['symbol']
        
        # Check if symbol matches known ETF patterns
        is_likely_etf = False
        reasons = []
        
        if symbol in common_etfs:
            is_likely_etf = True
            reasons.append(f"Known ETF symbol: {symbol}")
        
        for pattern in etf_patterns:
            if pattern in symbol.upper():
                is_likely_etf = True
                reasons.append(f"Contains ETF pattern: {pattern}")
        
        # Check for 3-letter symbols (often ETFs)
        if len(symbol) == 3 and symbol.isupper():
            reasons.append(f"3-letter symbol pattern: {symbol}")
        
        if is_likely_etf:
            potential_etfs.append({
                "symbol": symbol,
                "score": candidate.get('total_score', 0),
                "reasons": reasons,
                "price": getattr(candidate.get('snapshot'), 'price', 'N/A') if candidate.get('snapshot') else 'N/A'
            })
    
    return {
        "etf_leakage_count": len(potential_etfs),
        "total_candidates": len(candidates),
        "etf_leakage_pct": round(100 * len(potential_etfs) / len(candidates), 1) if candidates else 0,
        "leaked_etfs": potential_etfs
    }

def scoring_variance_analysis(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze score distribution to detect identical scoring issues"""
    
    if not candidates:
        return {"variance": 0, "unique_scores": 0, "score_distribution": {}}
    
    scores = [candidate.get('total_score', 0) for candidate in candidates]
    
    # Calculate variance
    variance = statistics.pvariance(scores) if len(scores) > 1 else 0
    
    # Count unique scores
    unique_scores = len(set(scores))
    
    # Score distribution
    score_counts = Counter(scores)
    distribution = [{"score": score, "count": count} for score, count in score_counts.most_common()]
    
    return {
        "variance": round(variance, 3),
        "unique_scores": unique_scores,
        "total_candidates": len(candidates),
        "min_score": min(scores),
        "max_score": max(scores),
        "avg_score": round(statistics.mean(scores), 2),
        "identical_score_issue": unique_scores == 1 and len(candidates) > 1,
        "score_distribution": distribution[:10]  # Top 10 most common scores
    }

def quick_health_check(audit_report: Dict[str, Any]) -> Dict[str, Any]:
    """Quick health check based on audit results"""
    
    issues = []
    warnings = []
    
    # Check ETF leakage
    etf_leakage = audit_report.get('etf_analysis', {}).get('etf_leakage_count', 0)
    if etf_leakage > 0:
        issues.append(f"ETF leakage: {etf_leakage} ETFs found in results")
    
    # Check score variance
    variance = audit_report.get('scoring_analysis', {}).get('variance', 0)
    if variance < 5:
        issues.append(f"Low score variance: {variance} (should be >5)")
    
    # Check identical scores
    if audit_report.get('scoring_analysis', {}).get('identical_score_issue', False):
        issues.append("All candidates have identical scores")
    
    # Check feature coverage
    coverage = audit_report.get('coverage', {}).get('feature_coverage_pct', {})
    for feature, pct in coverage.items():
        if pct < 90:
            warnings.append(f"Low {feature} coverage: {pct}%")
    
    return {
        "health_status": "NEEDS_ATTENTION" if issues else ("WARNING" if warnings else "GOOD"),
        "critical_issues": issues,
        "warnings": warnings,
        "recommendations": _generate_recommendations(issues, warnings)
    }

def _generate_recommendations(issues: List[str], warnings: List[str]) -> List[str]:
    """Generate specific recommendations based on issues found"""
    
    recs = []
    
    for issue in issues:
        if "ETF leakage" in issue:
            recs.append("Strengthen ETF exclusion filter - add more patterns or use name-based filtering")
        if "score variance" in issue or "identical scores" in issue:
            recs.append("Fix scoring engine - ensure real data differentiation, not proxy values")
    
    for warning in warnings:
        if "coverage" in warning:
            recs.append(f"Improve data enrichment for {warning.split()[1]} feature")
    
    return recs