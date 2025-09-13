#!/usr/bin/env python3
"""
Preflight validation script.
Runs on startup and CI to verify all dependencies are accessible.
Exits with non-zero code on any failure.
"""
import sys
import os
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))

import httpx
import redis.asyncio as redis
from sqlalchemy import create_engine
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


class PreflightChecker:
    """Performs preflight checks on all external dependencies."""
    
    def __init__(self):
        self.checks_passed = []
        self.checks_failed = []
    
    def _check_env_var(self, name: str) -> bool:
        """Check if environment variable is set and not a placeholder."""
        value = os.getenv(name)
        if not value:
            print(f"❌ Environment variable {name} is not set")
            return False
        if value.startswith("your_") or value == "":
            print(f"❌ Environment variable {name} has placeholder value: {value[:20]}...")
            return False
        print(f"✅ Environment variable {name} is set")
        return True
    
    async def check_environment(self) -> bool:
        """Check all required environment variables."""
        print("\n=== Checking Environment Variables ===")
        required_vars = [
            "POLYGON_API_KEY",
            "ALPACA_API_KEY",
            "ALPACA_API_SECRET",
            "DATABASE_URL",
            "REDIS_URL"
        ]
        
        all_set = True
        for var in required_vars:
            if not self._check_env_var(var):
                all_set = False
                self.checks_failed.append(f"env:{var}")
            else:
                self.checks_passed.append(f"env:{var}")
        
        return all_set
    
    async def check_database(self) -> bool:
        """Check database connectivity."""
        print("\n=== Checking Database Connection ===")
        try:
            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                print("❌ DATABASE_URL not set")
                self.checks_failed.append("database")
                return False
            
            engine = create_engine(db_url)
            with engine.connect() as conn:
                result = conn.execute("SELECT 1")
                print("✅ Database connection successful")
                self.checks_passed.append("database")
                return True
                
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            self.checks_failed.append("database")
            return False
    
    async def check_redis(self) -> bool:
        """Check Redis connectivity."""
        print("\n=== Checking Redis Connection ===")
        try:
            redis_url = os.getenv("REDIS_URL")
            if not redis_url:
                print("❌ REDIS_URL not set")
                self.checks_failed.append("redis")
                return False
            
            client = redis.from_url(redis_url)
            await client.ping()
            await client.close()
            print("✅ Redis connection successful")
            self.checks_passed.append("redis")
            return True
            
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            self.checks_failed.append("redis")
            return False
    
    async def check_polygon(self) -> bool:
        """Check Polygon API access."""
        print("\n=== Checking Polygon API ===")
        try:
            api_key = os.getenv("POLYGON_API_KEY")
            if not api_key or api_key.startswith("your_"):
                print("❌ POLYGON_API_KEY not properly set")
                self.checks_failed.append("polygon")
                return False
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try to get last trade for AAPL
                url = "https://api.polygon.io/v2/last/trade/AAPL"
                response = await client.get(url, params={"apiKey": api_key})
                data = response.json()
                
                if data.get("status") == "OK":
                    price = data.get("results", {}).get("p")
                    print(f"✅ Polygon API accessible (AAPL last trade: ${price})")
                    self.checks_passed.append("polygon")
                    return True
                else:
                    print(f"❌ Polygon API error: {data.get('message', 'Unknown error')}")
                    self.checks_failed.append("polygon")
                    return False
                    
        except Exception as e:
            print(f"❌ Polygon API check failed: {e}")
            self.checks_failed.append("polygon")
            return False
    
    async def check_alpaca(self) -> bool:
        """Check Alpaca API access."""
        print("\n=== Checking Alpaca API ===")
        try:
            api_key = os.getenv("ALPACA_API_KEY")
            api_secret = os.getenv("ALPACA_API_SECRET")
            base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
            
            if not api_key or not api_secret:
                print("❌ Alpaca API credentials not set")
                self.checks_failed.append("alpaca")
                return False
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Check account status
                url = f"{base_url}/v2/account"
                headers = {
                    "APCA-API-KEY-ID": api_key,
                    "APCA-API-SECRET-KEY": api_secret
                }
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Alpaca API accessible (Account status: {data.get('status')})")
                    print(f"   Buying power: ${data.get('buying_power')}")
                    self.checks_passed.append("alpaca")
                    return True
                else:
                    print(f"❌ Alpaca API error: HTTP {response.status_code}")
                    self.checks_failed.append("alpaca")
                    return False
                    
        except Exception as e:
            print(f"❌ Alpaca API check failed: {e}")
            self.checks_failed.append("alpaca")
            return False
    
    async def run_all_checks(self) -> bool:
        """Run all preflight checks."""
        print("=" * 50)
        print("PREFLIGHT CHECKS - Stock Discovery System")
        print("=" * 50)
        
        # Run checks
        env_ok = await self.check_environment()
        
        # Only check external services if env vars are set
        if env_ok:
            # Run checks in parallel where possible
            results = await asyncio.gather(
                self.check_database(),
                self.check_redis(),
                self.check_polygon(),
                self.check_alpaca(),
                return_exceptions=True
            )
            
            # Check for exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"Check failed with exception: {result}")
        
        # Summary
        print("\n" + "=" * 50)
        print("PREFLIGHT SUMMARY")
        print("=" * 50)
        print(f"✅ Passed: {len(self.checks_passed)} checks")
        if self.checks_passed:
            print(f"   {', '.join(self.checks_passed)}")
        
        if self.checks_failed:
            print(f"❌ Failed: {len(self.checks_failed)} checks")
            print(f"   {', '.join(self.checks_failed)}")
            print("\nPreflight checks FAILED. Please fix the above issues.")
            return False
        else:
            print("\n🚀 All preflight checks PASSED! System ready to start.")
            return True


async def main():
    """Main entry point."""
    checker = PreflightChecker()
    success = await checker.run_all_checks()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())