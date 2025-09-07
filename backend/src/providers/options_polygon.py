"""
Polygon Options Provider for Live Options Data
ATM IV, IV Percentile, Call/Put Flow, and Options Metrics
"""
import json
import time
import logging
import requests
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
import redis
import os
from dataclasses import dataclass
import statistics

logger = logging.getLogger(__name__)

@dataclass
class OptionsFlow:
    symbol: str
    atm_iv: float
    iv_percentile: float  # 252-day
    call_volume: int
    put_volume: int
    call_put_ratio: float
    total_volume: int
    gamma_exposure: float
    timestamp: int
    
    def to_redis(self) -> str:
        return json.dumps({
            "atm_iv": self.atm_iv,
            "iv_percentile": self.iv_percentile,
            "call_volume": self.call_volume,
            "put_volume": self.put_volume,
            "call_put_ratio": self.call_put_ratio,
            "total_volume": self.total_volume,
            "gamma_exposure": self.gamma_exposure,
            "ts": self.timestamp,
            "source": "polygon_options",
            "confidence": 0.95,
            "latency_ms": int((time.time() * 1000) - self.timestamp)
        })

class PolygonOptionsProvider:
    """
    Live Options data provider using Polygon.io Options API
    Computes ATM IV, IV percentile, call/put ratios
    """
    
    def __init__(self, api_key: str, redis_client: redis.Redis):
        self.api_key = api_key
        self.redis = redis_client
        self.base_url = "https://api.polygon.io"
        self.session = requests.Session()
        self.session.headers.update({'Authorization': f'Bearer {api_key}'})
        
        # Cache for IV history (for percentile calculation)
        self.iv_history: Dict[str, List[Tuple[int, float]]] = {}  # symbol -> [(timestamp, iv)]
        
        self.stats = {
            'requests_made': 0,
            'options_processed': 0,
            'errors': 0,
            'cache_hits': 0,
            'last_request_time': 0
        }
    
    async def get_options_flow(self, symbol: str, stock_price: float) -> Optional[OptionsFlow]:
        """Get comprehensive options flow data for symbol"""
        try:
            # Check Redis cache first
            cached = self._get_cached_flow(symbol)
            if cached:
                self.stats['cache_hits'] += 1
                return cached
            
            # Get options chain for ATM strikes
            chain_data = await self._get_options_chain(symbol, stock_price)
            if not chain_data:
                return None
            
            # Calculate metrics
            flow = self._calculate_options_metrics(symbol, stock_price, chain_data)
            if flow:
                # Cache in Redis
                key = f"feat:options:{symbol}"
                self.redis.setex(key, 60, flow.to_redis())  # 60s TTL
                self.stats['options_processed'] += 1
            
            return flow
            
        except Exception as e:
            logger.error(f"❌ Options flow error for {symbol}: {e}")
            self.stats['errors'] += 1
            return None
    
    def _get_cached_flow(self, symbol: str) -> Optional[OptionsFlow]:
        """Check Redis cache for recent options data"""
        try:
            key = f"feat:options:{symbol}"
            cached_data = self.redis.get(key)
            if cached_data:
                data = json.loads(cached_data)
                # Check if still fresh (< 60s)
                age_ms = (time.time() * 1000) - data['ts']
                if age_ms < 60000:  # 60s freshness
                    return OptionsFlow(
                        symbol=symbol,
                        atm_iv=data['atm_iv'],
                        iv_percentile=data['iv_percentile'],
                        call_volume=data['call_volume'],
                        put_volume=data['put_volume'],
                        call_put_ratio=data['call_put_ratio'],
                        total_volume=data['total_volume'],
                        gamma_exposure=data['gamma_exposure'],
                        timestamp=data['ts']
                    )
            return None
        except Exception as e:
            logger.debug(f"Cache read error for {symbol}: {e}")
            return None
    
    async def _get_options_chain(self, symbol: str, stock_price: float) -> Optional[dict]:
        """Get options chain data from Polygon"""
        try:
            self.stats['requests_made'] += 1
            self.stats['last_request_time'] = time.time()
            
            # Get next Friday expiration
            expiry = self._get_next_friday()
            
            # Find ATM strikes (within 5% of current price)
            strike_range = stock_price * 0.05
            
            # Get options contracts
            url = f"{self.base_url}/v3/reference/options/contracts"
            params = {
                'underlying_ticker': symbol,
                'expiration_date': expiry.strftime('%Y-%m-%d'),
                'strike_price.gte': stock_price - strike_range,
                'strike_price.lte': stock_price + strike_range,
                'limit': 50,
                'apikey': self.api_key
            }
            
            response = self.session.get(url, params=params, timeout=5)
            if response.status_code != 200:
                logger.error(f"❌ Options chain API error: {response.status_code}")
                return None
            
            data = response.json()
            contracts = data.get('results', [])
            
            if not contracts:
                logger.debug(f"No options contracts found for {symbol}")
                return None
            
            # Get market data for these contracts
            return await self._get_contracts_market_data(contracts)
            
        except Exception as e:
            logger.error(f"❌ Options chain request error: {e}")
            self.stats['errors'] += 1
            return None
    
    async def _get_contracts_market_data(self, contracts: List[dict]) -> dict:
        """Get market data for options contracts"""
        try:
            # Group by call/put
            calls = [c for c in contracts if c['contract_type'] == 'call']
            puts = [c for c in contracts if c['contract_type'] == 'put']
            
            # Get snapshot data for all contracts
            tickers = [c['ticker'] for c in contracts]
            
            url = f"{self.base_url}/v3/snapshot/options/{'/'.join(tickers[:20])}"  # Limit batch size
            params = {'apikey': self.api_key}
            
            response = self.session.get(url, params=params, timeout=5)
            if response.status_code != 200:
                return {'calls': calls, 'puts': puts, 'market_data': {}}
            
            data = response.json()
            results = data.get('results', [])
            
            # Index market data by ticker
            market_data = {}
            for result in results:
                if 'value' in result:
                    ticker = result['value']['underlying_ticker'] 
                    market_data[ticker] = result['value']
            
            return {
                'calls': calls,
                'puts': puts, 
                'market_data': market_data
            }
            
        except Exception as e:
            logger.error(f"❌ Contract market data error: {e}")
            return {'calls': [], 'puts': [], 'market_data': {}}
    
    def _calculate_options_metrics(self, symbol: str, stock_price: float, chain_data: dict) -> Optional[OptionsFlow]:
        """Calculate comprehensive options metrics"""
        try:
            calls = chain_data.get('calls', [])
            puts = chain_data.get('puts', [])
            market_data = chain_data.get('market_data', {})
            
            if not calls and not puts:
                return None
            
            # Find ATM options (closest to stock price)
            atm_call = self._find_atm_option(calls, stock_price)
            atm_put = self._find_atm_option(puts, stock_price)
            
            # Calculate ATM IV (average of call and put if both exist)
            atm_iv = self._calculate_atm_iv(atm_call, atm_put, market_data)
            if atm_iv is None:
                atm_iv = 0.0
            
            # Calculate IV percentile (252-day)
            iv_percentile = self._calculate_iv_percentile(symbol, atm_iv)
            
            # Calculate call/put volumes
            call_volume = sum(self._get_volume(c, market_data) for c in calls)
            put_volume = sum(self._get_volume(c, market_data) for c in puts)
            total_volume = call_volume + put_volume
            
            # Calculate call/put ratio
            call_put_ratio = call_volume / max(put_volume, 1)
            
            # Estimate gamma exposure (simplified)
            gamma_exposure = self._estimate_gamma_exposure(calls + puts, stock_price, market_data)
            
            return OptionsFlow(
                symbol=symbol,
                atm_iv=atm_iv,
                iv_percentile=iv_percentile,
                call_volume=call_volume,
                put_volume=put_volume,
                call_put_ratio=call_put_ratio,
                total_volume=total_volume,
                gamma_exposure=gamma_exposure,
                timestamp=int(time.time() * 1000)
            )
            
        except Exception as e:
            logger.error(f"❌ Options metrics calculation error: {e}")
            return None
    
    def _find_atm_option(self, options: List[dict], stock_price: float) -> Optional[dict]:
        """Find the at-the-money option closest to stock price"""
        if not options:
            return None
        
        return min(options, key=lambda o: abs(o['strike_price'] - stock_price))
    
    def _calculate_atm_iv(self, atm_call: Optional[dict], atm_put: Optional[dict], market_data: dict) -> Optional[float]:
        """Calculate ATM implied volatility"""
        ivs = []
        
        if atm_call:
            call_data = market_data.get(atm_call['ticker'], {})
            if 'implied_volatility' in call_data:
                ivs.append(call_data['implied_volatility'])
        
        if atm_put:
            put_data = market_data.get(atm_put['ticker'], {})
            if 'implied_volatility' in put_data:
                ivs.append(put_data['implied_volatility'])
        
        return statistics.mean(ivs) if ivs else None
    
    def _calculate_iv_percentile(self, symbol: str, current_iv: float) -> float:
        """Calculate 252-day IV percentile"""
        try:
            # Add current IV to history
            now = int(time.time())
            if symbol not in self.iv_history:
                self.iv_history[symbol] = []
            
            self.iv_history[symbol].append((now, current_iv))
            
            # Keep only last 252 trading days (about 1 year)
            cutoff = now - (252 * 24 * 60 * 60)  # 252 days ago
            self.iv_history[symbol] = [(ts, iv) for ts, iv in self.iv_history[symbol] if ts > cutoff]
            
            # Calculate percentile
            ivs = [iv for _, iv in self.iv_history[symbol]]
            if len(ivs) < 10:  # Need minimum history
                return 50.0  # Default to median
            
            sorted_ivs = sorted(ivs)
            rank = sum(1 for iv in sorted_ivs if iv < current_iv)
            percentile = (rank / len(sorted_ivs)) * 100
            
            return percentile
            
        except Exception as e:
            logger.error(f"❌ IV percentile calculation error: {e}")
            return 50.0  # Default
    
    def _get_volume(self, option: dict, market_data: dict) -> int:
        """Get volume for an option contract"""
        ticker = option['ticker']
        data = market_data.get(ticker, {})
        return data.get('day', {}).get('volume', 0)
    
    def _estimate_gamma_exposure(self, options: List[dict], stock_price: float, market_data: dict) -> float:
        """Estimate total gamma exposure (simplified calculation)"""
        try:
            total_gamma = 0
            for option in options:
                data = market_data.get(option['ticker'], {})
                greeks = data.get('greeks', {})
                gamma = greeks.get('gamma', 0)
                volume = data.get('day', {}).get('volume', 0)
                open_interest = data.get('open_interest', 0)
                
                # Estimate exposure: gamma * (volume + open_interest) * stock_price
                exposure = gamma * (volume + open_interest) * stock_price
                total_gamma += exposure
            
            return total_gamma / 1000000  # Scale to millions
            
        except Exception as e:
            logger.debug(f"Gamma calculation error: {e}")
            return 0.0
    
    def _get_next_friday(self) -> datetime:
        """Get next Friday for options expiration"""
        today = datetime.now(timezone.utc).date()
        days_ahead = 4 - today.weekday()  # Friday is 4
        if days_ahead <= 0:  # Today is Friday or weekend
            days_ahead += 7
        return datetime.combine(today + timedelta(days=days_ahead), datetime.min.time())
    
    def get_stats(self) -> dict:
        """Get provider statistics"""
        return {
            **self.stats,
            'iv_history_symbols': len(self.iv_history),
            'avg_iv_history_points': statistics.mean([len(hist) for hist in self.iv_history.values()]) if self.iv_history else 0
        }

# Singleton instance
_options_provider: Optional[PolygonOptionsProvider] = None

def get_options_provider() -> PolygonOptionsProvider:
    """Get singleton options provider"""
    global _options_provider
    
    if _options_provider is None:
        api_key = os.getenv('POLYGON_API_KEY')
        if not api_key:
            raise ValueError("POLYGON_API_KEY environment variable required")
        
        from backend.src.lib.redis_client import get_redis_client
        redis_client = get_redis_client()
        
        _options_provider = PolygonOptionsProvider(api_key, redis_client)
    
    return _options_provider

async def get_options_data(symbol: str, stock_price: float) -> Optional[dict]:
    """Get options data for a symbol"""
    try:
        provider = get_options_provider()
        flow = await provider.get_options_flow(symbol, stock_price)
        
        if flow:
            return {
                'symbol': flow.symbol,
                'atm_iv': flow.atm_iv,
                'iv_percentile': flow.iv_percentile,
                'call_volume': flow.call_volume,
                'put_volume': flow.put_volume,
                'call_put_ratio': flow.call_put_ratio,
                'total_volume': flow.total_volume,
                'gamma_exposure': flow.gamma_exposure,
                'source': 'polygon_options',
                'confidence': 0.95,
                'timestamp': flow.timestamp
            }
        return None
        
    except Exception as e:
        logger.error(f"❌ Options data error for {symbol}: {e}")
        return None

def get_options_stats() -> dict:
    """Get options provider stats"""
    try:
        provider = get_options_provider()
        return provider.get_stats()
    except:
        return {"error": "Options provider not initialized"}