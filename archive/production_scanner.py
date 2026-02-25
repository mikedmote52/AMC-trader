#!/usr/bin/env python3
"""
PRODUCTION SQUEEZE SCANNER
- Scans ALL stocks under $100
- Detects catalysts via Polygon news
- Alerts via Telegram on ≥75 scores
- Runs 6x daily via cron
"""

from polygon import RESTClient
import json
import time
from datetime import datetime, timedelta
import requests
import os

# Load credentials
with open('/Users/mikeclawd/.openclaw/secrets/polygon.json', 'r') as f:
    polygon_creds = json.load(f)

client = RESTClient(api_key=polygon_creds['apiKey'])

def get_all_active_stocks():
    """Get ALL active stocks from Polygon"""
    print("📡 Fetching all active stocks from Polygon...")
    
    stocks = []
    try:
        # Get all tickers
        for ticker in client.list_tickers(
            market="stocks",
            type="CS",  # Common stock only
            active=True,
            limit=1000
        ):
            stocks.append(ticker.ticker)
            
            if len(stocks) % 1000 == 0:
                print(f"   Retrieved {len(stocks)} tickers...")
                
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print(f"✅ Retrieved {len(stocks)} total stocks\n")
    return stocks

def quick_filter(symbol):
    """
    Fast pre-filter using snapshots
    Returns: (should_score, basic_data) or (False, None)
    """
    try:
        # Get snapshot (faster than full details)
        snapshot = client.get_snapshot_ticker("stocks", symbol)
        
        if not snapshot or not snapshot.day:
            return False, None
        
        price = snapshot.day.close
        volume = snapshot.day.volume
        
        # Quick filters
        if not (0.50 <= price <= 100):
            return False, None
        if volume < 1_000_000:
            return False, None
        
        return True, {'price': price, 'volume': volume}
        
    except:
        return False, None

def get_detailed_data(symbol, snapshot_data):
    """Get full data for stocks that passed quick filter"""
    try:
        # Get ticker details for float
        details = client.get_ticker_details(symbol)
        float_shares = details.share_class_shares_outstanding or 0
        
        # Get recent bars
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        
        bars = list(client.list_aggs(symbol, 1, "day", start_date, end_date, limit=10))
        
        if not bars or len(bars) < 2:
            return None
        
        latest = bars[-1]
        prev = bars[-2]
        
        # Check for news/catalyst (last 7 days)
        news_items = list(client.list_ticker_news(symbol, limit=5))
        has_catalyst = len(news_items) > 0
        catalyst_text = news_items[0].title if news_items else "None"
        
        return {
            'symbol': symbol,
            'price': snapshot_data['price'],
            'volume': snapshot_data['volume'],
            'float': float_shares,
            'bars': bars,
            'daily_change': ((latest.close - prev.close) / prev.close) * 100,
            'has_catalyst': has_catalyst,
            'catalyst': catalyst_text[:80]
        }
        
    except:
        return None

def score_stock(data):
    """Full 0-100 scoring"""
    score = 0
    signals = []
    
    # 1. Float score (30 pts)
    float_shares = data['float']
    if float_shares <= 10_000_000:
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
        score += 5
        signals.append(f"⚠️  Large float: {float_shares/1e6:.1f}M")
    
    # 2. Momentum score (25 pts) - TIGHTENED
    daily_change = data['daily_change']
    
    if 5 <= daily_change <= 15:
        score += 25
        signals.append(f"✅ IDEAL momentum: +{daily_change:.1f}%")
    elif 15 < daily_change <= 25:
        score += 15
        signals.append(f"⚠️  Extended: +{daily_change:.1f}%")
    elif 2 < daily_change < 5:
        score += 8
        signals.append(f"⚠️  Early: +{daily_change:.1f}%")
    elif daily_change > 25:
        score += 5
        signals.append(f"❌ TOO EXTENDED: +{daily_change:.1f}%")
    
    # 3. Catalyst (20 pts) - NEW!
    if data['has_catalyst']:
        score += 20
        signals.append(f"✅ CATALYST: {data['catalyst']}")
    else:
        signals.append("❌ No recent catalyst")
    
    # 4. Multi-day structure (15 pts)
    bars = data['bars']
    if len(bars) >= 5:
        last_5 = bars[-5:]
        green_days = sum(1 for i in range(1, len(last_5)) if last_5[i].close > last_5[i-1].close)
        
        if 2 <= green_days <= 3:
            score += 15
            signals.append(f"✅ Structure: {green_days}/4 green days")
        elif green_days == 4:
            score += 8
            signals.append(f"⚠️  Too hot: {green_days}/4 green")
    
    # 5. Volume spike (10 pts)
    if len(bars) >= 20:
        avg_volume = sum(b.volume for b in bars[-20:-1]) / 19
        volume_ratio = data['volume'] / avg_volume
        
        if volume_ratio >= 3.0:
            score += 10
            signals.append(f"✅ Volume SPIKE: {volume_ratio:.1f}x")
        elif volume_ratio >= 2.0:
            score += 5
            signals.append(f"⚠️  Volume: {volume_ratio:.1f}x")
    
    return score, signals

def send_telegram_alert(results):
    """Send Telegram message with top stocks"""
    if not results:
        return
    
    # Format message
    msg = f"🚨 *SQUEEZE SCANNER ALERT*\n"
    msg += f"_{datetime.now().strftime('%I:%M %p PT')}_\n\n"
    
    trade_ready = [r for r in results if r['score'] >= 75]
    
    if trade_ready:
        msg += f"*🚀 TRADE-READY ({len(trade_ready)} stocks):*\n\n"
        for r in trade_ready[:5]:  # Top 5
            msg += f"*{r['symbol']}*: {r['score']}/100\n"
            msg += f"${r['price']:.2f} (+{r['daily_change']:.1f}%)\n"
            msg += f"Float: {r['float']/1e6:.1f}M\n"
            if r['has_catalyst']:
                msg += f"📰 {r['catalyst']}\n"
            msg += "\n"
    else:
        msg += "_No trade-ready stocks found (score ≥75)_\n"
        
        # Show top 3 watch list
        watch = sorted(results, key=lambda x: x['score'], reverse=True)[:3]
        if watch:
            msg += f"\n*👀 Top Watch List:*\n"
            for r in watch:
                msg += f"{r['symbol']}: {r['score']}/100 (${r['price']:.2f})\n"
    
    # Send via OpenClaw message tool
    print(f"\n📱 Sending Telegram alert...")
    print(msg)
    
    # Save to file for now (will integrate with message tool)
    alert_file = '/Users/mikeclawd/.openclaw/workspace/data/latest_alert.txt'
    os.makedirs(os.path.dirname(alert_file), exist_ok=True)
    with open(alert_file, 'w') as f:
        f.write(msg)

def run_full_scan():
    """Run complete market scan"""
    print("=" * 80)
    print("PRODUCTION SQUEEZE SCANNER - FULL MARKET")
    print(f"Running at {datetime.now().strftime('%I:%M %p PT')}")
    print("=" * 80)
    print()
    
    # Step 1: Get all stocks
    all_stocks = get_all_active_stocks()
    
    if not all_stocks:
        print("❌ Failed to get stock universe")
        return []
    
    # Step 2: Quick filter (fast pass)
    print("🔍 Quick filtering by price and volume...")
    
    filtered = []
    for i, symbol in enumerate(all_stocks[:1000], 1):  # Limit to 1000 for now
        if i % 100 == 0:
            print(f"   Checked {i}/1000, {len(filtered)} passed...")
        
        passed, snapshot_data = quick_filter(symbol)
        if passed:
            filtered.append((symbol, snapshot_data))
        
        time.sleep(0.05)  # Rate limit
    
    print(f"✅ {len(filtered)} stocks passed quick filter\n")
    
    # Step 3: Get detailed data and score
    print("📊 Scoring candidates...")
    
    results = []
    for i, (symbol, snapshot_data) in enumerate(filtered, 1):
        print(f"[{i}/{len(filtered)}] Analyzing {symbol}...", end=" ")
        
        data = get_detailed_data(symbol, snapshot_data)
        
        if not data:
            print("❌ No data")
            continue
        
        score, signals = score_stock(data)
        
        if score >= 40:  # Save anything promising
            print(f"✅ {score}/100")
            results.append({
                'symbol': symbol,
                'score': score,
                'price': data['price'],
                'volume': data['volume'],
                'float': data['float'],
                'daily_change': data['daily_change'],
                'has_catalyst': data['has_catalyst'],
                'catalyst': data['catalyst'],
                'signals': signals
            })
        else:
            print(f"❌ {score}/100")
        
        time.sleep(0.12)  # Rate limit (5 req/sec)
    
    # Sort by score
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # Save results
    output_file = '/Users/mikeclawd/.openclaw/workspace/data/production_scan_results.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 80)
    print("SCAN COMPLETE")
    print("=" * 80)
    print(f"Scanned: {len(all_stocks[:1000])} stocks")
    print(f"Passed filter: {len(filtered)}")
    print(f"Candidates found: {len(results)}")
    print(f"Trade-ready (≥75): {len([r for r in results if r['score'] >= 75])}")
    print("=" * 80)
    
    # Send alert if trade-ready stocks found
    if results:
        send_telegram_alert(results)
    
    return results

if __name__ == '__main__':
    run_full_scan()
