"""
Feature Store with Fail-Closed Freshness Enforcement
Reads live WebSocket data first, falls back to REST, enforces strict freshness
"""
import json
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
import redis
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class MarketSession(Enum):
    PREMARKET = "premarket"
    REGULAR = "regular" 
    AFTERHOURS = "afterhours"
    CLOSED = "closed"

@dataclass
class FeatureSet:
    """Complete feature set for a symbol with provenance"""
    symbol: str
    
    # Price/Volume features
    price: Optional[float] = None
    volume: Optional[int] = None
    vwap: Optional[float] = None
    rel_vol: Optional[float] = None
    atr_pct: Optional[float] = None
    
    # Options features
    atm_iv: Optional[float] = None
    iv_percentile: Optional[float] = None
    call_put_ratio: Optional[float] = None
    
    # Fundamental features
    short_interest: Optional[float] = None
    float_shares: Optional[float] = None
    
    # Provenance and freshness
    provenance: Dict[str, Dict] = None
    freshness_failures: List[str] = None
    is_fresh: bool = True
    session: MarketSession = MarketSession.REGULAR
    
    def __post_init__(self):
        if self.provenance is None:
            self.provenance = {}
        if self.freshness_failures is None:
            self.freshness_failures = []

class FeatureStore:
    """
    Centralized feature store with fail-closed freshness enforcement
    Prioritizes live WebSocket data, enforces strict staleness limits
    """
    
    def __init__(self, redis_client: redis.Redis, config: Dict):
        self.redis = redis_client
        self.config = config
        self.session_cache: Dict[str, Tuple[MarketSession, float]] = {}  # Cache session detection
        
        # Load freshness thresholds from config
        self.thresholds = config.get('freshness_thresholds', {})
        self.market_sessions = config.get('market_sessions', {})
        self.fail_closed = config.get('fail_closed', {})
        
        self.stats = {
            'features_requested': 0,
            'cache_hits': 0,
            'freshness_failures': 0,
            'symbols_dropped': 0,
            'last_request_time': 0
        }
    
    def get_market_session(self) -> MarketSession:
        """Determine current market session"""
        try:
            now = datetime.now(timezone.utc)
            hour = now.hour
            minute = now.minute
            weekday = now.weekday()
            
            # Weekend = closed
            if weekday >= 5:  # Saturday=5, Sunday=6
                return MarketSession.CLOSED
            
            # Convert to EST (approximate)
            est_hour = (hour - 5) % 24
            
            if est_hour < 4:  # Before 4 AM EST
                return MarketSession.CLOSED
            elif est_hour < 9 or (est_hour == 9 and minute < 30):  # 4 AM - 9:30 AM EST
                return MarketSession.PREMARKET
            elif est_hour < 16:  # 9:30 AM - 4 PM EST
                return MarketSession.REGULAR
            elif est_hour < 20:  # 4 PM - 8 PM EST
                return MarketSession.AFTERHOURS
            else:  # After 8 PM EST
                return MarketSession.CLOSED
                
        except Exception as e:
            logger.error(f"❌ Market session detection error: {e}")
            return MarketSession.REGULAR  # Safe default
    
    def get_freshness_thresholds(self, session: MarketSession) -> Dict[str, float]:
        """Get freshness thresholds for current market session"""
        base_thresholds = {
            'quotes_sec': self.thresholds.get('quotes_sec', 2),
            'bars_1m_sec': self.thresholds.get('bars_1m_sec', 15),
            'options_sec': self.thresholds.get('options_sec', 60),
            'short_interest_days': self.thresholds.get('short_interest_days', 20),
            'short_volume_hours': self.thresholds.get('short_volume_hours', 36)
        }
        
        # Apply session multipliers
        session_config = self.market_sessions.get(session.value, {})
        multiplier = session_config.get('freshness_multiplier', 1.0)
        
        # Override specific thresholds for session
        if 'quotes_sec' in session_config:
            base_thresholds['quotes_sec'] = session_config['quotes_sec']
        else:
            base_thresholds['quotes_sec'] *= multiplier
            
        if 'bars_1m_sec' in session_config:
            base_thresholds['bars_1m_sec'] = session_config['bars_1m_sec']
        else:
            base_thresholds['bars_1m_sec'] *= multiplier
        
        return base_thresholds
    
    async def get_features(self, symbols: List[str]) -> Dict[str, FeatureSet]:
        """Get feature sets for symbols with fail-closed freshness enforcement"""
        self.stats['features_requested'] += len(symbols)
        self.stats['last_request_time'] = time.time()
        
        session = self.get_market_session()
        thresholds = self.get_freshness_thresholds(session)
        
        feature_sets = {}
        stale_symbols = []
        
        for symbol in symbols:
            try:
                feature_set = await self._build_feature_set(symbol, session, thresholds)
                
                if feature_set.is_fresh:
                    feature_sets[symbol] = feature_set
                else:
                    stale_symbols.append(symbol)
                    self.stats['freshness_failures'] += 1
                    logger.warning(f"🚫 Dropping {symbol}: freshness failures: {feature_set.freshness_failures}")
                    
            except Exception as e:
                logger.error(f"❌ Feature extraction error for {symbol}: {e}")
                stale_symbols.append(symbol)
        
        # Fail-closed enforcement
        stale_percentage = len(stale_symbols) / len(symbols) if symbols else 0
        max_stale = self.fail_closed.get('max_stale_percent', 40) / 100
        
        if stale_percentage > max_stale:
            logger.error(f"🚫 FAIL-CLOSED: {stale_percentage:.1%} symbols stale (>{max_stale:.1%} threshold)")
            self.stats['symbols_dropped'] += len(feature_sets)
            return {}  # Return empty - fail closed
        
        return feature_sets
    
    async def _build_feature_set(self, symbol: str, session: MarketSession, thresholds: Dict) -> FeatureSet:
        """Build complete feature set for a symbol"""
        feature_set = FeatureSet(symbol=symbol, session=session)
        now_ms = time.time() * 1000
        
        # 1. Price/Volume features (live priority)
        await self._load_price_volume_features(symbol, feature_set, thresholds, now_ms)
        
        # 2. Options features (live when available)
        await self._load_options_features(symbol, feature_set, thresholds, now_ms)
        
        # 3. Fundamental features (longer TTL acceptable)
        await self._load_fundamental_features(symbol, feature_set, thresholds, now_ms)
        
        # 4. Calculate derived features
        self._calculate_derived_features(feature_set)
        
        # 5. Check overall freshness
        self._assess_freshness(feature_set, thresholds)
        
        return feature_set
    
    async def _load_price_volume_features(self, symbol: str, fs: FeatureSet, thresholds: Dict, now_ms: float):
        """Load price/volume features with live WebSocket priority"""
        
        # Try live quote first
        quote_data = self._get_redis_feature(f"feat:quotes:{symbol}")
        if quote_data:
            age_ms = now_ms - quote_data['ts']
            age_sec = age_ms / 1000
            
            if age_sec <= thresholds['quotes_sec']:
                fs.price = quote_data['price']
                fs.provenance['price'] = {
                    'source': quote_data['source'],
                    'age_sec': age_sec,
                    'confidence': 0.98  # Live data high confidence
                }
            else:
                fs.freshness_failures.append(f"quotes_stale_{age_sec:.1f}s")
        else:
            fs.freshness_failures.append("quotes_missing")
        
        # Try live bars for volume/VWAP
        bar_data = self._get_redis_feature(f"feat:bars_1m:{symbol}")
        if bar_data:
            age_ms = now_ms - bar_data['close_time']
            age_sec = age_ms / 1000
            
            if age_sec <= thresholds['bars_1m_sec']:
                fs.volume = bar_data.get('v')
                fs.provenance['volume'] = {
                    'source': bar_data['source'],
                    'age_sec': age_sec,
                    'confidence': 0.95
                }
            else:
                fs.freshness_failures.append(f"bars_stale_{age_sec:.1f}s")
        else:
            fs.freshness_failures.append("bars_missing")
        
        # Try VWAP
        vwap_data = self._get_redis_feature(f"feat:vwap:{symbol}")
        if vwap_data:
            age_ms = now_ms - vwap_data['ts']
            age_sec = age_ms / 1000
            
            if age_sec <= thresholds['bars_1m_sec']:  # Same threshold as bars
                fs.vwap = vwap_data['vwap']
                fs.provenance['vwap'] = {
                    'source': vwap_data['source'],
                    'age_sec': age_sec,
                    'confidence': 0.90
                }
    
    async def _load_options_features(self, symbol: str, fs: FeatureSet, thresholds: Dict, now_ms: float):
        """Load options features from live Polygon data"""
        
        options_data = self._get_redis_feature(f"feat:options:{symbol}")
        if options_data:
            age_ms = now_ms - options_data['ts']
            age_sec = age_ms / 1000
            
            if age_sec <= thresholds['options_sec']:
                fs.atm_iv = options_data.get('atm_iv')
                fs.iv_percentile = options_data.get('iv_percentile')
                fs.call_put_ratio = options_data.get('call_put_ratio')
                
                fs.provenance['options'] = {
                    'source': options_data['source'],
                    'age_sec': age_sec,
                    'confidence': options_data.get('confidence', 0.85)
                }
            else:
                fs.freshness_failures.append(f"options_stale_{age_sec:.1f}s")
        else:
            # Options are optional for some symbols, don't fail
            logger.debug(f"No options data for {symbol}")
    
    async def _load_fundamental_features(self, symbol: str, fs: FeatureSet, thresholds: Dict, now_ms: float):
        """Load fundamental features (longer TTL acceptable)"""
        
        # Short interest (FINRA - updated less frequently)
        si_data = self._get_redis_feature(f"feat:short_interest:{symbol}")
        if si_data:
            age_hours = (now_ms - si_data['ts']) / (1000 * 3600)
            max_age_hours = thresholds['short_interest_days'] * 24
            
            if age_hours <= max_age_hours:
                fs.short_interest = si_data.get('short_interest_pct')
                fs.provenance['short_interest'] = {
                    'source': si_data['source'],
                    'age_hours': age_hours,
                    'confidence': si_data.get('confidence', 0.95)  # FINRA high confidence
                }
        
        # Float shares (relatively static)
        float_data = self._get_redis_feature(f"feat:float:{symbol}")
        if float_data:
            fs.float_shares = float_data.get('float_shares')
            fs.provenance['float'] = {
                'source': float_data.get('source', 'static'),
                'confidence': 0.90
            }
    
    def _calculate_derived_features(self, fs: FeatureSet):
        """Calculate derived features from base features"""
        
        # RelVol calculation (if we have current volume and historical average)
        if fs.volume:
            # Try to get 30-day average volume
            avg_vol_data = self._get_redis_feature(f"feat:avg_volume_30d:{fs.symbol}")
            if avg_vol_data and avg_vol_data.get('avg_volume'):
                fs.rel_vol = fs.volume / avg_vol_data['avg_volume']
                fs.provenance['rel_vol'] = {
                    'source': 'calculated',
                    'confidence': 0.85
                }
        
        # ATR% calculation (simplified - would need historical data)
        # For now, stub with basic volatility estimate
        if fs.price:
            # This is oversimplified - real ATR needs historical high/low/close data
            fs.atr_pct = 0.04  # Placeholder
            fs.provenance['atr_pct'] = {
                'source': 'estimated',
                'confidence': 0.60  # Low confidence for estimate
            }
    
    def _assess_freshness(self, fs: FeatureSet, thresholds: Dict):
        """Assess overall freshness of feature set"""
        
        # Critical features that must be fresh
        critical_failures = [
            f for f in fs.freshness_failures 
            if any(keyword in f for keyword in ['quotes_stale', 'quotes_missing', 'bars_stale'])
        ]
        
        # Fail if critical features are stale
        if critical_failures:
            fs.is_fresh = False
            logger.debug(f"❌ {fs.symbol} failed freshness: {critical_failures}")
        else:
            fs.is_fresh = True
    
    def _get_redis_feature(self, key: str) -> Optional[Dict]:
        """Get feature from Redis with error handling"""
        try:
            data = self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.debug(f"Redis read error for {key}: {e}")
            return None
    
    def get_stats(self) -> Dict:
        """Get feature store statistics"""
        return {
            **self.stats,
            'session_cache_size': len(self.session_cache),
            'current_session': self.get_market_session().value
        }

# Singleton instance
_feature_store: Optional[FeatureStore] = None

def get_feature_store(config: Dict = None) -> FeatureStore:
    """Get singleton feature store"""
    global _feature_store
    
    if _feature_store is None:
        if config is None:
            # Load from active config
            import json
            try:
                with open('/Users/michaelmote/Desktop/AMC-TRADER/backend/calibration/active.json', 'r') as f:
                    config = json.load(f)
            except:
                config = {}  # Use defaults
        
        from backend.src.lib.redis_client import get_redis_client
        redis_client = get_redis_client()
        
        _feature_store = FeatureStore(redis_client, config)
    
    return _feature_store

def get_feature_store_stats() -> Dict:
    """Get feature store statistics"""
    try:
        store = get_feature_store()
        return store.get_stats()
    except:
        return {"error": "Feature store not initialized"}