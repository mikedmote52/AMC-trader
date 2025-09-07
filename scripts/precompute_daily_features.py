#!/usr/bin/env python3
"""
Nightly Precompute Script for Daily Features
Calculates real 5d/30d momentum and ATR14 from historical data
"""

import asyncio
import sys
import os
import time
import json
import redis
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np

# Add backend to path
sys.path.append('/Users/michaelmote/Desktop/AMC-TRADER/backend')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DailyFeaturesPrecomputer:
    """Precomputes daily technical features for faster discovery"""
    
    def __init__(self, polygon_api_key: str, redis_url: str = None):
        self.polygon_api_key = polygon_api_key
        self.redis_client = redis.from_url(redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379'))
        
        # Rate limiting (use lower rate for batch processing)
        self.rate_limit_per_sec = 2  # Conservative for batch job
        self.last_call_time = 0
        
    def rate_limit(self):
        """Simple rate limiting for batch processing"""
        now = time.time()
        elapsed = now - self.last_call_time
        if elapsed < (1.0 / self.rate_limit_per_sec):
            sleep_time = (1.0 / self.rate_limit_per_sec) - elapsed
            time.sleep(sleep_time)
        self.last_call_time = time.time()
    
    async def get_historical_data(self, session: aiohttp.ClientSession, symbol: str) -> Optional[Dict]:
        """Get 30 days of historical OHLCV data for a symbol"""
        try:
            # Get date range (30 days ago to today)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=35)  # Extra buffer for weekends
            
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_str}/{end_str}"
            params = {
                'apikey': self.polygon_api_key,
                'adjusted': 'true',
                'sort': 'asc',
                'limit': 50
            }
            
            async with session.get(url, params=params, timeout=30) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                if not data.get('results') or len(data['results']) < 15:  # Need minimum data
                    return None
                
                return data['results']
                
        except Exception as e:
            logger.debug(f"Error fetching historical data for {symbol}: {e}")
            return None
    
    def calculate_features(self, ohlcv_data: List[Dict], symbol: str) -> Dict:
        """Calculate all technical features from OHLCV data"""
        if len(ohlcv_data) < 15:  # Minimum required for ATR14
            return {}
        
        try:
            # Convert to arrays
            opens = np.array([float(d['o']) for d in ohlcv_data])
            highs = np.array([float(d['h']) for d in ohlcv_data])
            lows = np.array([float(d['l']) for d in ohlcv_data])
            closes = np.array([float(d['c']) for d in ohlcv_data])
            volumes = np.array([float(d['v']) for d in ohlcv_data])
            
            # Current values (most recent)
            current_close = closes[-1]
            current_volume = volumes[-1]
            
            # Momentum calculations
            momentum_1d = 0.0
            momentum_5d = 0.0
            momentum_30d = 0.0
            
            if len(closes) >= 2:
                momentum_1d = ((closes[-1] - closes[-2]) / closes[-2]) * 100
            
            if len(closes) >= 6:
                momentum_5d = ((closes[-1] - closes[-6]) / closes[-6]) * 100
            
            if len(closes) >= 30:
                momentum_30d = ((closes[-1] - closes[-30]) / closes[-30]) * 100
            elif len(closes) > 1:
                # Use available data if less than 30 days
                momentum_30d = ((closes[-1] - closes[0]) / closes[0]) * 100
            
            # ATR14 calculation
            atr_14 = 0.0
            if len(ohlcv_data) >= 14:
                # True Range calculation
                tr_values = []
                for i in range(1, len(ohlcv_data)):
                    high = highs[i]
                    low = lows[i]
                    prev_close = closes[i-1]
                    
                    tr = max(
                        high - low,
                        abs(high - prev_close),
                        abs(low - prev_close)
                    )
                    tr_values.append(tr)
                
                if len(tr_values) >= 14:
                    # Simple Moving Average of last 14 TR values
                    atr_14 = np.mean(tr_values[-14:])
            
            # Volume statistics
            avg_vol_30d = np.mean(volumes) if len(volumes) > 0 else current_volume
            
            # Calculate ATR percentage
            atr_pct = (atr_14 / current_close) * 100 if current_close > 0 else 0.0
            
            features = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'price': float(current_close),
                'volume': float(current_volume),
                'momentum_1d': round(momentum_1d, 2),
                'momentum_5d': round(momentum_5d, 2),
                'momentum_30d': round(momentum_30d, 2),
                'atr_14': round(atr_14, 4),
                'atr_pct': round(atr_pct, 2),
                'avg_vol_30d': float(avg_vol_30d),
                'data_points': len(ohlcv_data)
            }
            
            return features
            
        except Exception as e:
            logger.error(f"Error calculating features for {symbol}: {e}")
            return {}
    
    def store_features(self, symbol: str, features: Dict):
        """Store computed features in Redis"""
        try:
            if not features:
                return False
                
            # Store in Redis hash with 24-hour expiry
            key = f"features:{symbol}"
            self.redis_client.hset(key, mapping=features)
            self.redis_client.expire(key, 86400)  # 24 hours
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing features for {symbol}: {e}")
            return False
    
    async def get_universe_symbols(self) -> List[str]:
        """Get list of symbols to precompute (from recent discovery or static list)"""
        try:
            # Try to get recent candidates from cache
            cached_candidates = self.redis_client.get("bms:candidates:all")
            if cached_candidates:
                candidates = json.loads(cached_candidates)
                symbols = [c['symbol'] for c in candidates if isinstance(c, dict)]
                if symbols:
                    logger.info(f"Using {len(symbols)} symbols from cached candidates")
                    return symbols
            
            # Fallback: use a curated list of popular symbols
            popular_symbols = [
                # Mega caps
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'BRK.B',
                'JPM', 'JNJ', 'V', 'PG', 'UNH', 'HD', 'DIS', 'MA', 'PYPL', 'BAC',
                
                # Growth/Tech
                'NFLX', 'CRM', 'ADBE', 'INTC', 'AMD', 'ORCL', 'UBER', 'SQ', 'SHOP',
                'ZOOM', 'DOCU', 'ROKU', 'TWLO', 'SNOW', 'PLTR', 'DDOG', 'CRWD',
                
                # Meme/Popular
                'GME', 'AMC', 'BB', 'NOK', 'SPCE', 'WISH', 'CLOV', 'SOFI', 'HOOD',
                
                # ETFs (will be filtered out by discovery but useful for cache)
                'SPY', 'QQQ', 'IWM', 'VTI', 'VOO', 'ARKK', 'XLF', 'XLK', 'XLE'
            ]
            
            logger.info(f"Using {len(popular_symbols)} popular symbols for precompute")
            return popular_symbols
            
        except Exception as e:
            logger.error(f"Error getting universe symbols: {e}")
            return []
    
    async def run_precompute(self, max_symbols: int = 1000):
        """Main precompute process"""
        try:
            start_time = time.time()
            logger.info("🌙 Starting nightly features precompute...")
            
            # Get symbols to process
            symbols = await self.get_universe_symbols()
            if not symbols:
                logger.error("No symbols to process")
                return
            
            # Limit processing for nightly job
            if len(symbols) > max_symbols:
                symbols = symbols[:max_symbols]
            
            logger.info(f"Processing {len(symbols)} symbols...")
            
            success_count = 0
            error_count = 0
            
            # Process with async session
            connector = aiohttp.TCPConnector(limit=5)
            timeout = aiohttp.ClientTimeout(total=60)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                for i, symbol in enumerate(symbols, 1):
                    try:
                        # Get historical data
                        historical_data = await self.get_historical_data(session, symbol)
                        if not historical_data:
                            error_count += 1
                            continue
                        
                        # Calculate features
                        features = self.calculate_features(historical_data, symbol)
                        if not features:
                            error_count += 1
                            continue
                        
                        # Store in Redis
                        if self.store_features(symbol, features):
                            success_count += 1
                            logger.debug(f"✅ {symbol}: 1d={features['momentum_1d']:.1f}%, "
                                       f"5d={features['momentum_5d']:.1f}%, ATR={features['atr_pct']:.1f}%")
                        else:
                            error_count += 1
                        
                        # Progress update
                        if i % 50 == 0 or i == len(symbols):
                            elapsed = time.time() - start_time
                            rate = i / elapsed if elapsed > 0 else 0
                            logger.info(f"Progress: {i}/{len(symbols)} ({rate:.1f}/sec) | "
                                      f"Success: {success_count}, Errors: {error_count}")
                        
                        # Rate limiting
                        await asyncio.sleep(1.0 / self.rate_limit_per_sec)
                        
                    except Exception as e:
                        logger.error(f"Error processing {symbol}: {e}")
                        error_count += 1
            
            # Final statistics
            elapsed = time.time() - start_time
            logger.info(f"🎯 Precompute complete in {elapsed:.1f}s:")
            logger.info(f"  ✅ Success: {success_count}/{len(symbols)} symbols")
            logger.info(f"  ❌ Errors: {error_count}")
            logger.info(f"  📈 Rate: {len(symbols)/elapsed:.1f} symbols/sec")
            
            # Store metadata
            metadata = {
                'timestamp': datetime.now().isoformat(),
                'symbols_processed': len(symbols),
                'success_count': success_count,
                'error_count': error_count,
                'duration_seconds': round(elapsed, 1)
            }
            self.redis_client.set("features:metadata", json.dumps(metadata), ex=86400)
            
        except Exception as e:
            logger.error(f"Precompute failed: {e}")

async def main():
    """Main entry point"""
    polygon_key = os.getenv('POLYGON_API_KEY')
    if not polygon_key:
        logger.error("POLYGON_API_KEY environment variable required")
        sys.exit(1)
    
    redis_url = os.getenv('REDIS_URL')
    max_symbols = int(os.getenv('PRECOMPUTE_MAX_SYMBOLS', '1000'))
    
    precomputer = DailyFeaturesPrecomputer(polygon_key, redis_url)
    await precomputer.run_precompute(max_symbols)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Precompute interrupted by user")
    except Exception as e:
        logger.error(f"Precompute failed: {e}")
        sys.exit(1)