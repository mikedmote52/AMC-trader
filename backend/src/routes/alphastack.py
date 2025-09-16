"""
AlphaStack 4.1 API endpoints for AMC-trader backend.
Provides real data from Redis cache (matches discovery job output).
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import redis.asyncio as redis
import os
import json
import logging

from backend.src.constants import CACHE_KEY_CONTENDERS

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for AlphaStack 4.1 responses
class CandidateOut(BaseModel):
    symbol: str
    ticker: str = None  # For compatibility
    total_score: float
    score: float = None  # For compatibility
    action_tag: Optional[str] = None
    price: Optional[float] = None
    entry: Optional[float] = None
    stop: Optional[float] = None
    tp1: Optional[float] = None
    tp2: Optional[float] = None
    snapshot: Optional[Dict[str, Any]] = None
    updated_at: Optional[datetime] = None

class CandidatesResp(BaseModel):
    schema_version: str = "4.1"
    items: List[CandidateOut]

class ExplosiveResp(BaseModel):
    schema_version: str = "4.1"
    explosive_top: List[CandidateOut]

class SystemHealth(BaseModel):
    system_ready: bool

class ProductionHealth(BaseModel):
    stale_data_detected: bool

class PipelineStats(BaseModel):
    universe_size: Optional[int] = None
    enriched: Optional[int] = None
    filtered: Optional[int] = None
    scored: Optional[int] = None

class TelemetryResp(BaseModel):
    schema_version: str = "4.1"
    system_health: SystemHealth
    production_health: ProductionHealth
    pipeline_stats: PipelineStats

async def fetch_discovery_cache() -> Dict[str, Any]:
    """Fetch discovery results from Redis cache"""
    try:
        redis_client = redis.from_url(os.getenv('REDIS_URL'))
        cache_data = await redis_client.get(CACHE_KEY_CONTENDERS)
        await redis_client.close()

        if cache_data:
            try:
                payload = json.loads(cache_data)
                logger.info(f"Found cached discovery data: {payload.get('count', 0)} candidates")
                return payload
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse cache data: {e}")
                return {}
        else:
            logger.warning("No discovery cache data found")
            return {}

    except Exception as e:
        logger.error(f"Failed to fetch discovery cache: {e}")
        return {}

def map_candidate_data(candidate: Dict[str, Any]) -> CandidateOut:
    """Map cached candidate data to CandidateOut model with safety guards"""
    snapshot = {}

    # Handle various snapshot data formats
    if isinstance(candidate.get('snapshot'), dict):
        snapshot = candidate['snapshot']
    elif candidate.get('relative_volume'):
        snapshot['intraday_relvol'] = float(candidate['relative_volume'])
    if candidate.get('volume'):
        snapshot['volume'] = int(candidate['volume'])

    # Handle price from multiple possible locations
    price = 0.0
    if candidate.get('price'):
        price = float(candidate['price'])
    elif candidate.get('snapshot', {}).get('price'):
        price = float(candidate['snapshot']['price'])
    elif candidate.get('current_price'):
        price = float(candidate['current_price'])

    # Handle score from multiple possible fields
    score = 0.0
    if candidate.get('total_score'):
        score = float(candidate['total_score'])
    elif candidate.get('score'):
        score = float(candidate['score'])
    elif candidate.get('confidence_score'):
        score = float(candidate['confidence_score'])

    symbol = candidate.get('symbol', candidate.get('ticker', 'UNKNOWN'))

    return CandidateOut(
        symbol=symbol,
        ticker=symbol,  # For compatibility
        total_score=score,
        score=score,  # For compatibility
        action_tag=candidate.get('action_tag', candidate.get('tag', 'MONITOR')),
        price=price if price > 0 else None,
        entry=float(candidate['entry']) if candidate.get('entry') else None,
        stop=float(candidate['stop']) if candidate.get('stop') else None,
        tp1=float(candidate['tp1']) if candidate.get('tp1') else None,
        tp2=float(candidate['tp2']) if candidate.get('tp2') else None,
        snapshot=snapshot if snapshot else None,
        updated_at=None  # Could parse from cache timestamp if needed
    )

@router.get("/candidates/top", response_model=CandidatesResp)
async def get_top_candidates(limit: int = Query(50, ge=1, le=500)):
    """Get top candidates from Redis cache."""
    try:
        cache_payload = await fetch_discovery_cache()

        if not cache_payload:
            logger.warning("No cache data available, returning empty results")
            return CandidatesResp(items=[])

        candidates_data = cache_payload.get('candidates', [])

        # Apply limit and convert to CandidateOut models
        limited_candidates = candidates_data[:limit] if candidates_data else []
        candidates = [map_candidate_data(candidate) for candidate in limited_candidates]

        logger.info(f"Returning {len(candidates)} candidates (requested limit: {limit})")
        return CandidatesResp(items=candidates)

    except Exception as e:
        logger.error(f"Failed to fetch candidates: {e}")
        # Return empty but valid response instead of 500 error
        return CandidatesResp(items=[])

@router.get("/explosive", response_model=ExplosiveResp)
async def get_explosive_candidates():
    """Get explosive/high-momentum candidates from cache."""
    try:
        cache_payload = await fetch_discovery_cache()

        if not cache_payload:
            return ExplosiveResp(explosive_top=[])

        candidates_data = cache_payload.get('candidates', [])

        # Filter for high-score candidates (explosive criteria)
        explosive_candidates = []
        for candidate in candidates_data:
            # Consider explosive if high score or trade_ready tag
            score = candidate.get('total_score', candidate.get('score', 0))
            action_tag = candidate.get('action_tag', candidate.get('tag', ''))

            if (isinstance(score, (int, float)) and score >= 70.0) or action_tag == 'trade_ready':
                explosive_candidates.append(candidate)

        # Limit to top 20 explosive candidates
        explosive_candidates = explosive_candidates[:20]
        explosive = [map_candidate_data(candidate) for candidate in explosive_candidates]

        logger.info(f"Returning {len(explosive)} explosive candidates")
        return ExplosiveResp(explosive_top=explosive)

    except Exception as e:
        logger.error(f"Failed to fetch explosive candidates: {e}")
        return ExplosiveResp(explosive_top=[])

@router.get("/telemetry", response_model=TelemetryResp)
async def get_telemetry():
    """Get system telemetry and health status."""
    try:
        # Check Redis connectivity
        redis_connected = False
        cache_age_seconds = None

        try:
            redis_client = redis.from_url(os.getenv('REDIS_URL'))
            await redis_client.ping()
            redis_connected = True

            # Check cache freshness using TTL
            cache_exists = await redis_client.exists(CACHE_KEY_CONTENDERS)
            cache_ttl = await redis_client.ttl(CACHE_KEY_CONTENDERS) if cache_exists else -1

            await redis_client.close()

        except Exception as e:
            logger.warning(f"Redis connectivity check failed: {e}")
            cache_exists = False
            cache_ttl = -1

        # Determine system status based on Redis TTL
        # If key exists and TTL > 0, data is fresh
        # Target TTL is 600s (10 minutes), job runs every 5 minutes
        system_ready = redis_connected and cache_exists and cache_ttl > 0
        stale_data_detected = not (cache_exists and cache_ttl > 0)

        pipeline_stats = PipelineStats(
            universe_size=None,  # Could extract from cache payload if available
            enriched=None,
            filtered=None,
            scored=None
        )

        return TelemetryResp(
            system_health=SystemHealth(system_ready=system_ready),
            production_health=ProductionHealth(stale_data_detected=stale_data_detected),
            pipeline_stats=pipeline_stats
        )

    except Exception as e:
        logger.error(f"Telemetry error: {e}")
        return TelemetryResp(
            system_health=SystemHealth(system_ready=False),
            production_health=ProductionHealth(stale_data_detected=True),
            pipeline_stats=PipelineStats()
        )