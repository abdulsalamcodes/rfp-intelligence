#!/usr/bin/env python
"""
Worker Startup Script

Run this to start the ARQ background worker.

Usage:
    python -m workers.startup
    
Or with arq CLI:
    arq workers.settings.WorkerSettings
"""

import asyncio
import logging

from arq import run_worker

from workers.settings import WorkerSettings


def main():
    """Start the ARQ worker."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger = logging.getLogger("rfp_intelligence.worker")
    logger.info("Starting ARQ worker...")
    
    # Run the worker
    run_worker(WorkerSettings)


if __name__ == "__main__":
    main()
