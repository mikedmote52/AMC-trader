#!/usr/bin/env python
"""
Wrapper script for Render cron job to run discovery
"""
import sys
import os
import subprocess

# Run the discovery job directly as a subprocess to avoid import issues
if __name__ == "__main__":
    result = subprocess.run(
        [sys.executable, "backend/src/jobs/discover.py"],
        env=os.environ.copy()
    )
    sys.exit(result.returncode)