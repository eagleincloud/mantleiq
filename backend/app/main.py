"""
MantleIQ Discovery Engine - FastAPI Application

Natural Hydrogen Prospectivity Scoring & Attribution Platform
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.core.config import settings
from app.core.database import init_db
from app.api import basins_router, analysis_router, zones_router, export_router, results_router
from app.api.data_layers import router as data_layers_router
from app.api.grids import router as grids_router
from app.api.prospects import router as prospects_router

# Configure logging
logging.basicConfig(level=settings.api_log_level)
logger = logging.getLogger(__name__)


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    # Startup
    logger.info("🚀 Starting MantleIQ Discovery Engine")
    try:
        init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")

    yield

    # Shutdown
    logger.info("🛑 Shutting down MantleIQ Discovery Engine")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="AI-powered geospatial discovery system for natural hydrogen prospectivity scoring",
    version=settings.app_version,
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)


# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.

    Returns:
        dict: Service status and version info
    """
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to MantleIQ Discovery Engine",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


# ============================================================================
# API ROUTES - REGISTER ALL ROUTERS
# ============================================================================

app.include_router(basins_router)
app.include_router(analysis_router)
app.include_router(zones_router)
app.include_router(export_router)
app.include_router(results_router)
app.include_router(data_layers_router)
app.include_router(grids_router)
app.include_router(prospects_router)


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for all unhandled errors"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_type": type(exc).__name__,
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.api_log_level.lower(),
    )
