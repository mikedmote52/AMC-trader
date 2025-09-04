"""
Strategy Resolution for Production Deployment
Enforces Hybrid V1 in production while maintaining emergency controls
"""
import os
from datetime import datetime, timezone


def resolve_effective_strategy(request_strategy: str = None, state=None) -> str:
    """
    Resolve the effective strategy with production enforcement
    
    Priority:
    1. Emergency override (15-min legacy fallback)
    2. Hard force in production (FORCE_STRATEGY env)
    3. Per-request override (staging only)
    4. Environment default
    
    Args:
        request_strategy: Strategy requested via ?strategy= parameter
        state: Application state (for emergency override checking)
    
    Returns:
        Effective strategy: "hybrid_v1" or "legacy_v0"
    """
    
    # 1) Emergency override wins (existing 15-min override)
    if _emergency_override_active():
        return "legacy_v0"
    
    # 2) Hard force in production (Render)
    force = os.getenv("FORCE_STRATEGY", "").strip()
    if force in {"hybrid_v1", "legacy_v0"}:
        return force
    
    # 3) Optional per-request override (for staging only)
    allow_override = os.getenv("ALLOW_STRATEGY_OVERRIDE", "false").lower() == "true"
    if allow_override and request_strategy in {"hybrid_v1", "legacy_v0"}:
        return request_strategy
    
    # 4) Environment default (fallback)
    return os.getenv("SCORING_STRATEGY", "legacy_v0")


def _emergency_override_active() -> bool:
    """Check if emergency override is currently active"""
    emergency_override = os.getenv("EMERGENCY_OVERRIDE")
    if not emergency_override:
        return False
    
    try:
        expire_time = int(emergency_override)
        if datetime.now(timezone.utc).timestamp() < expire_time:
            return True
        else:
            # Clean up expired override
            os.environ.pop("EMERGENCY_OVERRIDE", None)
            return False
    except (ValueError, TypeError):
        return False


def get_strategy_metadata(effective: str = None, preset: str = None, weights_hash: str = None, thresholds_hash: str = None) -> dict:
    """Get current strategy resolution metadata for diagnostics"""
    if effective is None:
        effective = resolve_effective_strategy()
    
    return {
        "strategy": effective,
        "effective_strategy": effective,
        "preset": preset,
        "weights_hash": weights_hash,
        "thresholds_hash": thresholds_hash,
        "force_strategy": os.getenv("FORCE_STRATEGY", ""),
        "allow_override": os.getenv("ALLOW_STRATEGY_OVERRIDE", "false"),
        "env_strategy": os.getenv("SCORING_STRATEGY", "legacy_v0"),
        "emergency_active": _emergency_override_active(),
        "emergency_expires": _get_emergency_expiry()
    }


def _get_emergency_expiry() -> str:
    """Get emergency override expiry time as ISO string"""
    if not _emergency_override_active():
        return None
    
    try:
        emergency_override = os.getenv("EMERGENCY_OVERRIDE")
        expire_time = int(emergency_override)
        return datetime.fromtimestamp(expire_time, timezone.utc).isoformat()
    except:
        return None