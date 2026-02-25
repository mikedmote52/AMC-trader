#!/usr/bin/env python3
"""
NIGHTLY LEARNER — Runs learning engine analysis and applies weight adjustments.
Saves updated weights to data/scanner_weights.json which the scanner reads.

Safety: No single weight changes more than 20% per cycle. All changes logged.
Runs nightly after market close.
"""

import json
import os
import sys
from datetime import date

WORKSPACE = '/Users/mikeclawd/.openclaw/workspace'
WEIGHTS_FILE = os.path.join(WORKSPACE, 'data', 'scanner_weights.json')
LEARNING_LOG = os.path.join(WORKSPACE, 'data', 'learning_log.json')

sys.path.insert(0, os.path.join(WORKSPACE, 'scripts'))

# Default weights (matching V3.3 scanner)
DEFAULT_WEIGHTS = {
    'float': {'ultra_tiny': 60, 'ultra_low': 50, 'very_low': 35, 'low': 20, 'moderate': 10, 'large': 0},
    'momentum': {'perfect': 40, 'early': 30, 'moving': 15, 'late': 5},
    'volume_acceleration': {'strong': 30, 'moderate': 20, 'none': 0},
    'volume_explosive': {'mega': 30, 'explosive': 25, 'major': 20, 'strong': 15, 'spike': 10, 'elevated': 5},
    'catalyst': {'strong_bullish': 30, 'bullish': 20, 'neutral': 10, 'bearish': -10},
    'squeeze': {'extreme': 30, 'high': 25, 'moderate': 20, 'low': 15, 'minimal': 5},
    'squeeze_jackpot_bonus': 15,
    'gap': {'huge': 20, 'big': 15, 'moderate': 10, 'dip': 5},
    'multiday': {'ideal': 20, 'building': 10},
    'vwap': {'above_with_volume': 20, 'above': 10},
    'sector_hot': 15,
    'breakout': 25,
    'vigl': {'perfect': 15, 'near': 10, 'partial': 5},
    'market_cap': {'ideal': 15, 'micro': 10, 'nano': 5},
    'version': '3.3.0',
    'last_updated': None,
    'update_history': []
}


def load_weights():
    """Load current weights or create defaults"""
    if os.path.exists(WEIGHTS_FILE):
        try:
            with open(WEIGHTS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_WEIGHTS.copy()


def save_weights(weights):
    """Save weights with timestamp"""
    weights['last_updated'] = date.today().isoformat()
    os.makedirs(os.path.dirname(WEIGHTS_FILE), exist_ok=True)
    with open(WEIGHTS_FILE, 'w') as f:
        json.dump(weights, f, indent=2)


def analyze_outcomes():
    """
    Analyze which scoring factors correlate with positive outcomes.
    Returns recommended adjustments.
    """
    try:
        from scanner_performance_tracker import analyze_performance, get_factor_performance

        # Get factor-level analysis
        factor_data = get_factor_performance(30)  # Last 30 days
        overall = analyze_performance(30)

        return factor_data, overall
    except Exception as e:
        print(f"⚠️  Could not run analysis: {e}")
        return None, None


def calculate_adjustments(factor_data, current_weights):
    """
    Calculate weight adjustments based on factor performance.
    Rule: No single weight changes more than 20% per cycle.
    """
    if not factor_data:
        return {}

    adjustments = {}
    MAX_CHANGE_PCT = 0.20  # 20% max change per cycle

    # The factor_data structure from scanner_performance_tracker
    # tells us which factors correlated with winners vs losers
    # We increase weights for factors that predict winners
    # and decrease weights for factors that don't

    for factor_name, factor_info in factor_data.items():
        if not isinstance(factor_info, dict):
            continue

        win_rate = factor_info.get('win_rate', 0.5)
        avg_return = factor_info.get('avg_return', 0)
        sample_size = factor_info.get('count', 0)

        # Need minimum sample size to adjust
        if sample_size < 5:
            continue

        # Determine direction: win_rate > 60% = increase, < 40% = decrease
        if win_rate > 0.60 and avg_return > 5:
            direction = min(MAX_CHANGE_PCT, (win_rate - 0.50) * 0.5)  # Scale proportionally
            adjustments[factor_name] = {
                'direction': 'increase',
                'magnitude': direction,
                'reason': f"Win rate {win_rate:.0%}, avg return {avg_return:+.1f}%, n={sample_size}"
            }
        elif win_rate < 0.40 and avg_return < -2:
            direction = min(MAX_CHANGE_PCT, (0.50 - win_rate) * 0.5)
            adjustments[factor_name] = {
                'direction': 'decrease',
                'magnitude': direction,
                'reason': f"Win rate {win_rate:.0%}, avg return {avg_return:+.1f}%, n={sample_size}"
            }

    return adjustments


def apply_adjustments(weights, adjustments):
    """Apply adjustments with 20% cap and logging"""
    changes = []

    for factor, adj in adjustments.items():
        # Find the matching weight category
        if factor in weights and isinstance(weights[factor], dict):
            for tier, value in weights[factor].items():
                if not isinstance(value, (int, float)):
                    continue
                if adj['direction'] == 'increase':
                    new_value = int(value * (1 + adj['magnitude']))
                else:
                    new_value = int(value * (1 - adj['magnitude']))

                # Don't let weights go below 0 or above 100
                new_value = max(0, min(100, new_value))

                if new_value != value:
                    changes.append({
                        'factor': factor,
                        'tier': tier,
                        'old': value,
                        'new': new_value,
                        'reason': adj['reason']
                    })
                    weights[factor][tier] = new_value

    return weights, changes


def run_nightly_learning():
    """Main entry point for nightly learning cycle"""
    print("=" * 60)
    print("🧠 NIGHTLY LEARNER — Weight Calibration")
    print(f"   {date.today().isoformat()}")
    print("=" * 60)

    # Load current weights
    weights = load_weights()
    print(f"\n📊 Current weights version: {weights.get('version', 'unknown')}")
    print(f"   Last updated: {weights.get('last_updated', 'never')}")

    # Analyze outcomes
    print("\n🔬 Analyzing last 30 days of outcomes...")
    factor_data, overall = analyze_outcomes()

    if not factor_data:
        print("\n⚠️  Insufficient data for analysis. Need more completed trades.")
        save_weights(weights)  # Save defaults if first run
        return

    if overall:
        print(f"   Win rate: {overall.get('win_rate', 'N/A')}")
        print(f"   Avg return: {overall.get('avg_return', 'N/A')}")
        print(f"   Total trades: {overall.get('total_trades', 'N/A')}")

    # Calculate adjustments
    print("\n📐 Calculating weight adjustments (20% max per cycle)...")
    adjustments = calculate_adjustments(factor_data, weights)

    if not adjustments:
        print("   No adjustments needed — current weights performing within bounds")
        save_weights(weights)
        return

    # Apply adjustments
    weights, changes = apply_adjustments(weights, adjustments)

    if changes:
        print(f"\n✅ Applied {len(changes)} weight changes:")
        for c in changes:
            print(f"   {c['factor']}.{c['tier']}: {c['old']} → {c['new']} ({c['reason']})")

        # Log changes
        weights['update_history'] = weights.get('update_history', [])
        weights['update_history'].append({
            'date': date.today().isoformat(),
            'changes': changes,
            'overall_win_rate': overall.get('win_rate') if overall else None
        })
        # Keep last 90 days of history
        weights['update_history'] = weights['update_history'][-90:]
    else:
        print("   Adjustments calculated but no changes needed")

    # Save
    save_weights(weights)
    print(f"\n💾 Weights saved to {WEIGHTS_FILE}")
    print("=" * 60)


if __name__ == '__main__':
    run_nightly_learning()
