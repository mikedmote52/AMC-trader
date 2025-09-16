#!/usr/bin/env python3
"""
Real-time market analysis showing which stocks would pass the unified discovery filters
"""

# Current market data from MCP
current_gainers = [
    {"ticker": "CHEK", "todaysChangePerc": 231.16, "day": {"c": 2.12, "v": 129607368.0}, "prevDay": {"v": 20443257.0}},
    {"ticker": "HSDT", "todaysChangePerc": 155.69, "day": {"c": 18.27, "v": 20034254.0}, "prevDay": {"v": 187517.0}},
    {"ticker": "ATCH", "todaysChangePerc": 153.85, "day": {"c": 0.99, "v": 498098307.0}, "prevDay": {"v": 281071801.0}},
    {"ticker": "WLACW", "todaysChangePerc": 112.10, "day": {"c": 0.25, "v": 43838}, "prevDay": {"v": 9397}},
    {"ticker": "MTVA", "todaysChangePerc": 102.63, "day": {"c": 1.50, "v": 90297146.0}, "prevDay": {"v": 29031}},
    {"ticker": "WBTN", "todaysChangePerc": 66.36, "day": {"c": 14.96, "v": 4356867.0}, "prevDay": {"v": 462334}},
    {"ticker": "IHT", "todaysChangePerc": 66.00, "day": {"c": 3.32, "v": 28911283.0}, "prevDay": {"v": 747526}},
    {"ticker": "OPI", "todaysChangePerc": 59.60, "day": {"c": 0.88, "v": 151435735.0}, "prevDay": {"v": 329776544.0}},
    {"ticker": "LVROW", "todaysChangePerc": 58.73, "day": {"c": 0.0378, "v": 14075}, "prevDay": {"v": 300}},
    {"ticker": "LVRO", "todaysChangePerc": 58.46, "day": {"c": 1.40, "v": 959565}, "prevDay": {"v": 9152}},
    {"ticker": "ADAP", "todaysChangePerc": 55.18, "day": {"c": 0.0666, "v": 93327079.0}, "prevDay": {"v": 66422794.0}},
    {"ticker": "NAOV", "todaysChangePerc": 51.00, "day": {"c": 10.70, "v": 55313931.0}, "prevDay": {"v": 14709}},
    {"ticker": "SQFTW", "todaysChangePerc": 50.91, "day": {"c": 0.0495, "v": 63480}, "prevDay": {"v": 3045}},
    {"ticker": "RCEL", "todaysChangePerc": 44.74, "day": {"c": 6.76, "v": 19595584.0}, "prevDay": {"v": 293334}},
    {"ticker": "LRE", "todaysChangePerc": 42.26, "day": {"c": 2.15, "v": 42562330.0}, "prevDay": {"v": 61065}},
    {"ticker": "BLNE", "todaysChangePerc": 40.80, "day": {"c": 3.41, "v": 5494115.0}, "prevDay": {"v": 1765140.0}},
    {"ticker": "NFE", "todaysChangePerc": 38.17, "day": {"c": 1.38, "v": 12423695.0}, "prevDay": {"v": 9066110.0}},
    {"ticker": "SOCAW", "todaysChangePerc": 38.15, "day": {"c": 0.235, "v": 18742}, "prevDay": {"v": 247}},
    {"ticker": "CCCC", "todaysChangePerc": 37.22, "day": {"c": 3.57, "v": 8094169.0}, "prevDay": {"v": 484762}},
    {"ticker": "GLUE", "todaysChangePerc": 37.19, "day": {"c": 6.93, "v": 31708353.0}, "prevDay": {"v": 309332}},
    {"ticker": "CNFR", "todaysChangePerc": 33.88, "day": {"c": 1.13, "v": 1734735.0}, "prevDay": {"v": 544210}}
]

def analyze_market_with_filters():
    print("🔍 AMC-TRADER UNIFIED DISCOVERY - REAL MARKET ANALYSIS")
    print("=" * 70)
    print("Filter Settings:")
    print("- Max Daily Move: 20%")
    print("- Volume Ratio: 2-15x")
    print("- Price Range: $0.50-$50.00")
    print()

    # Filter settings
    MAX_DAILY_MOVE = 20.0
    MIN_VOLUME_RATIO = 2.0
    MAX_VOLUME_RATIO = 15.0
    MIN_PRICE = 0.50
    MAX_PRICE = 50.00

    print("📊 FILTER ANALYSIS")
    print("-" * 50)

    passed_candidates = []
    filter_stats = {
        'post_explosion': 0,
        'volume_explosion': 0,
        'price_too_high': 0,
        'price_too_low': 0,
        'insufficient_volume': 0,
        'passed': 0
    }

    for candidate in current_gainers:
        symbol = candidate['ticker']
        daily_change = abs(candidate['todaysChangePerc'])
        price = candidate['day']['c']
        volume = candidate['day']['v']
        prev_volume = candidate['prevDay']['v']
        volume_ratio = volume / max(prev_volume, 1)

        # Apply filters
        if daily_change > MAX_DAILY_MOVE:
            filter_stats['post_explosion'] += 1
            status = f"❌ POST-EXPLOSION: {daily_change:.1f}% move"
        elif volume_ratio > MAX_VOLUME_RATIO:
            filter_stats['volume_explosion'] += 1
            status = f"❌ VOLUME-EXPLOSION: {volume_ratio:.1f}x volume"
        elif price > MAX_PRICE:
            filter_stats['price_too_high'] += 1
            status = f"❌ PRICE-TOO-HIGH: ${price:.2f}"
        elif price < MIN_PRICE:
            filter_stats['price_too_low'] += 1
            status = f"❌ PRICE-TOO-LOW: ${price:.3f}"
        elif volume_ratio < MIN_VOLUME_RATIO:
            filter_stats['insufficient_volume'] += 1
            status = f"❌ INSUFFICIENT-VOLUME: {volume_ratio:.1f}x"
        else:
            filter_stats['passed'] += 1
            status = f"✅ PASSED: {daily_change:.1f}% | {volume_ratio:.1f}x vol | ${price:.2f}"

            # Calculate score
            candidate['volume_ratio'] = volume_ratio
            candidate['filter_score'] = calculate_score(candidate)
            passed_candidates.append(candidate)

        print(f"{symbol:8} {status}")

    print()
    print("📈 FILTER SUMMARY")
    print("-" * 30)
    print(f"Total analyzed: {len(current_gainers)}")
    print(f"Post-explosion: {filter_stats['post_explosion']}")
    print(f"Volume-explosion: {filter_stats['volume_explosion']}")
    print(f"Price too high: {filter_stats['price_too_high']}")
    print(f"Price too low: {filter_stats['price_too_low']}")
    print(f"Insufficient volume: {filter_stats['insufficient_volume']}")
    print(f"✅ PASSED FILTERS: {filter_stats['passed']}")
    print()

    if passed_candidates:
        print("🎯 QUALIFIED OPPORTUNITIES")
        print("-" * 40)

        # Sort by score
        passed_candidates.sort(key=lambda x: x.get('filter_score', 0), reverse=True)

        for i, candidate in enumerate(passed_candidates, 1):
            symbol = candidate['ticker']
            score = candidate.get('filter_score', 0)
            change = candidate['todaysChangePerc']
            price = candidate['day']['c']
            vol_ratio = candidate.get('volume_ratio', 0)

            if score >= 0.7:
                action = "🟢 TRADE-READY"
            elif score >= 0.4:
                action = "🟡 WATCHLIST"
            else:
                action = "⚪ MONITOR"

            print(f"{i}. {symbol}")
            print(f"   {action} | Score: {score:.3f}")
            print(f"   Move: {change:.1f}% | Price: ${price:.2f} | Volume: {vol_ratio:.1f}x")
            print()
    else:
        print("⚠️ NO OPPORTUNITIES FOUND")
        print()
        print("📋 CURRENT MARKET STATUS:")
        print("- Market in extreme volatility phase")
        print("- All major movers already post-explosion")
        print("- System correctly filtering out late entries")
        print()
        print("💡 ACTIONABLE INSIGHTS:")
        print("1. Run discovery earlier in trading session (9:30-11:00 AM)")
        print("2. Look for 5-15% movers, not 50%+ movers")
        print("3. Monitor for pre-market unusual activity")
        print("4. Current setup is working - preventing bad entries")

    return passed_candidates

def calculate_score(ticker):
    """Calculate opportunity score"""
    daily_change = abs(ticker.get('todaysChangePerc', 0))
    volume_ratio = ticker.get('volume_ratio', 1)
    price = ticker.get('day', {}).get('c', 0)

    # Ideal ranges
    if 5 <= daily_change <= 15:
        move_score = 1.0
    elif daily_change < 5:
        move_score = daily_change / 5.0
    else:
        move_score = max(0, (20 - daily_change) / 5.0)

    if 3 <= volume_ratio <= 8:
        volume_score = 1.0
    elif volume_ratio < 3:
        volume_score = volume_ratio / 3.0
    else:
        volume_score = max(0, (15 - volume_ratio) / 7.0)

    if 2 <= price <= 20:
        price_score = 1.0
    elif price < 2:
        price_score = price / 2.0
    else:
        price_score = max(0, (50 - price) / 30.0)

    return round((move_score * 0.4) + (volume_score * 0.4) + (price_score * 0.2), 3)

if __name__ == "__main__":
    analyze_market_with_filters()