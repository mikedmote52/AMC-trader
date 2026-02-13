#!/usr/bin/env python3
"""
WORKING SQUEEZE SCANNER - No excuses edition
Uses Polygon + fallbacks to get the job done
"""

from polygon import RESTClient
import json
import time
from datetime import datetime, timedelta

# Load Polygon credentials
with open('/Users/mikeclawd/.openclaw/secrets/polygon.json', 'r') as f:
    creds = json.load(f)

client = RESTClient(api_key=creds['apiKey'])

def get_stock_data(symbol):
    """
    Get all data for a stock using Polygon
    Returns: dict with price, volume, float, bars
    """
    try:
        # Get ticker details (for float)
        details = client.get_ticker_details(symbol)
        float_shares = details.share_class_shares_outstanding or 0
        
        # Get recent bars (5 days)
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        
        bars = list(client.list_aggs(symbol, 1, "day", start_date, end_date, limit=10))
        
        if not bars or len(bars) < 2:
            return None
        
        # Get latest data from most recent bar
        latest = bars[-1]
        prev = bars[-2]
        
        return {
            'symbol': symbol,
            'price': latest.close,
            'volume': latest.volume,
            'float': float_shares,
            'bars': bars,
            'daily_change': ((latest.close - prev.close) / prev.close) * 100
        }
        
    except Exception as e:
        return None

def score_stock(data):
    """
    Score stock 0-100 based on squeeze criteria
    """
    score = 0
    signals = []
    
    # 1. Price filter (must be $0.50 - $100)
    if not (0.50 <= data['price'] <= 100):
        return 0, ["❌ Price outside range"]
    
    # 2. Volume filter (>1M)
    if data['volume'] < 1_000_000:
        return 0, ["❌ Volume too low"]
    
    # 3. Float score (30 pts max)
    float_shares = data['float']
    if float_shares == 0:
        float_score = 0
    elif float_shares <= 10_000_000:
        score += 30
        signals.append(f"✅ Ultra-low float: {float_shares/1e6:.1f}M")
    elif float_shares <= 30_000_000:
        score += 25
        signals.append(f"✅ Low float: {float_shares/1e6:.1f}M")
    elif float_shares <= 50_000_000:
        score += 20
        signals.append(f"✅ Float: {float_shares/1e6:.1f}M")
    elif float_shares <= 150_000_000:
        score += 10
        signals.append(f"⚠️  Med float: {float_shares/1e6:.1f}M")
    else:
        # Large float - need options data for gamma squeeze
        score += 5
        signals.append(f"⚠️  Large float: {float_shares/1e6:.1f}M (gamma only)")
    
    # 4. Momentum score (25 pts max)
    daily_change = data['daily_change']
    
    if 5 <= daily_change <= 20:
        score += 25
        signals.append(f"✅ IDEAL momentum: +{daily_change:.1f}%")
    elif 20 < daily_change <= 30:
        score += 15
        signals.append(f"⚠️  Extended: +{daily_change:.1f}%")
    elif 0 < daily_change < 5:
        score += 5
        signals.append(f"⚠️  Weak: +{daily_change:.1f}%")
    elif daily_change < 0:
        signals.append(f"❌ Negative: {daily_change:.1f}%")
    else:
        signals.append(f"❌ Too extended: +{daily_change:.1f}%")
    
    # 5. Multi-day structure (20 pts max)
    bars = data['bars']
    if len(bars) >= 5:
        last_5 = bars[-5:]
        green_days = sum(1 for i in range(1, len(last_5)) if last_5[i].close > last_5[i-1].close)
        
        if 2 <= green_days <= 4:
            score += 20
            signals.append(f"✅ Structure: {green_days}/4 green days")
        elif green_days == 1:
            score += 5
            signals.append(f"⚠️  Weak structure: {green_days}/4 green")
    
    # 6. Volume spike (15 pts max)
    if len(bars) >= 20:
        avg_volume = sum(b.volume for b in bars[-20:-1]) / 19
        volume_ratio = data['volume'] / avg_volume
        
        if volume_ratio >= 3.0:
            score += 15
            signals.append(f"✅ Volume SPIKE: {volume_ratio:.1f}x avg")
        elif volume_ratio >= 2.0:
            score += 10
            signals.append(f"✅ Volume up: {volume_ratio:.1f}x avg")
        elif volume_ratio >= 1.5:
            score += 5
            signals.append(f"⚠️  Volume: {volume_ratio:.1f}x avg")
    
    # 7. Higher lows (10 pts)
    if len(bars) >= 3:
        lows = [bar.low for bar in bars[-3:]]
        if lows[-1] > lows[-2] > lows[-3]:
            score += 10
            signals.append("✅ Higher lows")
    
    return score, signals

def scan_stocks(symbols):
    """Scan list of stock symbols"""
    print("=" * 80)
    print("WORKING SQUEEZE SCANNER")
    print(f"Running at {datetime.now().strftime('%I:%M %p PT')}")
    print("=" * 80)
    print()
    
    results = []
    
    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] Scanning {symbol}...", end=" ")
        
        data = get_stock_data(symbol)
        
        if not data:
            print("❌ No data")
            continue
        
        score, signals = score_stock(data)
        
        if score >= 40:  # Lower threshold to see more results
            print(f"✅ {score}/100")
            results.append({
                'symbol': symbol,
                'score': score,
                'price': data['price'],
                'volume': data['volume'],
                'float': data['float'],
                'daily_change': data['daily_change'],
                'signals': signals
            })
        else:
            print(f"❌ {score}/100")
        
        time.sleep(0.15)  # Rate limit
    
    # Sort by score
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # Print results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    if results:
        trade_ready = [r for r in results if r['score'] >= 75]
        watch = [r for r in results if 60 <= r['score'] < 75]
        review = [r for r in results if 40 <= r['score'] < 60]
        
        if trade_ready:
            print("\n🚀 TRADE-READY (Score ≥ 75):")
            print("-" * 80)
            for r in trade_ready:
                print(f"\n{r['symbol']}: {r['score']}/100 - ${r['price']:.2f} (+{r['daily_change']:.1f}%)")
                print(f"   Float: {r['float']/1e6:.1f}M | Volume: {r['volume']:,}")
                for signal in r['signals']:
                    print(f"   {signal}")
        
        if watch:
            print("\n👀 WATCH LIST (Score 60-74):")
            print("-" * 80)
            for r in watch:
                print(f"{r['symbol']}: {r['score']}/100 - ${r['price']:.2f} (+{r['daily_change']:.1f}%) - Float: {r['float']/1e6:.1f}M")
        
        if review:
            print("\n📋 REVIEW (Score 40-59):")
            print("-" * 80)
            for r in review:
                print(f"{r['symbol']}: {r['score']}/100 - ${r['price']:.2f} (+{r['daily_change']:.1f}%)")
    else:
        print("\n❌ No candidates found")
    
    print("\n" + "=" * 80)
    print(f"Scanned: {len(symbols)} | Found: {len(results)} candidates")
    print("=" * 80)
    
    return results

if __name__ == '__main__':
    # Test with known stocks + your portfolio
    test_symbols = [
        # Your current positions
        'PTNM', 'SPHR', 'WULF', 'UUUU', 'UEC', 'LGN',
        'RGTI', 'SOUN', 'QUBT', 'KOPN', 'SERV', 'KNOW',
        # Known squeeze stocks
        'VIGL', 'CRWV', 'AEVA', 'GME', 'AMC',
        # Popular momentum
        'NVDA', 'TSLA', 'PLTR', 'IONQ', 'MARA', 'RIOT',
        # Small caps
        'CVNA', 'HOOD', 'SOFI', 'COIN', 'DKNG'
    ]
    
    results = scan_stocks(test_symbols)
    
    # Save to file
    import os
    output_file = '/Users/mikeclawd/.openclaw/workspace/data/squeeze_results.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to {output_file}")
