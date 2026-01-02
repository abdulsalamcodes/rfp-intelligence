"""
RFP Intelligence - FastAPI Application

Main API server for RFP analysis and proposal generation.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from config.logging_config import setup_logging
from api.routes import analysis, documents
from api.routes.organizations import router as orgs_router
from api.auth.router import router as auth_router
from api.middleware.error_handler import setup_error_handlers
from api.middleware.logging import LoggingMiddleware
from api.middleware.rate_limit import setup_rate_limiting

# Set up logging
logger = setup_logging(log_level="INFO")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    logger.info("Starting RFP Intelligence API...")
    logger.info(f"Environment: {settings.api_env}")
    logger.info(f"LLM Provider: {settings.llm_provider.value}")
    
    # Startup: Seed default plans if using database
    try:
        from services.storage import is_using_database
        if is_using_database():
            from services.billing import seed_plans
            plans = await seed_plans()
            if plans:
                logger.info(f"Seeded {len(plans)} default plans")
    except Exception as e:
        logger.warning(f"Could not seed plans: {e}")
    
    yield
    
    # Shutdown: Close connections
    try:
        from workers.queue import close_redis_pool
        await close_redis_pool()
    except Exception:
        pass  # Redis may not be configured
    
    logger.info("Shutting down RFP Intelligence API...")


# Create FastAPI app
app = FastAPI(
    title="RFP Intelligence API",
    description="AI-driven RFP analysis and proposal generation",
    version="1.0.0",
    lifespan=lifespan
)

# Set up error handlers (before middleware)
setup_error_handlers(app)

# Set up rate limiting
setup_rate_limiting(app)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Configure CORS (should be last middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# API Routes
# ============================================================================

# v1 API routes (production)
app.include_router(auth_router, prefix="/api/v1", tags=["Authentication"])
app.include_router(orgs_router, prefix="/api/v1", tags=["Organizations"])

# Import and register v1 routes
from api.routes.rfps import router as rfps_router
from api.routes.billing import router as billing_router
app.include_router(rfps_router, prefix="/api/v1", tags=["RFPs"])
app.include_router(billing_router, prefix="/api/v1", tags=["Billing"])

# Legacy routes (for Streamlit compatibility - will deprecate)
app.include_router(documents.router, prefix="/api/documents", tags=["Documents (Legacy)"])
app.include_router(analysis.router, prefix="/api", tags=["Analysis (Legacy)"])


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "RFP Intelligence API",
        "version": "1.0.0",
        "status": "running",
        "environment": settings.api_env,
        "llm_provider": settings.llm_provider.value,
        "model": settings.default_model,
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.api_env
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
