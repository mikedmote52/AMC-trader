"""
Volume Momentum Detector with Live Data Priority
RelVol, VWAP reclaim, ATR% using live WebSocket feeds
"""
import logging
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from backend.src.discovery.feature_store import FeatureSet, get_feature_store

logger = logging.getLogger(__name__)

@dataclass
class VolumeMomentumSignal:
    symbol: str
    rel_vol: float
    vwap_reclaim: bool
    atr_pct: float
    volume_spike: bool
    sustained_momentum: bool
    score: float
    confidence: float
    reasons: List[str]
    provenance: Dict[str, Dict]

class VolumeMomentumDetector:
    """
    Live volume momentum detection with strict freshness requirements
    Uses WebSocket feeds for real-time RelVol and VWAP analysis
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.thresholds = {
            'min_rel_vol': 3.0,           # 3x sustained volume
            'min_atr_pct': 0.04,          # 4% ATR minimum
            'vwap_reclaim_required': True, # Must be above VWAP
            'volume_spike_threshold': 2.0, # 2x for initial spike
            'momentum_window_bars': 3      # Sustained over 3 bars
        }
        
        # Update thresholds from config
        detector_config = config.get('detectors', {}).get('volume_momentum', {})
        self.thresholds.update(detector_config)
        
        self.stats = {
            'signals_generated': 0,
            'vwap_reclaim_passes': 0,
            'rel_vol_passes': 0,
            'atr_passes': 0,
            'confidence_failures': 0
        }
    
    async def detect(self, feature_sets: Dict[str, FeatureSet]) -> Dict[str, VolumeMomentumSignal]:
        """Detect volume momentum signals from live feature data"""
        signals = {}
        
        for symbol, fs in feature_sets.items():
            try:
                signal = await self._analyze_momentum(fs)
                if signal and signal.score > 0:
                    signals[symbol] = signal
                    self.stats['signals_generated'] += 1
                    
            except Exception as e:
                logger.error(f"❌ Volume momentum error for {symbol}: {e}")
        
        return signals
    
    async def _analyze_momentum(self, fs: FeatureSet) -> Optional[VolumeMomentumSignal]:
        """Analyze volume momentum for a single symbol"""
        reasons = []
        score_components = []
        confidence = 1.0
        
        # Check data availability and freshness
        if not fs.is_fresh:
            return None
        
        # 1. RelVol Analysis (critical component)
        rel_vol_score, rel_vol_conf = self._analyze_rel_vol(fs, reasons)
        if rel_vol_score is None:
            return None  # Can't analyze without volume data
        
        score_components.append(('rel_vol', rel_vol_score, 0.4))  # 40% weight
        confidence *= rel_vol_conf
        
        # 2. VWAP Reclaim Analysis
        vwap_score, vwap_conf, vwap_reclaim = self._analyze_vwap_reclaim(fs, reasons)
        if vwap_score is not None:
            score_components.append(('vwap', vwap_score, 0.3))  # 30% weight
            confidence *= vwap_conf
        else:
            vwap_reclaim = False  # Default if no VWAP data
        
        # 3. ATR% Analysis (volatility expansion)
        atr_score, atr_conf = self._analyze_atr(fs, reasons)
        if atr_score is not None:
            score_components.append(('atr', atr_score, 0.2))  # 20% weight
            confidence *= atr_conf
        
        # 4. Volume Spike Detection
        volume_spike = self._detect_volume_spike(fs, reasons)
        
        # 5. Sustained Momentum Check
        sustained = self._check_sustained_momentum(fs, reasons)
        
        # Calculate composite score
        if not score_components:
            return None
        
        weighted_score = sum(score * weight for _, score, weight in score_components)
        total_weight = sum(weight for _, _, weight in score_components)
        final_score = weighted_score / total_weight if total_weight > 0 else 0
        
        # Apply gates
        final_score = self._apply_gates(final_score, fs, reasons)
        
        # Confidence penalty for missing data
        if len(score_components) < 3:
            confidence *= 0.8
        
        return VolumeMomentumSignal(
            symbol=fs.symbol,
            rel_vol=fs.rel_vol or 0,
            vwap_reclaim=vwap_reclaim,
            atr_pct=fs.atr_pct or 0,
            volume_spike=volume_spike,
            sustained_momentum=sustained,
            score=final_score,
            confidence=confidence,
            reasons=reasons,
            provenance=fs.provenance
        )
    
    def _analyze_rel_vol(self, fs: FeatureSet, reasons: List[str]) -> Tuple[Optional[float], float]:
        """Analyze relative volume with live data priority"""
        if fs.rel_vol is None:
            reasons.append("rel_vol_missing")
            return None, 0.0
        
        # Get confidence from provenance
        vol_prov = fs.provenance.get('volume', {})
        base_confidence = vol_prov.get('confidence', 0.5)
        
        # Live WebSocket data gets higher confidence
        if vol_prov.get('source') == 'polygon_ws':
            base_confidence = min(base_confidence * 1.2, 1.0)
        
        # Score based on RelVol magnitude
        if fs.rel_vol >= self.thresholds['min_rel_vol']:
            # Strong relative volume
            score = min(fs.rel_vol / 5.0, 1.0)  # Cap at 5x = 1.0 score
            reasons.append(f"rel_vol_strong_{fs.rel_vol:.1f}x")
            self.stats['rel_vol_passes'] += 1
            return score, base_confidence
        
        elif fs.rel_vol >= 2.0:
            # Moderate relative volume
            score = fs.rel_vol / 5.0
            reasons.append(f"rel_vol_moderate_{fs.rel_vol:.1f}x")
            return score, base_confidence * 0.8
        
        else:
            # Below minimum
            reasons.append(f"rel_vol_low_{fs.rel_vol:.1f}x")
            return 0.0, base_confidence
    
    def _analyze_vwap_reclaim(self, fs: FeatureSet, reasons: List[str]) -> Tuple[Optional[float], float, bool]:
        """Analyze VWAP reclaim with live price priority"""
        if fs.price is None or fs.vwap is None:
            reasons.append("vwap_data_missing")
            return None, 0.0, False
        
        # Get confidence from provenance
        price_prov = fs.provenance.get('price', {})
        vwap_prov = fs.provenance.get('vwap', {})
        confidence = min(price_prov.get('confidence', 0.5), vwap_prov.get('confidence', 0.5))
        
        # Live data confidence boost
        if price_prov.get('source') == 'polygon_ws' and vwap_prov.get('source') == 'polygon_ws':
            confidence = min(confidence * 1.3, 1.0)
        
        # Calculate VWAP reclaim
        vwap_diff_pct = (fs.price - fs.vwap) / fs.vwap
        reclaimed = vwap_diff_pct > 0
        
        if reclaimed:
            # Score based on how far above VWAP
            score = min(abs(vwap_diff_pct) * 10, 1.0)  # 10% above VWAP = 1.0 score
            reasons.append(f"vwap_reclaim_+{vwap_diff_pct:.1%}")
            self.stats['vwap_reclaim_passes'] += 1
            
            return score, confidence, True
        else:
            reasons.append(f"vwap_below_{vwap_diff_pct:.1%}")
            return 0.0, confidence, False
    
    def _analyze_atr(self, fs: FeatureSet, reasons: List[str]) -> Tuple[Optional[float], float]:
        """Analyze ATR% for volatility expansion"""
        if fs.atr_pct is None:
            reasons.append("atr_missing")
            return None, 0.0
        
        # Get confidence from provenance (usually calculated/estimated)
        atr_prov = fs.provenance.get('atr_pct', {})
        confidence = atr_prov.get('confidence', 0.6)  # Lower confidence for ATR
        
        if fs.atr_pct >= self.thresholds['min_atr_pct']:
            # Sufficient volatility expansion
            score = min(fs.atr_pct / 0.08, 1.0)  # 8% ATR = 1.0 score
            reasons.append(f"atr_expansion_{fs.atr_pct:.1%}")
            self.stats['atr_passes'] += 1
            return score, confidence
        else:
            reasons.append(f"atr_low_{fs.atr_pct:.1%}")
            return 0.0, confidence
    
    def _detect_volume_spike(self, fs: FeatureSet, reasons: List[str]) -> bool:
        """Detect initial volume spike (less strict than sustained RelVol)"""
        if fs.rel_vol is None:
            return False
        
        spike_threshold = self.thresholds.get('volume_spike_threshold', 2.0)
        
        if fs.rel_vol >= spike_threshold:
            reasons.append(f"volume_spike_{fs.rel_vol:.1f}x")
            return True
        
        return False
    
    def _check_sustained_momentum(self, fs: FeatureSet, reasons: List[str]) -> bool:
        """Check for sustained momentum (simplified - would need time series)"""
        # This is a placeholder - real implementation would check multiple bars
        # For now, use strong RelVol as proxy for sustained momentum
        
        if fs.rel_vol and fs.rel_vol >= self.thresholds['min_rel_vol']:
            reasons.append("momentum_sustained")
            return True
        
        return False
    
    def _apply_gates(self, base_score: float, fs: FeatureSet, reasons: List[str]) -> float:
        """Apply hard gates that can zero out the score"""
        
        # Gate 1: Minimum RelVol gate
        if fs.rel_vol and fs.rel_vol < self.thresholds['min_rel_vol']:
            reasons.append(f"gate_rel_vol_fail_{fs.rel_vol:.1f}x_below_{self.thresholds['min_rel_vol']:.1f}x")
            return 0.0
        
        # Gate 2: VWAP reclaim gate (if required)
        if self.thresholds.get('vwap_reclaim_required', False):
            if fs.price and fs.vwap and fs.price <= fs.vwap:
                reasons.append("gate_vwap_reclaim_fail")
                return 0.0
        
        # Gate 3: Minimum ATR gate
        if fs.atr_pct and fs.atr_pct < self.thresholds['min_atr_pct']:
            reasons.append(f"gate_atr_fail_{fs.atr_pct:.1%}_below_{self.thresholds['min_atr_pct']:.1%}")
            return 0.0
        
        # All gates passed
        return base_score
    
    def get_stats(self) -> Dict:
        """Get detector statistics"""
        return self.stats

def create_volume_momentum_detector(config: Dict = None) -> VolumeMomentumDetector:
    """Create volume momentum detector with config"""
    if config is None:
        config = {}
    
    return VolumeMomentumDetector(config)