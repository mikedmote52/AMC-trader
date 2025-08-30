#!/usr/bin/env python3
"""
Rapid Explosive Stock Selector
REPLACEMENT for slow Bollinger Band compression analysis
Focuses on real-time volume spikes and momentum breakouts
"""

import asyncio
import httpx
import logging
import math
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RapidExplosiveSelector:
    """
    Fast explosive opportunity detection
    NO Bollinger Bands - focuses on volume spikes and momentum
    """
    
    def __init__(self, poly_key: str):
        self.poly_key = poly_key
        
    async def _poly_get(self, client, path, params=None, timeout=10):
        """Quick Polygon API call"""
        p = {"apiKey": self.poly_key}
        if params: p.update(params)
        r = await client.get(f"https://api.polygon.io{path}", params=p, timeout=timeout)
        r.raise_for_status()
        return r.json()
    
    async def find_explosive_candidates(self, universe: List[str], limit: int = 50) -> List[Dict[str, Any]]:
        """
        Find explosive candidates using SPEED-OPTIMIZED approach
        NO 60-day compression analysis - just real explosive signals
        """
        
        timeout = httpx.Timeout(15.0, connect=5.0)
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
        
        candidates = []
        
        async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
            # Get recent trading data for all symbols in parallel
            tasks = [self._analyze_explosive_potential(client, symbol) for symbol in universe[:200]]  # Limit for speed
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for symbol, result in zip(universe[:200], results):
                if isinstance(result, Exception):
                    continue
                    
                if result and result.get('explosive_score', 0) >= 0.30:  # Lower threshold for speed
                    candidates.append(result)
        
        # Sort by explosive score (best first)
        candidates.sort(key=lambda x: x.get('explosive_score', 0), reverse=True)
        
        return candidates[:limit]
    
    async def _analyze_explosive_potential(self, client, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Rapid explosive analysis - NO BOLLINGER BANDS
        Focus on: Volume spikes, Recent momentum, Price action
        """
        try:
            # Get just last 10 days of data (vs 60+ for Bollinger)
            bars = await self._get_recent_bars(client, symbol, days=10)
            
            if len(bars) < 5:
                return None
                
            current_bar = bars[-1]
            price = current_bar.get('c', 0)
            volume = current_bar.get('v', 0)
            high = current_bar.get('h', 0)
            low = current_bar.get('l', 0)
            
            if price <= 0 or volume <= 0:
                return None
                
            # EXPLOSIVE SIGNALS (NO COMPRESSION LAG)
            
            # 1. VOLUME EXPLOSION (most important)
            avg_volume = sum(bar.get('v', 0) for bar in bars[-5:-1]) / 4  # 4-day avg
            volume_spike = volume / avg_volume if avg_volume > 0 else 1.0
            volume_score = min(volume_spike / 10.0, 1.0)  # 10x = max score
            
            # 2. MOMENTUM BREAKOUT (recent strength)
            if len(bars) >= 3:
                price_3d_ago = bars[-4].get('c', price)
                momentum_3d = (price - price_3d_ago) / price_3d_ago if price_3d_ago > 0 else 0
                momentum_score = max(0, min(momentum_3d * 5, 1.0))  # 20% move = max score
            else:
                momentum_score = 0
                
            # 3. INTRADAY STRENGTH (where in daily range)
            if high > low:
                range_position = (price - low) / (high - low)
                range_score = range_position  # Higher in range = better
            else:
                range_score = 0.5
                
            # 4. RECENT VOLATILITY EXPANSION (vs steady state)
            if len(bars) >= 5:
                recent_ranges = [(b.get('h', 0) - b.get('l', 0)) / b.get('c', 1) for b in bars[-3:]]
                earlier_ranges = [(b.get('h', 0) - b.get('l', 0)) / b.get('c', 1) for b in bars[-8:-3]]
                
                avg_recent = sum(recent_ranges) / len(recent_ranges) if recent_ranges else 0
                avg_earlier = sum(earlier_ranges) / len(earlier_ranges) if earlier_ranges else 0
                
                if avg_earlier > 0:
                    volatility_expansion = avg_recent / avg_earlier
                    volatility_score = min(volatility_expansion / 2.0, 1.0)  # 2x expansion = max
                else:
                    volatility_score = 0.5
            else:
                volatility_score = 0.5
            
            # EXPLOSIVE COMPOSITE SCORE (NO COMPRESSION COMPONENT)
            explosive_score = (
                volume_score * 0.45 +        # Volume spike MOST important
                momentum_score * 0.30 +      # Recent momentum 
                range_score * 0.15 +         # Intraday strength
                volatility_score * 0.10      # Volatility expansion
            )
            
            # Generate rapid thesis
            thesis = self._generate_explosive_thesis(symbol, price, volume_spike, momentum_3d, explosive_score)
            
            return {
                'symbol': symbol,
                'price': price,
                'explosive_score': explosive_score,
                'volume_spike': volume_spike,
                'momentum_3d': momentum_3d,
                'range_position': range_position,
                'volatility_expansion': volatility_score * 2.0,
                'thesis': thesis,
                'method': 'RAPID_EXPLOSIVE',
                'analysis_days': len(bars)
            }
            
        except Exception as e:
            logger.debug(f"Explosive analysis failed for {symbol}: {e}")
            return None
    
    async def _get_recent_bars(self, client, symbol: str, days: int = 10) -> List[Dict]:
        """Get recent daily bars - FAST"""
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days+5)).strftime('%Y-%m-%d')
            
            data = await self._poly_get(
                client, 
                f"/v2/aggs/ticker/{symbol}/range/1/day/{start_date}/{end_date}",
                params={"adjusted": "true", "limit": days+5}
            )
            
            return data.get("results", [])[-days:] if data.get("results") else []
        except:
            return []
    
    def _generate_explosive_thesis(self, symbol: str, price: float, volume_spike: float, 
                                 momentum: float, explosive_score: float) -> str:
        """Generate rapid explosive thesis"""
        
        # Volume analysis
        if volume_spike >= 10.0:
            vol_desc = f"EXPLOSIVE {volume_spike:.1f}x volume"
        elif volume_spike >= 5.0:
            vol_desc = f"strong {volume_spike:.1f}x volume surge"
        elif volume_spike >= 2.0:
            vol_desc = f"elevated {volume_spike:.1f}x volume"
        else:
            vol_desc = f"{volume_spike:.1f}x volume"
            
        # Momentum analysis
        momentum_pct = momentum * 100
        if momentum_pct >= 15:
            mom_desc = f"+{momentum_pct:.1f}% breakout momentum"
        elif momentum_pct >= 5:
            mom_desc = f"+{momentum_pct:.1f}% positive momentum"
        elif momentum_pct >= 0:
            mom_desc = f"+{momentum_pct:.1f}% momentum"
        else:
            mom_desc = f"{momentum_pct:.1f}% momentum"
            
        # Explosive potential
        if explosive_score >= 0.70:
            potential = "HIGH explosive potential"
        elif explosive_score >= 0.50:
            potential = "MODERATE explosive potential"
        elif explosive_score >= 0.30:
            potential = "developing explosive setup"
        else:
            potential = "early explosive indicators"
            
        return f"{symbol} ${price:.2f}: {potential} - {vol_desc}, {mom_desc}. Rapid analysis score: {explosive_score:.3f}"

# Integration functions
async def rapid_explosive_scan(poly_key: str, universe: List[str], limit: int = 50) -> List[Dict[str, Any]]:
    """Main function to replace Bollinger Band compression analysis"""
    selector = RapidExplosiveSelector(poly_key)
    return await selector.find_explosive_candidates(universe, limit)

def should_use_rapid_mode() -> bool:
    """Determine if should use rapid mode vs compression analysis"""
    # For now, always use rapid mode - it's faster and more effective
    return True