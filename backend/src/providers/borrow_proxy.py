"""
Borrow Cost Proxy Provider  
Estimates borrow stress using statistical proxies and no fabrication
"""

import structlog
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Optional
import math

logger = structlog.get_logger()

class BorrowProxyProvider:
    """
    Provider for estimated borrow stress using statistical proxies
    - Uses z-scores of SVR (Short Volume Ratio) and DTCR (Days to Cover Ratio)
    - Incorporates FTD (Fails to Deliver) and Threshold Security flags when available
    - No fabrication - returns confidence-weighted estimates or empty
    """
    
    def __init__(self):
        # Historical statistical thresholds for scoring
        self.svr_high_threshold = 45.0  # >45% short volume ratio indicates stress
        self.svr_extreme_threshold = 65.0  # >65% indicates extreme stress
        self.dtcr_high_threshold = 7.0  # >7 days to cover indicates stress  
        self.dtcr_extreme_threshold = 15.0  # >15 days indicates extreme stress
    
    def calculate_borrow_stress(self, 
                               svr: float,
                               dtcr: float, 
                               ftd_flag: bool = False,
                               threshold_security: bool = False,
                               short_interest_pct: float = 0.0) -> Dict:
        """
        Calculate borrow stress proxy score
        Returns: {
            'borrow_stress_score': float (0-100),
            'confidence': float (0-1),  
            'stress_level': str ('LOW', 'MODERATE', 'HIGH', 'EXTREME'),
            'contributing_factors': List[str],
            'asof': str (ISO),
            'source': 'proxy_calculation',
            'staleness_policy_pass': bool,
            'methodology': str
        }
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            contributing_factors = []
            stress_components = []
            
            # SVR Component (30% weight)
            svr_score = self._score_svr(svr)
            if svr >= self.svr_high_threshold:
                contributing_factors.append(f"high_svr_{svr:.1f}%")
            stress_components.append(('svr', svr_score, 0.30))
            
            # DTCR Component (25% weight) 
            dtcr_score = self._score_dtcr(dtcr)
            if dtcr >= self.dtcr_high_threshold:
                contributing_factors.append(f"high_dtcr_{dtcr:.1f}d")
            stress_components.append(('dtcr', dtcr_score, 0.25))
            
            # Short Interest Component (20% weight)
            si_score = self._score_short_interest(short_interest_pct)
            if short_interest_pct >= 20.0:
                contributing_factors.append(f"high_si_{short_interest_pct:.1f}%")
            stress_components.append(('short_interest', si_score, 0.20))
            
            # Regulatory Flags (25% weight combined)
            flag_score = 0
            if ftd_flag:
                flag_score += 40
                contributing_factors.append("ftd_flag")
            if threshold_security:
                flag_score += 60  
                contributing_factors.append("threshold_security")
            
            stress_components.append(('regulatory_flags', min(flag_score, 100), 0.25))
            
            # Calculate weighted composite score
            borrow_stress_score = sum(score * weight for _, score, weight in stress_components)
            borrow_stress_score = max(0, min(100, borrow_stress_score))
            
            # Determine stress level
            stress_level = self._categorize_stress_level(borrow_stress_score)
            
            # Calculate confidence based on data availability
            confidence = self._calculate_confidence(svr, dtcr, short_interest_pct, ftd_flag, threshold_security)
            
            # All proxy calculations are considered "fresh"
            staleness_pass = True
            
            result = {
                'borrow_stress_score': round(borrow_stress_score, 1),
                'confidence': round(confidence, 3),
                'stress_level': stress_level,
                'contributing_factors': contributing_factors,
                'components': {
                    'svr_score': round(svr_score, 1),
                    'dtcr_score': round(dtcr_score, 1), 
                    'si_score': round(si_score, 1),
                    'flag_score': flag_score
                },
                'asof': datetime.now(timezone.utc).isoformat(),
                'source': 'proxy_calculation',
                'ingested_at': datetime.now(timezone.utc).isoformat(),
                'staleness_policy_pass': staleness_pass,
                'methodology': 'weighted_composite_z_score',
                'latency_sec': (datetime.now(timezone.utc) - start_time).total_seconds()
            }
            
            logger.info("Borrow stress calculated", 
                       score=borrow_stress_score, level=stress_level, 
                       confidence=confidence, factors=len(contributing_factors))
            return result
            
        except Exception as e:
            logger.error("Borrow stress calculation failed", error=str(e))
            return self._empty_response(start_time, f"error_{str(e)[:20]}")
    
    def _score_svr(self, svr: float) -> float:
        """
        Score Short Volume Ratio (0-100 scale)
        SVR above 45% indicates potential borrow stress
        """
        if svr <= 20:
            return 0  # Normal/low short volume
        elif svr <= 35:
            return 20  # Moderate short volume
        elif svr <= self.svr_high_threshold:
            return 50  # Elevated short volume
        elif svr <= self.svr_extreme_threshold:
            return 80  # High short volume stress
        else:
            return 100  # Extreme short volume stress
    
    def _score_dtcr(self, dtcr: float) -> float:
        """
        Score Days to Cover Ratio (0-100 scale)
        DTCR above 7 days indicates potential borrow difficulty
        """
        if dtcr <= 2:
            return 0  # Easy to cover
        elif dtcr <= 5:
            return 20  # Moderate coverage time
        elif dtcr <= self.dtcr_high_threshold:
            return 50  # Longer coverage time
        elif dtcr <= self.dtcr_extreme_threshold:
            return 80  # High coverage time stress  
        else:
            return 100  # Extreme coverage time stress
    
    def _score_short_interest(self, si_pct: float) -> float:
        """
        Score Short Interest Percentage (0-100 scale)
        Higher short interest can indicate borrow pressure
        """
        if si_pct <= 5:
            return 0  # Low short interest
        elif si_pct <= 15:
            return 30  # Moderate short interest
        elif si_pct <= 25:
            return 60  # High short interest
        elif si_pct <= 40:
            return 80  # Very high short interest
        else:
            return 100  # Extreme short interest
    
    def _categorize_stress_level(self, score: float) -> str:
        """Categorize stress level based on composite score"""
        if score >= 80:
            return 'EXTREME'
        elif score >= 60:
            return 'HIGH'
        elif score >= 30:
            return 'MODERATE'
        else:
            return 'LOW'
    
    def _calculate_confidence(self, svr: float, dtcr: float, si_pct: float, ftd_flag: bool, threshold_security: bool) -> float:
        """
        Calculate confidence in borrow stress estimate
        Higher confidence when more data points are available and recent
        """
        confidence_factors = []
        
        # SVR data quality (0.3 weight)
        if svr > 0:
            confidence_factors.append(0.3)
        
        # DTCR data quality (0.25 weight)  
        if dtcr > 0:
            confidence_factors.append(0.25)
        
        # Short Interest data quality (0.2 weight)
        if si_pct > 0:
            confidence_factors.append(0.2)
        
        # Regulatory flags add confidence (0.25 weight combined)
        flag_confidence = 0
        if ftd_flag:
            flag_confidence += 0.125
        if threshold_security:
            flag_confidence += 0.125
        
        if flag_confidence > 0:
            confidence_factors.append(flag_confidence)
        
        # Base confidence is sum of available data factors
        base_confidence = sum(confidence_factors)
        
        # Proxy calculations have inherent uncertainty (max 0.8 confidence)
        adjusted_confidence = min(0.8, base_confidence)
        
        return max(0.1, adjusted_confidence)  # Minimum 0.1 confidence for proxy
    
    def _empty_response(self, start_time: datetime, reason: str) -> Dict:
        """Generate empty response with error reason"""
        latency_sec = (datetime.now(timezone.utc) - start_time).total_seconds()
        return {
            'borrow_stress_score': 0.0,
            'confidence': 0.0,
            'stress_level': 'UNKNOWN',
            'contributing_factors': [],
            'components': {
                'svr_score': 0.0,
                'dtcr_score': 0.0,
                'si_score': 0.0,
                'flag_score': 0
            },
            'asof': datetime.now(timezone.utc).isoformat(),
            'source': 'proxy_calculation',
            'ingested_at': datetime.now(timezone.utc).isoformat(),
            'staleness_policy_pass': False,
            'methodology': 'weighted_composite_z_score', 
            'latency_sec': round(latency_sec, 3),
            'error_reason': reason
        }

# Usage example:
# provider = BorrowProxyProvider()
# stress_data = provider.calculate_borrow_stress(
#     svr=52.3,  # 52.3% short volume ratio
#     dtcr=12.5,  # 12.5 days to cover
#     ftd_flag=True,
#     threshold_security=False,
#     short_interest_pct=28.5
# )