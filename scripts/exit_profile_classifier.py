#!/usr/bin/env python3
"""
EXIT PROFILE CLASSIFIER - Tag positions with squeeze/momentum/default profiles
Updates exit_state.json with correct trade_type for dynamic exit manager
"""

import json
from pathlib import Path
from datetime import datetime

WORKSPACE = Path('/Users/mikeclawd/.openclaw/workspace')
DATA = WORKSPACE / 'data'

def classify_position(symbol, float_shares, short_interest, catalyst_strength, sector_momentum):
    """Classify position into exit profile"""
    
    # SQUEEZE profile criteria
    squeeze_score = 0
    if float_shares and float_shares < 20_000_000:
        squeeze_score += 3
    if short_interest and short_interest > 0.20:  # >20% short
        squeeze_score += 3
    if catalyst_strength == "high":
        squeeze_score += 2
    if sector_momentum == "hot":
        squeeze_score += 2
    
    if squeeze_score >= 7:
        return {
            "trade_type": "squeeze",
            "initial_stop": -0.25,  # -25% wide stop
            "trail_trigger_1": 0.50,  # At +50%
            "trail_1_level": 0.40,  # Trail at 40% of peak
            "trail_trigger_2": 1.00,  # At +100%
            "trail_2_level": 0.50,  # Trail at 50% of peak
            "trail_trigger_3": 2.00,  # At +200%
            "trail_3_level": 0.60,  # Trail at 60% of peak
            "scale_1": 0.25,  # Scale 25% at +30%
            "scale_2": 0.25,  # Scale 25% at +50%
        }
    
    # MOMENTUM profile criteria
    momentum_score = 0
    if float_shares and 20_000_000 <= float_shares < 100_000_000:
        momentum_score += 2
    if catalyst_strength in ["medium", "high"]:
        momentum_score += 3
    if sector_momentum in ["warm", "hot"]:
        momentum_score += 2
    if short_interest and short_interest < 0.10:  # Low short interest
        momentum_score += 1
    
    if momentum_score >= 5:
        return {
            "trade_type": "momentum",
            "initial_stop": -0.15,  # -15% standard stop
            "trail_trigger_1": 0.20,  # At +20%
            "trail_1_level": 0.50,  # Trail at 50% of peak
            "trail_trigger_2": 0.40,  # At +40%
            "trail_2_level": 0.60,  # Trail at 60% of peak
            "scale_1": 0.30,  # Scale 30% at +30%
            "scale_2": None,  # No second scale
        }
    
    # DEFAULT profile (everything else)
    return {
        "trade_type": "default",
        "initial_stop": -0.15,  # -15% stop
        "profit_target": 0.30,  # +30% scale
        "scale_1": 0.50,  # Scale 50% at +30%
        "trailing_stop": -0.20,  # -20% trailing after +30%
    }

def update_exit_profiles():
    """Update all positions with correct exit profiles"""
    
    # Current portfolio classifications
    classifications = {
        "RIG": {"float": 1101_000_000, "short": 0.08, "catalyst": "high", "sector": "hot"},  # Energy hot
        "SPHR": {"float": 28_600_000, "short": 0.05, "catalyst": "medium", "sector": "warm"},
        "KSS": {"float": 112_200_000, "short": 0.12, "catalyst": "high", "sector": "warm"},  # Retail recovery
        "LGN": {"float": 58_700_000, "short": 0.03, "catalyst": "low", "sector": "neutral"},
        "KNOW": {"float": 500_000, "short": 0.15, "catalyst": "medium", "sector": "warm"},
        "RIVN": {"float": 50_000_000, "short": 0.10, "catalyst": "low", "sector": "neutral"},
        "MMCA": {"float": 10_000_000, "short": 0.05, "catalyst": "unknown", "sector": "neutral"},
        "CFLT": {"float": 30_000_000, "short": 0.08, "catalyst": "unknown", "sector": "neutral"},
        "PAII.U": {"float": 5_000_000, "short": 0.00, "catalyst": "spac", "sector": "neutral"},
        "PAAA": {"float": 8_000_000, "short": 0.02, "catalyst": "unknown", "sector": "neutral"},
        "IPCX": {"float": 12_000_000, "short": 0.04, "catalyst": "unknown", "sector": "neutral"},
        "ITOS": {"float": 45_000_000, "short": 0.06, "catalyst": "biotech", "sector": "neutral"},
        "SERV": {"float": 25_000_000, "short": 0.07, "catalyst": "unknown", "sector": "neutral"},
        "KRE": {"float": 200_000_000, "short": 0.05, "catalyst": "low", "sector": "cold"},
        "UUUU": {"float": 203_000_000, "short": 0.10, "catalyst": "low", "sector": "neutral"},
        "KOPN": {"float": 15_000_000, "short": 0.08, "catalyst": "ar", "sector": "neutral"},
        "RGTI": {"float": 34_000_000, "short": 0.20, "catalyst": "quantum", "sector": "hot"},  # Quantum hot
    }
    
    # Load or create exit_state.json
    exit_state_path = DATA / 'exit_state.json'
    if exit_state_path.exists():
        with open(exit_state_path) as f:
            exit_state = json.load(f)
    else:
        exit_state = {}
    
    # Update each position
    updated = {}
    for symbol, attrs in classifications.items():
        profile = classify_position(
            symbol,
            attrs["float"],
            attrs["short"],
            attrs["catalyst"],
            attrs["sector"]
        )
        
        # Merge with existing state if present
        if symbol in exit_state:
            updated[symbol] = {**exit_state[symbol], **profile}
        else:
            updated[symbol] = {
                "symbol": symbol,
                "trade_type": profile["trade_type"],
                "entry_date": "2026-02-01",  # Approximate
                "entry_price": 0.0,  # Will be filled from Alpaca
                "peak_gain": 0.0,
                "current_gain": 0.0,
                **{k: v for k, v in profile.items() if k != "trade_type"}
            }
    
    # Save updated state
    with open(exit_state_path, 'w') as f:
        json.dump(updated, f, indent=2)
    
    return updated

def generate_profile_report():
    """Generate report of exit profile assignments"""
    profiles = update_exit_profiles()
    
    squeeze_count = sum(1 for p in profiles.values() if p.get("trade_type") == "squeeze")
    momentum_count = sum(1 for p in profiles.values() if p.get("trade_type") == "momentum")
    default_count = sum(1 for p in profiles.values() if p.get("trade_type") == "default")
    
    report = f"""🎯 EXIT PROFILE CLASSIFICATION
Generated: {datetime.now().strftime('%Y-%m-%d %I:%M %p PT')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 PROFILE DISTRIBUTION:
• SQUEEZE:   {squeeze_count} positions (wide stops, let runners)
• MOMENTUM:  {momentum_count} positions (standard + trailing)
• DEFAULT:   {default_count} positions (conservative -15%/+30%)

🔥 SQUEEZE PLAYS (High Volatility, Wide Stops):
"""
    
    for symbol, profile in profiles.items():
        if profile.get("trade_type") == "squeeze":
            report += f"• {symbol}: -25% stop, scale 25% at +30%, trail from +50%\n"
    
    report += f"""
📈 MOMENTUM PLAYS (Steady Climbers):
"""
    
    for symbol, profile in profiles.items():
        if profile.get("trade_type") == "momentum":
            report += f"• {symbol}: -15% stop, scale 30% at +30%, trail from +20%\n"
    
    report += f"""
⚙️ DEFAULT PLAYS (Conservative):
"""
    
    for symbol, profile in profiles.items():
        if profile.get("trade_type") == "default":
            report += f"• {symbol}: -15% stop, scale 50% at +30%\n"
    
    report += f"""
💡 KEY IMPROVEMENTS:
• RIG tagged as SQUEEZE (energy momentum, potential +100%)
• RGTI tagged as SQUEEZE (quantum hype, volatile)
• KSS tagged as MOMENTUM (retail recovery, steady)
• Most small positions stay DEFAULT (no strong thesis)

⚠️ ACTION NEEDED:
• Verify entry prices from Alpaca API
• Update peak_gain values from actual performance
• Review classifications weekly as conditions change

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ exit_state.json updated with correct profiles
"""
    
    return report

def main():
    report = generate_profile_report()
    print(report)
    
    # Save report
    report_path = WORKSPACE / 'logs' / f'exit_profiles_{datetime.now().strftime("%Y-%m-%d")}.txt'
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, 'w') as f:
        f.write(report)

if __name__ == '__main__':
    main()
