#!/usr/bin/env python3
"""
SMART SQUEEZE SCANNER - Pre-filtered approach
Uses Polygon's bulk snapshot API to filter 7,000 stocks in seconds
Then only analyzes stocks that pass initial criteria

10x faster than checking each stock individually
"""

from polygon import RESTClient
import json
import time
from datetime import datetime, timedelta
import os

# Load credentials
with open('/Users/mikeclawd/.openclaw/secrets/polygon.json', 'r') as f:
    creds = json.load(f)

client = RESTClient(api_key=creds['apiKey'])

def get_filtered_universe():
    """
    Step 1: Get ALL stock snapshots in one API call
    Step 2: Filter in-memory (lightning fast)
    Returns: List of symbols that pass initial filters
    """
    print("=" * 80)
    print("SMART SCANNER - PRE-FILTERING APPROACH")
    print(f"Running at {datetime.now().strftime('%I:%M %p PT')}")
    print("=" * 80)
    print()
    
    print("📡 Fetching ALL stock snapshots from Polygon...")
    print("   (This gets price/volume for 7,000+ stocks in one API call)\n")
    
    try:
        # Get all snapshots at once
        response = client.get_snapshot_all("stocks")
        
        # Handle different response formats
        if hasattr(response, 'tickers'):
            all_snapshots = response.tickers
        elif isinstance(response, list):
            all_snapshots = response
        else:
            print(f"❌ Unexpected response type: {type(response)}")
            return []
        
        print(f"✅ Retrieved snapshots for {len(all_snapshots)} stocks\n")
        
        # Filter in-memory (FAST!)
        print("🔍 Applying filters:")
        print("   • Type: Common stock only (no ETFs/funds)")
        print("   • Price: $0.50 - $100")
        print("   • Volume: ≥ 1M shares\n")
        
        filtered = []
        
        for snapshot in all_snapshots:
            try:
                symbol = snapshot.ticker
                
                # Skip funds/ETFs (basic check)
                if any(x in symbol for x in ['ETF', 'FUND', '-', '.']):
                    continue
                
                # Check if we have day data
                if not snapshot.day:
                    continue
                
                price = snapshot.day.close  # close price
                volume = snapshot.day.volume  # volume
                
                # Apply filters
                if 0.50 <= price <= 100 and volume >= 1_000_000:
                    filtered.append({
                        'symbol': symbol,
                        'price': price,
                        'volume': volume,
                        'prev_close': snapshot.prev_day.close if (snapshot.prev_day and hasattr(snapshot.prev_day, 'close')) else price,
                    })
            
            except (AttributeError, TypeError):
                continue
        
        print(f"✅ {len(filtered)} stocks passed initial filters\n")
        
        # Sort by volume (highest first - usually most active)
        filtered.sort(key=lambda x: x['volume'], reverse=True)
        
        return filtered
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_float_and_news(symbol):
    """Get float data and recent news for a stock"""
    try:
        # Get ticker details
        details = client.get_ticker_details(symbol)
        float_shares = details.share_class_shares_outstanding or 0
        
        # Get recent news
        news = list(client.list_ticker_news(symbol, limit=3))
        has_catalyst = len(news) > 0
        catalyst_text = news[0].title if news else "None"
        
        return float_shares, has_catalyst, catalyst_text[:80]
        
    except:
        return 0, False, "None"

def get_historical_bars(symbol, days=10):
    """Get recent bars for multi-day analysis"""
    try:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days+5)).strftime("%Y-%m-%d")
        
        bars = list(client.list_aggs(symbol, 1, "day", start_date, end_date, limit=days))
        return bars
        
    except:
        return []

def score_stock(symbol, price, volume, prev_close):
    """
    Full scoring with all data
    Returns: (score, signals, data_dict)
    """
    score = 0
    signals = []
    
    # Calculate daily change
    daily_change = ((price - prev_close) / prev_close) * 100 if prev_close > 0 else 0
    
    # Get float and news
    float_shares, has_catalyst, catalyst = get_float_and_news(symbol)
    
    # 1. Float score (30 pts)
    if float_shares == 0:
        signals.append("❌ No float data")
    elif float_shares <= 10_000_000:
        score += 30
        signals.append(f"✅ ULTRA-LOW float: {float_shares/1e6:.1f}M")
    elif float_shares <= 30_000_000:
        score += 25
        signals.append(f"✅ Low float: {float_shares/1e6:.1f}M")
    elif float_shares <= 50_000_000:
        score += 20
        signals.append(f"✅ Float: {float_shares/1e6:.1f}M")
    elif float_shares <= 100_000_000:
        score += 10
        signals.append(f"⚠️  Med float: {float_shares/1e6:.1f}M")
    else:
        score += 5
        signals.append(f"⚠️  Large float: {float_shares/1e6:.1f}M")
    
    # 2. Momentum score (25 pts) - STRICT
    if 5 <= daily_change <= 15:
        score += 25
        signals.append(f"✅ IDEAL: +{daily_change:.1f}%")
    elif 15 < daily_change <= 25:
        score += 12
        signals.append(f"⚠️  Hot: +{daily_change:.1f}%")
    elif 2 < daily_change < 5:
        score += 8
        signals.append(f"⚠️  Early: +{daily_change:.1f}%")
    elif daily_change > 25:
        score += 3
        signals.append(f"❌ EXTENDED: +{daily_change:.1f}%")
    else:
        signals.append(f"❌ Weak: {daily_change:+.1f}%")
    
    # 3. Catalyst (20 pts)
    if has_catalyst:
        score += 20
        signals.append(f"✅ NEWS: {catalyst}")
    
    # 4. Get bars for structure/volume analysis
    bars = get_historical_bars(symbol)
    
    if len(bars) >= 5:
        # Multi-day structure (15 pts)
        last_5 = bars[-5:]
        green_days = sum(1 for i in range(1, len(last_5)) if last_5[i].close > last_5[i-1].close)
        
        if green_days == 3:
            score += 15
            signals.append(f"✅ Perfect structure: 3/4 green")
        elif green_days == 2:
            score += 12
            signals.append(f"✅ Good structure: 2/4 green")
        elif green_days == 4:
            score += 8
            signals.append(f"⚠️  Too hot: 4/4 green")
        
        # Volume spike (10 pts)
        if len(bars) >= 20:
            avg_volume = sum(b.volume for b in bars[-20:-1]) / 19
            volume_ratio = volume / avg_volume
            
            if volume_ratio >= 3.0:
                score += 10
                signals.append(f"✅ VOLUME SPIKE: {volume_ratio:.1f}x")
            elif volume_ratio >= 2.0:
                score += 6
                signals.append(f"✅ Volume: {volume_ratio:.1f}x")
    
    return score, signals, {
        'symbol': symbol,
        'price': price,
        'volume': volume,
        'float': float_shares,
        'daily_change': daily_change,
        'has_catalyst': has_catalyst,
        'catalyst': catalyst
    }

def run_smart_scan():
    """Main scan function"""
    
    # Step 1: Get pre-filtered universe (fast!)
    candidates = get_filtered_universe()
    
    if not candidates:
        print("❌ No stocks passed initial filter")
        return []
    
    # Step 2: Score top candidates by volume
    print(f"📊 Scoring top {min(200, len(candidates))} stocks by volume...")
    print("   (Only analyzing high-volume stocks for speed)\n")
    
    results = []
    
    for i, stock in enumerate(candidates[:200], 1):  # Top 200 by volume
        symbol = stock['symbol']
        
        if i % 10 == 0:
            print(f"   [{i}/200] Scored {len(results)} candidates so far...")
        
        score, signals, data = score_stock(
            symbol, 
            stock['price'], 
            stock['volume'], 
            stock['prev_close']
        )
        
        if score >= 40:  # Only save promising stocks
            data['score'] = score
            data['signals'] = signals
            results.append(data)
        
        time.sleep(0.2)  # Rate limit (5 req/sec)
    
    # Sort by score
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # Print results
    print("\n" + "=" * 80)
    print("SCAN RESULTS")
    print("=" * 80)
    
    trade_ready = [r for r in results if r['score'] >= 75]
    watch = [r for r in results if 60 <= r['score'] < 75]
    review = [r for r in results if 40 <= r['score'] < 60]
    
    if trade_ready:
        print(f"\n🚀 TRADE-READY (Score ≥75): {len(trade_ready)} stocks")
        print("-" * 80)
        for r in trade_ready:
            print(f"\n*{r['symbol']}*: {r['score']}/100 - ${r['price']:.2f} (+{r['daily_change']:.1f}%)")
            print(f"   Float: {r['float']/1e6:.1f}M | Volume: {r['volume']:,}")
            for signal in r['signals']:
                print(f"   {signal}")
    
    if watch:
        print(f"\n👀 WATCH LIST (60-74): {len(watch)} stocks")
        print("-" * 80)
        for r in watch[:10]:
            print(f"{r['symbol']}: {r['score']}/100 - ${r['price']:.2f} (+{r['daily_change']:.1f}%) - Float: {r['float']/1e6:.1f}M")
    
    if not trade_ready and not watch and review:
        print(f"\n📋 TOP REVIEW (40-59): {len(review)} stocks")
        print("-" * 80)
        for r in review[:5]:
            print(f"{r['symbol']}: {r['score']}/100 - ${r['price']:.2f} (+{r['daily_change']:.1f}%)")
    
    print("\n" + "=" * 80)
    print(f"Filtered: {len(candidates)} stocks")
    print(f"Analyzed: {min(200, len(candidates))} high-volume stocks")
    print(f"Found: {len(results)} candidates (score ≥40)")
    print(f"Trade-ready: {len(trade_ready)} (score ≥75)")
    print("=" * 80)
    
    # Save results
    output_file = '/Users/mikeclawd/.openclaw/workspace/data/smart_scan_results.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to {output_file}\n")
    
    return results

if __name__ == '__main__':
    run_smart_scan()
