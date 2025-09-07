"""
Squeeze Detector
Analyzes short squeeze opportunity indicators using free-data providers
"""

import structlog
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import asyncio

logger = structlog.get_logger()

class SqueezeDetector:
    """
    Detects squeeze opportunities using multiple data sources
    - Float tightness analysis
    - Short interest and borrow stress
    - Days to cover ratio (DTCR)
    - Short volume ratio (SVR) patterns
    - Options gamma potential
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.weights = {
            'float_tightness': 0.3,   # Float size and availability
            'short_metrics': 0.4,     # SI%, DTCR, borrow stress
            'options_gamma': 0.2,     # Call/put ratios and gamma
            'volume_pressure': 0.1    # Volume-based squeeze indicators
        }
        
        # Squeeze thresholds
        self.thresholds = {
            'small_float_max': 75_000_000,    # 75M shares
            'large_float_min': 150_000_000,   # 150M shares
            'high_si_min': 15.0,              # 15% short interest
            'extreme_si_min': 25.0,           # 25% short interest
            'high_dtcr_min': 5.0,             # 5 days to cover
            'extreme_dtcr_min': 10.0,         # 10 days to cover
            'high_svr_min': 40.0,             # 40% short volume ratio
            'borrow_stress_min': 60.0         # 60/100 borrow stress
        }
    
    async def analyze(self, symbol: str, enriched_data: Dict, providers: Optional[Dict] = None) -> Dict:
        """
        Analyze squeeze opportunity potential
        Returns: {
            'score': float (0-1),
            'confidence': float (0-1),
            'signals': List[str],
            'metrics': Dict,
            'squeeze_type': str,
            'catalyst_strength': str
        }
        """
        try:
            signals = []
            metrics = {}
            
            # 1. Float Tightness Analysis
            float_score = self._analyze_float_tightness(enriched_data, signals, metrics)
            
            # 2. Short Metrics Analysis (SI%, DTCR, SVR, borrow stress)
            short_score = await self._analyze_short_metrics(symbol, enriched_data, signals, metrics, providers)
            
            # 3. Options Gamma Analysis
            gamma_score = await self._analyze_options_gamma(symbol, enriched_data, signals, metrics, providers)
            
            # 4. Volume Pressure Analysis  
            volume_score = self._analyze_volume_pressure(enriched_data, signals, metrics)
            
            # Calculate composite squeeze score
            composite_score = (
                float_score * self.weights['float_tightness'] +
                short_score * self.weights['short_metrics'] +
                gamma_score * self.weights['options_gamma'] +
                volume_score * self.weights['volume_pressure']
            )
            
            # Determine squeeze type and catalyst strength
            squeeze_type = self._classify_squeeze_type(metrics, signals)
            catalyst_strength = self._assess_catalyst_strength(composite_score, signals)
            
            # Calculate overall confidence
            confidence = self._calculate_confidence(enriched_data, metrics, providers)
            
            result = {
                'score': round(composite_score, 4),
                'confidence': round(confidence, 3),
                'signals': signals,
                'metrics': metrics,
                'squeeze_type': squeeze_type,
                'catalyst_strength': catalyst_strength,
                'detector': 'squeeze',
                'components': {
                    'float_score': round(float_score, 3),
                    'short_score': round(short_score, 3),
                    'gamma_score': round(gamma_score, 3),
                    'volume_score': round(volume_score, 3)
                }
            }
            
            logger.debug("Squeeze analysis complete", 
                        symbol=symbol, score=composite_score,
                        squeeze_type=squeeze_type, signals=len(signals))
            
            return result
            
        except Exception as e:
            logger.error("Squeeze analysis failed", symbol=symbol, error=str(e))
            return self._empty_result()
    
    def _analyze_float_tightness(self, enriched_data: Dict, signals: List, metrics: Dict) -> float:
        """Analyze float size and tightness"""
        float_shares = enriched_data.get('float_shares', 0)
        shares_outstanding = enriched_data.get('shares_outstanding', float_shares)
        
        metrics['float_shares'] = float_shares
        metrics['shares_outstanding'] = shares_outstanding
        
        if float_shares == 0:
            return 0.0
        
        # Float tightness scoring
        if float_shares <= 10_000_000:  # Ultra-small float
            signals.append('micro_float_<10M')
            float_score = 1.0
        elif float_shares <= 25_000_000:  # Small float
            signals.append('small_float_<25M')
            float_score = 0.8
        elif float_shares <= self.thresholds['small_float_max']:  # Medium-small float
            signals.append('medium_float_<75M')
            float_score = 0.6
        elif float_shares >= self.thresholds['large_float_min']:  # Large float (can still squeeze with strong metrics)
            signals.append('large_float_>150M')
            float_score = 0.3
        else:
            float_score = 0.4  # Medium float
        
        # Float-to-outstanding ratio bonus
        if shares_outstanding > 0:
            float_ratio = float_shares / shares_outstanding
            metrics['float_ratio'] = round(float_ratio, 3)
            
            if float_ratio <= 0.5:  # Less than 50% of shares in float
                signals.append('restricted_float')
                float_score = min(1.0, float_score + 0.1)
        
        return float_score
    
    async def _analyze_short_metrics(self, symbol: str, enriched_data: Dict, signals: List, metrics: Dict, providers: Optional[Dict]) -> float:
        """Analyze short interest and borrow metrics"""
        score_components = []
        
        # Get short interest data (from FINRA or enriched data)
        si_pct = enriched_data.get('short_interest_pct', 0)
        if providers and 'finra_short' in providers:
            try:
                si_data = await providers['finra_short'].get_short_interest(symbol)
                if si_data.get('staleness_policy_pass', False):
                    si_pct = si_data.get('short_interest_pct', si_pct)
                    metrics['si_source'] = 'finra'
                    metrics['si_freshness'] = si_data.get('latency_sec', 0)
            except Exception as e:
                logger.warning("FINRA short interest fetch failed", symbol=symbol, error=str(e))
        
        metrics['short_interest_pct'] = si_pct
        
        # Score short interest
        if si_pct >= self.thresholds['extreme_si_min']:
            signals.append(f'extreme_si_{si_pct:.1f}%')
            score_components.append(1.0)
        elif si_pct >= self.thresholds['high_si_min']:
            signals.append(f'high_si_{si_pct:.1f}%')
            score_components.append(0.7)
        elif si_pct >= 8.0:
            signals.append(f'moderate_si_{si_pct:.1f}%')
            score_components.append(0.4)
        else:
            score_components.append(0.1)
        
        # Get short volume data
        svr = enriched_data.get('short_volume_ratio', 0)
        if providers and 'finra_short' in providers:
            try:
                sv_data = await providers['finra_short'].get_daily_short_volume(symbol)
                if sv_data.get('staleness_policy_pass', False):
                    svr = sv_data.get('svr', svr)
                    metrics['svr_source'] = 'finra'
            except Exception as e:
                logger.warning("FINRA short volume fetch failed", symbol=symbol, error=str(e))
        
        metrics['short_volume_ratio'] = svr
        
        # Score short volume ratio
        if svr >= 60.0:
            signals.append(f'extreme_svr_{svr:.1f}%')
            score_components.append(0.8)
        elif svr >= self.thresholds['high_svr_min']:
            signals.append(f'high_svr_{svr:.1f}%')
            score_components.append(0.6)
        else:
            score_components.append(0.2)
        
        # Calculate DTCR (Days to Cover Ratio)
        adv_30 = enriched_data.get('avg_volume_30d', enriched_data.get('volume', 1))
        if adv_30 > 0 and si_pct > 0:
            float_shares = enriched_data.get('float_shares', 0)
            short_shares = (si_pct / 100) * float_shares if float_shares > 0 else 0
            dtcr = short_shares / adv_30 if adv_30 > 0 else 0
            
            metrics['dtcr'] = round(dtcr, 2)
            
            if dtcr >= self.thresholds['extreme_dtcr_min']:
                signals.append(f'extreme_dtcr_{dtcr:.1f}d')
                score_components.append(1.0)
            elif dtcr >= self.thresholds['high_dtcr_min']:
                signals.append(f'high_dtcr_{dtcr:.1f}d')
                score_components.append(0.7)
            else:
                score_components.append(0.3)
        
        # Get borrow stress if available
        if providers and 'borrow_proxy' in providers:
            try:
                borrow_data = providers['borrow_proxy'].calculate_borrow_stress(
                    svr=svr,
                    dtcr=metrics.get('dtcr', 0),
                    short_interest_pct=si_pct,
                    ftd_flag=enriched_data.get('ftd_flag', False),
                    threshold_security=enriched_data.get('threshold_security', False)
                )
                
                borrow_score = borrow_data.get('borrow_stress_score', 0)
                metrics['borrow_stress'] = borrow_score
                
                if borrow_score >= 80:
                    signals.append('extreme_borrow_stress')
                    score_components.append(0.8)
                elif borrow_score >= self.thresholds['borrow_stress_min']:
                    signals.append('high_borrow_stress')
                    score_components.append(0.6)
                else:
                    score_components.append(0.2)
                    
            except Exception as e:
                logger.warning("Borrow stress calculation failed", symbol=symbol, error=str(e))
        
        # Return average of available components
        return sum(score_components) / len(score_components) if score_components else 0.0
    
    async def _analyze_options_gamma(self, symbol: str, enriched_data: Dict, signals: List, metrics: Dict, providers: Optional[Dict]) -> float:
        """Analyze options flow for gamma squeeze potential"""
        score_components = []
        
        # Get current stock price
        stock_price = enriched_data.get('price', enriched_data.get('close', 0))
        
        # Get options data if available
        if providers and 'alpha_vantage_options' in providers and stock_price > 0:
            try:
                options_data = await providers['alpha_vantage_options'].get_atm_options_data(symbol, stock_price)
                
                if options_data.get('staleness_policy_pass', False):
                    iv_percentile = options_data.get('iv_percentile', 50)
                    atm_iv = options_data.get('atm_iv', 0)
                    confidence = options_data.get('confidence', 0)
                    
                    metrics['iv_percentile'] = iv_percentile
                    metrics['atm_iv'] = atm_iv
                    metrics['options_confidence'] = confidence
                    
                    # Score based on IV percentile (low IV = potential expansion)
                    if iv_percentile <= 20:
                        signals.append('low_iv_expansion_potential')
                        score_components.append(0.8)
                    elif iv_percentile <= 40:
                        signals.append('moderate_iv_potential')  
                        score_components.append(0.5)
                    else:
                        score_components.append(0.2)
                    
                    # High absolute IV can indicate pending volatility
                    if atm_iv >= 0.6:  # 60% IV
                        signals.append('high_iv_volatility')
                        score_components.append(0.6)
                    
            except Exception as e:
                logger.warning("Options data fetch failed", symbol=symbol, error=str(e))
        
        # Use basic call/put ratio if available
        call_put_ratio = enriched_data.get('call_put_ratio', 0)
        if call_put_ratio > 0:
            metrics['call_put_ratio'] = call_put_ratio
            
            if call_put_ratio >= 3.0:  # Heavy call bias
                signals.append('heavy_call_bias')
                score_components.append(0.7)
            elif call_put_ratio >= 1.5:
                signals.append('moderate_call_bias')
                score_components.append(0.4)
            else:
                score_components.append(0.2)
        
        return sum(score_components) / len(score_components) if score_components else 0.3
    
    def _analyze_volume_pressure(self, enriched_data: Dict, signals: List, metrics: Dict) -> float:
        """Analyze volume-based squeeze pressure"""
        volume_spike = enriched_data.get('volume_spike', 0)
        relvol_30 = enriched_data.get('relvol_30', 0)
        
        metrics['volume_spike'] = volume_spike
        metrics['relvol_30'] = relvol_30
        
        score = 0
        
        # Volume spike scoring
        if volume_spike >= 5.0:
            signals.append('extreme_volume_spike')
            score += 0.6
        elif volume_spike >= 2.0:
            signals.append('high_volume_spike')
            score += 0.4
        elif volume_spike >= 1.5:
            signals.append('moderate_volume_spike')
            score += 0.2
        
        # Sustained volume (RelVol 30) bonus
        if relvol_30 >= 2.0:
            signals.append('sustained_volume')
            score += 0.4
        
        return min(1.0, score)
    
    def _classify_squeeze_type(self, metrics: Dict, signals: List) -> str:
        """Classify the type of squeeze opportunity"""
        float_shares = metrics.get('float_shares', 0)
        si_pct = metrics.get('short_interest_pct', 0)
        borrow_stress = metrics.get('borrow_stress', 0)
        
        # Gamma squeeze indicators
        has_options_signals = any('iv_' in signal or 'call_' in signal for signal in signals)
        
        # Short squeeze indicators
        has_short_signals = any('si_' in signal or 'dtcr_' in signal or 'borrow_' in signal for signal in signals)
        
        if has_options_signals and has_short_signals:
            return 'HYBRID_SQUEEZE'  # Both gamma and short squeeze potential
        elif has_options_signals:
            return 'GAMMA_SQUEEZE'   # Primarily options-driven
        elif has_short_signals:
            return 'SHORT_SQUEEZE'   # Primarily short-driven
        elif float_shares > 0 and float_shares <= 25_000_000:
            return 'FLOAT_SQUEEZE'   # Low float momentum play
        else:
            return 'VOLUME_SQUEEZE'  # Volume-driven momentum
    
    def _assess_catalyst_strength(self, score: float, signals: List) -> str:
        """Assess the strength of squeeze catalysts"""
        extreme_signals = [s for s in signals if 'extreme_' in s]
        high_signals = [s for s in signals if 'high_' in s and 'extreme_' not in s]
        
        if len(extreme_signals) >= 2:
            return 'EXPLOSIVE'
        elif len(extreme_signals) >= 1 or score >= 0.7:
            return 'STRONG'
        elif len(high_signals) >= 2 or score >= 0.5:
            return 'MODERATE'
        elif score >= 0.3:
            return 'DEVELOPING'
        else:
            return 'WEAK'
    
    def _calculate_confidence(self, enriched_data: Dict, metrics: Dict, providers: Optional[Dict]) -> float:
        """Calculate confidence based on data availability and quality"""
        confidence_factors = []
        
        # Float data quality
        if enriched_data.get('float_shares', 0) > 0:
            confidence_factors.append(0.25)
        
        # Short interest data quality
        if metrics.get('short_interest_pct', 0) > 0:
            if metrics.get('si_source') == 'finra':
                confidence_factors.append(0.3)  # High confidence in FINRA data
            else:
                confidence_factors.append(0.2)  # Lower confidence in other sources
        
        # Volume data quality
        if enriched_data.get('volume', 0) > 0:
            confidence_factors.append(0.2)
        
        # Options data quality (if available)
        options_confidence = metrics.get('options_confidence', 0)
        if options_confidence > 0:
            confidence_factors.append(0.25 * options_confidence)
        
        # Provider availability bonus
        if providers:
            available_providers = len([p for p in providers.values() if p])
            provider_bonus = min(0.1, available_providers * 0.03)
            confidence_factors.append(provider_bonus)
        
        return min(1.0, sum(confidence_factors))
    
    def _empty_result(self) -> Dict:
        """Return empty result for errors"""
        return {
            'score': 0.0,
            'confidence': 0.0,
            'signals': [],
            'metrics': {},
            'squeeze_type': 'UNKNOWN',
            'catalyst_strength': 'ERROR',
            'detector': 'squeeze',
            'components': {
                'float_score': 0.0,
                'short_score': 0.0,
                'gamma_score': 0.0,
                'volume_score': 0.0
            }
        }