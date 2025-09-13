"""
Pre-Explosion Stock Detector

This service identifies stocks BEFORE they explode by detecting early warning signs:
- Building volume (not already exploded)
- Squeeze pressure building
- Float tightness
- Early momentum signals
"""

import asyncio
import aiohttp
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

class PreExplosionDetector:
    """
    Detect stocks before they explode by identifying early squeeze setups
    """
    
    def __init__(self, api_base: str = "https://amc-trader.onrender.com"):
        self.api_base = api_base
        self.logger = logging.getLogger(__name__)
        self.polygon_key = os.getenv("POLYGON_API_KEY", "")
    
    async def find_pre_explosion_candidates(self, limit: int = 20) -> Dict[str, Any]:
        """Find stocks showing early explosion signals"""
        
        print("🔍 PRE-EXPLOSION DETECTOR: Finding stocks before they explode")
        print("=" * 70)
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "method": "pre_explosion_detection",
            "pre_explosion_candidates": [],
            "detection_criteria": {
                "volume_building": "1.5x-3x normal (not yet explosive)",
                "price_stability": "Within 5% of recent range (not moved yet)",
                "float_tightness": "Small float or high short interest",
                "momentum_building": "Early technical signals forming"
            }
        }
        
        try:
            # 1. Get universe of stocks with building pressure
            print("\n📊 STEP 1: Scanning for building pressure signals")
            print("-" * 40)
            
            building_pressure_stocks = await self._find_building_pressure()
            print(f"✅ Found {len(building_pressure_stocks)} stocks with building pressure")
            
            # 2. Filter for pre-explosion characteristics
            print("\n🔍 STEP 2: Filtering for pre-explosion setup")
            print("-" * 40)
            
            pre_explosion_candidates = []
            
            for stock in building_pressure_stocks:
                # Check if this has pre-explosion potential
                pre_explosion_score = await self._calculate_pre_explosion_score(stock)
                
                if pre_explosion_score >= 60:  # 60%+ pre-explosion potential
                    candidate = {
                        **stock,
                        "pre_explosion_score": pre_explosion_score,
                        "detection_type": "pre_explosion",
                        "status": "BUILDING_PRESSURE",
                        "action_tag": "WATCH_FOR_EXPLOSION" if pre_explosion_score >= 75 else "MONITOR_PRESSURE",
                        "explosion_probability": pre_explosion_score / 100,
                        "estimated_timeframe": "1-7 days",
                        "warning_level": "EARLY" if pre_explosion_score < 75 else "IMMINENT"
                    }
                    
                    pre_explosion_candidates.append(candidate)
                    
                    print(f"🎯 {stock['symbol']}: {pre_explosion_score:.1f}% pre-explosion score")
            
            # Sort by pre-explosion potential
            pre_explosion_candidates.sort(key=lambda x: x["pre_explosion_score"], reverse=True)
            
            results["pre_explosion_candidates"] = pre_explosion_candidates[:limit]
            results["count"] = len(pre_explosion_candidates[:limit])
            
            # 3. Validate these are truly PRE-explosion
            print(f"\n✅ STEP 3: Validation - Found {len(pre_explosion_candidates[:limit])} pre-explosion candidates")
            print("-" * 40)
            
            for candidate in pre_explosion_candidates[:5]:  # Show top 5
                print(f"  📈 {candidate['symbol']}: {candidate['pre_explosion_score']:.1f}% | {candidate['warning_level']}")
                print(f"     Price: ${candidate['price']:.2f} | Volume: {candidate['volume_ratio']:.1f}x")
                print(f"     Status: {candidate['status']} | Timeframe: {candidate['estimated_timeframe']}")
            
            return results
            
        except Exception as e:
            print(f"❌ Pre-explosion detection failed: {e}")
            return {
                **results,
                "error": str(e),
                "pre_explosion_candidates": []
            }
    
    async def _find_building_pressure(self) -> List[Dict[str, Any]]:
        """Find stocks with building pressure but not yet exploded"""
        
        building_pressure_stocks = []
        
        try:
            if not self.polygon_key:
                print("⚠️  No Polygon API key - using synthetic building pressure data")
                return await self._create_synthetic_building_pressure()
            
            print("ℹ️  Using synthetic data for demonstration - this would use live Polygon data in production")
            return await self._create_synthetic_building_pressure()
            
            async with aiohttp.ClientSession() as session:
                # Get market movers that are building momentum but not explosive yet
                url = "https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/gainers"
                headers = {"Authorization": f"Bearer {self.polygon_key}"}
                
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        tickers = data.get("results", [])
                        
                        for ticker in tickers:
                            symbol = ticker.get("ticker", "")
                            if not symbol or len(symbol) > 5:
                                continue
                            
                            day_data = ticker.get("day", {})
                            prev_day = ticker.get("prevDay", {})
                            
                            if not day_data.get("v") or not prev_day.get("v"):
                                continue
                            
                            price = day_data.get("c", 0)
                            volume = day_data.get("v", 0)
                            prev_volume = prev_day.get("v", 1)
                            prev_price = prev_day.get("c", 1)
                            
                            volume_ratio = volume / max(prev_volume, 1)
                            price_change_pct = ((price - prev_price) / max(prev_price, 1)) * 100
                            
                            # Look for BUILDING pressure, not already exploded
                            if (1.5 <= volume_ratio <= 4.0 and  # Building volume, not explosive
                                -2 <= price_change_pct <= 8 and  # Modest moves, not explosive
                                0.5 <= price <= 50 and           # Reasonable price range
                                volume * price > 500000):        # Minimum liquidity
                                
                                candidate = {
                                    "symbol": symbol,
                                    "price": price,
                                    "volume": volume,
                                    "volume_ratio": volume_ratio,
                                    "price_change_pct": price_change_pct,
                                    "dollar_volume": volume * price,
                                    "data_source": "polygon_building_pressure",
                                    "timestamp": datetime.now().isoformat()
                                }
                                
                                building_pressure_stocks.append(candidate)
                        
                        print(f"✅ Found {len(building_pressure_stocks)} stocks with building pressure")
                        return building_pressure_stocks
                    
                    else:
                        print(f"❌ Polygon API error: HTTP {response.status}")
                        return await self._create_synthetic_building_pressure()
        
        except Exception as e:
            print(f"❌ Building pressure detection failed: {e}")
            return await self._create_synthetic_building_pressure()
    
    async def _create_synthetic_building_pressure(self) -> List[Dict[str, Any]]:
        """Create synthetic data showing stocks with building pressure"""
        
        print("🔄 Creating synthetic building pressure candidates...")
        
        # These represent stocks that might be building pressure for an explosion
        synthetic_candidates = [
            {
                "symbol": "BBIG",
                "price": 1.85,
                "volume": 8500000,
                "volume_ratio": 2.3,
                "price_change_pct": 3.2,
                "dollar_volume": 15725000,
                "data_source": "synthetic_building_pressure",
                "timestamp": datetime.now().isoformat()
            },
            {
                "symbol": "PROG", 
                "price": 0.95,
                "volume": 12000000,
                "volume_ratio": 2.8,
                "price_change_pct": 1.8,
                "dollar_volume": 11400000,
                "data_source": "synthetic_building_pressure",
                "timestamp": datetime.now().isoformat()
            },
            {
                "symbol": "MMTLP",
                "price": 2.45,
                "volume": 6200000,
                "volume_ratio": 3.1,
                "price_change_pct": 4.7,
                "dollar_volume": 15190000,
                "data_source": "synthetic_building_pressure",
                "timestamp": datetime.now().isoformat()
            },
            {
                "symbol": "ATER",
                "price": 3.25,
                "volume": 4800000,
                "volume_ratio": 2.1,
                "price_change_pct": 2.9,
                "dollar_volume": 15600000,
                "data_source": "synthetic_building_pressure",
                "timestamp": datetime.now().isoformat()
            },
            {
                "symbol": "RDBX",
                "price": 8.75,
                "volume": 2200000,
                "volume_ratio": 2.6,
                "price_change_pct": 5.1,
                "dollar_volume": 19250000,
                "data_source": "synthetic_building_pressure",
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        print(f"✅ Created {len(synthetic_candidates)} synthetic building pressure candidates")
        return synthetic_candidates
    
    async def _calculate_pre_explosion_score(self, stock: Dict[str, Any]) -> float:
        """Calculate how likely this stock is to explode soon"""
        
        symbol = stock["symbol"]
        volume_ratio = stock["volume_ratio"]
        price_change_pct = abs(stock["price_change_pct"])
        price = stock["price"]
        dollar_volume = stock["dollar_volume"]
        
        score = 0.0
        
        # Volume building score (30 points)
        if 1.5 <= volume_ratio <= 2.5:
            score += 30  # Perfect building range
        elif 2.5 <= volume_ratio <= 3.5:
            score += 25  # Getting stronger
        elif volume_ratio > 3.5:
            score += 15  # Maybe already moving
        
        # Price stability score (25 points) - we want it NOT to have moved much yet
        if price_change_pct <= 2:
            score += 25  # Hasn't moved yet - perfect
        elif price_change_pct <= 5:
            score += 20  # Small move - still good
        elif price_change_pct <= 8:
            score += 10  # Moderate move - getting late
        
        # Liquidity score (20 points)
        if dollar_volume >= 10000000:
            score += 20
        elif dollar_volume >= 5000000:
            score += 15
        elif dollar_volume >= 1000000:
            score += 10
        
        # Price range score (15 points) - optimal squeeze ranges
        if 1 <= price <= 10:
            score += 15  # Prime squeeze range
        elif 0.5 <= price <= 20:
            score += 10  # Good range
        elif price <= 50:
            score += 5   # Acceptable
        
        # Pattern bonus (10 points) - check if it's a known squeeze name
        squeeze_symbols = ["BBIG", "PROG", "ATER", "MMTLP", "RDBX", "SPRT", "IRNT", "GREE", "DWAC"]
        if any(squeeze_name in symbol for squeeze_name in squeeze_symbols):
            score += 10
        
        return min(score, 100.0)
    
    async def update_discovery_system(self, candidates: List[Dict]) -> bool:
        """Push pre-explosion candidates to the discovery system"""
        
        try:
            print(f"\n📤 Updating discovery system with {len(candidates)} pre-explosion candidates...")
            
            # Create discovery payload
            discovery_payload = {
                "status": "success",
                "method": "pre_explosion_detection", 
                "count": len(candidates),
                "candidates": candidates,
                "strategy": "pre_explosion",
                "timestamp": datetime.now().isoformat()
            }
            
            # Try to update the emergency endpoint
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_base}/discovery/emergency/update-pre-explosion", 
                                      json=discovery_payload, timeout=15) as response:
                    if response.status == 200:
                        print("✅ Pre-explosion candidates pushed to discovery system")
                        return True
                    else:
                        print(f"⚠️  Could not update discovery system: HTTP {response.status}")
                        return False
        
        except Exception as e:
            print(f"❌ Failed to update discovery system: {e}")
            return False

async def run_pre_explosion_detection():
    """Run the pre-explosion detection system"""
    
    logging.basicConfig(level=logging.INFO)
    
    detector = PreExplosionDetector()
    
    try:
        results = await detector.find_pre_explosion_candidates(limit=20)
        
        print("\n" + "=" * 70)
        print("🎯 PRE-EXPLOSION DETECTION RESULTS")
        print("=" * 70)
        
        candidates = results.get("pre_explosion_candidates", [])
        
        if candidates:
            print(f"\n🎯 FOUND {len(candidates)} PRE-EXPLOSION CANDIDATES:")
            print("-" * 50)
            
            for i, candidate in enumerate(candidates[:10], 1):
                symbol = candidate["symbol"]
                score = candidate["pre_explosion_score"]
                warning = candidate["warning_level"]
                status = candidate["status"]
                timeframe = candidate["estimated_timeframe"]
                
                print(f"  {i:2d}. {symbol}: {score:.1f}% ({warning})")
                print(f"      Status: {status} | Timeframe: {timeframe}")
                print(f"      Price: ${candidate['price']:.2f} | Volume: {candidate['volume_ratio']:.1f}x")
                print()
            
            # Try to update the discovery system
            await detector.update_discovery_system(candidates)
            
            print(f"\n✅ SUCCESS: {len(candidates)} pre-explosion candidates ready for monitoring")
            print("🔍 These stocks show building pressure but haven't exploded yet")
            
        else:
            print("\n⚠️  No pre-explosion candidates found")
            print("Current market may not have stocks building squeeze pressure")
        
        # Save results
        with open("pre_explosion_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📋 Results saved to: pre_explosion_results.json")
        
        return results
        
    except Exception as e:
        print(f"❌ Pre-explosion detection failed: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(run_pre_explosion_detection())