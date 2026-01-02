"""
Job Queue Service

Helper functions to enqueue jobs and check status.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from arq import create_pool
from arq.connections import ArqRedis

from workers.settings import get_redis_settings


# Module-level connection pool
_redis_pool: Optional[ArqRedis] = None


async def get_redis_pool() -> ArqRedis:
    """Get or create Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = await create_pool(get_redis_settings())
    return _redis_pool


async def close_redis_pool():
    """Close the Redis connection pool."""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None


async def enqueue_analysis_job(rfp_id: str, org_id: Optional[str] = None) -> str:
    """
    Enqueue a full analysis job.
    
    Args:
        rfp_id: RFP to analyze
        org_id: Organization context
        
    Returns:
        Job ID for tracking
    """
    job_id = str(uuid.uuid4())
    
    redis = await get_redis_pool()
    
    # Initialize job status
    await redis.hset(
        f"job:{job_id}",
        mapping={
            "job_id": job_id,
            "rfp_id": rfp_id,
            "org_id": org_id or "",
            "status": "queued",
            "current_step": "0",
            "total_steps": "5",
            "step_name": "",
            "step_description": "Waiting to start...",
            "progress_percent": "0",
            "error": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    )
    await redis.expire(f"job:{job_id}", 86400)  # 24 hour TTL
    
    # Enqueue the job
    await redis.enqueue_job(
        "run_analysis_job",
        job_id,
        rfp_id,
        org_id,
        _job_id=job_id
    )
    
    # Also track job by RFP ID for quick lookup
    await redis.set(f"rfp_job:{rfp_id}", job_id, ex=86400)
    
    return job_id


async def enqueue_single_agent_job(
    rfp_id: str, 
    agent_name: str,
    org_id: Optional[str] = None
) -> str:
    """
    Enqueue a single agent job.
    
    Args:
        rfp_id: RFP to process
        agent_name: Agent to run
        org_id: Organization context
        
    Returns:
        Job ID for tracking
    """
    job_id = str(uuid.uuid4())
    
    redis = await get_redis_pool()
    
    # Initialize job status
    await redis.hset(
        f"job:{job_id}",
        mapping={
            "job_id": job_id,
            "rfp_id": rfp_id,
            "agent": agent_name,
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    )
    await redis.expire(f"job:{job_id}", 86400)
    
    # Enqueue the job
    await redis.enqueue_job(
        "run_single_agent_job",
        job_id,
        rfp_id,
        agent_name,
        org_id,
        _job_id=job_id
    )
    
    return job_id


async def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get job status from Redis.
    
    Args:
        job_id: Job to check
        
    Returns:
        Job status dict or None if not found
    """
    redis = await get_redis_pool()
    
    status = await redis.hgetall(f"job:{job_id}")
    
    if not status:
        return None
    
    # Convert bytes to strings if needed
    result = {}
    for key, value in status.items():
        k = key.decode() if isinstance(key, bytes) else key
        v = value.decode() if isinstance(value, bytes) else value
        result[k] = v
    
    # Convert numeric fields
    if "current_step" in result:
        result["current_step"] = int(result["current_step"])
    if "total_steps" in result:
        result["total_steps"] = int(result["total_steps"])
    if "progress_percent" in result:
        result["progress_percent"] = int(result["progress_percent"])
    
    return result


async def get_job_by_rfp(rfp_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the latest job status for an RFP.
    
    Args:
        rfp_id: RFP to check
        
    Returns:
        Job status dict or None if no job found
    """
    redis = await get_redis_pool()
    
    job_id = await redis.get(f"rfp_job:{rfp_id}")
    
    if not job_id:
        return None
    
    if isinstance(job_id, bytes):
        job_id = job_id.decode()
    
    return await get_job_status(job_id)


async def cancel_job(job_id: str) -> bool:
    """
    Cancel a queued/running job.
    
    Note: This only marks the job as cancelled in Redis.
    The worker should check this and stop processing.
    
    Args:
        job_id: Job to cancel
        
    Returns:
        True if job was found and cancelled
    """
    redis = await get_redis_pool()
    
    exists = await redis.exists(f"job:{job_id}")
    if not exists:
        return False
    
    await redis.hset(
        f"job:{job_id}",
        mapping={
            "status": "cancelled",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    )
    
    return True
