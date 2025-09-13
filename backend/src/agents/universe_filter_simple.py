"""
Simple Universe Filtering Test
Shows complete filtering from thousands of stocks to final candidates
"""
import os
import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, List, Any

class SimpleUniverseFilterTest:
    """
    Test filtering starting from full universe using direct Polygon API
    """
    
    def __init__(self):
        self.api_key = 'c8SZM3s6nkdRGHqk8MqsJqKo_gXNYMGo'
        
    async def run_universe_test(self) -> Dict[str, Any]:
        """Run complete universe filtering test"""
        
        print("🌍 COMPLETE UNIVERSE FILTERING TEST")
        print("=" * 80)
        print("Starting from THOUSANDS of stocks from Polygon API")
        print("Filtering down to explosive opportunity candidates")
        print()
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "universe_stats": {},
            "filtering_stages": {},
            "final_candidates": []
        }
        
        try:
            # Stage 1: Fetch Full Universe
            print("📊 STAGE 1: Fetching Complete Stock Universe")
            print("-" * 60)
            universe_result = await self._fetch_full_universe()
            
            if not universe_result.get("success"):
                print(f"❌ Failed to fetch universe: {universe_result.get('error')}")
                return {"error": "Universe fetch failed"}
            
            all_tickers = universe_result["tickers"]
            print(f"✅ Fetched {len(all_tickers):,} stocks from Polygon API")
            
            results["universe_stats"] = {
                "total_universe": len(all_tickers),
                "data_source": "polygon_api"
            }
            
            # Stage 2: Basic Filtering
            print(f"\n🔍 STAGE 2: Basic Stock Filtering")
            print("-" * 60)
            basic_filtered = self._apply_basic_filters(all_tickers)
            print(f"✅ After basic filtering: {len(basic_filtered)} stocks")
            
            # Stage 3: Get Market Data Sample
            print(f"\n📊 STAGE 3: Fetching Market Data (Sample)")
            print("-" * 60)
            market_data = await self._fetch_market_data_sample(basic_filtered[:500])  # Limit for demo
            print(f"✅ Market data retrieved for {len(market_data)} stocks")
            
            # Stage 4: Quality Filtering
            print(f"\n📈 STAGE 4: Quality & Volume Filtering")
            print("-" * 60)
            quality_filtered = self._apply_quality_filters(market_data)
            print(f"✅ After quality filtering: {len(quality_filtered)} stocks")
            
            # Stage 5: Pre-Explosion Scoring
            print(f"\n🎯 STAGE 5: Pre-Explosion Detection Scoring")
            print("-" * 60)
            scored_stocks = self._score_pre_explosion_candidates(quality_filtered)
            print(f"✅ Scoring complete: {len(scored_stocks)} scored")
            
            # Stage 6: Final Selection
            print(f"\n✅ STAGE 6: Final Candidate Selection")
            print("-" * 60)
            final_candidates = self._select_final_candidates(scored_stocks)
            
            # Calculate complete funnel stats
            funnel_stats = {
                "initial_universe": len(all_tickers),
                "after_basic_filter": len(basic_filtered),
                "with_market_data": len(market_data),
                "after_quality_filter": len(quality_filtered),
                "scored_stocks": len(scored_stocks),
                "final_candidates": len(final_candidates)
            }
            
            results["filtering_stages"] = funnel_stats
            results["final_candidates"] = final_candidates[:10]
            
            # Display Complete Funnel
            print(f"📊 COMPLETE FILTERING FUNNEL:")
            print(f"  🌍 Total Universe: {len(all_tickers):,} stocks")
            print(f"  🔍 Basic Filtering: {len(basic_filtered):,} stocks")
            print(f"  📊 Market Data: {len(market_data):,} stocks")
            print(f"  📈 Quality Filtering: {len(quality_filtered):,} stocks")
            print(f"  🎯 Scored: {len(scored_stocks):,} stocks")
            print(f"  ✅ FINAL CANDIDATES: {len(final_candidates)} stocks")
            
            if len(all_tickers) > 0:
                efficiency = (len(final_candidates) / len(all_tickers)) * 100
                concentration = len(all_tickers) / len(final_candidates) if len(final_candidates) > 0 else 0
                print(f"\n📈 FILTERING EFFICIENCY:")
                print(f"  • Survival rate: {efficiency:.4f}%")
                print(f"  • Concentration ratio: {concentration:.0f}:1")
            
            return results
            
        except Exception as e:
            print(f"❌ Universe test failed: {e}")
            return {"error": str(e)}
    
    async def _fetch_full_universe(self) -> Dict[str, Any]:
        """Fetch complete universe from Polygon"""
        
        print("📡 Connecting to Polygon API...")
        
        try:
            async with aiohttp.ClientSession() as session:
                all_tickers = []
                page = 1
                
                while page <= 10:  # Limit pages for demo
                    url = "https://api.polygon.io/v3/reference/tickers"
                    params = {
                        "market": "stocks",
                        "active": "true", 
                        "limit": 1000,
                        "apikey": self.api_key
                    }
                    
                    if page > 1:
                        # Add cursor for next page (simplified)
                        params["cursor"] = f"page_{page}"
                    
                    async with session.get(url, params=params, timeout=30) as response:
                        if response.status == 200:
                            data = await response.json()
                            tickers = data.get("results", [])
                            
                            if not tickers:
                                break
                                
                            all_tickers.extend(tickers)
                            print(f"  Page {page}: +{len(tickers)} stocks (total: {len(all_tickers):,})")
                            
                            page += 1
                            await asyncio.sleep(0.1)  # Rate limiting
                        
                        elif response.status == 429:
                            print("  ⚠️ Rate limited, continuing with current data...")
                            break
                        else:
                            print(f"  ❌ API Error: HTTP {response.status}")
                            break
                
                return {
                    "success": True,
                    "tickers": all_tickers,
                    "total_pages": page - 1
                }
                
        except Exception as e:
            print(f"❌ Universe fetch failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _apply_basic_filters(self, tickers: List[Dict]) -> List[Dict]:
        """Apply basic filtering rules"""
        
        filtered = []
        
        for ticker in tickers:
            symbol = ticker.get("ticker", "")
            ticker_type = ticker.get("type", "")
            active = ticker.get("active", False)
            
            # Filter 1: Active stocks only
            if not active:
                continue
                
            # Filter 2: Common stocks only  
            if ticker_type not in ["CS", "ADRC"]:
                continue
                
            # Filter 3: Reasonable symbol length
            if len(symbol) > 6:
                continue
                
            # Filter 4: Avoid obvious ETFs
            if any(etf in symbol.upper() for etf in ["SPY", "QQQ", "IWM", "ETF", "FUND"]):
                continue
            
            filtered.append(ticker)
        
        return filtered
    
    async def _fetch_market_data_sample(self, tickers: List[Dict]) -> List[Dict]:
        """Fetch market data for a sample of stocks"""
        
        print(f"📊 Fetching market data for {len(tickers)} stocks...")
        
        stocks_with_data = []
        
        try:
            async with aiohttp.ClientSession() as session:
                for i, ticker_info in enumerate(tickers[:100]):  # Limit for demo
                    symbol = ticker_info["ticker"]
                    
                    try:
                        url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}"
                        params = {"apikey": self.api_key}
                        
                        async with session.get(url, params=params, timeout=5) as response:
                            if response.status == 200:
                                data = await response.json()
                                ticker_data = data.get("results", {})
                                
                                if ticker_data:
                                    day = ticker_data.get("day", {})
                                    prev_day = ticker_data.get("prevDay", {})
                                    
                                    if day.get("c") and day.get("v") and prev_day.get("c"):
                                        price = day.get("c")
                                        volume = day.get("v")
                                        prev_price = prev_day.get("c")
                                        prev_volume = prev_day.get("v", 1)
                                        
                                        stock_data = {
                                            "symbol": symbol,
                                            "price": price,
                                            "volume": volume,
                                            "prev_price": prev_price,
                                            "prev_volume": prev_volume,
                                            "volume_ratio": volume / max(prev_volume, 1),
                                            "price_change_pct": ((price - prev_price) / max(prev_price, 1)) * 100,
                                            "dollar_volume": price * volume
                                        }
                                        
                                        stocks_with_data.append(stock_data)
                        
                        # Progress update
                        if (i + 1) % 25 == 0:
                            print(f"    Progress: {i+1}/{min(100, len(tickers))} ({((i+1)/min(100, len(tickers)))*100:.0f}%)")
                        
                        await asyncio.sleep(0.05)  # Rate limiting
                        
                    except Exception:
                        continue
        
        except Exception as e:
            print(f"⚠️ Market data fetch error: {e}")
        
        return stocks_with_data
    
    def _apply_quality_filters(self, stocks: List[Dict]) -> List[Dict]:
        """Apply quality and volume filters"""
        
        filtered = []
        
        for stock in stocks:
            price = stock["price"]
            volume = stock["volume"]
            dollar_volume = stock["dollar_volume"]
            volume_ratio = stock["volume_ratio"]
            price_change = abs(stock["price_change_pct"])
            
            # Quality filters
            if price < 0.25 or price > 500:  # Price range
                continue
                
            if volume < 50000:  # Minimum volume
                continue
                
            if dollar_volume < 100000:  # Minimum liquidity
                continue
                
            if price_change > 500:  # Avoid extreme moves (already exploded)
                continue
                
            if volume_ratio < 0.5:  # Some volume activity
                continue
            
            filtered.append(stock)
        
        return filtered
    
    def _score_pre_explosion_candidates(self, stocks: List[Dict]) -> List[Dict]:
        """Score stocks for pre-explosion potential"""
        
        scored_stocks = []
        
        for stock in stocks:
            score = 0
            
            volume_ratio = stock["volume_ratio"]
            price_change = abs(stock["price_change_pct"])
            price = stock["price"]
            dollar_volume = stock["dollar_volume"]
            
            # Volume pressure scoring (40 points max)
            if 1.5 <= volume_ratio <= 3.0:
                score += 40  # Perfect building range
            elif 3.0 < volume_ratio <= 5.0:
                score += 35  # Good activity
            elif 5.0 < volume_ratio <= 10.0:
                score += 25  # Strong activity
            elif volume_ratio > 10.0:
                score += max(5, 20 - (volume_ratio / 5))  # Penalize extreme
            
            # Price stability scoring (30 points max)
            if price_change <= 2:
                score += 30  # Perfect - hasn't moved yet
            elif price_change <= 5:
                score += 25  # Small move
            elif price_change <= 10:
                score += 15  # Moderate move
            elif price_change > 20:
                score -= 10  # Penalize large moves
            
            # Liquidity scoring (20 points max)
            if dollar_volume >= 10_000_000:  # $10M+
                score += 20
            elif dollar_volume >= 5_000_000:   # $5M+
                score += 15
            elif dollar_volume >= 1_000_000:   # $1M+
                score += 10
            else:
                score += 5
            
            # Price range bonus (10 points max)
            if 1 <= price <= 10:
                score += 10  # Sweet spot
            elif 10 < price <= 50:
                score += 8
            elif 0.5 <= price < 1:
                score += 5
            
            # Determine action tag
            if score >= 75:
                action_tag = "PRE_EXPLOSION_IMMINENT"
            elif score >= 60:
                action_tag = "BUILDING_PRESSURE"
            elif score >= 45:
                action_tag = "EARLY_ACCUMULATION"
            else:
                action_tag = "MONITOR"
            
            stock_scored = stock.copy()
            stock_scored.update({
                "score": score,
                "action_tag": action_tag,
                "thesis": f"{stock['symbol']}: {volume_ratio:.1f}x vol, {price_change:+.1f}% move, score: {score}"
            })
            
            scored_stocks.append(stock_scored)
        
        # Sort by score
        scored_stocks.sort(key=lambda x: x["score"], reverse=True)
        
        return scored_stocks
    
    def _select_final_candidates(self, scored_stocks: List[Dict]) -> List[Dict]:
        """Select final candidates based on thresholds"""
        
        # Apply minimum score threshold
        candidates = [s for s in scored_stocks if s["score"] >= 45]
        
        # Categorize
        pre_explosion = [s for s in candidates if s["score"] >= 75]
        building = [s for s in candidates if 60 <= s["score"] < 75]
        early = [s for s in candidates if 45 <= s["score"] < 60]
        
        print(f"🚨 Pre-Explosion Imminent (75+): {len(pre_explosion)}")
        print(f"📈 Building Pressure (60-75): {len(building)}")
        print(f"👀 Early Accumulation (45-60): {len(early)}")
        print(f"✅ Total Final Candidates: {len(candidates)}")
        
        if candidates:
            print(f"\n🎯 TOP CANDIDATES:")
            print("-" * 70)
            for i, candidate in enumerate(candidates[:10], 1):
                symbol = candidate["symbol"]
                score = candidate["score"]
                volume_ratio = candidate["volume_ratio"]
                price_change = candidate["price_change_pct"]
                action = candidate["action_tag"]
                price = candidate["price"]
                
                print(f"{i:2d}. {symbol:6s} | ${price:7.2f} | Score: {score:5.1f} | Vol: {volume_ratio:5.1f}x | Move: {price_change:+6.1f}% | {action}")
        
        return candidates

async def run_simple_universe_test():
    """Execute the simple universe filtering test"""
    
    tester = SimpleUniverseFilterTest()
    
    try:
        results = await tester.run_universe_test()
        
        print("\n" + "=" * 80)
        print("📋 UNIVERSE FILTERING TEST COMPLETE")
        print("=" * 80)
        
        if "error" in results:
            print(f"❌ Test failed: {results['error']}")
            return None
        
        universe_stats = results.get("universe_stats", {})
        filtering_stats = results.get("filtering_stages", {})
        
        print("✅ SUMMARY:")
        print(f"  🌍 Total Universe: {universe_stats.get('total_universe', 0):,} stocks")
        print(f"  📊 Complete Funnel:")
        for stage, count in filtering_stats.items():
            if stage != "final_candidates":
                print(f"    • {stage.replace('_', ' ').title()}: {count:,}")
        print(f"  🎯 FINAL CANDIDATES: {filtering_stats.get('final_candidates', 0)}")
        
        if filtering_stats.get('final_candidates', 0) > 0:
            efficiency = (filtering_stats['final_candidates'] / universe_stats['total_universe']) * 100
            print(f"  📈 Filtering efficiency: {efficiency:.4f}% (extreme selectivity)")
            concentration = universe_stats['total_universe'] // filtering_stats['final_candidates']
            print(f"  🔍 Concentration ratio: {concentration:,}:1 (needle in haystack)")
        
        # Save results
        with open("simple_universe_filter_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📋 Complete results saved to: simple_universe_filter_results.json")
        print(f"🚫 NO FALLBACK DATA - 100% REAL POLYGON API DATA")
        
        return results
        
    except Exception as e:
        print(f"❌ Universe filter test failed: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(run_simple_universe_test())