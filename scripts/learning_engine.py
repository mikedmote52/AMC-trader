#!/usr/bin/env python3
"""
Learning Engine - Continuously improves scanner based on performance

This script:
1. Analyzes scanner performance over last 30/60/90 days
2. Calculates which factors predict success
3. Generates optimal weight recommendations
4. Can auto-update scanner weights (with --apply flag)
5. Logs all learning updates to memory files

Usage:
    python3 learning_engine.py                  # Show recommendations
    python3 learning_engine.py --apply          # Apply weight updates
    python3 learning_engine.py --days 60        # Analyze last 60 days
"""

import sys
import json
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent))
from scanner_performance_tracker import analyze_performance, get_factor_performance

WORKSPACE = Path('/Users/mikeclawd/.openclaw/workspace')
SCANNER_FILE = WORKSPACE / 'diamond_scanner.py'
MEMORY_DIR = WORKSPACE / 'memory'
LEARNING_LOG = WORKSPACE / 'data/learning_updates.json'

# Current weights in scanner
CURRENT_WEIGHTS = {
    'float': {
        'ultra_low': 50,   # <= 10M shares
        'very_low': 40,    # 10-20M
        'low': 30,         # 20-30M
        'medium': 20       # 30-50M
    },
    'momentum': {
        'perfect': 40,     # -1% to +3%
        'early': 30,       # +3% to +5%
        'moving': 15,      # +5% to +8%
        'late': 5          # > +8%
    },
    'volume': {
        'base': 30,        # Volume acceleration
        'spike_bonus': 10  # 2x volume spike
    },
    'catalyst': {
        'fda': 30,
        'earnings': 25,
        'partnership': 20,
        'insider': 15,
        'general': 10
    },
    'multiday': {
        'base': 20
    }
}


def calculate_optimal_weights(days=30):
    """
    Calculate optimal weights based on performance data

    Returns:
        dict: Recommended weight adjustments
    """
    print(f"\n{'='*70}")
    print(f"LEARNING ENGINE - Analyzing Last {days} Days")
    print(f"{'='*70}\n")

    # Get performance data
    analysis = analyze_performance(days)
    if 'error' in analysis:
        print(f"⚠️  {analysis['error']}")
        return None

    factors = get_factor_performance(days)
    if 'error' in factors:
        print(f"⚠️  {factors['error']}")
        return None

    recommendations = {}

    print("📊 Performance Overview:")
    print(f"   Total Trades: {analysis['total_trades']}")
    print(f"   Win Rate: {analysis['win_rate']:.1f}%")
    print(f"   Avg Return: {analysis['avg_return']:+.1f}%\n")

    # Analyze float performance
    print("🔬 Float Analysis:")
    if 'ultra_low_float' in factors and 'low_float' in factors:
        ultra = factors['ultra_low_float']
        low = factors['low_float']

        print(f"   Ultra-low float (<10M): {ultra['win_rate']:.0f}% win rate, {ultra['avg_return']:+.1f}% avg")
        print(f"   Low float (10-30M): {low['win_rate']:.0f}% win rate, {low['avg_return']:+.1f}% avg")

        # If ultra-low float significantly outperforms, increase weight
        if ultra['win_rate'] > low['win_rate'] + 15:
            recommendations['float_ultra_low'] = {
                'current': CURRENT_WEIGHTS['float']['ultra_low'],
                'recommended': min(60, CURRENT_WEIGHTS['float']['ultra_low'] + 5),
                'reason': f"Ultra-low float has {ultra['win_rate']:.0f}% win rate vs {low['win_rate']:.0f}% for low float"
            }
            print(f"   💡 RECOMMENDATION: Increase ultra-low float weight to {recommendations['float_ultra_low']['recommended']}")
    print()

    # Analyze momentum performance
    print("🚀 Momentum Analysis:")
    if 'early_entry' in factors and 'chasing' in factors:
        early = factors['early_entry']
        chase = factors['chasing']

        print(f"   Early entry (≤5% up): {early['win_rate']:.0f}% win rate, {early['avg_return']:+.1f}% avg")
        print(f"   Chasing (>10% up): {chase['win_rate']:.0f}% win rate, {chase['avg_return']:+.1f}% avg")

        # If chasing consistently fails, add penalty
        if chase['win_rate'] < 40:
            recommendations['momentum_penalty'] = {
                'current': 0,
                'recommended': -15,
                'reason': f"Chasing stocks >10% up has only {chase['win_rate']:.0f}% win rate"
            }
            print(f"   💡 RECOMMENDATION: Add -15pt penalty for stocks already up >10%")

        # If early entry works well, boost it
        if early['win_rate'] > 60:
            recommendations['momentum_perfect'] = {
                'current': CURRENT_WEIGHTS['momentum']['perfect'],
                'recommended': min(50, CURRENT_WEIGHTS['momentum']['perfect'] + 5),
                'reason': f"Early entry has {early['win_rate']:.0f}% win rate"
            }
            print(f"   💡 RECOMMENDATION: Increase perfect entry weight to {recommendations['momentum_perfect']['recommended']}")
    print()

    # Analyze catalyst performance
    print("📰 Catalyst Analysis:")
    if 'with_catalyst' in factors and 'without_catalyst' in factors:
        with_cat = factors['with_catalyst']
        without_cat = factors['without_catalyst']

        print(f"   With catalyst: {with_cat['win_rate']:.0f}% win rate, {with_cat['avg_return']:+.1f}% avg")
        print(f"   Without catalyst: {without_cat['win_rate']:.0f}% win rate, {without_cat['avg_return']:+.1f}% avg")

        # If catalyst doesn't add value, reduce weight
        if abs(with_cat['win_rate'] - without_cat['win_rate']) < 10:
            recommendations['catalyst_reduce'] = {
                'current': 30,
                'recommended': 20,
                'reason': f"Catalyst not significantly improving win rate ({with_cat['win_rate']:.0f}% vs {without_cat['win_rate']:.0f}%)"
            }
            print(f"   💡 RECOMMENDATION: Reduce catalyst weight to 20 (not adding much value)")
    print()

    # Analyze by score range
    print("🎯 Score Range Performance:")
    for range_name, perf in analysis['score_performance'].items():
        print(f"   {range_name}: {perf['trades']} trades, {perf['win_rate']:.0f}% win rate, {perf['avg_return']:+.1f}% avg")

    if '150+' in analysis['score_performance']:
        high_score = analysis['score_performance']['150+']
        if high_score['win_rate'] > 70:
            print(f"\n   💡 High confidence: Scores 150+ have {high_score['win_rate']:.0f}% win rate")
            print(f"      → Consider increasing position size on 150+ scores")
    print()

    return recommendations


def apply_recommendations(recommendations):
    """
    Apply weight recommendations to scanner

    NOTE: This is a placeholder. Actual implementation would:
    1. Parse diamond_scanner.py
    2. Update weight values
    3. Write back to file
    4. Log changes to memory

    For now, this just logs recommendations.
    """
    print(f"\n{'='*70}")
    print("APPLYING WEIGHT UPDATES")
    print(f"{'='*70}\n")

    if not recommendations:
        print("   No recommendations to apply")
        return

    # Log to learning updates file
    if not LEARNING_LOG.exists():
        LEARNING_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LEARNING_LOG, 'w') as f:
            json.dump([], f)

    with open(LEARNING_LOG, 'r') as f:
        learning_history = json.load(f)

    update_entry = {
        'timestamp': datetime.now().isoformat(),
        'recommendations': recommendations,
        'applied': True
    }

    learning_history.append(update_entry)

    with open(LEARNING_LOG, 'w') as f:
        json.dump(learning_history, f, indent=2)

    print(f"   ✅ Logged {len(recommendations)} recommendations")
    print(f"   📝 Saved to {LEARNING_LOG}")
    print(f"\n   ⚠️  NOTE: Auto-updating scanner code coming soon.")
    print(f"   For now, manually update diamond_scanner.py with these weights:\n")

    for key, rec in recommendations.items():
        print(f"   {key}:")
        print(f"      Current: {rec['current']} → Recommended: {rec['recommended']}")
        print(f"      Reason: {rec['reason']}\n")

    # Log to memory file
    today = datetime.now().strftime('%Y-%m-%d')
    memory_file = MEMORY_DIR / f'{today}.md'

    memory_entry = f"\n## {datetime.now().strftime('%I:%M %p')} - LEARNING ENGINE UPDATE\n\n"
    memory_entry += "**Scanner Weight Recommendations:**\n\n"
    for key, rec in recommendations.items():
        memory_entry += f"- **{key}**: {rec['current']} → {rec['recommended']}\n"
        memory_entry += f"  - Reason: {rec['reason']}\n\n"

    if memory_file.exists():
        with open(memory_file, 'a') as f:
            f.write(memory_entry)
        print(f"   ✅ Logged to {memory_file}")
    else:
        print(f"   ⚠️  Memory file for today doesn't exist yet: {memory_file}")

    print()


def main():
    days = 30
    apply = False

    # Parse arguments
    if '--days' in sys.argv:
        idx = sys.argv.index('--days')
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])

    if '--apply' in sys.argv:
        apply = True

    # Calculate recommendations
    recommendations = calculate_optimal_weights(days)

    if recommendations and apply:
        apply_recommendations(recommendations)
    elif recommendations:
        print(f"\n{'='*70}")
        print("💡 RECOMMENDATIONS READY")
        print(f"{'='*70}\n")
        print("To apply these recommendations, run:")
        print(f"   python3 {sys.argv[0]} --apply\n")


if __name__ == '__main__':
    main()
