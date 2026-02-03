#!/usr/bin/env python3
"""
Quick setup verification script for SqueezeSeeker Dashboard
"""

import json
import os
import sys

def check_credentials():
    """Check if Alpaca credentials exist and are valid"""
    creds_path = os.path.expanduser('~/.openclaw/secrets/alpaca.json')
    
    print("🔍 Checking Alpaca credentials...")
    
    if not os.path.exists(creds_path):
        print("❌ Alpaca credentials not found at:", creds_path)
        print("   Please create the file with your API credentials.")
        return False
    
    try:
        with open(creds_path, 'r') as f:
            creds = json.load(f)
        
        required_keys = ['apiKey', 'apiSecret', 'baseUrl']
        missing_keys = [key for key in required_keys if key not in creds]
        
        if missing_keys:
            print("❌ Missing required keys:", ', '.join(missing_keys))
            return False
        
        print("✅ Credentials file found and valid")
        print(f"   Base URL: {creds['baseUrl']}")
        print(f"   Paper Trading: {creds.get('paperTrading', 'Not specified')}")
        return True
        
    except json.JSONDecodeError:
        print("❌ Invalid JSON in credentials file")
        return False
    except Exception as e:
        print(f"❌ Error reading credentials: {e}")
        return False

def check_dependencies():
    """Check if required packages are installed"""
    print("\n🔍 Checking Python dependencies...")
    
    required_packages = {
        'flask': 'Flask',
        'requests': 'requests',
        'yfinance': 'yfinance'
    }
    
    missing = []
    
    for package, name in required_packages.items():
        try:
            __import__(package)
            print(f"✅ {name} installed")
        except ImportError:
            print(f"❌ {name} not installed")
            missing.append(name)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("   Run: pip install -r requirements.txt")
        return False
    
    return True

def check_files():
    """Check if all required files exist"""
    print("\n🔍 Checking dashboard files...")
    
    required_files = [
        'app.py',
        'static/index.html',
        'static/css/style.css',
        'static/js/app.js',
        'requirements.txt',
        'README.md'
    ]
    
    all_exist = True
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} not found")
            all_exist = False
    
    return all_exist

def main():
    print("=" * 60)
    print("SqueezeSeeker Trading Dashboard - Setup Verification")
    print("=" * 60)
    print()
    
    checks = [
        check_credentials(),
        check_dependencies(),
        check_files()
    ]
    
    print("\n" + "=" * 60)
    
    if all(checks):
        print("✅ All checks passed! You're ready to go.")
        print("\nTo start the dashboard, run:")
        print("   python app.py")
        print("\nOr use the convenience script:")
        print("   ./start.sh")
        print("\nThen open: http://localhost:5000")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
