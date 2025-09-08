#!/usr/bin/env python3
"""
Test worker imports for debugging
"""

import sys
import os

# Add backend to path  
sys.path.insert(0, os.path.join(os.getcwd(), 'backend', 'src'))

try:
    print("Testing imports...")
    
    print("1. Testing worker module...")
    import backend.src.worker as worker_module
    print(f"   ✅ Worker module: {worker_module.__file__}")
    
    print("2. Testing run_discovery function...")
    from backend.src.worker import run_discovery
    print(f"   ✅ run_discovery function: {run_discovery}")
    
    print("3. Testing BMS engine...")
    from backend.src.services.bms_engine_real import RealBMSEngine
    print(f"   ✅ BMS engine: {RealBMSEngine}")
    
    print("\n✅ All imports successful!")
    
except Exception as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()