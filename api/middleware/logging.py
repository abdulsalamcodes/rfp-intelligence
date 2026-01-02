"""
Logging Middleware

Request/response logging for observability.
"""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("rfp_intelligence.api.requests")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all requests and responses.
    
    Logs:
    - Request method, path, and correlation ID
    - Response status code and duration
    - Errors with details
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate correlation ID for request tracing
        correlation_id = str(uuid.uuid4())[:8]
        request.state.correlation_id = correlation_id
        
        # Start timer
        start_time = time.perf_counter()
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Log request
        logger.info(
            f"[{correlation_id}] {request.method} {request.url.path} "
            f"from {client_ip}"
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Add headers
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
            
            # Log response
            log_level = logging.INFO if response.status_code < 400 else logging.WARNING
            logger.log(
                log_level,
                f"[{correlation_id}] {request.method} {request.url.path} "
                f"-> {response.status_code} ({duration_ms:.2f}ms)"
            )
            
            return response
            
        except Exception as e:
            # Calculate duration even on error
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Log error
            logger.error(
                f"[{correlation_id}] {request.method} {request.url.path} "
                f"ERROR: {str(e)} ({duration_ms:.2f}ms)"
            )
            raise


def get_correlation_id(request: Request) -> str:
    """Get the correlation ID from the request state."""
    return getattr(request.state, "correlation_id", "unknown")
