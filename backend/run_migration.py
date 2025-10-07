#!/usr/bin/env python3
"""
Run PostgreSQL migration using asyncpg (matches backend setup)
"""
import asyncio
import asyncpg
import sys
import os

# Render database connection
DATABASE_URL = "postgresql://amc_user:zvbwAwfF1BW5NymSi0bpyV5YxHMHmDtb@dpg-d2me21d7diees73cg8ehg-a.oregon-postgres.render.com:5432/amc_trader"

async def run_migration():
    try:
        print("🔄 Connecting to Render PostgreSQL...")

        # Connect using asyncpg with SSL required
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        conn = await asyncpg.connect(DATABASE_URL, ssl=ssl_context)

        print("✅ Connected! Running migration...")

        # Run migration SQL directly (no file read needed)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS volume_averages (
                symbol VARCHAR(10) PRIMARY KEY,
                avg_volume_20d BIGINT NOT NULL,
                avg_volume_30d BIGINT,
                last_updated TIMESTAMP NOT NULL DEFAULT NOW(),
                created_at TIMESTAMP DEFAULT NOW(),
                CONSTRAINT positive_volume CHECK (avg_volume_20d > 0)
            );
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_volume_avg_updated ON volume_averages(last_updated);
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_volume_avg_symbol ON volume_averages(symbol);
        """)

        print("✅ Migration complete!")

        # Verify table created
        count = await conn.fetchval("SELECT COUNT(*) FROM volume_averages;")
        print(f"✅ Table 'volume_averages' exists with {count} rows")

        await conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_migration())
