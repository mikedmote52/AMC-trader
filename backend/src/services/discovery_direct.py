"""
Direct Discovery Runner - Simple synchronous discovery that always works
This bypasses all the complex async/worker systems
"""
import os
import json
import time
import logging
import requests
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class DirectDiscovery:
    """Direct discovery that fetches and scores stocks immediately"""
    
    def __init__(self):
        self.polygon_key = os.getenv("POLYGON_API_KEY", "")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
    def run_direct(self, limit: int = 50) -> Dict[str, Any]:
        """
        Run discovery directly using simple Polygon API calls
        Returns scored candidates immediately
        """
        start_time = time.time()
        
        try:
            # Step 1: Get market movers from Polygon
            candidates = self._get_market_movers()
            
            if not candidates:
                # Fallback: Get some active stocks
                candidates = self._get_active_stocks()
            
            # Step 2: Score them
            scored_candidates = []
            for symbol in candidates[:limit]:
                try:
                    score_data = self._score_stock(symbol)
                    if score_data:
                        scored_candidates.append(score_data)
                except Exception as e:
                    logger.error(f"Failed to score {symbol}: {e}")
                    continue
            
            # Step 3: Sort by score
            scored_candidates.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            # Step 4: Cache the results
            self._cache_results(scored_candidates)
            
            elapsed = time.time() - start_time
            
            return {
                "status": "success",
                "method": "direct_discovery",
                "count": len(scored_candidates),
                "candidates": scored_candidates,
                "elapsed_seconds": elapsed,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Direct discovery failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "elapsed_seconds": time.time() - start_time
            }
    
    def _get_market_movers(self) -> List[str]:
        """Get top market movers from Polygon"""
        try:
            # Get gainers
            url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/gainers"
            headers = {"Authorization": f"Bearer {self.polygon_key}"}
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                tickers = [t['ticker'] for t in data.get('tickers', [])[:20]]
                logger.info(f"Found {len(tickers)} market movers")
                return tickers
        except Exception as e:
            logger.error(f"Failed to get market movers: {e}")
        
        return []
    
    def _get_active_stocks(self) -> List[str]:
        """Fallback: Get some known active stocks"""
        # Popular stocks that are usually active
        return [
            "TSLA", "AAPL", "NVDA", "AMD", "SPY", 
            "MSFT", "AMZN", "META", "GOOGL", "QQQ",
            "PLTR", "SOFI", "F", "NIO", "RIVN",
            "LCID", "CCL", "AAL", "BAC", "WFC"
        ]
    
    def _score_stock(self, symbol: str) -> Dict[str, Any]:
        """Score a single stock with basic metrics"""
        try:
            # Get snapshot data
            url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}"
            headers = {"Authorization": f"Bearer {self.polygon_key}"}
            
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code != 200:
                return None
            
            data = response.json()
            ticker_data = data.get('ticker', {})
            
            # Extract key metrics
            day = ticker_data.get('day', {})
            prev_day = ticker_data.get('prevDay', {})
            
            if not day.get('v') or not prev_day.get('v'):
                return None
            
            # Calculate simple scores
            volume_ratio = day.get('v', 0) / max(prev_day.get('v', 1), 1)
            price_change = ((day.get('c', 0) - prev_day.get('c', 1)) / max(prev_day.get('c', 1), 1)) * 100
            
            # Simple scoring formula
            volume_score = min(volume_ratio / 5, 1.0) * 40  # Max 40 points
            momentum_score = min(abs(price_change) / 10, 1.0) * 30  # Max 30 points
            volatility_score = 20  # Default 20 points
            liquidity_score = 10 if day.get('v', 0) * day.get('c', 0) > 1000000 else 5  # 10 points if > $1M volume
            
            total_score = volume_score + momentum_score + volatility_score + liquidity_score
            
            return {
                "symbol": symbol,
                "score": round(total_score, 2),
                "price": day.get('c', 0),
                "volume": day.get('v', 0),
                "volume_ratio": round(volume_ratio, 2),
                "price_change_pct": round(price_change, 2),
                "dollar_volume": day.get('v', 0) * day.get('c', 0),
                "thesis": f"{symbol}: {volume_ratio:.1f}x volume, {price_change:+.1f}% move, score: {total_score:.0f}%",
                "action_tag": "trade_ready" if total_score >= 70 else "watchlist" if total_score >= 50 else "monitor",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to score {symbol}: {e}")
            return None
    
    def _cache_results(self, candidates: List[Dict]) -> bool:
        """Cache results to Redis"""
        try:
            import redis
            from backend.src.constants import CACHE_KEY_CONTENDERS
            
            r = redis.from_url(self.redis_url, decode_responses=False)
            
            cache_payload = {
                "timestamp": int(datetime.now().timestamp()),
                "iso_timestamp": datetime.now().isoformat(),
                "count": len(candidates),
                "candidates": candidates,
                "engine": "Direct Discovery",
                "strategy": "direct",
                "universe_size": 100,
                "filtered_size": len(candidates)
            }
            
            # Store in multiple keys for compatibility
            cache_data = json.dumps(cache_payload, default=str).encode('utf-8')
            r.setex(CACHE_KEY_CONTENDERS, 600, cache_data)
            r.setex("amc:discovery:contenders.latest", 600, cache_data)
            
            logger.info(f"Cached {len(candidates)} candidates")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache results: {e}")
            return False

# Global instance
direct_discovery = DirectDiscovery()