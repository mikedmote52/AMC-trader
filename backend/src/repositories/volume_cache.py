"""
Volume Cache Repository - PostgreSQL cache for 20-day average volumes.
Stage 4 optimization from Squeeze-Prophet architecture.

CRITICAL: This repository ONLY handles database operations.
NO data generation, NO fallbacks, NO mock data.
"""
from typing import Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()


class VolumeCacheRepository:
    """Repository for cached volume averages - NO FAKE DATA"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def fetch_batch(self, symbols: List[str]) -> Dict[str, float]:
        """
        Fetch 20-day average volumes for multiple symbols.

        Returns ONLY cached data from database.
        If symbol not in cache, it will NOT be in returned dict.
        NO fallbacks, NO defaults, NO fake data.

        Args:
            symbols: List of stock symbols to fetch

        Returns:
            Dict mapping symbol to avg_volume_20d (only for cached symbols)
        """
        if not symbols:
            return {}

        try:
            # Query cached averages (only fresh data within 24 hours)
            query = text("""
                SELECT symbol, avg_volume_20d
                FROM volume_averages
                WHERE symbol = ANY(:symbols)
                AND last_updated > NOW() - INTERVAL '24 hours'
                AND avg_volume_20d > 0
            """)

            result = await self.session.execute(query, {"symbols": symbols})
            rows = result.fetchall()

            cache_data = {row[0]: float(row[1]) for row in rows}

            # Log cache statistics
            cache_hit_rate = len(cache_data) / len(symbols) * 100 if symbols else 0
            logger.info(
                "Volume cache lookup",
                requested=len(symbols),
                found=len(cache_data),
                hit_rate=f"{cache_hit_rate:.1f}%",
                missing=len(symbols) - len(cache_data)
            )

            return cache_data

        except Exception as e:
            logger.error("Volume cache fetch failed", error=str(e))
            # Return empty dict on error - NO fake data
            return {}

    async def upsert_batch(self, volume_data: Dict[str, float]) -> int:
        """
        Bulk upsert volume averages from REAL calculated data.

        CRITICAL: Only accepts real volume data from Polygon API.
        Validates all inputs before inserting.

        Args:
            volume_data: Dict of {symbol: avg_volume_20d} from real API data

        Returns:
            Number of records successfully updated
        """
        if not volume_data:
            return 0

        try:
            # Validate: reject zero or negative volumes (indicates fake data)
            valid_data = {
                symbol: avg_vol
                for symbol, avg_vol in volume_data.items()
                if avg_vol > 0
            }

            if len(valid_data) < len(volume_data):
                rejected = len(volume_data) - len(valid_data)
                logger.warning(
                    "Rejected invalid volume data",
                    rejected_count=rejected,
                    reason="zero_or_negative_volumes"
                )

            if not valid_data:
                return 0

            # Prepare batch insert values
            values = [
                {
                    'symbol': symbol,
                    'avg_volume_20d': int(avg_vol),
                    'last_updated': datetime.utcnow()
                }
                for symbol, avg_vol in valid_data.items()
            ]

            # Bulk upsert with conflict resolution
            query = text("""
                INSERT INTO volume_averages (symbol, avg_volume_20d, last_updated)
                VALUES (:symbol, :avg_volume_20d, :last_updated)
                ON CONFLICT (symbol)
                DO UPDATE SET
                    avg_volume_20d = EXCLUDED.avg_volume_20d,
                    last_updated = EXCLUDED.last_updated
            """)

            await self.session.execute(query, values)
            await self.session.commit()

            logger.info(
                "Volume cache updated",
                upserted=len(values),
                rejected=len(volume_data) - len(valid_data)
            )

            return len(values)

        except Exception as e:
            logger.error("Volume cache upsert failed", error=str(e))
            await self.session.rollback()
            return 0

    async def get_stale_symbols(self, max_age_hours: int = 24) -> List[str]:
        """
        Get symbols with stale cache data (need refresh).

        Args:
            max_age_hours: Maximum age before considering stale

        Returns:
            List of symbols needing refresh
        """
        try:
            query = text("""
                SELECT symbol
                FROM volume_averages
                WHERE last_updated < NOW() - INTERVAL ':hours hours'
                ORDER BY last_updated ASC
                LIMIT 1000
            """)

            result = await self.session.execute(query, {"hours": max_age_hours})
            stale_symbols = [row[0] for row in result.fetchall()]

            return stale_symbols

        except Exception as e:
            logger.error("Failed to get stale symbols", error=str(e))
            return []
