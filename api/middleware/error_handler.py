"""
Error Handler Middleware

Global error handling for consistent API responses.
"""

import logging
import traceback
from typing import Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("rfp_intelligence.api.errors")


class APIError(Exception):
    """Base API error with status code and error code."""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR"
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


class NotFoundError(APIError):
    """Resource not found error."""
    
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, 404, "NOT_FOUND")


class ValidationError(APIError):
    """Validation error."""
    
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, 400, "VALIDATION_ERROR")


class AuthenticationError(APIError):
    """Authentication error."""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, 401, "AUTH_REQUIRED")


class AuthorizationError(APIError):
    """Authorization error."""
    
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, 403, "PERMISSION_DENIED")


class RateLimitError(APIError):
    """Rate limit exceeded error."""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, 429, "RATE_LIMIT_EXCEEDED")


def setup_error_handlers(app: FastAPI):
    """
    Set up global error handlers for the application.
    
    Args:
        app: FastAPI application instance
    """
    
    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError):
        """Handle custom API errors."""
        logger.warning(f"API Error: {exc.error_code} - {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message
                }
            }
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": "HTTP_ERROR",
                    "message": exc.detail
                }
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": errors
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        # Log the full traceback
        logger.error(f"Unhandled exception: {str(exc)}")
        logger.error(traceback.format_exc())
        
        # Don't expose internal errors in production
        from config.settings import settings
        
        if settings.api_env == "development":
            message = str(exc)
        else:
            message = "An internal error occurred"
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": message
                }
            }
        )
