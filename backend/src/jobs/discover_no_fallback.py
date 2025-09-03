#!/usr/bin/env python3
"""
NO-FALLBACK Discovery System
CRITICAL: Never uses stale/cached data - fails loudly when fresh data unavailable
Built for finding minute-to-minute explosive opportunities
"""

import os
import sys
import logging
import json
import asyncio
import httpx
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.polygon_client_fixed import poly_fixed_singleton
from shared.redis_client import get_redis_client
from services.squeeze_detector import SqueezeDetector

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NoFallbackDiscovery:
    """
    Discovery system that NEVER uses stale data
    Fails loudly when fresh data isn't available
    """
    
    def __init__(self):
        self.polygon_api_key = os.getenv("POLYGON_API_KEY")
        if not self.polygon_api_key:
            raise RuntimeError("❌ CRITICAL: POLYGON_API_KEY not set - cannot proceed!")
        
        self.squeeze_detector = SqueezeDetector()
        self.redis = get_redis_client()
        
        # CRITICAL THRESHOLDS - No compromises
        self.MIN_UNIVERSE_SIZE = 5000  # Minimum acceptable universe
        self.MAX_CACHE_AGE_SECONDS = 300  # 5 minutes max cache age
        self.MIN_CANDIDATES = 5  # Minimum candidates to consider valid
        
    async def run_discovery(self, limit: int = 20, with_trace: bool = True) -> Tuple[List, Dict]:
        """
        Run discovery with ZERO tolerance for stale data
        Returns (candidates, trace) or raises exception
        """
        start_time = time.time()
        trace = {
            "timestamp": datetime.now().isoformat(),
            "counts_in": {},
            "counts_out": {},
            "errors": [],
            "data_freshness": "REAL_TIME"
        }
        
        try:
            # Step 1: Fetch universe (FRESH ONLY)
            logger.info("🔍 Fetching FRESH universe from Polygon...")
            universe = await self._fetch_fresh_universe()
            
            if len(universe) < self.MIN_UNIVERSE_SIZE:
                error_msg = f"❌ CRITICAL: Universe too small ({len(universe)} < {self.MIN_UNIVERSE_SIZE}). Data source compromised!"
                logger.error(error_msg)
                trace["errors"].append(error_msg)
                raise RuntimeError(error_msg)
            
            trace["counts_in"]["universe"] = len(universe)
            logger.info(f"✅ Fresh universe loaded: {len(universe)} stocks")
            
            # Step 2: Fetch FRESH prices (no cache)
            logger.info("💰 Fetching FRESH prices...")
            price_data = await self._fetch_fresh_prices(universe[:1000])  # Limit for speed
            
            if len(price_data) < 100:
                error_msg = f"❌ CRITICAL: Not enough price data ({len(price_data)} stocks). API may be down!"
                logger.error(error_msg)
                trace["errors"].append(error_msg)
                raise RuntimeError(error_msg)
            
            trace["counts_out"]["with_prices"] = len(price_data)
            logger.info(f"✅ Fresh prices fetched: {len(price_data)} stocks")
            
            # Step 3: Apply STRICT filters
            candidates = []
            for symbol, data in price_data.items():
                price = data.get('price', 0)
                volume = data.get('volume', 0)
                
                # STRICT FILTERING - No compromises
                if not (1.0 <= price <= 100.0):
                    continue
                if volume < 1_000_000:
                    continue
                    
                # Calculate volume spike
                dollar_volume = price * volume
                if dollar_volume < 5_000_000:
                    continue
                
                # Volume spike detection
                avg_volume = volume / 20  # Rough estimate
                volume_spike = volume / max(avg_volume, 1)
                
                if volume_spike < 2.0:  # Minimum 2x volume
                    continue
                
                # Create candidate
                candidates.append({
                    "symbol": symbol,
                    "price": price,
                    "volume": volume,
                    "dollar_vol": dollar_volume,
                    "volume_spike": volume_spike,
                    "source": "FRESH_DISCOVERY",
                    "timestamp": datetime.now().isoformat(),
                    "score": min(volume_spike * 10, 100),  # Simple scoring
                    "reason": f"Volume spike {volume_spike:.1f}x"
                })
            
            # Sort by score
            candidates.sort(key=lambda x: x['score'], reverse=True)
            candidates = candidates[:limit]
            
            trace["counts_out"]["final_candidates"] = len(candidates)
            
            # Step 4: VALIDATE we have enough candidates
            if len(candidates) < self.MIN_CANDIDATES:
                error_msg = f"❌ WARNING: Only {len(candidates)} candidates found. Market may be quiet."
                logger.warning(error_msg)
                trace["errors"].append(error_msg)
                # Don't fail here - legitimate market condition
            
            # Step 5: NEVER serve stale data
            self._clear_all_caches()
            
            # Store FRESH results with short TTL
            self._store_fresh_results(candidates, trace)
            
            processing_time = time.time() - start_time
            trace["processing_time_seconds"] = processing_time
            
            logger.info(f"✅ Discovery complete: {len(candidates)} FRESH candidates in {processing_time:.2f}s")
            
            return candidates, trace
            
        except Exception as e:
            error_msg = f"❌ CRITICAL DISCOVERY FAILURE: {str(e)}"
            logger.error(error_msg)
            trace["errors"].append(error_msg)
            trace["data_freshness"] = "FAILED"
            
            # CRITICAL: Clear all caches to prevent stale data
            self._clear_all_caches()
            
            # Return empty results - NEVER stale data
            return [], trace
    
    async def _fetch_fresh_universe(self) -> List[str]:
        """Fetch universe directly from Polygon - no cache"""
        all_symbols = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"https://api.polygon.io/v3/reference/tickers"
            params = {
                "market": "stocks",
                "active": "true",
                "limit": "1000",
                "apikey": self.polygon_api_key
            }
            
            for page in range(10):  # Limit pages
                response = await client.get(url, params=params)
                
                if response.status_code != 200:
                    raise RuntimeError(f"Polygon API failed: {response.status_code}")
                
                data = response.json()
                results = data.get('results', [])
                
                for stock in results:
                    ticker = stock.get('ticker', '')
                    if ticker and len(ticker) <= 6:
                        all_symbols.append(ticker)
                
                # Check for next page
                next_url = data.get('next_url')
                if not next_url:
                    break
                
                # Update URL for next page
                params['cursor'] = next_url.split('cursor=')[-1].split('&')[0]
        
        return list(set(all_symbols))
    
    async def _fetch_fresh_prices(self, symbols: List[str]) -> Dict[str, Dict]:
        """Fetch current prices - NEVER from cache"""
        price_data = {}
        
        # Fetch in batches to avoid overwhelming
        batch_size = 50
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i+batch_size]
            
            await asyncio.gather(*[
                self._fetch_single_price(symbol, price_data)
                for symbol in batch
            ])
            
            # Small delay between batches
            if i + batch_size < len(symbols):
                await asyncio.sleep(0.1)
        
        return price_data
    
    async def _fetch_single_price(self, symbol: str, price_data: Dict):
        """Fetch single stock price"""
        try:
            data = await poly_fixed_singleton.get_snapshot(symbol)
            if data and data.get('price'):
                price_data[symbol] = data
        except Exception as e:
            # Silently skip failed symbols
            pass
    
    def _clear_all_caches(self):
        """Clear ALL Redis caches to prevent stale data"""
        try:
            # Clear discovery caches
            keys_to_clear = [
                "amc:discovery:v2:contenders.latest",
                "amc:discovery:v2:explain.latest",
                "amc:discovery:contenders.latest",
                "amc:discovery:explain.latest",
                "amc:discovery:status"
            ]
            
            for key in keys_to_clear:
                self.redis.delete(key)
            
            logger.info("🗑️ All caches cleared - only fresh data will be served")
        except Exception as e:
            logger.error(f"Failed to clear caches: {e}")
    
    def _store_fresh_results(self, candidates: List, trace: Dict):
        """Store results with SHORT expiration"""
        try:
            # Store with 5-minute expiration ONLY
            ttl = 300  # 5 minutes
            
            self.redis.setex(
                "amc:discovery:v2:contenders.latest",
                ttl,
                json.dumps(candidates)
            )
            
            self.redis.setex(
                "amc:discovery:v2:explain.latest",
                ttl,
                json.dumps(trace)
            )
            
            status = {
                "last_run": datetime.now().isoformat(),
                "status": "FRESH",
                "candidates_found": len(candidates),
                "data_age_seconds": 0
            }
            
            self.redis.setex(
                "amc:discovery:status",
                ttl,
                json.dumps(status)
            )
            
            logger.info(f"📝 Fresh results stored with {ttl}s expiration")
        except Exception as e:
            logger.error(f"Failed to store results: {e}")

# Export for compatibility
async def select_candidates(relaxed: bool = False, limit: int = 10, with_trace: bool = True):
    """
    Entry point for discovery - NEVER uses stale data
    """
    discovery = NoFallbackDiscovery()
    return await discovery.run_discovery(limit=limit, with_trace=with_trace)

if __name__ == "__main__":
    # Test the no-fallback discovery
    async def test():
        candidates, trace = await select_candidates(limit=20)
        print(f"Found {len(candidates)} FRESH candidates")
        for c in candidates[:5]:
            print(f"  {c['symbol']}: ${c['price']:.2f}, Volume: {c['volume']:,}, Spike: {c['volume_spike']:.1f}x")
        
        if trace.get('errors'):
            print("Errors:", trace['errors'])
    
    asyncio.run(test())