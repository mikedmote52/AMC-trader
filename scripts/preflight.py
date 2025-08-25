#!/usr/bin/env python3
"""
Preflight check script - exits non-zero on any failure
Validates all system dependencies and configurations before starting the API
"""

import sys
import os
import subprocess
from typing import Dict, Tuple
import structlog

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

logger = structlog.get_logger()

def check_environment_variables() -> Tuple[bool, str]:
    """Check if all required environment variables are set"""
    required_vars = [
        "DATABASE_URL",
        "REDIS_URL", 
        "ALPACA_API_KEY",
        "ALPACA_SECRET_KEY",
        "ALPACA_BASE_URL",
        "POLYGON_API_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        return False, f"Missing environment variables: {', '.join(missing_vars)}"
    
    return True, "All environment variables present"

def check_python_dependencies() -> Tuple[bool, str]:
    """Check if all Python dependencies are installed"""
    try:
        requirements_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'requirements.txt')
        
        if not os.path.exists(requirements_path):
            return False, "requirements.txt not found"
        
        # Try importing critical modules
        critical_imports = [
            'fastapi',
            'sqlalchemy', 
            'redis',
            'httpx',
            'alpaca_trade_api',
            'structlog'
        ]
        
        for module in critical_imports:
            try:
                __import__(module)
            except ImportError as e:
                return False, f"Failed to import {module}: {e}"
        
        return True, "All Python dependencies available"
        
    except Exception as e:
        return False, f"Dependency check failed: {e}"

def check_database_connection() -> Tuple[bool, str]:
    """Check database connectivity"""
    try:
        from app.deps import check_database_health
        
        if check_database_health():
            return True, "Database connection successful"
        else:
            return False, "Database connection failed"
            
    except Exception as e:
        return False, f"Database check error: {e}"

def check_redis_connection() -> Tuple[bool, str]:
    """Check Redis connectivity"""
    try:
        from app.deps import check_redis_health
        
        if check_redis_health():
            return True, "Redis connection successful"
        else:
            return False, "Redis connection failed"
            
    except Exception as e:
        return False, f"Redis check error: {e}"

def check_external_apis() -> Tuple[bool, str]:
    """Check external API connectivity"""
    try:
        from app.deps import check_polygon_health, check_alpaca_health
        
        polygon_ok = check_polygon_health()
        alpaca_ok = check_alpaca_health()
        
        if polygon_ok and alpaca_ok:
            return True, "All external APIs accessible"
        elif not polygon_ok and not alpaca_ok:
            return False, "Both Polygon and Alpaca APIs failed"
        elif not polygon_ok:
            return False, "Polygon API connection failed"
        else:
            return False, "Alpaca API connection failed"
            
    except Exception as e:
        return False, f"External API check error: {e}"

def run_preflight_checks() -> int:
    """Run all preflight checks and return exit code"""
    checks = [
        ("Environment Variables", check_environment_variables),
        ("Python Dependencies", check_python_dependencies),
        ("Database Connection", check_database_connection),
        ("Redis Connection", check_redis_connection),
        ("External APIs", check_external_apis)
    ]
    
    all_passed = True
    results = {}
    
    print("🚀 Running AMC Trading API Preflight Checks")
    print("=" * 50)
    
    for check_name, check_func in checks:
        try:
            success, message = check_func()
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {check_name}: {message}")
            
            results[check_name] = {"success": success, "message": message}
            
            if not success:
                all_passed = False
                
        except Exception as e:
            print(f"❌ FAIL {check_name}: Unexpected error - {e}")
            results[check_name] = {"success": False, "message": str(e)}
            all_passed = False
    
    print("=" * 50)
    
    if all_passed:
        print("🎉 All preflight checks passed! API ready to start.")
        logger.info("Preflight checks passed", results=results)
        return 0
    else:
        print("💥 Preflight checks failed! Fix issues before starting API.")
        logger.error("Preflight checks failed", results=results)
        return 1

if __name__ == "__main__":
    # Configure basic logging for preflight
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.JSONRenderer()
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    exit_code = run_preflight_checks()
    sys.exit(exit_code)