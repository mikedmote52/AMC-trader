"""
Free Data Mode Configuration
Controls data provider selection and anti-fabrication policies
"""

import os
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()

class FreeDataConfig:
    """
    Configuration for Free Data Mode operations
    Enforces no-fabrication policies and provider selection
    """
    
    def __init__(self):
        self.enabled = self._get_bool_env('FREE_DATA_MODE', False)
        
        # Provider configuration
        self.providers = {
            'short_interest': os.getenv('SHORT_INTEREST_PROVIDER', 'finra'),
            'short_volume': os.getenv('SHORT_VOLUME_PROVIDER', 'finra'),  
            'options': os.getenv('OPTIONS_PROVIDER', 'alpha_vantage'),
            'borrow': os.getenv('BORROW_PROVIDER', 'proxy_only')
        }
        
        # Freshness thresholds (in hours unless specified)
        self.freshness = {
            'short_interest_days': int(os.getenv('SI_FRESHNESS_DAYS', 20)),  # 20 days for bi-monthly FINRA reports
            'short_volume_hours': int(os.getenv('SV_FRESHNESS_HOURS', 36)),  # 36 hours for daily FINRA data
            'options_hours': int(os.getenv('OPTIONS_FRESHNESS_HOURS', 24)),  # 24 hours for options data
            'market_data_minutes': int(os.getenv('MARKET_DATA_FRESHNESS_MINUTES', 5))  # 5 minutes for quotes/bars
        }
        
        # Anti-fabrication enforcement
        self.fabrication_guard = {
            'enabled': True,
            'banned_defaults': [
                25.0,  # Common SI% default
                0.25,  # Common SI fraction default
                30.0,  # Common IV default
                0.30,  # Common IV fraction default
                50.0,  # Common percentile default
                100.0,  # Common volume spike default
                1.0,   # Common ratio default
            ],
            'require_source_attribution': True,
            'require_timestamp': True
        }
        
        # Confidence weighting
        self.confidence_weights = {
            'finra_short_interest': 0.95,  # High confidence in official FINRA data
            'finra_short_volume': 0.90,    # High confidence in daily FINRA data
            'alpha_vantage_options': 0.75, # Moderate confidence in AV options
            'polygon_live': 0.98,          # Very high confidence in Polygon live data
            'borrow_proxy': 0.60,          # Lower confidence in proxy calculations
            'fabricated': 0.0              # Zero confidence in fabricated data (banned)
        }
        
        # Rate limiting
        self.rate_limits = {
            'finra_api': {'calls_per_minute': 60, 'backoff_seconds': 1},
            'alpha_vantage': {'calls_per_minute': 5, 'backoff_seconds': 12},
            'polygon': {'calls_per_minute': 1000, 'backoff_seconds': 0.1}
        }
    
    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Get boolean environment variable"""
        value = os.getenv(key, '').lower()
        return value in ('true', '1', 'yes', 'on') if value else default
    
    def is_enabled(self) -> bool:
        """Check if free data mode is enabled"""
        return self.enabled
    
    def get_provider(self, data_type: str) -> str:
        """Get configured provider for data type"""
        return self.providers.get(data_type, 'unknown')
    
    def get_freshness_threshold(self, data_type: str, unit: str = 'hours') -> int:
        """Get freshness threshold for data type"""
        if unit == 'days':
            key = f"{data_type}_days"
        elif unit == 'minutes':
            key = f"{data_type}_minutes"
        else:
            key = f"{data_type}_hours"
        
        return self.freshness.get(key, 24)  # Default 24 hours
    
    def validate_data_source(self, data: Dict[str, Any]) -> bool:
        """
        Validate that data meets free-data-mode requirements
        Returns False if data appears fabricated or violates policies
        """
        if not self.enabled:
            return True  # No validation when free mode disabled
        
        # Check for source attribution
        if self.fabrication_guard['require_source_attribution']:
            if 'source' not in data or not data['source']:
                logger.warning("Data rejected: missing source attribution", data_sample=str(data)[:100])
                return False
        
        # Check for timestamp
        if self.fabrication_guard['require_timestamp']:
            if 'asof' not in data and 'ingested_at' not in data:
                logger.warning("Data rejected: missing timestamp", data_sample=str(data)[:100])
                return False
        
        # Check for banned default values
        for key, value in data.items():
            if isinstance(value, (int, float)) and value in self.fabrication_guard['banned_defaults']:
                logger.error("FABRICATION DETECTED: Banned default value", 
                           key=key, value=value, data_source=data.get('source', 'unknown'))
                raise ValueError(f"Fabricated data detected: {key}={value} matches banned default")
        
        # Check confidence score if present
        confidence = data.get('confidence', 1.0)
        if confidence <= 0:
            logger.warning("Data rejected: zero confidence", data_source=data.get('source'))
            return False
        
        return True
    
    def apply_confidence_weighting(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply confidence weighting based on data source
        """
        if not self.enabled:
            return data
        
        source = data.get('source', 'unknown')
        base_confidence = data.get('confidence', 1.0)
        
        # Get source-specific confidence multiplier
        source_weight = self.confidence_weights.get(source, 0.5)  # Default 0.5 for unknown sources
        
        # Apply weighting
        adjusted_confidence = base_confidence * source_weight
        
        # Add metadata
        result = data.copy()
        result['confidence'] = round(adjusted_confidence, 3)
        result['confidence_metadata'] = {
            'original_confidence': base_confidence,
            'source_weight': source_weight,
            'free_data_mode': True
        }
        
        return result
    
    def get_rate_limit(self, provider: str) -> Dict[str, int]:
        """Get rate limit configuration for provider"""
        return self.rate_limits.get(provider, {'calls_per_minute': 100, 'backoff_seconds': 1})
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        return {
            'enabled': self.enabled,
            'providers': self.providers,
            'freshness': self.freshness,
            'fabrication_guard': self.fabrication_guard,
            'confidence_weights': self.confidence_weights,
            'rate_limits': self.rate_limits
        }

# Global instance
free_data_config = FreeDataConfig()

# Convenience functions
def is_free_data_mode() -> bool:
    """Check if free data mode is enabled"""
    return free_data_config.is_enabled()

def validate_no_fabrication(data: Dict[str, Any]) -> bool:
    """Validate data against fabrication policies"""
    return free_data_config.validate_data_source(data)

def apply_source_confidence(data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply confidence weighting based on source"""
    return free_data_config.apply_confidence_weighting(data)