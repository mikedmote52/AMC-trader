#!/usr/bin/env python3
"""
DIAMOND SCANNER - Finds stocks BEFORE they explode
Focus: Volume acceleration + Float + Catalysts = Pre-breakout detection
"""

from polygon import RESTClient
import json
from datetime import datetime, timedelta
import time
import os

with open('/Users/mikeclawd/.openclaw/secrets/polygon.json', 'r') as f:
    creds = json.load(f)

client = RESTClient(api_key=creds['apiKey'])

def detect_volume_acceleration(symbol):
    """
    Key insight: Winners show volume INCREASING day-over-day BEFORE breakout
    Returns: (acceleration_score, volume_pattern)
    """
    try:
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        
        bars = list(client.list_aggs(symbol, 1, "day", start, end, limit=7))
        
        if len(bars) < 5:
            return 0, "Insufficient data"
        
        # Get last 5 days of volume
        volumes = [bar.volume for bar in bars[-5:]]
        
        # Check if volume is increasing
        increasing_days = sum(1 for i in range(1, len(volumes)) if volumes[i] > volumes[i-1])
        
        # Calculate acceleration score
        score = 0
        pattern = []
        
        if increasing_days >= 3:  # 3+ days of increasing volume
            score = 20
            pattern.append(f"✅ {increasing_days}/4 days increasing volume")
        elif increasing_days == 2:
            score = 12
            pattern.append(f"⚠️  {increasing_days}/4 days increasing")
        
        # Check if today's volume is significantly higher
        if len(volumes) >= 2:
            today_vs_yesterday = volumes[-1] / volumes[-2]
            if today_vs_yesterday >= 2.0:
                score += 10
                pattern.append(f"✅ Today 2x+ yesterday's volume")
        
        return score, " | ".join(pattern) if pattern else "No acceleration"
        
    except:
        return 0, "Error"

def check_squeeze_setup(symbol):
    """
    Float + Short Interest combo = Squeeze potential
    Returns: (squeeze_score, details)
    """
    try:
        details = client.get_ticker_details(symbol)
        float_shares = details.share_class_shares_outstanding or 0
        
        score = 0
        info = []
        
        # Float scoring (higher score for lower float)
        if float_shares == 0:
            return 0, "No float data"
        elif float_shares <= 10_000_000:
            score = 50
            info.append(f"✅ ULTRA-LOW float: {float_shares/1e6:.1f}M")
        elif float_shares <= 20_000_000:
            score = 40
            info.append(f"✅ Very low float: {float_shares/1e6:.1f}M")
        elif float_shares <= 30_000_000:
            score = 30
            info.append(f"✅ Low float: {float_shares/1e6:.1f}M")
        elif float_shares <= 50_000_000:
            score = 20
            info.append(f"✅ Float: {float_shares/1e6:.1f}M")
        else:
            score = 5
            info.append(f"⚠️  Large float: {float_shares/1e6:.1f}M")
        
        # TODO: Add short interest when Polygon provides it
        # For now, ultra-low float is the main signal
        
        return score, " | ".join(info)
        
    except:
        return 0, "Error"

def check_fresh_catalyst(symbol):
    """
    Catalyst within 48 hours = Breakout trigger
    Returns: (catalyst_score, news)
    """
    try:
        # Get news from last 48 hours
        two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        
        news_items = list(client.list_ticker_news(
            symbol, 
            published_utc_gte=two_days_ago,
            limit=5
        ))
        
        if not news_items:
            return 0, "No recent catalyst"
        
        # Analyze news titles for key catalysts
        score = 0
        catalyst_type = "General news"
        
        for news in news_items:
            title = news.title.lower()
            
            # High-value catalysts
            if any(word in title for word in ['fda', 'approval', 'approved']):
                score = 30
                catalyst_type = "FDA/Regulatory"
                break
            elif any(word in title for word in ['earnings', 'beat', 'revenue']):
                score = 25
                catalyst_type = "Earnings"
                break
            elif any(word in title for word in ['contract', 'partnership', 'deal', 'agreement']):
                score = 20
                catalyst_type = "Contract/Partnership"
                break
            elif any(word in title for word in ['insider', 'buying', 'purchase']):
                score = 15
                catalyst_type = "Insider buying"
                break
        
        if score == 0:
            score = 10  # Generic recent news
        
        latest_title = news_items[0].title[:60]
        return score, f"{catalyst_type}: {latest_title}"
        
    except:
        return 0, "Error checking news"

def check_early_momentum(price, prev_close):
    """
    Look for 0-5% moves (BEFORE big breakout, not after)
    Returns: (momentum_score, description)
    """
    if prev_close == 0:
        return 0, "No previous close"
    
    change_pct = ((price - prev_close) / prev_close) * 100
    
    # Score EARLY moves higher (this is the key insight)
    if 0 <= change_pct <= 3:
        return 15, f"✅ EARLY: +{change_pct:.1f}% (pre-breakout)"
    elif 3 < change_pct <= 5:
        return 12, f"✅ Starting: +{change_pct:.1f}%"
    elif 5 < change_pct <= 8:
        return 8, f"⚠️  Moving: +{change_pct:.1f}%"
    elif change_pct > 8:
        return 3, f"❌ Late: +{change_pct:.1f}% (already moving)"
    elif change_pct < 0:
        return 0, f"❌ Down: {change_pct:.1f}%"
    
    return 0, "No momentum"

def scan_for_diamonds():
    """
    Main scanner - finds diamonds BEFORE they explode
    """
    print("=" * 80)
    print("DIAMOND SCANNER - Pre-Breakout Detection")
    print(f"{datetime.now().strftime('%I:%M %p PT')}")
    print("=" * 80)
    print()
    
    # Phase 1: Get market snapshots
    print("📡 Phase 1: Scanning market snapshots...")
    response = client.get_snapshot_all("stocks")
    
    # Filter for price/volume only (low threshold to catch early)
    candidates = []
    
    for snap in response:
        try:
            if not snap.day or not snap.day.close or not snap.day.volume:
                continue
            
            symbol = snap.ticker
            price = snap.day.close
            volume = snap.day.volume
            
            # Skip ETFs/funds
            if any(x in symbol for x in ['-', '.', 'ETF', 'FUND']):
                continue
            
            # Loose filters (catch early)
            if 0.50 <= price <= 100 and volume >= 500_000:  # Lower volume threshold
                prev_close = snap.prev_day.close if snap.prev_day and hasattr(snap.prev_day, 'close') else price
                
                candidates.append({
                    'symbol': symbol,
                    'price': price,
                    'volume': volume,
                    'prev_close': prev_close
                })
        except:
            continue
    
    print(f"✅ Found {len(candidates)} stocks passing initial filters")
    print(f"   (Price $0.50-$100, Volume >500K)\n")
    
    # Phase 2-4: Deep analysis on top volume stocks
    print("📊 Phase 2-4: Deep analysis...")
    print("   • Volume acceleration detection")
    print("   • Float + squeeze setup analysis")
    print("   • Fresh catalyst detection")
    print("   • Early momentum scoring\n")
    
    # Sort by volume, analyze top 50
    candidates.sort(key=lambda x: x['volume'], reverse=True)
    
    diamonds = []
    
    for i, stock in enumerate(candidates[:50], 1):
        symbol = stock['symbol']
        
        if i % 10 == 0:
            print(f"   [{i}/50] Analyzed {len(diamonds)} potential diamonds...")
        
        try:
            # Volume acceleration
            vol_score, vol_pattern = detect_volume_acceleration(symbol)
            
            # Squeeze setup
            squeeze_score, squeeze_info = check_squeeze_setup(symbol)
            
            # Fresh catalyst
            catalyst_score, catalyst_info = check_fresh_catalyst(symbol)
            
            # Early momentum
            momentum_score, momentum_info = check_early_momentum(stock['price'], stock['prev_close'])
            
            # Calculate total score
            total_score = vol_score + squeeze_score + catalyst_score + momentum_score
            
            # Only save high-potential stocks
            if total_score >= 60:  # Lower threshold to catch more early signals
                diamonds.append({
                    'symbol': symbol,
                    'score': total_score,
                    'price': stock['price'],
                    'volume': stock['volume'],
                    'volume_score': vol_score,
                    'volume_pattern': vol_pattern,
                    'squeeze_score': squeeze_score,
                    'squeeze_info': squeeze_info,
                    'catalyst_score': catalyst_score,
                    'catalyst': catalyst_info,
                    'momentum_score': momentum_score,
                    'momentum': momentum_info
                })
            
            time.sleep(0.2)  # Rate limit
            
        except Exception as e:
            continue
    
    # Sort by score
    diamonds.sort(key=lambda x: x['score'], reverse=True)
    
    # Print results
    print("\n" + "=" * 80)
    print("💎 DIAMONDS FOUND")
    print("=" * 80)
    
    high_conviction = [d for d in diamonds if d['score'] >= 120]
    strong_watch = [d for d in diamonds if 100 <= d['score'] < 120]
    monitor = [d for d in diamonds if 60 <= d['score'] < 100]
    
    if high_conviction:
        print(f"\n🔥 HIGH CONVICTION (≥120): {len(high_conviction)} stocks")
        print("-" * 80)
        for d in high_conviction:
            print(f"\n*{d['symbol']}*: {d['score']}/200 points")
            print(f"   ${d['price']:.2f} | Volume: {d['volume']:,}")
            print(f"   🎯 Squeeze: {d['squeeze_score']} pts - {d['squeeze_info']}")
            print(f"   📈 Volume: {d['volume_score']} pts - {d['volume_pattern']}")
            print(f"   📰 Catalyst: {d['catalyst_score']} pts - {d['catalyst']}")
            print(f"   ⚡ Momentum: {d['momentum_score']} pts - {d['momentum']}")
    
    if strong_watch:
        print(f"\n👀 STRONG WATCH (100-119): {len(strong_watch)} stocks")
        print("-" * 80)
        for d in strong_watch[:10]:
            print(f"{d['symbol']}: {d['score']}/200 - ${d['price']:.2f}")
            print(f"   Float: {d['squeeze_info']}")
    
    if monitor:
        print(f"\n📋 MONITOR (60-99): {len(monitor)} stocks")
        print("-" * 80)
        for d in monitor[:5]:
            print(f"{d['symbol']}: {d['score']}/200 - ${d['price']:.2f}")
    
    if not diamonds:
        print("\n❌ No diamonds found meeting criteria")
        print("   Try again during market hours or adjust thresholds")
    
    print("\n" + "=" * 80)
    print(f"Scanned: {len(candidates)} stocks")
    print(f"Deep analyzed: 50 highest volume")
    print(f"Diamonds found: {len(diamonds)}")
    print(f"High conviction: {len(high_conviction)}")
    print("=" * 80)
    
    # Save
    os.makedirs('data', exist_ok=True)
    with open('data/diamonds.json', 'w') as f:
        json.dump(diamonds, f, indent=2)
    
    print("\n💾 Results saved to data/diamonds.json\n")
    
    return diamonds

if __name__ == '__main__':
    scan_for_diamonds()
