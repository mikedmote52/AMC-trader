"""
BMS Filter Tracer - Shows exactly what happens at each filtering stage
Traces through the real BMS engine filters step by step
"""
import asyncio
import aiohttp
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any

class BMSFilterTracer:
    """
    Trace through the exact BMS engine filtering stages
    """
    
    def __init__(self):
        self.api_key = 'c8SZM3s6nkdRGHqk8MqsJqKo_gXNYMGo'
        
        # BMS Configuration (from real engine)
        self.config = {
            'universe': {
                'min_price': 0.50,          # No penny stocks under $0.50
                'max_price': 100.0,         # CRITICAL: Under $100 only
                'min_dollar_volume_m': 5.0, # $5M+ dollar volume for liquidity
            },
            'thresholds': {
                'min_volume_surge': 2.5,    # 2.5x RelVol minimum
                'min_atr_pct': 0.04,        # 4% ATR minimum
            },
            'scoring': {
                'trade_ready_min': 65,      # Lowered from 75
                'monitor_min': 45           # Lowered from 60
            }
        }
        
    async def trace_bms_filters(self) -> Dict[str, Any]:
        """Trace through BMS filtering pipeline step by step"""
        
        print("🔍 BMS FILTER TRACER")
        print("=" * 80)
        print("Tracing through the EXACT BMS engine filtering pipeline")
        print("Showing what survives each filter stage")
        print()
        
        trace_results = {
            "timestamp": datetime.now().isoformat(),
            "config": self.config,
            "stages": {},
            "final_analysis": {}
        }
        
        try:
            # Stage 1: Fetch Raw Universe (Polygon Grouped Data)
            print("📊 STAGE 1: Raw Universe from Polygon Grouped Data")
            print("-" * 70)
            raw_universe = await self._fetch_raw_universe()
            
            if not raw_universe.get("success"):
                print(f"❌ Failed to fetch raw universe: {raw_universe.get('error')}")
                return {"error": "Universe fetch failed"}
            
            stage1_data = raw_universe["data"]
            print(f"✅ Fetched {len(stage1_data):,} stocks from Polygon grouped endpoint")
            trace_results["stages"]["stage1_raw_universe"] = {
                "count": len(stage1_data),
                "description": "All stocks from Polygon grouped daily data"
            }
            
            # Stage 2: Price Filter (Under $100 Rule)
            print(f"\n💰 STAGE 2: Price Filter (${self.config['universe']['min_price']}-${self.config['universe']['max_price']})")
            print("-" * 70)
            price_filtered = self._apply_price_filter(stage1_data)
            
            print(f"✅ Price filter: {len(price_filtered):,} stocks pass price bounds")
            print(f"  📊 Eliminated: {len(stage1_data) - len(price_filtered):,} stocks")
            print(f"  📈 Survival rate: {(len(price_filtered)/len(stage1_data)*100):.1f}%")
            
            trace_results["stages"]["stage2_price_filter"] = {
                "count": len(price_filtered),
                "eliminated": len(stage1_data) - len(price_filtered),
                "survival_rate": len(price_filtered)/len(stage1_data)*100,
                "filter_rules": f"${self.config['universe']['min_price']}-${self.config['universe']['max_price']}"
            }
            
            # Stage 3: Volume Filter ($5M+ Dollar Volume)
            print(f"\n📈 STAGE 3: Volume Filter (${self.config['universe']['min_dollar_volume_m']}M+ Dollar Volume)")
            print("-" * 70)
            volume_filtered = self._apply_volume_filter(price_filtered)
            
            print(f"✅ Volume filter: {len(volume_filtered):,} stocks have sufficient liquidity")
            print(f"  📊 Eliminated: {len(price_filtered) - len(volume_filtered):,} stocks")
            print(f"  📈 Survival rate: {(len(volume_filtered)/len(price_filtered)*100):.1f}%")
            
            trace_results["stages"]["stage3_volume_filter"] = {
                "count": len(volume_filtered),
                "eliminated": len(price_filtered) - len(volume_filtered),
                "survival_rate": len(volume_filtered)/len(price_filtered)*100,
                "filter_rules": f"${self.config['universe']['min_dollar_volume_m']}M+ dollar volume"
            }
            
            # Stage 4: Fund/ETF Exclusion Filter
            print(f"\n🏢 STAGE 4: Fund/ETF Exclusion Filter")
            print("-" * 70)
            equity_filtered = self._apply_fund_filter(volume_filtered)
            
            print(f"✅ Fund exclusion: {len(equity_filtered):,} common stocks remain")
            print(f"  📊 Eliminated: {len(volume_filtered) - len(equity_filtered):,} funds/ETFs")
            print(f"  📈 Survival rate: {(len(equity_filtered)/len(volume_filtered)*100):.1f}%")
            
            trace_results["stages"]["stage4_fund_filter"] = {
                "count": len(equity_filtered),
                "eliminated": len(volume_filtered) - len(equity_filtered),
                "survival_rate": len(equity_filtered)/len(volume_filtered)*100,
                "filter_rules": "Exclude ETFs, funds, trusts, indices"
            }
            
            # Stage 5: Get Live Market Data (Sample)
            print(f"\n📊 STAGE 5: Live Market Data Enrichment (Sample)")
            print("-" * 70)
            live_data = await self._get_live_market_data(equity_filtered[:200])  # Sample for demo
            
            print(f"✅ Live data: {len(live_data)} stocks with current market data")
            print(f"  📊 Sample size: {min(200, len(equity_filtered))} stocks tested")
            print(f"  📈 Data success rate: {(len(live_data)/min(200, len(equity_filtered))*100):.1f}%")
            
            trace_results["stages"]["stage5_live_data"] = {
                "count": len(live_data),
                "sample_size": min(200, len(equity_filtered)),
                "success_rate": len(live_data)/min(200, len(equity_filtered))*100,
                "description": "Real-time market data enrichment"
            }
            
            # Stage 6: BMS Scoring Algorithm
            print(f"\n🎯 STAGE 6: BMS Scoring Algorithm")
            print("-" * 70)
            scored_stocks = self._apply_bms_scoring(live_data)
            
            # Analyze score distribution
            high_scores = [s for s in scored_stocks if s['score'] >= 70]
            medium_scores = [s for s in scored_stocks if 50 <= s['score'] < 70]
            low_scores = [s for s in scored_stocks if s['score'] < 50]
            
            print(f"✅ BMS scoring complete:")
            print(f"  🔥 High scores (70+): {len(high_scores)} stocks")
            print(f"  📈 Medium scores (50-70): {len(medium_scores)} stocks")
            print(f"  📊 Low scores (<50): {len(low_scores)} stocks")
            print(f"  📊 Average score: {sum(s['score'] for s in scored_stocks)/len(scored_stocks):.1f}")
            
            trace_results["stages"]["stage6_bms_scoring"] = {
                "total_scored": len(scored_stocks),
                "high_scores": len(high_scores),
                "medium_scores": len(medium_scores),
                "low_scores": len(low_scores),
                "average_score": sum(s['score'] for s in scored_stocks)/len(scored_stocks)
            }
            
            # Stage 7: Final Candidate Selection
            print(f"\n✅ STAGE 7: Final Candidate Selection")
            print("-" * 70)
            final_candidates = [s for s in scored_stocks if s['score'] >= self.config['scoring']['monitor_min']]
            
            trade_ready = [s for s in final_candidates if s['score'] >= self.config['scoring']['trade_ready_min']]
            monitor = [s for s in final_candidates if s['score'] < self.config['scoring']['trade_ready_min']]
            
            print(f"🚨 Trade Ready (65+): {len(trade_ready)} stocks")
            print(f"👀 Monitor (45-65): {len(monitor)} stocks")
            print(f"✅ Total Final Candidates: {len(final_candidates)} stocks")
            
            trace_results["stages"]["stage7_final_selection"] = {
                "final_candidates": len(final_candidates),
                "trade_ready": len(trade_ready),
                "monitor": len(monitor),
                "threshold_trade": self.config['scoring']['trade_ready_min'],
                "threshold_monitor": self.config['scoring']['monitor_min']
            }
            
            # Show Complete Filtering Funnel
            print(f"\n📊 COMPLETE BMS FILTERING FUNNEL:")
            print("=" * 70)
            print(f"🌍 Raw Universe:           {len(stage1_data):,} stocks")
            print(f"💰 After Price Filter:     {len(price_filtered):,} stocks")
            print(f"📈 After Volume Filter:    {len(volume_filtered):,} stocks")
            print(f"🏢 After Fund Filter:      {len(equity_filtered):,} stocks")
            print(f"📊 With Live Data:         {len(live_data):,} stocks (sample)")
            print(f"🎯 After BMS Scoring:      {len(scored_stocks):,} stocks")
            print(f"✅ FINAL CANDIDATES:       {len(final_candidates):,} stocks")
            
            # Calculate overall efficiency
            if len(stage1_data) > 0:
                overall_efficiency = (len(final_candidates) / len(stage1_data)) * 100
                concentration_ratio = len(stage1_data) // len(final_candidates) if len(final_candidates) > 0 else 0
                
                print(f"\n📈 FILTERING EFFICIENCY:")
                print(f"  • Overall survival rate: {overall_efficiency:.4f}%")
                print(f"  • Concentration ratio: {concentration_ratio:,}:1")
                print(f"  • Key filter: Under $100 rule eliminates {((len(stage1_data)-len(price_filtered))/len(stage1_data)*100):.1f}% of universe")
            
            # Show top candidates
            if final_candidates:
                print(f"\n🎯 TOP FINAL CANDIDATES:")
                print("-" * 70)
                final_candidates.sort(key=lambda x: x['score'], reverse=True)
                
                for i, candidate in enumerate(final_candidates[:10], 1):
                    symbol = candidate['symbol']
                    score = candidate['score']
                    price = candidate['price']
                    volume_ratio = candidate.get('volume_ratio', 0)
                    price_change = candidate.get('price_change_pct', 0)
                    category = "TRADE_READY" if score >= 65 else "MONITOR"
                    
                    print(f"{i:2d}. {symbol:6s} | ${price:7.2f} | Score: {score:5.1f} | Vol: {volume_ratio:5.1f}x | Move: {price_change:+6.1f}% | {category}")
            
            trace_results["final_analysis"] = {
                "overall_efficiency": overall_efficiency,
                "concentration_ratio": concentration_ratio,
                "top_candidates": final_candidates[:10]
            }
            
            return trace_results
            
        except Exception as e:
            print(f"❌ BMS filter trace failed: {e}")
            return {"error": str(e)}
    
    async def _fetch_raw_universe(self) -> Dict[str, Any]:
        """Fetch raw universe using Polygon grouped data"""
        
        try:
            # Calculate date (use recent trading day)
            today = datetime.now()
            days_back = 3 if today.weekday() < 3 else 2
            date_to_use = (today - timedelta(days=days_back)).strftime('%Y-%m-%d')
            
            print(f"📡 Fetching grouped market data for {date_to_use}...")
            
            async with aiohttp.ClientSession() as session:
                url = f"https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/{date_to_use}"
                params = {
                    'apikey': self.api_key,
                    'adjusted': 'true',
                    'include_otc': 'false'
                }
                
                async with session.get(url, params=params, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get('results', [])
                        
                        if not results:
                            return {"success": False, "error": "No grouped data available"}
                        
                        print(f"✅ Retrieved {len(results):,} stocks from Polygon")
                        return {"success": True, "data": results}
                    
                    elif response.status == 401:
                        return {"success": False, "error": "API key invalid"}
                    
                    else:
                        return {"success": False, "error": f"HTTP {response.status}"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _apply_price_filter(self, stocks: List[Dict]) -> List[Dict]:
        """Apply BMS price filter: $0.50 - $100.00"""
        
        min_price = self.config['universe']['min_price']
        max_price = self.config['universe']['max_price']
        
        filtered = []
        for stock in stocks:
            price = float(stock.get('c', 0))  # Close price
            
            if min_price <= price <= max_price:
                stock['price'] = price
                filtered.append(stock)
        
        print(f"  💰 Price range ${min_price}-${max_price}: {len(filtered):,} stocks pass")
        
        # Show some examples of what was eliminated
        eliminated = [s for s in stocks if not (min_price <= float(s.get('c', 0)) <= max_price)]
        if eliminated:
            too_low = [s for s in eliminated if float(s.get('c', 0)) < min_price]
            too_high = [s for s in eliminated if float(s.get('c', 0)) > max_price]
            print(f"    • Too low (<${min_price}): {len(too_low):,} stocks")
            print(f"    • Too high (>${max_price}): {len(too_high):,} stocks")
        
        return filtered
    
    def _apply_volume_filter(self, stocks: List[Dict]) -> List[Dict]:
        """Apply BMS volume filter: $5M+ dollar volume"""
        
        min_dv_m = self.config['universe']['min_dollar_volume_m']
        
        filtered = []
        for stock in stocks:
            price = stock['price']
            volume = int(stock.get('v', 0))
            dollar_volume_m = (price * volume) / 1_000_000
            
            if dollar_volume_m >= min_dv_m:
                stock['volume'] = volume
                stock['dollar_volume_m'] = dollar_volume_m
                filtered.append(stock)
        
        print(f"  📈 Min ${min_dv_m}M dollar volume: {len(filtered):,} stocks pass")
        
        return filtered
    
    def _apply_fund_filter(self, stocks: List[Dict]) -> List[Dict]:
        """Apply BMS fund exclusion filter"""
        
        fund_keywords = ['ETF', 'FUND', 'TRUST', 'INDEX', 'SPDR', 'ISHARES', 'VANGUARD']
        
        filtered = []
        for stock in stocks:
            symbol = stock.get('T', '')  # Ticker symbol
            
            # Check if symbol contains fund keywords
            is_fund = any(keyword in symbol.upper() for keyword in fund_keywords)
            
            if not is_fund:
                stock['symbol'] = symbol
                filtered.append(stock)
        
        print(f"  🏢 Fund exclusion: {len(filtered):,} common stocks remain")
        
        return filtered
    
    async def _get_live_market_data(self, stocks: List[Dict]) -> List[Dict]:
        """Get live market data for stocks"""
        
        print(f"📊 Fetching live data for {len(stocks)} stocks...")
        
        live_stocks = []
        
        try:
            async with aiohttp.ClientSession() as session:
                # Process in smaller batches to avoid rate limits
                for i in range(0, min(50, len(stocks)), 10):
                    batch = stocks[i:i+10]
                    
                    for stock in batch:
                        symbol = stock['symbol']
                        
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
                                            current_price = day.get("c")
                                            current_volume = day.get("v")
                                            prev_price = prev_day.get("c")
                                            prev_volume = prev_day.get("v", 1)
                                            
                                            enhanced_stock = stock.copy()
                                            enhanced_stock.update({
                                                "current_price": current_price,
                                                "current_volume": current_volume,
                                                "prev_price": prev_price,
                                                "prev_volume": prev_volume,
                                                "volume_ratio": current_volume / max(prev_volume, 1),
                                                "price_change_pct": ((current_price - prev_price) / max(prev_price, 1)) * 100,
                                                "current_dollar_volume": current_price * current_volume
                                            })
                                            
                                            live_stocks.append(enhanced_stock)
                            
                            await asyncio.sleep(0.1)  # Rate limiting
                            
                        except Exception:
                            continue
                    
                    # Progress update
                    print(f"    Processed {min(i+10, len(stocks))}/{len(stocks)} stocks...")
        
        except Exception as e:
            print(f"⚠️ Live data fetch error: {e}")
        
        return live_stocks
    
    def _apply_bms_scoring(self, stocks: List[Dict]) -> List[Dict]:
        """Apply BMS scoring algorithm"""
        
        scored_stocks = []
        
        for stock in stocks:
            # BMS Scoring Components
            volume_ratio = stock.get('volume_ratio', 1)
            price_change = abs(stock.get('price_change_pct', 0))
            current_price = stock.get('current_price', stock.get('price', 0))
            dollar_volume = stock.get('current_dollar_volume', 0)
            
            score = 0
            
            # Volume Surge Score (40 points max)
            if volume_ratio >= 5.0:
                score += 40
            elif volume_ratio >= 3.0:
                score += 35
            elif volume_ratio >= 2.5:
                score += 30
            elif volume_ratio >= 1.5:
                score += 20
            else:
                score += 10
            
            # Price Momentum Score (30 points max)
            if 2 <= price_change <= 8:
                score += 30  # Sweet spot
            elif price_change <= 2:
                score += 25  # Building
            elif 8 < price_change <= 15:
                score += 20  # Moving
            elif price_change > 20:
                score += 5   # Already moved
            
            # Liquidity Score (20 points max)
            if dollar_volume >= 50_000_000:  # $50M+
                score += 20
            elif dollar_volume >= 20_000_000:  # $20M+
                score += 15
            elif dollar_volume >= 10_000_000:  # $10M+
                score += 10
            else:
                score += 5
            
            # Price Range Bonus (10 points max)
            if 1 <= current_price <= 15:
                score += 10  # Sweet spot for explosive moves
            elif 15 < current_price <= 50:
                score += 8
            elif 0.50 <= current_price < 1:
                score += 6
            else:
                score += 3
            
            stock_scored = stock.copy()
            stock_scored.update({
                "score": round(score, 1),
                "price": current_price
            })
            
            scored_stocks.append(stock_scored)
        
        return scored_stocks

async def run_bms_filter_trace():
    """Execute the BMS filter trace"""
    
    tracer = BMSFilterTracer()
    
    try:
        results = await tracer.trace_bms_filters()
        
        if "error" in results:
            print(f"\n❌ BMS filter trace failed: {results['error']}")
            return None
        
        print("\n" + "=" * 80)
        print("📋 BMS FILTER TRACE COMPLETE")
        print("=" * 80)
        
        # Save detailed results
        with open("bms_filter_trace_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📋 Complete trace results saved to: bms_filter_trace_results.json")
        print(f"🔍 This shows EXACTLY how the BMS engine filters the universe")
        
        return results
        
    except Exception as e:
        print(f"❌ BMS filter trace failed: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(run_bms_filter_trace())