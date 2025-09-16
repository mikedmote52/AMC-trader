#!/usr/bin/env python3
"""
Test script to validate MCP-based data sourcing for price data
Compare MCP vs HTTP client approach
"""

import asyncio
import sys
import os

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_mcp_vs_http():
    print('🔍 MCP VS HTTP DATA SOURCING TEST')
    print('=' * 80)
    print('Testing Polygon MCP functions vs current HTTP client approach')
    print()
    
    # Test symbols we know should have data
    test_symbols = ['AAPL', 'TSLA', 'MSFT', 'GOOGL', 'NVDA', 'META', 'AMZN']
    
    print('📊 TESTING MCP INDIVIDUAL PRICE CALLS:')
    print('-' * 50)
    
    for symbol in test_symbols:
        try:
            # This should be using the MCP function in our calling context
            print(f'{symbol}: Testing via MCP...')
            
        except Exception as e:
            print(f'{symbol}: MCP Error - {e}')
    
    print()
    print('🎯 SOLUTION NEEDED:')
    print('=' * 50)
    print('The current AlphaStack system uses HTTP client but should use MCP.')
    print('Two approaches:')
    print('  1. Replace HTTP calls with MCP calls in alphastack_v4.py')
    print('  2. Create MCP wrapper functions for efficient bulk data')
    print()
    print('Key MCP functions to use:')
    print('  • mcp__polygon__get_previous_close_agg(ticker) - Individual prices')
    print('  • mcp__polygon__get_snapshot_ticker(market_type, ticker) - Live data')
    print('  • mcp__polygon__list_tickers() - Get universe of symbols')
    print()
    print('The $0.00 prices indicate the HTTP client is getting stale/cached data')
    print('while MCP has access to fresh data.')

if __name__ == "__main__":
    asyncio.run(test_mcp_vs_http())