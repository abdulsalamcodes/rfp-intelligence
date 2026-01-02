"""
RFP Intelligence - FastAPI Application

Main API server for RFP analysis and proposal generation.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from config.logging_config import setup_logging
from api.routes import analysis, documents

# Set up logging
logger = setup_logging(log_level="INFO")
logger.info("Starting RFP Intelligence API...")

# Create FastAPI app
app = FastAPI(
    title="RFP Intelligence API",
    description="AI-driven RFP analysis and proposal generation",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(analysis.router, prefix="/api", tags=["Analysis"])


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "RFP Intelligence API",
        "version": "1.0.0",
        "status": "running",
        "llm_provider": settings.llm_provider.value,
        "model": settings.default_model
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
