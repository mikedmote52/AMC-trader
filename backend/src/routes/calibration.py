"""
Calibration API endpoints for AMC-TRADER strategy management
"""
import os
import json
import logging
from fastapi import APIRouter, Body, HTTPException
from typing import Dict, Any, Optional
from ..strategy_resolver import resolve_effective_strategy, get_strategy_metadata

router = APIRouter()
logger = logging.getLogger(__name__)

def _load_calibration_config():
    """Load calibration config from file"""
    try:
        calibration_path = os.path.join(os.path.dirname(__file__), "../../../calibration/active.json")
        if os.path.exists(calibration_path):
            with open(calibration_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Could not load calibration config: {e}")
    return {}

def _save_calibration_config(config: dict):
    """Save calibration config to file"""
    try:
        calibration_path = os.path.join(os.path.dirname(__file__), "../../../calibration/active.json")
        with open(calibration_path, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Could not save calibration config: {e}")
        return False

@router.get("/status")
def get_status():
    """Get current strategy and configuration status"""
    try:
        config = _load_calibration_config()
        
        # Get effective strategy
        effective_strategy = os.getenv("FORCE_STRATEGY") or os.getenv("SCORING_STRATEGY", "legacy_v0")
        
        # Get current preset
        preset = config.get("scoring", {}).get("preset")
        
        # Calculate hash for weights and thresholds (simple hash for now)
        weights = config.get("scoring", {}).get("hybrid_v1", {}).get("weights", {})
        thresholds = config.get("scoring", {}).get("hybrid_v1", {}).get("thresholds", {})
        
        weights_hash = str(hash(str(sorted(weights.items()))))[:8] if weights else "none"
        thresholds_hash = str(hash(str(sorted(thresholds.items()))))[:8] if thresholds else "none"
        
        return {
            "effective_strategy": effective_strategy,
            "preset": preset,
            "weights_hash": weights_hash,
            "thresholds_hash": thresholds_hash,
            "thresholds_snapshot": thresholds,
            "emergency_flag": os.getenv("EMERGENCY_OVERRIDE") is not None,
            "last_updated": "2025-09-04T00:00:00Z"  # TODO: track actual update time
        }
    except Exception as e:
        logger.error(f"Error getting calibration status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/hybrid_v1")
def patch_hybrid_v1(payload: Dict[str, Any] = Body(...)):
    """
    Update hybrid_v1 thresholds and/or weights
    
    Body example:
    {
        "thresholds": {"vwap_proximity_pct": 0.5},
        "weights": {"catalyst": 0.25, "squeeze": 0.20}
    }
    """
    try:
        config = _load_calibration_config()
        
        # Ensure structure exists
        if "scoring" not in config:
            config["scoring"] = {}
        if "hybrid_v1" not in config["scoring"]:
            config["scoring"]["hybrid_v1"] = {"weights": {}, "thresholds": {}}
        
        # Update thresholds if provided
        if "thresholds" in payload:
            thresholds = payload["thresholds"]
            config["scoring"]["hybrid_v1"]["thresholds"].update(thresholds)
            logger.info(f"Updated hybrid_v1 thresholds: {thresholds}")
        
        # Update weights if provided
        if "weights" in payload:
            weights = payload["weights"]
            # Normalize weights to sum to 1.0
            total = sum(weights.values()) if weights else 1.0
            if total > 0:
                normalized_weights = {k: v/total for k, v in weights.items()}
                config["scoring"]["hybrid_v1"]["weights"].update(normalized_weights)
                logger.info(f"Updated hybrid_v1 weights: {normalized_weights}")
        
        # Save config
        if not _save_calibration_config(config):
            raise HTTPException(status_code=500, detail="Failed to save configuration")
        
        # TODO: Invalidate Redis cache
        # cache.invalidate_namespace("contenders:hybrid_v1")
        
        return {
            "ok": True,
            "thresholds": config["scoring"]["hybrid_v1"]["thresholds"],
            "weights": config["scoring"]["hybrid_v1"]["weights"]
        }
        
    except Exception as e:
        logger.error(f"Error updating hybrid_v1 config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Alias endpoint to prevent 404s
@router.patch("/discovery/calibration/hybrid_v1") 
def patch_hybrid_v1_alias(payload: Dict[str, Any] = Body(...)):
    """Alias endpoint for hybrid_v1 configuration updates"""
    return patch_hybrid_v1(payload)