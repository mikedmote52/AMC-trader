"""
Background job to refresh 20-day volume averages.

Schedule: Run daily at 5 PM ET (after market close)
Duration: ~30 minutes for full universe
API Calls: ~8,000 (batched with rate limiting)

CRITICAL: This job uses ONLY real Polygon API data.
NO mock data, NO fallbacks, NO fake volumes.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
import structlog
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.market import MarketService
from app.repositories.volume_cache import VolumeCacheRepository
from app.deps import get_db


logger = structlog.get_logger()


async def calculate_20day_average(
    market_service: MarketService,
    symbol: str
) -> float:
    """
    Calculate 20-day average volume from real Polygon data.

    CRITICAL: Returns 0.0 if data unavailable (NO fake fallback).

    Args:
        market_service: MarketService instance
        symbol: Stock symbol

    Returns:
        20-day average volume (or 0.0 if unavailable)
    """
    try:
        # Fetch 20-day volume history from Polygon
        bars_data = await market_service.get_volume_data(symbol, days=20)

        if not bars_data or not bars_data.get('results'):
            return 0.0

        # Extract volumes from bars
        volumes = [bar.get('v', 0) for bar in bars_data['results']]

        # Filter out zero volumes (missing data)
        valid_volumes = [v for v in volumes if v > 0]

        if not valid_volumes:
            return 0.0

        # Calculate average
        avg_volume = sum(valid_volumes) / len(valid_volumes)

        return float(avg_volume)

    except Exception as e:
        logger.debug(f"Failed to calculate 20-day avg for {symbol}: {e}")
        return 0.0


async def refresh_volume_cache(
    batch_size: int = 100,
    rate_limit_delay: float = 1.0,
    max_symbols: int = None
):
    """
    Refresh 20-day volume averages for active symbols.

    Process:
    1. Get active symbols from bulk snapshot
    2. Fetch 20-day history for each symbol (batched)
    3. Calculate averages
    4. Bulk upsert to PostgreSQL

    CRITICAL: Uses ONLY real Polygon data.
    Skips symbols with missing data (NO fake volumes).

    Args:
        batch_size: Number of symbols per batch
        rate_limit_delay: Delay between batches (seconds)
        max_symbols: Limit for testing (None = all symbols)
    """
    logger.info("🔄 Starting volume cache refresh job...")
    start_time = datetime.utcnow()

    try:
        market_service = MarketService()

        # Step 1: Get active symbols from bulk snapshot
        logger.info("Fetching active symbols from bulk snapshot...")
        snapshots = await market_service.get_bulk_snapshot_optimized()

        if not snapshots:
            logger.error("No snapshots available - cannot refresh cache")
            return

        active_symbols = list(snapshots.keys())

        if max_symbols:
            active_symbols = active_symbols[:max_symbols]

        logger.info(f"Refreshing {len(active_symbols):,} active symbols...")

        # Step 2: Process in batches
        volume_data = {}
        processed = 0
        skipped = 0
        errors = 0

        for i in range(0, len(active_symbols), batch_size):
            batch = active_symbols[i:i+batch_size]
            batch_start = datetime.utcnow()

            # Process batch
            for symbol in batch:
                try:
                    avg_volume = await calculate_20day_average(market_service, symbol)

                    if avg_volume > 0:
                        volume_data[symbol] = avg_volume
                        processed += 1
                    else:
                        skipped += 1

                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
                    errors += 1

            # Rate limiting
            await asyncio.sleep(rate_limit_delay)

            # Progress logging
            batch_time = (datetime.utcnow() - batch_start).total_seconds()
            logger.info(
                f"Batch {i//batch_size + 1}: "
                f"{processed:,} processed, {skipped:,} skipped, {errors} errors "
                f"({batch_time:.1f}s)"
            )

        # Step 3: Bulk upsert to database
        if volume_data:
            logger.info(f"Upserting {len(volume_data):,} volume averages to database...")

            async with get_db() as session:
                repo = VolumeCacheRepository(session)
                updated_count = await repo.upsert_batch(volume_data)

            logger.info(f"✅ Database updated: {updated_count:,} records")
        else:
            logger.warning("No volume data to upsert - all symbols skipped")

        # Final stats
        elapsed = (datetime.utcnow() - start_time).total_seconds()

        logger.info(
            "✅ Volume cache refresh complete",
            total_symbols=len(active_symbols),
            processed=processed,
            skipped=skipped,
            errors=errors,
            duration=f"{elapsed:.1f}s",
            avg_time_per_symbol=f"{elapsed/len(active_symbols):.3f}s"
        )

    except Exception as e:
        logger.error("Volume cache refresh failed", error=str(e), exc_info=True)
        raise


async def refresh_stale_symbols_only(max_age_hours: int = 24):
    """
    Refresh only symbols with stale cache data (incremental update).

    More efficient than full refresh - use for hourly updates.

    Args:
        max_age_hours: Refresh symbols older than this
    """
    logger.info(f"🔄 Refreshing stale symbols (age > {max_age_hours}h)...")

    try:
        market_service = MarketService()

        # Get stale symbols from database
        async with get_db() as session:
            repo = VolumeCacheRepository(session)
            stale_symbols = await repo.get_stale_symbols(max_age_hours)

        if not stale_symbols:
            logger.info("No stale symbols found - cache is fresh")
            return

        logger.info(f"Found {len(stale_symbols):,} stale symbols")

        # Refresh stale symbols only
        volume_data = {}

        for symbol in stale_symbols:
            avg_volume = await calculate_20day_average(market_service, symbol)
            if avg_volume > 0:
                volume_data[symbol] = avg_volume

        # Update database
        if volume_data:
            async with get_db() as session:
                repo = VolumeCacheRepository(session)
                updated = await repo.upsert_batch(volume_data)

            logger.info(f"✅ Refreshed {updated:,} stale symbols")

    except Exception as e:
        logger.error("Stale symbol refresh failed", error=str(e), exc_info=True)


# CLI entry point for manual execution
if __name__ == "__main__":
    import sys

    # Parse arguments
    if len(sys.argv) > 1 and sys.argv[1] == "stale":
        # Incremental refresh
        asyncio.run(refresh_stale_symbols_only())
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test with limited symbols
        asyncio.run(refresh_volume_cache(max_symbols=100))
    else:
        # Full refresh
        asyncio.run(refresh_volume_cache())
