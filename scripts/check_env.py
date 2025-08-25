#!/usr/bin/env python3
"""
Environment variable validation script for AMC-trader services.
Asserts required environment variables are set for API and Cron services.
"""

import os
import sys
from typing import List, Dict, Optional


class EnvironmentValidator:
    """Validates environment variables for different service types."""
    
    # Required environment variables for each service
    REQUIRED_ENV_VARS = {
        "api": [
            "ALPACA_API_KEY",
            "ALPACA_SECRET_KEY", 
            "ALPACA_BASE_URL",
            "CLAUDE_API_KEY",
            "POLYGON_API_KEY",
            "NODE_ENV",
            "PORT"
        ],
        "cron": [
            "ALPACA_API_KEY",
            "ALPACA_SECRET_KEY",
            "ALPACA_BASE_URL", 
            "CLAUDE_API_KEY",
            "POLYGON_API_KEY",
            "PYTHONPATH"
        ]
    }
    
    def __init__(self):
        self.missing_vars: Dict[str, List[str]] = {}
        self.warnings: List[str] = []
    
    def validate_service(self, service_type: str) -> bool:
        """
        Validate environment variables for a specific service type.
        
        Args:
            service_type: Either 'api' or 'cron'
            
        Returns:
            bool: True if all required vars are set, False otherwise
        """
        if service_type not in self.REQUIRED_ENV_VARS:
            raise ValueError(f"Unknown service type: {service_type}")
        
        required_vars = self.REQUIRED_ENV_VARS[service_type]
        missing = []
        
        for var in required_vars:
            value = os.getenv(var)
            if not value:
                missing.append(var)
            elif var in ["ALPACA_API_KEY", "ALPACA_SECRET_KEY", "CLAUDE_API_KEY", "POLYGON_API_KEY"]:
                # Check for placeholder values
                if value.startswith("your_") or value.startswith("pk_") or len(value) < 10:
                    self.warnings.append(f"⚠️  {var} appears to be a placeholder value")
        
        if missing:
            self.missing_vars[service_type] = missing
            return False
        
        return True
    
    def validate_all(self) -> bool:
        """Validate all service types."""
        all_valid = True
        
        for service_type in self.REQUIRED_ENV_VARS.keys():
            if not self.validate_service(service_type):
                all_valid = False
        
        return all_valid
    
    def print_results(self):
        """Print validation results."""
        if not self.missing_vars and not self.warnings:
            print("✅ All environment variables are properly configured!")
            return
        
        if self.missing_vars:
            print("❌ Missing required environment variables:")
            for service, vars_list in self.missing_vars.items():
                print(f"\n{service.upper()} service:")
                for var in vars_list:
                    print(f"  - {var}")
        
        if self.warnings:
            print("\n⚠️  Warnings:")
            for warning in self.warnings:
                print(f"  {warning}")
        
        if self.missing_vars:
            print("\n📖 See README.md for complete environment variable setup instructions.")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate AMC-trader environment variables")
    parser.add_argument(
        "--service", 
        choices=["api", "cron", "all"], 
        default="all",
        help="Service type to validate (default: all)"
    )
    parser.add_argument(
        "--strict",
        action="store_true", 
        help="Exit with non-zero code on warnings"
    )
    
    args = parser.parse_args()
    
    validator = EnvironmentValidator()
    
    if args.service == "all":
        valid = validator.validate_all()
    else:
        valid = validator.validate_service(args.service)
    
    validator.print_results()
    
    # Exit with appropriate code
    if not valid:
        sys.exit(1)
    elif args.strict and validator.warnings:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()