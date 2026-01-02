"""
Rate Limiting Middleware

Protect API from abuse with rate limiting.
"""

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware


def get_identifier(request: Request) -> str:
    """
    Get rate limit identifier from request.
    
    Uses authenticated user ID if available, otherwise client IP.
    """
    # Try to get user ID from request state (set by auth middleware)
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    
    # Fall back to IP address
    return get_remote_address(request)


# Create limiter instance
limiter = Limiter(key_func=get_identifier)


def setup_rate_limiting(app: FastAPI):
    """
    Set up rate limiting for the application.
    
    Default limits (can be overridden per-route):
    - 100 requests per minute for general endpoints
    - 10 requests per minute for expensive operations (analysis)
    
    Args:
        app: FastAPI application instance
    """
    # Add state to app
    app.state.limiter = limiter
    
    # Add exception handler
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Add middleware
    app.add_middleware(SlowAPIMiddleware)


# Rate limit decorators for use on routes
# Usage: @limiter.limit("5/minute")

# Common limits
LIMIT_STANDARD = "100/minute"
LIMIT_ANALYSIS = "10/minute"  # Expensive LLM operations
LIMIT_AUTH = "20/minute"  # Auth operations
LIMIT_UPLOAD = "30/minute"  # File uploads
