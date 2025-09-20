#!/usr/bin/env python3
"""
Explosive Discovery API - Enhanced Polygon-based Discovery
Parallel system for explosive growth stock discovery
Does not interfere with existing discovery routes
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/discovery/explosive")
async def get_explosive_candidates(limit: int = Query(20, le=100, ge=1)):
    """
    Enhanced explosive discovery endpoint
    Uses Polygon MCP bridge for explosive growth detection
    Runs in parallel with existing discovery systems
    """
    try:
        from backend.src.discovery.polygon_explosive_discovery import create_polygon_explosive_discovery

        logger.info(f"💥 Starting explosive discovery with limit={limit}")

        # Create discovery engine
        discovery_engine = create_polygon_explosive_discovery()

        # Run explosive discovery
        result = await discovery_engine.discover_explosive_stocks(limit=limit)

        if result['status'] == 'success':
            return {
                "success": True,
                "data": result['candidates'],
                "count": result['count'],
                "metadata": {
                    "engine": result.get('engine', 'Unknown'),
                    "strategy": result.get('strategy', 'Unknown'),
                    "execution_time_sec": result.get('execution_time_sec', 0),
                    "pipeline_stats": result.get('pipeline_stats', {}),
                    "universe_size": result.get('pipeline_stats', {}).get('universe_size', 0),
                    "analyzed_count": result.get('pipeline_stats', {}).get('analyzed', 0),
                    "filter_efficiency": f"{result.get('pipeline_stats', {}).get('analyzed', 0)}/{result.get('pipeline_stats', {}).get('universe_size', 0)}"
                },
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Explosive discovery failed",
                    "message": result.get('error', 'Unknown error'),
                    "engine": "Polygon MCP Explosive Discovery",
                    "timestamp": datetime.now().isoformat()
                }
            )

    except ImportError as e:
        logger.error(f"Failed to import explosive discovery: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Explosive discovery engine not available",
                "message": f"Import error: {e}",
                "timestamp": datetime.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Explosive discovery API failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Explosive discovery system error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

@router.get("/discovery/explosive/test")
async def test_explosive_discovery():
    """
    Test explosive discovery system
    Returns system status and sample discovery run
    """
    try:
        from backend.src.discovery.polygon_explosive_discovery import create_polygon_explosive_discovery

        logger.info("🧪 Testing explosive discovery system")

        # Create discovery engine
        discovery_engine = create_polygon_explosive_discovery()

        # Run small test discovery
        result = await discovery_engine.discover_explosive_stocks(limit=5)

        return {
            "test_status": "success" if result['status'] == 'success' else "failed",
            "engine_available": True,
            "sample_results": {
                "count": result.get('count', 0),
                "execution_time_sec": result.get('execution_time_sec', 0),
                "candidates": result.get('candidates', [])[:3],  # First 3 candidates
                "pipeline_stats": result.get('pipeline_stats', {})
            },
            "system_info": {
                "engine": result.get('engine', 'Unknown'),
                "strategy": result.get('strategy', 'Unknown'),
                "timestamp": datetime.now().isoformat()
            }
        }

    except ImportError as e:
        return {
            "test_status": "engine_unavailable",
            "engine_available": False,
            "error": f"Import error: {e}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "test_status": "system_error",
            "engine_available": True,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/discovery/explosive/health")
async def explosive_discovery_health():
    """
    Check explosive discovery system health
    """
    try:
        from backend.src.discovery.polygon_explosive_discovery import create_polygon_explosive_discovery
        from backend.src.services.mcp_polygon_bridge import mcp_polygon_bridge

        # Test MCP bridge
        test_tickers = ['AAPL', 'TSLA', 'NVDA']
        snapshot_result = await mcp_polygon_bridge.get_market_snapshot(tickers=test_tickers)

        # Test discovery engine creation
        discovery_engine = create_polygon_explosive_discovery()

        return {
            "status": "healthy",
            "components": {
                "explosive_discovery_engine": True,
                "mcp_polygon_bridge": True,
                "market_data_access": snapshot_result.get('status') == 'OK',
                "universe_size": len(mcp_polygon_bridge._get_liquid_universe())
            },
            "test_results": {
                "snapshot_status": snapshot_result.get('status'),
                "snapshot_count": snapshot_result.get('count', 0)
            },
            "timestamp": datetime.now().isoformat()
        }

    except ImportError as e:
        return {
            "status": "degraded",
            "error": f"Component unavailable: {e}",
            "components": {
                "explosive_discovery_engine": False,
                "mcp_polygon_bridge": False,
                "market_data_access": False
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }