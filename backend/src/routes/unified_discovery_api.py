#!/usr/bin/env python3
"""
UNIFIED DISCOVERY API - Single Entry Point
Uses only the unified MCP-based discovery system
NO FALLBACKS, NO MOCK DATA, NO ALTERNATIVES
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any

from backend.src.discovery.unified_discovery import UnifiedDiscoverySystem

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/discovery/opportunities")
@router.get("/api/contenders")  # Legacy endpoint compatibility
async def get_opportunities(limit: int = Query(20, le=100, ge=1)):
    """
    THE ONLY DISCOVERY ENDPOINT
    Returns pre-breakout opportunities using real-time MCP data
    Fails with clear error if real data unavailable
    """
    try:
        discovery = UnifiedDiscoverySystem()
        result = await discovery.discover_opportunities(limit=limit)

        if result['status'] == 'FAILED':
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Real-time market data unavailable",
                    "message": result.get('alert', 'Data source failure'),
                    "data_source": result.get('data_source', 'UNKNOWN'),
                    "system_health": result.get('system_health', {})
                }
            )

        return {
            "success": True,
            "data": result['candidates'],
            "count": len(result['candidates']),
            "metadata": {
                "execution_time_sec": result['execution_time_sec'],
                "data_source": result['data_source'],
                "data_age_status": result['data_age_status'],
                "universe_size": result['universe_size'],
                "filter_pass_rate_pct": result['filter_pass_rate_pct'],
                "summary": result['summary'],
                "system_health": result['system_health']
            },
            "timestamp": result['timestamp']
        }

    except Exception as e:
        logger.error(f"❌ Discovery API failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Discovery system error",
                "message": str(e),
                "alert": "🚨 TRADING RECOMMENDATIONS UNAVAILABLE"
            }
        )

@router.get("/discovery/health")
async def discovery_health():
    """
    Check discovery system health
    Returns detailed status of MCP connectivity and data freshness
    """
    try:
        discovery = UnifiedDiscoverySystem()

        # Quick validation test
        try:
            # Test MCP connectivity without full discovery
            test_result = await discovery.get_market_universe()
            universe_size = len(test_result)

            return {
                "status": "healthy",
                "mcp_operational": True,
                "universe_size": universe_size,
                "data_source": "POLYGON_MCP_REAL_TIME",
                "no_fallbacks": True,
                "timestamp": discovery.get_timestamp()
            }

        except Exception as health_error:
            return {
                "status": "degraded",
                "mcp_operational": False,
                "error": str(health_error),
                "data_source": "UNAVAILABLE",
                "alert": "🚨 Real-time data unavailable",
                "timestamp": discovery.get_timestamp()
            }

    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "alert": "🚨 Discovery system offline"
        }

@router.get("/discovery/system-status")
async def system_status():
    """
    Detailed system status for monitoring
    Shows configuration and operational status
    """
    try:
        discovery = UnifiedDiscoverySystem()

        return {
            "system": "UNIFIED_AMC_DISCOVERY",
            "version": "1.0.0",
            "configuration": {
                "max_daily_move_pct": discovery.max_daily_move_pct,
                "min_volume_ratio": discovery.min_volume_ratio,
                "max_volume_ratio": discovery.max_volume_ratio,
                "price_range": [discovery.min_price, discovery.max_price],
                "max_data_age_minutes": discovery.max_data_age_minutes
            },
            "architecture": {
                "data_source": "POLYGON_MCP_ONLY",
                "fallbacks_enabled": False,
                "mock_data_enabled": False,
                "real_time_only": True
            },
            "filters": {
                "post_explosion_filter": True,
                "volume_explosion_filter": True,
                "price_range_filter": True
            }
        }

    except Exception as e:
        logger.error(f"❌ System status failed: {e}")
        return {
            "system": "UNIFIED_AMC_DISCOVERY",
            "status": "error",
            "error": str(e)
        }

# Remove all other discovery endpoints - force single entry point
@router.get("/discovery/legacy-endpoint")
async def legacy_endpoint():
    """Redirect legacy endpoints to unified system"""
    raise HTTPException(
        status_code=410,
        detail={
            "error": "Legacy endpoint removed",
            "message": "Use /discovery/opportunities instead",
            "redirect": "/discovery/opportunities"
        }
    )