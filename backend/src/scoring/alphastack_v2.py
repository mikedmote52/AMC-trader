#!/usr/bin/env python3
"""
AlphaStack v2 — Momentum Builder Scoring Engine
Focus: Multi‑day momentum ("Builder" regime) + Classic "Spike" regime

This module implements the revised scoring based on insights:
- Track consecutive up days, moderate 2–3× volume, VWAP/EMA structure
- Keep catalyst/options/sentiment inputs, but allow early builders before the big spike
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# ------------------------- Config -------------------------
@dataclass
class Config:
    # thresholds derived from pattern study
    watchlist_cut: int = 60
    trade_ready_cut: int = 75

    # momentum windows
    up_days_min: int = 3          # 3+ consecutive up days qualifies as Builder
    up_days_strong: int = 5       # 5+ is high-conviction momentum

    # volume
    avg_rel_vol_window: int = 5   # average relative volume window
    avg_rel_vol_min: float = 1.5  # allow 1.5–3×, not just 3×+
    any_day_rel_vol_strong: float = 2.5 # at least one day >=2.5× in last 5

    # price constraints
    max_price: float = 100.0      # broaden universe to $100

    # technicals
    rsi_min: float = 55           # healthy momentum floor
    rsi_pref: float = 60          # sweet spot 60–70
    atr_pct_min: float = 0.04     # ATR >= 4% of price

    # squeeze characteristics (still valuable but not required)
    float_cap: float = 50e6
    short_si_min: float = 0.20
    borrow_fee_min: float = 0.20
    utilization_min: float = 0.85

CFG = Config()

# ------------------------- Feature Schema -------------------------
"""Expected input fields in `features` (dict):
- ticker: str
- price: float
- rel_vol_now: float                 # intraday relative volume (optional)
- rel_vol_5d: list[float]           # last 5 days' relative volume
- consecutive_up_days: int
- daily_change_pct: float
- rsi: float
- atr_pct: float
- vwap: float
- ema9: float
- ema20: float
- float_shares: float (optional)
- short_interest: float (optional)
- utilization: float (optional)
- borrow_fee_pct: float (optional)
- options_call_oi: int (optional)
- options_put_oi: int (optional)
- iv_percentile: float (optional)
- catalyst_detected: bool
- social_rank: int (optional, 1-100)
"""

def detect_regime(features: Dict[str, Any]) -> str:
    """Detect whether this is a BUILDER or SPIKE regime"""

    consecutive_up = features.get('consecutive_up_days', 0)
    rel_vol_now = features.get('rel_vol_now', 1.0)
    daily_change = abs(features.get('daily_change_pct', 0))

    # SPIKE regime: big single-day move
    if rel_vol_now >= 3.0 and daily_change >= 10.0:
        return 'SPIKE'

    # BUILDER regime: steady momentum
    if consecutive_up >= CFG.up_days_min:
        return 'BUILDER'

    # Default to spike if unclear
    return 'SPIKE'

def score_momentum(features: Dict[str, Any], regime: str) -> float:
    """Score momentum component (0-25 points)"""
    score = 0.0

    consecutive_up = features.get('consecutive_up_days', 0)
    rel_vol_5d = features.get('rel_vol_5d', [1.0] * 5)
    rel_vol_now = features.get('rel_vol_now', 1.0)
    daily_change = abs(features.get('daily_change_pct', 0))

    # Average relative volume over 5 days
    avg_rel_vol = sum(rel_vol_5d) / len(rel_vol_5d) if rel_vol_5d else 1.0
    max_rel_vol = max(rel_vol_5d) if rel_vol_5d else rel_vol_now

    if regime == 'BUILDER':
        # Builder regime scoring (multi-day momentum)

        # Consecutive up days (0-10 points)
        if consecutive_up >= CFG.up_days_strong:
            score += 10
        elif consecutive_up >= CFG.up_days_min:
            score += 5 + (consecutive_up - CFG.up_days_min) * 2.5
        else:
            score += consecutive_up * 1.5

        # Average volume (0-10 points)
        if avg_rel_vol >= 2.5:
            score += 10
        elif avg_rel_vol >= CFG.avg_rel_vol_min:
            score += 5 + (avg_rel_vol - CFG.avg_rel_vol_min) * 3.3
        else:
            score += avg_rel_vol * 3.3

        # Peak volume day (0-5 points)
        if max_rel_vol >= CFG.any_day_rel_vol_strong:
            score += 5
        elif max_rel_vol >= 2.0:
            score += 2.5 + (max_rel_vol - 2.0) * 5

    else:
        # SPIKE regime scoring (single-day explosion)

        # Current volume spike (0-12 points)
        if rel_vol_now >= 5.0:
            score += 12
        elif rel_vol_now >= 3.0:
            score += 8 + (rel_vol_now - 3.0) * 2
        elif rel_vol_now >= 2.0:
            score += 4 + (rel_vol_now - 2.0) * 4
        else:
            score += rel_vol_now * 2

        # Daily price change (0-8 points)
        if daily_change >= 15:
            score += 8
        elif daily_change >= 10:
            score += 5 + (daily_change - 10) * 0.6
        elif daily_change >= 5:
            score += 2 + (daily_change - 5) * 0.6
        else:
            score += daily_change * 0.4

        # Recent momentum (0-5 points)
        if consecutive_up >= 2:
            score += min(consecutive_up, 5)

    return min(score, 25.0)

def score_float_short(features: Dict[str, Any]) -> float:
    """Score float/short squeeze potential (0-15 points)"""
    score = 0.0

    float_shares = features.get('float_shares', float('inf'))
    short_interest = features.get('short_interest', 0)
    utilization = features.get('utilization', 0)
    borrow_fee = features.get('borrow_fee_pct', 0)

    # Float size (0-5 points)
    if float_shares <= CFG.float_cap:
        score += 5 * (1 - float_shares / CFG.float_cap)

    # Short interest (0-5 points)
    if short_interest >= CFG.short_si_min:
        score += min(short_interest / CFG.short_si_min * 5, 5)

    # Utilization (0-3 points)
    if utilization >= CFG.utilization_min:
        score += 3
    elif utilization >= 0.7:
        score += utilization * 4.3 - 3

    # Borrow fee (0-2 points)
    if borrow_fee >= CFG.borrow_fee_min:
        score += min(borrow_fee / CFG.borrow_fee_min * 2, 2)

    return min(score, 15.0)

def score_catalyst(features: Dict[str, Any]) -> float:
    """Score catalyst component (0-20 points)"""
    catalyst = features.get('catalyst_detected', False)
    social_rank = features.get('social_rank', 0)

    score = 0.0

    # Direct catalyst (0-15 points)
    if catalyst:
        score += 15

    # Social momentum (0-5 points)
    if social_rank > 0:
        score += min(social_rank / 20, 5)  # Top 20 gets full 5 points

    return min(score, 20.0)

def score_sentiment(features: Dict[str, Any]) -> float:
    """Score sentiment/social component (0-15 points)"""
    social_rank = features.get('social_rank', 0)
    rel_vol_now = features.get('rel_vol_now', 1.0)

    score = 0.0

    # Social ranking (0-10 points)
    if social_rank > 0:
        if social_rank <= 10:
            score += 10
        elif social_rank <= 50:
            score += 10 * (1 - (social_rank - 10) / 40)

    # Volume as sentiment proxy (0-5 points)
    if rel_vol_now >= 3.0:
        score += 5
    elif rel_vol_now >= 2.0:
        score += 2.5 + (rel_vol_now - 2.0) * 2.5

    return min(score, 15.0)

def score_options(features: Dict[str, Any]) -> float:
    """Score options flow component (0-10 points)"""
    call_oi = features.get('options_call_oi', 0)
    put_oi = features.get('options_put_oi', 0)
    iv_percentile = features.get('iv_percentile', 50)

    score = 0.0

    # Call/Put ratio (0-5 points)
    if put_oi > 0:
        cp_ratio = call_oi / put_oi
        if cp_ratio >= 2.0:
            score += 5
        elif cp_ratio >= 1.5:
            score += 2.5 + (cp_ratio - 1.5) * 5
        elif cp_ratio >= 1.0:
            score += cp_ratio * 2.5

    # IV percentile (0-5 points)
    if 30 <= iv_percentile <= 70:  # Sweet spot
        score += 5
    elif iv_percentile < 30:
        score += iv_percentile / 6
    else:
        score += max(0, 5 - (iv_percentile - 70) / 6)

    return min(score, 10.0)

def score_technicals(features: Dict[str, Any]) -> float:
    """Score technical setup (0-15 points)"""
    rsi = features.get('rsi', 50)
    atr_pct = features.get('atr_pct', 0)
    price = features.get('price', 0)
    vwap = features.get('vwap', price)
    ema9 = features.get('ema9', price)
    ema20 = features.get('ema20', price)

    score = 0.0

    # RSI momentum (0-5 points)
    if CFG.rsi_pref <= rsi <= 70:
        score += 5
    elif CFG.rsi_min <= rsi < CFG.rsi_pref:
        score += (rsi - CFG.rsi_min) / (CFG.rsi_pref - CFG.rsi_min) * 5
    elif 70 < rsi <= 75:
        score += 5 - (rsi - 70)

    # ATR volatility (0-5 points)
    if atr_pct >= CFG.atr_pct_min:
        score += min(atr_pct / CFG.atr_pct_min * 5, 5)

    # Price structure (0-5 points)
    structure_score = 0
    if price >= vwap:
        structure_score += 2
    if ema9 > ema20:
        structure_score += 2
    if price >= ema9:
        structure_score += 1
    score += structure_score

    return min(score, 15.0)

def generate_entry_plan(features: Dict[str, Any], composite: float, regime: str) -> Dict[str, Any]:
    """Generate entry and risk management plan"""
    price = features.get('price', 0)
    vwap = features.get('vwap', price)
    atr_pct = features.get('atr_pct', 0.05)

    if composite >= CFG.trade_ready_cut:
        if regime == 'BUILDER':
            trigger = f"VWAP reclaim at ${vwap:.2f} or break above ${price * 1.02:.2f}"
        else:
            trigger = f"Hold above ${vwap:.2f} for 15min with volume"

        stop = price * 0.9  # 10% stop
        tp1 = price * 1.2   # 20% first target
        tp2 = price * 1.5   # 50% runner target

    elif composite >= CFG.watchlist_cut:
        trigger = f"Wait for 3x+ volume day with VWAP reclaim"
        stop = price * 0.9
        tp1 = price * 1.15
        tp2 = price * 1.35
    else:
        trigger = "Needs catalyst or momentum improvement"
        stop = price * 0.9
        tp1 = price * 1.1
        tp2 = price * 1.2

    return {
        'trigger': trigger,
        'stop': round(stop, 2),
        'tp1': round(tp1, 2),
        'tp2': round(tp2, 2)
    }

def score_ticker(features: Dict[str, Any]) -> Dict[str, Any]:
    """Main scoring function - AlphaStack v2"""

    ticker = features.get('ticker', 'UNKNOWN')
    price = features.get('price', 0)

    # Detect regime
    regime = detect_regime(features)

    # Calculate component scores
    scores = {
        'momentum': score_momentum(features, regime),
        'float_short': score_float_short(features),
        'catalyst': score_catalyst(features),
        'sentiment': score_sentiment(features),
        'options': score_options(features),
        'technicals': score_technicals(features)
    }

    # Calculate composite
    composite = sum(scores.values())

    # Determine action
    if composite >= CFG.trade_ready_cut:
        action = 'Trade-ready'
    elif composite >= CFG.watchlist_cut:
        action = 'Watch'
    else:
        action = 'Pass'

    # Generate entry plan
    entry_plan = generate_entry_plan(features, composite, regime)

    return {
        'ticker': ticker,
        'regime': regime,
        'scores': scores,
        'composite': round(composite, 1),
        'action': action,
        'entry_plan': entry_plan,
        'price': price
    }