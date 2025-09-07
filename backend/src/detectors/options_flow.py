"""
Options Flow Detector with Live Polygon Data
ATM IV, IV Percentile, Call/Put Ratio analysis with live options feeds
"""
import logging
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from backend.src.discovery.feature_store import FeatureSet

logger = logging.getLogger(__name__)

@dataclass
class OptionsFlowSignal:
    symbol: str
    atm_iv: float
    iv_percentile: float
    call_put_ratio: float
    iv_rank: str  # HIGH/MEDIUM/LOW
    flow_bias: str  # BULLISH/BEARISH/NEUTRAL
    gamma_risk: str  # HIGH/MEDIUM/LOW
    score: float
    confidence: float
    reasons: List[str]
    provenance: Dict[str, Dict]

class OptionsFlowDetector:
    """
    Live options flow analysis with Polygon data
    Higher weight now that options data is live and reliable
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.thresholds = {
            'min_iv_percentile': 80,      # 80th percentile minimum for high IV
            'min_call_put_ratio': 2.0,    # 2:1 call/put for bullish flow
            'max_call_put_ratio': 0.5,    # 1:2 put/call for bearish flow  
            'min_atm_iv': 0.30,           # 30% minimum ATM IV
            'high_iv_percentile': 90,     # 90th+ percentile = HIGH
            'low_iv_percentile': 20,      # <20th percentile = LOW
            'volume_significance': 1000   # Minimum options volume for signal
        }
        
        # Update from config
        detector_config = config.get('detectors', {}).get('options_flow', {})
        self.thresholds.update(detector_config)
        
        # Weights adjusted for live data
        weights_override = config.get('weights_override', {})
        self.weight = weights_override.get('options_flow', 0.12)  # Increased from default
        
        self.stats = {
            'signals_generated': 0,
            'high_iv_signals': 0,
            'bullish_flow_signals': 0,
            'bearish_flow_signals': 0,
            'confidence_boosts': 0
        }
    
    async def detect(self, feature_sets: Dict[str, FeatureSet]) -> Dict[str, OptionsFlowSignal]:
        """Detect options flow signals from live Polygon data"""
        signals = {}
        
        for symbol, fs in feature_sets.items():
            try:
                signal = await self._analyze_options_flow(fs)
                if signal and signal.score > 0:
                    signals[symbol] = signal
                    self.stats['signals_generated'] += 1
                    
            except Exception as e:
                logger.error(f"❌ Options flow error for {symbol}: {e}")
        
        return signals
    
    async def _analyze_options_flow(self, fs: FeatureSet) -> Optional[OptionsFlowSignal]:
        """Analyze options flow for a single symbol"""
        reasons = []
        score_components = []
        
        # Must have options data to analyze
        if not self._has_options_data(fs):
            return None
        
        # Get options provenance for confidence
        options_prov = fs.provenance.get('options', {})
        base_confidence = options_prov.get('confidence', 0.5)
        
        # Live Polygon data gets confidence boost
        if options_prov.get('source') == 'polygon_options':
            base_confidence = min(base_confidence * 1.4, 1.0)  # 40% boost for live data
            self.stats['confidence_boosts'] += 1
        
        # 1. IV Percentile Analysis (primary signal)
        iv_score, iv_rank = self._analyze_iv_percentile(fs, reasons)
        if iv_score > 0:
            score_components.append(('iv_percentile', iv_score, 0.4))  # 40% weight
        
        # 2. ATM IV Analysis (absolute level)
        atm_iv_score = self._analyze_atm_iv(fs, reasons)
        if atm_iv_score > 0:
            score_components.append(('atm_iv', atm_iv_score, 0.3))  # 30% weight
        
        # 3. Call/Put Flow Analysis
        flow_score, flow_bias = self._analyze_call_put_flow(fs, reasons)
        if flow_score > 0:
            score_components.append(('flow', flow_score, 0.3))  # 30% weight
        
        # 4. Gamma Risk Assessment
        gamma_risk = self._assess_gamma_risk(fs, reasons)
        
        # Calculate composite score
        if not score_components:
            return None
        
        weighted_score = sum(score * weight for _, score, weight in score_components)
        total_weight = sum(weight for _, _, weight in score_components)
        final_score = weighted_score / total_weight if total_weight > 0 else 0
        
        # Apply significance gates
        final_score = self._apply_significance_gates(final_score, fs, reasons)
        
        return OptionsFlowSignal(
            symbol=fs.symbol,
            atm_iv=fs.atm_iv or 0,
            iv_percentile=fs.iv_percentile or 0,
            call_put_ratio=fs.call_put_ratio or 0,
            iv_rank=iv_rank,
            flow_bias=flow_bias,
            gamma_risk=gamma_risk,
            score=final_score,
            confidence=base_confidence,
            reasons=reasons,
            provenance=fs.provenance
        )
    
    def _has_options_data(self, fs: FeatureSet) -> bool:
        """Check if symbol has sufficient options data"""
        return (fs.atm_iv is not None and fs.atm_iv > 0) or \
               (fs.iv_percentile is not None and fs.iv_percentile > 0) or \
               (fs.call_put_ratio is not None and fs.call_put_ratio > 0)
    
    def _analyze_iv_percentile(self, fs: FeatureSet, reasons: List[str]) -> Tuple[float, str]:
        """Analyze IV percentile for high volatility opportunities"""
        if fs.iv_percentile is None:
            return 0.0, "UNKNOWN"
        
        iv_pct = fs.iv_percentile
        
        if iv_pct >= self.thresholds['high_iv_percentile']:
            # Very high IV - prime for volatility plays
            score = min(iv_pct / 100, 1.0)
            rank = "HIGH"
            reasons.append(f"iv_percentile_high_{iv_pct:.0f}th")
            self.stats['high_iv_signals'] += 1
            
        elif iv_pct >= self.thresholds['min_iv_percentile']:
            # Elevated IV - moderate opportunity
            score = iv_pct / 100 * 0.8  # Scale down for moderate
            rank = "MEDIUM"
            reasons.append(f"iv_percentile_elevated_{iv_pct:.0f}th")
            
        elif iv_pct <= self.thresholds['low_iv_percentile']:
            # Very low IV - potential mean reversion
            score = (100 - iv_pct) / 100 * 0.6  # Inverse scoring for low IV
            rank = "LOW"
            reasons.append(f"iv_percentile_low_{iv_pct:.0f}th_reversion")
            
        else:
            # Middle range - not significant
            score = 0.0
            rank = "MEDIUM"
            reasons.append(f"iv_percentile_neutral_{iv_pct:.0f}th")
        
        return score, rank
    
    def _analyze_atm_iv(self, fs: FeatureSet, reasons: List[str]) -> float:
        """Analyze absolute ATM IV level"""
        if fs.atm_iv is None:
            return 0.0
        
        atm_iv = fs.atm_iv
        
        if atm_iv >= self.thresholds['min_atm_iv']:
            # High absolute IV
            score = min(atm_iv / 1.0, 1.0)  # 100% IV = 1.0 score
            reasons.append(f"atm_iv_high_{atm_iv:.1%}")
            return score
            
        elif atm_iv >= 0.15:  # 15% minimum
            # Moderate IV
            score = atm_iv / 0.30 * 0.6  # Scale to 60% max for moderate
            reasons.append(f"atm_iv_moderate_{atm_iv:.1%}")
            return score
            
        else:
            reasons.append(f"atm_iv_low_{atm_iv:.1%}")
            return 0.0
    
    def _analyze_call_put_flow(self, fs: FeatureSet, reasons: List[str]) -> Tuple[float, str]:
        """Analyze call/put ratio for directional bias"""
        if fs.call_put_ratio is None:
            return 0.0, "NEUTRAL"
        
        cp_ratio = fs.call_put_ratio
        
        if cp_ratio >= self.thresholds['min_call_put_ratio']:
            # Bullish flow (heavy call buying)
            score = min(cp_ratio / 5.0, 1.0)  # 5:1 ratio = 1.0 score
            bias = "BULLISH"
            reasons.append(f"call_heavy_{cp_ratio:.1f}_to_1")
            self.stats['bullish_flow_signals'] += 1
            
        elif cp_ratio <= self.thresholds['max_call_put_ratio']:
            # Bearish flow (heavy put buying)
            score = min((1/cp_ratio) / 5.0, 1.0) if cp_ratio > 0 else 1.0
            bias = "BEARISH"
            reasons.append(f"put_heavy_1_to_{1/cp_ratio:.1f}" if cp_ratio > 0 else "put_heavy_extreme")
            self.stats['bearish_flow_signals'] += 1
            
        else:
            # Neutral flow
            score = 0.0
            bias = "NEUTRAL"
            reasons.append(f"flow_neutral_{cp_ratio:.1f}_to_1")
        
        return score, bias
    
    def _assess_gamma_risk(self, fs: FeatureSet, reasons: List[str]) -> str:
        """Assess gamma risk level (simplified)"""
        
        # This would ideally use gamma exposure data from options chain
        # For now, use IV and flow as proxies
        
        high_iv = fs.iv_percentile and fs.iv_percentile >= 80
        high_flow = fs.call_put_ratio and (fs.call_put_ratio >= 3.0 or fs.call_put_ratio <= 0.33)
        
        if high_iv and high_flow:
            reasons.append("gamma_risk_high")
            return "HIGH"
        elif high_iv or high_flow:
            reasons.append("gamma_risk_medium")
            return "MEDIUM"
        else:
            reasons.append("gamma_risk_low")
            return "LOW"
    
    def _apply_significance_gates(self, base_score: float, fs: FeatureSet, reasons: List[str]) -> float:
        """Apply gates for options significance"""
        
        # Gate 1: Minimum IV requirement
        if fs.atm_iv and fs.atm_iv < 0.10:  # Less than 10% IV
            reasons.append(f"gate_min_iv_fail_{fs.atm_iv:.1%}")
            return 0.0
        
        # Gate 2: Very low IV percentile (unless mean reversion play)
        if fs.iv_percentile and fs.iv_percentile < 5:  # Bottom 5%
            if fs.call_put_ratio and fs.call_put_ratio < 2.0:  # Not bullish flow
                reasons.append(f"gate_iv_percentile_too_low_{fs.iv_percentile:.0f}th")
                return 0.0
        
        return base_score
    
    def get_stats(self) -> Dict:
        """Get detector statistics"""
        return self.stats

def create_options_flow_detector(config: Dict = None) -> OptionsFlowDetector:
    """Create options flow detector with config"""
    if config is None:
        config = {}
    
    return OptionsFlowDetector(config)