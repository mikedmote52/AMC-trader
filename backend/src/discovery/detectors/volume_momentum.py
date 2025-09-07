"""
Volume & Momentum Detector
Analyzes volume spikes, momentum indicators, and VWAP reclaim patterns
"""

import structlog
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import numpy as np

logger = structlog.get_logger()

class VolumeMomentumDetector:
    """
    Detects volume and momentum patterns for squeeze opportunities
    - RelVol (relative volume) analysis
    - VWAP reclaim detection  
    - Uptrend day counting
    - ATR expansion analysis
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.weights = {
            'relvol': 0.4,      # Relative volume importance
            'vwap_reclaim': 0.3, # VWAP reclaim importance
            'uptrend_days': 0.2, # Recent uptrend importance
            'atr_expansion': 0.1 # ATR expansion importance  
        }
    
    def analyze(self, symbol: str, enriched_data: Dict) -> Dict:
        """
        Analyze volume and momentum patterns
        Returns: {
            'score': float (0-1),
            'confidence': float (0-1),
            'signals': List[str],
            'metrics': Dict,
            'pattern_strength': str
        }
        """
        try:
            signals = []
            metrics = {}
            
            # Extract data with safe defaults
            relvol_30 = enriched_data.get('relvol_30', 0)
            relvol_5 = enriched_data.get('relvol_5', 0) 
            vwap = enriched_data.get('vwap', 0)
            current_price = enriched_data.get('price', enriched_data.get('close', 0))
            atr_pct = enriched_data.get('atr_pct', 0)
            volume_spike = enriched_data.get('volume_spike', 0)
            
            # 1. Relative Volume Analysis
            relvol_score = self._analyze_relvol(relvol_30, relvol_5, signals, metrics)
            
            # 2. VWAP Reclaim Analysis
            vwap_score = self._analyze_vwap_reclaim(current_price, vwap, signals, metrics)
            
            # 3. Uptrend Analysis (from price history if available)
            uptrend_score = self._analyze_uptrend(enriched_data, signals, metrics)
            
            # 4. ATR Expansion Analysis
            atr_score = self._analyze_atr_expansion(atr_pct, signals, metrics)
            
            # Calculate composite score
            composite_score = (
                relvol_score * self.weights['relvol'] +
                vwap_score * self.weights['vwap_reclaim'] +
                uptrend_score * self.weights['uptrend_days'] +
                atr_score * self.weights['atr_expansion']
            )
            
            # Determine pattern strength
            pattern_strength = self._categorize_strength(composite_score)
            
            # Calculate confidence based on data quality
            confidence = self._calculate_confidence(enriched_data, metrics)
            
            result = {
                'score': round(composite_score, 4),
                'confidence': round(confidence, 3),
                'signals': signals,
                'metrics': metrics,
                'pattern_strength': pattern_strength,
                'detector': 'volume_momentum',
                'components': {
                    'relvol_score': round(relvol_score, 3),
                    'vwap_score': round(vwap_score, 3),
                    'uptrend_score': round(uptrend_score, 3),
                    'atr_score': round(atr_score, 3)
                }
            }
            
            logger.debug("Volume momentum analysis complete", 
                        symbol=symbol, score=composite_score, 
                        signals=len(signals), pattern=pattern_strength)
            
            return result
            
        except Exception as e:
            logger.error("Volume momentum analysis failed", symbol=symbol, error=str(e))
            return self._empty_result()
    
    def _analyze_relvol(self, relvol_30: float, relvol_5: float, signals: List, metrics: Dict) -> float:
        """Analyze relative volume patterns"""
        metrics['relvol_30'] = relvol_30
        metrics['relvol_5'] = relvol_5
        
        # Score based on 30-day relative volume
        if relvol_30 >= 5.0:
            signals.append('extreme_volume_5x')
            score = 1.0
        elif relvol_30 >= 3.0:
            signals.append('high_volume_3x')
            score = 0.8
        elif relvol_30 >= 2.0:
            signals.append('elevated_volume_2x')
            score = 0.6
        elif relvol_30 >= 1.5:
            signals.append('moderate_volume_1.5x')
            score = 0.4
        else:
            score = 0.2
        
        # Bonus for recent acceleration (5-day vs 30-day)
        if relvol_5 > relvol_30 * 1.2:
            signals.append('volume_acceleration')
            score = min(1.0, score + 0.1)
        
        return score
    
    def _analyze_vwap_reclaim(self, price: float, vwap: float, signals: List, metrics: Dict) -> float:
        """Analyze VWAP reclaim pattern"""
        if not vwap or not price:
            return 0.0
        
        price_vwap_ratio = price / vwap if vwap > 0 else 0
        metrics['price_vwap_ratio'] = round(price_vwap_ratio, 4)
        metrics['vwap'] = vwap
        
        if price_vwap_ratio >= 1.02:  # 2% above VWAP
            signals.append('strong_vwap_reclaim')
            return 1.0
        elif price_vwap_ratio >= 1.005:  # 0.5% above VWAP
            signals.append('vwap_reclaim')
            return 0.7
        elif price_vwap_ratio >= 0.995:  # Near VWAP
            signals.append('vwap_test')
            return 0.4
        else:
            return 0.1  # Below VWAP
    
    def _analyze_uptrend(self, enriched_data: Dict, signals: List, metrics: Dict) -> float:
        """Analyze recent uptrend strength"""
        uptrend_days = enriched_data.get('uptrend_days', 0)
        price_change_5d = enriched_data.get('price_change_5d_pct', 0)
        
        metrics['uptrend_days'] = uptrend_days
        metrics['price_change_5d_pct'] = price_change_5d
        
        score = 0
        
        # Uptrend days component
        if uptrend_days >= 3:
            signals.append(f'uptrend_{uptrend_days}d')
            score += 0.6
        elif uptrend_days >= 2:
            signals.append(f'uptrend_{uptrend_days}d')
            score += 0.4
        elif uptrend_days >= 1:
            score += 0.2
        
        # Recent price performance component
        if price_change_5d >= 10:
            signals.append('strong_5d_gain')
            score += 0.4
        elif price_change_5d >= 5:
            signals.append('moderate_5d_gain')
            score += 0.2
        elif price_change_5d >= 0:
            score += 0.1
        
        return min(1.0, score)
    
    def _analyze_atr_expansion(self, atr_pct: float, signals: List, metrics: Dict) -> float:
        """Analyze ATR expansion for volatility breakouts"""
        metrics['atr_pct'] = atr_pct
        
        if atr_pct >= 0.08:  # 8%+ ATR
            signals.append('high_volatility_expansion')
            return 1.0
        elif atr_pct >= 0.05:  # 5%+ ATR
            signals.append('moderate_volatility_expansion')
            return 0.7
        elif atr_pct >= 0.03:  # 3%+ ATR
            signals.append('some_volatility_expansion')
            return 0.4
        else:
            return 0.1
    
    def _categorize_strength(self, score: float) -> str:
        """Categorize pattern strength"""
        if score >= 0.8:
            return 'EXPLOSIVE'
        elif score >= 0.6:
            return 'STRONG'
        elif score >= 0.4:
            return 'MODERATE'
        elif score >= 0.2:
            return 'WEAK'
        else:
            return 'MINIMAL'
    
    def _calculate_confidence(self, enriched_data: Dict, metrics: Dict) -> float:
        """Calculate confidence based on data quality"""
        confidence_factors = []
        
        # Volume data quality
        if enriched_data.get('relvol_30', 0) > 0:
            confidence_factors.append(0.3)
        
        # Price/VWAP data quality
        if enriched_data.get('vwap', 0) > 0 and enriched_data.get('price', 0) > 0:
            confidence_factors.append(0.3)
        
        # Historical data quality
        if enriched_data.get('uptrend_days', 0) >= 0:  # Even 0 is valid
            confidence_factors.append(0.2)
        
        # ATR data quality
        if enriched_data.get('atr_pct', 0) > 0:
            confidence_factors.append(0.2)
        
        base_confidence = sum(confidence_factors)
        
        # Adjust for data freshness if available
        freshness_factor = 1.0
        if 'data_age_minutes' in enriched_data:
            age_minutes = enriched_data['data_age_minutes']
            if age_minutes > 10:
                freshness_factor = max(0.5, 1.0 - (age_minutes / 60))
        
        return min(1.0, base_confidence * freshness_factor)
    
    def _empty_result(self) -> Dict:
        """Return empty result for errors"""
        return {
            'score': 0.0,
            'confidence': 0.0,
            'signals': [],
            'metrics': {},
            'pattern_strength': 'ERROR',
            'detector': 'volume_momentum',
            'components': {
                'relvol_score': 0.0,
                'vwap_score': 0.0,
                'uptrend_score': 0.0,
                'atr_score': 0.0
            }
        }