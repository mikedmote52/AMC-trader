#!/usr/bin/env python
"""
Wrapper script for Render cron job to run discovery
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Run the discovery job
from src.jobs.discover import main

if __name__ == "__main__":
    sys.exit(main())