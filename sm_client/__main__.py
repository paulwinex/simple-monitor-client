# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "apscheduler>=3.10.4",
#     "httpx>=0.26.0",
#     "psutil>=5.9.8",
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
Simple Monitor Client - Collects system metrics and sends to backend.

Usage:
    uv run sm_client/__main__.py

Or from any directory:
    uv run -m sm_client
"""
import asyncio
import sys

from sm_client.app import main

if __name__ == "__main__":
    if "--check" in sys.argv:
        from sm_client.utils import check_sensors
        asyncio.run(check_sensors())
    else:
        asyncio.run(main())
