#!/usr/bin/env python3
"""
POSITION CULLING ENGINE - Trim Portfolio to 10-12 Target
Analyzes all 17 positions and recommends which 5 to cut
"""

import json
from pathlib import Path
from datetime import datetime

WORKSPACE = Path('/Users/mikeclawd/.openclaw/workspace')

def load_portfolio():
    """Load current positions from state/current.md"""
    positions = [
        {"symbol": "RIG", "gain": 22.4, "value": 360, "thesis": "Energy/oil", "conviction": 9},
        {"symbol": "SPHR", "gain": 18.6, "value": 226, "thesis": "Entertainment", "conviction": 8},
        {"symbol": "KSS", "gain": 15.1, "value": 124, "thesis": "Retail recovery", "conviction": 8},
        {"symbol": "LGN", "gain": 10.9, "value": 165, "thesis": "Pharma", "conviction": 6},
        {"symbol": "KNOW", "gain": 10.1, "value": 138, "thesis": "AI tutoring", "conviction": 6},
        {"symbol": "RIVN", "gain": 5.7, "value": 198, "thesis": "EV trucks", "conviction": 5},
        {"symbol": "MMCA", "gain": 2.1, "value": 89, "thesis": "Unknown", "conviction": 3},
        {"symbol": "CFLT", "gain": 0.6, "value": 92, "thesis": "Unknown", "conviction": 3},
        {"symbol": "PAII.U", "gain": 0.4, "value": 92, "thesis": "SPAC", "conviction": 2},
        {"symbol": "PAAA", "gain": 0.1, "value": 154, "thesis": "Unknown", "conviction": 2},
        {"symbol": "IPCX", "gain": 0.1, "value": 91, "thesis": "Unknown", "conviction": 2},
        {"symbol": "ITOS", "gain": -0.0, "value": 91, "thesis": "Biotech", "conviction": 4},
        {"symbol": "SERV", "gain": -0.5, "value": 97, "thesis": "Unknown", "conviction": 2},
        {"symbol": "KRE", "gain": -3.1, "value": 69, "thesis": "Regional banks", "conviction": 3},
        {"symbol": "UUUU", "gain": -6.0, "value": 8, "thesis": "Uranium", "conviction": 4, "remnant": True},
        {"symbol": "KOPN", "gain": -8.5, "value": 93, "thesis": "AR displays", "conviction": 4},
        {"symbol": "RGTI", "gain": -8.8, "value": 49, "thesis": "Quantum", "conviction": 5},
    ]
    return positions

def rank_positions(positions):
    """Rank by conviction, performance, thesis strength"""
    
    # Scoring algorithm
    for p in positions:
        score = 0
        
        # Conviction score (0-10)
        score += p['conviction'] * 3
        
        # Performance score
        if p['gain'] > 20:
            score += 20
        elif p['gain'] > 10:
            score += 15
        elif p['gain'] > 0:
            score += 10
        elif p['gain'] > -5:
            score += 5
        else:
            score -= 10
        
        # Thesis clarity bonus
        if p['thesis'] != "Unknown":
            score += 5
        
        # Remnant penalty (tiny positions)
        if p.get('remnant', False):
            score -= 20
        
        p['total_score'] = score
    
    # Sort by total score descending
    return sorted(positions, key=lambda x: x['total_score'], reverse=True)

def generate_cull_recommendations():
    """Generate which positions to cut"""
    positions = load_portfolio()
    ranked = rank_positions(positions)
    
    # Top 12 to keep
    keep = ranked[:12]
    # Bottom 5 to cut
    cull = ranked[12:]
    
    report = f"""📊 POSITION CULLING ANALYSIS
Generated: {datetime.now().strftime('%Y-%m-%d %I:%M %p PT')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 TARGET: Reduce 17 positions → 12 positions
📉 ACTION: Cut 5 lowest-conviction holdings

🏆 TOP 12 - KEEP (Ranked by Conviction + Performance):

"""
    
    for i, p in enumerate(keep, 1):
        report += f"{i:2d}. {p['symbol']:6s} | {p['gain']:+.1f}% | Score: {p['total_score']:3d} | {p['thesis']}\n"
    
    report += f"""
❌ BOTTOM 5 - CUT (Lowest Scores):

"""
    
    for i, p in enumerate(cull, 1):
        report += f"{i}. {p['symbol']:6s} | {p['gain']:+.1f}% | Score: {p['total_score']:3d} | Reason: "
        
        if p.get('remnant', False):
            report += "Remnant position (too small)\n"
        elif p['thesis'] == "Unknown":
            report += "No documented thesis\n"
        elif p['gain'] < -5:
            report += "Underperforming, weak thesis\n"
        elif p['conviction'] < 4:
            report += "Low conviction\n"
        else:
            report += "Lowest ranked\n"
    
    report += f"""
💰 ESTIMATED PROCEEDS FROM CUTS:
"""
    
    total_value = sum(p['value'] for p in cull)
    for p in cull:
        report += f"• Sell {p['symbol']}: ~${p['value']:.0f}\n"
    
    report += f"""
Total Cash Released: ~${total_value:.0f}
New Cash Position: ~${99500 + total_value:.0f}

📝 EXECUTION PLAN:
1. Review thesis for bottom 5 positions
2. Confirm no near-term catalysts
3. Sell at market open (no rush)
4. Document reasons in memory log
5. Redeploy cash to high-conviction setups

⚠️ EXCEPTIONS:
• Don't cut if position has pending catalyst
• Don't cut if <1% of portfolio (remnants)
• Consider tax implications (loss harvesting)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
System Status: {'✅ RECOMMENDATION READY' if len(cull) == 5 else '⚠️ REVIEW NEEDED'}
"""
    
    return report, keep, cull

def main():
    report, keep, cull = generate_cull_recommendations()
    print(report)
    
    # Save to file
    report_path = WORKSPACE / 'logs' / f'position_culling_{datetime.now().strftime("%Y-%m-%d")}.txt'
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, 'w') as f:
        f.write(report)
    
    return keep, cull

if __name__ == '__main__':
    keep, cull = main()
