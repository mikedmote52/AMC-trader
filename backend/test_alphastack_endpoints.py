#!/usr/bin/env python3
"""
Test script for AlphaStack 4.1 API endpoints.
Run this after starting the backend to verify endpoints work.
"""

import asyncio
import httpx
import json
from datetime import datetime

API_BASE = "http://localhost:8000"  # Change if running on different port

async def test_endpoints():
    """Test all AlphaStack 4.1 endpoints."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("🔍 Testing AlphaStack 4.1 API Endpoints")
        print(f"API Base: {API_BASE}")
        print("-" * 50)

        # Test 1: /v1/telemetry
        print("1. Testing /v1/telemetry...")
        try:
            response = await client.get(f"{API_BASE}/v1/telemetry")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Schema Version: {data.get('schema_version')}")
                print(f"   System Ready: {data.get('system_health', {}).get('system_ready')}")
                print(f"   Stale Data: {data.get('production_health', {}).get('stale_data_detected')}")
                print("   ✅ Success")
            else:
                print(f"   ❌ Failed: {response.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        print()

        # Test 2: /v1/candidates/top
        print("2. Testing /v1/candidates/top...")
        try:
            response = await client.get(f"{API_BASE}/v1/candidates/top?limit=5")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Schema Version: {data.get('schema_version')}")
                print(f"   Candidates Count: {len(data.get('items', []))}")
                if data.get('items'):
                    print(f"   First Candidate: {data['items'][0].get('symbol')} (Score: {data['items'][0].get('total_score')})")
                print("   ✅ Success")
            else:
                print(f"   ❌ Failed: {response.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        print()

        # Test 3: /v1/explosive
        print("3. Testing /v1/explosive...")
        try:
            response = await client.get(f"{API_BASE}/v1/explosive")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Schema Version: {data.get('schema_version')}")
                print(f"   Explosive Count: {len(data.get('explosive_top', []))}")
                if data.get('explosive_top'):
                    print(f"   First Explosive: {data['explosive_top'][0].get('symbol')} (Score: {data['explosive_top'][0].get('total_score')})")
                print("   ✅ Success")
            else:
                print(f"   ❌ Failed: {response.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        print()

        # Test 4: WebSocket connection (basic)
        print("4. Testing WebSocket connection...")
        try:
            import socketio

            sio = socketio.AsyncClient()

            @sio.event
            async def connect():
                print("   WebSocket connected")

            @sio.event
            async def connected(data):
                print(f"   Received connection confirmation: {data}")

            @sio.event
            async def disconnect():
                print("   WebSocket disconnected")

            # Connect to WebSocket
            await sio.connect(f"{API_BASE}/v1/stream", transports=['websocket'])
            await asyncio.sleep(2)  # Wait for connection confirmation
            await sio.disconnect()
            print("   ✅ WebSocket Success")

        except ImportError:
            print("   ⚠️ Skipped: python-socketio not installed")
        except Exception as e:
            print(f"   ❌ WebSocket Error: {e}")

        print()
        print("✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(test_endpoints())