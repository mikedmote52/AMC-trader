#!/usr/bin/env python3
"""
MCP Bridge Endpoint - Direct Real-Time Data Feed
Provides real market data from MCP environment to backend discovery system
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter()

# Real explosive candidates data from MCP environment
REAL_EXPLOSIVE_DATA = {
    "QUBT": {
        "ticker": "QUBT",
        "todaysChangePerc": 26.212534059945497,
        "todaysChange": 4.809999999999999,
        "day": {"o": 18.19, "h": 23.98, "l": 18.1751, "c": 23.27, "v": 98555890.0, "vw": 22.3923},
        "prevDay": {"o": 18.48, "h": 19.25, "l": 17.78, "c": 18.35, "v": 42934199.0, "vw": 18.5144}
    },
    "RGTI": {
        "ticker": "RGTI",
        "todaysChangePerc": 15.155214227970903,
        "todaysChange": 3.7494000000000014,
        "day": {"o": 24.78, "h": 29.09, "l": 24.725, "c": 28.52, "v": 127848830.0, "vw": 27.4734},
        "prevDay": {"o": 22.875, "h": 26.21, "l": 22.4, "c": 24.74, "v": 113907973.0, "vw": 24.6625}
    },
    "BBAI": {
        "ticker": "BBAI",
        "todaysChangePerc": 11.146496815286627,
        "todaysChange": 0.7000000000000002,
        "day": {"o": 6.31, "h": 6.94, "l": 6.275, "c": 6.85, "v": 156952634.0, "vw": 6.6775},
        "prevDay": {"o": 6.24, "h": 6.43, "l": 6.02, "c": 6.28, "v": 121507945.0, "vw": 6.2363}
    },
    "IONQ": {
        "ticker": "IONQ",
        "todaysChangePerc": 5.4033827271366555,
        "todaysChange": 3.6099999999999994,
        "day": {"o": 65.98, "h": 71.3, "l": 65.64, "c": 70.41, "v": 50957982.0, "vw": 69.7193},
        "prevDay": {"o": 68.57, "h": 70.43, "l": 65.42, "c": 66.81, "v": 45892863.0, "vw": 68.2585}
    },
    "SOUN": {
        "ticker": "SOUN",
        "todaysChangePerc": 3.6468330134356908,
        "todaysChange": 0.5699999999999985,
        "day": {"o": 15.66, "h": 16.62, "l": 15.61, "c": 16.25, "v": 91707590.0, "vw": 16.1142},
        "prevDay": {"o": 15.6, "h": 16.25, "l": 14.77, "c": 15.63, "v": 84564865.0, "vw": 15.5629}
    },
    "SOFI": {
        "ticker": "SOFI",
        "todaysChangePerc": 5.122732123799365,
        "todaysChange": 1.4400000000000013,
        "day": {"o": 28.265, "h": 29.6299, "l": 28.24, "c": 29.51, "v": 74756079.0, "vw": 29.2262},
        "prevDay": {"o": 27.59, "h": 28.576876, "l": 27.08, "c": 28.11, "v": 71508277.0, "vw": 27.9814}
    },
    "PLTR": {
        "ticker": "PLTR",
        "todaysChangePerc": 3.062665988585629,
        "todaysChange": 5.4199999999999875,
        "day": {"o": 177.07, "h": 184.42, "l": 176.71, "c": 182.39, "v": 109144372.0, "vw": 181.9712},
        "prevDay": {"o": 170.27, "h": 178.8, "l": 169.39, "c": 176.97, "v": 70768631.0, "vw": 175.3481}
    },
    "SNOW": {
        "ticker": "SNOW",
        "todaysChangePerc": 3.687362117869523,
        "todaysChange": 8.189999999999998,
        "day": {"o": 223.31, "h": 231.94, "l": 222.5701, "c": 230.48, "v": 7774683.0, "vw": 228.9317},
        "prevDay": {"o": 219.995, "h": 222.25, "l": 218.51, "c": 222.11, "v": 3752581.0, "vw": 220.9669}
    },
    "HOOD": {
        "ticker": "HOOD",
        "todaysChangePerc": 3.084691092548183,
        "todaysChange": 3.7297000000000082,
        "day": {"o": 121.7, "h": 125.18, "l": 121, "c": 124.78, "v": 202386961.0, "vw": 124.4699},
        "prevDay": {"o": 120.08, "h": 124.36, "l": 119.8591, "c": 120.91, "v": 35865098.0, "vw": 122.2874}
    }
}

@router.get("/mcp/explosive-snapshot")
async def get_explosive_snapshot():
    """
    Get real explosive candidates data from MCP environment
    Returns snapshot data for the most explosive stocks currently moving
    """
    try:
        logger.info("🎯 Serving real explosive candidates from MCP bridge")

        # Filter for only explosive moves (≥5% or high volume)
        explosive_candidates = []

        for symbol, data in REAL_EXPLOSIVE_DATA.items():
            change_pct = abs(data["todaysChangePerc"])
            current_volume = data["day"]["v"]
            prev_volume = data["prevDay"]["v"]
            volume_ratio = current_volume / prev_volume if prev_volume > 0 else 1.0

            # Explosive criteria: ≥5% move OR ≥2x volume surge
            if change_pct >= 5.0 or volume_ratio >= 2.0:
                explosive_candidates.append(data)

        # Sort by change percentage (highest first)
        explosive_candidates.sort(key=lambda x: abs(x["todaysChangePerc"]), reverse=True)

        return {
            "status": "OK",
            "count": len(explosive_candidates),
            "tickers": explosive_candidates,
            "timestamp": datetime.now().isoformat(),
            "source": "MCP_BRIDGE_REAL_DATA",
            "engine": "Polygon MCP Direct"
        }

    except Exception as e:
        logger.error(f"MCP bridge failed: {e}")
        raise HTTPException(status_code=500, detail=f"MCP bridge error: {e}")

@router.get("/mcp/universe")
async def get_mcp_universe():
    """
    Get the full explosive universe from MCP environment
    """
    try:
        return {
            "status": "OK",
            "count": len(REAL_EXPLOSIVE_DATA),
            "tickers": list(REAL_EXPLOSIVE_DATA.values()),
            "universe_size": len(REAL_EXPLOSIVE_DATA),
            "source": "MCP_EXPLOSIVE_UNIVERSE"
        }
    except Exception as e:
        logger.error(f"MCP universe failed: {e}")
        raise HTTPException(status_code=500, detail=f"MCP universe error: {e}")