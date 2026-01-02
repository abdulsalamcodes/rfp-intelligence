"""
ARQ Worker Settings

Configuration for the async Redis queue worker.
"""

from arq.connections import RedisSettings

from config.settings import settings


def get_redis_settings() -> RedisSettings:
    """
    Get Redis connection settings from app config.
    
    Parses the REDIS_URL environment variable.
    """
    url = settings.redis_url
    
    # Parse redis://host:port or redis://user:pass@host:port/db
    if url.startswith("redis://"):
        url = url[8:]  # Remove redis://
    
    # Handle authentication
    if "@" in url:
        auth, host_part = url.rsplit("@", 1)
        if ":" in auth:
            _, password = auth.split(":", 1)
        else:
            password = None
    else:
        host_part = url
        password = None
    
    # Parse host:port/db
    if "/" in host_part:
        host_port, db = host_part.rsplit("/", 1)
        database = int(db) if db else 0
    else:
        host_port = host_part
        database = 0
    
    if ":" in host_port:
        host, port = host_port.rsplit(":", 1)
        port = int(port)
    else:
        host = host_port
        port = 6379
    
    return RedisSettings(
        host=host,
        port=port,
        password=password,
        database=database
    )


class WorkerSettings:
    """
    ARQ Worker configuration.
    
    Usage:
        arq workers.settings.WorkerSettings
    """
    
    # Redis connection
    redis_settings = get_redis_settings()
    
    # Job functions to register
    functions = [
        "workers.analysis.run_analysis_job",
    ]
    
    # Worker behavior
    max_jobs = 5  # Max concurrent jobs
    job_timeout = 600  # 10 minutes max per job
    keep_result = 3600  # Keep results for 1 hour
    
    # Retry settings
    max_tries = 3
    retry_delay = 60  # Seconds between retries
    
    # Health check
    health_check_interval = 30
    
    @staticmethod
    async def on_startup(ctx):
        """Called when worker starts."""
        import logging
        logging.info("ARQ Worker starting...")
    
    @staticmethod
    async def on_shutdown(ctx):
        """Called when worker shuts down."""
        import logging
        logging.info("ARQ Worker shutting down...")
