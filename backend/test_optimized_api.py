#!/usr/bin/env python3
import asyncio
import httpx
from datetime import datetime, timedelta
import os

async def test_optimized_approach():
    api_key = os.getenv('POLYGON_API_KEY', '1ORwpSzeOV20X6uaA8G3Zuxx7hLJ0KIC')
    print('🔍 Testing optimized universe collection approach')

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get yesterday's date (markets closed on weekends)
        today = datetime.now()
        if today.weekday() == 0:  # Monday
            market_day = today - timedelta(days=3)  # Get Friday
        elif today.weekday() == 6:  # Sunday
            market_day = today - timedelta(days=2)  # Get Friday
        else:
            market_day = today - timedelta(days=1)  # Get previous day

        date_str = market_day.strftime('%Y-%m-%d')

        # Use grouped daily bars - gets ALL stocks in one call but with less data
        grouped_url = f'https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/{date_str}'

        response = await client.get(grouped_url, params={
            'apikey': api_key,
            'adjusted': 'true'
        })

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f'Grouped daily bars returned: {len(results)} stocks for {date_str}')

            # Filter to our criteria
            active_stocks = []
            for stock in results:
                ticker = stock.get('T', '')
                close_price = stock.get('c', 0)
                volume = stock.get('v', 0)
                open_price = stock.get('o', 0)

                # Calculate daily change
                if open_price > 0:
                    daily_change = ((close_price - open_price) / open_price) * 100
                else:
                    daily_change = 0

                # Apply our filters for pre-explosive detection
                if (0.50 <= close_price <= 100.0 and
                    volume > 500000 and  # Min 500K volume (adjustable)
                    not any(x in ticker for x in ['.', 'W'])):  # Skip ETFs/special tickers

                    active_stocks.append({
                        'ticker': ticker,
                        'price': close_price,
                        'volume': volume,
                        'change': daily_change
                    })

            # Sort by volume descending to focus on most active
            active_stocks.sort(key=lambda x: x['volume'], reverse=True)

            print(f'\n📊 OPTIMIZATION RESULTS:')
            print(f'   Raw stocks from API: {len(results)}')
            print(f'   After price/volume filter: {len(active_stocks)}')
            print(f'   Reduction: {100 - (len(active_stocks)/len(results)*100):.1f}%')

            print(f'\n🎯 Top 10 High-Volume Candidates (for deeper analysis):')
            for i, stock in enumerate(active_stocks[:10], 1):
                print(f"   {i}. {stock['ticker']}: ${stock['price']:.2f} | Vol: {stock['volume']:,} | Δ: {stock['change']:+.1f}%")

            # Now we would enrich only these top candidates with real-time data
            print(f'\n💡 STRATEGY: Instead of processing {len(results)} stocks,')
            print(f'   we can focus enrichment on top {min(100, len(active_stocks))} candidates')
            print(f'   This reduces API calls by ~{100 - (min(100, len(active_stocks))/len(results)*100):.0f}%')

        else:
            print(f'Error: {response.status_code}')
            print(response.text)

if __name__ == "__main__":
    asyncio.run(test_optimized_approach())