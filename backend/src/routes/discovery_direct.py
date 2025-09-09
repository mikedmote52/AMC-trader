"""
Direct Discovery API - Real market data without complex async/worker system
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import logging
import os
import time
from datetime import datetime
import httpx
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()

# Polygon API configuration
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY', '1ORwpSzeOV20X6uaA8G3Zuxx7hLJ0KIC')
POLYGON_BASE = "https://api.polygon.io"

async def get_market_movers() -> List[Dict]:
    """Get top gaining stocks from Polygon"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get gainers/losers
            url = f"{POLYGON_BASE}/v2/snapshot/locale/us/markets/stocks/gainers"
            params = {"apiKey": POLYGON_API_KEY}
            
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                tickers = data.get("tickers", [])
                
                candidates = []
                for ticker_data in tickers[:20]:  # Top 20 gainers
                    ticker = ticker_data.get("ticker", "")
                    day = ticker_data.get("day", {})
                    prev_day = ticker_data.get("prevDay", {})
                    
                    # Skip if no data
                    if not day or not prev_day:
                        continue
                    
                    # Calculate metrics
                    price = day.get("c", 0)  # Close price
                    volume = day.get("v", 0)  # Volume
                    prev_volume = prev_day.get("v", 1)
                    change_pct = ticker_data.get("todaysChangePerc", 0)
                    
                    # Skip penny stocks and low volume
                    if price < 1.0 or volume < 100000:
                        continue
                    
                    # Calculate volume surge
                    volume_surge = volume / prev_volume if prev_volume > 0 else 1.0
                    
                    # Calculate BMS score (simplified)
                    bms_score = min(100, (
                        min(40, volume_surge * 10) +  # Volume component (40%)
                        min(30, change_pct * 5) +      # Momentum component (30%)
                        20 +                            # Base score
                        (10 if volume > 1000000 else 0)  # Liquidity bonus
                    ))
                    
                    # Determine action
                    if bms_score >= 75:
                        action = "TRADE_READY"
                    elif bms_score >= 60:
                        action = "MONITOR"
                    else:
                        action = "REJECT"
                    
                    candidates.append({
                        "symbol": ticker,
                        "bms_score": round(bms_score, 1),
                        "action": action,
                        "price": price,
                        "volume_surge": round(volume_surge, 1),
                        "dollar_volume": int(price * volume),
                        "momentum_1d": round(change_pct, 1),
                        "atr_pct": abs(round(change_pct, 1)),  # Simplified
                        "confidence": "HIGH" if bms_score >= 75 else "MEDIUM",
                        "risk_level": "HIGH" if change_pct > 10 else "MEDIUM",
                        "thesis": f"{'Strong' if volume_surge > 2 else 'Moderate'} volume surge with {change_pct:.1f}% gain",
                        "component_scores": {
                            "volume_surge": min(100, int(volume_surge * 20)),
                            "price_momentum": min(100, int(change_pct * 5)),
                            "volatility_expansion": min(100, int(abs(change_pct) * 5)),
                            "risk_filter": 60
                        }
                    })
                
                # Sort by BMS score
                candidates.sort(key=lambda x: x["bms_score"], reverse=True)
                return candidates
                
    except Exception as e:
        logger.error(f"Error fetching market movers: {e}")
        
    return []

async def get_active_stocks() -> List[Dict]:
    """Get most active stocks as fallback"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get most active stocks
            url = f"{POLYGON_BASE}/v2/snapshot/locale/us/markets/stocks/tickers"
            params = {
                "apiKey": POLYGON_API_KEY,
                "order": "desc",
                "sort": "volume",
                "limit": 50
            }
            
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                tickers = data.get("tickers", [])
                
                candidates = []
                for ticker_data in tickers[:30]:
                    ticker = ticker_data.get("ticker", "")
                    day = ticker_data.get("day", {})
                    prev_day = ticker_data.get("prevDay", {})
                    
                    if not day or not ticker:
                        continue
                    
                    price = day.get("c", 0)
                    volume = day.get("v", 0)
                    prev_volume = prev_day.get("v", 1) if prev_day else 1
                    prev_price = prev_day.get("c", price) if prev_day else price
                    change_pct = ((price - prev_price) / prev_price * 100) if prev_price > 0 else 0
                    
                    # Filter criteria
                    if price < 0.5 or price > 500 or volume < 500000:
                        continue
                    
                    volume_surge = volume / prev_volume if prev_volume > 0 else 1.0
                    
                    # Simplified BMS calculation
                    bms_score = min(100, (
                        min(35, volume_surge * 8) +
                        min(25, abs(change_pct) * 3) +
                        min(20, (volume / 1000000)) +
                        20
                    ))
                    
                    candidates.append({
                        "symbol": ticker,
                        "bms_score": round(bms_score, 1),
                        "action": "TRADE_READY" if bms_score >= 75 else ("MONITOR" if bms_score >= 60 else "REJECT"),
                        "price": round(price, 2),
                        "volume_surge": round(volume_surge, 1),
                        "dollar_volume": int(price * volume),
                        "momentum_1d": round(change_pct, 1),
                        "atr_pct": abs(round(change_pct, 1)),
                        "confidence": "MEDIUM",
                        "risk_level": "MEDIUM",
                        "thesis": f"High activity with {volume/1000000:.1f}M volume",
                        "component_scores": {
                            "volume_surge": min(100, int(volume_surge * 15)),
                            "price_momentum": min(100, int(abs(change_pct) * 4)),
                            "volatility_expansion": 50,
                            "risk_filter": 50
                        }
                    })
                
                candidates.sort(key=lambda x: x["bms_score"], reverse=True)
                return candidates
                
    except Exception as e:
        logger.error(f"Error fetching active stocks: {e}")
    
    return []

@router.get("/candidates")
async def get_candidates(
    limit: int = Query(20, description="Maximum number of candidates to return")
):
    """Get real discovery candidates using the actual BMS engine"""
    try:
        # Import and use the real BMS discovery engine
        from backend.src.services.bms_engine_real import RealBMSEngine
        
        # Initialize the BMS engine
        polygon_key = os.getenv('POLYGON_API_KEY')
        if not polygon_key:
            raise ValueError("POLYGON_API_KEY not found")
            
        logger.info("Initializing BMS engine for discovery...")
        bms_engine = RealBMSEngine(polygon_key)
        
        # Run the real discovery process
        logger.info(f"Running BMS discovery with limit={limit}")
        candidates = await bms_engine.discover_real_candidates(limit=limit)
        
        if candidates:
            logger.info(f"BMS engine found {len(candidates)} real discovery candidates")
            return {
                "status": "ready",
                "candidates": candidates,
                "count": len(candidates),
                "timestamp": datetime.now().isoformat(),
                "engine": "BMS Real Engine v1.1 - Always-On Discovery",
                "cached": False
            }
        else:
            # BMS engine ran but found no qualifying candidates after full analysis
            logger.info("BMS engine completed full analysis but found no candidates meeting criteria")
            return {
                "status": "ready",
                "candidates": [],
                "count": 0,
                "timestamp": datetime.now().isoformat(),
                "engine": "BMS Real Engine v1.1 - Analysis Complete",
                "message": "Real market analysis complete - no candidates meet BMS scoring thresholds"
            }
        
    except Exception as e:
        logger.error(f"Error in BMS discovery: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Return error details for debugging
        return {
            "status": "error",
            "candidates": [],
            "count": 0,
            "timestamp": datetime.now().isoformat(),
            "engine": "BMS - Error",
            "error": str(e)
        }

@router.get("/candidates/trade-ready")
async def get_trade_ready_candidates(
    limit: int = Query(10, description="Max trade-ready candidates")
):
    """Get only TRADE_READY candidates"""
    all_candidates = await get_candidates(limit=50)
    
    if all_candidates.get("candidates"):
        trade_ready = [c for c in all_candidates["candidates"] if c.get("action") == "TRADE_READY"]
        trade_ready = trade_ready[:limit]
        
        return {
            "status": "ready",
            "candidates": trade_ready,
            "count": len(trade_ready),
            "timestamp": datetime.now().isoformat(),
            "engine": "BMS Direct - Trade Ready Filter"
        }
    
    return all_candidates

@router.get("/contenders")
async def get_contenders(
    limit: int = Query(50, description="Maximum number of contenders to return")
):
    """Legacy alias for candidates endpoint"""
    return await get_candidates(limit=limit)

@router.get("/health")
async def discovery_health():
    """Discovery system health check"""
    return {
        "status": "healthy",
        "engine": "BMS Direct - Real Market Data",
        "components": {
            "polygon_api": "configured",
            "data_source": "live_market",
            "processing": "direct"
        },
        "timestamp": datetime.now().isoformat()
    }

@router.post("/trigger")
async def trigger_discovery(
    limit: int = Query(25, description="Number of candidates to discover")
):
    """Manually trigger discovery"""
    return await get_candidates(limit=limit)

@router.get("/audit/{symbol}")
async def audit_symbol(symbol: str):
    """Get detailed info for a symbol"""
    symbol = symbol.upper()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get ticker snapshot
            url = f"{POLYGON_BASE}/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}"
            params = {"apiKey": POLYGON_API_KEY}
            
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                ticker_data = data.get("ticker", {})
                
                day = ticker_data.get("day", {})
                prev_day = ticker_data.get("prevDay", {})
                
                price = day.get("c", 0)
                volume = day.get("v", 0)
                prev_volume = prev_day.get("v", 1)
                change_pct = ticker_data.get("todaysChangePerc", 0)
                
                volume_surge = volume / prev_volume if prev_volume > 0 else 1.0
                
                return {
                    "symbol": symbol,
                    "analysis": {
                        "symbol": symbol,
                        "bms_score": min(100, volume_surge * 10 + abs(change_pct) * 5 + 30),
                        "action": "MONITOR",
                        "price": price,
                        "volume_surge": round(volume_surge, 1),
                        "momentum_1d": round(change_pct, 1),
                        "component_scores": {
                            "volume_surge": min(100, int(volume_surge * 20)),
                            "price_momentum": min(100, int(change_pct * 5)),
                            "volatility_expansion": 50,
                            "risk_filter": 60
                        }
                    },
                    "market_data": ticker_data,
                    "timestamp": datetime.now().isoformat()
                }
    
    except Exception as e:
        logger.error(f"Error auditing {symbol}: {e}")
    
    # Return basic data on error
    return {
        "symbol": symbol,
        "analysis": {
            "symbol": symbol,
            "bms_score": 0,
            "action": "REJECT",
            "error": "Unable to fetch data"
        },
        "timestamp": datetime.now().isoformat()
    }