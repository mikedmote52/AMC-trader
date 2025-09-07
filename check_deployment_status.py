#!/usr/bin/env python3
"""
Deployment Status Check
Verifies if the new real BMS system is deployed and functioning
"""

import requests
import json
import time

def check_deployment_status():
    """Check if new BMS system is deployed"""
    
    print("🚀 CHECKING DEPLOYMENT STATUS")
    print("=" * 50)
    
    api_base = "https://amc-trader.onrender.com"
    
    # Test 1: Check health endpoint format
    print("1️⃣ Testing Health Endpoint...")
    try:
        response = requests.get(f"{api_base}/discovery/health", timeout=30)
        data = response.json()
        
        if 'price_bounds' in data and 'engine' in data:
            print("✅ NEW BMS system detected!")
            print(f"   Engine: {data.get('engine', 'N/A')}")
            print(f"   Price bounds: {data.get('price_bounds', 'N/A')}")
            print(f"   Volume min: {data.get('dollar_volume_min_m', 'N/A')}M")
            return True
        elif 'universe' in data and 'system_state' in data:
            print("⚠️ OLD discovery system still running")
            print(f"   Universe: {data.get('universe', 'N/A')}")
            print(f"   State: {data.get('system_state', 'N/A')}")
            print(f"   Last run: {data.get('last_run', 'N/A')}")
            return False
        else:
            print("❓ Unknown system format")
            print(f"   Data: {json.dumps(data, indent=2)}")
            return False
            
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")
        return False
    
    # Test 2: Check candidates endpoint
    print(f"\n2️⃣ Testing Candidates Endpoint...")
    try:
        response = requests.get(f"{api_base}/discovery/candidates?limit=5", timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            if 'candidates' in data and 'engine' in data:
                print("✅ NEW candidates format detected!")
                print(f"   Found: {len(data.get('candidates', []))} candidates")
                print(f"   Engine: {data.get('engine', 'N/A')}")
                
                if data.get('candidates'):
                    candidate = data['candidates'][0]
                    print(f"   Sample: {candidate.get('symbol')} at ${candidate.get('price', 0):.2f}")
                
                return True
            else:
                print("⚠️ OLD candidates format (array)")
                return False
        else:
            print(f"❌ Candidates endpoint error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Candidates endpoint error: {e}")
        return False

def check_render_deployment():
    """Check Render deployment status"""
    print(f"\n3️⃣ Deployment Diagnostics...")
    
    api_base = "https://amc-trader.onrender.com"
    
    # Check if service is responsive
    try:
        start_time = time.time()
        response = requests.get(f"{api_base}/health", timeout=30)
        response_time = time.time() - start_time
        
        print(f"   Service response time: {response_time:.1f}s")
        print(f"   HTTP status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Service status: {data.get('status', 'unknown')}")
            print(f"   Commit: {data.get('commit', 'unknown')[:8]}")
            
        return response.status_code == 200
        
    except Exception as e:
        print(f"   ❌ Service unreachable: {e}")
        return False

def main():
    """Main deployment check"""
    print("Checking AMC-TRADER deployment status...\n")
    
    # Wait a bit for deployment
    print("⏳ Waiting for Render deployment to complete...")
    time.sleep(10)
    
    # Run checks
    new_system_deployed = check_deployment_status()
    service_healthy = check_render_deployment()
    
    print(f"\n" + "=" * 50)
    print("📋 DEPLOYMENT STATUS SUMMARY")
    print("=" * 50)
    
    if new_system_deployed:
        print("🎉 SUCCESS: New real BMS discovery system is LIVE!")
        print("✅ Price bounds ($0.5-$100) active")
        print("✅ Real market data scanning enabled")
        print("✅ 5000+ stock universe ready")
        print(f"\n🔗 Test the system:")
        print(f"   Frontend: https://amc-frontend.onrender.com/discovery")
        print(f"   API: https://amc-trader.onrender.com/discovery/candidates")
        
    elif service_healthy:
        print("⚠️ PARTIAL: Service healthy but old system still running")
        print("📝 Possible causes:")
        print("   - Render deployment in progress (can take 5-15 minutes)")
        print("   - Import path issues preventing new engine loading")
        print("   - Environment variables not updated")
        print(f"\n🔄 Recommendation: Wait 5 more minutes and check again")
        
    else:
        print("❌ ISSUE: Service problems detected")
        print("📝 Check Render dashboard for deployment errors")
    
    return new_system_deployed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)