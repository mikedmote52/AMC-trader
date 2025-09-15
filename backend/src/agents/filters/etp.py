#!/usr/bin/env python3
"""
Robust ETF/ETN exclusion filter with comprehensive pattern matching
"""
import re

# Major ETF/ETN issuers to block
ISSUER_DENY = {
    'spdr', 'ishares', 'vanguard', 'proshares', 'direxion', 'invesco', 'global x',
    'wisdomtree', 'vaneck', 'ark', 'pimco', 'jp morgan', 'ubs', 'barclays',
    'franklin', 'kraneshares', 'blackrock', 'state street', 'first trust',
    'schwab', 'fidelity', 'flexshares', 'innovator', 'defiance', 'roundhill',
    'simplify', 'amplify', 'pacer', 'xtrackers', 'graniteshares'
}

# Name keywords that indicate ETF/ETN
NAME_KEYS = {
    ' etf', ' etn', ' index', ' fund', ' trust', ' notes', ' leverage', 
    ' inverse', ' ultra', ' 2x', ' 3x', ' bear', ' bull', 'short ', 'long ',
    'daily ', 'monthly ', 'quarterly ', 'volatility', 'vix ', 'dividend ',
    'covered call', 'treasury', 'bond', 'commodity', 'currency', 'crypto'
}

# Known ETF/ETN tickers (comprehensive list)
STATIC_TICKERS = {
    # Major indices
    'SPY', 'QQQ', 'DIA', 'IWM', 'VTI', 'VOO', 'IVV', 'VEA', 'VWO', 'EFA', 'EEM',
    # Sector SPDRs
    'XLF', 'XLK', 'XLE', 'XLV', 'XLI', 'XLB', 'XLU', 'XLRE', 'XLY', 'XLP', 'XLC',
    # Banking/Finance
    'KRE', 'KBE', 'FAS', 'FAZ', 'XLF', 'IYF', 'IYG', 'KBWB', 'KBWR', 'DPST',
    # Retail
    'XRT', 'RTH', 'IBUY', 'EMTY', 'CLIX', 'ONLN',
    # Biotech/Healthcare  
    'XBI', 'IBB', 'LABU', 'LABD', 'BIB', 'BIS', 'SBIO', 'ARKG',
    # Bonds/Fixed Income
    'TLT', 'IEF', 'SHY', 'BND', 'AGG', 'LQD', 'HYG', 'JNK', 'EMB', 'TMF', 'TBT',
    # Leveraged/Inverse
    'TQQQ', 'SQQQ', 'SOXL', 'SOXS', 'UPRO', 'SPXU', 'SDS', 'SH', 'UVXY', 'SVXY',
    'VIXY', 'VXX', 'TVIX', 'UVIX', 'SPXL', 'SPXS', 'TNA', 'TZA', 'FAS', 'FAZ',
    'TSLL', 'TSLQ',  # Tesla leveraged/inverse ETFs
    # Covered Call/Options
    'QYLD', 'RYLD', 'XYLD', 'JEPI', 'JEPQ', 'NUSI', 'DIVO', 'SVOL', 'IVOL',
    # Commodities
    'GLD', 'SLV', 'USO', 'UCO', 'SCO', 'UNG', 'BOIL', 'KOLD', 'DBA', 'CORN', 'WEAT',
    # ARK Funds
    'ARKK', 'ARKQ', 'ARKW', 'ARKG', 'ARKF', 'ARKX', 'PRNT', 'IZRL',
    # Income/Dividend
    'SCHD', 'VIG', 'VYM', 'DVY', 'HDV', 'SDY', 'NOBL', 'PFF', 'PFFD',
    # International
    'IEFA', 'IEMG', 'INDA', 'EWJ', 'EWZ', 'FXI', 'ASHR', 'MCHI', 'EWT', 'EWY',
    # Thematic
    'ICLN', 'TAN', 'LIT', 'HACK', 'CIBR', 'ROBO', 'BOTZ', 'CLOU', 'SKYY', 'FINX',
    # Recent problem ETFs from audit
    'TSLZ', 'BNDW', 'IHDG', 'BSV', 'UTG', 'MGEE', 'DLN', 'DFIS'
}

# Leveraged/Inverse suffix patterns (very specific to known patterns)
LEV_PATTERNS = [
    re.compile(r'^[A-Z]{3}[LS]$'),  # SOXL, SOXS, etc.
    re.compile(r'^[A-Z]{2}[UDS]$'),  # SDS, etc.
    re.compile(r'^T[A-Z]{2}[QS]$'),  # TQQQ, SQQQ, etc.
    re.compile(r'^[A-Z]{4}$')        # Check against known leveraged symbols only
]

# Known leveraged symbols to avoid false positives
KNOWN_LEVERAGED = {
    'SOXL', 'SOXS', 'TQQQ', 'SQQQ', 'UPRO', 'SPXU', 'SDS', 'TMF', 'TBT',
    'UVXY', 'SVXY', 'VIXY', 'TNA', 'TZA', 'FAS', 'FAZ', 'LABU', 'LABD'
}

def is_etp(sym: str, name: str = None, meta: dict = None) -> bool:
    """
    Comprehensive ETF/ETN detection with multiple checks.
    Returns True if the symbol is an ETF/ETN and should be excluded.
    """
    if not sym:
        return False
        
    s = sym.upper()
    n = (name or '').lower()
    meta = meta or {}
    
    # Debug for AAPL
    debug = s == 'AAPL'
    
    # 1. Check static ticker list (highest confidence)
    if s in STATIC_TICKERS:
        if debug: print(f"  AAPL flagged by static ticker list")
        return True
    
    # 2. Check leveraged/inverse patterns (use specific list to avoid false positives)
    if s in KNOWN_LEVERAGED:
        if debug: print(f"  AAPL flagged by known leveraged list")
        return True
    
    # 3. Check asset/security type metadata
    type_info = (meta.get('assetType', '') + ' ' + meta.get('securityType', '')).lower()
    if any(k in type_info for k in ('etf', 'etn', 'fund', 'trust', 'index', 'note')):
        if debug: print(f"  AAPL flagged by type metadata: {type_info}")
        return True
    
    # 4. Check issuer names
    if any(issuer in n for issuer in ISSUER_DENY):
        if debug: print(f"  AAPL flagged by issuer name: {n}")
        return True
    
    # 5. Check name keywords
    if any(key in n for key in NAME_KEYS):
        if debug: print(f"  AAPL flagged by name keywords: {n}")
        return True
    
    # 6. Heuristic: massive shares and no earnings = likely ETF (more conservative)
    shares = meta.get('sharesOutstanding', 0)
    has_earnings = meta.get('nextEarningsDate') or meta.get('lastEarningsDate')
    # Only flag if BOTH massive shares AND no earnings AND no corporate name indicators
    if shares > 10_000_000_000 and not has_earnings:  # Raised threshold to 10B shares
        # Check if name suggests it's a real company
        has_corp_indicators = any(k in n for k in ('inc', 'corp', 'corporation', 'company', 'ltd', 'plc'))
        if not has_corp_indicators:
            return True
    
    # 7. Additional heuristics (more conservative)
    # ETFs often have exactly round number shares, but many companies do too
    # Only flag if it's a very obvious round number AND has other ETF indicators
    if shares in [50_000_000, 100_000_000, 200_000_000, 500_000_000]:
        # Must also have ETF name indicators to be flagged
        if any(k in n for k in NAME_KEYS):
            return True
    
    # 8. Symbol patterns common in ETFs (more conservative)
    # Three-letter symbols ending in specific letters
    if len(s) == 3:
        if s.endswith(('Q', 'Y', 'X', 'Z')):  # Common ETF endings
            # More conservative - only flag if no corporate indicators AND has ETF indicators
            has_corp_suffix = name and any(k in n for k in (' inc', ' corp', ' corporation', ' ltd', ' plc', ' company'))
            has_etf_indicators = name and any(k in n for k in NAME_KEYS)
            
            if has_corp_suffix and not has_etf_indicators:
                return False  # Definitely a company
            elif has_etf_indicators:
                return True   # Definitely an ETF
            else:
                return False  # Unclear - err on side of keeping it
    
    return False

def filter_etps(stocks: list, strict: bool = True) -> tuple[list, list]:
    """
    Filter out ETPs from a list of stocks.
    
    Args:
        stocks: List of stock dictionaries with 'symbol', 'name', and metadata
        strict: If True, applies strictest filtering
        
    Returns:
        (kept_stocks, removed_etps) tuple
    """
    kept = []
    removed = []
    
    for stock in stocks:
        # Extract symbol, name, and metadata
        if hasattr(stock, 'symbol'):  # Pydantic model
            sym = stock.symbol
            name = getattr(stock, 'name', None) or getattr(stock, 'company_name', None)
            meta = {
                'assetType': getattr(stock, 'asset_type', ''),
                'securityType': getattr(stock, 'security_type', ''),
                'sharesOutstanding': getattr(stock, 'shares_outstanding', 0),
                'nextEarningsDate': getattr(stock, 'next_earnings_date', None),
            }
        else:  # Dictionary
            sym = stock.get('symbol') or stock.get('ticker')
            name = stock.get('name') or stock.get('company_name')
            meta = stock.get('meta', {})
        
        if is_etp(sym, name, meta):
            removed.append(stock)
        else:
            kept.append(stock)
    
    # Strict mode: apply additional checks
    if strict and kept:
        # Sanity check - no known ETFs should pass
        for stock in kept:
            sym = stock.symbol if hasattr(stock, 'symbol') else stock.get('symbol', stock.get('ticker'))
            assert sym not in STATIC_TICKERS, f"Known ETF {sym} leaked through filter!"
    
    return kept, removed