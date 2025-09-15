#!/usr/bin/env python3
"""
Shares Outstanding data enrichment using Polygon MCP sidecar
"""
import os
from typing import List, Dict, Any, Optional
import asyncio

def calculate_shares_from_market_cap(market_cap: float, price: float) -> Optional[int]:
    """
    Calculate approximate shares outstanding from market cap and price
    
    Args:
        market_cap: Market capitalization in USD
        price: Current stock price
        
    Returns:
        Estimated shares outstanding
    """
    if not market_cap or not price or price <= 0:
        return None
    
    estimated_shares = int(market_cap / price)
    
    # Sanity check - typical range is 1M to 50B shares
    if 1_000_000 <= estimated_shares <= 50_000_000_000:
        return estimated_shares
    
    return None

def polygon_batch_financials(tickers: List[str], api_key: str = None) -> Dict[str, Dict]:
    """
    Fetch financial data from Polygon.io for multiple tickers
    
    Args:
        tickers: List of ticker symbols
        api_key: Polygon API key (will use env var if not provided)
        
    Returns:
        Dict mapping ticker to financial data
    """
    if not api_key:
        api_key = os.getenv('POLYGON_API_KEY')
    
    if not api_key:
        print("Warning: No Polygon API key available for shares outstanding lookup")
        return {}
    
    # For now, return empty dict - would implement actual Polygon API calls here
    # This is a placeholder for the actual implementation
    print(f"Would fetch financial data for {len(tickers)} tickers from Polygon API")
    return {}

def mcp_get_shares_outstanding(tickers: List[str]) -> Dict[str, Dict]:
    """
    Use MCP Polygon server to get shares outstanding data
    
    Args:
        tickers: List of ticker symbols
        
    Returns:
        Dict mapping ticker to shares data
    """
    try:
        # This would use the actual MCP polygon server if available
        # For now, return empty dict as placeholder
        print(f"Would fetch shares data for {len(tickers)} tickers via MCP")
        return {}
    except Exception as e:
        print(f"MCP shares lookup failed: {e}")
        return {}

def extract_shares_from_snapshot(stock: Dict[str, Any]) -> Optional[int]:
    """
    Extract shares outstanding from various stock data sources
    
    Args:
        stock: Stock dictionary with metadata
        
    Returns:
        Shares outstanding if found
    """
    meta = stock.get('meta', {})
    
    # Check multiple possible field names
    shares_fields = [
        'sharesOutstanding',
        'shares_outstanding', 
        'outstandingShares',
        'outstanding_shares',
        'weighted_shares_outstanding',
        'common_shares_outstanding'
    ]
    
    for field in shares_fields:
        shares = meta.get(field)
        if shares and isinstance(shares, (int, float)) and shares > 0:
            return int(shares)
    
    # Try to extract from Pydantic model attributes
    if hasattr(stock, 'shares_outstanding'):
        shares = stock.shares_outstanding
        if shares and shares > 0:
            return int(shares)
    
    return None

def estimate_shares_from_fundamentals(stock: Dict[str, Any]) -> Optional[int]:
    """
    Estimate shares outstanding from other fundamental data
    
    Args:
        stock: Stock dictionary with metadata
        
    Returns:
        Estimated shares outstanding
    """
    meta = stock.get('meta', {})
    
    # Method 1: Market cap / price
    market_cap = meta.get('marketCap') or meta.get('market_cap')
    price = meta.get('last') or meta.get('price')
    
    if hasattr(stock, 'price'):
        price = price or stock.price
    
    if market_cap and price:
        estimated = calculate_shares_from_market_cap(float(market_cap), float(price))
        if estimated:
            return estimated
    
    # Method 2: Enterprise value approach
    enterprise_value = meta.get('enterpriseValue') or meta.get('enterprise_value')
    if enterprise_value and price:
        # Rough approximation: EV ≈ market cap for many stocks
        estimated = calculate_shares_from_market_cap(float(enterprise_value), float(price))
        if estimated:
            return estimated
    
    # Method 3: Revenue per share approach (if available)
    revenue = meta.get('revenue') or meta.get('total_revenue')
    revenue_per_share = meta.get('revenuePerShare') or meta.get('revenue_per_share')
    
    if revenue and revenue_per_share and revenue_per_share > 0:
        estimated_shares = int(float(revenue) / float(revenue_per_share))
        if 1_000_000 <= estimated_shares <= 50_000_000_000:
            return estimated_shares
    
    return None

def assign_float_bucket(shares_outstanding: int) -> str:
    """
    Assign float size bucket based on shares outstanding
    
    Args:
        shares_outstanding: Number of shares outstanding
        
    Returns:
        Float bucket classification
    """
    if shares_outstanding < 25_000_000:
        return 'micro'
    elif shares_outstanding < 50_000_000:
        return 'small'
    elif shares_outstanding < 200_000_000:
        return 'medium'
    elif shares_outstanding < 1_000_000_000:
        return 'large'
    else:
        return 'mega'

def fill_shares_outstanding(stocks: List[Dict[str, Any]], use_mcp: bool = False, 
                          api_key: str = None) -> List[Dict[str, Any]]:
    """
    Fill in missing shares outstanding data for stocks
    
    Args:
        stocks: List of stock dictionaries
        use_mcp: Whether to use MCP Polygon server
        api_key: Polygon API key for direct API calls
        
    Returns:
        Updated list of stocks with shares outstanding data
    """
    if not stocks:
        return stocks
    
    # Identify stocks missing shares outstanding data
    missing_shares = []
    for stock in stocks:
        existing_shares = extract_shares_from_snapshot(stock)
        if not existing_shares:
            ticker = stock.get('symbol') or stock.get('ticker')
            if ticker:
                missing_shares.append(ticker)
    
    print(f"Found {len(missing_shares)} stocks missing shares outstanding data")
    
    # Fetch data from external sources if needed
    external_data = {}
    if missing_shares:
        if use_mcp:
            external_data = mcp_get_shares_outstanding(missing_shares)
        else:
            external_data = polygon_batch_financials(missing_shares, api_key)
    
    # Process each stock
    enriched_count = 0
    estimated_count = 0
    
    for stock in stocks:
        meta = stock.setdefault('meta', {})
        
        # Check if shares outstanding already exists
        existing_shares = extract_shares_from_snapshot(stock)
        if existing_shares:
            meta['sharesOutstanding'] = existing_shares
            meta['shares_source'] = 'existing'
        else:
            # Try to get from external data
            ticker = stock.get('symbol') or stock.get('ticker')
            if ticker and ticker in external_data:
                shares_data = external_data[ticker]
                shares = shares_data.get('shares_outstanding') or shares_data.get('weighted_shares_outstanding')
                if shares:
                    meta['sharesOutstanding'] = int(shares)
                    meta['shares_source'] = 'mcp' if use_mcp else 'polygon_api'
                    enriched_count += 1
            
            # If still missing, try to estimate
            if 'sharesOutstanding' not in meta:
                estimated_shares = estimate_shares_from_fundamentals(stock)
                if estimated_shares:
                    meta['sharesOutstanding'] = estimated_shares
                    meta['shares_source'] = 'estimated'
                    meta['shares_estimated'] = True
                    estimated_count += 1
        
        # Add float bucket classification if shares are available
        shares = meta.get('sharesOutstanding')
        if shares:
            meta['float_bucket'] = assign_float_bucket(shares)
            
            # Add squeeze potential flags
            if shares < 50_000_000:
                meta['small_float'] = True
            if shares < 25_000_000:
                meta['micro_float'] = True
    
    print(f"Shares outstanding enrichment complete:")
    print(f"  - External lookups: {enriched_count}")
    print(f"  - Estimated from fundamentals: {estimated_count}")
    print(f"  - Total with shares data: {len([s for s in stocks if s.get('meta', {}).get('sharesOutstanding')])}")
    
    return stocks

def calculate_float_metrics(stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculate additional float-based metrics for squeeze analysis
    
    Args:
        stocks: List of stocks with shares outstanding data
        
    Returns:
        Updated stocks with float metrics
    """
    for stock in stocks:
        meta = stock.get('meta', {})
        shares = meta.get('sharesOutstanding')
        
        if not shares:
            continue
        
        # Calculate dollar market cap approximations
        price = meta.get('last') or meta.get('price')
        if hasattr(stock, 'price'):
            price = price or stock.price
        
        if price and price > 0:
            market_cap = shares * float(price)
            meta['calculated_market_cap'] = market_cap
            
            # Market cap buckets
            if market_cap < 300_000_000:
                meta['market_cap_bucket'] = 'small_cap'
            elif market_cap < 2_000_000_000:
                meta['market_cap_bucket'] = 'mid_cap'
            elif market_cap < 10_000_000_000:
                meta['market_cap_bucket'] = 'large_cap'
            else:
                meta['market_cap_bucket'] = 'mega_cap'
        
        # Squeeze scoring factors
        volume = meta.get('volume') or (stock.get('feats', {}).get('volume', 0))
        if volume and shares:
            turnover_ratio = float(volume) / float(shares)
            meta['daily_turnover_ratio'] = turnover_ratio
            
            # High turnover on small float = squeeze potential
            if shares < 50_000_000 and turnover_ratio > 0.1:  # >10% daily turnover
                meta['high_turnover_small_float'] = True
    
    return stocks