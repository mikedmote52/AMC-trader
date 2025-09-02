#!/usr/bin/env python3
"""
Short Interest Data Validator
Debug and validate short interest data from multiple sources to find most accurate values.
"""

import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime
import json

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

logger = logging.getLogger(__name__)

class ShortInterestValidator:
    """
    Validator to debug short interest data sources and find accurate values
    """
    
    def __init__(self):
        self.test_symbols = ["UP", "SPHR", "NAK", "AMC", "GME", "TSLA"]  # Known short squeeze candidates
    
    async def debug_yahoo_finance_fields(self, symbol: str) -> Dict:
        """Debug all available Yahoo Finance fields related to short interest"""
        if not HAS_YFINANCE:
            return {"error": "yfinance not available"}
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Extract all short interest related fields
            short_fields = {}
            potential_fields = [
                'shortPercentOfFloat',
                'shortRatio', 
                'sharesShort',
                'sharesShortPriorMonth',
                'floatShares',
                'sharesOutstanding',
                'heldPercentInstitutions',
                'heldPercentInsiders',
                'shortName',
                'impliedSharesOutstanding',
                'bookValue',
                'priceToBook'
            ]
            
            for field in potential_fields:
                value = info.get(field)
                if value is not None:
                    short_fields[field] = value
            
            # Calculate different possible short interest interpretations
            calculations = {}
            
            if info.get('shortPercentOfFloat') is not None:
                raw_percent = float(info.get('shortPercentOfFloat', 0))
                calculations['interpretation_1_raw'] = raw_percent  # As returned
                calculations['interpretation_2_percent'] = raw_percent / 100.0  # Divide by 100
                calculations['interpretation_3_already_decimal'] = raw_percent  # Already decimal
                
            if info.get('sharesShort') and info.get('floatShares'):
                shares_short = float(info.get('sharesShort', 0))
                float_shares = float(info.get('floatShares', 0))
                if float_shares > 0:
                    calculations['manual_calculation'] = shares_short / float_shares
                    calculations['manual_percentage'] = (shares_short / float_shares) * 100
            
            # Get recent price for context
            hist = ticker.history(period="1d")
            current_price = float(hist['Close'].iloc[-1]) if len(hist) > 0 else None
            
            return {
                "symbol": symbol,
                "timestamp": datetime.utcnow().isoformat(),
                "raw_fields": short_fields,
                "calculations": calculations,
                "current_price": current_price,
                "data_source": "yahoo_finance"
            }
            
        except Exception as e:
            return {
                "symbol": symbol,
                "error": str(e),
                "data_source": "yahoo_finance"
            }
    
    async def validate_against_known_values(self, symbol: str) -> Dict:
        """Validate against known short interest values for common stocks"""
        known_values = {
            "AMC": {"expected_si_range": (0.15, 0.40), "notes": "Historically high short interest"},
            "GME": {"expected_si_range": (0.10, 0.30), "notes": "GameStop squeeze candidate"},  
            "TSLA": {"expected_si_range": (0.02, 0.08), "notes": "Low short interest typically"},
            "UP": {"expected_si_range": (0.08, 0.12), "notes": "Based on external sources showing ~9.34%"}
        }
        
        yahoo_data = await self.debug_yahoo_finance_fields(symbol)
        
        validation_result = {
            "symbol": symbol,
            "yahoo_data": yahoo_data,
            "known_range": known_values.get(symbol, {"expected_si_range": None, "notes": "No known range"}),
            "validation_status": "unknown"
        }
        
        if symbol in known_values and "calculations" in yahoo_data:
            expected_range = known_values[symbol]["expected_si_range"]
            calculations = yahoo_data["calculations"]
            
            # Check which calculation method falls within expected range
            for calc_method, value in calculations.items():
                if isinstance(value, (int, float)):
                    decimal_value = float(value)
                    if expected_range[0] <= decimal_value <= expected_range[1]:
                        validation_result["validation_status"] = f"MATCH: {calc_method}"
                        validation_result["best_value"] = decimal_value
                        break
            else:
                validation_result["validation_status"] = "NO_MATCH"
                validation_result["issue"] = "No calculation matches expected range"
        
        return validation_result
    
    async def run_comprehensive_validation(self) -> Dict:
        """Run validation across multiple test symbols"""
        results = {
            "validation_timestamp": datetime.utcnow().isoformat(),
            "symbols_tested": self.test_symbols,
            "individual_results": {},
            "summary": {}
        }
        
        for symbol in self.test_symbols:
            logger.info(f"Validating short interest data for {symbol}")
            validation_result = await self.validate_against_known_values(symbol)
            results["individual_results"][symbol] = validation_result
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)
        
        # Generate summary
        match_count = sum(1 for r in results["individual_results"].values() 
                         if r.get("validation_status", "").startswith("MATCH"))
        
        results["summary"] = {
            "total_symbols": len(self.test_symbols),
            "matches_found": match_count,
            "match_rate": match_count / len(self.test_symbols) if self.test_symbols else 0,
            "data_quality": "HIGH" if match_count >= len(self.test_symbols) * 0.8 else 
                           "MEDIUM" if match_count >= len(self.test_symbols) * 0.5 else "LOW"
        }
        
        return results
    
    async def test_alternative_calculation(self, symbol: str) -> Dict:
        """Test alternative short interest calculation methods"""
        if not HAS_YFINANCE:
            return {"error": "yfinance not available"}
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Method 1: Direct field (current method)
            method1 = info.get('shortPercentOfFloat', 0)
            
            # Method 2: Manual calculation
            shares_short = info.get('sharesShort', 0)
            float_shares = info.get('floatShares', 1)  # Avoid division by zero
            method2 = (shares_short / float_shares) if float_shares > 0 else 0
            
            # Method 3: Use shares outstanding instead of float
            shares_outstanding = info.get('sharesOutstanding', 1)
            method3 = (shares_short / shares_outstanding) if shares_outstanding > 0 else 0
            
            # Method 4: Check if the field is already a percentage (needs /100)
            method4 = method1 / 100.0 if method1 > 1 else method1
            
            return {
                "symbol": symbol,
                "method1_direct_field": method1,
                "method2_manual_calc": method2,  
                "method3_vs_outstanding": method3,
                "method4_percentage_adjusted": method4,
                "raw_data": {
                    "shortPercentOfFloat": info.get('shortPercentOfFloat'),
                    "sharesShort": shares_short,
                    "floatShares": float_shares,
                    "sharesOutstanding": shares_outstanding
                },
                "recommendation": self._recommend_best_method(method1, method2, method3, method4)
            }
            
        except Exception as e:
            return {"symbol": symbol, "error": str(e)}
    
    def _recommend_best_method(self, m1, m2, m3, m4) -> str:
        """Recommend the best calculation method based on reasonableness"""
        methods = {
            "method1_direct": m1,
            "method2_manual": m2, 
            "method3_outstanding": m3,
            "method4_adjusted": m4
        }
        
        # Filter methods that give reasonable short interest values (0.1% to 50%)
        reasonable_methods = {}
        for name, value in methods.items():
            if isinstance(value, (int, float)) and 0.001 <= float(value) <= 0.50:
                reasonable_methods[name] = float(value)
        
        if not reasonable_methods:
            return "NO_REASONABLE_VALUES"
        
        # Prefer manual calculation if available and reasonable
        if "method2_manual" in reasonable_methods:
            return f"USE_MANUAL: {reasonable_methods['method2_manual']:.4f}"
        
        # Otherwise use the most reasonable value
        best_method = max(reasonable_methods.items(), key=lambda x: x[1])
        return f"USE_{best_method[0].upper()}: {best_method[1]:.4f}"

# Global validator instance
_validator = None

async def get_short_interest_validator() -> ShortInterestValidator:
    """Get global validator instance"""
    global _validator
    if _validator is None:
        _validator = ShortInterestValidator()
    return _validator