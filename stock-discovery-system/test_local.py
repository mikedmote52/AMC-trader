#!/usr/bin/env python3
"""
Local test script to verify the system works with real APIs.
Run this before deploying to ensure everything connects properly.
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend" / "src"))


async def test_real_apis():
    """Test real API connections."""
    print("\n" + "=" * 50)
    print("TESTING REAL API CONNECTIONS")
    print("=" * 50)
    
    # Import after env is loaded
    from deps import HTTPClientWithRetry
    from services.market import MarketService
    
    # Create HTTP client
    http_client = HTTPClientWithRetry(timeout=10.0, retries=2)
    
    try:
        # Test market service with real Polygon data
        print("\n1. Testing Polygon Market Data...")
        market = MarketService(http_client)
        
        # Get quotes for a few symbols
        test_symbols = ["AAPL", "MSFT", "GOOGL"]
        quotes_result = await market.get_quotes(test_symbols)
        
        print(f"   Fetched quotes for {len(quotes_result['quotes'])} symbols:")
        for symbol, quote in quotes_result['quotes'].items():
            print(f"   - {symbol}: ${quote['price']}")
        
        if quotes_result['errors']:
            print(f"   Errors: {quotes_result['errors']}")
        
        # Test momentum calculation
        print("\n2. Testing momentum calculation...")
        momentum = await market.calculate_momentum("AAPL", days=5)
        print(f"   AAPL 5-day momentum: {momentum}%")
        
        # Test volatility calculation
        print("\n3. Testing volatility calculation...")
        volatility = await market.calculate_volatility("AAPL", days=20)
        print(f"   AAPL 20-day volatility: {volatility}%")
        
        # Test snapshot
        print("\n4. Testing market snapshot...")
        snapshot = await market.get_snapshot("AAPL")
        print(f"   AAPL snapshot:")
        print(f"   - Price: ${snapshot['price']}")
        print(f"   - Volume: {snapshot['volume']:,}")
        print(f"   - Change: {snapshot['change_percent']:.2f}%")
        
        print("\n✅ All market data tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await http_client.close()
    
    return True


async def test_health_endpoint():
    """Test the health endpoint locally."""
    print("\n" + "=" * 50)
    print("TESTING HEALTH ENDPOINT")
    print("=" * 50)
    
    import httpx
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health")
            data = response.json()
            
            print(f"Health check status: {data['status']}")
            print("\nComponent statuses:")
            for component, check in data['checks'].items():
                status_icon = "✅" if check['status'] == 'healthy' else "❌"
                print(f"  {status_icon} {component}: {check['message']}")
            
            if response.status_code == 200:
                print("\n✅ Health endpoint test passed!")
                return True
            else:
                print(f"\n⚠️ Health endpoint returned {response.status_code}")
                return False
                
    except httpx.ConnectError:
        print("❌ Could not connect to server. Is it running?")
        print("   Start with: cd backend && uvicorn src.app:app --reload")
        return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("Starting local tests...")
    
    # Test real APIs directly
    api_test = await test_real_apis()
    
    # Check if server is running
    print("\n" + "=" * 50)
    print("Note: To test the health endpoint, start the server first:")
    print("  cd backend && uvicorn src.app:app --reload")
    print("Then run this test again.")
    print("=" * 50)
    
    # Try health endpoint (will fail if server not running)
    # await test_health_endpoint()
    
    if api_test:
        print("\n🚀 Direct API tests passed! System can connect to real data sources.")
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())