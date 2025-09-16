"""
AlphaStack 4.1 API endpoints for AMC-trader backend.
Provides real data from database tables (no mock payloads).
"""

from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import asyncio
import asyncpg
import os
import json

router = APIRouter()

# Pydantic models for AlphaStack 4.1 responses
class CandidateOut(BaseModel):
    symbol: str
    total_score: float
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

# Database connection helper
async def get_db_connection():
    """Get async database connection."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=503, detail="Database not configured")

    try:
        conn = await asyncpg.connect(database_url)
        return conn
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

def map_row_to_candidate(row: asyncpg.Record) -> CandidateOut:
    """Map database row to CandidateOut model."""
    # Handle both direct columns and JSON payload columns
    symbol = getattr(row, 'ticker', None) or getattr(row, 'symbol', 'UNKNOWN')
    score = getattr(row, 'score', 0.0) or 0.0

    # Try to extract price from different possible columns
    price = None
    if hasattr(row, 'price') and row.price:
        price = float(row.price)
    elif hasattr(row, 'snapshot') and row.snapshot:
        try:
            snapshot_data = row.snapshot if isinstance(row.snapshot, dict) else json.loads(row.snapshot)
            price = snapshot_data.get('price')
        except:
            pass
    elif hasattr(row, 'payload') and row.payload:
        try:
            payload_data = row.payload if isinstance(row.payload, dict) else json.loads(row.payload)
            price = payload_data.get('price')
        except:
            pass

    # Extract other fields
    action_tag = getattr(row, 'action_tag', None)
    entry = getattr(row, 'entry', None)
    stop = getattr(row, 'stop', None)
    tp1 = getattr(row, 'tp1', None)
    tp2 = getattr(row, 'tp2', None)
    updated_at = getattr(row, 'updated_at', None)

    # Build snapshot from available data
    snapshot = {}
    if hasattr(row, 'snapshot') and row.snapshot:
        try:
            snapshot = row.snapshot if isinstance(row.snapshot, dict) else json.loads(row.snapshot)
        except:
            pass
    elif hasattr(row, 'payload') and row.payload:
        try:
            snapshot = row.payload if isinstance(row.payload, dict) else json.loads(row.payload)
        except:
            pass

    # Add additional fields to snapshot if available
    if price and 'price' not in snapshot:
        snapshot['price'] = price
    if hasattr(row, 'intraday_relvol') and row.intraday_relvol:
        snapshot['intraday_relvol'] = float(row.intraday_relvol)

    return CandidateOut(
        symbol=symbol,
        total_score=float(score) if score else 0.0,
        action_tag=action_tag,
        price=float(price) if price else None,
        entry=float(entry) if entry else None,
        stop=float(stop) if stop else None,
        tp1=float(tp1) if tp1 else None,
        tp2=float(tp2) if tp2 else None,
        snapshot=snapshot if snapshot else None,
        updated_at=updated_at
    )

@router.get("/candidates/top", response_model=CandidatesResp)
async def get_top_candidates(limit: int = Query(50, ge=1, le=500)):
    """Get top candidates from database."""
    conn = await get_db_connection()
    try:
        # Try different possible table names and structures
        candidates = []

        # First try candidates_latest table
        try:
            query = """
            SELECT * FROM candidates_latest
            ORDER BY score DESC NULLS LAST
            LIMIT $1
            """
            rows = await conn.fetch(query, limit)
            candidates = [map_row_to_candidate(row) for row in rows]
        except asyncpg.UndefinedTableError:
            # Fallback to monitoring.recommendation_tracking
            try:
                query = """
                SELECT
                    symbol as ticker,
                    discovery_score as score,
                    'watchlist' as action_tag,
                    discovery_price as price,
                    NULL as entry,
                    NULL as stop,
                    NULL as tp1,
                    NULL as tp2,
                    NULL as snapshot,
                    updated_at
                FROM monitoring.recommendation_tracking
                WHERE recommendation_date >= NOW() - INTERVAL '24 hours'
                ORDER BY discovery_score DESC NULLS LAST
                LIMIT $1
                """
                rows = await conn.fetch(query, limit)
                candidates = [map_row_to_candidate(row) for row in rows]
            except asyncpg.UndefinedTableError:
                # No suitable table found, return empty list
                pass

        return CandidatesResp(items=candidates)

    finally:
        await conn.close()

@router.get("/explosive", response_model=ExplosiveResp)
async def get_explosive_candidates():
    """Get explosive candidates from database."""
    conn = await get_db_connection()
    try:
        # Try different possible table names and structures
        candidates = []

        # First try explosive_latest table
        try:
            query = """
            SELECT * FROM explosive_latest
            ORDER BY score DESC NULLS LAST
            """
            rows = await conn.fetch(query)
            candidates = [map_row_to_candidate(row) for row in rows]
        except asyncpg.UndefinedTableError:
            # Fallback to monitoring.recommendation_tracking with explosive filter
            try:
                query = """
                SELECT
                    symbol as ticker,
                    discovery_score as score,
                    'trade_ready' as action_tag,
                    discovery_price as price,
                    NULL as entry,
                    NULL as stop,
                    NULL as tp1,
                    NULL as tp2,
                    NULL as snapshot,
                    updated_at
                FROM monitoring.recommendation_tracking
                WHERE (outcome_classification = 'EXPLOSIVE' OR discovery_score > 0.8)
                  AND recommendation_date >= NOW() - INTERVAL '24 hours'
                ORDER BY discovery_score DESC NULLS LAST
                LIMIT 20
                """
                rows = await conn.fetch(query)
                candidates = [map_row_to_candidate(row) for row in rows]
            except asyncpg.UndefinedTableError:
                # No suitable table found, return empty list
                pass

        return ExplosiveResp(explosive_top=candidates)

    finally:
        await conn.close()

@router.get("/telemetry", response_model=TelemetryResp)
async def get_telemetry():
    """Get system telemetry and health information."""
    conn = await get_db_connection()
    try:
        # Check data freshness from candidates_latest or fallback table
        max_updated = None
        stale_data_detected = True
        system_ready = False

        # Try to get latest update time from candidates table
        try:
            max_updated_result = await conn.fetchval(
                "SELECT MAX(updated_at) FROM candidates_latest"
            )
            max_updated = max_updated_result
        except asyncpg.UndefinedTableError:
            # Fallback to monitoring table
            try:
                max_updated_result = await conn.fetchval(
                    "SELECT MAX(updated_at) FROM monitoring.recommendation_tracking"
                )
                max_updated = max_updated_result
            except asyncpg.UndefinedTableError:
                pass

        # Determine if data is stale (older than 5 minutes)
        if max_updated:
            from datetime import timedelta
            now = datetime.now(timezone.utc)
            if max_updated.tzinfo is None:
                max_updated = max_updated.replace(tzinfo=timezone.utc)

            time_diff = now - max_updated
            stale_data_detected = time_diff > timedelta(seconds=300)  # 5 minutes
            system_ready = not stale_data_detected

        # Try to get pipeline stats from discovery_flow_stats
        pipeline_stats = PipelineStats()
        try:
            stats_row = await conn.fetchrow("""
                SELECT universe_size, final_candidates
                FROM monitoring.discovery_flow_stats
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            if stats_row:
                pipeline_stats.universe_size = stats_row['universe_size']
                pipeline_stats.scored = stats_row['final_candidates']
        except asyncpg.UndefinedTableError:
            # No pipeline stats available
            pass

        return TelemetryResp(
            system_health=SystemHealth(system_ready=system_ready),
            production_health=ProductionHealth(stale_data_detected=stale_data_detected),
            pipeline_stats=pipeline_stats
        )

    finally:
        await conn.close()