#!/usr/bin/env python3
"""
SqueezeSeeker Scanner - Phase 1
Implements the proven 63.8% return framework from June-July tracker

Phase 1 capabilities:
- Universe filter (price, volume)
- Early momentum detection (+5-20%, not chasing)
- Basic scoring (without float/options data)
- News catalyst detection
"""

import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
import time

def get_stock_universe():
    """
    Get initial stock universe from common indices
    In production, this would use a real screener API
    """
    # Start with popular small-cap tickers
    # In real implementation, would screen all NYSE/NASDAQ
    universe = [
        # Recent movers
        'VIGL', 'CRWV', 'AEVA', 'CRDO', 'SEZL',
        # Current portfolio
        'PTNM', 'SPHR', 'LGN', 'WULF', 'UEC', 'UUUU', 'RGTI', 'AI',
        'SOUN', 'QUBT', 'KOPN', 'SERV', 'KNOW', 'COOK', 'MMCA',
        # Popular small caps
        'NVDA', 'TSLA', 'SMCI', 'PLTR', 'IONQ', 'MARA', 'RIOT',
        'CVNA', 'OPEN', 'DKNG', 'HOOD', 'SOFI', 'UPST', 'COIN',
        # Biotech
        'TNXP', 'GEVO', 'NKLA', 'BLNK', 'CHPT', 'LCID', 'RIVN',
        # Squeeze candidates
        'GME', 'AMC', 'BBBY', 'BYND', 'CLOV', 'WISH', 'SKLZ'
    ]
    return universe

def universe_filter(symbol):
    """
    1️⃣ Universe Filter - Hard filters (80% die here)
    - Price: $0.50 – $100
    - Avg daily volume (30D): ≥ 1M shares
    - Today's volume: ≥ 3× 30-day average
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period='2mo')
        
        if len(hist) < 30:
            return None, "Insufficient history"
        
        # Price check
        current_price = hist['Close'].iloc[-1]
        if current_price < 0.50 or current_price > 100:
            return None, f"Price ${current_price:.2f} outside $0.50-$100 range"
        
        # Avg volume check (30 day)
        avg_volume_30d = hist['Volume'].tail(30).mean()
        if avg_volume_30d < 1_000_000:
            return None, f"Avg volume {avg_volume_30d/1e6:.1f}M < 1M"
        
        # Today's volume vs 30-day avg
        today_volume = hist['Volume'].iloc[-1]
        volume_ratio = today_volume / avg_volume_30d
        if volume_ratio < 3.0:
            return None, f"Volume ratio {volume_ratio:.1f}x < 3x"
        
        return {
            'symbol': symbol,
            'price': current_price,
            'volume_30d_avg': avg_volume_30d,
            'volume_today': today_volume,
            'volume_ratio': volume_ratio,
            'history': hist
        }, None
        
    except Exception as e:
        return None, f"Error: {str(e)}"

def early_momentum_signature(data):
    """
    2️⃣ Early Momentum Signature (MOST IMPORTANT)
    Required pattern (at least 3 of 4):
    - Intraday % gain: +5% to +20% (not +60% already)
    - Multi-day structure: 2–4 green days in last 5
    - Not chasing extended moves
    
    Returns: (score 0-25, signals list)
    """
    hist = data['history']
    score = 0
    signals = []
    
    # Check 1: Intraday gain +5% to +20%
    prev_close = hist['Close'].iloc[-2]
    current = hist['Close'].iloc[-1]
    daily_gain_pct = ((current - prev_close) / prev_close) * 100
    
    if 5 <= daily_gain_pct <= 20:
        score += 10
        signals.append(f"✅ Ideal momentum: +{daily_gain_pct:.1f}%")
    elif daily_gain_pct > 20:
        signals.append(f"⚠️  Extended: +{daily_gain_pct:.1f}% (chasing risk)")
    elif daily_gain_pct < 5:
        signals.append(f"❌ Weak momentum: +{daily_gain_pct:.1f}%")
    
    # Check 2: Multi-day structure (2-4 green days in last 5)
    last_5 = hist['Close'].tail(5)
    green_days = (last_5.diff() > 0).sum()
    
    if 2 <= green_days <= 4:
        score += 10
        signals.append(f"✅ Healthy structure: {green_days} green days in last 5")
    else:
        signals.append(f"❌ Poor structure: {green_days} green days in last 5")
    
    # Check 3: Higher lows (simplified - check last 3 lows)
    lows = hist['Low'].tail(3).values
    if len(lows) >= 3 and lows[-1] > lows[-2] > lows[-3]:
        score += 5
        signals.append("✅ Higher lows pattern")
    
    return score, signals, daily_gain_pct

def technical_health(data):
    """
    6️⃣ Technical Health (Entry Precision)
    - RSI: 60–70 (momentum, not overbought)
    - Price trend: 9 EMA above 20 EMA
    
    Returns: (score 0-15, signals list)
    """
    hist = data['history']
    score = 0
    signals = []
    
    # Calculate RSI (14 period)
    delta = hist['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    current_rsi = rsi.iloc[-1]
    
    if 60 <= current_rsi <= 70:
        score += 10
        signals.append(f"✅ RSI {current_rsi:.1f} (momentum zone)")
    elif current_rsi > 70:
        signals.append(f"⚠️  RSI {current_rsi:.1f} (overbought)")
    else:
        signals.append(f"❌ RSI {current_rsi:.1f} (weak)")
    
    # Calculate EMAs
    ema_9 = hist['Close'].ewm(span=9, adjust=False).mean()
    ema_20 = hist['Close'].ewm(span=20, adjust=False).mean()
    
    if ema_9.iloc[-1] > ema_20.iloc[-1]:
        score += 5
        signals.append("✅ 9 EMA > 20 EMA (bullish)")
    else:
        signals.append("❌ 9 EMA < 20 EMA (bearish)")
    
    return score, signals

def check_catalyst(symbol):
    """
    4️⃣ Verified Catalyst (No "Hope Trades")
    Check for recent news/catalysts
    
    Returns: (score 0-20, catalyst description)
    """
    # Simplified: in production would use news API
    # For now, check if stock has recent price action
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news[:3] if hasattr(ticker, 'news') else []
        
        if news:
            recent_news = news[0]
            title = recent_news.get('title', 'Unknown')
            return 10, f"Recent news: {title[:60]}..."
        else:
            return 0, "No recent catalyst found"
    except:
        return 0, "Unable to check catalysts"

def calculate_final_score(momentum_score, technical_score, catalyst_score):
    """
    7️⃣ Scoring Thresholds
    - Score ≥ 75 → Trade-ready (core allocation)
    - Score 70–74 → Watch / starter size
    - Score < 70 → Ignore
    
    Max possible: 25 (momentum) + 15 (technical) + 20 (catalyst) + 40 (placeholder for supply constraint)
    = 100 points
    
    Phase 1: Max = 60 (without supply constraint data)
    Scale to 100: multiply by 1.67
    """
    base_score = momentum_score + technical_score + catalyst_score
    # Scale to 100 (since we're missing 40 pts from supply constraint)
    scaled_score = min(100, base_score * 1.67)
    return scaled_score

def scan():
    """Run the squeeze scanner"""
    print("=" * 80)
    print("SQUEEZE SCANNER - Phase 1")
    print(f"Running at {datetime.now().strftime('%I:%M %p PT')}")
    print("=" * 80)
    
    universe = get_stock_universe()
    print(f"\n🔍 Scanning {len(universe)} stocks...\n")
    
    candidates = []
    
    for symbol in universe:
        print(f"Checking {symbol}...", end=" ")
        
        # Step 1: Universe filter
        data, error = universe_filter(symbol)
        if error:
            print(f"❌ {error}")
            continue
        
        print(f"✅ Passed filter (${data['price']:.2f}, {data['volume_ratio']:.1f}x volume)")
        
        # Step 2: Early momentum
        momentum_score, momentum_signals, daily_gain = early_momentum_signature(data)
        
        # Step 3: Technical health
        technical_score, technical_signals = technical_health(data)
        
        # Step 4: Catalyst check
        catalyst_score, catalyst_info = check_catalyst(symbol)
        
        # Calculate final score
        final_score = calculate_final_score(momentum_score, technical_score, catalyst_score)
        
        candidates.append({
            'symbol': symbol,
            'price': data['price'],
            'volume_ratio': data['volume_ratio'],
            'daily_gain': daily_gain,
            'momentum_score': momentum_score,
            'technical_score': technical_score,
            'catalyst_score': catalyst_score,
            'final_score': final_score,
            'momentum_signals': momentum_signals,
            'technical_signals': technical_signals,
            'catalyst': catalyst_info
        })
        
        time.sleep(0.5)  # Rate limiting
    
    # Sort by score
    candidates.sort(key=lambda x: x['final_score'], reverse=True)
    
    # Print results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    trade_ready = [c for c in candidates if c['final_score'] >= 75]
    watch_list = [c for c in candidates if 70 <= c['final_score'] < 75]
    
    if trade_ready:
        print("\n🚀 TRADE-READY (Score ≥ 75):")
        print("-" * 80)
        for c in trade_ready:
            print(f"\n{c['symbol']}: {c['final_score']:.0f}/100 - ${c['price']:.2f} (+{c['daily_gain']:.1f}%)")
            print(f"   Volume: {c['volume_ratio']:.1f}x average")
            print(f"   Momentum: {c['momentum_score']}/25")
            for signal in c['momentum_signals']:
                print(f"      {signal}")
            print(f"   Technical: {c['technical_score']}/15")
            for signal in c['technical_signals']:
                print(f"      {signal}")
            print(f"   Catalyst: {c['catalyst']}")
    else:
        print("\n⚠️  No trade-ready candidates found (score ≥ 75)")
    
    if watch_list:
        print("\n👀 WATCH LIST (Score 70-74):")
        print("-" * 80)
        for c in watch_list:
            print(f"{c['symbol']}: {c['final_score']:.0f}/100 - ${c['price']:.2f} (+{c['daily_gain']:.1f}%)")
    
    print("\n" + "=" * 80)
    print(f"Scanned {len(universe)} stocks | Found {len(candidates)} passing universe filter")
    print(f"Trade-ready: {len(trade_ready)} | Watch list: {len(watch_list)}")
    print("=" * 80)
    
    return candidates

if __name__ == '__main__':
    scan()
