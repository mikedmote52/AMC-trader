#!/usr/bin/env python3
"""
Generate Full Stock Universe from Polygon API
Creates a comprehensive universe file with all tradeable US stocks for discovery.
"""

import os
import sys
import requests
import time
from typing import List

def generate_full_universe(api_key: str, output_file: str = "data/universe.txt") -> None:
    """Generate full stock universe from Polygon API"""
    
    if not api_key:
        print("Error: POLYGON_API_KEY required")
        sys.exit(1)
    
    all_stocks = []
    next_url = None
    page = 1
    
    print("🔍 Fetching full stock universe from Polygon API...")
    
    while True:
        try:
            # Build API URL
            if next_url:
                url = f"https://api.polygon.io/v3/reference/tickers?apikey={api_key}&cursor={next_url}"
            else:
                # Get ALL US stocks, exclude ETFs for now to focus on individual companies
                url = f"https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&limit=1000&apikey={api_key}"
            
            print(f"📡 Fetching page {page}...")
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Extract stock tickers
            results = data.get('results', [])
            for stock in results:
                ticker = stock.get('ticker')
                stock_type = stock.get('type', '')
                primary_exchange = stock.get('primary_exchange', '')
                
                # Filter for common stocks on major exchanges
                if (ticker and 
                    stock_type in ['CS'] and  # Common Stock
                    primary_exchange in ['XNYS', 'XNAS', 'ARCX', 'BATS'] and  # Major exchanges
                    len(ticker) <= 5 and  # Reasonable ticker length
                    ticker.isalpha()):  # Letters only, no special characters
                    
                    all_stocks.append(ticker)
            
            print(f"📊 Found {len(results)} stocks on page {page}, total collected: {len(all_stocks)}")
            
            # Check if there's a next page
            next_url = data.get('next_url')
            if not next_url:
                break
                
            page += 1
            time.sleep(0.1)  # Rate limiting
            
        except requests.exceptions.RequestException as e:
            print(f"❌ API request failed: {e}")
            break
        except Exception as e:
            print(f"❌ Error processing data: {e}")
            break
    
    # Sort and deduplicate
    unique_stocks = sorted(list(set(all_stocks)))
    print(f"✅ Total unique stocks found: {len(unique_stocks)}")
    
    # Write to file
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w') as f:
            f.write("# Full US Stock Universe - Generated from Polygon API\n")
            f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total Symbols: {len(unique_stocks)}\n")
            f.write("# Criteria: Common stocks on major US exchanges (NYSE, NASDAQ, ARCA, BATS)\n\n")
            
            for ticker in unique_stocks:
                f.write(f"{ticker}\n")
        
        print(f"💾 Universe file written to: {output_file}")
        print(f"📈 Ready for full market discovery with {len(unique_stocks)} stocks!")
        
    except Exception as e:
        print(f"❌ Failed to write universe file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        print("❌ POLYGON_API_KEY environment variable required")
        print("💡 Export your Polygon API key: export POLYGON_API_KEY=your_key_here")
        sys.exit(1)
    
    generate_full_universe(api_key)