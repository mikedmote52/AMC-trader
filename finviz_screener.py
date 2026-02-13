#!/usr/bin/env python3
"""
FinViz-based stock screener for Squeeze Scanner
Scans ALL US stocks under $100 with volume and float criteria
"""

from finviz.screener import Screener
import time
from datetime import datetime

def get_squeeze_candidates():
    """
    Use FinViz screener to find ALL stocks matching squeeze criteria
    
    Filters match SQUEEZE_STRATEGY.md framework:
    1. Price: $0.50 - $100
    2. Volume: > 1M shares
    3. Float: < 50M (for small-cap squeezes)
    4. Market cap: Small/Mid cap preferred
    """
    
    print("=" * 80)
    print("FINVIZ SQUEEZE SCREENER")
    print(f"Running at {datetime.now().strftime('%I:%M %p PT')}")
    print("=" * 80)
    
    # FinViz filter syntax
    filters = [
        'sh_price_u100',        # Price under $100
        'sh_avgvol_o1000',      # Avg volume over 1M
        'sh_float_u50',         # Float under 50M (squeeze potential)
    ]
    
    print("\n🔍 Scanning with filters:")
    print("   • Price: Under $100")
    print("   • Avg Volume: Over 1M shares")
    print("   • Float: Under 50M shares")
    print("\nFetching results from FinViz...\n")
    
    try:
        # Create screener
        stock_list = Screener(filters=filters, table='Performance', order='price')
        
        # Get all results
        results = []
        for stock in stock_list.data:
            results.append({
                'Ticker': stock['Ticker'],
                'Price': float(stock['Price']) if stock['Price'] != '-' else 0,
                'Volume': stock.get('Volume', 'N/A'),
                'Float': stock.get('Shs Float', 'N/A'),
                'Change': stock.get('Change', 'N/A'),
                'Rel Volume': stock.get('Rel Volume', 'N/A'),
            })
        
        print(f"✅ Found {len(results)} stocks matching criteria\n")
        
        # Filter for price range $0.50 - $100
        filtered = [s for s in results if 0.50 <= s['Price'] <= 100]
        
        print("=" * 80)
        print(f"RESULTS: {len(filtered)} stocks under $100 with float < 50M")
        print("=" * 80)
        
        # Show top 20 by volume
        print("\nTop 20 by Price (showing volume leaders):")
        print("-" * 80)
        print(f"{'Ticker':<8} {'Price':<10} {'Change':<10} {'Volume':<15} {'Float':<12}")
        print("-" * 80)
        
        for stock in filtered[:20]:
            ticker = stock['Ticker']
            price = f"${stock['Price']:.2f}"
            change = stock['Change']
            volume = stock['Volume']
            float_shares = stock['Float']
            
            print(f"{ticker:<8} {price:<10} {change:<10} {volume:<15} {float_shares:<12}")
        
        if len(filtered) > 20:
            print(f"\n... and {len(filtered) - 20} more")
        
        print("=" * 80)
        
        # Save results to file
        output_file = '/Users/mikeclawd/.openclaw/workspace/data/finviz_universe.csv'
        import os
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w') as f:
            f.write("Ticker,Price,Change,Volume,Float\n")
            for stock in filtered:
                f.write(f"{stock['Ticker']},{stock['Price']},{stock['Change']},{stock['Volume']},{stock['Float']}\n")
        
        print(f"\n💾 Saved {len(filtered)} tickers to {output_file}")
        print("\nThese tickers will be used by squeeze_scanner.py for detailed analysis.")
        print("=" * 80)
        
        return [s['Ticker'] for s in filtered]
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nFinViz may be rate-limiting. Try again in a few minutes.")
        return []

if __name__ == '__main__':
    tickers = get_squeeze_candidates()
    print(f"\n📋 {len(tickers)} tickers ready for scanning:")
    print(", ".join(tickers[:30]))
    if len(tickers) > 30:
        print(f"... and {len(tickers) - 30} more")
