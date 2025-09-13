"""
Improved Discovery Scorer - Finds Stocks BEFORE They Explode

Modified scoring algorithm that prioritizes:
1. Building pressure (not already exploded)
2. Volume accumulation (2-5x, not 100x+)
3. Price stability with coiling patterns
4. Early momentum signals
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import os

class ImprovedDiscoveryScorer:
    """
    Enhanced scorer that finds pre-explosion opportunities
    """
    
    def __init__(self, api_base: str = "https://amc-trader.onrender.com"):
        self.api_base = api_base
        self.polygon_key = os.getenv("POLYGON_API_KEY", "")
    
    def calculate_pre_explosion_score(self, stock: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate score prioritizing pre-explosion characteristics
        """
        
        symbol = stock.get('symbol', 'N/A')
        price = stock.get('price', 0)
        volume_ratio = stock.get('volume_ratio', 0)
        price_change_pct = abs(stock.get('price_change_pct', 0))
        dollar_volume = stock.get('dollar_volume', 0)
        
        # Initialize scores
        scores = {
            "volume_pressure": 0,
            "price_coiling": 0,
            "liquidity": 0,
            "squeeze_setup": 0,
            "momentum_building": 0
        }
        
        # 1. VOLUME PRESSURE SCORE (35 points max)
        # Best: 2-5x volume (building), not 100x+ (already exploded)
        if 2.0 <= volume_ratio <= 3.0:
            scores["volume_pressure"] = 35  # Perfect building range
        elif 3.0 < volume_ratio <= 5.0:
            scores["volume_pressure"] = 30  # Strong building
        elif 1.5 <= volume_ratio < 2.0:
            scores["volume_pressure"] = 25  # Early building
        elif 5.0 < volume_ratio <= 10.0:
            scores["volume_pressure"] = 20  # Getting heated
        elif volume_ratio > 10.0:
            # Penalize extreme volume - likely already exploded
            scores["volume_pressure"] = max(0, 15 - (volume_ratio / 10))
        else:
            scores["volume_pressure"] = 0
        
        # 2. PRICE COILING SCORE (25 points max)
        # Best: Small moves (<5%), indicating compression before explosion
        if price_change_pct <= 3:
            scores["price_coiling"] = 25  # Perfect - hasn't moved yet
        elif price_change_pct <= 5:
            scores["price_coiling"] = 22  # Tight range
        elif price_change_pct <= 10:
            scores["price_coiling"] = 18  # Starting to move
        elif price_change_pct <= 20:
            scores["price_coiling"] = 10  # Moving but not exploded
        else:
            # Penalize big moves - already exploded
            scores["price_coiling"] = max(0, 5 - (price_change_pct / 20))
        
        # 3. LIQUIDITY SCORE (15 points max)
        # Need enough liquidity but not massive (which indicates already popular)
        if 1_000_000 <= dollar_volume <= 10_000_000:
            scores["liquidity"] = 15  # Sweet spot
        elif 500_000 <= dollar_volume < 1_000_000:
            scores["liquidity"] = 12  # Good liquidity
        elif 10_000_000 < dollar_volume <= 50_000_000:
            scores["liquidity"] = 10  # High but acceptable
        elif dollar_volume > 50_000_000:
            scores["liquidity"] = 5  # Too liquid - likely already discovered
        elif dollar_volume >= 100_000:
            scores["liquidity"] = 8  # Minimum acceptable
        else:
            scores["liquidity"] = 0
        
        # 4. SQUEEZE SETUP SCORE (15 points max)
        # Favor lower-priced stocks with specific characteristics
        if 0.5 <= price <= 5:
            scores["squeeze_setup"] = 15  # Prime squeeze range
        elif 5 < price <= 10:
            scores["squeeze_setup"] = 12
        elif 10 < price <= 20:
            scores["squeeze_setup"] = 8
        elif price < 0.5:
            scores["squeeze_setup"] = 5  # Too penny
        else:
            scores["squeeze_setup"] = 3  # Higher priced
        
        # 5. MOMENTUM BUILDING SCORE (10 points max)
        # Combination of volume trend and price stability
        if volume_ratio >= 1.5 and price_change_pct <= 10:
            momentum_score = min(10, (volume_ratio * 2))
            scores["momentum_building"] = momentum_score
        else:
            scores["momentum_building"] = 0
        
        # Calculate total score
        total_score = sum(scores.values())
        
        # Determine action tag based on NEW criteria
        if total_score >= 75:
            action_tag = "PRE_EXPLOSION_IMMINENT"
        elif total_score >= 60:
            action_tag = "BUILDING_PRESSURE"
        elif total_score >= 45:
            action_tag = "EARLY_ACCUMULATION"
        elif total_score >= 30:
            action_tag = "MONITOR"
        else:
            action_tag = "NOT_READY"
        
        # Generate thesis
        thesis = self._generate_thesis(symbol, scores, volume_ratio, price_change_pct)
        
        return {
            "symbol": symbol,
            "score": total_score,
            "subscores": scores,
            "price": price,
            "volume": stock.get('volume', 0),
            "volume_ratio": volume_ratio,
            "price_change_pct": stock.get('price_change_pct', 0),
            "dollar_volume": dollar_volume,
            "action_tag": action_tag,
            "thesis": thesis,
            "explosion_probability": total_score / 100,
            "data_source": stock.get('data_source', 'unknown'),
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_thesis(self, symbol: str, scores: Dict, volume_ratio: float, price_change: float) -> str:
        """Generate investment thesis based on scores"""
        
        key_points = []
        
        # Volume analysis
        if scores["volume_pressure"] >= 30:
            key_points.append(f"{volume_ratio:.1f}x volume building")
        elif scores["volume_pressure"] >= 20:
            key_points.append(f"{volume_ratio:.1f}x volume accumulation")
        
        # Price analysis
        if scores["price_coiling"] >= 22:
            key_points.append(f"tight {price_change:.1f}% range (coiling)")
        elif scores["price_coiling"] >= 18:
            key_points.append(f"controlled {price_change:.1f}% move")
        
        # Squeeze setup
        if scores["squeeze_setup"] >= 12:
            key_points.append("prime squeeze setup")
        
        # Momentum
        if scores["momentum_building"] >= 8:
            key_points.append("momentum building")
        
        if key_points:
            return f"{symbol}: {', '.join(key_points)}"
        else:
            return f"{symbol}: Early stage opportunity"
    
    async def score_market_data(self, limit: int = 50) -> Dict[str, Any]:
        """Score current market data with improved algorithm"""
        
        print("🎯 IMPROVED DISCOVERY SCORER - Finding Pre-Explosion Opportunities")
        print("=" * 70)
        
        try:
            # Get market data
            market_data = await self._fetch_market_data(limit)
            
            if not market_data:
                print("❌ No market data available")
                return {"error": "No market data"}
            
            print(f"📊 Processing {len(market_data)} candidates...")
            
            # Score all candidates
            scored_candidates = []
            for stock in market_data:
                scored = self.calculate_pre_explosion_score(stock)
                scored_candidates.append(scored)
            
            # Sort by score
            scored_candidates.sort(key=lambda x: x['score'], reverse=True)
            
            # Filter by minimum score (30+)
            qualified_candidates = [c for c in scored_candidates if c['score'] >= 30]
            
            # Categorize results
            pre_explosion = [c for c in qualified_candidates if c['action_tag'] == 'PRE_EXPLOSION_IMMINENT']
            building = [c for c in qualified_candidates if c['action_tag'] == 'BUILDING_PRESSURE']
            early = [c for c in qualified_candidates if c['action_tag'] == 'EARLY_ACCUMULATION']
            
            print(f"\n✅ RESULTS:")
            print(f"  🔥 Pre-Explosion Imminent: {len(pre_explosion)}")
            print(f"  📈 Building Pressure: {len(building)}")
            print(f"  👀 Early Accumulation: {len(early)}")
            
            # Show top candidates
            if qualified_candidates:
                print(f"\n🎯 TOP PRE-EXPLOSION CANDIDATES:")
                print("-" * 50)
                
                for i, candidate in enumerate(qualified_candidates[:10], 1):
                    symbol = candidate['symbol']
                    score = candidate['score']
                    volume_ratio = candidate['volume_ratio']
                    price_change = candidate['price_change_pct']
                    action_tag = candidate['action_tag']
                    
                    print(f"{i:2d}. {symbol:6s} | Score: {score:.1f} | Vol: {volume_ratio:.1f}x | Move: {price_change:+.1f}%")
                    print(f"    Action: {action_tag}")
                    print(f"    {candidate['thesis']}")
                    print()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "total_processed": len(market_data),
                "qualified_count": len(qualified_candidates),
                "pre_explosion_count": len(pre_explosion),
                "building_count": len(building),
                "early_count": len(early),
                "candidates": qualified_candidates,
                "success": True
            }
            
        except Exception as e:
            print(f"❌ Scoring failed: {e}")
            return {"error": str(e), "success": False}
    
    async def _fetch_market_data(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch market data from API"""
        
        try:
            async with aiohttp.ClientSession() as session:
                # Try emergency endpoint first
                url = f"{self.api_base}/discovery/emergency/run-direct?limit={limit * 2}"
                async with session.post(url, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        candidates = data.get('candidates', [])
                        print(f"✅ Fetched {len(candidates)} candidates from API")
                        return candidates
                    else:
                        print(f"❌ API returned status {response.status}")
                        return self._create_test_data()
        except Exception as e:
            print(f"⚠️ API error: {e}, using test data")
            return self._create_test_data()
    
    def _create_test_data(self) -> List[Dict[str, Any]]:
        """Create realistic test data for pre-explosion scenarios"""
        
        test_stocks = [
            # Pre-explosion candidates (good scores)
            {"symbol": "APDN", "price": 1.45, "volume": 5200000, "volume_ratio": 2.8, "price_change_pct": 3.2, "dollar_volume": 7540000},
            {"symbol": "CLOV", "price": 0.89, "volume": 8900000, "volume_ratio": 2.3, "price_change_pct": 1.8, "dollar_volume": 7921000},
            {"symbol": "WKHS", "price": 2.34, "volume": 4500000, "volume_ratio": 3.1, "price_change_pct": 4.5, "dollar_volume": 10530000},
            {"symbol": "BBIG", "price": 0.67, "volume": 12000000, "volume_ratio": 2.5, "price_change_pct": 2.1, "dollar_volume": 8040000},
            {"symbol": "MULN", "price": 0.34, "volume": 45000000, "volume_ratio": 1.9, "price_change_pct": 1.5, "dollar_volume": 15300000},
            
            # Building momentum (medium scores)
            {"symbol": "SNDL", "price": 2.15, "volume": 3200000, "volume_ratio": 1.7, "price_change_pct": 5.8, "dollar_volume": 6880000},
            {"symbol": "GNUS", "price": 0.58, "volume": 6700000, "volume_ratio": 2.1, "price_change_pct": 8.2, "dollar_volume": 3886000},
            {"symbol": "XELA", "price": 0.23, "volume": 28000000, "volume_ratio": 1.6, "price_change_pct": 6.5, "dollar_volume": 6440000},
            
            # Already moving (lower scores)
            {"symbol": "SPRT", "price": 8.90, "volume": 2100000, "volume_ratio": 8.5, "price_change_pct": 25.3, "dollar_volume": 18690000},
            {"symbol": "IRNT", "price": 15.20, "volume": 1800000, "volume_ratio": 12.3, "price_change_pct": 45.6, "dollar_volume": 27360000},
            
            # Too hot (very low scores)
            {"symbol": "GME", "price": 145.00, "volume": 800000, "volume_ratio": 0.8, "price_change_pct": 1.2, "dollar_volume": 116000000},
            {"symbol": "AMC", "price": 5.20, "volume": 25000000, "volume_ratio": 0.9, "price_change_pct": -2.3, "dollar_volume": 130000000}
        ]
        
        # Add data source and timestamp
        for stock in test_stocks:
            stock['data_source'] = 'test_data'
            stock['timestamp'] = datetime.now().isoformat()
        
        return test_stocks

async def run_improved_scorer():
    """Run the improved discovery scorer"""
    
    scorer = ImprovedDiscoveryScorer()
    
    try:
        results = await scorer.score_market_data(limit=100)
        
        if results.get("success"):
            print("\n" + "=" * 70)
            print("📊 SCORING COMPLETE")
            print("=" * 70)
            
            print(f"Total Processed: {results['total_processed']}")
            print(f"Qualified Candidates: {results['qualified_count']}")
            print(f"Pre-Explosion Imminent: {results['pre_explosion_count']}")
            print(f"Building Pressure: {results['building_count']}")
            print(f"Early Accumulation: {results['early_count']}")
            
            # Save results
            with open("improved_scoring_results.json", "w") as f:
                json.dump(results, f, indent=2, default=str)
            
            print(f"\n📋 Results saved to: improved_scoring_results.json")
            
            return results
        else:
            print(f"❌ Scoring failed: {results.get('error')}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(run_improved_scorer())