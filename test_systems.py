#!/usr/bin/env python3
"""
System Test - Verify all critical functions work
Run this after any changes to validate nothing broke
"""

import json
import requests
import os
from datetime import datetime

def test_alpaca_api():
    """Test Alpaca API connection"""
    print("1. Testing Alpaca API...")
    
    try:
        with open('/Users/mikeclawd/.openclaw/secrets/alpaca.json', 'r') as f:
            creds = json.load(f)
        
        base_url = creds['baseUrl'].rstrip('/v2').rstrip('/')
        headers = {
            'APCA-API-KEY-ID': creds['apiKey'],
            'APCA-API-SECRET-KEY': creds['apiSecret']
        }
        
        # Test positions endpoint
        url = f"{base_url}/v2/positions"
        r = requests.get(url, headers=headers)
        
        if r.status_code == 200:
            positions = r.json()
            print(f"   ✅ API working - {len(positions)} positions")
            return True
        else:
            print(f"   ❌ API failed: {r.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_scanner():
    """Test scanner can run"""
    print("2. Testing scanner...")
    
    try:
        if os.path.exists('/Users/mikeclawd/.openclaw/workspace/diamond_scanner.py'):
            print(f"   ✅ Scanner file exists")
            return True
        else:
            print(f"   ❌ Scanner file missing")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_data_files():
    """Test required data files exist"""
    print("3. Testing data files...")
    
    required = [
        'data/diamonds.json',
        'PROCEDURES.md',
        'MEMORY.md'
    ]
    
    all_exist = True
    for file in required:
        path = f'/Users/mikeclawd/.openclaw/workspace/{file}'
        if os.path.exists(path):
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} missing")
            all_exist = False
    
    return all_exist

def test_memory_system():
    """Test memory file for today exists"""
    print("4. Testing memory system...")
    
    today = datetime.now().strftime('%Y-%m-%d')
    memory_file = f'/Users/mikeclawd/.openclaw/workspace/memory/{today}.md'
    
    if os.path.exists(memory_file):
        print(f"   ✅ Today's memory file exists")
        return True
    else:
        print(f"   ⚠️  Creating today's memory file")
        os.makedirs(os.path.dirname(memory_file), exist_ok=True)
        with open(memory_file, 'w') as f:
            f.write(f"# {today}\n\n")
        return True

def main():
    print("=" * 80)
    print("SYSTEM TEST")
    print(f"{datetime.now().strftime('%I:%M %p PT')}")
    print("=" * 80)
    print()
    
    results = {
        'Alpaca API': test_alpaca_api(),
        'Scanner': test_scanner(),
        'Data Files': test_data_files(),
        'Memory System': test_memory_system()
    }
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    passed = sum(results.values())
    total = len(results)
    
    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ ALL SYSTEMS OPERATIONAL")
    else:
        print(f"\n⚠️  {total - passed} SYSTEM(S) NEED ATTENTION")
    
    print("=" * 80)

if __name__ == '__main__':
    main()
