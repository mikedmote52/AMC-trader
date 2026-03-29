#!/usr/bin/env python3
"""
COIL DETECTOR - Find stocks at bottom of dead cat, before bounce

Pattern:
1. Massive drop (-50% to -70%) over 3-5 days
2. Volume exhaustion (dries up) 
3. Consolidation/bottoming for 1-2 days
4. Ready for reversal

Buy signal: Break above consolidation range with volume
"""

def detect_coil_setup(symbol, bars):
    """
    Detect if stock is at bottom coil before dead cat bounce
    Returns: (score, description) or (0, None)
    """
    if not bars or len(bars) < 10:
        return 0, None
    
    # Look at last 10 days
    prices = [bar.close for bar in bars[-10:]]
    volumes = [bar.volume for bar in bars[-10:]]
    
    if len(prices) < 10:
        return 0, None
    
    # Stage 1: Massive drop in first 5 days
    max_5d = max(prices[:5])
    min_5d = min(prices[:5])
    drop_pct = (max_5d - min_5d) / max_5d * 100 if max_5d > 0 else 0
    
    if drop_pct < 40:  # Not enough drop
        return 0, None
    
    # Stage 2: Consolidation in last 5 days
    recent_prices = prices[5:]
    recent_high = max(recent_prices)
    recent_low = min(recent_prices)
    consolidation_range = (recent_high - recent_low) / recent_low * 100 if recent_low > 0 else 999
    
    if consolidation_range > 15:  # Still too volatile
        return 0, None
    
    # Stage 3: Volume exhaustion
    early_volumes = volumes[:5]
    recent_volumes = volumes[5:]
    
    avg_early_vol = sum(early_volumes) / len(early_volumes) if early_volumes else 1
    avg_recent_vol = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 1
    
    volume_dry_up = avg_recent_vol / avg_early_vol if avg_early_vol > 0 else 0
    
    if volume_dry_up > 0.5:  # Volume still too high
        return 0, None
    
    # Stage 4: Current price at/near bottom
    current = prices[-1]
    bottom_zone = recent_low + (recent_high - recent_low) * 0.3  # Lower 30% of range
    
    if current > bottom_zone * 1.1:  # Not near bottom
        return 0, None
    
    # COIL DETECTED
    coil_score = min(100, int(drop_pct * 2))  # Max 100 pts for -50% drop
    
    desc = f"🌀 COIL: -{drop_pct:.0f}% drop → {consolidation_range:.0f}% range consolidation"
    desc += f"\n   Volume dried up to {volume_dry_up*100:.0f}% of drop phase"
    desc += f"\n   Ready for reversal, buy on break above ${recent_high:.2f}"
    desc += f"\n   Stop below ${recent_low:.2f}"
    
    return coil_score, desc


def get_coil_entry_trigger(symbol, bars):
    """
    Get the price to watch for entry (break of consolidation)
    """
    if not bars or len(bars) < 5:
        return None, None
    
    recent_prices = [bar.close for bar in bars[-5:]]
    recent_high = max(recent_prices)
    recent_low = min(recent_prices)
    
    entry_price = recent_high * 1.02  # Break +2%
    stop_price = recent_low * 0.98    # Stop -2%
    
    return entry_price, stop_price


if __name__ == '__main__':
    print("Coil Detector v1.0")
    print("Import this module to use detect_coil_setup()")
