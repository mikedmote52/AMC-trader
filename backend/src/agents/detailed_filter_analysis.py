"""
Detailed Filter Analysis

Shows exactly which stocks survive each filter stage and why others are eliminated.
This helps identify if thresholds are too high/low and which filters are most effective.
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, List, Any

class DetailedFilterAnalysis:
    """
    Analyze each filter stage in detail
    """
    
    def __init__(self, api_base: str = "https://amc-trader.onrender.com"):
        self.api_base = api_base
    
    async def run_detailed_analysis(self) -> Dict[str, Any]:
        """Run detailed filter analysis showing stock-by-stock elimination"""
        
        print("🔍 DETAILED FILTER ANALYSIS")
        print("=" * 90)
        print("Shows exactly which stocks survive each filter and why")
        print()
        
        # Get raw candidates
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_base}/discovery/emergency/run-direct?limit=100", timeout=30) as response:
                    if response.status != 200:
                        return {"error": "Could not get raw data"}
                    
                    data = await response.json()
                    raw_candidates = data.get('candidates', [])
        
        except Exception as e:
            return {"error": str(e)}
        
        if not raw_candidates:
            return {"error": "No candidates found"}
        
        print(f"🌍 INITIAL UNIVERSE: {len(raw_candidates)} candidates")
        print("-" * 60)
        
        # Show initial distribution
        self._show_initial_distribution(raw_candidates)
        
        # Run detailed filter analysis
        filter_results = await self._analyze_filters_detailed(raw_candidates)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "initial_count": len(raw_candidates),
            "filter_results": filter_results
        }
    
    def _show_initial_distribution(self, candidates: List[Dict]):
        """Show initial distribution of key metrics"""
        
        print("📊 INITIAL DISTRIBUTION:")
        
        # Price distribution
        prices = [c.get('price', 0) for c in candidates]
        print(f"  💰 Prices: ${min(prices):.4f} - ${max(prices):.2f}")
        
        price_ranges = {
            "Under $1": len([p for p in prices if p < 1]),
            "$1-$5": len([p for p in prices if 1 <= p < 5]),
            "$5-$20": len([p for p in prices if 5 <= p < 20]), 
            "$20+": len([p for p in prices if p >= 20])
        }
        
        for range_name, count in price_ranges.items():
            print(f"    {range_name}: {count} candidates")
        
        # Volume ratio distribution
        volume_ratios = [c.get('volume_ratio', 0) for c in candidates]
        print(f"  📊 Volume Ratios: {min(volume_ratios):.1f}x - {max(volume_ratios):.1f}x")
        
        volume_ranges = {
            "1-2x": len([v for v in volume_ratios if 1 <= v < 2]),
            "2-5x": len([v for v in volume_ratios if 2 <= v < 5]),
            "5-20x": len([v for v in volume_ratios if 5 <= v < 20]),
            "20x+": len([v for v in volume_ratios if v >= 20])
        }
        
        for range_name, count in volume_ranges.items():
            print(f"    {range_name}: {count} candidates")
        
        # Price change distribution  
        price_changes = [abs(c.get('price_change_pct', 0)) for c in candidates]
        print(f"  📈 Price Changes: {min(price_changes):.1f}% - {max(price_changes):.1f}%")
        
        change_ranges = {
            "0-5%": len([p for p in price_changes if p < 5]),
            "5-20%": len([p for p in price_changes if 5 <= p < 20]),
            "20-100%": len([p for p in price_changes if 20 <= p < 100]),
            "100%+": len([p for p in price_changes if p >= 100])
        }
        
        for range_name, count in change_ranges.items():
            print(f"    {range_name}: {count} candidates")
        
        print()
    
    async def _analyze_filters_detailed(self, candidates: List[Dict]) -> Dict[str, Any]:
        """Run detailed analysis of each filter stage"""
        
        filter_results = {}
        current_candidates = candidates.copy()
        
        # Filter 1: Price Range Filter
        print("🔍 FILTER 1: Price Range ($0.10 - $500)")
        print("-" * 50)
        
        price_survivors = []
        price_eliminated = []
        
        for candidate in current_candidates:
            price = candidate.get('price', 0)
            symbol = candidate.get('symbol', 'N/A')
            
            if 0.1 <= price <= 500:
                price_survivors.append(candidate)
            else:
                price_eliminated.append({
                    "symbol": symbol,
                    "price": price,
                    "reason": f"Price ${price:.4f} outside range $0.10-$500"
                })
        
        print(f"✅ Survivors: {len(price_survivors)}")
        print(f"❌ Eliminated: {len(price_eliminated)}")
        
        if price_eliminated:
            print("  📋 Eliminated stocks:")
            for elim in price_eliminated[:5]:  # Show first 5
                print(f"    {elim['symbol']}: {elim['reason']}")
        
        filter_results["price_filter"] = {
            "survivors": len(price_survivors),
            "eliminated": len(price_eliminated),
            "eliminated_details": price_eliminated
        }
        
        current_candidates = price_survivors
        print()
        
        # Filter 2: Volume Ratio Filter
        print("🔍 FILTER 2: Volume Ratio (≥ 1.5x)")
        print("-" * 50)
        
        volume_survivors = []
        volume_eliminated = []
        
        for candidate in current_candidates:
            volume_ratio = candidate.get('volume_ratio', 0)
            symbol = candidate.get('symbol', 'N/A')
            
            if volume_ratio >= 1.5:
                volume_survivors.append(candidate)
            else:
                volume_eliminated.append({
                    "symbol": symbol,
                    "volume_ratio": volume_ratio,
                    "reason": f"Volume ratio {volume_ratio:.2f}x below 1.5x threshold"
                })
        
        print(f"✅ Survivors: {len(volume_survivors)}")
        print(f"❌ Eliminated: {len(volume_eliminated)}")
        
        if volume_eliminated:
            print("  📋 Eliminated stocks:")
            for elim in volume_eliminated[:5]:
                print(f"    {elim['symbol']}: {elim['reason']}")
        
        filter_results["volume_filter"] = {
            "survivors": len(volume_survivors),
            "eliminated": len(volume_eliminated),
            "eliminated_details": volume_eliminated
        }
        
        current_candidates = volume_survivors
        print()
        
        # Filter 3: Liquidity Filter
        print("🔍 FILTER 3: Dollar Volume (≥ $100K)")
        print("-" * 50)
        
        liquidity_survivors = []
        liquidity_eliminated = []
        
        for candidate in current_candidates:
            dollar_volume = candidate.get('dollar_volume', 0)
            symbol = candidate.get('symbol', 'N/A')
            
            if dollar_volume >= 100000:
                liquidity_survivors.append(candidate)
            else:
                liquidity_eliminated.append({
                    "symbol": symbol,
                    "dollar_volume": dollar_volume,
                    "reason": f"Dollar volume ${dollar_volume:,.0f} below $100K threshold"
                })
        
        print(f"✅ Survivors: {len(liquidity_survivors)}")
        print(f"❌ Eliminated: {len(liquidity_eliminated)}")
        
        if liquidity_eliminated:
            print("  📋 Eliminated stocks:")
            for elim in liquidity_eliminated[:5]:
                print(f"    {elim['symbol']}: {elim['reason']}")
        
        filter_results["liquidity_filter"] = {
            "survivors": len(liquidity_survivors),
            "eliminated": len(liquidity_eliminated),
            "eliminated_details": liquidity_eliminated
        }
        
        current_candidates = liquidity_survivors
        print()
        
        # Test multiple score thresholds
        score_thresholds = [50, 60, 70, 80]
        
        for threshold in score_thresholds:
            print(f"🔍 SCORE FILTER: {threshold}% Threshold")
            print("-" * 50)
            
            score_survivors = []
            score_eliminated = []
            
            for candidate in current_candidates:
                score = candidate.get('score', 0)
                symbol = candidate.get('symbol', 'N/A')
                
                if score >= threshold:
                    score_survivors.append(candidate)
                else:
                    score_eliminated.append({
                        "symbol": symbol,
                        "score": score,
                        "reason": f"Score {score:.1f}% below {threshold}% threshold"
                    })
            
            print(f"✅ Survivors: {len(score_survivors)}")
            print(f"❌ Eliminated: {len(score_eliminated)}")
            
            if score_survivors:
                print("  🔥 Top survivors:")
                for survivor in score_survivors[:5]:
                    symbol = survivor.get('symbol', 'N/A')
                    score = survivor.get('score', 0)
                    volume_ratio = survivor.get('volume_ratio', 0)
                    price_change = survivor.get('price_change_pct', 0)
                    action_tag = survivor.get('action_tag', 'N/A')
                    print(f"    {symbol}: {score:.1f}% | {volume_ratio:.1f}x vol | {price_change:+.1f}% | {action_tag}")
            
            if score_eliminated:
                print("  📋 Eliminated stocks:")
                for elim in score_eliminated[:5]:
                    print(f"    {elim['symbol']}: {elim['reason']}")
            
            filter_results[f"score_filter_{threshold}"] = {
                "survivors": len(score_survivors),
                "eliminated": len(score_eliminated),
                "eliminated_details": score_eliminated,
                "survivor_details": score_survivors[:10]  # Top 10 survivors
            }
            
            print()
        
        return filter_results
    
    async def generate_recommendations(self, filter_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on filter analysis"""
        
        recommendations = []
        
        # Analyze where most eliminations happen
        eliminations = {}
        for filter_name, result in filter_results.items():
            if isinstance(result, dict) and 'eliminated' in result:
                eliminations[filter_name] = result['eliminated']
        
        # Find biggest elimination stage
        if eliminations:
            biggest_elimination = max(eliminations.items(), key=lambda x: x[1])
            filter_name, count = biggest_elimination
            
            if count > 0:
                if 'price' in filter_name:
                    recommendations.append("Price filter eliminating candidates - consider wider price range")
                elif 'volume' in filter_name:
                    recommendations.append("Volume filter eliminating candidates - consider lower volume threshold")
                elif 'liquidity' in filter_name:
                    recommendations.append("Liquidity filter eliminating candidates - consider lower dollar volume threshold")
                elif 'score' in filter_name:
                    recommendations.append(f"Score filter eliminating too many - consider lower threshold")
        
        # Check final survival rates
        score_70_survivors = filter_results.get('score_filter_70', {}).get('survivors', 0)
        score_50_survivors = filter_results.get('score_filter_50', {}).get('survivors', 0)
        
        if score_70_survivors == 0:
            recommendations.append("70% threshold too strict - no survivors. Use 50-60% instead")
        elif score_70_survivors < 3:
            recommendations.append("70% threshold very strict - consider 60% for more opportunities")
        elif score_70_survivors > 20:
            recommendations.append("70% threshold too loose - consider 80% for better quality")
        
        return recommendations

async def run_detailed_analysis():
    """Run the detailed filter analysis"""
    
    analyzer = DetailedFilterAnalysis()
    
    try:
        results = await analyzer.run_detailed_analysis()
        
        if "error" in results:
            print(f"❌ Analysis failed: {results['error']}")
            return None
        
        # Generate recommendations
        recommendations = await analyzer.generate_recommendations(results["filter_results"])
        
        print("💡 RECOMMENDATIONS:")
        print("-" * 50)
        
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        else:
            print("  ✅ Current filter settings appear optimal")
        
        print()
        
        # Save results
        with open("detailed_filter_analysis.json", "w") as f:
            json.dump({**results, "recommendations": recommendations}, f, indent=2, default=str)
        
        print("📋 Detailed analysis saved to: detailed_filter_analysis.json")
        
        return results
        
    except Exception as e:
        print(f"❌ Detailed analysis failed: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(run_detailed_analysis())