#!/usr/bin/env python3
"""
MCP Deployment Configuration for AMC-TRADER
Handles environment detection and graceful fallbacks for Render deployment
"""
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MCPEnvironmentConfig:
    """Configuration class for MCP environment detection and fallbacks"""

    def __init__(self):
        self.is_claude_environment = self._detect_claude_environment()
        self.is_render_deployment = self._detect_render_deployment()
        self.polygon_api_key = os.getenv('POLYGON_API_KEY')

    def _detect_claude_environment(self) -> bool:
        """Detect if we're running in Claude Code environment with MCP support"""
        try:
            # Check multiple ways MCP functions might be available
            try:
                import builtins
                if hasattr(builtins, 'mcp__polygon__get_aggs'):
                    return True
            except:
                pass

            # Check global namespace
            if 'mcp__polygon__get_aggs' in globals():
                return True

            # Check if we have environment indicators that suggest MCP availability
            if os.getenv('CLAUDE_CODE_ENV') or os.getenv('MCP_AVAILABLE'):
                return True

            return False
        except:
            return False

    def _detect_render_deployment(self) -> bool:
        """Detect if we're running in Render deployment environment"""
        return bool(os.getenv('RENDER_SERVICE_NAME') or os.getenv('RENDER'))

    def get_data_sources_config(self) -> Dict[str, bool]:
        """Get configuration for available data sources"""
        # Check if we're in any production environment with MCP access
        is_production_with_mcp = (
            self.is_claude_environment or
            self.is_render_deployment or
            os.getenv('AMC_TRADER_ENV') or
            os.getenv('MCP_AVAILABLE')
        )

        if is_production_with_mcp:
            # Full MCP capabilities available
            return {
                'mcp_functions': True,
                'short_interest': True,
                'news_sentiment': True,
                'aggregates': True,
                'options_flow': True,  # Try with graceful fallback
                'realtime_trades': True,  # Try with graceful fallback
                'fallback_to_api': False
            }
        else:
            # Local development without MCP
            return {
                'mcp_functions': False,
                'short_interest': False,
                'news_sentiment': False,
                'aggregates': False,
                'options_flow': False,
                'realtime_trades': False,
                'fallback_to_api': False
            }

    def get_scoring_weights_for_environment(self) -> Dict[str, int]:
        """Get optimized scoring weights based on available data sources"""
        config = self.get_data_sources_config()

        if config['mcp_functions']:
            # Full 8-pillar system with MCP
            return {
                "price_momentum": 20,
                "volume_surge": 20,
                "float_short": 15,
                "catalyst": 15,
                "sentiment": 10,
                "technical": 10,
                "options_flow": 5,
                "realtime_momentum": 5,
            }
        else:
            # Simplified system for deployment without MCP
            return {
                "price_momentum": 35,
                "volume_surge": 35,
                "float_short": 0,    # Not available
                "catalyst": 15,
                "sentiment": 0,      # Not available
                "technical": 15,
                "options_flow": 0,   # Not available
                "realtime_momentum": 0, # Not available
            }

    def log_environment_status(self):
        """Log current environment configuration"""
        logger.info(f"🔧 AMC-TRADER Environment Configuration:")
        logger.info(f"   Claude Environment: {self.is_claude_environment}")
        logger.info(f"   Render Deployment: {self.is_render_deployment}")
        logger.info(f"   Polygon API Key: {'Set' if self.polygon_api_key else 'Missing'}")

        config = self.get_data_sources_config()
        available_sources = [k for k, v in config.items() if v]
        logger.info(f"   Available Data Sources: {available_sources}")

        weights = self.get_scoring_weights_for_environment()
        active_pillars = [k for k, v in weights.items() if v > 0]
        logger.info(f"   Active Scoring Pillars: {active_pillars}")

# Global configuration instance
mcp_config = MCPEnvironmentConfig()

def get_deployment_ready_weights() -> Dict[str, int]:
    """Get deployment-ready scoring weights"""
    return mcp_config.get_scoring_weights_for_environment()

def is_mcp_available() -> bool:
    """Check if MCP functions are available"""
    return mcp_config.is_claude_environment

def get_environment_info() -> Dict[str, Any]:
    """Get complete environment information"""
    return {
        'claude_environment': mcp_config.is_claude_environment,
        'render_deployment': mcp_config.is_render_deployment,
        'polygon_api_available': bool(mcp_config.polygon_api_key),
        'data_sources': mcp_config.get_data_sources_config(),
        'scoring_weights': mcp_config.get_scoring_weights_for_environment()
    }