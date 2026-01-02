"""
Workers Package

Background job processing with ARQ (async Redis queue).
"""

from workers.settings import WorkerSettings, get_redis_settings
from workers.analysis import run_analysis_job, run_single_agent_job
from workers.queue import (
    get_redis_pool,
    close_redis_pool,
    enqueue_analysis_job,
    enqueue_single_agent_job,
    get_job_status,
    get_job_by_rfp,
    cancel_job
)

__all__ = [
    # Settings
    "WorkerSettings",
    "get_redis_settings",
    # Jobs
    "run_analysis_job",
    "run_single_agent_job",
    # Queue operations
    "get_redis_pool",
    "close_redis_pool",
    "enqueue_analysis_job",
    "enqueue_single_agent_job",
    "get_job_status",
    "get_job_by_rfp",
    "cancel_job"
]

